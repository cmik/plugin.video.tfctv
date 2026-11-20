# -*- coding: utf-8 -*-

"""
Website collections and rails (home sections, ids of the shows they list)
"""

import re
from resources import config
from resources.lib.libraries import cache
from resources.lib.libraries import control
from .db import showDB
from .formatters import formatToShow, formatSearchResults, LIVE_ASSETS
from .graphql import getAppLaunchDetails, getCollection
from .user import getCountryCode
from .utils import removeDuplicates

logger = control.logger

def getWebsiteCollections(refresh=False):
    """Get website collections (the menu of the website changes seldom: kept for a few hours, by country)"""
    logger.logInfo('called function')
    return cache.getCachedJson(
        cache.shortCache,
        'menu-%s' % (getCountryCode() or ''),
        lambda: getAppLaunchDetails().get('menu', {}).get('collections', []),
        refresh,
        config.cacheTTLs['menu']
    ) or []

def getCachedCollection(collectionId, refresh=False, ttl=None):
    """Get a collection (its rails), kept `ttl` seconds (an hour by default); the rails depend on the country"""
    logger.logInfo('called function with param (%s, %s)' % (collectionId, refresh))
    return cache.getCachedJson(
        cache.shortCache,
        'collection-%s-%s' % (collectionId, getCountryCode() or ''),
        lambda: getCollection(collectionId),
        refresh,
        config.cacheTTLs['rails'] if ttl is None else ttl
    ) or {}

def getCollectionContent(id):
    """Get website home sections"""
    logger.logInfo('called function with param (%s)' % id)
    data = []
    catalog = getCachedCollection(id, True)
    for section in catalog.get('rails', {}):
        sectionName = section.get('title', {})
        exceptSections = []
        if sectionName not in exceptSections:
            if section.get('assets', {}).get('totalItems', 0) > 0:
                data.append({
                    'id': section.get('id', cache.generateHashKey(sectionName)),
                    'name': sectionName
                })
    return data

SHOW_ASSET_TYPES = ('tvshow', 'movie', 'documentary')

def getCollectionShowIds(collectionId, refresh=False):
    """Get the ids of the shows/movies listed in the rails of a collection"""
    logger.logInfo('called function with param (%s, %s)' % (collectionId, refresh))
    ids = []
    for rail in getCachedCollection(collectionId, refresh).get('rails', {}):
        assets = rail.get('assets', {}) or {}
        items = assets.get('items', []) or []
        if (assets.get('totalItems') or 0) > len(items):
            # the API call only returns the first page of a rail (hasNextPage is also true for complete rails, e.g. Top 10)
            logger.logWarning('Rail %s of collection %s: only %d of %s items read (hasNextPage=%s)' % (
                rail.get('title', rail.get('id')), collectionId, len(items), assets.get('totalItems'), assets.get('hasNextPage')))
        for item in items:
            if item.get('id') and item.get('assetType', '') in SHOW_ASSET_TYPES:
                ids.append(item.get('id'))
    return list(dict.fromkeys(ids))

def getLiveTV():
    """The live channels, then the live events, listed by the rails of the website collections (what the website
    offers in the user's country; nothing is stored in the databases, the rails are kept 5 minutes: the events come and go)"""
    logger.logInfo('called function')
    rails = []
    for collection in getWebsiteCollections():
        try:
            rails += getCachedCollection(collection.get('collectionId', collection.get('id')), ttl=config.cacheTTLs['live']).get('rails') or []
        except Exception as e:
            logger.logError('Can\'t read collection %s : %s' % (collection.get('collectionId'), str(e)))
    live = [i for i in formatSearchResults({'rails': rails}) if i.get('type') in LIVE_ASSETS]
    # channels first (the order of the website is kept), then the events
    return sorted(live, key=lambda i: i['type'] != 'channel')

def getCatalogShowIds(refresh=False):
    """Get the ids of all the shows listed in the website collections (without duplicates).

    Returns (ids, nbFailedCollections): a collection that can't be read is skipped."""
    logger.logInfo('called function with param (%s)' % refresh)
    ids = []
    failed = 0
    for collection in getWebsiteCollections():
        collectionId = collection.get('collectionId', collection.get('id'))
        try:
            collectionIds = getCollectionShowIds(collectionId, refresh)
            if not collectionIds:
                logger.logWarning('No show found in collection %s' % collectionId)
            ids += collectionIds
        except Exception as e:
            failed += 1
            logger.logError('Can\'t read collection %s : %s' % (collectionId, str(e)))
    # shows only reachable through search/My List are not in any collection: keep My List ones up to date
    try:
        ids += showDB.getUserData().getMyListIds()
    except Exception as e:
        logger.logError('Can\'t read My List: %s' % str(e))
    return list(dict.fromkeys(ids)), failed

def findCollectionRail(sectionId):
    """Find a rail (section) by id.

    The id of a rail can also be a valid collection id on the API side: asking for that
    collection then returns another collection whose rails don't contain it (empty
    section). So look in the collection with this id first, then in the website
    collections the rail is listed from (home, movies, shows...)."""
    # a rail id that is a title hash can't be a collection id
    candidates = [] if re.match(r'^[0-9a-f]{32}$', str(sectionId)) else [sectionId]
    try:
        candidates += [c.get('collectionId') for c in getWebsiteCollections() if c.get('collectionId')]
    except Exception as e:
        logger.logError('Unable to list website collections: %s' % str(e))
    for collectionId in dict.fromkeys(candidates):
        try:
            for rail in getCachedCollection(collectionId).get('rails', {}):
                if sectionId in (rail.get('id'), cache.generateHashKey(rail.get('title', {}))):
                    return rail
        except Exception as e:
            logger.logError('Unable to read collection %s : %s' % (collectionId, str(e)))
    return {}

def getWebsiteSectionContent(sectionId, page=1, itemsPerPage=8):
    """Get section content"""
    logger.logInfo('called function with param (%s, %s, %s)' % (sectionId, page, itemsPerPage))
    page -= 1
    data = []
    section = findCollectionRail(sectionId)

    logger.logInfo(section)

    index = itemsPerPage * page
    containsShows = True
    i = 0
    for s in section.get('assets', {}).get('items', []):
        i += 1
        if i > index:
            data.append(formatToShow(s))     
        if i >= (index + itemsPerPage):
            break
   
    return removeDuplicates(sorted(
        data,
        key=lambda item: item['dateaired'] if item.get('type') == 'episode' else item['name'],
        reverse=True if containsShows is False else False
    ))

