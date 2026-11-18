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

import re
import xbmc
from inspect import stack as getStack
from os import path

LOGDEBUG = 7
LOGINFO = 6
LOGNOTICE = 5
LOGWARNING = 4
LOGERROR = 3
LOGSEVERE = 2
LOGFATAL = 1
LOGNONE = 0

# Default log level
defaultLogLevel = LOGNONE
plugin = ''
status = False
logLevel = defaultLogLevel

def enable(bool):
    global status
    status = True if bool else False
    
def setLevel(level):
    if (level in (LOGNONE, LOGDEBUG, LOGINFO, LOGNOTICE, LOGWARNING, LOGERROR, LOGSEVERE, LOGFATAL)):
        global logLevel
        logLevel = level
        return True
    return False
    
# What must not reach the Kodi log (users share it): tokens, cookies, passwords
_SECRETS = [
    (re.compile(r'(Bearer\s+)[A-Za-z0-9._~+/=-]+'), r'\1***'),
    (re.compile(r'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]*)?'), '***'),
    (re.compile(r'(Set-Cookie3?:\s*[^=\s]+=)"?[^";\n]*"?'), r'\1***'),
    (re.compile(r'(Cookie:\s*[^=\s]+=)[^\s(]*'), r'\1***'),
    (re.compile(r'''(["']?(?:password|passwd|pwd|access_token|refresh_token|id_token|client_secret|iWantUserAuthentication|FBAccessToken)["']?\s*[:=]\s*)(["']?)[^"'&,}\s]*''', re.IGNORECASE), r'\1\2***'),
]

def redact(mixed):
    """The text to log with the tokens, cookies and passwords it holds hidden"""
    text = mixed if isinstance(mixed, str) else str(mixed)
    for pattern, replacement in _SECRETS:
        text = pattern.sub(replacement, text)
    return text

def log(mixed, level=defaultLogLevel, subFonc=False):
    stackSubLevel = 1 if not subFonc else 2
    if status and logLevel >= level:
        xbmcLogLevel = xbmc.LOGINFO
        if level == LOGWARNING:     
            xbmcLogLevel = xbmc.LOGWARNING        
        if level == LOGERROR:     
            xbmcLogLevel = xbmc.LOGERROR
        
        stack = getStack()
        text = redact(mixed)
        try:
            xbmc.log(u"[%s] %s :%s @%s : '%s'" % (plugin, path.basename(stack[stackSubLevel][1]), stack[stackSubLevel][2], stack[stackSubLevel][3], text), xbmcLogLevel)
        except:
            xbmc.log(u"[%s] %s : '%s'" % (plugin, path.basename(stack[stackSubLevel][1]), stack[stackSubLevel][2], stack[stackSubLevel][3], repr(text)), xbmcLogLevel)
    return mixed
            
def logDebug(mixed):
    log(mixed, LOGDEBUG, True)
    return mixed

def logInfo(mixed):
    log(mixed, LOGINFO, True)
    return mixed

def logNotice(mixed):
    log(mixed, LOGNOTICE, True)
    return mixed

def logWarning(mixed):
    log(mixed, LOGWARNING, True)
    return mixed
    
def logError(mixed):
    log(mixed, LOGERROR, True)
    return mixed
    
def logSevere(mixed):
    log(mixed, LOGSEVERE, True)
    return mixed
    
def logFatal(mixed):
    log(mixed, LOGFATAL, True)
    return mixed
    
    
