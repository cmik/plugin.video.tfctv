# -*- coding: utf-8 -*-

"""
Utility functions
"""

import os
import time
import datetime
import http.cookiejar as cookielib
from unidecode import unidecode
from resources import config
from resources.lib.libraries import control, cache
from .api import callServiceApi, reset_opener, cookieJar

logger = control.logger
bs = control.soup

def unicodetoascii(text):
    """Convert unicode to ASCII"""
    logger.logInfo('called function')
    try:
        return unidecode(text)
    except Exception as e:
        logger.logError(e)
        return text

def checkProxy():
    """Check proxy connection"""
    logger.logInfo('called function')
    if (control.setting('useProxy') == 'true'):
        url = control.setting('proxyCheckUrl') % (control.setting('proxyHost'), control.setting('proxyPort'))
        response = callServiceApi(url, base_url='', useCache=False, returnMessage=False)
        logger.logDebug(response)
        if response.get('status', '') != 200:
            control.alert(control.lang(37028), title=control.lang(30004))
            return False
    return True

def cleanCookies(notify=True):
    """Clean cookies"""
    logger.logInfo('called function')
    message = ''
    if os.path.exists(os.path.join(control.homePath, 'cache', 'cookies.dat')):
        logger.logInfo('cookies file FOUND (cache)')
        try:
            os.unlink(os.path.join(control.homePath, 'cache', 'cookies.dat'))
            message = control.lang(37004)
        except Exception:
            message = control.lang(37005)
                
    elif os.path.exists(os.path.join(control.homePath, 'temp', 'cookies.dat')):
        logger.logInfo('cookies file FOUND (temp)')
        try:
            os.unlink(os.path.join(control.homePath, 'temp', 'cookies.dat'))
            message = control.lang(37004)
        except Exception:
            message = control.lang(37005)

    elif os.path.exists(os.path.join(control.dataPath, config.cookieFileName)):
        logger.logInfo('cookies file FOUND (profile)')
        try:
            if (isinstance(cookieJar, cookielib.LWPCookieJar) and os.path.exists(cookieJar.filename)):
                cookieJar.clear()
                cookieJar.save(ignore_discard=True, ignore_expires=True)
            else:
                os.unlink(os.path.join(control.dataPath, config.cookieFileName))
            message = control.lang(37004)
        except Exception:
            message = control.lang(37005)

    else:
        message = control.lang(37006)
    
    # Reset opener after cleaning cookies
    reset_opener()
        
    if notify:
        control.showNotification(message)

def checkIfError(html):
    """Check if HTML contains error"""
    error = False
    message = ''
    if html == '' or html is None:
        error = True
        message = control.lang(37029)
    else:
        t = bs(html, 'html.parser').title
        if t:
            if 'Error' in t:
                error = True
                message = t.get_text().split(' | ')[1]
    return {'error': error, 'message': message}

def removeDuplicates(list):
    """Remove duplicates from list"""
    newList = []
    uniq = {}
    for d in list:
        key = '%s_%s' % (d.get('type'), str(d.get('id')))
        if key not in uniq:
            newList.append(d)
        uniq[key] = 1
    return newList

def updateCatalogCache(loadEpisodes=False):
    """Update catalog cache"""
    logger.logInfo('called function')
    from .catalog import refreshCatalogShows

    control.showNotification(control.lang(37015), control.lang(30005))
    cache.longCache.cacheClean(True)
    cache.shortCache.cacheClean(True)

    control.showNotification(control.lang(37014), control.lang(30005))
    return refreshCatalogShows(loadEpisodes)

def reloadCatalogCache():
    """Reload catalog cache"""
    logger.logInfo('called function')
    updateEpisodes = False
    if (control.confirm('%s\n%s' % (control.lang(37035), control.lang(37036)), title=control.lang(30402))):
        updateEpisodes = True
    if updateCatalogCache(updateEpisodes) is True:
        control.showNotification(control.lang(37003), control.lang(30010))
    else:
        control.showNotification(control.lang(37027), control.lang(30004))

def resetCatalogCache():
    """Reset catalog cache"""
    logger.logInfo('called function')
    from .catalog import episodeDB, showDB
    from resources.lib.libraries import tools
    tools.importUserData()  # My List and counters are kept apart from the databases dropped here
    episodeDB.drop()
    showDB.drop()
    control.showNotification(control.lang(37039), control.lang(30010))
    reloadCatalogCache()
