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
# how long what the website answers is kept (seconds), by kind: what changes seldom is kept longer. The search and the
# data of the user (watchlist, playback, login) are never kept.
cacheTTLs = {
    'menu': 6 * 3600,       # the collections of the website (appLaunchDetails)
    'rails': 3600,          # the rails of a collection
    'live': 5 * 60,         # the live channels and events: an event can start or end any time
    'episodes': 6 * 3600,   # when the episodes of a show of My List are read again from the website (Last Episodes)
    'picks': 30 * 60,       # Top Picks Near You!
}

# HOSTS / URI
webserviceUrl = 'https://api.iwanttfc.com'
websiteUrl = 'https://www.iwanttfc.com'
websiteSecuredUrl = 'https://www.iwanttfc.com'
websiteCDNUrl = 'https://img.tfc.tv'
geoLocationUrl = 'https://pql-geo.iwanttfc.com/prod/location'
Facebook = {
    'login' : 'https://graph.facebook.com/v12.0/device/login',
    'status' : 'https://graph.facebook.com/v12.0/device/login_status',
    'info' : 'https://graph.facebook.com/v12.0/me'
}
uri = {
    'login' : '/identity/api/iam/oauth?api-version=1.2',
    'getUserData' : '/identity/api/iam/get-contact?api-version=1.2',
    'getSubscriptions' : '/subs/api/subscription/get-active-entitlements',
    'graphql' : '/consumer/graphql',
    'watchlist' : '/watchlist/watchlist',
    'video' : '/entitlement/playback/start/%s',

    'base' : '/',
    'home' : '/#!/',
    'loginStatus' : '/api/1.0/user/login',
    'profile' : 'https://purchase.iwanttfc.com/proxy',
    'licence' : '/api/1.0/license?itemID=%s',
    'profileDetails' : '/profile/details',
    'logout' : "/logout",
    'apiKey' : '/sso/api/apikey?ocpKey=%s&siteUrl=https://tfc.tv',
    'ssoLogin' : '/sso/api/sso.login?include=profile,loginIDs,data,password',
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
    webserviceUrl : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:143.0) Gecko/20100101 Firefox/143.0',
    websiteUrl : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:143.0) Gecko/20100101 Firefox/143.0',
    'default' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:143.0) Gecko/20100101 Firefox/143.0'
    }

# MODES
CHECKFORUPDATES = 1
SUBCATEGORYSHOWS = 2
SHOWEPISODES = 3
PLAY = 4
PLAYDISABLED = 5
CATEGORIES = 10
COLLECTIONCONTENT = 12
SECTIONCONTENT = 13
SEASONS = 11
MYACCOUNT = 14
MYINFO = 15
MYSUBSCRIPTIONS = 16
MYTRANSACTIONS = 17
LOGOUT = 20
MYLISTSHOWLASTEPISODES = 21
MYLIST = 22
LISTCATEGORY = 23
ADDTOLIST = 24
REMOVEFROMLIST = 25
ADDTOLIBRARY = 26
REMOVEFROMLIBRARY = 27
CHECKLIBRARYUPDATES = 28
EXPORTEDSHOWS = 29
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
IMPORTALLDB = 60
LOGINWITHTFC = 61
LOGINWITHFB = 62
CATCHUPCATALOG = 63
VIEWHISTORY = 64
CLEARHISTORY = 65
REMOVEFROMHISTORY = 66
CONTINUEWATCHING = 67
TRAKTCONNECT = 68
TRAKTDISCONNECT = 69
REFRESHGEO = 70
TRAKTLINK = 71
TOPPICKS = 72
SYNCWATCHLIST = 73
LIVETV = 74
FIRSTINSTALL = 98
ENDSETUP = 99

# Trakt: client id of the production application of the add-on (public client: it has no secret, and the account of each
# user is identified by the token they get when they connect). The settings can replace it by the user's own.
TRAKT_CLIENT_ID = 'lV5NGnVpsqx9i54jlPGXGZjZ-quHQ64dUKjYtdaVgio'
