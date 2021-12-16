#!/usr/bin/env python2
# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

import re,shutil,threading,ssl,time,xbmc,xbmcaddon
import http.cookiejar as cookielib
from six.moves import socketserver
from urllib import request as libRequest
from urllib.parse import quote,urlencode,urlparse,parse_qsl
from http.server import SimpleHTTPRequestHandler
from resources import config
from resources.lib.libraries import control

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
            url = query.get('url') + '&UserAuthentication=%s' % control.setting('iWantUserAuthentication')
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

    while not monitor.abortRequested():
        # Sleep/wait for abort for 10 seconds
        if monitor.waitForAbort(10):
            # Abort was requested while waiting. We should exit
            break

    server.shutdown()
    server_thread.join()
    xbmc.log('[%s] - Service: stopping HTTP proxy server on port %s' % (control.addonInfo('name'), httpPort), level=xbmc.LOGINFO)
    if libActive == True: 
        libChecker.shutdown()
        libSchedTask.join()
        xbmc.log('[%s] - Service: stopping library checker' % control.addonInfo('name'), level=xbmc.LOGINFO)