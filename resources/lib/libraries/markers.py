# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik

    Skip intro / Skip recap: iWant gives, with the playback of some episodes, the markers of the intro, the recap
    and the outro (`markers` of the answer to /entitlement/playback/start, times in milliseconds). The plugin hands
    them to the service through a property of the played item; the service follows the position of the player and
    offers (or does) the skip. The decisions are made here, apart from Kodi, so that they can be tested.
'''

import json

PROPERTY = 'tfctv.markers'
INTRO, RECAP, OUTRO = 'intro', 'recap', 'outro'
KINDS = (INTRO, RECAP, OUTRO)
SKIPPABLE = (INTRO, RECAP)
# the settings: what to do with an intro or a recap
ASK, AUTO, OFF = 0, 1, 2
SETTINGS = {INTRO: 'skipIntro', RECAP: 'skipRecap'}
# a marker is offered a bit before it starts (the recap comes right after the intro) and nothing is left to skip in its last second
LEAD = 1.0


def parse(raw):
    """The markers of the answer of iWant as [{'kind', 'start', 'end'}] in seconds, ordered; what is not usable is left out"""
    found = []
    for item in raw if isinstance(raw, list) else []:
        try:
            kind, start, end = item.get('id'), float(item.get('startTs')) / 1000.0, float(item.get('endTs')) / 1000.0
        except (AttributeError, TypeError, ValueError):
            continue
        if kind in KINDS and 0 <= start < end:
            found.append({'kind': kind, 'start': start, 'end': end})
    return sorted(found, key=lambda m: m['start'])


def encode(found):
    return json.dumps(found, separators=(',', ':')) if found else ''


def decode(raw):
    try:
        return parse([{'id': m['kind'], 'startTs': m['start'] * 1000, 'endTs': m['end'] * 1000} for m in json.loads(raw)])
    except (TypeError, ValueError, KeyError):
        return []


def outroStart(found, total):
    """Seconds before the end where the outro starts (when Up Next should offer the next episode), or None"""
    for m in found:
        if m['kind'] == OUTRO and total and 0 < total - m['start'] < total:
            return int(total - m['start'])
    return None


def modeOf(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return ASK


class SkipController(object):
    """Follows the position and says what to do: ('offer', marker) shows the button, ('skip', marker) skips,
    ('hide', None) takes the button away; None when nothing changes. `modes` gives ASK/AUTO/OFF by kind."""

    def __init__(self, found, modes):
        self.markers = [m for m in found if m['kind'] in SKIPPABLE and modes.get(m['kind'], ASK) != OFF]
        self.modes = modes
        self.offered = None
        self.done = set()  # (kind, start) already skipped: going back in the video does not skip it again

    def active(self, position):
        for m in self.markers:
            if (m['kind'], m['start']) not in self.done and m['start'] - LEAD <= position < m['end'] - LEAD:
                return m
        return None

    def tick(self, position):
        m = self.active(position)
        if m is None:
            if self.offered:
                self.offered = None
                return ('hide', None)
            return None
        if self.modes.get(m['kind'], ASK) == AUTO:
            self.done.add((m['kind'], m['start']))
            return ('skip', m)
        if self.offered is not m:
            self.offered = m
            return ('offer', m)
        return None

    def skipped(self, m):
        """The viewer chose to skip `m` (the button): it is not offered again"""
        self.done.add((m['kind'], m['start']))
        self.offered = None
