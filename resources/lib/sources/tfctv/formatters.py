# -*- coding: utf-8 -*-

"""
Formatting of the website assets (shows, episodes, seasons) into the add-on structures
"""

import re
from resources.lib.libraries import control
from .utils import unicodetoascii

logger = control.logger

def formatToShow(data):
    """Format show data"""
    logger.logInfo('called function')
    logger.logDebug(data)

    if data is None or not isinstance(data, dict) or 'id' not in data:
        return {}
    
    type = 'show' if data.get('assetType', '') == 'tvshow' else 'movie' if data.get('assetType', '') == 'movie' else 'documentary' if data.get('assetType', '') == 'documentary' else 'livestream' if data.get('assetType', '') == 'channel' else 'unknown'
    image = data.get('images', {})
    showDetails = data.get('tvShowDetails', {}) if data.get('tvShowDetails', {}) is not None else {}
    return {
        'id': data.get('id'),
        'name': data.get('title', ''),
        'logo': image.get('title', '') if image.get('title', '') != '' else image.get('square', ''),
        'image': image.get('portrait', '') if image.get('portrait', '') != '' else image.get('portraitHero', ''),
        'fanart': image.get('landscapeHero', ''),
        'banner': image.get('landscapeHero', ''),
        'description': unicodetoascii(data.get('shortDescription', '')),
        'year': data.get('releaseDate', '')[:4],
        'genres': data.get('genres', []),
        'type': data.get('assetType', type),
        'ltype': type,
        'nbSeasons': len(getSeasonFilters(data)),
        'isPlayable': data.get('isPlayable', True),
    }

def formatAssetToEpisode(asset, show={}):
    """Format asset to episode"""
    logger.logInfo('called function')

    if asset is None or not isinstance(asset, dict) or 'id' not in asset:
        return {}

    image = asset.get('images', {})

    """datePublished = time.strptime(dateAiredString, '%b %d, %Y')
    dateaired = time.strftime('%B %d, %Y', datePublished)
    date = time.strftime('%Y-%m-%d', datePublished)"""

    showInfo = asset.get('showInfo', {}) if asset.get('showInfo', {}) is not None else {}
    return {
        'id': asset.get('id'),
        'title': asset.get('title', ''),
        'parentid': showInfo.get('id', show.get('id', '')),
        'show': showInfo.get('title', show.get('name', '')),
        'image': image.get('landscape', '') if image.get('landscape', '') != '' else image.get('portrait', '') if image.get('portrait', '') != '' else show.get('image', ''),
        'fanart': show.get('fanart', ''),
        'episodenumber': showInfo.get('episodeNumber', 1),
        'url': asset.get('slugUrl', asset.get('id')),
        'description': asset.get('shortDescription', asset.get('description', '')) or '',
        'shortdescription': asset.get('shortDescription', asset.get('description', '')) or '',
        'dateaired': asset.get('releaseDate', ''),
        'date': asset.get('releaseDate', ''),
        'year': show.get('year', asset.get('releaseDate', '')[:4]),
        'parentalAdvisory': show.get('parentalAdvisory', 'true' if asset.get('rating', '') == 'SPG' else 'false'),
        'duration': asset.get('durationInSeconds', 0),
        'showObj': show,
        'ltype': show.get('ltype', 'show'),
        'type': 'episode',
        'media': ''
    }

def formatAssetToShow(asset, episodes={}):
    """Format asset to show"""
    logger.logInfo('called function')

    if asset is None or not isinstance(asset, dict) or 'id' not in asset:
        return {}

    type = 'show' if asset.get('assetType', '') == 'tvshow' else 'movie' if asset.get('assetType', '') == 'movie' else 'documentary' if asset.get('assetType', '') == 'documentary' else 'livestream' if asset.get('assetType', '') == 'channel' else 'unknown'
    image = asset.get('images', {})
    showDetails = asset.get('tvShowDetails', {}) if asset.get('tvShowDetails', {}) is not None else {}
    return {
        'id': asset.get('id'),
        'name': asset.get('title', ''),
        'parentid': asset.get('assetType', ''),
        # the categories of a show are its genres
        'parentname': '|'.join(str(g) for g in (asset.get('genres') or asset.get('genreLabels') or [])),
        'logo': image.get('title', '') if image.get('title', '') != '' else image.get('square', ''),
        'image': image.get('portrait', '') if image.get('portrait', '') != '' else image.get('portraitHero', ''),
        'fanart': image.get('landscape', '') if image.get('landscape', '') != '' else image.get('landscapeHero', ''),
        'banner': image.get('landscapeHero', '') if image.get('landscapeHero', '') != '' else image.get('landscape', ''),
        'url': asset.get('slugUrl', asset.get('id')),
        'description': asset.get('shortDescription', ''),
        'shortdescription': asset.get('shortDescription', ''),
        'year': asset.get('releaseDate', '')[:4],
        'nbEpisodes': len(episodes),
        'episodes': episodes,
        'casts': [{
                'actorid': str(c).lower().replace(' ', '-'),
                'showid': id,
                'name': c,
                'thumbnail': '',
                'order': i
            } for i, c in enumerate(asset.get('cast', []))],
        'ltype': type,
        'duration': asset.get('durationInSeconds', 0),
        'views': 0,
        'rating': 0,
        'votes': 0,
        'mylist': '',
        'type': asset.get('assetType', type),
        'parentalAdvisory': 'true' if asset.get('rating', '') == 'SPG' else 'false',
        'media': False,
        'streamID': False,
        'nbSeasons': len(getSeasonFilters(asset)),
        'isPlayable': asset.get('isPlayable', True),
    }

def formatItemsToEpisodes(items, showAsset={}):
    """Format items to episodes"""
    logger.logInfo('called function')

    if items is None or not isinstance(items, list) or len(items) == 0:
        return []

    def getShowInfo(key, showInfo, show):
        return showInfo.get(key, show.get('title' if key == 'name' else key, ''))
    
    def extractEpisodeNumber(title):
        """Extract episode number from title"""
        match = re.search(r'(?i)(?:Episode|Ep|E)[\s\.]*(\d+)', title)
        if match:
            return match.group(1)
        return '0'
    
    show = formatToShow(showAsset) if 'id' in showAsset else {}
    data = []
    for item in items:
        showInfo = item.get('showInfo', {})
        image = item.get('images', {})
        e = {
            'id': item.get('id'),
            'title': '%s - %s' % (item.get('subHeader', ''), item.get('title', '')) if item.get('subHeader', '') != '' else item.get('title', ''),
            'parentid': getShowInfo('id', showInfo, show),
            'show': getShowInfo('name', showInfo, show),
            'image': image.get('landscape', '') if image.get('landscape', '') != '' else image.get('portrait', '') if image.get('portrait', '') != '' else image.get('portraitHero', '') if image.get('portraitHero', '') != '' else show.get('image', ''),
            'fanart': image.get('landscape', '') if image.get('landscape', '') != '' else image.get('portrait', '') if image.get('portrait', '') != '' else image.get('portraitHero', '') if image.get('portraitHero', '') != '' else show.get('fanart', ''),
            'episodenumber': int(extractEpisodeNumber(item.get('subHeader', ''))),
            'url': item.get('slugUrl', item.get('id')),
            'description': unicodetoascii(item.get('shortDescription', '')),
            'shortdescription': unicodetoascii(item.get('shortDescription', '')),
            'dateaired': item.get('releaseDate', ''),
            'date': item.get('releaseDate', ''),
            'year': item.get('releaseDate', '')[:4],
            'ltype': show.get('ltype', 'show'),
            'duration': item.get('durationInSeconds', 0),
            'views': 0,
            'rating': 0,
            'votes': 0,
            'type': 'episode'
        }
        data.append(e)
    return data

def getSeasonFilters(asset):
    """List the 'seasons' of an asset with the filter to use to get their episodes.

    Most shows have numbered seasons, some (e.g. Pinoy Big Brother) have none and their
    episodes are split by month: the API then lists them in asset.seasons with a null seasonId."""
    asset = asset or {}
    seasons = []
    for season in asset.get('seasons') or []:
        f = season.get('filter') or {}
        seasons.append({
            'id': season.get('id'),
            'name': season.get('title') or str(season.get('id')),
            'seasonId': f.get('seasonId'),
            'year': f.get('year'),
            'month': f.get('month')
        })
    if not seasons:
        details = asset.get('tvShowDetails') or {}
        for i in range(1, (details.get('totalSeasons') or 1) + 1):
            seasons.append({'id': i, 'name': 'Season %d' % i, 'seasonId': str(i), 'year': None, 'month': None})
    return seasons

