# -*- coding: utf-8 -*-

"""
Media playback module
"""

import re
from urllib.parse import quote
from resources import config
from resources.lib.libraries import control
from .catalog import getEpisode, getShow, episodeDB, showDB
from .auth import isLoggedIn, login
from .utils import checkProxy

logger = control.logger

try:
    import inputstreamhelper
except:
    inputstreamhelper = None

def playEpisode(episodeId, name, type, thumbnail, bandwidth=False):
    """Play an episode"""
    logger.logInfo('called function')
    thisPlugin = control.thisPlugin
    
    if checkProxy():
        # Check if logged in
        if control.setting('emailAddress') != '' and not isLoggedIn():
            control.showNotification(control.lang(37012), control.lang(30002))
            login()
                
        episodeDetails = getMediaInfo(episodeId, name, type, thumbnail, bandwidth)
        logger.logDebug(episodeDetails)
        if episodeDetails and 'errorCode' in episodeDetails and episodeDetails['errorCode'] == 0 and 'data' in episodeDetails:
            if 'preview' in episodeDetails['data'] and episodeDetails['data']['preview'] is True:
                control.infoDialog(control.lang(37025), control.lang(30002), time=5000)
            elif 'StatusMessage' in episodeDetails and episodeDetails['StatusMessage'] != '':
                control.showNotification(episodeDetails['StatusMessage'], control.lang(30009))
            
            url = control.setting('proxyStreamingUrl') % (control.setting('proxyHost'), control.setting('proxyPort'), quote(episodeDetails['data']['uri']), '') if not episodeDetails.get('disableProxy', False) and not episodeDetails.get('useDash', False) and (control.setting('useProxy') == 'true') else episodeDetails['data']['uri']
            kodiurl = url+'|Origin=%s&Referer=%s&User-Agent=%s&Sec-Fetch-Mode=cors' % (config.websiteUrl, config.websiteUrl+'/', config.userAgents['default'])
            if ('tfcmsl.akamaized.net' in url):
                kodiurl = kodiurl + '&Sec-Fetch-Dest=empty&Sec-Fetch-Site=cross-site'
            else:
                kodiurl = kodiurl + '&Accept=*/*,akamai/media-acceleration-sdk;b=1702200;v=1.2.2;p=javascript'
            liz = control.item(name, path=kodiurl)
            #liz = control.item(name, path=episodeDetails['data']['uri'])
            liz.setArt({'thumb': thumbnail, 'icon': "DefaultVideo.png"})
            liz.setInfo(type='video', infoLabels={
                'title': name,
                'sorttitle': episodeDetails['data']['dateaired'],
                'tvshowtitle': episodeDetails['data']['show'],
                'genre': episodeDetails['data']['parentname'],
                'episode': episodeDetails['data']['episodenumber'],
                'tracknumber': episodeDetails['data']['episodenumber'],
                'plot': episodeDetails['data']['plot'],
                'aired': episodeDetails['data']['dateaired'],
                'year': episodeDetails['data']['year'],
                'mediatype': episodeDetails['data']['type']
                })

            # Add eventual subtitles
            if 'subtitles' in episodeDetails['data'] and len(episodeDetails['data']['subtitles']) > 0:
                try:
                    liz.setSubtitles([s['url'] for s in episodeDetails['data']['subtitles'] if 'url' in s])
                    for subtitle in episodeDetails['data']['subtitles']:
                        if 'lang' in subtitle:
                            liz.addStreamInfo('subtitle', {'language': subtitle['lang']})
                except:
                    pass

            if episodeDetails.get('useDash', False) and inputstreamhelper:
                logger.logDebug(episodeDetails['dash'])
                
                protocol = 'mpd'
                drm = episodeDetails['dash']['type']
                license_server = episodeDetails['dash']['key']
                headers = episodeDetails['dash']['headers']
                license_key = logger.logDebug('%s|%s|%s|%s' % (license_server, headers, 'R{SSM}', ''))

                is_helper = inputstreamhelper.Helper(protocol, drm=drm)
                is_helper.check_inputstream()
                liz.setProperty('inputstream', 'inputstream.adaptive')
                liz.setProperty('inputstream.adaptive.manifest_type', protocol)
                liz.setProperty('inputstream.adaptive.license_type', drm)
                liz.setProperty('inputstream.adaptive.stream_headers', 'Origin=%s&Referer=%s&User-Agent=%s&cache-control=no-cache&pragma=no-cache&sec-fetch-mode=cors&sec-fetch-site=cross-site' % (config.websiteUrl, config.websiteUrl+'/', config.userAgents['default']))
                liz.setProperty('inputstream.adaptive.license_key', license_key)
                liz.setMimeType(episodeDetails['data']['type'])
                liz.setContentLookup(False)
            
            liz.setProperty('fanart_image', episodeDetails['data']['fanart'])
            liz.setProperty('IsPlayable', 'true')
            try:
                return control.resolve(thisPlugin, True, liz)
            except:
                control.showNotification(control.lang(37032), control.lang(30004))
        elif (not episodeDetails) or (episodeDetails and 'errorCode' in episodeDetails and episodeDetails['errorCode'] != 0):
            logger.logNotice(episodeDetails['StatusMessage'] if 'StatusMessage' in episodeDetails else 'Unknown error')
            if 'StatusMessage' in episodeDetails:
                control.showNotification(episodeDetails['StatusMessage'], control.lang(30004))
            else:
                control.showNotification(control.lang(37001), control.lang(30009))
    return False

def getMediaInfo(episodeId, title, type, thumbnail, bandwidth=False):
    """Get media info for playback"""
    logger.logInfo('called function')
    mediaInfo = retrieveMediaInfo(episodeId, type, bandwidth)
    if mediaInfo['errorCode'] == 0:
        e = {
            'id': episodeId,
            'title': title,
            'parentid': mediaInfo['data']['showid'],
            'show': mediaInfo['data']['show'],
            'image': thumbnail,
            'fanart': mediaInfo['data']['fanart'],
            'episodenumber': mediaInfo['data']['episodenumber'],
            'url': mediaInfo['data']['url'],
            'description': mediaInfo['data']['plot'],
            'shortdescription': mediaInfo['data']['plot'],
            'dateaired': mediaInfo['data']['dateaired'],
            'date': mediaInfo['data']['date'],
            'year': mediaInfo['data']['year'],
            'parentalAdvisory': mediaInfo['data']['parentalAdvisory'],
            'ltype': mediaInfo['data']['ltype'],
            'type': 'episode',
            'duration': mediaInfo['data']['duration'],
            'views': mediaInfo['data']['views'] + 1,
            'rating': mediaInfo['data']['rating'],
            'votes': mediaInfo['data']['votes']
            }
        episodeDB.set(e)

        s = mediaInfo['data']['showObj']
        showDB.update({'id': s.get('id'), 'views': s.get('views', 0) + 1})
        
    return mediaInfo

def getEpisodeBandwidthList(episodeId, title, type, thumbnail):
    """Get available bandwidth options"""
    logger.logInfo('called function')
    mediaInfo = retrieveMediaInfo(episodeId, type)
    data = []
    if mediaInfo['errorCode'] == 0:
        i = 0
        for resolution in mediaInfo['data']['bandwidth']:
            data.append({
                'id': episodeId,
                'title': title,
                'parentid': mediaInfo['data']['showid'],
                'show': mediaInfo['data']['show'],
                'image': thumbnail,
                'fanart': mediaInfo['data']['fanart'],
                'episodenumber': mediaInfo['data']['episodenumber'],
                'url': mediaInfo['data']['url'],
                'description': mediaInfo['data']['plot'],
                'shortdescription': mediaInfo['data']['plot'],
                'dateaired': mediaInfo['data']['dateaired'],
                'date': mediaInfo['data']['date'],
                'year': mediaInfo['data']['year'],
                'parentalAdvisory': mediaInfo['data']['parentalAdvisory'],
                'ltype': mediaInfo['data']['ltype'],
                'type': 'episode',
                'duration': mediaInfo['data']['duration'],
                'views': mediaInfo['data']['views'],
                'rating': mediaInfo['data']['rating'],
                'votes': mediaInfo['data']['votes'],
                'showObj': mediaInfo['data']['showObj'],
                'bandwidth': i,
                'resolution': resolution})
            i += 1
    return data

def retrieveMediaInfo(episodeId, type, bandwidth=False):
    """Get media info from website"""
    logger.logInfo('called function with param (%s, %s, %s)' % (str(episodeId), type, bandwidth))
    from .api import callJsonApi

    playback = callJsonApi(
        config.uri.get('video') % episodeId,
        {
            'platform': 'web',
            'subPlatform': 'firefox',
            'appVersion': '25.09.11-1',
            'appVersionCode': 1,
            'playbackSessionId': control.generateUUID(),
            'playbackCapabilities': {
                'drm': [
                    'wv'
                ],
                'streamType': [
                    'dash'
                ],
                'resolution': [
                    'fhd'
                ],
                'audio': [
                    'stereo'
                ],
                'hdr': [
                    'hdr10'
                ]
            }
        },
        useCache=False,
    )

    """
    'referralProperties': {
        'railTitle':'Hero Banner',
        'railType':'Banner',
        'railSubType':'Carousel',
        'pageName':'page_details'
    }

    {
        'railTitle': 'Continue Watching',
        'railType': 'Portrait',
        'railSubType': 'ContinueWatching',
        'pageName': 'page_details'
    }
    """
    
    mediaInfo = {
        'errorCode': 0,
        'StatusMessage': ''
        }

    logger.logInfo('episode')
    episode = logger.logDebug(getEpisode(episodeId))

    if episode.get('id', True) is True or 'playbackInfo' not in playback or 'url' not in playback.get('playbackInfo', {}):
        mediaInfo['StatusMessage'] = control.lang(37032)
        mediaInfo['errorCode'] = 2
    else:
        show = logger.logInfo(episode.get('showObj', {}))
        mediaInfo['data'] = {}
        mediaInfo['data']['url'] = episode.get('url')
        mediaInfo['data']['uri'] = playback.get('playbackInfo', {}).get('url', '')
        
        # Parental advisory
        mediaInfo['data']['parentalAdvisory'] = 'false'
        if episode.get('parentalAdvisory') == 'true':
            mediaInfo['data']['parentalAdvisory'] = 'true'
            if control.setting('parentalAdvisoryCheck') == 'true':
                control.alert(control.lang(37011), title=control.lang(30003))
            if control.setting('parentalControl') == 'true':
                code = control.numpad(control.lang(37021))
                if code != control.setting('parentalCode'):
                    mediaInfo['StatusMessage'] = control.lang(37022)
                    mediaInfo['errorCode'] = 3
                    mediaInfo['data'] = {}
                    return mediaInfo
        
        # check if mpd to use inputstream.adaptive
        if 'mpd' in mediaInfo['data']['uri']:
            mediaInfo['useDash'] = True
            headers = 'Origin=%s&Referer=%s&User-Agent=%s&Sec-Fetch-Dest=empty&Sec-Fetch-Mode=cors&Sec-Fetch-Site=cross-site&Sec-GPC=1&Connection=keep-alive' % (config.websiteUrl, config.websiteUrl+'/', quote(config.userAgents['default']))

            """
            # choose best stream quality
            defaultQuality = 0
            if bandwidth is False:
                mediaInfo['data']['bandwidth'] = []
                for stream in episode.get('media', {}).get('mpds', []):
                    mpd_match = re.compile('manifest\.(\d+x\d+)\.mpd', re.IGNORECASE).search(stream)
                    if mpd_match:
                        resolution = mpd_match.group(1)
                        mediaInfo['data']['bandwidth'].append(resolution)
                        
                streamQualities = ['1920x1080', '1280x720', '960x540', '768x432', '640x360', '512x288', '384x216']
                for quality in streamQualities:
                    if quality in mediaInfo['data']['bandwidth']:
                        defaultQuality = mediaInfo['data']['bandwidth'].index(quality)
                        break
            else:
                defaultQuality = bandwidth
                
            mediaInfo['data']['uri'] = episode.get('media', {}).get('mpds', [])[defaultQuality]
            """
            
            # DRM
            mediaInfo['dash'] = {
                'type': 'com.widevine.alpha',
                'key': playback.get('playbackInfo', {}).get('licenseUrl', ''),
                'headers': headers
            }
        """
        else:
            # choose best stream quality
            defaultQuality = 0
            if bandwidth is False:
                mediaInfo['data']['bandwidth'] = []
                for stream in episode.get('media', {}).get('m3u8s', []):
                    m3u8_match = re.compile('playlist\.(\d+x\d+)\.m3u8', re.IGNORECASE).search(stream)
                    if m3u8_match:
                        resolution = m3u8_match.group(1)
                        mediaInfo['data']['bandwidth'].append(resolution)
                        
                streamQualities = ['1920x1080', '1280x720', '960x540', '768x432', '640x360', '512x288', '384x216']
                for quality in streamQualities:
                    if quality in mediaInfo['data']['bandwidth']:
                        defaultQuality = mediaInfo['data']['bandwidth'].index(quality)
                        break
            else:
                defaultQuality = bandwidth
                
            mediaInfo['data']['uri'] = episode.get('media', {}).get('m3u8s', [])[defaultQuality]
        """

        mediaInfo['data']['preview'] = False
        mediaInfo['data']['showid'] = show.get('id')
        mediaInfo['data']['show'] = show.get('name', episode.get('title'))
        mediaInfo['data']['parentname'] = show.get('parentname', '')
        mediaInfo['data']['rating'] = show.get('rating', 0)
        mediaInfo['data']['votes'] = show.get('votes', 0)
        mediaInfo['data']['plot'] = episode.get('description')
        mediaInfo['data']['image'] = episode.get('image')
        mediaInfo['data']['fanart'] = show.get('fanart', episode.get('image'))
        mediaInfo['data']['ltype'] = episode.get('ltype', 'show')
        mediaInfo['data']['type'] = episode.get('type', 'show')
        if 'subtitles' in playback.get('playbackInfo', {}) and len(playback.get('playbackInfo', {}).get('subtitles', [])) > 0:
            mediaInfo['data']['subtitles'] = playback.get('playbackInfo', {}).get('subtitles', [])
        mediaInfo['data']['dateaired'] = ''
        mediaInfo['data']['date'] = ''
        mediaInfo['data']['year'] = show.get('year')
        mediaInfo['data']['episodenumber'] = episode.get('episodenumber', 1)
        mediaInfo['data']['duration'] = episode.get('duration')
        mediaInfo['data']['views'] = episode.get('views', 0)
        mediaInfo['data']['showObj'] = show
                
        logger.logInfo(mediaInfo)
    
    return mediaInfo

def getEpisodeFromShow(id):
    """Get episode from show (for movies)"""
    logger.logInfo('called function with param (%s)' % id)
    data = {}
    
    show = getShow(id, True)
    if show.get('id', False):
        data = {
            'id': id,
            'title': show.get('name'),
            'parentid': show.get('id'),
            'show': show.get('name', ''),
            'image': show.get('image'),
            'fanart': show.get('fanart', ''),
            'episodenumber': 1,
            'url': id,
            'description': show.get('description'),
            'shortdescription': show.get('description'),
            'dateaired': '',
            'date': '',
            'year': show.get('year', ''),
            'parentalAdvisory': show.get('parentalAdvisory'),
            'showObj': show,
            'ltype': show.get('ltype', 'show'),
            'type': 'episode',
            'media': show.get('media')
            }
        data['media']['id'] = show.get('mediaID', '')
                
    return data

def getEpisodeFromLiveStream(id):
    """Get episode from live stream"""
    logger.logInfo('called function with param (%s)' % id)
    from .api import callJsonApi
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
            useCache=False
            )
        if 'kid' in stream:
            data = {
                'id': id,
                'title': show.get('name'),
                'parentid': show.get('id'),
                'show': show.get('name', ''),
                'image': show.get('image'),
                'fanart': show.get('fanart', ''),
                'episodenumber': 1,
                'url': id,
                'description': show.get('description'),
                'shortdescription': show.get('description'),
                'dateaired': '',
                'date': '',
                'year': show.get('year', ''),
                'parentalAdvisory': show.get('parentalAdvisory'),
                'showObj': show,
                'ltype': show.get('ltype', 'show'),
                'type': 'episode',
                'media': {}
                }
            if 'm3u8' in stream:
                data['media']['m3u8s'] = [stream['m3u8']]
            if 'mpd' in stream:
                data['media']['mpds'] = [stream['mpd']]
            data['media']['id'] = show.get('streamID', stream.get('streamID', ''))
                
    return data
