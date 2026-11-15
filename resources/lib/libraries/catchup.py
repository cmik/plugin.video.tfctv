# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik

    Scheduled look for what is new in the catalog (new shows, new episodes of the shows of My List).
'''

META = 'catchUpAt'
# how often the service looks at the schedule (seconds) and how long it waits after it starts
CHECK_EVERY = 600
START_DELAY = 120


def due(last, now, hours):
    """Is it time to look for what is new? `last` is the time (epoch seconds, a number or a string) of the last
    look, nothing yet when empty; `hours` the wanted delay, 0 meaning never."""
    if not hours or int(hours) <= 0:
        return False
    try:
        return now - int(last) >= int(hours) * 3600
    except (TypeError, ValueError):
        return True


def episodesSummary(newEpisodes, limit=3):
    """'A (3), B (1) and 2 more' for {show title: number of new episodes}, the shows with most new episodes first"""
    items = sorted(((count, title) for title, count in newEpisodes.items() if count > 0), key=lambda i: (-i[0], i[1]))
    shown = ['%s (%d)' % (title, count) for count, title in items[:limit]]
    if len(items) > limit:
        shown.append('+%d' % (len(items) - limit))
    return ', '.join(shown)
