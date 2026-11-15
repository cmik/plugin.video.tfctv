#!/usr/bin/env python2
# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

import re
#import shutil
import threading
import ssl
import time
import xbmc
import xbmcaddon
import xbmcgui
import http.cookiejar as cookielib
from six.moves import socketserver
from urllib import request as libRequest
from urllib.parse import quote, urlencode, urlparse, parse_qsl
from http.server import SimpleHTTPRequestHandler
from resources import config
from resources.lib.libraries import control

class PlaybackMonitor(xbmc.Player):
    """Keeps where each episode was left (see libraries/playertracker.py)"""

    def __init__(self):
        xbmc.Player.__init__(self)
        from resources.lib.libraries import playertracker
        from resources.lib.models import userdata
        self._tracker = playertracker
        self.tracker = playertracker.PlaybackTracker(lambda: userdata.UserData(control.userDataFile))
        self._window = xbmcgui.Window(10000)
        self._trakt = None  # (scrobble body of what is played) while it is scrobbled

    def _log(self, message, level=xbmc.LOGINFO):
        xbmc.log('[%s] Playback tracking: %s' % (control.addonInfo('name'), message), level=level)

    def _playedEpisode(self):
        """The id of the episode the plugin started: the property of the played item, else what the plugin left in the window"""
        try:
            episodeId = self.getPlayingItem().getProperty(self._tracker.ITEM_PROPERTY)
            if episodeId:
                return episodeId
        except Exception as e:
            self._log('can\'t read the played item: %s' % e, xbmc.LOGDEBUG)
        info = self._tracker.decode(self._window.getProperty(self._tracker.PROPERTY))
        return info['id'] if info else None

    def onAVStarted(self):
        try:
            episodeId = self._playedEpisode()
            if not episodeId:
                return  # not played by this add-on
            self._window.clearProperty(self._tracker.PROPERTY)
            self.tracker.start(episodeId)
            self._log('following %s' % episodeId)
            threading.Thread(target=self._follow, args=(episodeId,)).start()
            self._upNext(episodeId)
            threading.Thread(target=self._traktStart, args=(episodeId,)).start()
        except Exception as e:
            self._log('start failed: %s' % e, xbmc.LOGERROR)

    def _traktStart(self, episodeId):
        """Prepare the scrobbling of what starts (see libraries/trakt.py) and tell Trakt"""
        self._trakt = None
        if control.getAddonSetting('traktScrobble') != 'true':
            return
        try:
            from resources.lib.libraries import trakt
            from resources.lib.models import episodes, shows, userdata
            client = trakt.fromSettings(userdata.UserData(control.userDataFile))
            if not client.isConnected():
                return
            found = episodes.Episode(control.episodesFile).get(episodeId)
            current = found[0] if found else None
            parent = shows.Show(control.showsFile).get(current.get('parentid')) if current and current.get('parentid') else None
            show = parent[0] if parent else None
            traktId = None
            if current and current.get('ltype') != 'movie' and current.get('parentid'):
                # Trakt knows the show by its own title, find it once (in a thread: it is a network call)
                traktId = client.resolveShow(current.get('parentid'), (show or {}).get('name') or current.get('show'))
            body = trakt.scrobbleBody(current, show, 0, traktId)
            if not body:
                self._log('Trakt: %s can\'t be identified, not scrobbled' % episodeId)
                return
            self._trakt = body
            self._traktSend('start', 0.0)
        except Exception as e:
            self._log('Trakt start failed: %s' % e, xbmc.LOGERROR)

    def _traktSend(self, action, progress):
        """Tell Trakt in the background (a slow answer must not hold the player)"""
        if not self._trakt:
            return
        body = self._trakt

        def send():
            try:
                # a database connection can't change thread: the client is made in the one that sends
                from resources.lib.libraries import trakt
                from resources.lib.models import userdata
                client = trakt.fromSettings(userdata.UserData(control.userDataFile))
                status = client.scrobble(action, dict(body, progress=round(progress, 2)))
                self._log('Trakt: %s at %d%% -> HTTP %s' % (action, progress, status))
            except Exception as e:
                self._log('Trakt %s failed: %s' % (action, e), xbmc.LOGERROR)
        threading.Thread(target=send).start()

    def _traktProgress(self):
        from resources.lib.libraries import trakt
        return trakt.progressOf(self.tracker.position, self.tracker.total)

    def _upNext(self, episodeId):
        """Tell the Up Next add-on which episode follows the one that starts (see libraries/upnext.py)"""
        if control.setting('upNext') == 'false' or not xbmc.getCondVisibility('System.AddonIsEnabled(service.upnext)'):
            return
        try:
            from resources.lib.libraries import upnext
            from resources.lib.models import episodes, shows
            addonId = control.addonInfo('id')
            data = upnext.buildData(episodes.Episode(control.episodesFile), shows.Show(control.showsFile), episodeId, addonId)
            if data:
                upnext.send(data, addonId)
                self._log('Up Next: %s is followed by %s' % (episodeId, data['next_episode']['episodeid']))
            else:
                self._log('Up Next: no next episode for %s' % episodeId)
        except Exception as e:
            self._log('Up Next failed: %s' % e, xbmc.LOGERROR)

    def _follow(self, episodeId):
        monitor = xbmc.Monitor()
        while self.tracker.active and self.tracker.episodeId == episodeId and not monitor.abortRequested():
            self._sample()
            monitor.waitForAbort(5)

    def _sample(self):
        try:
            if self.isPlayingVideo():
                position, total = self.getTime(), self.getTotalTime()
                if not total:  # the player answers with the info labels when it doesn't with its methods
                    position, total = float(xbmc.getInfoLabel('Player.Time(secs)') or 0), float(xbmc.getInfoLabel('Player.Duration(secs)') or 0)
                self.tracker.update(position, total)
        except (RuntimeError, ValueError):
            pass  # nothing is playing anymore

    def _finish(self, ended):
        try:
            episodeId, position, total = self.tracker.episodeId, self.tracker.position, self.tracker.total
            if self._trakt:
                self._traktSend('stop', 100.0 if ended else self._traktProgress())
                self._trakt = None
            outcome = self.tracker.finish(ended)
            if episodeId:
                self._log('%s %s at %d/%d s -> %s' % (episodeId, 'ended' if ended else 'stopped', position, total, outcome))
        except Exception as e:
            self._log('stop failed: %s' % e, xbmc.LOGERROR)

    def onPlayBackPaused(self):
        self._sample()
        if self._trakt:
            self._traktSend('pause', self._traktProgress())

    def onPlayBackResumed(self):
        if self._trakt:
            self._traktSend('start', self._traktProgress())

    def onPlayBackStopped(self):
        self._sample()
        self._finish(False)

    def onPlayBackEnded(self):
        self._finish(True)


class ProxyHandler(SimpleHTTPRequestHandler):

    _cj = cookielib.LWPCookieJar()
    _user_agent = config.userAgents['default']
    _websiteUrl = config.websiteUrl
            
    def do_GET(self):
        xbmc.log('Requested GET: %s' % (self.path), level=xbmc.LOGDEBUG)
        if '/healthcheck' in self.path:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
        else:
            self.send_error(404)

    def do_POST(self):
        xbmc.log('Requested POST: %s' % (self.path), level=xbmc.LOGDEBUG)
        query = self.getQueryParameters(self.path)
        requestHeaders = dict(self.headers)

        for header in requestHeaders.items():
            xbmc.log('Service HEADER_OUT: %s: %s' % (header[0], header[1]), level=xbmc.LOGDEBUG)

        length = int(self.headers.get('content-length', 0))
        data = self.rfile.read(length)
        xbmc.log('Service DATA_OUT: %s' % repr(data), level=xbmc.LOGDEBUG)

        if 'url' in query:
            url = query.get('url')
            xbmc.log('Service URL_OUT: %s' % url, level=xbmc.LOGDEBUG)
            res = self.urlopen(url, data, headers=requestHeaders.items())
            
            if res.get('status'):
                proxyUrlFormat = control.setting('proxyStreamingUrl')
                content = res.get('body')
                xbmc.log('Service DATA_IN_LENGTH: %d' % len(content), level=xbmc.LOGDEBUG)
                self.send_response(res.get('status'))
                for header, value in res.get('headers').items():
                    xbmc.log('Service HEADER_IN: %s: %s' % (header, value), level=xbmc.LOGDEBUG)
                    if (header.lower() == 'content-length'):
                        value = len(content)
                    if (header.lower() == 'set-cookie'):
                        netloc = urlparse(proxyUrlFormat).netloc
                        host = netloc.split(':')[0] if ':' in netloc else netloc
                        value = re.sub(r'path=[^;]+; domain=.+', 'path=/; domain=%s' % (host), value)
                    if (header.lower() in ('server', 'set-cookie')):
                        continue
                    self.send_header(header, value)
                xbmc.log('Service BODY_IN: %s' % repr(content), level=xbmc.LOGDEBUG)
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(522)
        else:
            self.send_error(400)
                        
    def urlopen(self, url, params = '', headers = []):        
        res = {}
        opener = libRequest.build_opener(libRequest.HTTPRedirectHandler(), libRequest.HTTPCookieProcessor(self._cj))
        opener.addheaders = headers
        requestTimeOut = int(xbmcaddon.Addon().getSetting('requestTimeOut')) if xbmcaddon.Addon().getSetting('requestTimeOut') != '' else 20
        response = None
        
        try:
            if params:
                # data = urlencode(params) if isinstance(params, dict) else params
                response = opener.open(url, params, timeout = requestTimeOut)
            else:
                response = opener.open(url, timeout = requestTimeOut)
                
            res['body'] = response.read() if response else ''
            res['status'] = response.getcode()
            res['headers'] = response.info()
            res['url'] = response.geturl()
        except (libRequest.URLError, ssl.SSLError) as e:
            message = '%s : %s' % (e, url)
            xbmc.log(message, level=xbmc.LOGERROR)
        
        return res
        
    def getQueryParameters(self, url):
        qparam = {}
        query = url.split('?')[1] if (len(url.split('?')) > 1) else None 
        if query:
            qparam = dict(parse_qsl(query.replace('?','')))
        return qparam 
        

class LibraryChecker():
    _status = True
    _scheduled = 60 * int(control.setting('librayCheckSchedule'))
        
    def checkLibraryUpdates(self):
        first = True
        start = time.time()
        while self._status:
            if ((time.time()-start) > int(self._scheduled)) or first:
                first = False
                start = time.time()
                control.run(config.CHECKLIBRARYUPDATES, 'service')
                time.sleep(10)
            
            
    def shutdown(self):
        self._status = False
        
if __name__ == "__main__":
    httpPort = int(control.setting('proxyPort'))
    # let a restarted service rebind the port right away (the old socket may still be in TIME_WAIT)
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(('', httpPort), ProxyHandler)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    xbmc.log('[%s] Service: starting HTTP proxy server on port %s' % (control.addonInfo('name'), httpPort), level=xbmc.LOGINFO)
    
    libActive = True if control.setting('libraryAutoUpdate') == 'true' else False
    
    if libActive == True:
        libChecker = LibraryChecker()
        libSchedTask = threading.Thread(target=libChecker.checkLibraryUpdates)
        libSchedTask.start()
        xbmc.log('[%s] Service: starting library checker' % control.addonInfo('name'), level=xbmc.LOGINFO)
    
    monitor = xbmc.Monitor()
    playbackMonitor = PlaybackMonitor()

    from resources.lib.libraries import catchup
    from resources.lib.models import userdata
    ticks = 0
    while not monitor.abortRequested():
        # Sleep/wait for abort for 10 seconds
        if monitor.waitForAbort(10):
            # Abort was requested while waiting. We should exit
            break
        ticks += 1
        # look for what is new in the catalog when it is time (not while something is played)
        if ticks * 10 >= catchup.START_DELAY and ticks % (catchup.CHECK_EVERY // 10) == catchup.START_DELAY // 10:
            try:
                hours = control.setting('catalogCheckHours')
                if not playbackMonitor.isPlaying() and catchup.due(userdata.UserData(control.userDataFile).getMeta(catchup.META), time.time(), 24 if hours == '' else hours):
                    xbmc.log('[%s] Service: looking for what is new in the catalog' % control.addonInfo('name'), level=xbmc.LOGINFO)
                    control.run(config.CATCHUPCATALOG, 'service')
            except Exception as e:
                xbmc.log('[%s] Service: can\'t look for what is new: %s' % (control.addonInfo('name'), e), level=xbmc.LOGERROR)

    server.shutdown()
    server.server_close()
    server_thread.join()
    xbmc.log('[%s] - Service: stopping HTTP proxy server on port %s' % (control.addonInfo('name'), httpPort), level=xbmc.LOGINFO)
    if libActive == True: 
        libChecker.shutdown()
        libSchedTask.join()
        xbmc.log('[%s] - Service: stopping library checker' % control.addonInfo('name'), level=xbmc.LOGINFO)