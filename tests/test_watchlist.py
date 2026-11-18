# -*- coding: utf-8 -*-
"""Tests of the synchronisation of My List with the watchlist of iWant"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import test_catalog_modules  # noqa: E402  (loads the catalog modules with the Kodi side faked)
import test_userdata  # noqa: E402
from resources.lib.libraries import watchlist as plan  # noqa: E402

wl = test_catalog_modules.MODULES['watchlist']
db = test_catalog_modules.MODULES['db']
control = test_userdata.control


class PlanTest(unittest.TestCase):

    def test_differences(self):
        self.assertEqual((['a'], ['c']), plan.differences(['a', 'b'], ['b', 'c']))
        self.assertEqual(([], []), plan.differences(['a', 'a'], ['a']))

    def test_merge_removes_nothing(self):
        self.assertEqual({'localAdd': ['c'], 'localRemove': [], 'remoteAdd': ['a'], 'remoteRemove': []}, plan.plan(plan.MERGE, ['a', 'b'], ['b', 'c']))

    def test_overwrite_kodi(self):
        self.assertEqual({'localAdd': ['c'], 'localRemove': ['a'], 'remoteAdd': [], 'remoteRemove': []}, plan.plan(plan.KODI, ['a', 'b'], ['b', 'c']))

    def test_overwrite_iwant(self):
        self.assertEqual({'localAdd': [], 'localRemove': [], 'remoteAdd': ['a'], 'remoteRemove': ['c']}, plan.plan(plan.IWANT, ['a', 'b'], ['b', 'c']))

    def test_unknown_mode(self):
        with self.assertRaises(ValueError):
            plan.plan('x', [], [])


def show(i, name=None):
    return {'id': i, 'name': name or i, 'stored': True}


class SyncTest(unittest.TestCase):

    def setUp(self):
        self.userData = db.showDB.getUserData()
        for showId, _ in self.userData.getMyList():
            self.userData.removeFromMyList(showId)
        self.userData.setMeta(wl.SYNCED, '')
        self.added, self.removed, self.alerts, self.notes = [], [], [], []
        self.remote = []
        self.choice, self.confirm = 0, True
        wl.getRemoteWatchlist = lambda: self.remote
        wl.addToRemote = lambda i: self.added.append(i) or True
        wl.removeFromRemote = lambda i: self.removed.append(i) or True
        wl.keepFound = lambda found: found
        control.lang = lambda number: '%s' if number == 30264 else '%s %s'
        control.selectDialog = lambda items, heading='': self.choice
        control.yesnoDialog = lambda message: self.confirm
        control.alert = lambda message, *a, **k: self.alerts.append(message)
        control.showNotification = lambda message, *a, **k: self.notes.append(message)

    def local(self):
        return [i for i, _ in self.userData.getMyList()]

    def test_same_lists_are_marked_synchronized(self):
        self.userData.addToMyList('a', 'A')
        self.remote = [show('a')]
        self.assertTrue(wl.syncWatchlist())
        self.assertTrue(wl.isSynced())
        self.assertEqual(([], []), (self.added, self.removed))

    def test_merge(self):
        self.userData.addToMyList('a', 'A')
        self.remote = [show('b')]
        self.choice = 0
        self.assertTrue(wl.syncWatchlist())
        self.assertEqual(['a', 'b'], sorted(self.local()))
        self.assertEqual((['a'], []), (self.added, self.removed))

    def test_overwrite_kodi(self):
        self.userData.addToMyList('a', 'A')
        self.remote = [show('b')]
        self.choice = 1
        self.assertTrue(wl.syncWatchlist())
        self.assertEqual(['b'], self.local())
        self.assertEqual(([], []), (self.added, self.removed))

    def test_overwrite_iwant(self):
        self.userData.addToMyList('a', 'A')
        self.remote = [show('b')]
        self.choice = 2
        self.assertTrue(wl.syncWatchlist())
        self.assertEqual(['a'], self.local())
        self.assertEqual((['a'], ['b']), (self.added, self.removed))

    def test_refused_confirmation_changes_nothing(self):
        self.userData.addToMyList('a', 'A')
        self.remote = [show('b')]
        self.choice, self.confirm = 2, False
        self.assertFalse(wl.syncWatchlist())
        self.assertEqual(['a'], self.local())
        self.assertEqual(([], []), (self.added, self.removed))
        self.assertFalse(wl.isSynced())

    def test_cancel(self):
        self.userData.addToMyList('a', 'A')
        self.remote = [show('b')]
        self.choice = -1
        self.assertFalse(wl.syncWatchlist())
        self.assertEqual(['a'], self.local())

    def test_watchlist_unreadable(self):
        self.remote = None
        self.assertFalse(wl.syncWatchlist())
        self.assertEqual(1, len(self.alerts))

    def test_failed_push_is_not_marked_synchronized(self):
        self.userData.addToMyList('a', 'A')
        self.remote = [show('b')]
        wl.addToRemote = lambda i: False
        self.assertFalse(wl.syncWatchlist())
        self.assertEqual(1, len(self.alerts))
        self.assertTrue(wl.isSynced())  # what failed comes with the next synchronization, the changes after it are sent

    def test_a_channel_is_not_sent_to_iwant(self):
        formatters = test_catalog_modules.MODULES['formatters']
        db.showDB.set(formatters.formatAssetToShow({'id': 'ch', 'assetType': 'channel', 'title': 'A channel', 'images': {}}))
        self.userData.addToMyList('ch', 'A channel')
        self.userData.addToMyList('a', 'A')
        self.remote = [show('b')]
        self.choice = 2  # iWant gets what Kodi has
        self.assertTrue(wl.syncWatchlist())
        self.assertEqual((['a'], ['b']), (self.added, self.removed))
        self.assertIn('ch', self.local())  # it stays in Kodi
        self.added[:] = []
        self.userData.setMeta(wl.SYNCED, '1')
        control.setting = lambda key: ''
        wl.pushChange('ch', True)
        self.assertEqual([], self.added)

    def test_changes_are_pushed_only_after_a_synchronization(self):
        control.setting = lambda key: ''
        self.assertTrue(wl.pushChange('a', True))
        self.assertEqual([], self.added)
        self.userData.setMeta(wl.SYNCED, '1')
        wl.pushChange('a', True)
        wl.pushChange('b', False)
        self.assertEqual((['a'], ['b']), (self.added, self.removed))
        control.setting = lambda key: 'false'
        wl.pushChange('c', True)
        self.assertEqual(['a'], self.added)


if __name__ == '__main__':
    unittest.main()
