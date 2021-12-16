# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''


#---------------------- CONFIG ----------------------------------------
# Cookies
cookieFileName = 'tfctv.cookie'

# Cache
settingsRefreshRate = 10 * 60                       # catalog updates every 10 minutes
shortCache = {'name' : 'tfctv', 'ttl': 1}
longCache = {'name' : 'tfctv_db', 'ttl': 24*7}
urlCachePrefix = 'urlcache_'

# HOSTS / URI
webserviceUrl = 'https://www.iwanttfc.com'
websiteUrl = 'https://www.iwanttfc.com'
websiteSecuredUrl = 'https://www.iwanttfc.com'
websiteCDNUrl = 'https://img.tfc.tv'
Facebook = {
    'login' : 'https://graph.facebook.com/v12.0/device/login',
    'status' : 'https://graph.facebook.com/v12.0/device/login_status',
    'info' : 'https://graph.facebook.com/v12.0/me'
}
uri = {
    'base' : '/',
    'home' : '/#!/',
    'loginStatus' : '/api/1.0/user/login',
    'profile' : 'https://purchase.iwanttfc.com/proxy',
    'licence' : '/api/1.0/license?itemID=%s',
    'livestream' : '/api/1.0/stream?streamID=%s',
    'devices' : '/api/1.0/user/devices',
    'deleteDevice' : '/api/1.0/user/devices?action=delete&deviceID=%s',
    'profileDetails' : '/profile/details',
    'logout' : "/logout",
    'apiKey' : '/sso/api/apikey?ocpKey=%s&siteUrl=https://tfc.tv',
    'ssoLogin' : '/sso/api/sso.login?include=profile,loginIDs,data,password',
    'login' : '/api/1.0/user/auth',
    'socialLogin' : '/api/1.0/user/auth',
    'callback' : '/callback',
    'authSSO' : '/sso/authenticate',
    'checkSSO' : '/sso/checksession',
    'signin' : '/signin',
    'welcome' : '/welcome',
    'checksession' : '/checksession',
    'webSdkApi' : '/gs/webSdk/Api.aspx',
    'webSdkBootstrap' : '/accounts.webSdkBootstrap',
    'gigyaSSO' : '/gs/sso.htm',
    'gigyaJS' : '/js/gigya.js',
    'gigyaNotifyLogin' : '/socialize.notifyLogin',
    'gigyaAccountInfo' : '/accounts.getAccountInfo',
    'gigyaGmidTicket' : '/socialize.getGmidTicket',
    'authCallback' : '/connect/authorize/callback',
    'episodeDetails' : '/episode/details/%s',
    'mediaFetch' : '/media/fetch',
    'myList' : '/user/mylist',
    'categoryList' : '/category/list/%s',
    'showDetails' : '/show/details/%s',
    'showEpisodesList' : '/prod-feed/eplist/o/feed-%s.json?v=%s',
    'episodePagination' : '/modulebuilder/getepisodes/%s/show/%s',
    'addToList' : '/method/addtolistcdb',
    'removeFromList' : '/method/deletefromlistcdb',
}

# User-agent
userAgents = { 
    webserviceUrl : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
    websiteUrl : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
    'default' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36'
    }

# MODES
CHECKFORUPDATES = 1
SUBCATEGORYSHOWS = 2
SHOWEPISODES = 3
PLAY = 4
CHOOSEBANDWIDTH = 5
CATEGORIES = 10
SECTIONCONTENT = 11
MYACCOUNT = 12
MYINFO = 13
MYSUBSCRIPTIONS = 14
MYTRANSACTIONS = 15
MYDEVICES = 16
INFODEVICE = 17
LOGOUT = 18
MYLISTSHOWLASTEPISODES = 19
MYLIST = 20
LISTCATEGORY = 21
ADDTOLIST = 22
REMOVEFROMLIST = 23
ADDTOLIBRARY = 24
REMOVEFROMLIBRARY = 25
CHECKLIBRARYUPDATES = 26
EXPORTEDSHOWS = 27
SEARCHMENU = 30
EXECUTESEARCH = 31
TOOLS = 50
RELOADCATALOG = 51
CLEANCOOKIES = 52
OPENSETTINGS = 53
ENTERCREDENTIALS = 54
PERSONALIZESETTINGS = 55
OPTIMIZELIBRARY = 56
RESETCATALOG = 57
IMPORTSHOWDB = 58
IMPORTEPISODEDB = 59
IMPORTALLDB = 60
LOGINWITHTFC = 61
LOGINWITHFB = 62
FIRSTINSTALL = 98
ENDSETUP = 99


