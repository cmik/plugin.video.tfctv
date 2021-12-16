# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

import os,sys,re,urllib,urllib2,ssl,cookielib,json,datetime,time,hashlib,inputstreamhelper
from unidecode import unidecode
from operator import itemgetter
from resources import config
from resources.lib.libraries import control
from resources.lib.libraries import cache
from resources.lib.models import episodes
from resources.lib.models import shows
from resources.lib.models import library
from resources.lib.models import showcast

common = control.common
logger = control.logger

# Load DB
episodeDB = episodes.Episode(control.episodesFile)
showDB = shows.Show(control.showsFile)
libraryDB = library.Library(control.libraryFile)
castDB = showcast.ShowCast(control.celebritiesFile)

Logged = False

#---------------------- FUNCTIONS ----------------------------------------                  

def playEpisode(episodeId, name, type, thumbnail, bandwidth=False):
    logger.logInfo('called function')
    errorCode = -1
    episodeDetails = {}
    
    if checkProxy() == True:
        # Check if logged in
        if control.setting('emailAddress') != '' and isLoggedIn() == False:
            control.showNotification(control.lang(57012), control.lang(50002))
            login()
            
        # for i in range(int(control.setting('loginRetries')) + 1):
            # episodeDetails = getMediaInfo(episodeId, name, thumbnail)
            # if episodeDetails and 'errorCode' in episodeDetails and episodeDetails['errorCode'] == 0 and 'data' in episodeDetails:
                # break
            # else:
                # login()
                
        episodeDetails = getMediaInfo(episodeId, name, type, thumbnail, bandwidth)
        logger.logDebug(episodeDetails)
        if episodeDetails and 'errorCode' in episodeDetails and episodeDetails['errorCode'] == 0 and 'data' in episodeDetails:
            if 'preview' in episodeDetails['data'] and episodeDetails['data']['preview'] == True:
                control.infoDialog(control.lang(57025), control.lang(50002), time=5000)
            elif 'StatusMessage' in episodeDetails and episodeDetails['StatusMessage'] != '':
                control.showNotification(episodeDetails['StatusMessage'], control.lang(50009))
            
            url = control.setting('proxyStreamingUrl') % (control.setting('proxyHost'), control.setting('proxyPort'), urllib.quote(episodeDetails['data']['uri']), '') if not episodeDetails.get('disableProxy', False) and not episodeDetails.get('useDash', False) and (control.setting('useProxy') == 'true') else episodeDetails['data']['uri']
            liz = control.item(name, path=url+'|User-Agent=%s' % (config.userAgents['default']), thumbnailImage=thumbnail, iconImage="DefaultVideo.png")
            liz.setInfo(type='video', infoLabels={
                'title': name, 
                'sorttitle' : episodeDetails['data']['dateaired'],
                'tvshowtitle' : episodeDetails['data']['show'],
                'genre' : episodeDetails['data']['parentname'],
                'episode' : episodeDetails['data']['episodenumber'],
                'tracknumber' : episodeDetails['data']['episodenumber'],
                'plot' : episodeDetails['data']['plot'],
                'aired' : episodeDetails['data']['dateaired'],
                'year' : episodeDetails['data']['year'],
                'mediatype' : episodeDetails['data']['type'] 
                })

            # Add eventual subtitles
            if 'subtitles' in episodeDetails['data'] and len(episodeDetails['data']['subtitles']) and 'id' in episodeDetails['data']['subtitles'][0]:
                logger.logInfo(control.setting('basePath') + config.uri.get('captions') % (episodeDetails['data']['subtitles'][0]['id'], 'vtt'))
                try:
                    liz.setSubtitles([control.setting('basePath') + config.uri.get('captions') % (episodeDetails['data']['subtitles'][0]['id'], 'vtt')])
                    if 'lang' in episodeDetails['data']['subtitles'][0]: liz.addStreamInfo('subtitle', {'language' : episodeDetails['data']['subtitles'][0]['lang']})
                except: pass

            if episodeDetails.get('useDash', False):
                logger.logDebug(episodeDetails['dash'])
                
                protocol = 'mpd'
                drm = episodeDetails['dash']['type']
                license_server = episodeDetails['dash']['key']
                headers = episodeDetails['dash']['headers']
                license_key = logger.logDebug('%s|%s|%s|%s' % (license_server, headers, 'R{SSM}', ''))

                is_helper = inputstreamhelper.Helper(protocol, drm=drm)
                is_helper.check_inputstream()
                liz.setProperty('inputstreamaddon', 'inputstream.adaptive')
                liz.setProperty('inputstream.adaptive.manifest_type', protocol)
                liz.setProperty('inputstream.adaptive.license_type', drm)
                liz.setProperty('inputstream.adaptive.stream_headers','Origin=%s&Referer=%s&User-Agent=%s&cache-control=no-cache&pragma=no-cache&sec-fetch-mode=cors&sec-fetch-site=cross-site' % (config.websiteUrl, config.websiteUrl+'/', config.userAgents['default']))
                # liz.setProperty('inputstream.adaptive.license_data', '')
                liz.setProperty('inputstream.adaptive.license_key', license_key)
                liz.setMimeType(episodeDetails['data']['type'])
                liz.setContentLookup(False)
            
            liz.setProperty('fanart_image', episodeDetails['data']['fanart'])
            liz.setProperty('IsPlayable', 'true')
            try: 
                return control.resolve(thisPlugin, True, liz)
            except: 
                control.showNotification(control.lang(57032), control.lang(50004))
        elif (not episodeDetails) or (episodeDetails and 'errorCode' in episodeDetails and episodeDetails['errorCode'] != 0):
            logger.logNotice(episodeDetails['StatusMessage'])
            if 'StatusMessage' in episodeDetails:
                control.showNotification(episodeDetails['StatusMessage'], control.lang(50004))
            else:
                control.showNotification(control.lang(57001), control.lang(50009))
    return False
    
def getMediaInfo(episodeId, title, type, thumbnail, bandwidth=False):
    logger.logInfo('called function')
    mediaInfo = getMediaInfoFromWebsite(episodeId, type, bandwidth)
    if mediaInfo['errorCode'] == 0:
        e = {
            'id' : episodeId,
            'title' : title,
            'parentid' : mediaInfo['data']['showid'],
            'show' : mediaInfo['data']['show'],
            'image' : thumbnail,
            'fanart' : mediaInfo['data']['fanart'],
            'episodenumber' : mediaInfo['data']['episodenumber'],
            'url' : mediaInfo['data']['url'],
            'description' : mediaInfo['data']['plot'],
            'shortdescription' : mediaInfo['data']['plot'],
            'dateaired' : mediaInfo['data']['dateaired'],
            'date' : mediaInfo['data']['date'],
            'year' : mediaInfo['data']['year'],
            'parentalAdvisory' : mediaInfo['data']['parentalAdvisory'],
            'ltype' : mediaInfo['data']['ltype'],
            'type' : 'episode',
            'duration' : mediaInfo['data']['duration'],
            'views' : mediaInfo['data']['views'] + 1,
            'rating' : mediaInfo['data']['rating'],
            'votes' : mediaInfo['data']['votes']
            }
        episodeDB.set(e)

        s = mediaInfo['data']['showObj']
        showDB.update({'id' : s.get('id'), 'views' : s.get('views', 0) + 1})
        
    return mediaInfo

def getEpisodeBandwidthList(episodeId, title, type, thumbnail):
    logger.logInfo('called function')
    mediaInfo = getMediaInfoFromWebsite(episodeId, type)
    data = []
    if mediaInfo['errorCode'] == 0:
        i = 0
        for resolution in mediaInfo['data']['bandwidth']:
            data.append({
            'id' : episodeId,
            'title' : title,
            'parentid' : mediaInfo['data']['showid'],
            'show' : mediaInfo['data']['show'],
            'image' : thumbnail,
            'fanart' : mediaInfo['data']['fanart'],
            'episodenumber' : mediaInfo['data']['episodenumber'],
            'url' : mediaInfo['data']['url'],
            'description' : mediaInfo['data']['plot'],
            'shortdescription' : mediaInfo['data']['plot'],
            'dateaired' : mediaInfo['data']['dateaired'],
            'date' : mediaInfo['data']['date'],
            'year' : mediaInfo['data']['year'],
            'parentalAdvisory' : mediaInfo['data']['parentalAdvisory'],
            'ltype' : mediaInfo['data']['ltype'],
            'type' : 'episode',
            'duration' : mediaInfo['data']['duration'],
            'views' : mediaInfo['data']['views'],
            'rating' : mediaInfo['data']['rating'],
            'votes' : mediaInfo['data']['votes'],
            'showObj' : mediaInfo['data']['showObj'],
            'bandwidth' : i, 
            'resolution' : resolution})
            i+=1
    return data

def getMediaInfoFromWebsite(episodeId, type, bandwidth=False):
    logger.logInfo('called function with param (%s, %s, %s)' % (str(episodeId), type, bandwidth))
    
    mediaInfo = {
        'errorCode' : 0,
        'StatusMessage': ''
        }

    liveStream = False
    episode = {}
    if type == 'show':
        logger.logInfo('episode')
        episode = logger.logInfo(getEpisode(episodeId))
    elif type == 'livestream':
        logger.logInfo('livestream')
        episode = logger.logInfo(getEpisodeFromLiveStream(episodeId))
        liveStream = True
    else:
        logger.logInfo(type)
        episode = logger.logInfo(getEpisodeFromShow(episodeId))

    if episode.get('id', True) == True:
        mediaInfo['StatusMessage'] = control.lang(57032)
        mediaInfo['errorCode'] = 2
    else :
        show = logger.logInfo(episode.get('showObj', {}))
        mediaInfo['data'] = {}
        mediaInfo['data']['url'] = episode.get('url')
        mediaInfo['data']['uri'] = episode.get('media', {}).get('m3u8s', [])[0]
        
        # Parental advisory
        mediaInfo['data']['parentalAdvisory'] = 'false'
        if episode.get('parentalAdvisory') == 'true':
            mediaInfo['data']['parentalAdvisory'] = 'true'
            if control.setting('parentalAdvisoryCheck') == 'true':
                control.alert(control.lang(57011),title=control.lang(50003))
            if control.setting('parentalControl') == 'true':
                code = control.numpad(control.lang(57021))
                if code != control.setting('parentalCode'):
                    mediaInfo['StatusMessage'] = control.lang(57022)
                    mediaInfo['errorCode'] = 3
                    mediaInfo['data'] = {}
                    return mediaInfo
        
        # check if amssabscbn.akamaized.net to use inputstream.adaptive

        if 'mpds' in episode.get('media', {}):
            # mediaInfo['StatusMessage'] = control.lang(57038)
            # mediaInfo['errorCode'] = 5

            mediaInfo['useDash'] = True
            headers = 'Origin=%s&Referer=%s&User-Agent=%s&Sec-Fetch-Dest=empty&Sec-Fetch-Mode=cors&Sec-Fetch-Site=same-origin' % (config.websiteUrl, config.websiteUrl+'/', config.userAgents['default'])

            # choose best stream quality
            defaultQuality = 0
            if bandwidth is False:    
                mediaInfo['data']['bandwidth'] = []
                for stream in episode.get('media', {}).get('mpds', []):
                    mpd_match = re.compile('manifest\.(\d+x\d+)\.mpd', re.IGNORECASE).search(stream)
                    if mpd_match :
                        resolution = mpd_match.group(1)
                        mediaInfo['data']['bandwidth'].append(resolution)
            else:
                defaultQuality = int(bandwidth)
            
            mediaInfo['data']['uri'] = episode.get('media', {}).get('mpds', [])[defaultQuality]
            mediaInfo['dash'] = {
                'type': 'com.widevine.alpha',
                'headers': headers,
                'key': control.setting('proxyStreamingUrl') % (control.setting('proxyHost'), control.setting('proxyPort'), urllib.quote_plus(config.websiteUrl + config.uri.get('licence') % episodeId), '')
                }
                
        #     logger.logDebug(m3u8)
        #     if m3u8:
        #         lines = m3u8.split('\n')
        #         i = 0
        #         bestBandwidth = 0
        #         choosedStream = ''
        #         for l in lines:
        #             bw_match = re.compile('BANDWIDTH=([0-9]+)', re.IGNORECASE).search(lines[i])
        #             if bw_match :
        #                 currentBandwidth = int(bw_match.group(1))
        #                 res_match = re.compile('RESOLUTION=([0-9]+x[0-9]+)', re.IGNORECASE).search(lines[i])
        #                 if res_match :
        #                     mediaInfo['data']['bandwidth'][str(currentBandwidth)] = res_match.group(1)
        #                 if bandwidth != False and currentBandwidth == int(bandwidth):
        #                     choosedStream = lines[i+1]
        #                     break
        #                 elif currentBandwidth > bestBandwidth:
        #                     bestBandwidth = currentBandwidth
        #                     choosedStream = lines[i+1]
        #                 i+=2
        #             else:
        #                 i+=1

        #             if i >= len(lines):
        #                 break

        #         if (control.setting('chooseBestStream') == 'true' or bandwidth != False): # and liveStream == False: 
        #             logger.logInfo(choosedStream)
        #             mediaInfo['data']['uri'] = choosedStream
        #     else:
        #         mediaInfo['StatusMessage'] = control.lang(57032)
        #         mediaInfo['errorCode'] = 9

        mediaInfo['data'].update(episode.get('media'))
        mediaInfo['data']['preview'] = False
        mediaInfo['data']['showid'] = show.get('id')
        mediaInfo['data']['show'] = show.get('name', episode.get('title'))
        mediaInfo['data']['parentname'] = show.get('parentname','')
        mediaInfo['data']['rating'] = show.get('rating', 0)
        mediaInfo['data']['votes'] = show.get('votes', 0)
        mediaInfo['data']['plot'] = episode.get('description')
        mediaInfo['data']['image'] = episode.get('image')
        mediaInfo['data']['fanart'] = show.get('fanart', episode.get('image'))
        mediaInfo['data']['ltype'] = episode.get('ltype', 'show')
        mediaInfo['data']['type'] = episode.get('type', 'show')
        if 'captions' in mediaInfo['data'] and len(mediaInfo['data']['captions']):
            for caption in mediaInfo['data']['captions']:
                if caption.get('lang') == 'en':
                    mediaInfo['data'].update({'subtitles' : [caption]})
                    del mediaInfo['data']['captions']
                    break
        # try:
        #     datePublished = datetime.datetime.strptime(episodeData.get('datePublished'), '%Y-%m-%d')
        # except TypeError:
        #     datePublished = datetime.datetime(*(time.strptime(episodeData.get('datePublished'), '%Y-%m-%d')[0:6]))
        mediaInfo['data']['dateaired'] = ''
        mediaInfo['data']['date'] = ''
        mediaInfo['data']['year'] = show.get('year')
        mediaInfo['data']['episodenumber'] = episode.get('episodenumber', 1)
        mediaInfo['data']['duration'] = episode.get('media', {}).get('duration')
        mediaInfo['data']['views'] = episode.get('views', 0)
        mediaInfo['data']['showObj'] = show
                
        logger.logInfo(mediaInfo)
    
    return mediaInfo

def resetCatalogCache():
    logger.logInfo('called function')
    episodeDB.drop()
    showDB.drop()
    control.showNotification(control.lang(57039), control.lang(50010))
    reloadCatalogCache()

def reloadCatalogCache():
    logger.logInfo('called function')
    updateEpisodes = False
    if (control.confirm(control.lang(57035), line1=control.lang(57036), title=control.lang(50402))):
        updateEpisodes = True
    if updateCatalogCache(updateEpisodes) is True:
        control.showNotification(control.lang(57003), control.lang(50010))
    else:
        control.showNotification(control.lang(57027), control.lang(50004))
    
def updateCatalogCache(loadEpisodes=False):
    logger.logInfo('called function')
    control.showNotification(control.lang(57015), control.lang(50005))
    cache.longCache.cacheClean(True) 
    cache.shortCache.cacheClean(True)
    
    # checkElaps = lambda x, y: x = time.time()-x if (time.time()-x) > y else x
    elaps = start = time.time()
    
    try:
        control.showNotification(control.lang(57014), control.lang(50005))
        # update by items
        # if control.setting('displayWebsiteSections') == 'true':
            # control.showNotification(control.lang(57013))
            # sections = cache.sCacheFunction(getWebsiteHomeSections)
            # for section in sections:
                # cache.sCacheFunction(getWebsiteSectionContent, section['id'])

        # update categories cache
        # categories = cache.lCacheFunction(getCategories)
        categories = getWebsiteHomeSections()
        nbCat = len(categories)
        i = 0
    except Exception as e:
        logger.logError('Can\'t update the catalog : %s' % (str(e)))
        return False

    for cat in categories:
        nbItems = 0
        try: 
            items = getWebsiteSectionContent(cat['id'], 1, 100)
            nbItems = len(items)
        except Exception as ce:
            logger.logError('Can\'t update category %s : %s' % (cat['id'], str(ce)))
            continue
        j = 0
        for s in items:
            try: 
                if loadEpisodes: episodes = getEpisodesPerPage(s['id'], 1)
                else: show = getShow(s['id'])
            except Exception as se: 
                logger.logError('Can\'t update show %s : %s' % (s['id'], str(se)))
                j+=1
                continue
            j+=1
            
            elaps = time.time()-start 
            if elaps > 5:
                start = time.time()
                catpercent = 100 * i / nbCat
                cat1percent = 100 * 1 / nbCat
                showpercent = 100 * j / nbItems
                percent = part * 100 * (1 + 1 * (catpercent + (cat1percent * (cat1percent * showpercent / 100) / 100)))
                logger.logNotice('Updating catalog... %s' % (str(percent)+'%'))
                control.infoDialog('Updating catalog... %s' % (str(percent)+'%'), heading=control.lang(50005), icon=control.addonIcon(), time=10000)
        i+=1
        
    return True

def checkCatalogUpdates(loadEpisodes=True):
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
                logger.logInfo(item)
                if loadEpisodes: episodes = getEpisodesPerPage(id, 1)
                else: show = getShow(id)
            except Exception as se: 
                logger.logError('Can\'t update show %s : %s' % (id, str(se)))
                k+=1
                continue

        elaps = time.time()-start     
        if elaps > 5:
            start = time.time()
            percent = 100 * k / nbItems
            logger.logNotice('Updating catalog... %s' % (str(percent)+'%'))
            control.infoDialog('Updating catalog... %s' % (str(percent)+'%'), heading=control.lang(50005), icon=control.addonIcon(), time=10000)
        k+=1

    return True
    
def getSiteItems():
    logger.logInfo('called function')
    return callJsonApi(config.uri.get('items'), base_url=control.setting('basePath'), useCache=False)
    
def getCategories():
    logger.logInfo('called function')
    data = []
    uniq = {}
    categories = logger.logInfo(showDB.getAllCategories())
    for cat in categories:
        for c in cat.split('|'):
            if c.strip() != '': uniq[c]=1
                
    for cat in sorted(uniq.keys()):
        data.append({'id': cat, 'name': cat})

    return data
    
def getMyList():
    logger.logInfo('called function')
    data = showDB.getMyList()
    return sorted(data, key=lambda item: item['title'] if 'title' in item else item['name'], reverse=False)

def getMylistShowLastEpisodes():
    logger.logInfo('called function')
    data = []
    # key = 'mylistShowLastEpisodes-%s' % datetime.datetime.now().strftime('%Y%m%d%H')
    # logger.logInfo(key)
    # if cache.shortCache.get(key) == '':
    shows = showDB.getMyList()
    if len(shows) > 0:
        for show in shows:
            (episodes, n) = getEpisodesPerPage(show.get('id'), 1, 1)
            data.append(episodes.pop())

    #         cache.shortCache.set(key, json.dumps(data))
    # else:
    #     data = json.loads(cache.shortCache.get(key).replace('\\\'', '\''))

    return sorted(data, key=lambda item: item['title'] if 'title' in item else item['name'], reverse=False)
    
def getSettings(refresh=False):
    logger.logInfo('called function')
    settings = {}
    settingJson = control.setting('iwanttfc_settings').replace('\\\'', '\'')

    lastUpdate = int(float(control.setting('iwanttfc_settings_timestamp'))) if control.setting('iwanttfc_settings_timestamp') != '' else 0
    if time.time() - lastUpdate > config.settingsRefreshRate: refresh = True

    if not settingJson or refresh == True:
        logger.logDebug('Update settings')
        html = callServiceApi(config.uri.get('base'), base_url=config.websiteUrl, useCache=False)
        scriptUrlMatch = re.compile('<script src="(((https://.+/c/6/)catalog/.+/)script\.js)"></script>', re.IGNORECASE).search(html)
        if scriptUrlMatch:
            scriptUrl = scriptUrlMatch.group(1)
            catalogBasePath = scriptUrlMatch.group(2)
            basePath = scriptUrlMatch.group(3)
            control.setSetting('catalogBasePath', catalogBasePath);
            control.setSetting('basePath', basePath);
            scriptContent = callServiceApi(scriptUrl, base_url='', useCache=False)
            settingMatch = re.compile('var index = (\{[^\r\n]+\});', re.IGNORECASE).search(scriptContent)
            if settingMatch:
                settingJson = re.sub(r"<\w+>", "%s", settingMatch.group(1))
                control.setSetting('iwanttfc_settings', settingJson)
                control.setSetting('iwanttfc_settings_timestamp', str(time.time()))
                settings = json.loads(settingJson)
    else:
        logger.logDebug('Retrieve cached settings')
        settingJson = control.setting('iwanttfc_settings').replace('\\\'', '\'')
        settings = json.loads(settingJson)

    return settings

def loadSettings(refresh=False):
    logger.logInfo('called function')
    config.uri.update(getSettings(refresh))
    logger.logDebug(config.uri)

def getHomeCatalog(refresh=False):
    logger.logInfo('called function')
    catalogKey = 'catalog-%s' % datetime.datetime.now().strftime('%Y%m%d%H')
    catalogJson = cache.getCached(cache.shortCache, catalogKey, lambda: json.dumps(callJsonApi(config.uri.get('catalog'), base_url=control.setting('basePath'), useCache=False)), refresh)
    return {} if catalogJson is None else json.loads(catalogJson)

def getWebsiteHomeSections():
    logger.logInfo('called function')
    data = []
    catalog = getHomeCatalog(True)
    for section in catalog.get('home', {}):
        header = section.get('title', {}).get('en', '')
        if len(header):
            sectionName = header
            exceptSections = []
            if sectionName not in exceptSections:
                data.append({'id' : cache.generateHashKey(sectionName), 'name' : sectionName}) #, 'url' : '/', 'fanart' : ''})
    return data
    
def getWebsiteSectionContent(sectionId, page=1, itemsPerPage=8):
    logger.logInfo('called function')
    page -= 1
    data = []
    section = ''
    
    catalog = getHomeCatalog()
    for section in catalog.get('home', {}):
        header = section.get('title', {}).get('en', '')
        if len(header):
            sectionName = header
            if cache.generateHashKey(sectionName) == sectionId: break
    
    index = itemsPerPage * page
    containsShows = True
    i = 0
    for s in section.get('items'):
        i += 1
        if i > index:
            data.append(getItemData(s.get('id')))
                
        if i >= (index + itemsPerPage):
            break
   
    # episodeDB.get([d.get('id') for d in data])
    return removeDuplicates(sorted(data, key=lambda item: item['dateaired'] if item.get('type') == 'episode' else item['name'], reverse=True if containsShows == False else False))
    
def removeDuplicates(list):
    newList = []
    uniq = {}
    for d in list:
        key = '%s_%s'% (d.get('type'), str(d.get('id')))
        if key not in uniq: newList.append(d)
        uniq[key]=1
    return newList
    
def getItemData(id):
    logger.logInfo('called function with param (%s)' % (id))
    return getShow(id)

""" def extractWebsiteSectionEpisodeData(url, html):
    logger.logInfo('called function with param (%s, %s)' % (url, html))
    episodeId = re.compile('/([0-9]+)/', re.IGNORECASE).search(url).group(1)
    res = episodeDB.get(episodeId)
    if len(res) == 1:
        return res[0]
    else:
        showName = common.replaceHTMLCodes(common.parseDOM(html, "h3", attrs = { 'class' : 'show-cover-thumb-title-mobile' })[0])
        try:image = common.parseDOM(html, "div", attrs = { 'class' : 'show-cover' }, ret = 'data-src')[0]
        except:image = common.parseDOM(html, "div", attrs = { 'class' : 'show-cover lazy' }, ret = 'data-src')[0]
        dateAired = common.parseDOM(html, "h4", attrs = { 'class' : 'show-cover-thumb-aired-mobile' })
        
        year = ''
        episodeNumber = 0
        description = ''
        episodeName = ''
        
        if dateAired and len(dateAired) > 0:
            episodeName = dateAired[0]
            year = episodeName.split(', ')[1]

        try:
            datePublished = datetime.datetime.strptime(episodeName, '%B %d, %Y')
        except:
            datePublished = datetime.datetime(*(time.strptime(episodeName, '%b %d, %Y')[0:6]))
            
        return {
            'id' : int(episodeId), 
            'parentid' : -1,
            'parentname' : '',
            'title' : common.replaceHTMLCodes('%s - %s' % (showName, episodeName)), 
            'show' : showName, 
            'image' : image, 
            'episodenumber' : episodeNumber,
            'url' : url, 
            'description' : '',
            'shortdescription' : '',
            'dateaired' : episodeName,
            'date' : datePublished.strftime('%Y-%m-%d'),
            'year' : year,
            'fanart' : image,
            'ltype' : 'episode',
            'type' : 'episode'
            } """

def getShows(categoryId):
    logger.logInfo('called function with param (%s)' % categoryId)
    return showDB.searchByCategory(categoryId)

def getShow(id, withEpisodes=False):
    logger.logInfo('called function with param (%s, %s)' % (id, withEpisodes)) 
    data = {}
    
    res = showDB.get(id)
    if withEpisodes is False and len(res) == 1:
        actors = castDB.getByShow(id)
        for actor in actors:
            actor['cadtid'] = actor.get('actorid')
        res[0]['actors'] = actors
        data = res[0]
    else:
        show = callJsonApi(config.uri.get('item') % id, base_url=control.setting('basePath'), useCache=False)
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
                label = callJsonApi(config.uri.get('value') % genre, base_url=control.setting('basePath'), useCache=True)
                if 'en' in label:
                    genreLabels.append(label.get('en'))
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
                    actor[0]['order'] = i
                    actors.append(actor[0])
                else:
                    cast = callJsonApi(config.uri.get('value') % castId, base_url=control.setting('basePath'), useCache=True)
                    logger.logInfo(cast)
                    castName = unicodetoascii(cast.get('en', ''))
                    castUrl = ''
                    castImage = ''
                    actors.append({
                        'castid': castId,
                        'showid': id,
                        'name': castName,
                        'role': '',
                        'thumbnail': castImage,
                        'order': i,
                        'url': castUrl
                        })
                    castDB.set(actors)
                i+=1

            data = {
                'id' : id,
                'name' : name,
                'parentid' : '|'.join(genres),
                'parentname' : '|'.join(genreLabels),
                'logo' : image,
                'image' : image,
                'fanart' : fanart,
                'banner' : fanart,
                'url' : id,
                'description' : description,
                'shortdescription' : description,
                'year' : year,
                'nbEpisodes' : len(show.get('children', [])) if type != 'movie' else 1,
                'episodes' : show.get('children', []),
                'casts' : actors,
                'ltype' : type,
                'duration' : 0,
                'views' : 0,
                'rating' : 0,
                'votes' : 0,
                'mylist' : res[0].get('mylist', 'false') if len(res) == 1 else 'false',
                'type': type,
                'parentalAdvisory' : 'true' if show.get('ratings', {}).get('us', '') == 'PG' else 'false',
                'media' : show.get('media', False),
                'streamID' : show.get('streamID', False)
                }
            showDB.set(data)
        else:
            logger.logWarning('Error on show %s: %s' % (id, 'not found'))
    
    return data

def getShowWithEpisodes(showId):
    logger.logInfo('called function with param (%s)' % (showId))
    data = {
        'nbEpisodes': 0,
        'episodes': []
        }

    show = getShow(showId, True)
    for e in show.get('episodes'):
        res = episodeDB.get(e.get('id'))
        if len(res) == 0:
            data['episodes'].append(getEpisode(e.get('id'), show))
        else:
            data['episodes'].append(res[0])
        data['nbEpisodes']+=1

    show['episodes'] = data['episodes']
    show['nbEpisodes'] = data['nbEpisodes']

    return show
      
def getEpisodesPerPage(showId, page=1, itemsPerPage=8, order='desc'):
    logger.logInfo('called function with param (%s, %s, %s)' % (showId, page, itemsPerPage))
    data = []
    
    show = getShowWithEpisodes(showId)

    hasNextPage = False

    if show:
        nbEpisodes = show.get('nbEpisodes', 0)
        
        # if movie or special
        if show.get('ltype', '') == 'movie':
            logger.logInfo('movie')
            url = showId
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
                    'id' : episodeId,
                    'title' : show.get('name'),
                    'show' : show.get('name'),
                    'image' : show.get('image'),
                    'episodenumber' : 1,
                    'description' : show.get('description'),
                    'shortdescription' : show.get('description'),
                    'dateaired' : '',
                    'date' : '',
                    'year' : show.get('year'),
                    'fanart' : show.get('fanart'),
                    'showObj' : show,
                    'ltype' : show.get('ltype', 'show'),
                    'duration' : 0,
                    'views' : 0,
                    'rating' : 0,
                    'votes' : 0,
                    'type' : 'episode'
                    }
                episodeDB.set(e)
                data.append(e)
        else:
            logger.logInfo('show')
            episodes = sorted(show.get('episodes'), key=lambda item: item['title'], reverse=True if order == 'desc' else False)

            # Calculating episode index according to page and items per page
            episodeIndex = (page * 1 - 1) * itemsPerPage

            for index in range(episodeIndex, episodeIndex+itemsPerPage, 1):
                if index >= nbEpisodes:
                    break

                episodeData = episodes[index]
                url = episodeData.get('url')
                episodeId = episodeData.get('id')
                res = episodeDB.get(episodeId)
                if len(res) == 1:
                    e = res[0]
                    # Update title value with episode number
                    if episodeData:
                        e['title'] = episodeData.get('title')
                        e['episodenumber'] = episodeData.get('episodenumber')
                        e['showObj'] = show
                    data.append(e)
                else:
                    episode = callJsonApi(config.uri.get('item') % episodeData.get('id'), base_url = control.setting('basePath'), useCache = False)
                    image = control.setting('basePath') + config.uri.get('images') % episode.get('thumbnail') if episode.get('thumbnail', '') != '' else ''
                    description = unicodetoascii(episode.get('description', {}).get('en', ''))
                    e = {
                        'id' : episodeData.get('id'),
                        'title' : unicodetoascii(episode.get('title', {}).get('en', episodeData.get('id'))),
                        'parentid' : showId,
                        'show' : show.get('name', ''),
                        'image' : image,
                        'fanart' : show.get('fanart', ''),
                        'episodenumber' : episode.get('episode', 0),
                        'url' : url,
                        'description' : description,
                        'shortdescription' : description,
                        'dateaired' : '',
                        'date' : '',
                        'year' : show.get('year', ''),
                        'parentalAdvisory' : show.get('parentalAdvisory'),
                        'showObj' : show,
                        'ltype' : show.get('ltype', 'show'),
                        'type' : 'episode'
                        }
                    episodeDB.set(e)
                    data.append(e)

    # return (sorted(data, key=lambda episode: episode['title'], reverse=True), hasNextPage)
    return (data, hasNextPage)
         
def getEpisode(id, show={}):
    logger.logInfo('called function with param (%s)' % id)
    data = {}
    
    episode = callJsonApi(config.uri.get('item') % id, base_url = control.setting('basePath'), useCache = False)
    if episode.get('id', False):
        parent = episode.get('parents', []).pop(0)
        if show == {} and type(parent) is dict:
            show = getShow(parent.get('id', ''))
        image = control.setting('basePath') + config.uri.get('images') % episode.get('thumbnail') if episode.get('thumbnail', '') != '' else ''
        description = unicodetoascii(episode.get('description', {}).get('en', ''))
        data = {
            'id' : id,
            'title' : unicodetoascii(episode.get('title', {}).get('en', id)),
            'parentid' : show.get('id'),
            'show' : show.get('name', ''),
            'image' : image,
            'fanart' : show.get('fanart', ''),
            'episodenumber' : episode.get('episode', 0),
            'url' : id,
            'description' : description,
            'shortdescription' : description,
            'dateaired' : '',
            'date' : '',
            'year' : show.get('year', ''),
            'parentalAdvisory' : show.get('parentalAdvisory'),
            'showObj' : show,
            'ltype' : show.get('ltype', 'show'),
            'type' : 'episode',
            'media' : episode.get('media')
            }
        res = episodeDB.get(id)
        if len(res) == 1:
            res[0].update(data)
            data = res[0]
        episodeDB.set(data)
        data['media']['id'] = episode.get('mediaID')
                
    return data

def getEpisodeFromShow(id):
    logger.logInfo('called function with param (%s)' % id)
    data = {}
    
    show = getShow(id, True)
    if show.get('id', False):
        data = {
            'id' : id,
            'title' : show.get('name'),
            'parentid' : show.get('id'),
            'show' : show.get('name', ''),
            'image' : show.get('image'),
            'fanart' : show.get('fanart', ''),
            'episodenumber' : 1,
            'url' : id,
            'description' : show.get('description'),
            'shortdescription' : show.get('description'),
            'dateaired' : '',
            'date' : '',
            'year' : show.get('year', ''),
            'parentalAdvisory' : show.get('parentalAdvisory'),
            'showObj' : show,
            'ltype' : show.get('ltype', 'show'),
            'type' : 'episode',
            'media' : show.get('media')
            }
        data['media']['id'] = show.get('mediaID', '')
                
    return data

def getEpisodeFromLiveStream(id):
    logger.logInfo('called function with param (%s)' % id)
    data = {}
    
    show = getShow(id, True)
    if show.get('streamID', False):
        stream = callJsonApi(
            config.uri.get('livestream') % show.get('streamID'),
            headers=[
                ('Cookie', 'UserAuthentication='+control.setting('iWantUserAuthentication')),
                ('UserAuthentication', control.setting('iWantUserAuthentication')),
                ('Referer', config.websiteSecuredUrl+'/'),
                ('Origin', config.websiteSecuredUrl),
                ('Pragma', 'no-cache'),
                ('Sec-Fetch-Dest', 'empty'),
                ('Sec-Fetch-Mode', 'cors'),
                ('Sec-Fetch-Site', 'same-orig')
                ],
            useCache = False
            )
        if 'kid' in stream:
            data = {
                'id' : id,
                'title' : show.get('name'),
                'parentid' : show.get('id'),
                'show' : show.get('name', ''),
                'image' : show.get('image'),
                'fanart' : show.get('fanart', ''),
                'episodenumber' : 1,
                'url' : id,
                'description' : show.get('description'),
                'shortdescription' : show.get('description'),
                'dateaired' : '',
                'date' : '',
                'year' : show.get('year', ''),
                'parentalAdvisory' : show.get('parentalAdvisory'),
                'showObj' : show,
                'ltype' : show.get('ltype', 'show'),
                'type' : 'episode',
                'media' : {}
                }
            if 'm3u8' in stream: data['media']['m3u8s'] = [stream['m3u8']]
            if 'mpd' in stream: data['media']['mpds'] = [stream['mpd']]
            data['media']['id'] = show.get('streamID', stream.get('streamID', ''))
                
    return data
    
def getUserInfo():
    logger.logInfo('called function')
    url = config.uri.get('profile')
    html = callJsonApi(url, params={'data': control.setting('iWantUserAuthentication')}, base_url='', useCache = False)
    
    # Retrieve info from website
    profileHeader = common.parseDOM(html, 'div', attrs = {'class' : 'profile_header'})
    name = common.parseDOM(profileHeader, 'div', attrs = {'class' : 'name'})[0]
    state = common.parseDOM(profileHeader, 'div', attrs = {'class' : 'name'})[0]
    memberSince = common.parseDOM(profileHeader, 'div', attrs = {'class' : 'date'})[0]    
    
    # Retrieve info from account JSON string
    user = json.loads(control.setting('accountJSON')).get('profile')
    
    return {
        'name' : name,
        'firstName' : user.get('firstName', ''),
        'lastName' : user.get('lastName', ''),
        'email' : user.get('email', ''),
        'state' : state,
        'country' : user.get('country', ''),
        'memberSince' : memberSince.replace('MEMBER SINCE ', '')
    }
    
def getUserSubscription():
    logger.logInfo('called function')
    url = config.uri.get('profileDetails')
    subscription = callJsonApi(url, useCache=False)
    logger.logInfo(subscription)
    first_cap_re = re.compile('(.)([A-Z][a-z]+)')
        
    subKeys = ['Type', 'SubscriptionName', 'SubscriptionStatus', 'ActivationDate', 'ExpirationDate', 'BillingPeriod', 'AutoRenewal']
    details = ''
    if 'Details' in subscription:
        for d in subscription['Details']:
            for key in subKeys:
                label = first_cap_re.sub(r'\1 \2', key)
                if key in d:
                    value = ''
                    if isinstance(d[key], (bool)):
                        value = 'ACTIVE' if d[key] == True else 'NON ACTIVE'
                    else:
                        value = d[key]
                    details += "%s: %s\n" % (label, value)
            details += "\n"
    return {
            'details' : details
        }
    
def getUserTransactions():
    logger.logInfo('called function')
    TAG_HTML = re.compile('<[^>]+>')

    data = []
    url = config.uri.get('profile')
    html = callServiceApi(url, useCache = False)
    
    transactionsHtml = common.parseDOM(html, 'div', attrs = {'id' : 'transactions'})
    transactions = common.parseDOM(common.parseDOM(transactionsHtml, 'tbody'), 'tr')
    
    header = []
    headers = common.parseDOM(common.parseDOM(transactionsHtml, 'thead'), 'th')
    for h in headers:
        header.append(h)
    
    for transaction in transactions:
        columns = common.parseDOM(transaction, 'td', attrs = {'class' : 'loader'})
        if len(columns) > 0:
            continue
        
        columns = common.parseDOM(transaction.replace('<td></td>', '<td>-</td>'), 'td')
        t = ''
        i = 0
        
        for c in columns:
            value = '-'
            if not TAG_HTML.search(c):
                value = c
            t += "%s: %s\n" % (header[i], value)
            i+=1
        data.append(t)
                
    return data
    
def addToMyList(id, name, ltype, type):
    logger.logInfo('called function with param (%s, %s, %s, %s)' % (id, name, ltype, type))
    show = getShow(id)
    show['mylist'] = 'true'
    if showDB.update(show):
        control.showNotification(control.lang(57053) % name)
    else:
        control.showNotification(control.lang(57054) % name)

def removeFromMyList(id, name, ltype, type):
    logger.logInfo('called function with param (%s, %s, %s, %s)' % (id, name, ltype, type))
    show = getShow(id)
    show['mylist'] = 'false'
    if showDB.update(show):
        control.showNotification(control.lang(57053) % name)
    else:
        control.showNotification(control.lang(57054) % name)
    
def showExportedShowsToLibrary():
    data = []
    temp = {}
    exported = libraryDB.getAll()
    for d in exported:
        if 'id' in d:
            temp[d.get('id')] = d
    if len(temp) > 0:
        shows = showDB.get(temp.keys())
        for s in shows:
            temp[s.get('id')].update(s)
            data.append(temp.get(s.get('id')))
    return data

def removeFromLibrary(id, name):
    data = libraryDB.get(int(id))
    if len(data) > 0:
        if logger.logInfo(libraryDB.delete(data[0])):
            path = os.path.join(control.showsLibPath, name, '')
            logger.logInfo(path)
            if logger.logInfo(control.pathExists(path)): 
                if control.confirm(control.lang(57041), line1=control.lang(57042), title=name) == False:
                    control.deleteFolder(path, True)
            control.showNotification(control.lang(57043) % name, control.lang(50010))
        else:
            control.showNotification(control.lang(57044), control.lang(50004))
    else:
        control.showNotification(control.lang(57045), control.lang(50001))


def addToLibrary(id, name, parentId=-1, year='', updateOnly=False):
    logger.logInfo('called function with param (%s, %s, %s, %s)' % (id, name, parentId, year))
    from resources.lib.indexers import navigator
    status = True
    updated = False
    nbUpdated = 0
    nbEpisodes = int(control.setting('exportLastNbEpisodes'))
    (episodes, n) = getEpisodesPerPage(id, page=1, itemsPerPage=nbEpisodes)
    
    if len(episodes) > 0:
    
        path = os.path.join(control.showsLibPath, name)
        control.makePath(path)
        
        # Show NFO file
        try: 
            e = episodes[0]
            show = e.get('showObj')
            res = libraryDB.get(show.get('id'))
            lib = res[0] if len(res) == 1 else {}
            control.writeFile(logger.logNotice(os.path.join(path, 'tvshow.nfo')), generateShowNFO(show, path).encode('utf-8'))
        except Exception as err:
            logger.logError(err)
            status = False
        
        if status == True:
            
            mostRecentDate = lastDate = lib.get('date', datetime.datetime(1900, 1, 1))
            lastCheck = lib.get('lastCheck', datetime.datetime(1900, 1, 1))
            logger.logNotice('last check date : %s' % lastCheck.strftime('%Y-%m-%d %H:%M:%S'))
            for e in sorted(episodes, key=lambda item: item['date'], reverse=False):
                filePath = os.path.join(path, '%s.strm' % e.get('title'))

                logger.logNotice('episode date : %s' % e.get('date'))
                try:
                    episodeDate = datetime.datetime.strptime(e.get('date'), '%Y-%m-%d')
                except TypeError:
                    episodeDate = datetime.datetime(*(time.strptime(e.get('date'), '%Y-%m-%d')[0:6]))
                
                if lastDate.date() < episodeDate.date():
                    updated = True
                    nbUpdated += 1
                    if mostRecentDate.date() < episodeDate.date(): mostRecentDate = episodeDate
                    
                if not updateOnly or updated:
                    try:
                        # Episode STRM / NFO files
                        control.writeFile(logger.logNotice(os.path.join(path, '%s.nfo' % e.get('title'))), generateEpisodeNFO(e, path, filePath).encode('utf-8'))
                        control.writeFile(logger.logNotice(filePath), navigator.navigator().generateActionUrl(str(e.get('id')), config.PLAY, '%s - %s' % (e.get('show'), e.get('dateaired')), e.get('image')))
                    except Exception as err:
                        logger.logError(err)
                        status = False
                        break
    else: 
        status = False
            
    if status == True: 
        if not updateOnly: control.showNotification(control.lang(57034) % name, control.lang(50010))
        libraryDB.set({'id' : int(show.get('id')), 
            'name' : show.get('name'), 
            'parentid' : int(show.get('parentid')),
            'year' : show.get('year'),
            'date' : mostRecentDate.strftime('%Y-%m-%d')
            })
    else: 
        if not updateOnly: control.showNotification(control.lang(57033), control.lang(50004))
    return {'status': status, 'updated': updated, 'nb': nbUpdated}

def generateShowNFO(info, path):
    logger.logInfo('called function')
    nfoString = ''
    nfoString += '<title>%s</title>' % info.get('name')
    nfoString += '<sorttitle>%s</sorttitle>' % info.get('name')
    nfoString += '<episode>%s</episode>' % info.get('nbEpisodes')
    nfoString += '<plot>%s</plot>' % info.get('description')
    nfoString += '<aired>%s</aired>' % info.get('dateaired')
    nfoString += '<year>%s</year>' % info.get('year')
    nfoString += '<thumb aspect="poster">%s</thumb>' % info.get('image')
    nfoString += '<fanart url=""><thumb dim="1280x720" colors="" preview="%s">%s</thumb></fanart>' % (info.get('fanart'), info.get('fanart'))
    nfoString += '<genre>%s</genre>' % info.get('parentname')
    nfoString += '<path>%s</path>' % path
    nfoString += '<filenameandpath></filenameandpath>'
    nfoString += '<basepath>%s</basepath>' % path
    for c in info.get('casts', []):
        nfoString += '<actor><name>%s</name><order>%d</order><thumb>%s</thumb></actor>' % (c.get('name'), c.get('order'), c.get('thumbnail'))
    
    return u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?> \
<!-- created on %s - by TFC.tv addon --> \
<tvshow> \
    %s \
</tvshow>' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nfoString)
    
def generateEpisodeNFO(info, path, filePath):
    logger.logInfo('called function')
    nfoString = ''
    nfoString += '<title>%s</title>' % info.get('title')
    nfoString += '<showtitle>%s</showtitle>' % info.get('show')
    nfoString += '<sorttitle>%s</sorttitle>' % info.get('dateaired')
    nfoString += '<episode>%s</episode>' % info.get('episodenumber')
    nfoString += '<plot>%s</plot>' % info.get('description')
    nfoString += '<aired>%s</aired>' % info.get('dateaired')
    nfoString += '<year>%s</year>' % info.get('year')
    nfoString += '<thumb>%s</thumb>' % info.get('image')
    nfoString += '<art><banner>%s</banner><fanart>%s</fanart></art>' % (info.get('fanart'), info.get('fanart'))
    nfoString += '<path>%s</path>' % path
    nfoString += '<filenameandpath>%s</filenameandpath>' % filePath
    nfoString += '<basepath>%s</basepath>' % filePath
    nfoString += '<studio>ABS-CBN</studio>'
    
    return u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?> \
<!-- created on %s - by TFC.tv addon --> \
<episodedetails> \
    %s \
</episodedetails>' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nfoString)

def checkLibraryUpdates(quiet=False):
    logger.logInfo('called function')
    items = libraryDB.getAll()
    for show in items:
        logger.logNotice('check for update for show %s' % show.get('name'))
        result = addToLibrary(show.get('id'), show.get('name'), show.get('parentid'), show.get('year'), updateOnly=True)
        if result.get('updated') == True:
            logger.logNotice('Updated %s episodes' % str(result.get('nb')))
            if not quiet: control.showNotification(control.lang(57037) % (str(result.get('nb')), show.get('name')), control.lang(50011))
        else:
            logger.logNotice('No updates for show %s' % show.get('name'))
    return True
    
def enterSearch(category, type):
    logger.logInfo('called function with params (%s, %s)' % (category, type))
    data = []
    search = control.inputText(control.lang(50204)).strip()
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
        control.showNotification(control.lang(57046), control.lang(50001))
    return data

def getUserName(html=False):
    logger.logInfo('called function')
    userName = ''
    if html == False:
        html = callServiceApi(config.uri.get('profile'), headers=[('Referer', config.websiteSecuredUrl+'/')], base_url=config.websiteSecuredUrl, useCache=False)
    avatar = common.parseDOM(html, "div", attrs = { 'class' : 'avatar' })[0]
    if len(avatar) > 0:
        avatarName = common.parseDOM(avatar, "img", ret = 'alt')
        if len(avatarName) > 0:
            userName = avatarName[0]
        logger.logInfo(userName)
    return userName

def enterCredentials():
    logger.logInfo('called function')
    email = control.inputText(control.lang(50400), control.setting('emailAddress'))
    password = ''
    i = 1
    while i < 3 and password == '':
        password = control.inputPassword(control.lang(50401))
        i+=1
    logger.logNotice('%s - %s' % (email, password))
    control.setSetting('emailAddress', email)
    control.setSetting('password', password)
    return login(False, email, password)
    
def checkAccountChange(forceSignIn=False):
    logger.logInfo('called function')
    email = control.setting('emailAddress')
    password = control.setting('password')
    hash = hashlib.sha1(email + password).hexdigest()
    hashFile = os.path.join(control.dataPath, 'a.tmp')
    savedHash = ''
    accountChanged = False
    logged = False
    loginSuccess = False
    
    if os.path.exists(hashFile):
        if forceSignIn == True: 
            os.unlink(hashFile)
        else: 
            with open(hashFile) as f:
                savedHash = f.read()
                f.close()
                
    if savedHash != hash:
        accountChanged = True
        logout()
        logged = True
    elif not isLoggedIn():
        logger.logInfo('Not logged in')
        logged = True
    
    if logged:
        cleanCookies(False)
        loginSuccess = login()
        if loginSuccess == True and os.path.exists(control.dataPath):
            with open(hashFile, 'w') as f:
                f.write(hash)
                f.close()
        elif os.path.exists(hashFile)==True: 
            os.unlink(hashFile)
        
    return (accountChanged, loginSuccess)
    
def login(quiet=False, login=False, password=False):
    logger.logInfo('called function')
    signedIntoWebsite = loginToWebsite(quiet, login, password)
    return signedIntoWebsite
    
def isLoggedIn():
    logger.logInfo('called function')
    global Logged
    if Logged == False and control.setting('iWantUserAuthentication') and control.setting('iWantUserAuthentication') != '':
        userAuth = callJsonApi(
            config.uri.get('loginStatus'),
            headers=[
                ('Content-Type', 'application/x-www-form-urlencoded'),
                ('Cookie', 'UserAuthentication='+control.setting('iWantUserAuthentication')),
                ('UserAuthentication', control.setting('iWantUserAuthentication')),
                ('Referer', config.websiteSecuredUrl+'/'),
                ('Origin', config.websiteSecuredUrl),
                ('Pragma', 'no-cache'),
                ('Sec-Fetch-Dest', 'empty'),
                ('Sec-Fetch-Mode', 'cors'),
                ('Sec-Fetch-Site', 'same-orig')
                ],
            base_url=config.websiteSecuredUrl,
            useCache=False
            )
        if userAuth.get('status') == 'OK':
            Logged = True  
            control.setSetting('loginSession', json.dumps(userAuth))
        else: 
            Logged = False
    return Logged
    
def loginToWebsite(quiet=False, login=False, password=False):
    logger.logInfo('called function')
    logged = False

    if control.setting('loginType') == "Facebook":
        token = control.setting('FBAccessToken')
        if token != None and token != '' and checkFacebookToken(token) == False:
            token = ''
            control.setSetting('FBAccessToken', '')
        logged = loginWithFacebook(quiet, token)
    else:
        if control.setting('emailAddress') != '':
            emailAddress = control.setting('emailAddress')
            password = control.setting('password')
            params = { "email" : emailAddress, "password": password }
            authInfos = callJsonApi(config.uri.get('login'), 
                params, 
                headers = [
                    ('Referer', config.websiteSecuredUrl+'/'),
                    ('Origin', config.websiteSecuredUrl),
                    ('Pragma', 'no-cache'),
                    ('Sec-Fetch-Dest', 'empty'),
                    ('Sec-Fetch-Mode', 'cors'),
                    ('Sec-Fetch-Site', 'same-orig')
                    ], 
                base_url = config.websiteSecuredUrl, 
                useCache = False
                )
            if authInfos.get('status') == 'OK':
                control.setSetting('iWantRefreshToken', authInfos.get('refreshToken'))
                control.setSetting('iWantUserAuthentication', authInfos.get('UserAuthentication'))
            if not isLoggedIn() and quiet == False:
                logger.logError('Authentification failed')
                control.showNotification(control.lang(57024), control.lang(50006))
            else:
                logged = True
                logger.logNotice('You are now logged in')
                control.showNotification(control.lang(57009) % '', control.lang(50007))
                if control.setting('generateNewFingerprintID') == 'true':
                    generateNewFingerprintID()
        else:
            control.showNotification(control.lang(50205), control.lang(50204))
    return logged

def checkFacebookToken(accessToken=''):
    logger.logInfo('called function')
    info = callJsonApi(config.Facebook.get('info'), params = {'fields' : 'name,first_name,last_name,email', 'access_token' : accessToken}, headers=[], base_url='', useCache=False)
    if 'name' in info:
        return True
    return False

def loginWithFacebook(quiet=False, accessToken=''):
    logger.logInfo('called function')
    logged = False
    token = None
    accountJSON = json.loads(control.setting('accountJSON')) if control.setting('accountJSON') else {}

    if control.setting('FBAppID') != '' or control.setting('FBClientToken') != '':

        appIdentifier = '%s|%s' % (control.setting('FBAppID'), control.setting('FBClientToken'))
        control.showNotification(control.lang(56024), control.lang(50005))
        if accessToken == '':
            login = callJsonApi(config.Facebook.get('login'), params = {'access_token' : appIdentifier}, headers=[], base_url='', useCache=False)
            if 'code' in login and 'user_code' in login:
                control.alert(control.lang(57048) % login.get('verification_uri'), line1='[B]%s[/B]' % login.get('user_code'), line2=control.lang(57049), title=control.lang(56024))
                i = 1
                expired = False
                while i < 5 and token == None and expired == False:
                    time.sleep(login.get('interval', 5))
                    status = callJsonApi(config.Facebook.get('status'), params = {'access_token' : appIdentifier, 'code' : login.get('code')}, headers=[], base_url='', useCache=False)
                    if 'access_token' in status:
                        info = callJsonApi(config.Facebook.get('info'), params = {'fields' : 'name,first_name,last_name,email', 'access_token' : status.get('access_token')}, headers=[], base_url='', useCache=False)
                        if 'name' in info:
                            accountJSON = {'name' : info.get('name', ''), 'firstName' : info.get('first_name', ''), 'lastName': info.get('last_name', ''), 'email': info.get('email', '')}
                            control.setSetting('accountJSON', json.dumps(accountJSON))
                            token = status.get('access_token')
                    elif 'error' in status and status.get('error').get('error_subcode', 0) == 1349152:
                        expired = True
                    i+=1
        else: 
            token = accessToken

        if token != None:
            html = callServiceApi(config.uri.get('socialLogin') % token, headers=[('Referer', config.websiteSecuredUrl+'/')], base_url=config.websiteSecuredUrl, useCache=False)
            logged = isLoggedIn()

        if quiet == False:
            if logged == True:
                logger.logNotice('You are now logged in')
                control.setSetting('FBAccessToken', token)
                control.showNotification(control.lang(57009) % accountJSON.get('name'), control.lang(50007))
            else:
                logger.logError('Authentification failed')
                control.showNotification(control.lang(57024), control.lang(50006))
    else:
        control.showMessage(control.lang(57052), control.lang(50006))

    return logged

def getFromCookieByName(string, startWith=False):
    logger.logInfo('called function')
    global cookieJar
    cookieObj = None
    
    for c in cookieJar:
        if (startWith and c.name.startswith(string)) or (not startWith and c.name == string) :
            cookieObj = c
            break
                
    return cookieObj
    
def getCookieContent(filter=False, exceptFilter=False):
    logger.logInfo('called function')
    global cookieJar
    cookie = []
    for c in cookieJar:
        if (filter and c.name not in filter) or (exceptFilter and c.name in exceptFilter):
            continue
        cookie.append('%s=%s' % (c.name, c.value))
    return cookie

def generateNewFingerprintID(previous=False):
    logger.logInfo('called function')
    from random import randint
    if previous == False:
        control.setSetting('previousFingerprintID', control.setting('fingerprintID'))
    else:
        control.setSetting('previousFingerprintID', previous)
    control.setSetting('fingerprintID', hashlib.md5(control.setting('emailAddress')+str(randint(0, 1000000))).hexdigest())
    if control.setting('generateNewFingerprintID') == 'true':
        control.setSetting('generateNewFingerprintID', 'false')
    return True
    
def logout(quiet=True):
    logger.logInfo('called function')
    if quiet == False and isLoggedIn() == False:
        control.showNotification(control.lang(57000), control.lang(50005))
    # callServiceApi(config.uri.get('logout'), headers = [('Referer', config.websiteUrl + config.uri.get('base'))], base_url = config.websiteUrl, useCache = False)
    control.setSetting('FBAccessToken', '')
    control.setSetting('iWantUserAuthentication', '')
    control.setSetting('iWantRefreshToken', '')
    cookieJar.clear()
    if quiet == False and isLoggedIn() == False:
        control.showNotification(control.lang(57010))
        control.exit()

def checkIfError(html):
    error = False
    message = ''
    if html == '' or html == None:
        error = True
        message = control.lang(57029)
    else:
        t = common.parseDOM(html, "title")
        if len(t) > 0:
            if 'Error' in t[0]:
                error = True
                message = t[0].split(' | ')[1]
    return { 'error' : error, 'message' : message }

def callServiceApi(path, params={}, headers=[], base_url=config.websiteUrl, useCache=True, jsonData=False, returnMessage=True):
    logger.logInfo('called function with param (%s)' % (path))
    global cookieJar
    
    res = {}
    cached = False
    toCache = False
    
    # No cache if full response required
    if returnMessage == False:
        useCache = False
    
    key = config.urlCachePrefix + cache.generateHashKey(base_url + path + urllib.urlencode(params))
    logger.logDebug('Key %s : %s - %s' % (key, base_url + path, params))
    
    if useCache == True:
        tmp = cache.shortCache.getMulti(key, ['url', 'timestamp'])
        if (tmp == '') or (tmp[0] == '') or (time.time()-float(tmp[1])>int(control.setting('cacheTTL'))*60):
            toCache = True
            logger.logInfo('No cache for (%s)' % key)
        else:
            cached = True
            res['message'] = logger.logDebug(tmp[0])
            logger.logInfo('Used cache for (%s)' % key)
    
    if cached is False:
        opener = urllib2.build_opener(urllib2.HTTPRedirectHandler(), urllib2.HTTPCookieProcessor(cookieJar))
        userAgent = config.userAgents[base_url] if base_url in config.userAgents else config.userAgents['default']
        headers.append(('User-Agent', userAgent))
        opener.addheaders = headers
        logger.logDebug('### Request headers, URL & params ###')
        logger.logDebug(headers)
        logger.logDebug('%s - %s' % (base_url + path, params))
        requestTimeOut = int(control.setting('requestTimeOut')) if control.setting('requestTimeOut') != '' else 20
        response = None
        
        try:
            if params:
                if jsonData == True:                    
                    request = urllib2.Request(base_url + path)
                    request.add_header('Content-Type', 'application/json')
                    response = opener.open(request, json.dumps(params), timeout = requestTimeOut)
                else:
                    data_encoded = urllib.urlencode(params)
                    response = opener.open(base_url + path, data_encoded, timeout = requestTimeOut)
            else:
                response = opener.open(base_url + path, timeout = requestTimeOut)
                
            logger.logDebug('### Response headers ###')
            logger.logDebug(response.geturl())
            logger.logDebug('### Response redirect URL ###')
            logger.logDebug(response.info())
            logger.logDebug('### Response ###')
            res['message'] = response.read() if response else ''
            res['status'] = int(response.getcode())
            res['headers'] = response.info()
            res['url'] = response.geturl()
            logger.logDebug(res)
        except (urllib2.URLError, ssl.SSLError) as e:
            logger.logError(e)
            message = '%s : %s' % (e, base_url + path)
            # message = "Connection timeout : " + base_url + path
            logger.logSevere(message)
            control.showNotification(message, control.lang(50004))
            # No internet connection error
            if 'Errno 11001' in message:
                logger.logError('Errno 11001 - No internet connection')
                control.showNotification(control.lang(57031), control.lang(50004), time=5000)
            toCache = False
            pass
        
        if toCache == True and res:
            value = res.get('message') if re.compile('application/json', re.IGNORECASE).search('|'.join(res['headers'].headers)) or re.compile('binary/octet-stream', re.IGNORECASE).search('|'.join(res['headers'].headers)) else repr(res.get('message'))
            cache.shortCache.setMulti(key, {'url': value, 'timestamp' : time.time()})
            logger.logDebug(res.get('message'))
            logger.logInfo('Stored in cache (%s) : %s' % (key, {'url': value, 'timestamp' : time.time()}))
    
    # Clear headers
    headers[:] = []
    
    if returnMessage == True:
        return res.get('message')
        
    return res

def callJsonApi(path, params={}, headers=[('X-Requested-With', 'XMLHttpRequest')], base_url=config.webserviceUrl, useCache=True, jsonData=False):
    logger.logInfo('called function')
    data = {}
    res = callServiceApi(path, params, headers, base_url, useCache, jsonData)
    try:
        data = json.loads(res) if res != '' else []
    except:
        pass
    return data
    
def checkProxy():
    if (control.setting('useProxy') == 'true'):
        url = control.setting('proxyCheckUrl') % (control.setting('proxyHost'), control.setting('proxyPort'))
        response = callServiceApi(url, base_url = '', useCache=False, returnMessage=False)
        logger.logDebug(response)
        if response.get('status', '') != 200:
            control.alert(control.lang(57028), title=control.lang(50004))
            return False
    return True
            
def unicodetoascii(text):
    try:
        return unidecode(text)
    except:
        logger.logError(text)
        return text
        
# This function is a workaround to fix an issue on cookies conflict between live stream and shows episodes
def cleanCookies(notify=True):
    logger.logInfo('called function')
    message = ''
    if os.path.exists(os.path.join(control.homePath, 'cache', 'cookies.dat'))==True:  
        logger.logInfo('cookies file FOUND (cache)')
        try: 
            os.unlink(os.path.join(control.homePath, 'cache', 'cookies.dat'))
            message = control.lang(57004)
        except: 
            message = control.lang(57005)
                
    elif os.path.exists(os.path.join(control.homePath, 'temp', 'cookies.dat'))==True:  
        logger.logInfo('cookies file FOUND (temp)')
        try: 
            os.unlink(os.path.join(control.homePath, 'temp', 'cookies.dat'))
            message = control.lang(57004)
        except: 
            message = control.lang(57005)
    elif os.path.exists(os.path.join(control.dataPath, config.cookieFileName))==True:  
        logger.logInfo('cookies file FOUND (profile)')
        try: 
            os.unlink(os.path.join(control.dataPath, config.cookieFileName))
            message = control.lang(57004)
        except: 
            message = control.lang(57005)
    else:
        message = control.lang(57006)
        
    if notify == True:
        control.showNotification(message)
    
#---------------------- MAIN ----------------------------------------
thisPlugin = int(sys.argv[1])
    
cookieJar = cookielib.CookieJar()
cookieFile = ''
cookieJarType = ''

if os.path.exists(control.dataPath):
    cookieFile = os.path.join(control.dataPath, config.cookieFileName)
    cookieJar = cookielib.LWPCookieJar(cookieFile)
    cookieJarType = 'LWPCookieJar'
    
if cookieJarType == 'LWPCookieJar':
    try:
        cookieJar.load()
    except:
        loginToWebsite()
    
if cookieJarType == 'LWPCookieJar':
    cookieJar.save()

loadSettings()