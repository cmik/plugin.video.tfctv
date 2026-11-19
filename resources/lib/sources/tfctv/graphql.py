# -*- coding: utf-8 -*-

"""
Calls of the website GraphQL API (no database access)
"""


from resources import config
from resources.lib.libraries import control
from . import queries
from .api import callGraphQLApi
from .user import getCountryCode, getServiceIds

logger = control.logger

def searchCatalog(query):
    """Search catalog"""
    logger.logInfo('called function')
    response = callGraphQLApi(
        queries.SEARCH,
        {
            'query': query,
            'skus': getServiceIds(),
            'apiCode':'GSE'
        },
        useCache=False
    )
    return response


def getWatchlist(headers):
    """The watchlist of the user on the website (needs the Authorization header): the `watchlist` part of the
    answer ({} when it can't be read)"""
    logger.logInfo('called function')
    response = callGraphQLApi(
        queries.WATCHLIST,
        {'skus': getServiceIds()},
        headers,
        useCache=False
    )
    return (response or {}).get('watchlist') or {}

def getAppLaunchDetails():
    """Get app launch details from website"""
    logger.logInfo('called function')
    data = callGraphQLApi(
        queries.APP_LAUNCH_DETAILS,
        {},
        [
            ('Referer', config.websiteSecuredUrl+'/'),
            ('Origin', config.websiteSecuredUrl),
            ('x-device-platform', 'web'),
            ('X-Device-SubPlatform', 'firefox'),
            ('X-IW-UserAgent', 'Name=iWant; Version=1.0.0; Platform=Web; OSVersion=14.0.0 Model=Chrome; BuildType=debug Environment=development'),
            ('x-country-code', getCountryCode()),
            ('Sec-GPC', '1'),
            ('Sec-Fetch-Dest', 'empty'),
            ('Sec-Fetch-Mode', 'cors'),
            ('Sec-Fetch-Site', 'same-site'),
            ('Priority', 'u=4'),
            ('TE', 'trailers')
        ],
        useCache=False
    )
    if data and 'appLaunchDetails' in data:
        logger.logDebug(data['appLaunchDetails'])
        return data['appLaunchDetails']
    return {}

def getCollection(id):
    """Get collection"""
    logger.logInfo('called function with param (%s)' % id)
    response = callGraphQLApi(
        queries.COLLECTION,
        variables={
            'collectionId': id,
            'skus': getServiceIds()
        },
        useCache=False
    )
    if response and 'collection' in response:
        return response['collection']
    return {}

def getTVShowEpisodes(id, page=1, itemsPerPage=500, year=None, month=None, seasonId=None):
    """Get TV show details"""
    logger.logInfo('called function with param (%s)' % id)
    response = callGraphQLApi(
        queries.TV_SHOW_EPISODES,
        variables={
            'tvShowEpisodesId': id,
            'filters':{
                'year': year,
                'month': month,
                'seasonId': seasonId,
                'pageNumber': page,
                'pageSize': itemsPerPage
            },
            'skus': getServiceIds()
        },
        useCache=False
    )
    # the API answers with a null tvShowEpisodes (and an error) when the filters match nothing
    return (response.get('tvShowEpisodes') if response else None) or {}

def getAsset(id):
    """Get asset details"""
    logger.logInfo('called function with param (%s)' % id)
    response = callGraphQLApi(
        queries.ASSET,
        variables={
            'assetId': id,
            'skus': getServiceIds()
        },
        useCache=False
    )

    return response.get('asset', {}) if response else {}
