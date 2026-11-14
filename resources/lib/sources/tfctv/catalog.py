# -*- coding: utf-8 -*-

"""
Catalog management (shows, episodes, categories).

The website calls, the formatting of the assets and the collections live in graphql.py,
formatters.py and rails.py (plus db.py for the databases); their functions stay importable from here.
"""

import time
from resources import config
from resources.lib.libraries import control
from .db import castDB, episodeDB, showDB
from .formatters import (
    formatAssetToEpisode, formatAssetToShow, formatItemsToEpisodes, formatToShow, getSeasonFilters
)
from .graphql import getAppLaunchDetails, getAsset, getCollection, getTVShowEpisodes, searchCatalog
from .rails import (
    SHOW_ASSET_TYPES, findCollectionRail, getCachedCollection, getCatalogShowIds, getCollectionContent,
    getCollectionShowIds, getWebsiteCollections, getWebsiteSectionContent
)

logger = control.logger

def getCategories():
    """Get all categories"""
    logger.logInfo('called function')
    data = []
    uniq = {}
    categories = logger.logInfo(showDB.getAllCategories())
    for cat in categories:
        for c in cat.split('|'):
            if c.strip() != '':
                uniq[c.strip()] = 1
                
    for cat in sorted(uniq.keys()):
        data.append({'id': cat, 'name': cat})

    return data

def getShows(categoryId):
    """Get shows by category"""
    logger.logInfo('called function with param (%s)' % categoryId)
    return showDB.searchByCategory(categoryId)

def getMyListShows():
    """Get the shows of My List: the ones missing from the catalog database (e.g. after the
    catalog was replaced) are loaded from the website"""
    shows = showDB.getMyList(limit=False)
    known = set(show.get('id') for show in shows)
    for showId in showDB.getUserData().getMyListIds():
        if showId not in known:
            show = getShow(showId)
            if show:
                show['mylist'] = 'true'
                shows.append(show)
    return shows

def getMyList():
    """Get user's list"""
    logger.logInfo('called function')
    data = getMyListShows()
    return sorted(data, key=lambda item: item['title'] if 'title' in item else item['name'], reverse=False)

def getMylistShowLastEpisodes():
    """Get last episodes from my list shows"""
    logger.logInfo('called function')
    data = []
    shows = getMyListShows()
    if len(shows) > 0:
        for show in shows:
            (episodes, n) = getEpisodesPerPage(show.get('id'), 1, 1)
            if episodes:
                data.append(episodes.pop())

    return sorted(data, key=lambda item: item['title'] if 'title' in item else item['name'], reverse=False)

def setMyList(id, name, inList):
    """Add a show to My List or remove it"""
    show = getShow(id)
    if showDB.update({'id': id, 'name': show.get('name') or name, 'mylist': 'true' if inList else 'false'}):
        control.showNotification(control.lang(37053) % name)
    else:
        control.showNotification(control.lang(37054) % name)

def addToMyList(id, name, ltype, type):
    """Add to my list"""
    logger.logInfo('called function with param (%s, %s, %s, %s)' % (id, name, ltype, type))
    setMyList(id, name, True)

def removeFromMyList(id, name, ltype, type):
    """Remove from my list"""
    logger.logInfo('called function with param (%s, %s, %s, %s)' % (id, name, ltype, type))
    setMyList(id, name, False)

def getSettings(refresh=False):
    """Get settings from website"""
    logger.logInfo('called function')
    settings = {}
    return settings

def loadSettings(refresh=False):
    """Load settings"""
    logger.logInfo('called function')
    # config.uri.update(getSettings(refresh))
    logger.logDebug(config.uri)

def refreshCatalogShows(loadEpisodes=True, refresh=False):
    """Refresh the shows listed in the website collections (and their episodes).

    Returns False when nothing could be read from the website collections."""
    logger.logInfo('called function with param (%s, %s)' % (loadEpisodes, refresh))
    try:
        showIds, failed = getCatalogShowIds(refresh)
    except Exception as e:
        logger.logError('Can\'t update the catalog : %s' % (str(e)))
        return False
    if not showIds:
        return False

    nbItems = len(showIds)
    logger.logInfo(nbItems)
    start = time.time()
    for k, showId in enumerate(showIds, 1):
        try:
            if loadEpisodes:
                getShowWithEpisodes(showId, 'all')
            else:
                getShow(showId)
        except Exception as se:
            logger.logError('Error updating item %s : %s' % (showId, str(se)))

        if time.time() - start > 5 and k < nbItems:
            start = time.time()
            message = 'Updating catalog... %d%%' % (100 * k // nbItems)
            logger.logNotice(message)
            control.infoDialog(message, heading=control.lang(30005), icon=control.addonIcon(), time=10000)
    return True

def checkCatalogUpdates(loadEpisodes=True):
    """Check catalog for updates (shows listed in the website collections)"""
    logger.logInfo('called function')
    return refreshCatalogShows(loadEpisodes, refresh=True)

def getSeasons(showId):
    """Get seasons for a show"""
    logger.logInfo('called function with param (%s)' % showId)
    data = []
    asset = getAsset(showId)
    if asset and ('seasons' in asset or 'tvShowDetails' in asset):
        for season in getSeasonFilters(asset):
            data.append({
                'id': season['id'],
                'showId': showId,
                'name': season['name']
            })
    return data

def getShowEpisodeItems(id, season='1', asset=None):
    """Get the episode items of a show for a season (an id of getSeasons()).

    The season may also be a month for the shows split by month, or 'all'. When the season is unknown
    (e.g. the default one) fall back on all the seasons/months of the show."""
    seasons = getSeasonFilters(asset or getAsset(id))
    selected = seasons if season == 'all' else [x for x in seasons if str(x['id']) == str(season)]
    if not selected:
        logger.logWarning('Season %s not found for show %s, using all seasons' % (season, id))
        selected = seasons
    items = []
    for x in selected:
        items += (getTVShowEpisodes(id, year=x['year'], month=x['month'], seasonId=x['seasonId']) or {}).get('items') or []
    return items

def getShow(id, season='1', withEpisodes=False):
    """Get show details"""
    logger.logInfo('called function with param (%s, %s, %s)' % (id, season, withEpisodes))
    data = {}
    
    res = showDB.get(id)
    if withEpisodes is False and len(res) == 1:
        actors = castDB.getCast(id)
        for actor in actors:
            actor['castid'] = actor.get('actorid')
        res[0]['actors'] = actors
        res[0]['casts'] = actors
        data = res[0]
    else:
        asset = getAsset(id)
        if asset:
            episodes = []
            if withEpisodes:
                episodes = getShowEpisodeItems(id, season, asset)
            data = formatAssetToShow(asset, formatItemsToEpisodes(episodes, asset))
            showDB.set(data)
            castDB.replaceApiCast(id, data.get('casts', []))
            data['casts'] = castDB.getCast(id)  # the API cast and the actors only the old catalog knows
            if withEpisodes:
                storeEpisodes(data.get('episodes', []))
        else:
            logger.logWarning('Error on show %s: %s' % (id, 'not found'))
    
    return data

def storeEpisodes(episodes):
    """Save episodes in the episodes database: new ones are inserted, known ones get their
    content updated (views, rating and votes stored locally are kept)"""
    episodes = [e for e in episodes if isinstance(e, dict) and e.get('id')]
    if not episodes:
        return
    known = set(e.get('id') for e in episodeDB.get([e.get('id') for e in episodes]))
    new = [e for e in episodes if e.get('id') not in known]
    if new:
        episodeDB.set(new)
    updated = [dict((k, v) for k, v in e.items() if k not in ('views', 'rating', 'votes')) for e in episodes if e.get('id') in known]
    if updated:
        episodeDB.update(updated)

def repairShowCategories():
    """Load again the details of the shows stored without categories (an older version didn't read them)"""
    logger.logInfo('called function')
    repaired = 0
    for showId in showDB.getWithoutCategory():
        try:
            data = formatAssetToShow(getAsset(showId))
            if data.get('parentname'):
                showDB.set(data)
                repaired += 1
        except Exception as e:
            logger.logError('Can\'t repair the categories of show %s : %s' % (showId, str(e)))
    logger.logNotice('Categories repaired for %d shows' % repaired)
    return repaired

def getShowWithEpisodes(showId, season='1'):
    """Get show with episodes"""
    logger.logInfo('called function with param (%s, %s)' % (showId, season))
    data = {
        'nbEpisodes': 0,
        'episodes': []
        }

    return getShow(showId, season, True)

def getEpisodesPerPage(showId, season='1', page=1, itemsPerPage=8, order='desc'):
    """Get episodes paginated"""
    logger.logInfo('called function with param (%s, %s, %s, %s)' % (showId, season, page, itemsPerPage))
    data = []
    
    show = getShowWithEpisodes(showId, season)

    hasNextPage = False

    if show:
        nbEpisodes = show.get('nbEpisodes', 0)
        
        # if movie or special
        if show.get('ltype', '') == 'movie':
            logger.logInfo('movie')
            episodeId = showId
            res = episodeDB.get(episodeId)
            if len(res) == 1:
                e = res[0]
                e['title'] = show.get('name')
                e['episodenumber'] = 1
                e['showObj'] = show
                data.append(e)
            else:
                e = {
                    'id': episodeId,
                    'title': show.get('name'),
                    'show': show.get('name'),
                    'image': show.get('image'),
                    'episodenumber': 1,
                    'description': show.get('description'),
                    'shortdescription': show.get('description'),
                    'dateaired': '',
                    'date': '',
                    'year': show.get('year'),
                    'fanart': show.get('fanart'),
                    'showObj': show,
                    'ltype': show.get('ltype', 'show'),
                    'duration': 0,
                    'views': 0,
                    'rating': 0,
                    'votes': 0,
                    'type': 'episode'
                    }
                episodeDB.set(e)
                data.append(e)
        else:
            logger.logInfo('show')
            episodes = sorted(show.get('episodes', []), key=lambda item: item['episodenumber'], reverse=True if order == 'desc' else False)

            # Calculating episode index according to page and items per page
            episodeIndex = (page * 1 - 1) * itemsPerPage

            for index in range(episodeIndex, episodeIndex+itemsPerPage, 1):
                if index >= nbEpisodes:
                    break

                episodeData = episodes[index]
                episodeId = episodeData.get('id')
                res = episodeDB.get(episodeId)
                if len(res) == 1:
                    e = res[0]
                    e['showObj'] = show
                    data.append(e)
                else:
                    episodeData['showObj'] = show
                    episodeDB.set(episodeData)
                    data.append(episodeData)

    return (data, hasNextPage)

def getEpisode(id, show={}):
    """Get episode details"""
    logger.logInfo('called function with param (%s)' % id)
    
    asset = getAsset(id)
    logger.logInfo(asset)
    if asset and 'showInfo' in asset and asset['showInfo'] is not None:
        showId = asset['showInfo'].get('id', '')
        seasonNumber = asset['showInfo'].get('seasonNumber', '1')
        if showId != '' and (not show or 'id' not in show or show.get('id', '') != showId):
            show = getShow(showId, seasonNumber, False)

    episode = formatAssetToEpisode(getAsset(id), show)
    logger.logDebug(episode)

    if episode.get('id', False):
        res = episodeDB.get(id)
        if len(res) == 1:
            # don't let empty values from the asset erase what is already stored
            # (description, fanart...) - only overwrite with non-empty data
            update = {k: v for k, v in episode.items() if v not in ('', None, {}, [])}
            # keep the artwork already stored for this episode (episode thumbnail):
            # the freshly built fanart is the show-level one
            for k in ('image', 'fanart'):
                if res[0].get(k):
                    update.pop(k, None)
            res[0].update(update)
            episode = res[0]
        episodeDB.set(episode)
        return logger.logInfo(episode)
    return {}

def enterSearch(category, type):
    """Search functionality"""
    logger.logInfo('called function with params (%s, %s)' % (category, type))
    data = []
    search = control.inputText(control.lang(30204)).strip()
    if len(search) >= 3:
        if category == 'movieshow':
            if type == 'title':
                data = showDB.searchByTitle(search)
            elif type == 'category':
                data = showDB.searchByCategory(search)
            elif type == 'year':
                data = showDB.searchByYear(search)
            elif type == 'cast':
                cast = castDB.searchByActorName(search)
                data = showDB.get([c.get('showid') for c in cast])
        elif category == 'episode':
            if type == 'title':
                data = episodeDB.searchByTitle(search)
            elif type == 'date':
                data = episodeDB.searchByDate(search)
    else:
        control.showNotification(control.lang(37046), control.lang(30001))
    return data
