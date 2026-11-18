# -*- coding: utf-8 -*-

"""
My List and the watchlist of the iWant website: reading it, adding to it, removing from it, and the synchronisation
(the plan of each way to settle the differences is in libraries/watchlist.py)
"""

from resources import config
from resources.lib.libraries import control, watchlist
from .api import callJsonApi
from .catalog import keepFound, showDB
from .formatters import STORED_ASSETS, formatSearchResults
from .graphql import getWatchlist

logger = control.logger

# what iWant keeps in its watchlist (it answers 400 "invalid content type" for a channel or a live event)
SYNCABLE = ('show', 'movie', 'documentary')
SYNCED = 'watchlistSyncedAt'  # META of userdata.db: set once the two lists were settled (not before, nothing is sent)


def _headers():
    return [
        ('Authorization', 'Bearer %s' % control.setting('iWantUserAuthentication')),
        ('Referer', config.websiteSecuredUrl + '/'),
        ('Origin', config.websiteSecuredUrl),
        ('x-device-platform', 'web'),
        ('X-Device-SubPlatform', 'firefox'),
        ('X-IW-UserAgent', 'Name=iWant; Version=1.0.0; Platform=Web; OSVersion=14.0.0 Model=Chrome; BuildType=debug Environment=development'),
    ]


def _login():
    from .auth import login
    return login(quiet=True)


def getRemoteWatchlist():
    """The shows, movies and documentaries of the iWant watchlist, as the search formats them (what is neither is
    not synchronised); None when it can't be read"""
    data = getWatchlist(_headers())
    if not data and _login():
        # an expired token is not answered by a 401 here but by a 400 "Failed to get watchlist" inside a 200:
        # log in again, then ask once more
        data = getWatchlist(_headers())
    if not data:
        return None
    if data.get('hasNextPage'):
        logger.logWarning('Watchlist: only %s of %s items read' % (len(data.get('items') or []), data.get('totalItems')))
    return [f for f in formatSearchResults({'rails': [{'assets': {'items': data.get('items') or []}}]}) if f.get('stored')]


def addToRemote(showId):
    """Adds a show to the iWant watchlist; True when iWant accepted it"""
    answer = callJsonApi(config.uri['watchlist'], {'assetId': showId}, _headers(), useCache=False)
    return bool(answer and answer.get('assetId'))


def removeFromRemote(showId):
    """Removes a show from the iWant watchlist; True when iWant accepted it"""
    answer = callJsonApi('%s/%s' % (config.uri['watchlist'], showId), {}, _headers(), useCache=False, jsonData=False, method='DELETE')
    return bool(answer and answer.get('message') == 'success')


def syncable(ids):
    """The ids of `ids` iWant can keep: the ones the catalog knows as another kind of asset (a live channel...) are left out"""
    ids = list(ids)
    kinds = dict((s.get('id'), s.get('ltype')) for s in showDB.get(ids)) if ids else {}
    return [i for i in ids if kinds.get(i, 'show') in SYNCABLE]


def isSynced():
    return bool(showDB.getUserData().getMeta(SYNCED))


def pushChange(showId, inList):
    """Tells iWant about a change made in Kodi, when the synchronisation is on and was done once. False when
    iWant could not be reached (the next synchronisation settles it)."""
    if control.setting('syncWatchlist') == 'false' or not isSynced() or not syncable([showId]):
        return True
    try:
        return addToRemote(showId) if inList else removeFromRemote(showId)
    except Exception as e:
        logger.logError('Watchlist: %s' % e)
        return False


def syncWatchlist():
    """Tools > Synchronize My List with iWant: when the two lists differ, the user chooses how to settle them"""
    logger.logInfo('called function')
    userData = showDB.getUserData()
    remote = getRemoteWatchlist()
    if remote is None:
        control.alert(control.lang(30267))
        return False
    remoteIds = [f['id'] for f in remote]
    local = syncable(m[0] for m in userData.getMyList())  # what is not a show or a movie stays in Kodi only
    onlyLocal, onlyRemote = watchlist.differences(local, remoteIds)
    if not onlyLocal and not onlyRemote:
        userData.setMeta(SYNCED, '1')
        control.showNotification(control.lang(30268))
        return True
    choices = [(watchlist.MERGE, control.lang(30260)), (watchlist.KODI, control.lang(30261)), (watchlist.IWANT, control.lang(30262))]
    picked = control.selectDialog([c[1] for c in choices], control.lang(30259) % (len(onlyLocal), len(onlyRemote)))
    if picked < 0:
        return False
    mode = choices[picked][0]
    changes = watchlist.plan(mode, local, remoteIds)
    removed = len(changes['localRemove']) + len(changes['remoteRemove'])
    if removed and not control.yesnoDialog(control.lang(30263) % (len(changes['localRemove']), len(changes['remoteRemove']))):
        return False
    failures = 0
    titles = dict((f['id'], f.get('name') or '') for f in remote)
    if changes['localAdd']:
        keepFound([f for f in remote if f['id'] in changes['localAdd']])  # the shows the catalog does not hold yet
        for showId in changes['localAdd']:
            userData.addToMyList(showId, titles.get(showId, ''))
    for showId in changes['localRemove']:
        userData.removeFromMyList(showId)
    for showId in changes['remoteAdd']:
        failures += 0 if addToRemote(showId) else 1
    for showId in changes['remoteRemove']:
        failures += 0 if removeFromRemote(showId) else 1
    userData.setMeta(SYNCED, '1')  # the lists were read and settled as far as iWant accepted: what failed comes with the next one
    if failures:
        control.alert(control.lang(30264) % failures)
        return False
    control.showNotification(control.lang(30265) % (len(changes['localAdd']) + len(changes['remoteAdd']), removed))
    return True
