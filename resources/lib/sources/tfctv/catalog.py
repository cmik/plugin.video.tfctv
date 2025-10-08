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
from .api import callJsonApi, callServiceApi, callGraphQLApi
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

def getHomeCatalog(refresh=False):
    """Get home catalog"""
    logger.logInfo('called function')
    catalogKey = 'catalog-%s' % datetime.datetime.now().strftime('%Y%m%d%H')
    catalogJson = cache.getCached(
        cache.shortCache,
        catalogKey,
        lambda: json.dumps(getCollection('home')),
        refresh
    )
    return {} if catalogJson is None else json.loads(catalogJson)

def getWebsiteHomeSections():
    """Get website home sections"""
    logger.logInfo('called function')
    getAppLaunchDetails()
    data = []
    catalog = getHomeCatalog(True)
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
    logger.logInfo('called function')
    page -= 1
    data = []
    section = next(
        (s for s in getHomeCatalog().get('rails', {}) 
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
    type = 'show' if data.get('assetType', '') == 'tvshow' else 'movie' if data.get('assetType', '') == 'movie' else 'documentary' if data.get('assetType', '') == 'documentary' else 'livestream' if data.get('assetType', '') == 'channel' else 'unknown'
    image = data.get('images', {})
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
        'type': type,
        'ltype': type
    }

def getShow(id, withEpisodes=False):
    """Get show details"""
    logger.logInfo('called function with param (%s, %s)' % (id, withEpisodes))
    data = {}
    
    res = showDB.get(id)
    if withEpisodes is False and len(res) == 1:
        actors = castDB.getByShow(id)
        for actor in actors:
            actor['castid'] = actor.get('actorid')
        res[0]['actors'] = actors
        data = res[0]
    else:
        show = callJsonApi(
            config.uri.get('item') % id,
            headers=[
                ('Referer', config.websiteSecuredUrl+'/'),
                ('Origin', config.websiteSecuredUrl),
                ('Cache-Control', 'no-cache'),
                ('Pragma', 'no-cache'),
                ('Sec-Fetch-Dest', 'script'),
                ('Sec-Fetch-Mode', 'no-cors'),
                ('Sec-Fetch-Site', 'cross-site')
                ],
            base_url=control.setting('basePath'),
            useCache=False)
        logger.logInfo(control.setting('basePath') + config.uri.get('item') % id)
        if show:
            name = unicodetoascii(show.get('title', {}).get('en', ''))
            image = control.setting('basePath') + config.uri.get('images') % show.get('thumbnail') if show.get('thumbnail', '') != '' else ''
            fanart = control.setting('basePath') + config.uri.get('images') % show.get('background') if show.get('background', '') != '' else ''
            description = unicodetoascii(show.get('description', {}).get('en', ''))
            year = show.get('release_year', '')
            genres = show.get('tags', {}).get('tag_id_genres', [])
            genreLabels = []
            for genre in genres:
                label = callJsonApi(
                    config.uri.get('value') % genre,
                    headers=[
                        ('Referer', config.websiteSecuredUrl+'/'),
                        ('Origin', config.websiteSecuredUrl),
                        ('Cache-Control', 'no-cache'),
                        ('Pragma', 'no-cache'),
                        ('Sec-Fetch-Dest', 'script'),
                        ('Sec-Fetch-Mode', 'no-cors'),
                        ('Sec-Fetch-Site', 'cross-site')
                        ],
                    base_url=control.setting('basePath'),
                    useCache=True)
                if 'en' in label:
                    genreLabels.append(unicodetoascii(label.get('en', '')))
                    
            type = 'show'
            if 'id_movie' in genres:
                type = 'movie'
            elif 'id_documentary' in genres:
                type = 'documentary'
            elif 'streamID' in show:
                type = 'livestream'
            elif show.get('rules', {}).get('type', 'show') in ('movie', 'show'):
                type = show.get('rules', {}).get('type', 'show')
            
            actors = []
            casts = show.get('tags', {}).get('tag_id_cast', [])
            i = 1
            for castId in casts:
                castId = unicodetoascii(castId)
                actor = castDB.get(castId)
                if len(actor) == 1:
                    actors.append(actor[0])
                else:
                    actorData = callJsonApi(
                        config.uri.get('value') % castId,
                        headers=[
                            ('Referer', config.websiteSecuredUrl+'/'),
                            ('Origin', config.websiteSecuredUrl),
                            ('Cache-Control', 'no-cache'),
                            ('Pragma', 'no-cache'),
                            ('Sec-Fetch-Dest', 'script'),
                            ('Sec-Fetch-Mode', 'no-cors'),
                            ('Sec-Fetch-Site', 'cross-site')
                            ],
                        base_url=control.setting('basePath'),
                        useCache=True)
                    if 'en' in actorData:
                        actorName = unicodetoascii(actorData.get('en', ''))
                        actorThumb = ''
                        actorInfo = {
                            'actorid': castId,
                            'showid': id,
                            'name': actorName,
                            'thumbnail': actorThumb,
                            'order': i
                        }
                        castDB.set(actorInfo)
                        actors.append(actorInfo)
                i += 1

            data = {
                'id': id,
                'name': name,
                'parentid': '|'.join(genres),
                'parentname': '|'.join(genreLabels),
                'logo': image,
                'image': image,
                'fanart': fanart,
                'banner': fanart,
                'url': id,
                'description': description,
                'shortdescription': description,
                'year': year,
                'nbEpisodes': len(show.get('children', [])) if type != 'movie' else 1,
                'episodes': show.get('children', []),
                'casts': actors,
                'ltype': type,
                'duration': 0,
                'views': 0,
                'rating': 0,
                'votes': 0,
                'mylist': res[0].get('mylist', 'false') if len(res) == 1 else 'false',
                'type': type,
                'parentalAdvisory': 'true' if show.get('ratings', {}).get('us', '') == 'PG' else 'false',
                'media': show.get('media', False),
                'streamID': show.get('streamID', False)
                }
            showDB.set(data)
        else:
            logger.logWarning('Error on show %s: %s' % (id, 'not found'))
    
    return data

def getShowWithEpisodes(showId):
    """Get show with episodes"""
    logger.logInfo('called function with param (%s)' % (showId))
    data = {
        'nbEpisodes': 0,
        'episodes': []
        }

    show = getShow(showId, True)
    for e in show.get('episodes', []):
        res = episodeDB.get(e.get('id'))
        if len(res) == 0:
            data['episodes'].append(getEpisode(e.get('id'), show))
        else:
            data['episodes'].append(res[0])
        data['nbEpisodes'] += 1

    show['episodes'] = data['episodes']
    show['nbEpisodes'] = data['nbEpisodes']

    return show

def getEpisodesPerPage(showId, page=1, itemsPerPage=8, order='desc'):
    """Get episodes paginated"""
    logger.logInfo('called function with param (%s, %s, %s)' % (showId, page, itemsPerPage))
    data = []
    
    show = getShowWithEpisodes(showId)

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
                    episode = callJsonApi(
                        config.uri.get('item') % episodeData.get('id'),
                        headers=[
                            ('Referer', config.websiteSecuredUrl+'/'),
                            ('Origin', config.websiteSecuredUrl),
                            ('Cache-Control', 'no-cache'),
                            ('Pragma', 'no-cache'),
                            ('Sec-Fetch-Dest', 'script'),
                            ('Sec-Fetch-Mode', 'no-cors'),
                            ('Sec-Fetch-Site', 'cross-site')
                            ],
                        base_url=control.setting('basePath'),
                        useCache=False)
                    image = control.setting('basePath') + config.uri.get('images') % episode.get('thumbnail') if episode.get('thumbnail', '') != '' else ''
                    description = unicodetoascii(episode.get('description', {}).get('en', ''))
                    e = {
                        'id': episodeData.get('id'),
                        'title': unicodetoascii(episode.get('title', {}).get('en', episodeData.get('id'))),
                        'parentid': showId,
                        'show': show.get('name', ''),
                        'image': image,
                        'fanart': show.get('fanart', ''),
                        'episodenumber': episode.get('episode', 0),
                        'url': episodeId,
                        'description': description,
                        'shortdescription': description,
                        'dateaired': '',
                        'date': '',
                        'year': show.get('year', ''),
                        'parentalAdvisory': show.get('parentalAdvisory'),
                        'showObj': show,
                        'ltype': show.get('ltype', 'show'),
                        'type': 'episode'
                        }
                    episodeDB.set(e)
                    data.append(e)

    return (data, hasNextPage)

def getEpisode(id, show={}):
    """Get episode details"""
    logger.logInfo('called function with param (%s)' % id)
    data = {}
    
    episode = callJsonApi(
        config.uri.get('item') % id,
        headers=[
            ('Referer', config.websiteSecuredUrl+'/'),
            ('Origin', config.websiteSecuredUrl),
            ('Cache-Control', 'no-cache'),
            ('Pragma', 'no-cache'),
            ('Sec-Fetch-Dest', 'script'),
            ('Sec-Fetch-Mode', 'no-cors'),
            ('Sec-Fetch-Site', 'cross-site')
            ],
        base_url=control.setting('basePath'),
        useCache=False
        )
    if episode.get('id', False):
        parents = episode.get('parents', [])
        if parents and show == {} and type(parents[0]) is dict:
            show = getShow(parents[0].get('id', ''))
        title = unicodetoascii(episode.get('title', {}).get('en', id))
        image = control.setting('basePath') + config.uri.get('images') % episode.get('thumbnail') if episode.get('thumbnail', '') != '' else ''
        description = unicodetoascii(episode.get('description', {}).get('en', ''))
        dateaired = ''
        date = ''
        
        # check if aired date in title
        logger.logInfo(title)
        dateaired_match = re.compile('([a-z-A-Z]+ \d+, \d{4})', re.IGNORECASE).search(title)
        if dateaired_match:
            dateAiredString = dateaired_match.group(1)
            logger.logInfo(dateAiredString)
            try:
                logger.logInfo('here')
                datePublished = time.strptime(dateAiredString, '%B %d, %Y')
            except:
                logger.logInfo('there')
                datePublished = time.strptime(dateAiredString, '%b %d, %Y')
            logger.logInfo(datePublished)
            dateaired = time.strftime('%B %d, %Y', datePublished)
            date = time.strftime('%Y-%m-%d', datePublished)

        data = {
            'id': id,
            'title': title,
            'parentid': show.get('id'),
            'show': show.get('name', ''),
            'image': image,
            'fanart': show.get('fanart', ''),
            'episodenumber': episode.get('episode', 0),
            'url': id,
            'description': description,
            'shortdescription': description,
            'dateaired': dateaired,
            'date': date,
            'year': show.get('year', ''),
            'parentalAdvisory': show.get('parentalAdvisory'),
            'showObj': show,
            'ltype': show.get('ltype', 'show'),
            'type': 'episode',
            'media': episode.get('media')
            }
        res = episodeDB.get(id)
        if len(res) == 1:
            res[0].update(data)
            data = res[0]
        episodeDB.set(data)
        if episode.get('mediaID'):
            data['media']['id'] = episode.get('mediaID')
    
    return logger.logInfo(data)

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