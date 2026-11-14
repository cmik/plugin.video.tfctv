# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik

    The view counters of the versions before the view history existed flag episodes as viewed
    without a history entry: list them (without a date, after the dated ones) so the history and
    the flags agree.
'''

from resources.lib.libraries import control

logger = control.logger

FLAG = 'historyBackfilled'


def backfill(userData, episodeDB):
    """Add to the view history the episodes that have a view count but no history entry. Done once.
    Returns the number of added entries."""
    if userData.getMeta(FLAG) == '1':
        return 0
    listed = set(userData.getHistoryIds())
    missing = [i for i in userData.getViewedEpisodeIds() if i not in listed]
    added = 0
    for episode in (episodeDB.get(missing) if missing else []):
        userData.addToHistory(episode.get('id'), episode.get('parentid', ''), episode.get('title', ''), episode.get('show', ''),
                              episode.get('image', ''), episode.get('ltype', ''), viewed='')
        added += 1
    userData.setMeta(FLAG, 1)
    logger.logNotice('View history: %d played episodes added (%d without catalog data left out)' % (added, len(missing) - added))
    return added
