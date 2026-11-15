# -*- coding: utf-8 -*-
"""Tests of the scheduled catch-up: when it is due, what it says, and the count of new episodes"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402  (fakes the Kodi control module)
from test_userdata import episode  # noqa: E402
import test_catalog_modules  # noqa: E402  (loads the catalog modules with Kodi faked)

from resources.lib.libraries import catchup  # noqa: E402
from resources.lib.models import userdata  # noqa: E402

catalog = test_catalog_modules.MODULES['catalog']
db = test_catalog_modules.MODULES['db']
HOUR = 3600


class DueTest(unittest.TestCase):

    def test_due(self):
        now = 1000000
        self.assertTrue(catchup.due(now - 25 * HOUR, now, 24))
        self.assertTrue(catchup.due(now - 24 * HOUR, now, 24))
        self.assertFalse(catchup.due(now - 23 * HOUR, now, 24))
        self.assertTrue(catchup.due(str(now - 7 * HOUR), now, '6'))  # settings come as strings

    def test_never_looked(self):
        for never in (None, '', 'garbage'):
            self.assertTrue(catchup.due(never, 1000000, 24))

    def test_switched_off(self):
        for hours in (0, '0', '', None, -1):
            self.assertFalse(catchup.due(None, 1000000, hours))

    def test_the_last_look_is_kept_in_the_user_data(self):
        ud = userdata.UserData(os.path.join(tempfile.mkdtemp(), 'userdata.db'))
        self.assertIsNone(ud.getMeta(catchup.META))
        ud.setMeta(catchup.META, 5000)
        self.assertFalse(catchup.due(ud.getMeta(catchup.META), 5000 + HOUR, 6))
        self.assertTrue(catchup.due(ud.getMeta(catchup.META), 5000 + 7 * HOUR, 6))

    def test_the_service_schedule(self):
        # it looks at the schedule every CHECK_EVERY seconds, the first time START_DELAY seconds after it starts
        ticks = [t for t in range(1, 200) if t * 10 >= catchup.START_DELAY and t % (catchup.CHECK_EVERY // 10) == catchup.START_DELAY // 10]
        self.assertEqual([12, 72, 132, 192], ticks)


class SummaryTest(unittest.TestCase):

    def test_summary(self):
        self.assertEqual('B (4), A (2)', catchup.episodesSummary({'A': 2, 'B': 4}))
        self.assertEqual('', catchup.episodesSummary({}))
        self.assertEqual('', catchup.episodesSummary({'A': 0}))

    def test_summary_is_limited(self):
        found = catchup.episodesSummary({'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}, limit=3)
        self.assertEqual('A (5), B (4), C (3), +2', found)

    def test_equal_counts_follow_the_title(self):
        self.assertEqual('A (1), B (1)', catchup.episodesSummary({'B': 1, 'A': 1}))


class NewEpisodesTest(unittest.TestCase):

    def setUp(self):
        ud = userdata.UserData(os.path.join(tempfile.mkdtemp(), 'userdata.db'))
        db.episodeDB._userdata = ud
        db.episodeDB.drop()

    def test_store_episodes_counts_the_new_ones(self):
        self.assertEqual(0, catalog.storeEpisodes([]))
        self.assertEqual(2, catalog.storeEpisodes([episode(1), episode(2)]))
        self.assertEqual(1, catalog.storeEpisodes([episode(1), episode(2), episode(3)]))  # only e3 is new
        self.assertEqual(0, catalog.storeEpisodes([episode(1), episode(3)]))  # known episodes are updated, not counted
        self.assertEqual(0, catalog.storeEpisodes([{'no': 'id'}, None]))


if __name__ == '__main__':
    unittest.main()
