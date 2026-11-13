# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
    
    Refactored into modular structure - this file maintains backwards compatibility
'''

# Import everything from the new modular structure
from resources.lib.sources.tfctv.api import (
    cookieJar, get_opener, reset_opener,
    callServiceApi, callJsonApi, getFromCookieByName, getCookieContent
)

from resources.lib.sources.tfctv.auth import (
    login, logout, isLoggedIn, loginToWebsite, loginWithFacebook,
    checkAccountChange, enterCredentials, checkFacebookToken, Logged
)

from resources.lib.sources.tfctv.user import (
    getUserData, getUserInfo, getUserName, getUserSubscription, getUserId,
    getUserTransactions, getUserDevices, refreshUserData,
    refreshUserSubscriptions, refreshUserInfo, refreshUserContext,
    getAccount, setAccount, getFingerprintID, getDeviceIP,
    getCountryCode, getGeoLocation, generateNewFingerprintID
)

from resources.lib.sources.tfctv.catalog import (
    getShow, getShows, getShowWithEpisodes, getEpisode,
    getEpisodesPerPage, getCategories, getWebsiteHomeSections,
    getWebsiteSectionContent, getHomeCatalog, getSettings, loadSettings,
    getItemData, getSiteItems, checkCatalogUpdates,
    getMyList, getMylistShowLastEpisodes, addToMyList, removeFromMyList,
    enterSearch, episodeDB, showDB, castDB
)

from resources.lib.sources.tfctv.playback import (
    playEpisode, getMediaInfo, getMediaInfoFromWebsite,
    getEpisodeBandwidthList, getEpisodeFromShow, getEpisodeFromLiveStream
)

from resources.lib.sources.tfctv.library import (
    addToLibrary, removeFromLibrary, showExportedShowsToLibrary,
    checkLibraryUpdates, generateShowNFO, generateEpisodeNFO, libraryDB
)

from resources.lib.sources.tfctv.utils import (
    unicodetoascii, checkProxy, cleanCookies,
    updateCatalogCache, reloadCatalogCache, resetCatalogCache,
    removeDuplicates, checkIfError
)

# Legacy imports for compatibility
from resources.lib.libraries import control

logger = control.logger
bs = control.soup
thisPlugin = control.thisPlugin

# Export all public functions for backwards compatibility
__all__ = [
    # Core objects
    'episodeDB', 'showDB', 'libraryDB', 'castDB',
    'cookieJar', 'get_opener', 'reset_opener', 'logger', 'bs', 'Logged',
    
    # Auth functions
    'login', 'logout', 'isLoggedIn', 'loginToWebsite', 'loginWithFacebook',
    'checkAccountChange', 'enterCredentials', 'checkFacebookToken',
    
    # Catalog functions
    'getShow', 'getShows', 'getShowWithEpisodes', 'getEpisode',
    'getEpisodesPerPage', 'getCategories', 'getWebsiteHomeSections',
    'getWebsiteSectionContent', 'getHomeCatalog', 'getSettings', 'loadSettings',
    'getItemData', 'getSiteItems', 'checkCatalogUpdates',
    
    # Playback functions
    'playEpisode', 'getMediaInfo', 'getMediaInfoFromWebsite',
    'getEpisodeBandwidthList', 'getEpisodeFromShow', 'getEpisodeFromLiveStream',
    
    # Library functions
    'addToLibrary', 'removeFromLibrary', 'showExportedShowsToLibrary',
    'checkLibraryUpdates', 'generateShowNFO', 'generateEpisodeNFO',
    
    # User functions
    'getUserData', 'getUserInfo', 'getUserName', 'getUserSubscription', 'getUserId',
    'getUserTransactions', 'getUserDevices', 'refreshUserData',
    'refreshUserSubscriptions', 'refreshUserInfo', 'refreshUserContext',
    'getAccount', 'setAccount', 'getFingerprintID', 'getDeviceIP',
    'getCountryCode', 'getGeoLocation', 'generateNewFingerprintID',
    
    # MyList functions
    'getMyList', 'getMylistShowLastEpisodes', 'addToMyList', 'removeFromMyList',
    
    # Search functions
    'enterSearch',
    
    # Utility functions
    'unicodetoascii', 'checkProxy', 'cleanCookies',
    'updateCatalogCache', 'reloadCatalogCache', 'resetCatalogCache',
    'removeDuplicates', 'checkIfError',
    
    # Cookie functions
    'getFromCookieByName', 'getCookieContent',
    
    # API functions
    'callServiceApi', 'callJsonApi'
]
