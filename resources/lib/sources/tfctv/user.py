# -*- coding: utf-8 -*-

"""
User data and account management
"""

import json
import datetime
import hashlib
from resources import config
from resources.lib.libraries import control
from .api import callJsonApi, getCookieContent

logger = control.logger

def getUserData():
    """Get user data from settings"""
    logger.logInfo('called function')
    userData = {}
    if control.setting('userData') and control.setting('userData') != '':
        userData = json.loads(control.setting('userData') if control.setting('userData') else '{}')
    return userData

def getUserSubscriptions():
    """Get user subscriptions from settings"""
    logger.logInfo('called function')
    subscriptions = {}
    if control.setting('userSubscriptions') and control.setting('userSubscriptions') != '':
        subscriptions = json.loads(control.setting('userSubscriptions') if control.setting('userSubscriptions') else '{}')
    if 'subscriptions' in subscriptions:
        return subscriptions
    return {}

def getUserId():
    """Get user ID"""
    logger.logInfo('called function')
    return getUserData().get('id', '')

def getUserName(html=False):
    """Get user name"""
    logger.logInfo('called function')
    contact = getUserData().get('contact', {})
    return '%s %s' % (contact.get('firstName', ''), contact.get('lastName', ''))

def refreshUserData():
    """Refresh user data from API"""
    logger.logInfo('called function')
    userData = callJsonApi(
        config.uri.get('getUserData'),
        headers=[
            ('Authorization', 'Bearer %s' % control.setting('iWantUserAuthentication')),
            ('Referer', config.websiteSecuredUrl+'/'),
            ('Origin', config.websiteSecuredUrl),
            ('x-device-platform', 'web'),
            ('X-Device-SubPlatform', 'browser'),
            ('X-IW-UserAgent', 'Name=iWant; Version=1.0.0; Platform=Web; OSVersion=14.0.0 Model=Chrome; BuildType=debug Environment=development'),
            ('Sec-GPC', '1'),
            ('Connection', 'keep-alive'),
            ('Sec-Fetch-Dest', 'empty'),
            ('Sec-Fetch-Mode', 'cors'),
            ('Sec-Fetch-Site', 'same-site'),
            ('TE', 'trailers')
        ],
        useCache=False
    )
    if userData and userData.get('statusCode', '') == '1' and userData.get('statusMessage', '') == 'OK' and 'data' in userData and 'user' in userData.get('data', {}):
        control.setSetting('userData', json.dumps(userData.get('data', {}).get('user', {})))
        control.setSetting('lastUserDataRefresh', str(datetime.datetime.now().timestamp()))
        return True
    else:
        control.setSetting('userData', '')
        from .auth import logout
        logout()
    return False

def refreshUserSubscriptions():
    """Refresh user subscriptions"""
    logger.logInfo('called function')
    subscriptions = callJsonApi(
        config.uri.get('getSubscriptions'),
        params={
            'userId': getUserId(),
            'includeTvod': False,
            'includeAllActive': False
        },
        headers=[
            ('Authorization', 'Bearer %s' % control.setting('iWantUserAuthentication')),
            ('Referer', config.websiteSecuredUrl+'/'),
            ('Origin', config.websiteSecuredUrl),
            ('x-device-platform', 'web'),
            ('X-Device-SubPlatform', 'browser'),
            ('X-IW-UserAgent', 'Name=iWant; Version=1.0.0; Platform=Web; OSVersion=14.0.0 Model=Chrome; BuildType=debug Environment=development'),
            ('Sec-GPC', '1'),
            ('Connection', 'keep-alive'),
            ('Sec-Fetch-Dest', 'empty'),
            ('Sec-Fetch-Mode', 'cors'),
            ('Sec-Fetch-Site', 'same-site'),
            ('TE', 'trailers')
        ],                        
        useCache=False
    )
    logger.logInfo(subscriptions)
    if subscriptions and 'statusCode' in subscriptions and subscriptions['statusCode'] == '1' and 'data' in subscriptions:
        control.setSetting('userSubscriptions', json.dumps(subscriptions.get('data', {})))
        return True
    else:
        control.setSetting('userSubscriptions', '')
        from .auth import logout
        logout()
    return False

def getServiceIds():
    """Get service IDs"""
    logger.logInfo('called function')
    subscriptions = getUserSubscriptions().get('subscriptions', {})
    return [x.get('serviceId', '') for x in subscriptions] if len(subscriptions) > 0 else []

def refreshUserInfo():
    """Refresh all user info"""
    logger.logInfo('called function')
    if refreshUserData():
        return refreshUserSubscriptions()
    return False

def refreshUserContext():
    """Refresh user context"""
    logger.logInfo('called function')
    # refreshWatchHistory()
    # refreshWatchlist()
    # refreshContinueWatching()
    return True

def getUserInfo():
    """Get user profile info"""
    logger.logInfo('called function')
    url = config.uri.get('profile')
    html = callJsonApi(
        url,
        params={'data': control.setting('iWantUserAuthentication')},
        headers=[
            ('Referer', config.websiteSecuredUrl+'/'),
            ('Origin', config.websiteSecuredUrl),
            ('Cache-Control', 'no-cache'),
            ('Pragma', 'no-cache'),
            ('Sec-Fetch-Dest', 'script'),
            ('Sec-Fetch-Mode', 'no-cors'),
            ('Sec-Fetch-Site', 'cross-site')
            ],
        base_url='',
        useCache=False)
    
    # Retrieve info from website
    bs = control.soup
    profileHeader = bs(html, 'html.parser').find_all('div', attrs={'class': 'profile_header'})
    name = profileHeader.find('div', attrs={'class': 'name'}).get_text()
    state = profileHeader.find('div', attrs={'class': 'name'}).get_text()
    memberSince = profileHeader.find('div', attrs={'class': 'date'}).get_text()
    
    # Retrieve info from account JSON string
    user = getAccount().get('profile')

    return {
        'name': name,
        'firstName': user.get('firstName', ''),
        'lastName': user.get('lastName', ''),
        'email': user.get('email', ''),
        'state': state,
        'country': user.get('country', ''),
        'memberSince': memberSince.replace('MEMBER SINCE ', '')
    }

def getUserSubscription():
    """Get user subscriptions"""
    logger.logInfo('called function')
    subscriptions = {}
    if control.setting('userSubscriptions'):
        subscriptions = json.loads(control.setting('userSubscriptions'))
    if 'subscriptions' in subscriptions:
        return subscriptions
    return {}

def getUserTransactions():
    """Get user transactions"""
    logger.logInfo('called function')
    import re
    from .api import callServiceApi
    
    see_more = re.compile('See more')

    data = []
    url = config.uri.get('profile')
    html = callServiceApi(url, useCache=False)
    
    bs = control.soup
    transactions = bs(html, 'html.parser').select('div[id=transactions] tbody > tr')
    headers = bs(html, 'html.parser').select('div[id=transactions] thead th')
    
    header = []
    for h in headers:
        header.append(h.get_text())
    
    for transaction in transactions:
        t = ''
        i = 0
        
        columns = transaction.select('td:not(.loader)')
        for col in columns:
            value = '-'
            c = col.get_text()
            if not see_more.search(c) and len(c) > 0:
                value = c
            t += "%s: %s\n" % (header[i], value)
            i += 1
        data.append(t)
                
    return data

def getUserDevices():
    """Get registered devices"""
    logger.logInfo('called function')
    data = callJsonApi(
        config.uri.get('devices'),
        headers=[
            ('Cookie', 'UserAuthentication='+control.setting('iWantUserAuthentication')),
            ('UserAuthentication', control.setting('iWantUserAuthentication')),
            ('Referer', config.websiteSecuredUrl+'/'),
            ('Origin', config.websiteSecuredUrl),
            ('Pragma', 'no-cache'),
            ('Sec-Fetch-Dest', 'empty'),
            ('Sec-Fetch-Mode', 'cors'),
            ('Sec-Fetch-Site', 'same-orig')
            ],
        useCache=False
        )
    if len(data) == 0:
        control.showNotification(control.lang(37055))
    return data

def getAccount():
    """Get account data"""
    logger.logInfo('called function')
    account = {}
    if control.setting('accountJSON') and control.setting('accountJSON') != '':
        account = json.loads(control.setting('accountJSON') if control.setting('accountJSON') else '{}')
    return account

def setAccount(id, name='', firstName='', lastName='', email=''):
    """Set account data"""
    logger.logInfo('called function')
    account = {
        'name': name,
        'firstName': firstName,
        'lastName': lastName,
        'email': email,
        'id': id
    }
    control.setSetting('accountJSON', json.dumps(account))
    return account

def getFingerprintID():
    """Get or generate fingerprint ID"""
    logger.logInfo('called function')
    if control.setting('fingerprintID') == '':
        generateNewFingerprintID()
    return control.setting('fingerprintID')

def generateNewFingerprintID():
    """Generate new fingerprint ID"""
    logger.logInfo('called function')
    from random import randint
    control.setSetting('previousFingerprintID', control.setting('fingerprintID'))
    control.setSetting('fingerprintID', hashlib.md5((control.setting('emailAddress')+str(randint(0, 1000000))).encode()).hexdigest())
    if control.setting('generateNewFingerprintID') == 'true':
        control.setSetting('generateNewFingerprintID', 'false')
    return True

def getDeviceIP():
    """Get device IP address"""
    logger.logInfo('called function')
    ipAddress = ''
    if control.setting('geoLocation') and control.setting('geoLocation') != '':
        ipAddress = json.loads(control.setting('geoLocation')).get('ipAddress', '')
    if ipAddress == '':
        ipAddress = getGeoLocation().get('ipAddress', '')
    logger.logInfo('Device IP address is %s' % ipAddress)
    return ipAddress

def getCountryCode():
    """Get country code"""
    countryCode = json.loads(control.setting('geoLocation') if control.setting('geoLocation') else '{}').get('geoLocation', {}).get('countryCode', '')
    if countryCode == '':
        countryCode = getGeoLocation().get('geoLocation', {}).get('countryCode', '')
    logger.logInfo('Device country code is %s' % countryCode)
    return countryCode

def getGeoLocation():
    """Get geo location"""
    location = callJsonApi(config.geoLocationUrl, base_url='', useCache=False)
    if 'status' in location and location.get('status') == 200 and 'data' in location and len(location.get('data')) > 0:
        data = location.get('data')[0]
        control.setSetting('geoLocation', json.dumps(data))
        return data
    return {}
