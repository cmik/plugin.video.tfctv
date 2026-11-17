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
import threading
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
# Trakt allows one write (scrobble) per second and per user, and asks to wait Retry-After after a 429.
# The service keeps this between the clients it makes (one per thread that sends).
MIN_POST_INTERVAL = 1.0
DEFAULT_RETRY_AFTER = 10
SKIPPED = 'skip'  # what is kept for a show the user said is not on Trakt
_state = {'lastPost': 0.0, 'blockedUntil': 0.0}
_stateLock = threading.Lock()


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


def titleVariants(title):
    """The titles to search on Trakt for a show, the most likely first: the title itself, then without the name of the
    star ("Coco Martin's Sigabo" is "Sigabo" on Trakt) and without a subtitle ("Show: Season 2", "Show - Part 2")"""
    title = re.sub(r'\s*\([^)]*\)\s*$', '', (title or '').strip())  # "(2026)" at the end
    variants = [title]
    possessive = re.match(r"^.+?['\u2019]s\s+(.+)$", title)
    if possessive:
        variants.append(possessive.group(1))
    for separator in (':', ' - '):
        if separator in title:
            variants.append(title.split(separator)[0])
            if possessive and separator in possessive.group(1):
                variants.append(possessive.group(1).split(separator)[0])
    unique, seen = [], set()
    for v in variants:
        v = v.strip()
        if len(normalize(v)) >= 2 and normalize(v) not in seen:
            seen.add(normalize(v))
            unique.append(v)
    return unique


def plausible(title, found):
    """Whether a title of Trakt can be the one of the show, or one of its variants (see titleVariants)"""
    return any(matches(v, found) for v in titleVariants(title))


def yearNear(year, other):
    """Whether two years are the same or one apart (the year here is the one of the latest season); True when one is unknown"""
    try:
        return abs(int(year) - int(other)) <= 1
    except (TypeError, ValueError):
        return True


def pickShow(title, year, candidates):
    """The Trakt id of the candidate that is surely the show, or None (nothing matches, or several shows could be it).
    In order: the same title; the only one equal to a variant of the title; the only one that matches; the only one
    of the right year among those that match."""
    possible = [c for c in candidates if plausible(title, c['title'])]
    if not possible:
        return None
    exact = [c for c in possible if normalize(c['title']) == normalize(title)]
    if len(exact) == 1:
        return exact[0]['id']
    names = set(normalize(v) for v in titleVariants(title))
    byVariant = [c for c in possible if normalize(c['title']) in names]
    if len(byVariant) == 1:
        return byVariant[0]['id']
    if len(possible) == 1:
        return possible[0]['id']
    near = [c for c in possible if yearNear(year, c.get('year'))]
    if len(near) == 1:
        return near[0]['id']
    return None


def rankCandidates(title, year, candidates):
    """The candidates, the most likely first: the same title, a title that matches, the right year, Trakt's score"""
    names = set(normalize(v) for v in titleVariants(title))
    def key(c):
        return (normalize(c['title']) in names, plausible(title, c['title']), yearNear(year, c.get('year')), c.get('score') or 0)
    return sorted(candidates, key=key, reverse=True)


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

    def __init__(self, clientId, clientSecret, store, opener=None, clock=time.time, sleep=time.sleep):
        self.clientId = (clientId or '').strip()
        self.clientSecret = (clientSecret or '').strip()
        self.store = store
        self.opener = opener or libRequest.urlopen
        self.clock = clock
        self.sleep = sleep
        self.lastStatus = None
        self.unresolved = False

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
        """(HTTP status, decoded JSON or None); 0 when Trakt can't be reached. Nothing is sent while the
        delay of a 429 is running (every request counts, the refresh and the searches too): 429 is answered."""
        with _stateLock:
            blocked = self.clock() < _state['blockedUntil']
        if blocked:
            self.lastStatus = 429
            return 429, None
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
            if status == 429:
                self._rateLimited(e.headers.get('Retry-After') if e.headers else None)
        except (URLError, OSError, ValueError) as e:
            logger.logError('Trakt: %s unreachable: %s' % (path, e))
            self.lastStatus = 0  # not the status of an earlier answer: the refresh uses it to tell a refusal from an outage
            return 0, None
        try:
            data = json.loads(raw.decode('utf-8')) if raw else None
        except ValueError:
            data = None
        self.lastStatus = status
        if status >= 400 and status != 400 or (status == 400 and not path.startswith('/oauth/device/token')):
            logger.logError('Trakt: %s answered HTTP %s %s' % (path, status, raw[:300]))
        return status, data

    def _rateLimited(self, retryAfter):
        """A 429: nothing is sent before the delay Trakt gives (or a default one) has passed"""
        try:
            delay = max(int(retryAfter), 1)
        except (TypeError, ValueError):
            delay = DEFAULT_RETRY_AFTER
        with _stateLock:
            _state['blockedUntil'] = max(_state['blockedUntil'], self.clock() + delay)
        logger.logError('Trakt: rate limited, waiting %d s' % delay)

    def _pace(self):
        """Waits so that two scrobbles are one second apart; False while a 429 delay is running"""
        with _stateLock:
            if self.clock() < _state['blockedUntil']:
                return False
            wait = MIN_POST_INTERVAL - (self.clock() - _state['lastPost'])
            _state['lastPost'] = self.clock() + max(wait, 0)
        if wait > 0:
            self.sleep(wait)
        return True

    def _forget(self):
        """Drops the tokens (not valid anymore: the user removed the access, or the refresh token was refused)"""
        for key in (ACCESS, REFRESH, EXPIRES):
            self.store.setMeta(key, '')

    def _saveTokens(self, data):
        self.store.setMeta(ACCESS, data['access_token'])
        self.store.setMeta(REFRESH, data['refresh_token'])
        self.store.setMeta(EXPIRES, int(data.get('created_at', self.clock())) + int(data.get('expires_in', 0)))

    def search(self, title):
        """The shows Trakt finds for a title (dicts id, title, year, score), or None when it can't answer"""
        status, data = self._call('/search/show?query=%s&limit=10' % quote(title or ''), token=None)
        if status != 200 or not isinstance(data, list):
            return None
        found = []
        for r in data:
            show = r.get('show') or {}
            traktId = (show.get('ids') or {}).get('trakt')
            if traktId and show.get('title'):
                found.append({'id': int(traktId), 'title': show['title'], 'year': show.get('year'), 'score': r.get('score') or 0})
        return found

    def candidates(self, title):
        """The shows found for the variants of the title, until one matches; None when Trakt can't answer"""
        found, answered = {}, False
        for query in titleVariants(title)[:3]:
            result = self.search(query)
            if result is None:
                if not answered:
                    return None
                break
            answered = True
            for c in result:
                found.setdefault(c['id'], c)
            if any(plausible(title, c['title']) for c in found.values()):
                break
        return list(found.values())

    def suggestions(self, title, year=None, limit=5):
        """The shows the user can choose among, the most likely first; None when Trakt can't answer"""
        found = self.candidates(title)
        return None if found is None else rankCandidates(title, year, found)[:limit]

    def findShow(self, title, year=None):
        """The Trakt id of the show with this title, or None when no result is surely it"""
        found = self.candidates(title)
        return pickShow(title, year, found) if found else None

    def resolveShow(self, showKey, title, year=None):
        """The Trakt id of a show, remembered by the id the show has here (what the user chose is kept the same way).
        A show Trakt doesn't know, or can't tell among several, is looked for again after a day (`unresolved` is then
        True: the user can choose it). None when it can't be found, when the user said it is not on Trakt, or when
        Trakt can't be reached."""
        self.unresolved = False
        key = 'traktShow:%s' % showKey
        saved = str(self.store.getMeta(key) or '')
        if saved.isdigit():
            return int(saved)
        if saved == SKIPPED:
            return None
        if saved.startswith('unsure:') and self.clock() - int(saved[7:] or 0) < 86400:
            return None
        found = self.candidates(title)
        if found is None:  # Trakt can't be reached: not remembered
            return None
        picked = pickShow(title, year, found)
        if picked:
            self.store.setMeta(key, picked)
            return int(picked)
        self.store.setMeta(key, 'unsure:%d' % int(self.clock()))
        self.unresolved = True
        return None

    def isSkipped(self, showKey):
        """True when the user said that the show is not on Trakt"""
        return str(self.store.getMeta('traktShow:%s' % showKey) or '') == SKIPPED

    def chooseShow(self, showKey, traktId):
        """Remembers the show the user chose on Trakt; None as the id remembers that it is not on Trakt (not scrobbled)"""
        self.store.setMeta('traktShow:%s' % showKey, int(traktId) if traktId else SKIPPED)

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
        self._forget()
        self.store.deleteMeta('traktShow:')

    def _token(self):
        if not self.isConnected():
            return None
        try:
            expires = int(self.store.getMeta(EXPIRES) or 0)
        except ValueError:
            expires = 0
        if expires - self.clock() < REFRESH_MARGIN and not self.refresh() and self.lastStatus in (400, 401, 403):
            self._forget()  # the access was withdrawn: stop using the account
            return None
        return self.store.getMeta(ACCESS)

    def scrobble(self, action, body):
        """`action` is start, pause or stop; returns the HTTP status (0: not connected or unreachable)"""
        token = self._token()
        if not token:
            return 0
        if not self._pace():
            return 429
        status, _ = self._call('/scrobble/%s' % action, body, token)
        if status == 401:
            if self.refresh():
                status, _ = self._call('/scrobble/%s' % action, body, self.store.getMeta(ACCESS))
            elif self.lastStatus in (400, 401, 403):
                self._forget()  # the access was withdrawn: stop using the account
        return status
