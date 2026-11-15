# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik

    Trakt: scrobbling of what is played (https://trakt.docs.apiary.io/#reference/scrobble).
    The user creates an application on trakt.tv/oauth/applications and gives its client id in the settings
    (and its client secret when the application has one: Trakt no longer gives one to the public clients), then connects the account with the device flow (a code to enter on trakt.tv).
    The tokens are kept in the META table of userdata.db, not in the settings.
    Only the standard library is used (there is no `requests` in Kodi).
'''

import json
import re
import time
from urllib import request as libRequest
from urllib.parse import quote
from urllib.error import HTTPError, URLError

from resources import config
from resources.lib.libraries import control
from resources.lib.libraries import upnext

logger = control.logger

API = 'https://api.trakt.tv'
ACCESS, REFRESH, EXPIRES = 'traktAccessToken', 'traktRefreshToken', 'traktExpiresAt'
# refresh the token when it expires within this delay (seconds)
REFRESH_MARGIN = 3600
TIMEOUT = 15


def normalize(title):
    """A title as compared with the ones of Trakt: letters and digits only, lower case"""
    return re.sub(r'[^a-z0-9]+', '', (title or '').lower())


def matches(wanted, found):
    """Whether the title of a Trakt show is the one of the show: the same, or one holding the other
    (the titles here often add the name of the star: "FPJ's Batang Quiapo" for "Batang Quiapo")"""
    a, b = normalize(wanted), normalize(found)
    if not a or not b:
        return False
    return a == b or (min(len(a), len(b)) >= 5 and (a in b or b in a))


def scrobbleBody(episode, show, progress, traktId=None):
    """What Trakt wants to scrobble an episode or a movie, or None when it can't be identified.
    Trakt finds the show by its title, and numbers its episodes by season: only the titles that give
    the season and the episode ("S2 E10 - ...") can be told (the others are named by their day)."""
    if not episode:
        return None
    ltype = episode.get('ltype')
    if ltype == 'movie':
        title = episode.get('title') or ''
        if not title:
            return None
        movie = {'title': title}
        if str(episode.get('year') or '').isdigit():
            movie['year'] = int(episode['year'])
        return {'movie': movie, 'progress': round(progress, 2)}
    if ltype in upnext.NOT_EPISODES:
        return None
    found = upnext.SEASON_EPISODE.match(episode.get('title') or '')
    showTitle = ((show or {}).get('name') or episode.get('show') or '').strip()
    if not found or not showTitle:
        return None
    return {'show': {'ids': {'trakt': int(traktId)}} if traktId else {'title': showTitle},
            'episode': {'season': int(found.group(1)), 'number': int(found.group(2))},
            'progress': round(progress, 2)}


def progressOf(position, total):
    """The progress in percent for Trakt (0 to 100)"""
    if not total or total <= 0:
        return 0.0
    return max(0.0, min(100.0, position * 100.0 / total))


def fromSettings(store):
    """The client for the settings: the application of the add-on, or the user's own when its client id is given
    (the secret of the settings is the one of that application, it is not used with the one of the add-on).
    The settings are read again each time: the service lives long."""
    ownId = (control.getAddonSetting('traktClientId') or '').strip()
    if ownId:
        return Trakt(ownId, control.getAddonSetting('traktClientSecret'), store)
    return Trakt(config.TRAKT_CLIENT_ID, '', store)


class Trakt(object):
    """Client of the Trakt API. `store` keeps the tokens (`getMeta`/`setMeta` of UserData);
    `opener` is `urllib.request.urlopen` unless a test gives another one."""

    def __init__(self, clientId, clientSecret, store, opener=None, clock=time.time):
        self.clientId = (clientId or '').strip()
        self.clientSecret = (clientSecret or '').strip()
        self.store = store
        self.opener = opener or libRequest.urlopen
        self.clock = clock
        self.lastStatus = None

    def hasCredentials(self):
        return bool(self.clientId)

    def _client(self, data):
        """`data` with the client id, and the secret when there is one"""
        data = dict(data, client_id=self.clientId)
        if self.clientSecret:
            data['client_secret'] = self.clientSecret
        return data

    def isConnected(self):
        return bool(self.store.getMeta(ACCESS) and self.store.getMeta(REFRESH))

    def _call(self, path, body=None, token=None):
        """(HTTP status, decoded JSON or None); 0 when Trakt can't be reached"""
        # Trakt (behind Cloudflare) refuses the default user agent of urllib (error 1010)
        headers = {'Content-Type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': self.clientId,
                   'User-Agent': 'plugin.video.tfctv/%s Kodi' % control.addonInfo('version')}
        if token:
            headers['Authorization'] = 'Bearer %s' % token
        req = libRequest.Request(API + path, data=json.dumps(body).encode('utf-8') if body is not None else None, headers=headers)
        try:
            with self.opener(req, timeout=TIMEOUT) as response:
                status, raw = response.getcode(), response.read()
        except HTTPError as e:
            status, raw = e.code, e.read()
        except (URLError, OSError, ValueError) as e:
            logger.logError('Trakt: %s unreachable: %s' % (path, e))
            return 0, None
        try:
            data = json.loads(raw.decode('utf-8')) if raw else None
        except ValueError:
            data = None
        self.lastStatus = status
        if status >= 400 and status != 400 or (status == 400 and not path.startswith('/oauth/device/token')):
            logger.logError('Trakt: %s answered HTTP %s %s' % (path, status, raw[:300]))
        return status, data

    def _saveTokens(self, data):
        self.store.setMeta(ACCESS, data['access_token'])
        self.store.setMeta(REFRESH, data['refresh_token'])
        self.store.setMeta(EXPIRES, int(data.get('created_at', self.clock())) + int(data.get('expires_in', 0)))

    def findShow(self, title):
        """The Trakt id of the show with this title (the best result of a search whose title matches), or None"""
        status, data = self._call('/search/show?query=%s&limit=10' % quote(title or ''), token=None)
        if status != 200 or not isinstance(data, list):
            return None
        found = [r for r in data if matches(title, (r.get('show') or {}).get('title'))]
        if not found:
            return None
        # the exact title first, then the best score
        found.sort(key=lambda r: (normalize(r['show']['title']) == normalize(title), r.get('score') or 0), reverse=True)
        return (found[0]['show'].get('ids') or {}).get('trakt')

    def resolveShow(self, showKey, title):
        """The Trakt id of a show, remembered by the id the show has here. A show Trakt doesn't know is
        looked for again after a day. None when it can't be found (or Trakt can't be reached)."""
        key = 'traktShow:%s' % showKey
        saved = str(self.store.getMeta(key) or '')
        if saved.isdigit():
            return int(saved)
        if saved.startswith('none:') and self.clock() - int(saved[5:] or 0) < 86400:
            return None
        found = self.findShow(title)
        if found:
            self.store.setMeta(key, found)
            return int(found)
        if self.lastStatus == 200:  # Trakt answered: the show is unknown to it
            self.store.setMeta(key, 'none:%d' % int(self.clock()))
        return None

    def deviceCode(self):
        """The code to enter on trakt.tv (user_code, verification_url, device_code, expires_in, interval), or None"""
        status, data = self._call('/oauth/device/code', {'client_id': self.clientId})
        return data if status == 200 and data else None

    def pollToken(self, deviceCode):
        """'connected', 'pending' (not entered yet), 'slow' (ask less often) or 'failed' (refused, expired, wrong code)"""
        status, data = self._call('/oauth/device/token', self._client({'code': deviceCode}))
        if status == 200 and data and data.get('access_token'):
            self._saveTokens(data)
            return 'connected'
        if status == 400:
            return 'pending'
        if status == 429:
            return 'slow'
        return 'failed'

    def refresh(self):
        status, data = self._call('/oauth/token', self._client({
            'refresh_token': self.store.getMeta(REFRESH), 'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob', 'grant_type': 'refresh_token'}))
        if status == 200 and data and data.get('access_token'):
            self._saveTokens(data)
            return True
        return False

    def disconnect(self):
        """Revokes the token (best effort) and forgets it"""
        token = self.store.getMeta(ACCESS)
        if token:
            self._call('/oauth/revoke', self._client({'token': token}))
        for key in (ACCESS, REFRESH, EXPIRES):
            self.store.setMeta(key, '')

    def _token(self):
        if not self.isConnected():
            return None
        try:
            expires = int(self.store.getMeta(EXPIRES) or 0)
        except ValueError:
            expires = 0
        if expires - self.clock() < REFRESH_MARGIN:
            self.refresh()
        return self.store.getMeta(ACCESS)

    def scrobble(self, action, body):
        """`action` is start, pause or stop; returns the HTTP status (0: not connected or unreachable)"""
        token = self._token()
        if not token:
            return 0
        status, _ = self._call('/scrobble/%s' % action, body, token)
        if status == 401 and self.refresh():
            status, _ = self._call('/scrobble/%s' % action, body, self.store.getMeta(ACCESS))
        return status
