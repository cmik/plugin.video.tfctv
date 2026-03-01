# -*- coding: utf-8 -*-

"""
Catalog management (shows, episodes, categories)
"""

import re
import time
import json
import datetime
from resources import config
from resources.lib.libraries import control, cache
from resources.lib.models import episodes, shows, showcast
from .api import callJsonApi, callGraphQLApi
from .utils import unicodetoascii, removeDuplicates
from .user import getCountryCode, getServiceIds

logger = control.logger

# Load DB
episodeDB = episodes.Episode(control.episodesFile)
showDB = shows.Show(control.showsFile)
castDB = showcast.ShowCast(control.celebritiesFile)

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

def getMyList():
    """Get user's list"""
    logger.logInfo('called function')
    data = showDB.getMyList()
    return sorted(data, key=lambda item: item['title'] if 'title' in item else item['name'], reverse=False)

def getMylistShowLastEpisodes():
    """Get last episodes from my list shows"""
    logger.logInfo('called function')
    data = []
    shows = showDB.getMyList()
    if len(shows) > 0:
        for show in shows:
            (episodes, n) = getEpisodesPerPage(show.get('id'), 1, 1)
            if episodes:
                data.append(episodes.pop())

    return sorted(data, key=lambda item: item['title'] if 'title' in item else item['name'], reverse=False)

def addToMyList(id, name, ltype, type):
    """Add to my list"""
    logger.logInfo('called function with param (%s, %s, %s, %s)' % (id, name, ltype, type))
    show = getShow(id)
    show['mylist'] = 'true'
    if showDB.update(show):
        control.showNotification(control.lang(37053) % name)
    else:
        control.showNotification(control.lang(37054) % name)

def removeFromMyList(id, name, ltype, type):
    """Remove from my list"""
    logger.logInfo('called function with param (%s, %s, %s, %s)' % (id, name, ltype, type))
    show = getShow(id)
    show['mylist'] = 'false'
    if showDB.update(show):
        control.showNotification(control.lang(37053) % name)
    else:
        control.showNotification(control.lang(37054) % name)

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

def getWebsiteCollections():
    """Get website collections"""
    logger.logInfo('called function')
    return getAppLaunchDetails().get('menu', {}).get('collections', [])

def getCachedCollection(collectionId, refresh=False):
    """Get cached collection"""
    logger.logInfo('called function with param (%s, %s)' % (collectionId, refresh))
    catalogKey = 'collection-%s-%s' % (collectionId, datetime.datetime.now().strftime('%Y%m%d%H'))
    catalogJson = cache.getCached(
        cache.shortCache,
        catalogKey,
        lambda: json.dumps(getCollection(collectionId)),
        refresh
    )
    return {} if catalogJson is None else json.loads(catalogJson)

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

def getWebsiteSectionContent(sectionId, page=1, itemsPerPage=8):
    """Get section content"""
    logger.logInfo('called function with param (%s, %s, %s)' % (sectionId, page, itemsPerPage))
    page -= 1
    data = []
    section = next(
        (s for s in getCachedCollection(sectionId).get('rails', {})
         if sectionId in (s.get('id'), cache.generateHashKey(s.get('title', {})))),
        {}
    )
    
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

def getSiteItems():
    """Get site items"""
    logger.logInfo('called function')
    return callJsonApi(config.uri.get('items'), base_url=control.setting('basePath'), useCache=False)

def checkCatalogUpdates(loadEpisodes=True):
    """Check catalog for updates"""
    logger.logInfo('called function')

    elaps = start = time.time()
    try:
        items = getSiteItems()
        nbItems = len(items.keys())
    except Exception as e:
        logger.logError('Can\'t update the catalog : %s' % (str(e)))
        return False

    k = 0
    logger.logInfo(nbItems)
    for id in items.keys():
        item = items[id]
        if 'parents' not in item:
            try:
                if loadEpisodes:
                    getShowWithEpisodes(id)
                else:
                    getShow(id)
            except Exception as se:
                logger.logError('Error updating item %s : %s' % (id, str(se)))

        elaps = time.time()-start
        if elaps > 5:
            start = time.time()
            percent = 100 * k / nbItems
            logger.logNotice('Updating catalog... %s' % (str(percent)+'%'))
            control.infoDialog('Updating catalog... %s' % (str(percent)+'%'), heading=control.lang(30005), icon=control.addonIcon(), time=10000)
        k += 1

    return True

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
        'nbSeasons': showDetails.get('totalSeasons', 1),
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
        'description': asset.get('description', ''),
        'shortdescription': asset.get('description', ''),
        'dateaired': asset.get('releaseDate', ''),
        'date': asset.get('releaseDate', ''),
        'year': show.get('year', asset.get('releaseDate', '')[:4]),
        'parentalAdvisory': show.get('parentalAdvisory', asset.get('rating', '') == 'SPG'),
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
        'parentname': '|'.join(
            asset.get('genreLabels', [])
        ),
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
        'nbSeasons': showDetails.get('totalSeasons', 1),
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

def getSeasons(showId):
    """Get seasons for a show"""
    logger.logInfo('called function with param (%s)' % showId)
    data = []
    asset = getAsset(showId)
    if asset and 'tvShowDetails' in asset and 'totalSeasons' in asset['tvShowDetails']:
        for i in range(1, asset['tvShowDetails']['totalSeasons'] + 1):
            data.append({
                'id': i,
                'showId': showId,
                'name': 'Season %d' % i
            })
    return data

def getShow(id, season='1', withEpisodes=False):
    """Get show details"""
    logger.logInfo('called function with param (%s, %s, %s)' % (id, season, withEpisodes))
    data = {}
    
    res = showDB.get(id)
    if withEpisodes is False and len(res) == 1:
        actors = castDB.getByShow(id)
        for actor in actors:
            actor['castid'] = actor.get('actorid')
        res[0]['actors'] = actors
        data = res[0]
    else:
        asset = getAsset(id)
        if asset:
            episodes = []
            if withEpisodes:
                episodes = getTVShowEpisodes(id, seasonId=season).get('items', [])
            data = formatAssetToShow(asset, formatItemsToEpisodes(episodes, asset))
            showDB.set(data)
        else:
            logger.logWarning('Error on show %s: %s' % (id, 'not found'))
    
    return data

def getShowWithEpisodes(showId, season='1'):
    """Get show with episodes"""
    logger.logInfo('called function with param (%s, %s)' % (showId, season))
    data = {
        'nbEpisodes': 0,
        'episodes': []
        }

    show = getShow(showId, season, True)
    """for e in show.get('episodes', []):
        logger.logDebug(e)
        res = episodeDB.get(e.get('id'))
        if len(res) == 0:
            data['episodes'].append(getEpisode(e.get('id'), show))
        else:
            data['episodes'].append(res[0])
        data['nbEpisodes'] += 1

    show['episodes'] = data['episodes']
    show['nbEpisodes'] = data['nbEpisodes']"""

    return show

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
            episodes = sorted(show.get('episodes', []), key=lambda item: item['title'], reverse=True if order == 'desc' else False)

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
            res[0].update(episode)
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

def searchCatalog(query):
    """Search catalog"""
    logger.logInfo('called function')
    response = callGraphQLApi(
"""query Search($query: String, $skus: [String!]) {
    search(query: $query, skus: $skus) {
        id
        rails {
        id
        railType
        title
        assets {
            items {
            id
            assetType
            title
            shortDescription
            images {
                landscape
                landscapeHero
                portrait
                portraitHero
                title
                square
            }
            isPlayable
            duration
            durationInSeconds
            labels {
                id
                position
                url
            }
            trailerUrls {
                dash {
                url
                }
            }
            genres
            releaseDate
            earlyAccessDate
            cast
            contentDescriptors
            contentOwner
            durationInMs
            directors
            languages
            originalLanguage
            rating
            videoQuality {
                id
                label
            }
            audioQuality {
                id
                label
            }
            subtitleLanguages
            subHeader
            subHeaders
            showInfo {
                id
                title
                tvShowType
                images {
                landscape
                landscapeHero
                portrait
                portraitHero
                title
                square
                }
            }
            tvShowDetails {
                totalSeasons
                tvShowType
                defaultEpisode {
                id
                title
                subHeader
                onAirDate
                }
            }
            monetization {
                type
                logoUrl
                hasSkuAccess
            }
            seasons {
                id
                title
                count
                filter {
                year
                month
                seasonId
                }
            }
            promotionalTag {
                iconUrl
                text
            }
            continueWatching {
                playbackPosition
                audioLang
                subtitleLang
                resolution
                bitrate
            }
            videoOrientation
            }
            currentPage
            hasNextPage
            hasPreviousPage
            pageSize
            totalItems
            totalPages
        }
        dynamicDataQuery
        isDynamicData
        preAggregated
        railSubType
        sourceType
        }
    }
    }""",
        {
            'query': query,
            'skus': getServiceIds(),
            'apiCode':'GSE'
        },
        useCache=False
    )
    return response


def getAppLaunchDetails():
    """Get app launch details from website"""
    logger.logInfo('called function')
    data = callGraphQLApi(
        """query AppLaunchDetails {
            appLaunchDetails
        }""",
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
"""query Collection($collectionId: ID, $skus: [String!]) {
      collection(id: $collectionId, skus: $skus) {
        id
    bannerAds {
          ads {
            adUnitId
        position
        adUnitSize {
              width
          height
        }
        adParams
      }
    }
    rails {
          id
      railType
      title
      images {
            titleUrl
        backgroundOverlayUrl
        sponsoredSectionBgImgUrl
        sponsoredBackdropImgUrl
      }
      assets {
            items {
              id
          assetType
          title
          shortDescription
          images {
                landscape
            landscapeHero
            portrait
            portraitHero
            title
            square
          }
          isPlayable
          duration
          durationInSeconds
          labels {
                id
            position
            url
          }
          trailerUrls {
                dash {
                  url
            }
          }
          genres
          releaseDate
          earlyAccessDate
          cast
          contentCategoryType
          contentDescriptors
          contentOwner
          durationInMs
          directors
          languages
          originalLanguage
          rating
          videoQuality {
                id
            label
          }
          audioQuality {
                id
            label
          }
          subtitleLanguages
          subHeader
          subHeaders
          showInfo {
                id
            title
            tvShowType
            images {
                  landscape
              landscapeHero
              portrait
              portraitHero
              title
              square
            }
          }
          tvShowDetails {
                totalSeasons
            tvShowType
            defaultEpisode {
                  id
              title
              subHeader
              onAirDate
            }
          }
          monetization {
                type
            logoUrl
            hasSkuAccess
          }
          seasons {
                id
            title
            count
            filter {
                  year
              month
              seasonId
            }
          }
          promotionalTag {
                iconUrl
            text
          }
          continueWatching {
                playbackPosition
            audioLang
            subtitleLang
            resolution
            bitrate
          }
          videoOrientation
        }
        currentPage
        hasNextPage
        hasPreviousPage
        pageSize
        totalItems
        totalPages
      }
      dynamicDataQuery
      isDynamicData
      preAggregated
      railSubType
      sourceType
    }
  }
}""",
        variables={
            'collectionId': 'home',
            'skus': getServiceIds()
        },
        useCache=False
    )
    if response and 'collection' in response:
        return response['collection']
    return {}

def getTVShowEpisodes(id, page=1, itemsPerPage=10, year=None, month=None, seasonId=None):
    """Get TV show details"""
    logger.logInfo('called function with param (%s)' % id)
    response = callGraphQLApi("""
query TvShowEpisodes($tvShowEpisodesId: ID, $filters: TvShowEpisodesFilterInput, $skus: [String!]) {
  tvShowEpisodes(id: $tvShowEpisodesId, filters: $filters, skus: $skus) {
    items {
      id
      assetType
      title
      shortDescription
      images {
        landscape
        landscapeHero
        portrait
        portraitHero
        title
        square
      }
      isPlayable
      duration
      durationInSeconds
      labels {
        id
        position
        url
      }
      trailerUrls {
        dash {
          url
        }
      }
      genres
      releaseDate
      earlyAccessDate
      cast
      contentDescriptors
      contentOwner
      durationInMs
      directors
      languages
      originalLanguage
      rating
      videoQuality {
        id
        label
      }
      audioQuality {
        id
        label
      }
      subtitleLanguages
      subHeader
      subHeaders
      showInfo {
        id
        title
        tvShowType
        images {
          landscape
          landscapeHero
          portrait
          portraitHero
          title
          square
        }
      }
      tvShowDetails {
        totalSeasons
        tvShowType
        defaultEpisode {
          id
          title
          subHeader
          onAirDate
        }
      }
      monetization {
        type
        logoUrl
        hasSkuAccess
      }
      seasons {
        id
        title
        count
        filter {
          year
          month
          seasonId
        }
      }
      promotionalTag {
        iconUrl
        text
      }
      continueWatching {
        playbackPosition
        audioLang
        subtitleLang
        resolution
        bitrate
      }
      videoOrientation
    }
    totalItems
    pageSize
    currentPage
    totalPages
    hasNextPage
    hasPreviousPage
  }
}
        """,
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
    return response.get('tvShowEpisodes', {}) if response else {}

def getAsset(id):
    """Get asset details"""
    logger.logInfo('called function with param (%s)' % id)
    response = callGraphQLApi("""
query Asset($assetId: ID, $skus: [String!]) {
  asset(id: $assetId, skus: $skus) {
    id
    assetType
    title
    shortDescription
    images {
      landscape
      landscapeHero
      portrait
      portraitHero
      title
      square
    }
    isPlayable
    duration
    durationInSeconds
    labels {
      id
      position
      url
    }
    trailerUrls {
      dash {
        url
      }
    }
    genres
    releaseDate
    earlyAccessDate
    cast
    contentDescriptors
    contentOwner
    durationInMs
    directors
    languages
    originalLanguage
    rating
    videoQuality {
      id
      label
    }
    audioQuality {
      id
      label
    }
    subtitleLanguages
    subHeader
    subHeaders
    showInfo {
      id
      title
      tvShowType
      seasonNumber
      episodeNumber
      images {
        landscape
        landscapeHero
        portrait
        portraitHero
        title
        square
      }
    }
    tvShowDetails {
      totalSeasons
      tvShowType
      defaultEpisode {
        id
        title
        subHeader
        onAirDate
      }
    }
    monetization {
      type
      logoUrl
      hasSkuAccess
    }
    seasons {
      id
      title
      count
      filter {
        year
        month
        seasonId
      }
    }
    promotionalTag {
      iconUrl
      text
    }
    continueWatching {
      playbackPosition
      audioLang
      subtitleLang
      resolution
      bitrate
    }
    slugUrl
    videoOrientation
  }
}""",
        variables={
            'assetId': id,
            'skus': getServiceIds()
        },
        useCache=False
    )
    return response.get('asset', {}) if response else {}