#!/usr/bin/env python2
# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

import SocketServer,cgi,re,shutil,threading,urllib,urllib2,ssl,cookielib,time
import xbmc,xbmcaddon

from SimpleHTTPServer import SimpleHTTPRequestHandler
from urlparse import urlparse, parse_qsl
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
        else:
            query = self.getQueryParameters(self.path)
            if ('url' in query):
            
                requestHeaders = []
                requestHeaders.append(('User-Agent', self._user_agent))
                requestHeaders.append(('Origin', self._websiteUrl))
                requestHeaders.append(('Referer', self._websiteUrl+'/'))
                requestHeaders.append(('Sec-Fetch-Mode', 'cors'))
                if ('tfcmsl.akamaized.net' in query.get('url')): 
                    requestHeaders.append(('Sec-Fetch-Dest', 'empty'))
                    requestHeaders.append(('Sec-Fetch-Site', 'cross-site'))
                else:
                    requestHeaders.append(('Accept', '*/*,akamai/media-acceleration-sdk;b=1702200;v=1.2.2;p=javascript'))
                res = self.urlopen(query.get('url'), headers=requestHeaders)
                
                if (res.get('status')):
                    sublevel = int(query.get('sublevel', 0)) + 1
                    proxyUrlFormat = control.setting('proxyStreamingUrl')
                    if 'http' in res.get('body') or 'force' in query or sublevel == 3: 
                        content = re.sub(r'(http[^\s"]+)', lambda x: proxyUrlFormat % (control.setting('proxyHost'), control.setting('proxyPort'), urllib.quote(x.group(0)), '&force=1&sublevel=%s' % sublevel), res.get('body'))
                    else:
                        streamingServerURL = re.compile('(http.?://[^\?]+/)', re.IGNORECASE).search(query.get('url')).group(1)
                        content = re.sub(r'^([^#].+)', lambda x: proxyUrlFormat % (control.setting('proxyHost'), control.setting('proxyPort'), urllib.quote(streamingServerURL+x.group(0)), '&sublevel=%s' % sublevel), res.get('body'), flags=re.MULTILINE)
                    self.send_response(res.get('status'))
                    for header, value in res.get('headers').items():
                        if (header.lower() == 'content-length'):
                            value = len(content)
                        if (header.lower() == 'set-cookie'):
                            netloc = urlparse(proxyUrlFormat).netloc
                            host = netloc.split(':')[0] if ':' in netloc else netloc
                            value = re.sub(r'path=[^;]+; domain=.+', 'path=/; domain=%s' % (host), value)
                        if (header.lower() in ('server', 'set-cookie')):
                            continue
                        self.send_header(header, value)
                    self.end_headers()
                    self.wfile.write(content)
                    self.wfile.close()
                else:
                    self.send_error(522)
            else:
                self.send_error(400)

    def do_POST(self):
        xbmc.log('Requested POST: %s' % (self.path), level=xbmc.LOGDEBUG)
        query = self.getQueryParameters(self.path)

        requestHeaders = dict(self.headers)
        # del requestHeaders['content-type']
        # requestHeaders['User-Agent'] = self._user_agent
        # requestHeaders['Origin'] = self._websiteUrl
        # requestHeaders['Referer'] = self._websiteUrl+'/'
        # requestHeaders['Sec-Fetch-Dest'] = 'empty'
        # requestHeaders['Sec-Fetch-Mode'] = 'cors'
        # requestHeaders['Sec-Fetch-Site'] = 'same-origin'

        for header in requestHeaders.items():
            xbmc.log('Service HEADER_OUT: %s: %s' % (header[0], header[1]), level=xbmc.LOGDEBUG)

        data = self.rfile.read(int(self.headers.getheader('content-length', 0)))
        xbmc.log('Service DATA_OUT: %s' % repr(data), level=xbmc.LOGDEBUG)

        if ('url' in query):
            url = query.get('url') + '&UserAuthentication=%s' % control.setting('iWantUserAuthentication')
            xbmc.log('Service URL_OUT: %s' % url, level=xbmc.LOGDEBUG)
            res = self.urlopen(url, params=data, headers=requestHeaders.items())
            
            if (res.get('status')):
                proxyUrlFormat = control.setting('proxyStreamingUrl')
                content = res.get('body')
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
                self.wfile.close()
            else:
                self.send_error(522)
        else:
            self.send_error(400)
                        
    def urlopen(self, url, params = {}, headers = []):        
        res = {}
        opener = urllib2.build_opener(urllib2.HTTPRedirectHandler(), urllib2.HTTPCookieProcessor(self._cj))
        opener.addheaders = headers
        requestTimeOut = int(xbmcaddon.Addon().getSetting('requestTimeOut')) if xbmcaddon.Addon().getSetting('requestTimeOut') != '' else 20
        response = None
        
        try:
            if params:
                data = params if isinstance(params, str) else urllib.urlencode(params)
                response = opener.open(url, data, timeout = requestTimeOut)
            else:
                response = opener.open(url, timeout = requestTimeOut)
                
            res['body'] = response.read() if response else ''
            res['status'] = response.getcode()
            res['headers'] = response.info()
            res['url'] = response.geturl()
        except (urllib2.URLError, ssl.SSLError) as e:
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
    server = SocketServer.TCPServer(('', httpPort), ProxyHandler)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    xbmc.log('[%s] Service: starting HTTP proxy server on port %s' % (control.addonInfo('name'), httpPort), level=xbmc.LOGNOTICE)
    
    libActive = True if control.setting('libraryAutoUpdate') == 'true' else False
    
    if libActive == True:
        libChecker = LibraryChecker()
        libSchedTask = threading.Thread(target=libChecker.checkLibraryUpdates)
        libSchedTask.start()
        xbmc.log('[%s] Service: starting library checker' % control.addonInfo('name'), level=xbmc.LOGNOTICE)
    
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        # Sleep/wait for abort for 10 seconds
        if monitor.waitForAbort(10):
            # Abort was requested while waiting. We should exit
            break

    server.shutdown()
    server_thread.join()
    xbmc.log('[%s] - Service: stopping HTTP proxy server on port %s' % (control.addonInfo('name'), httpPort), level=xbmc.LOGNOTICE)
    if libActive == True: 
        libChecker.shutdown()
        libSchedTask.join()
        xbmc.log('[%s] - Service: stopping library checker' % control.addonInfo('name'), level=xbmc.LOGNOTICE)