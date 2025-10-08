# -*- coding: utf-8 -*-

"""
API and network communication module
"""

import sys
import os
import ssl
import json
import time
import re
import gzip
import http.cookiejar as cookielib
from urllib import request as libRequest
from urllib.parse import urlencode
from resources import config
from resources.lib.libraries import control, cache

logger = control.logger

# Global state
cookieJar = None
_opener = None

def initialize(force=False):
    """Initialize cookie jar and opener"""
    logger.logInfo('called function')
    global cookieJar

    if cookieJar is None or force:
        logger.logDebug('Data path: %s' % control.dataPath)
        cookiePath = control.dataPath if control.pathExists(control.dataPath) else control.tempPath
        cookieFile = os.path.join(cookiePath, config.cookieFileName)
        cookieJar = cookielib.LWPCookieJar(cookieFile)
        
        if os.path.exists(cookieFile):
            try:
                cookieJar.load(ignore_discard=True, ignore_expires=True)
                cookieJar.clear_expired_cookies()
            except Exception as e:
                logger.logError(e)
        else:
            try:
                cookieJar.save(ignore_discard=True, ignore_expires=True)
                logger.logDebug('Created new cookie file: %s' % cookieFile)
            except Exception as e:
                logger.logError('Failed to create cookie file: %s' % e)

def cookiesArePresent():
    """Check if cookies are present"""
    global cookieJar
    return len(cookieJar) > 0

def cookiesFileExists():
    """Check if cookies file exists"""
    global cookieJar
    if isinstance(cookieJar, cookielib.LWPCookieJar):
        return os.path.exists(cookieJar.filename)
    return False

def get_opener():
    """Get or create a reusable URL opener instance"""
    global _opener, cookieJar
    if _opener is None:
        _opener = libRequest.build_opener(
            libRequest.HTTPRedirectHandler(), 
            libRequest.HTTPCookieProcessor(cookieJar)
        )
    logger.logDebug('cookies file exists: %s' % cookiesFileExists())
    if cookiesFileExists():
        logger.logDebug('cookie content : %s' % control.readFile(cookieJar.filename))
    return _opener

def reset_opener():
    """Reset the opener instance"""
    global _opener
    _opener = None

def callServiceApi(path, params={}, headers=[], base_url=config.websiteUrl, useCache=True, jsonData=False, returnMessage=True):
    """Call service API"""
    logger.logInfo('called function with param (%s%s)' % (base_url, path))
    global cookieJar

    url = base_url + path
    res = {}
    cached = False
    toCache = False
    
    if not returnMessage:
        useCache = False

    key = config.urlCachePrefix + cache.generateHashKey(url + urlencode(params))
    logger.logDebug('Key %s : %s - %s' % (key, url, params))

    if useCache:
        tmp = cache.shortCache.getMulti(key, ['url', 'timestamp'])
        if (tmp == '') or (tmp[0] == '') or (time.time()-float(tmp[1])>int(control.setting('cacheTTL'))*60):
            toCache = True
            logger.logInfo('No cache for (%s)' % key)
        else:
            cached = True
            res['message'] = tmp[0]
            logger.logInfo('Used cache for (%s)' % key)

    if not cached:
        header_dict = {h[0]: h[1] for h in headers}
        
        if 'User-agent' not in header_dict:
            header_dict['User-agent'] = config.userAgents.get(base_url, config.userAgents['default'])
        if 'Referer' not in header_dict:
            header_dict['Referer'] = config.websiteUrl+'/'
        if 'Origin' not in header_dict:
            header_dict['Origin'] = config.websiteUrl
        if 'Accept' not in header_dict:
            header_dict['Accept'] = '*/*'
        if 'Accept-Encoding' not in header_dict:
            header_dict['Accept-Encoding'] = 'gzip, deflate'
        if 'Connection' not in header_dict:
            header_dict['Connection'] = 'keep-alive'
        if 'Accept-Language' not in header_dict:
            header_dict['Accept-Language'] = 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3'
        
        try:
            opener = get_opener()
            request = libRequest.Request(url)
            logger.logDebug('### Request URL & params ###')
            logger.logDebug('%s - %s' % (url, params))
            logger.logDebug('### Request headers ###')
            for key, value in header_dict.items():
                request.add_header(key, value)
                logger.logDebug(f"  {key}: {value}")

            requestTimeOut = int(control.setting('requestTimeOut')) if control.setting('requestTimeOut') != '' else 20
            response = None
            if jsonData:
                logger.logDebug('### POST Request ###')
                response = opener.open(request, json.dumps(params).encode("utf-8"), timeout=requestTimeOut)
            else:
                if params:
                    logger.logDebug('### POST Request ###')
                    data_encoded = urlencode(params).encode("utf-8")
                    response = opener.open(request, data_encoded, timeout=requestTimeOut)
                else:
                    logger.logDebug('### GET Request ###')
                    response = opener.open(request, timeout=requestTimeOut)
            
            logger.logDebug('### Response headers ###')
            logger.logDebug(response.geturl())
            logger.logDebug('### Response redirect URL ###')
            logger.logDebug(response.info())
            logger.logDebug('### Response ###')
            
            if response.info().get('Content-Encoding') == 'gzip':
                res['message'] = gzip.decompress(response.read())
            else:
                res['message'] = response.read() if response else ''
                
            res['status'] = int(response.getcode())
            res['headers'] = response.info()
            res['url'] = response.geturl()

            logger.logInfo('Response status: %s' % res['status'])
            logger.logDebug(res)

            for header, value in response.headers.items():
                logger.logDebug(f"{header}: {value}")

            # Save cookies after successful response
            if (len(cookieJar) > 0):
                logger.logDebug('Cookies in jar: %d' % len(cookieJar))
                for cookie in cookieJar:
                    logger.logDebug('Cookie: %s=%s (domain=%s, path=%s, secure=%s, expires=%s)' % (cookie.name, cookie.value, cookie.domain, cookie.path, cookie.secure, cookie.expires))
                try:
                    cookieJar.save(ignore_discard=True, ignore_expires=True)
                    logger.logDebug('Cookies saved to: %s' % cookieJar.filename)
                except Exception as e:
                    logger.logError('Failed to save cookies: %s' % e)
            
        except (libRequest.URLError, ssl.SSLError) as e:
            logger.logError(e)
            message = '%s : %s' % (e, url)
            logger.logSevere(message)
            control.showNotification(message, control.lang(30004))
            
            if 'Errno 11001' in str(message):
                logger.logError('Errno 11001 - No internet connection')
                control.showNotification(control.lang(37031), control.lang(30004), time=5000)
            toCache = False
        
        if toCache and res:
            value = res.get('message') if re.compile('application/json', re.IGNORECASE).search('|'.join(res['headers'].keys())) or re.compile('binary/octet-stream', re.IGNORECASE).search('|'.join(res['headers'].values())) else repr(res.get('message'))
            cache.shortCache.setMulti(key, {'url': value, 'timestamp': time.time()})
            logger.logDebug(res.get('message'))
            logger.logInfo('Stored in cache (%s) : %s' % (key, {'url': value, 'timestamp': time.time()}))
    
    return res.get('message') if returnMessage else res

def callJsonApi(path, params={}, headers=[], base_url=config.webserviceUrl, useCache=True, jsonData=True):
    """Call JSON API"""
    logger.logInfo('called function')
    headers.append(('Accept', 'application/json'))
    if params != {} and jsonData:
        headers.append(('Content-Type', 'application/json'))
    res = callServiceApi(path, params, headers, base_url, useCache, jsonData)
    
    if not res:
        return {}
    
    try:
        return json.loads(res)
    except (json.JSONDecodeError, ValueError) as e:
        logger.logError(f'JSON decode error: {e}')
        return {}

def callGraphQLApi(query, variables={}, headers=[], base_url=config.webserviceUrl, useCache=True):
    """Call GraphQL API"""
    logger.logInfo('called function')
    headers.append(('Accept', 'application/graphql-response+json, application/json'))
    headers.append(('Content-Type', 'application/json'))
    params = {
        'query': query,
        'variables': variables
    }
    res = callServiceApi(config.uri.get('graphql'), params, headers, base_url, useCache, jsonData=True)

    if not res:
        return {}
    
    try:
        response = json.loads(res)
        if 'data' in response:
            return response['data']
        return {}
    except (json.JSONDecodeError, ValueError) as e:
        logger.logError(f'JSON decode error: {e}')
        return {}

def getFromCookieByName(string, startWith=False):
    """Get cookie by name"""
    logger.logInfo('called function')
    global cookieJar
    cookieObj = None
    
    for c in cookieJar:
        if (startWith and c.name.startswith(string)) or (not startWith and c.name == string):
            cookieObj = c
            break
                
    return cookieObj
    
def getCookieContent(filter=False, exceptFilter=False):
    """Get cookie content"""
    logger.logInfo('called function')
    global cookieJar
    cookie = []
    for c in cookieJar:
        if (filter and c.name not in filter) or (exceptFilter and c.name in exceptFilter):
            continue
        cookie.append('%s=%s' % (c.name, c.value))
    return cookie

# Initialize on import
initialize()
