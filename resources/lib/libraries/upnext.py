# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik

    Up Next: tells the service.upnext add-on which episode follows the one that starts, so that it
    offers to play it at the end (https://github.com/im85288/service.upnext/wiki/Integration).
'''

import base64
import json
import re
from urllib.parse import quote_plus

from resources import config
from resources.lib.libraries import control

logger = control.logger

# played items that are not episodes of a show
NOT_EPISODES = ('movie', 'documentary', 'livestream', 'channel')
SEASON_EPISODE = re.compile(r'^\s*S(\d+)\s*E(\d+)', re.IGNORECASE)
# titles of the shows split by day: "Ep 24th Oct 2026 - Episode 1"
DAILY = re.compile(r'(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3})[a-z]*\s+(\d{4})')
MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']


def _number(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def sortKey(episode):
    """Where an episode comes in its show. The air date is not stored, so the order is the one the titles
    give: season and episode ("S2 E10"), else the day of the title, else the episode number."""
    title = episode.get('title') or ''
    found = SEASON_EPISODE.match(title)
    if found:
        return (0, int(found.group(1)), int(found.group(2)), title)
    found = DAILY.search(title)
    if found and found.group(2).lower() in MONTHS:
        return (1, int(found.group(3)), MONTHS.index(found.group(2).lower()) + 1, int(found.group(1)), title)
    return (2, 0, _number(episode.get('episodenumber')), title)


def seasonAndEpisode(episode):
    found = SEASON_EPISODE.match(episode.get('title') or '')
    if found:
        return int(found.group(1)), int(found.group(2))
    return 1, _number(episode.get('episodenumber'))


def lastEpisode(episodes):
    """The last episode of a show (None without episodes), in the order of sortKey: the one of the latest season"""
    return max(episodes, key=sortKey) if episodes else None


def nextEpisode(current, siblings):
    """The episode that follows `current` among the episodes of its show (None for the last one)"""
    key = sortKey(current)
    later = [e for e in siblings if e.get('id') != current.get('id') and sortKey(e) > key]
    return min(later, key=sortKey) if later else None


def playUrl(addonId, episode):
    """The plugin URL that plays an episode (what the navigator builds for its PLAY items)"""
    return 'plugin://%s/?url=%s&mode=%d&name=%s&page=1&thumbnail=%s&ltype=%s&title=%s' % (
        addonId, quote_plus(str(episode['id'])), config.PLAY, quote_plus(episode.get('title') or ''),
        quote_plus(episode.get('image') or ''), quote_plus(episode.get('ltype') or 'show'), quote_plus(episode.get('title') or ''))


def episodeInfo(episode, show):
    """The description Up Next wants of an episode (all the keys are expected, even empty)"""
    show = show or {}
    season, number = seasonAndEpisode(episode)
    return {
        'episodeid': str(episode['id']),
        'tvshowid': str(episode.get('parentid') or show.get('id') or ''),
        'title': episode.get('title') or '',
        'art': {
            'thumb': episode.get('image') or '',
            'tvshow.fanart': show.get('fanart') or episode.get('fanart') or '',
            'tvshow.poster': show.get('image') or '',
            'tvshow.landscape': show.get('banner') or '',
            'tvshow.clearlogo': show.get('logo') or '',
            'tvshow.clearart': ''
        },
        'season': str(season),
        'episode': str(number),
        'showtitle': show.get('name') or episode.get('show') or '',
        'plot': episode.get('description') or '',
        'playcount': _number(episode.get('views')),
        'rating': 0,
        'firstaired': (episode.get('date') or '')[:10],
        'runtime': _number(episode.get('duration'))
    }


def buildData(episodeDB, showDB, episodeId, addonId):
    """What to tell Up Next when `episodeId` starts, or None (a movie, an unknown episode, the last episode of the show)"""
    found = episodeDB.get(episodeId)
    if not found:
        return None
    current = found[0]
    showId = current.get('parentid')
    if not showId or str(showId) == str(current.get('id')) or current.get('ltype') in NOT_EPISODES:
        return None
    following = nextEpisode(current, episodeDB.get(showId, 'SHOWID'))
    if following is None:
        return None
    shows = showDB.get(showId)
    show = shows[0] if shows else {}
    return {
        'current_episode': episodeInfo(current, show),
        'next_episode': episodeInfo(following, show),
        'play_url': playUrl(addonId, following)
    }


def request(data, addonId):
    """The JSON-RPC request that hands the data to Up Next: a notification from `<addon id>.SIGNAL`
    with the message `upnext_data` and the data as base64 encoded JSON"""
    return json.dumps({
        'jsonrpc': '2.0', 'id': 1, 'method': 'JSONRPC.NotifyAll',
        'params': {'sender': '%s.SIGNAL' % addonId, 'message': 'upnext_data',
                   'data': [base64.b64encode(json.dumps(data).encode('utf-8')).decode('ascii')]}
    })


def send(data, addonId):
    import xbmc
    xbmc.executeJSONRPC(request(data, addonId))
