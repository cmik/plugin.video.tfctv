# -*- coding: utf-8 -*-
"""Tests of the view history: storage, listing, flags, removal and the upgrade backfill"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402  (fakes the Kodi control module)
from test_userdata import show, episode  # noqa: E402
import test_catalog_modules  # noqa: E402  (loads the catalog modules with Kodi faked)

from resources.lib.libraries import viewhistory  # noqa: E402
from resources.lib.models import userdata  # noqa: E402

history = test_catalog_modules.MODULES['history']
db = test_catalog_modules.MODULES['db']


class UserDataHistoryTest(unittest.TestCase):

    def setUp(self):
        self.ud = userdata.UserData(os.path.join(tempfile.mkdtemp(), 'userdata.db'))

    def add(self, episodeId, day, showId='s1'):
        self.ud.addToHistory(episodeId, showId, 'Title ' + episodeId, 'Show', 'thumb', 'episode', viewed='2026-01-%02d 10:00:00' % day)

    def test_last_viewed_first_and_once_per_episode(self):
        self.add('e1', 1)
        self.add('e2', 2)
        self.add('e1', 3)  # watched again: listed once, with its last view
        rows = self.ud.getHistory()
        self.assertEqual(['e1', 'e2'], [r['episodeid'] for r in rows])
        self.assertEqual('2026-01-03 10:00:00', rows[0]['viewed'])
        self.assertEqual(2, self.ud.countHistory())

    def test_pages(self):
        for i in range(5):
            self.add('e%d' % i, i + 1)
        self.assertEqual(['e4', 'e3'], [r['episodeid'] for r in self.ud.getHistory(2, 0)])
        self.assertEqual(['e2', 'e1'], [r['episodeid'] for r in self.ud.getHistory(2, 2)])
        self.assertEqual(['e0'], [r['episodeid'] for r in self.ud.getHistory(2, 4)])

    def test_remove_and_clear_reset_the_viewed_flag(self):
        for e in ('e1', 'e2'):
            self.add(e, 1)
            self.ud.setStats(userdata.EPISODE, e, views=3)
        self.ud.setStats(userdata.SHOW, 's1', views=5)
        self.ud.removeFromHistory('e1')
        self.assertEqual((0, 3), (self.ud.getViews(userdata.EPISODE, 'e1'), self.ud.getViews(userdata.EPISODE, 'e2')))
        self.assertEqual(['e2'], [r['episodeid'] for r in self.ud.getHistory()])
        self.ud.clearHistory()
        self.assertEqual((0, 0, []), (self.ud.getViews(userdata.EPISODE, 'e2'), self.ud.countHistory(), self.ud.getHistory()))
        self.assertEqual(5, self.ud.getViews(userdata.SHOW, 's1'))  # the shows' counters are not part of the history

    def test_history_is_trimmed(self):
        self.ud.historyLimit = 3
        for i in range(6):
            self.add('e%d' % i, i + 1)
        self.assertEqual(['e5', 'e4', 'e3'], [r['episodeid'] for r in self.ud.getHistory()])

    def test_titles_with_quotes(self):
        self.ud.addToHistory('e1', 's1', "O'Brien's \"show\"; DROP TABLE HISTORY;--", 'S', '', 'movie')
        self.assertEqual("O'Brien's \"show\"; DROP TABLE HISTORY;--", self.ud.getHistory()[0]['title'])


class ViewHistoryTest(unittest.TestCase):

    def setUp(self):
        self.ud = userdata.UserData(os.path.join(tempfile.mkdtemp(), 'userdata.db'))
        for model in (db.showDB, db.episodeDB):
            model._userdata = self.ud
            model.drop()
        self.ud.clearHistory()
        self.ud._exec(self.ud.getCursor(), 'DELETE FROM STATS')
        self.ud.historyLimit = 2000

    def test_record_then_list_with_what_the_catalog_knows(self):
        db.showDB.set([show(1)])
        db.episodeDB.set([dict(episode(1), title='From the catalog')])
        history.recordView({'id': 'e1', 'parentid': 's1', 'title': 'Played title', 'show': 'Show 1', 'image': 'thumb', 'ltype': 'episode'})
        db.episodeDB.update({'id': 'e1', 'views': 2})
        item = history.getViewHistory(1, 8)[0]
        self.assertEqual(('e1', 'From the catalog', 2), (item['id'], item['title'], item['views']))
        self.assertEqual('s1', item['showObj']['id'])
        self.assertTrue(item['dateviewed'])

    def test_list_survives_a_catalog_reset(self):
        history.recordView({'id': 'e9', 'parentid': 'gone', 'title': 'Kept title', 'show': 'Kept show', 'image': 'thumb', 'ltype': 'movie'})
        self.ud.setStats(userdata.EPISODE, 'e9', views=1)
        item = history.getViewHistory(1, 8)[0]
        self.assertEqual(('Kept title', 'Kept show', 'thumb', 'movie', 1), (item['title'], item['show'], item['image'], item['ltype'], item['views']))
        self.assertNotIn('showObj', item)

    def test_next_page_and_viewed_counter(self):
        for i in range(3):
            history.recordView({'id': 'e%d' % i, 'title': 't'})
        self.assertTrue(history.hasNextViewHistoryPage(1, 2))
        self.assertFalse(history.hasNextViewHistoryPage(2, 2))
        self.ud.setStats(userdata.EPISODE, 'e1', views=4)
        self.assertEqual((4, 0), (history.getEpisodeViews('e1'), history.getEpisodeViews('e0')))

    def test_nothing_to_record(self):
        self.assertFalse(history.recordView({}))
        self.assertFalse(history.recordView({'title': 'no id'}))

    def test_remove_from_history(self):
        history.recordView({'id': 'e1', 'title': 't'})
        self.ud.setStats(userdata.EPISODE, 'e1', views=1)
        history.removeFromViewHistory('e1')
        self.assertEqual(([], 0), (history.getViewHistory(), history.getEpisodeViews('e1')))

    def test_backfill_lists_episodes_that_only_had_a_counter(self):
        db.episodeDB.set([episode(1), episode(2), episode(3)])
        for e in ('e1', 'e2'):
            self.ud.setStats(userdata.EPISODE, e, views=2)
        self.ud.setStats(userdata.EPISODE, 'unknown', views=1)  # not in the catalog anymore
        history.recordView({'id': 'e2', 'title': 'already listed'})
        self.assertEqual(1, viewhistory.backfill(self.ud, db.episodeDB))
        self.assertEqual({'e1', 'e2'}, set(self.ud.getHistoryIds()))
        self.assertEqual(0, viewhistory.backfill(self.ud, db.episodeDB))  # once
        self.assertEqual('e2', history.getViewHistory()[0]['id'])  # dated entries first


if __name__ == '__main__':
    unittest.main()
