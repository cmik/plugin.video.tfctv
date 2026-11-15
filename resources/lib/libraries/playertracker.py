# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik

    Follows what is played to keep where to resume. The plugin (a short-lived process) says what it
    starts through a window property; the service, which keeps running, watches the player.
'''

import json
import time

from resources.lib.libraries import control

logger = control.logger

PROPERTY = 'tfctv.nowplaying'
# the played item carries the episode id too: nothing to expire, nothing to clear
ITEM_PROPERTY = 'tfctv.episodeid'
# a started playback is only taken into account if it starts within this delay (seconds)
MAX_DELAY = 120
# below this position (seconds) there is nothing worth resuming
MIN_RESUME = 30
# beyond this part of the episode, it is considered finished
COMPLETED = 0.9


def encode(episodeId, now=None):
    return json.dumps({'id': str(episodeId), 'time': int(time.time() if now is None else now)})


def decode(raw, now=None):
    """What `encode` produced, or None when there is nothing usable (empty, corrupted, too old)"""
    try:
        data = json.loads(raw)
        if not data.get('id') or (time.time() if now is None else now) - int(data.get('time', 0)) > MAX_DELAY:
            return None
        return data
    except (TypeError, ValueError, AttributeError):
        return None


def decide(position, total, ended=False):
    """'completed' (nothing to resume), 'progress' (resume from the position) or None (not worth keeping)"""
    if ended or (total > 0 and position >= total * COMPLETED):
        return 'completed'
    if total > 0 and position >= MIN_RESUME:
        return 'progress'
    return None


class PlaybackTracker(object):
    """Keeps the last known position of what is played and stores the outcome when it stops.
    `userDataFactory` gives a user data database (one per call: callers run on several threads)."""

    def __init__(self, userDataFactory):
        self.userDataFactory = userDataFactory
        self.episodeId = None
        self.position = 0
        self.total = 0

    @property
    def active(self):
        return self.episodeId is not None

    def start(self, episodeId):
        self.episodeId, self.position, self.total = str(episodeId), 0, 0

    def update(self, position, total):
        if self.active and total and total > 0:
            self.position, self.total = int(position), int(total)

    def finish(self, ended=False):
        """Store the outcome of what was played; returns it ('completed', 'progress' or None)"""
        if not self.active:
            return None
        episodeId, position, total = self.episodeId, self.position, self.total
        self.episodeId = None
        outcome = decide(position, total, ended)
        if outcome is None:
            return None
        userData = self.userDataFactory()
        if outcome == 'completed':
            userData.clearProgress(episodeId)
        elif outcome == 'progress':
            userData.setProgress(episodeId, position, total)
        logger.logInfo('Playback of %s: %s (%d/%d s)' % (episodeId, outcome, position, total))
        return outcome
