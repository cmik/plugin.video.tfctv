# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2016 cmik

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import hashlib
import json
import time
from resources import config
from resources.lib.libraries import control

logger = control.logger

shortCache = None
sCacheFunction = None
longCache = None
lCacheFunction = None
 # execution cache
execCache = {}

# Cache
cacheActive = True if control.setting('cacheActive') == 'true' else False
logger.logInfo('cacheActive : %s' % (cacheActive))
if cacheActive: 
    logger.logInfo('Storage cache enabled')
    try:
       import StorageServer
    except:
       from resources.lib.dummy import storageserverdummy as StorageServer
    # Short TTL cache
    shortCache = StorageServer.StorageServer(config.shortCache['name'], config.shortCache['ttl']) 
    sCacheFunction = shortCache.cacheFunction
    # Long TTL cache
    longCache = StorageServer.StorageServer(config.longCache['name'], config.longCache['ttl']) 
    lCacheFunction = longCache.cacheFunction
else:
    logger.logInfo('Execution cache enabled')
    from resources.lib.libraries import executioncache
    # Execution cache
    shortCache = executioncache.ExecutionCache(execCache) 
    sCacheFunction = shortCache.cacheFunction
    longCache = shortCache
    lCacheFunction = longCache.cacheFunction

STAMP = ':at'  # companion key: when a value was stored


def getCached(cacheType, key, func, refresh=False, ttl=None):
    """The value kept under `key`, else `func()` (kept). With `ttl` (seconds) a value older than that is made again."""
    logger.logDebug('called function with parameter (%s, %s)' % (key, refresh))
    cached = None
    if refresh is True:
        forget(cacheType, key)
    if ttl is not None and cacheType.get(key) != '':
        try:
            expired = time.time() - float(cacheType.get(key + STAMP)) > ttl
        except (TypeError, ValueError):
            expired = True  # kept without a date: unknown age
        if expired:
            forget(cacheType, key)
    if cacheType.get(key) == '':
        cached = func()
        cacheType.set(key, cached)
        if ttl is not None:
            cacheType.set(key + STAMP, repr(time.time()))
    else:
        cached = cacheType.get(key)
    return logger.logDebug(cached)


def forget(cacheType, key):
    cacheType.delete(key)
    cacheType.delete(key + STAMP)


def getCachedJson(cacheType, key, func, refresh=False, ttl=None):
    """Same as getCached for what `func` gives as JSON-able data; an empty answer (a failed call) is not kept"""
    raw = getCached(cacheType, key, lambda: json.dumps(func()), refresh, ttl)
    value = json.loads(raw) if raw else None
    if not value:
        forget(cacheType, key)
    return value


def generateHashKey(string):
    return hashlib.md5(string.encode()).hexdigest()