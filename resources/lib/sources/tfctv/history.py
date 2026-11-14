# -*- coding: utf-8 -*-

"""
View history: what the user played (stored in the user data database)
"""

from resources.lib.libraries import control
from resources.lib.models import userdata
from .db import episodeDB, showDB

logger = control.logger


def recordView(episode):
    """Add a played episode (or movie) to the view history. `episode` is the dict built when playing."""
    if not episode or not episode.get('id'):
        return False
    return showDB.getUserData().addToHistory(
        episode.get('id'), episode.get('parentid', ''), episode.get('title', ''), episode.get('show', ''),
        episode.get('image', ''), episode.get('ltype', ''))


def getEpisodeViews(episodeId):
    """How many times an episode was played"""
    return showDB.getUserData().getViews(userdata.EPISODE, episodeId)


def _items(rows):
    """Episode dicts the navigator can list for rows of the user data database: what the catalog knows
    about the episode, else what was kept when it was played"""
    userData = showDB.getUserData()
    ids = [r['episodeid'] for r in rows]
    known = dict((e['id'], e) for e in episodeDB.get(ids)) if ids else {}
    stats = userData.getStats(userdata.EPISODE, ids) if ids else {}
    progress = userData.getProgress(ids) if ids else {}
    showIds = [r['showid'] for r in rows if r['showid']]
    shows = dict((s['id'], s) for s in showDB.get(showIds)) if showIds else {}
    items = []
    for row in rows:
        if row['episodeid'] in known:
            item = dict(known[row['episodeid']])
        else:
            views, rating, votes = stats.get(row['episodeid'], (0, 0, 0))
            position, total = progress.get(row['episodeid'], (0, 0))
            item = {
                'id': row['episodeid'], 'title': row['title'], 'parentid': row['showid'], 'show': row['show'], 'image': row['thumbnail'],
                'fanart': '', 'episodenumber': 0, 'url': row['episodeid'], 'description': '', 'shortdescription': '', 'dateaired': '',
                'date': '', 'year': '', 'ltype': row['ltype'] or 'episode', 'type': 'episode', 'duration': 0,
                'views': views, 'rating': rating, 'votes': votes, 'resumeposition': position, 'totaltime': total}
        item['dateviewed'] = row['viewed']
        show = shows.get(item.get('parentid') or row['showid'])
        if show:
            item['showObj'] = show
        items.append(item)
    return items


def getViewHistory(page=1, itemsPerPage=8):
    """The page of the view history, the last viewed first"""
    return _items(showDB.getUserData().getHistory(itemsPerPage, max(int(page) - 1, 0) * itemsPerPage))


def getContinueWatching(page=1, itemsPerPage=8):
    """The page of the episodes that can be resumed, the last played first"""
    return _items(showDB.getUserData().getProgressList(itemsPerPage, max(int(page) - 1, 0) * itemsPerPage))


def hasNextContinueWatchingPage(page, itemsPerPage):
    return showDB.getUserData().countProgress() > int(page) * itemsPerPage


def hasNextViewHistoryPage(page, itemsPerPage):
    return showDB.getUserData().countHistory() > int(page) * itemsPerPage


def removeFromViewHistory(episodeId):
    return showDB.getUserData().removeFromHistory(episodeId)


def clearViewHistory():
    return showDB.getUserData().clearHistory()
