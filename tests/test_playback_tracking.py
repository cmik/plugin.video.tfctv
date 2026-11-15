# -*- coding: utf-8 -*-
"""Tests of the playback progress: storage, resume decision, tracker, and what the lists get"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402  (fakes the Kodi control module)
from test_userdata import episode, show  # noqa: E402
import test_catalog_modules  # noqa: E402  (loads the catalog modules with Kodi faked)

from resources.lib.libraries import playertracker  # noqa: E402
from resources.lib.models import userdata  # noqa: E402

history = test_catalog_modules.MODULES['history']
db = test_catalog_modules.MODULES['db']


class UserDataProgressTest(unittest.TestCase):

    def setUp(self):
        self.ud = userdata.UserData(os.path.join(tempfile.mkdtemp(), 'userdata.db'))

    def test_set_get_clear(self):
        self.ud.setProgress('e1', 300, 1800)
        self.ud.setProgress('e1', 600, 1800)  # the last position wins
        self.ud.setProgress('e2', 90, 900)
        self.assertEqual({'e1': (600, 1800), 'e2': (90, 900)}, self.ud.getProgress(['e1', 'e2', 'e3']))
        self.ud.clearProgress('e1')
        self.assertEqual({'e2': (90, 900)}, self.ud.getProgress(['e1', 'e2']))
        self.assertEqual({}, self.ud.getProgress([]))

    def test_list_with_what_was_kept_of_the_view(self):
        self.ud.addToHistory('e1', 's1', 'Title 1', 'Show', 'thumb', 'episode')
        self.ud.setProgress('e1', 100, 1000)
        self.ud.setProgress('e2', 50, 500)  # never recorded in the history
        rows = dict((r['episodeid'], r) for r in self.ud.getProgressList())
        self.assertEqual(('Title 1', 'thumb', 100, 1000), (rows['e1']['title'], rows['e1']['thumbnail'], rows['e1']['position'], rows['e1']['total']))
        self.assertEqual(('', 50), (rows['e2']['title'], rows['e2']['position']))
        self.assertEqual(2, self.ud.countProgress())

    def test_forgetting_the_history_forgets_the_progress(self):
        self.ud.addToHistory('e1', 's1', 't', 's', '', 'episode')
        self.ud.addToHistory('e2', 's1', 't', 's', '', 'episode')
        self.ud.setProgress('e1', 100, 1000)
        self.ud.setProgress('e2', 100, 1000)
        self.ud.removeFromHistory('e1')
        self.assertEqual({'e2'}, set(self.ud.getProgress(['e1', 'e2'])))
        self.ud.clearHistory()
        self.assertEqual(0, self.ud.countProgress())


class DecisionTest(unittest.TestCase):

    def test_decide(self):
        self.assertEqual('progress', playertracker.decide(600, 1800))
        self.assertEqual('completed', playertracker.decide(1700, 1800))  # past 90 %
        self.assertEqual('completed', playertracker.decide(10, 1800, ended=True))
        self.assertIsNone(playertracker.decide(10, 1800))  # not worth resuming
        self.assertIsNone(playertracker.decide(600, 0))  # unknown length

    def test_what_the_plugin_hands_to_the_service(self):
        raw = playertracker.encode('e1', now=1000)
        self.assertEqual('e1', playertracker.decode(raw, now=1050)['id'])
        self.assertIsNone(playertracker.decode(raw, now=1000 + playertracker.MAX_DELAY + 1))  # stale: nothing was played
        for bad in ('', None, 'not json', '{"id": ""}', '[]'):
            self.assertIsNone(playertracker.decode(bad, now=1000))


class TrackerTest(unittest.TestCase):

    def setUp(self):
        path = os.path.join(tempfile.mkdtemp(), 'userdata.db')
        self.tracker = playertracker.PlaybackTracker(lambda: userdata.UserData(path))
        self.ud = userdata.UserData(path)

    def play(self, position, total, ended=False, episodeId='e1'):
        self.tracker.start(episodeId)
        self.tracker.update(position, total)
        return self.tracker.finish(ended)

    def test_stopped_in_the_middle_keeps_the_position(self):
        self.assertEqual('progress', self.play(600, 1800))
        self.assertEqual({'e1': (600, 1800)}, self.ud.getProgress(['e1']))
        self.assertFalse(self.tracker.active)

    def test_finishing_forgets_the_position(self):
        self.play(600, 1800)
        self.assertEqual('completed', self.play(1790, 1800))
        self.assertEqual({}, self.ud.getProgress(['e1']))

    def test_ended(self):
        self.play(600, 1800)
        self.assertEqual('completed', self.play(1000, 1800, ended=True))
        self.assertEqual({}, self.ud.getProgress(['e1']))

    def test_short_or_unknown_plays_store_nothing(self):
        self.assertIsNone(self.play(5, 1800))
        self.assertIsNone(self.play(0, 0))
        self.assertEqual(0, self.ud.countProgress())

    def test_nothing_started(self):
        self.assertIsNone(self.tracker.finish(True))
        self.tracker.update(600, 1800)
        self.assertEqual(0, self.tracker.position)


class ListsTest(unittest.TestCase):

    def setUp(self):
        self.ud = userdata.UserData(os.path.join(tempfile.mkdtemp(), 'userdata.db'))
        for model in (db.showDB, db.episodeDB):
            model._userdata = self.ud
            model.drop()

    def test_episodes_read_from_the_database_carry_their_resume_point(self):
        db.episodeDB.set([episode(1), episode(2)])
        self.ud.setProgress('e1', 600, 1800)
        found = dict((e['id'], e) for e in db.episodeDB.getAll())
        self.assertEqual((600, 1800), (found['e1']['resumeposition'], found['e1']['totaltime']))
        self.assertEqual((0, 0), (found['e2']['resumeposition'], found['e2']['totaltime']))

    def test_continue_watching(self):
        db.showDB.set([show(1)])
        db.episodeDB.set([dict(episode(1), title='From the catalog')])
        history.recordView({'id': 'e1', 'parentid': 's1', 'title': 'Played', 'show': 'Show 1', 'image': 'thumb', 'ltype': 'episode'})
        history.recordView({'id': 'e2', 'parentid': 'gone', 'title': 'Kept title', 'show': 'Kept', 'image': 'thumb2', 'ltype': 'movie'})
        self.ud.setProgress('e1', 600, 1800)
        self.ud.setProgress('e2', 90, 5400)
        items = dict((i['id'], i) for i in history.getContinueWatching(1, 8))
        self.assertEqual(('From the catalog', 600, 1800), (items['e1']['title'], items['e1']['resumeposition'], items['e1']['totaltime']))
        self.assertEqual(('Kept title', 'movie', 90, 5400), (items['e2']['title'], items['e2']['ltype'], items['e2']['resumeposition'], items['e2']['totaltime']))
        self.assertFalse(history.hasNextContinueWatchingPage(1, 8))
        self.assertTrue(history.hasNextContinueWatchingPage(1, 1))


if __name__ == '__main__':
    unittest.main()
