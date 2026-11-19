# -*- coding: utf-8 -*-
"""Tests of Skip intro / Skip recap: the markers of iWant and what to do at each position"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402,F401  (fakes the Kodi control module)

from resources.lib.libraries import markers  # noqa: E402

# the markers iWant gave for Coco Martin's Sigabo S1 E100 (milliseconds)
SIGABO = [
    {'id': 'intro', 'label': 'Skip Intro', 'startTs': 5072, 'endTs': 79846},
    {'id': 'outro', 'label': 'Next Episode', 'startTs': 1763962, 'endTs': 1837936},
    {'id': 'recap', 'label': 'Skip Recap', 'startTs': 79880, 'endTs': 120420},
]
ASK_ALL = {'intro': markers.ASK, 'recap': markers.ASK}


class ParseTest(unittest.TestCase):

    def test_seconds_and_order(self):
        found = markers.parse(SIGABO)
        self.assertEqual(['intro', 'recap', 'outro'], [m['kind'] for m in found])
        self.assertAlmostEqual(79.846, found[0]['end'])

    def test_unusable_markers_are_left_out(self):
        junk = [None, {}, {'id': 'intro'}, {'id': 'intro', 'startTs': 'x', 'endTs': 5}, {'id': 'ad', 'startTs': 0, 'endTs': 5},
                {'id': 'intro', 'startTs': 5000, 'endTs': 5000}, {'id': 'recap', 'startTs': 0, 'endTs': 4000}]
        self.assertEqual(['recap'], [m['kind'] for m in markers.parse(junk)])
        self.assertEqual([], markers.parse(None))
        self.assertEqual([], markers.parse([]))

    def test_property_round_trip(self):
        found = markers.parse(SIGABO)
        self.assertEqual(found, markers.decode(markers.encode(found)))
        self.assertEqual('', markers.encode([]))
        self.assertEqual([], markers.decode(''))
        self.assertEqual([], markers.decode('not json'))

    def test_outro_for_up_next(self):
        found = markers.parse(SIGABO)
        self.assertEqual(int(1900 - 1763.962), markers.outroStart(found, 1900))
        self.assertIsNone(markers.outroStart(found, 0))
        self.assertIsNone(markers.outroStart(found, 1000))  # the outro would start after the end
        self.assertIsNone(markers.outroStart(markers.parse(SIGABO[:1]), 1900))

    def test_mode_of_a_setting(self):
        self.assertEqual(markers.AUTO, markers.modeOf('1'))
        self.assertEqual(markers.ASK, markers.modeOf(''))
        self.assertEqual(markers.ASK, markers.modeOf(None))


class ControllerTest(unittest.TestCase):

    def controller(self, **modes):
        return markers.SkipController(markers.parse(SIGABO), dict(ASK_ALL, **modes))

    def test_the_outro_is_never_skipped(self):
        self.assertEqual(['intro', 'recap'], [m['kind'] for m in self.controller().markers])

    def test_nothing_before_the_intro_and_between(self):
        c = self.controller()
        self.assertIsNone(c.tick(2))
        self.assertIsNone(c.tick(300))

    def test_the_button_is_offered_once_then_hidden(self):
        c = self.controller()
        what, m = c.tick(4.5)
        self.assertEqual(('offer', 'intro'), (what, m['kind']))
        self.assertIsNone(c.tick(10))
        self.assertIsNone(c.tick(60))
        self.assertEqual(('hide', None), c.tick(300))
        self.assertIsNone(c.tick(301))

    def test_intro_then_recap_follow_each_other(self):
        c = self.controller()
        c.tick(10)
        what, m = c.tick(79.5)  # the recap starts a hair after the intro ends
        self.assertEqual(('offer', 'recap'), (what, m['kind']))

    def test_clicked_is_not_offered_again(self):
        c = self.controller()
        _, m = c.tick(10)
        c.skipped(m)
        self.assertIsNone(c.tick(10))  # back in the video
        self.assertEqual('recap', c.tick(79.6)[1]['kind'])

    def test_auto_skips_once(self):
        c = self.controller(intro=markers.AUTO)
        what, m = c.tick(5)
        self.assertEqual(('skip', 'intro', 79.846), (what, m['kind'], m['end']))
        self.assertIsNone(c.tick(5))  # the viewer went back: it is not skipped twice

    def test_off_leaves_the_kind_alone(self):
        c = self.controller(intro=markers.OFF)
        self.assertIsNone(c.tick(10))
        self.assertEqual(['recap'], [m['kind'] for m in c.markers])
        self.assertEqual([], self.controller(intro=markers.OFF, recap=markers.OFF).markers)

    def test_nothing_to_skip_in_the_last_second(self):
        c = markers.SkipController(markers.parse(SIGABO[:1]), ASK_ALL)
        self.assertEqual('intro', c.tick(78.8)[1]['kind'])
        c = markers.SkipController(markers.parse(SIGABO[:1]), ASK_ALL)
        self.assertIsNone(c.tick(78.9))  # a second before the end of the intro


if __name__ == '__main__':
    unittest.main()
