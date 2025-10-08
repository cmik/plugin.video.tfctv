# -*- coding: utf-8 -*-

"""
TFC.tv API Module
"""

from resources.lib.libraries.control import thisPlugin
from .auth import *
from .api import *
from .catalog import *
from .playback import *
from .library import *
from .user import *
from .utils import *

__all__ = [
    # Auth
    'login', 'logout', 'isLoggedIn', 'loginToWebsite', 'loginWithFacebook',
    'checkAccountChange', 'enterCredentials', 'checkFacebookToken',
    
    # Catalog
    'getShow', 'getShows', 'getShowWithEpisodes', 'getEpisode',
    'getEpisodesPerPage', 'getCategories', 'getWebsiteHomeSections',
    'getWebsiteSectionContent', 'getHomeCatalog', 'getSettings', 'loadSettings',
    'getItemData', 'getSiteItems', 'checkCatalogUpdates',
    
    # Playback
    'playEpisode', 'getMediaInfo', 'getMediaInfoFromWebsite',
    'getEpisodeBandwidthList', 'getEpisodeFromShow', 'getEpisodeFromLiveStream',
    
    # Library
    'addToLibrary', 'removeFromLibrary', 'showExportedShowsToLibrary',
    'checkLibraryUpdates', 'generateShowNFO', 'generateEpisodeNFO',
    
    # User
    'getUserData', 'getUserInfo', 'getUserName', 'getUserSubscription', 'getUserId',
    'getUserTransactions', 'getUserDevices', 'refreshUserData',
    'refreshUserSubscriptions', 'refreshUserInfo', 'refreshUserContext',
    'getAccount', 'setAccount', 'getFingerprintID', 'getDeviceIP',
    'getCountryCode', 'getGeoLocation', 'generateNewFingerprintID',
    
    # MyList
    'getMyList', 'getMylistShowLastEpisodes', 'addToMyList', 'removeFromMyList',
    
    # Search
    'enterSearch',
    
    # Utils
    'unicodetoascii', 'checkProxy', 'cleanCookies',
    'updateCatalogCache', 'reloadCatalogCache', 'resetCatalogCache',
    'removeDuplicates', 'checkIfError',
    
    # Cookies
    'getFromCookieByName', 'getCookieContent',
    
    # DB Access
    'episodeDB', 'showDB', 'libraryDB', 'castDB',
    
    # Global
    'thisPlugin'
]
