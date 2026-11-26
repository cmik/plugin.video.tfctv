# -*- coding: utf-8 -*-

"""
Media playback module
"""

import re
import json
import time
from urllib.parse import quote, urlencode
from resources import config
from resources.lib.libraries import control
from .catalog import getEpisode, getShow, episodeDB, showDB
from .graphql import getAsset
from .formatters import formatAssetToEpisode
from .history import recordView
from resources.lib.libraries import playertracker, liveplayback, markers as skipmarkers
from .auth import isLoggedIn, login
from .utils import checkProxy

logger = control.logger

try:
    import inputstreamhelper
except Exception:
    inputstreamhelper = None

def startAtEnd(item, episodeId, found):
    """With Skip automatically, the playback starts after the intro and the recap (StartOffset). Not for an episode that
    can be resumed: Kodi asks where to resume, and its Play from beginning must not be overridden."""
    try:
        modes = dict((kind, skipmarkers.modeOf(control.setting(key))) for kind, key in skipmarkers.SETTINGS.items())
        start = skipmarkers.startAfter(found, modes)
        if start and episodeId not in showDB.getUserData().getProgress([episodeId]):
            item.setProperty('StartOffset', str(int(start[0])))
            control.showNotification(control.lang(30281 if start[1] == skipmarkers.RECAP else 30280))
            logger.logInfo('start after the %s: %d s' % (start[1], start[0]))
    except Exception as e:
        logger.logError('start after the intro failed: %s' % e)


def playEpisode(episodeId, name, type, thumbnail):
    """Play an episode"""
    logger.logInfo('called function')
    thisPlugin = control.thisPlugin
    
    if checkProxy():
        # Check if logged in
        if control.setting('emailAddress') != '' and not isLoggedIn():
            control.showNotification(control.lang(37012), control.lang(30002))
            login()
                
        episodeDetails = getMediaInfo(episodeId, name, type, thumbnail)
        logger.logDebug(episodeDetails)
        if episodeDetails and 'errorCode' in episodeDetails and episodeDetails['errorCode'] == 0 and 'data' in episodeDetails:
            if 'preview' in episodeDetails['data'] and episodeDetails['data']['preview'] is True:
                control.infoDialog(control.lang(37025), control.lang(30002), time=5000)
            elif 'StatusMessage' in episodeDetails and episodeDetails['StatusMessage'] != '':
                control.showNotification(episodeDetails['StatusMessage'], control.lang(30009))
            
            url = control.setting('proxyStreamingUrl') % (control.setting('proxyHost'), control.setting('proxyPort'), quote(episodeDetails['data']['uri']), '') if not episodeDetails.get('disableProxy', False) and not episodeDetails.get('useDash', False) and (control.setting('useProxy') == 'true') else episodeDetails['data']['uri']
            kodiurl = url
            #+'|Origin=%s&Referer=%s&User-Agent=%s&Sec-Fetch-Mode=cors' % (config.websiteUrl, config.websiteUrl+'/', config.userAgents['default'])
            #if ('tfcmsl.akamaized.net' in url):
            #    kodiurl = kodiurl + '&Sec-Fetch-Dest=empty&Sec-Fetch-Site=cross-site'
            #else:
            #    kodiurl = kodiurl + '&Accept=*/*,akamai/media-acceleration-sdk;b=1702200;v=1.2.2;p=javascript'
            logger.logDebug('Final Kodi URL: %s' % kodiurl)
            item = control.item(name, path=kodiurl)
            item.setArt({'thumb': thumbnail, 'icon': "DefaultVideo.png"})
            tag = item.getVideoInfoTag()
            tag.setTitle(name)
            tag.setSortTitle(episodeDetails['data']['dateaired'])
            tag.setTvShowTitle(episodeDetails['data']['show'])
            tag.setGenres([episodeDetails['data']['parentname']] if episodeDetails['data']['parentname'] else [])
            tag.setEpisode(int(episodeDetails['data']['episodenumber']) if str(episodeDetails['data']['episodenumber']).isdigit() else 0)
            tag.setPlot(episodeDetails['data']['plot'])
            tag.setFirstAired(episodeDetails['data']['dateaired'])
            tag.setYear(int(episodeDetails['data']['year']) if str(episodeDetails['data']['year']).isdigit() else 0)
            tag.setMediaType(episodeDetails['data']['type'])

            # Add eventual subtitles
            if 'subtitles' in episodeDetails['data'] and len(episodeDetails['data']['subtitles']) > 0:
                try:
                    item.setSubtitles([s['url'] for s in episodeDetails['data']['subtitles'] if 'url' in s])
                    for subtitle in episodeDetails['data']['subtitles']:
                        if 'lang' in subtitle:
                            item.addStreamInfo('subtitle', {'language': subtitle['lang']})
                except Exception:
                    pass

            if episodeDetails.get('useDash', False) and inputstreamhelper:
                logger.logDebug(episodeDetails['dash'])
                
                protocol = 'mpd'
                drm = episodeDetails['dash']['type']
                license_server = episodeDetails['dash']['key']
                headers = episodeDetails['dash']['headers']
                stream_headers = {
                    'Origin': config.websiteUrl,
                    'Referer': config.websiteUrl+'/',
                    'User-Agent': config.userAgents['default'],
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'cross-site',
                    'Connection': 'keep-alive'
                }
                manifest_headers = {
                    'Origin': config.websiteUrl,
                    'Referer': config.websiteUrl+'/',
                    'User-Agent': config.userAgents['default'],
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'cross-site',
                    'Connection': 'keep-alive'
                }
                # EZDRM returns the raw Widevine license (binary), not JSON:
                # an empty response_data field tells inputstream.adaptive to use it as-is.
                # 'JBlicense' made it try to parse JSON -> "Unable to find license in JSON string".
                license_headers = dict(headers)
                license_headers['Content-Type'] = 'application/octet-stream'
                license_config = {
                    'license_server_url': license_server,
                    'headers': urlencode(license_headers),
                    'post_data': 'R{SSM}',
                    'response_data': ''
                }
                logger.logDebug(license_config)
                inputstream_config = {
                    'ssl_verify_peer': False
                }

                is_helper = inputstreamhelper.Helper(protocol, drm=drm)
                if not is_helper.check_inputstream():
                    control.showNotification(control.lang(37032), control.lang(30004))
                    return False
                item.setProperty('inputstream', 'inputstream.adaptive')
                item.setProperty('inputstream.adaptive.manifest_type', protocol)
                item.setProperty('inputstream.adaptive.license_type', drm)
                item.setProperty('inputstream.adaptive.stream_headers', urlencode(stream_headers))
                item.setProperty("inputstream.adaptive.manifest_headers", urlencode(manifest_headers))
                item.setProperty('inputstream.adaptive.license_key', '|'.join(list(license_config.values())))
                item.setProperty('inputstream.adaptive.config', json.dumps(inputstream_config))
                for key, value in streamQualityProperties().items():
                    item.setProperty(key, value)
                item.setMimeType('application/dash+xml')
                item.setContentLookup(False)
            
            item.setProperty('fanart_image', episodeDetails['data']['fanart'])
            item.setProperty('IsPlayable', 'true')
            # tell the service what is played, it keeps where it stops (libraries/playertracker.py)
            # (not for a live channel: nothing to resume, to scrobble or to follow with Up Next)
            if not liveplayback.isLive(type):
                item.setProperty(playertracker.ITEM_PROPERTY, str(episodeId))
                control.window.setProperty(playertracker.PROPERTY, playertracker.encode(episodeId))
                # the intro, recap and outro iWant knows: the service offers to skip them (libraries/markers.py)
                if episodeDetails['data'].get('markers'):
                    item.setProperty(skipmarkers.PROPERTY, skipmarkers.encode(episodeDetails['data']['markers']))
                    startAtEnd(item, episodeId, episodeDetails['data']['markers'])
            try:
                return control.resolve(thisPlugin, True, item)
            except Exception:
                control.showNotification(control.lang(37032), control.lang(30004))
        elif (not episodeDetails) or (episodeDetails and 'errorCode' in episodeDetails and episodeDetails['errorCode'] != 0):
            logger.logNotice(episodeDetails['StatusMessage'] if 'StatusMessage' in episodeDetails else 'Unknown error')
            if 'StatusMessage' in episodeDetails:
                control.showNotification(episodeDetails['StatusMessage'], control.lang(30004))
            else:
                control.showNotification(control.lang(37001), control.lang(30009))
    return False

def getMediaInfo(episodeId, title, type, thumbnail):
    """Get media info for playback"""
    logger.logInfo('called function')
    mediaInfo = retrieveMediaInfo(episodeId, type)
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
        if not liveplayback.isLive(type):
            # keep what is already stored (artwork, description): the values above can be
            # empty or show-level when playing from a list without thumbnail
            stored = episodeDB.get(episodeId)
            if len(stored) == 1:
                for k in ('image', 'fanart', 'description', 'shortdescription'):
                    if stored[0].get(k):
                        e[k] = stored[0][k]
            episodeDB.set(e)
            episodeDB.update({'id': episodeId, 'views': e['views'], 'rating': e['rating'], 'votes': e['votes']})

            s = mediaInfo['data']['showObj']
            showDB.update({'id': s.get('id'), 'views': s.get('views', 0) + 1})
            recordView(e)
        # a live channel is not an episode of the catalog: no stored views, no history
        
    return mediaInfo

STREAM_SELECTIONS = ('', 'ask-quality', 'manual-osd')

def streamQualityProperties():
    """inputstream.adaptive properties of the quality settings: how the stream is chosen
    (the add-on settings of inputstream.adaptive, a choice when the playback starts, or in
    the player's OSD) and the maximum resolution. Nothing is set when left on the defaults."""
    properties = {}
    try:
        selection = STREAM_SELECTIONS[int(control.setting('streamSelection') or 0)]
    except (ValueError, IndexError):
        selection = ''
    if selection:
        properties['inputstream.adaptive.stream_selection_type'] = selection
    maxResolution = control.setting('streamMaxResolution')
    if maxResolution and maxResolution != 'auto':
        properties['inputstream.adaptive.chooser_resolution_max'] = maxResolution
        # the streams protected by Widevine are limited by their own property
        properties['inputstream.adaptive.chooser_resolution_secure_max'] = maxResolution
    return properties

def getDeviceUUID():
    """Stable device UUID sent to playback/start (the website sends one; without it
    the Widevine license token has deviceId 'unknown' and EZDRM answers ACCESS_DENIED).
    Derived from the add-on fingerprint ID (32 hex chars) so it stays the same across runs."""
    import uuid
    from .user import getFingerprintID
    try:
        return str(uuid.UUID(getFingerprintID()))
    except Exception:
        return control.generateUUID()

def retrieveMediaInfo(episodeId, type):
    """Get media info from website"""
    logger.logInfo('called function with param (%s, %s)' % (str(episodeId), type))
    from .api import callJsonApi

    live = liveplayback.isLive(type)
    from .user import getCountryCode
    country = getCountryCode() or 'FR'
    playback = callJsonApi(
        liveplayback.startPath(config.uri.get('video') % episodeId, episodeId, type, country),
        liveplayback.withReferral({
            'platform': 'web',
            'subPlatform': 'firefox',
            'appVersion': '26.10.29-1',
            'appVersionCode': 1,
            'playbackSessionId': control.generateUUID(),
            'networkType': 'unknown',
            'deviceId': getDeviceUUID(),
            'playbackCapabilities': {
                'drm': [
                    'wv'
                ],
                'streamType': [
                    'dash'
                ],
                'resolution': [
                    'fhd'      #fhd, 'hd', 'sd', 'ld'
                ],
                'audio': [
                    'stereo'
                ],
                'hdr': [
                    'hdr10'
                ]
            }
        }, type),
        headers=[
            ('Authorization', 'Bearer %s' % control.setting('iWantUserAuthentication')),
            ('Referer', config.websiteSecuredUrl+'/'),
            ('Origin', config.websiteSecuredUrl),
            ('x-country-code', country),
            ('x-device-platform', 'web'),
            ('x-device-subplatform', 'firefox'),
            ('Sec-Fetch-Dest', 'empty'),
            ('Sec-Fetch-Mode', 'cors'),
            ('Sec-Fetch-Site', 'same-site')
        ],
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
    # a channel is shown from its asset: it is not stored in the episodes of the catalog
    episode = logger.logDebug(formatAssetToEpisode(getAsset(episodeId), {}) if live else getEpisode(episodeId))

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
            headers = {
                'Origin': config.websiteUrl,
                'Referer': config.websiteUrl+'/',
                'User-Agent': config.userAgents['default'],
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-GPC': '1',
                'Connection': 'keep-alive'
            }
            
            
            # DRM
            mediaInfo['dash'] = {
                'type': 'com.widevine.alpha',
                'key': playback.get('playbackInfo', {}).get('licenseUrl', ''),
                'headers': headers
            }

        mediaInfo['data']['preview'] = False
        mediaInfo['data']['disableProxy'] = True
        mediaInfo['data']['livestream'] = True if 'content_livestream=1' in mediaInfo['data']['uri'] else False
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
        if 'subtitles' in playback.get('playbackInfo', {}) and playback.get('playbackInfo', {}).get('subtitles', []) is not None and len(playback.get('playbackInfo', {}).get('subtitles', [])) > 0:
            mediaInfo['data']['subtitles'] = playback.get('playbackInfo', {}).get('subtitles', [])
        mediaInfo['data']['dateaired'] = ''
        mediaInfo['data']['date'] = ''
        mediaInfo['data']['year'] = show.get('year')
        mediaInfo['data']['episodenumber'] = episode.get('episodenumber', 1)
        mediaInfo['data']['duration'] = episode.get('duration')
        mediaInfo['data']['views'] = episode.get('views', 0)
        mediaInfo['data']['showObj'] = show
        mediaInfo['data']['markers'] = skipmarkers.parse(playback.get('markers'))  # intro, recap, outro of some episodes
                
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
