# -*- coding: utf-8 -*-

"""
Authentication module for TFC.tv
"""

import os
import time
import hashlib
import datetime
from resources import config
from resources.lib.libraries import control
from .api import callServiceApi, callJsonApi, cookieJar, reset_opener, getCookieContent
from .user import getUserData, refreshUserData, refreshUserSubscriptions, getFingerprintID, getDeviceIP, getAccount, setAccount

logger = control.logger
Logged = False

def isLoggedIn():
    """Check if user is logged in"""
    logger.logInfo('called function')
    global Logged
    userData = getUserData()
    now = datetime.datetime.now()
    lastRefresh = datetime.datetime.fromtimestamp(float(control.setting('lastUserDataRefresh'))) if control.setting('lastUserDataRefresh') != '' else None
    logger.logDebug('Last user data refresh: %s' % str(lastRefresh))
    logger.logDebug('Seconds since last refresh: %s' % (now - lastRefresh).total_seconds() if lastRefresh is not None else 'N/A')
    if control.setting('iWantUserAuthentication') and control.setting('iWantUserAuthentication') != '':
        Logged = refreshUserData() if (not Logged or userData == {} or lastRefresh is None or (now - lastRefresh).total_seconds() > 86400) else False
    return Logged

def login(quiet=False, login=False, password=False):
    """Login to TFC.tv"""
    logger.logInfo('called function')
    signedIntoWebsite = loginToWebsite(quiet, login, password)
    if signedIntoWebsite:
        refreshUserSubscriptions()
    return signedIntoWebsite

def loginToWebsite(quiet=False, login=False, password=False):
    """Login to TFC.tv website"""
    logger.logInfo('called function')
    logged = False

    if control.setting('loginType') == "Facebook":
        token = control.setting('FBAccessToken')
        if token is not None and token != '' and not checkFacebookToken(token):
            token = ''
            control.setSetting('FBAccessToken', '')
        logged = loginWithFacebook(quiet, token)
    else:
        if control.setting('emailAddress') != '':
            emailAddress = control.setting('emailAddress')
            password = control.setting('password')
            fingerprintId = getFingerprintID()
            ipAddress = getDeviceIP()
            params = {
                'identifier': emailAddress,
                'password': password,
                'identifierType': 'email',
                'socialLoginToken': '',
                'userAgent': config.userAgents['default'],
                'deviceName': 'MacIntel',
                'deviceType': 'desktop',
                'deviceModelNumber': '5.0 (Macintosh)',
                'fingerprintId': fingerprintId,
                'ipAddress': ipAddress,
                'webSource': config.websiteUrl+'/'
            }
            authInfos = callJsonApi(config.uri.get('login'),
                params,
                headers=[
                    ('Referer', config.websiteSecuredUrl + '/'),
                    ('Origin', config.websiteSecuredUrl),
                    ('Sec-GPC', '1'),
                    ('Connection', 'keep-alive'),
                    ('Sec-Fetch-Dest', 'empty'),
                    ('Sec-Fetch-Mode', 'cors'),
                    ('Sec-Fetch-Site', 'same-site'),
                    ('TE', 'trailer')
                ],
                useCache=False
            )
            logger.logDebug(authInfos)
            logger.logDebug('Cookies: %s' % getCookieContent())
            logger.logDebug(cookieJar)
            if authInfos and authInfos.get('statusCode', '') == '1' and authInfos.get('statusMessage', '') == 'OK':
                logger.logDebug('Login successful')
                control.setSetting('iWantRefreshToken', authInfos.get('data', {}).get('refreshToken', ''))
                control.setSetting('iWantUserAuthentication', authInfos.get('data', {}).get('accessToken', ''))
            if not isLoggedIn() and not quiet:
                logger.logError('Authentification failed')
                control.showNotification(control.lang(37024), control.lang(30006))
            else:
                logged = True
                logger.logNotice('You are now logged in')
                control.showNotification(control.lang(37009) % '', control.lang(30007))
                from .user import generateNewFingerprintID
                if control.setting('generateNewFingerprintID') == 'true':
                    generateNewFingerprintID()
        else:
            control.showNotification(control.lang(30205), control.lang(30204))
    return logged

def checkFacebookToken(accessToken=''):
    """Check Facebook token validity"""
    logger.logInfo('called function')
    info = callJsonApi(config.Facebook.get('info'), params={'fields': 'name,first_name,last_name,email', 'access_token': accessToken}, headers=[], base_url='', useCache=False)
    if 'name' in info:
        return True
    return False

def loginWithFacebook(quiet=False, accessToken=''):
    """Login with Facebook"""
    logger.logInfo('called function')
    logged = False
    token = None
    account = getAccount()

    if control.setting('FBAppID') != '' or control.setting('FBClientToken') != '':

        appIdentifier = '%s|%s' % (control.setting('FBAppID'), control.setting('FBClientToken'))
        control.showNotification(control.lang(36024), control.lang(30005))
        if accessToken == '':
            login = callJsonApi(config.Facebook.get('login'), params={'access_token': appIdentifier}, headers=[], base_url='', useCache=False)
            if 'code' in login and 'user_code' in login:
                control.alert(control.lang(37048) % login.get('verification_uri'), line1='[B]%s[/B]' % login.get('user_code'), line2=control.lang(37049), title=control.lang(36024))
                i = 1
                expired = False
                while i < 5 and token is None and not expired:
                    time.sleep(login.get('interval', 5))
                    status = callJsonApi(config.Facebook.get('status'), params={'access_token': appIdentifier, 'code': login.get('code')}, headers=[], base_url='', useCache=False)
                    if 'access_token' in status:
                        info = callJsonApi(config.Facebook.get('info'), params={'fields': 'name,first_name,last_name,email', 'access_token': status.get('access_token')}, headers=[], base_url='', useCache=False)
                        if 'name' in info:
                            account = setAccount(info.get('id', ''), info.get('name', ''), info.get('first_name', ''), info.get('last_name', ''), info.get('email', ''))
                            token = status.get('access_token')
                    elif 'error' in status and status.get('error').get('error_subcode', 0) == 1349152:
                        expired = True
                    i += 1
        else:
            token = accessToken

        if token is not None:
            params = {
                'facebookUserId': account.get('id'),
                'socialAccessToken': token
            }
            authInfos = callJsonApi(
                config.uri.get('socialLogin'),
                params=params,
                headers=[
                    ('Referer', config.websiteSecuredUrl+'/'),
                    ('Origin', config.websiteSecuredUrl),
                    ('Pragma', 'no-cache'),
                    ('Sec-Fetch-Dest', 'empty'),
                    ('Sec-Fetch-Mode', 'cors'),
                    ('Sec-Fetch-Site', 'same-orig')
                    ],
                base_url=config.websiteSecuredUrl,
                useCache=False
                )
            if authInfos.get('status') == 'OK':
                control.setSetting('iWantRefreshToken', authInfos.get('refreshToken'))
                control.setSetting('iWantUserAuthentication', authInfos.get('UserAuthentication'))
            logged = isLoggedIn()

        if not quiet:
            if logged:
                logger.logNotice('You are now logged in')
                control.setSetting('FBAccessToken', token)
                control.showNotification(control.lang(37009) % account.get('name'), control.lang(30007))
            else:
                logger.logError('Authentification failed')
                control.showNotification(control.lang(37024), control.lang(30006))
    else:
        control.showMessage(control.lang(37052), control.lang(30006))

    return logged

def logout(quiet=True):
    """Logout from TFC.tv"""
    logger.logInfo('called function')
    if not quiet and not isLoggedIn():
        control.showNotification(control.lang(37000), control.lang(30005))
    control.setSetting('FBAccessToken', '')
    control.setSetting('iWantUserAuthentication', '')
    control.setSetting('iWantRefreshToken', '')
    control.setSetting('userData', '')
    control.setSetting('accountJSON', '')
    control.setSetting('userSubscriptions', '')
    control.setSetting('userId', '')
    control.setSetting('serviceId', '')
    # cookieJar.clear()
    reset_opener()
    if not quiet and not isLoggedIn():
        control.showNotification(control.lang(37010))
        control.exit()

def checkAccountChange(forceSignIn=False):
    """Check if account credentials have changed"""
    logger.logInfo('called function')
    email = control.setting('emailAddress')
    password = control.setting('password')
    hash = hashlib.sha1((email + password).encode()).hexdigest()
    hashFile = os.path.join(control.dataPath, 'a.tmp')
    savedHash = ''
    accountChanged = False
    logged = False
    loginSuccess = False
    
    if os.path.exists(hashFile):
        if forceSignIn:
            os.unlink(hashFile)
        else:
            with open(hashFile) as f:
                savedHash = f.read()
                f.close()
    
    logger.logDebug('Current hash: %s' % hash)
    logger.logDebug('Saved hash: %s' % savedHash)
    if savedHash != hash:
        accountChanged = True
        logout()
        logged = True
    elif not isLoggedIn():
        logger.logInfo('Not logged in')
        logged = True
    
    if logged:
        from .utils import cleanCookies
        cleanCookies(False)
        loginSuccess = login()
        if loginSuccess and os.path.exists(control.dataPath):
            with open(hashFile, 'w') as f:
                f.write(hash)
                f.close()
        elif os.path.exists(hashFile):
            os.unlink(hashFile)
        
    return (accountChanged, loginSuccess)

def enterCredentials():
    """Prompt user to enter credentials"""
    logger.logInfo('called function')
    email = control.inputText(control.lang(30400), control.setting('emailAddress'))
    password = ''
    i = 1
    while i < 3 and password == '':
        password = control.inputPassword(control.lang(30401))
        i += 1
    logger.logNotice('%s - %s' % (email, password))
    control.setSetting('emailAddress', email)
    control.setSetting('password', password)
    return login(False, email, password)
