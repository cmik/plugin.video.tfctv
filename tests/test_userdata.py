# -*- coding: utf-8 -*-
"""Tests of the models outside Kodi: python -m unittest discover -s tests"""

import os
import sqlite3
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class _Logger(object):
    def __getattr__(self, name):
        return lambda message, *a, **k: message


# the models import resources.lib.libraries.control, which needs Kodi: replace it
control = types.ModuleType('resources.lib.libraries.control')
control.logger = _Logger()
libraries = types.ModuleType('resources.lib.libraries')
libraries.control = control
sys.modules['resources.lib.libraries'] = libraries
sys.modules['resources.lib.libraries.control'] = control

from resources.lib.models import episodes, shows, userdata  # noqa: E402


def show(i, name=None):
    return {'id': 's%d' % i, 'name': name or 'Show %d' % i, 'parentid': 'p', 'parentname': 'Cat', 'logo': 'l',
            'image': 'i', 'fanart': 'f', 'banner': 'b', 'url': 'u', 'description': 'd', 'shortdescription': 'd',
            'year': '2020', 'ltype': 'show', 'duration': 0, 'views': 0, 'rating': 0, 'votes': 0, 'mylist': ''}


def episode(i, showId='s1'):
    return {'id': 'e%d' % i, 'title': 'Episode %d' % i, 'parentid': showId, 'show': 'S', 'image': 'i', 'fanart': 'f',
            'episodenumber': i, 'url': 'u', 'description': 'd', 'shortdescription': 'd', 'date': '2020',
            'year': '2020', 'parentalAdvisory': 'G', 'ltype': 'episode', 'duration': 10, 'views': 0, 'rating': 0, 'votes': 0}


class ModelsTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ud = userdata.UserData(os.path.join(self.dir, 'userdata.db'))
        self.shows = shows.Show(os.path.join(self.dir, 'shows.db'))
        self.episodes = episodes.Episode(os.path.join(self.dir, 'episodes.db'))
        self.shows._userdata = self.episodes._userdata = self.ud

    def test_my_list(self):
        self.shows.set([show(1), show(2), show(3)])
        self.assertTrue(self.shows.update({'id': 's2', 'name': 'Show 2', 'mylist': 'true'}))
        self.assertEqual(['s2'], [s['id'] for s in self.shows.getMyList()])
        self.assertEqual(['true'], [s['mylist'] for s in self.shows.get('s2')])
        self.assertEqual(['false'], [s['mylist'] for s in self.shows.get('s1')])
        self.shows.update({'id': 's2', 'mylist': 'false'})
        self.assertEqual([], self.shows.getMyList())

    def test_catalog_replace_keeps_user_data(self):
        self.shows.set([show(1)])
        self.shows.update({'id': 's1', 'name': 'Show 1', 'mylist': 'true', 'views': 3})
        self.shows.set([show(1, 'Renamed')])  # refresh of the catalog
        found = self.shows.get('s1')[0]
        self.assertEqual(('Renamed', 'true', 3), (found['name'], found['mylist'], found['views']))

    def test_catalog_drop_keeps_user_data(self):
        self.shows.set([show(1)])
        self.episodes.set([episode(1)])
        self.shows.update({'id': 's1', 'name': 'Show 1', 'mylist': 'true'})
        self.episodes.update({'id': 'e1', 'views': 2})
        self.shows.drop()
        self.episodes.drop()
        self.shows.set([show(1)])
        self.episodes.set([episode(1)])
        self.assertEqual(['s1'], [s['id'] for s in self.shows.getMyList()])
        self.assertEqual(2, self.episodes.get('e1')[0]['views'])

    def test_my_list_show_missing_from_the_catalog(self):
        self.ud.addToMyList('gone', 'Gone')
        self.assertEqual([], self.shows.getMyList())
        self.assertEqual(['gone'], self.ud.getMyListIds())

    def test_episode_counters(self):
        self.episodes.set([episode(1), episode(2)])
        self.episodes.update({'id': 'e1', 'views': 4})
        self.episodes.update({'id': 'e1', 'rating': 5})  # the views are kept
        self.episodes.update({'id': 'e1', 'title': 'New title'})
        found = dict((e['id'], e) for e in self.episodes.getAll())
        self.assertEqual((4, 5, 0, 'New title'), (found['e1']['views'], found['e1']['rating'], found['e1']['votes'], found['e1']['title']))
        self.assertEqual(0, found['e2']['views'])

    def test_many_ids(self):
        self.shows.set([show(i) for i in range(1200)])
        for i in range(0, 1200, 3):
            self.ud.addToMyList('s%d' % i, 'x')
        self.assertEqual(400, len(self.shows.getMyList(limit=False)))
        self.assertEqual(1200, len(self.shows.getAll()))

    def test_normalize_title(self):
        self.assertEqual(userdata.normalizeTitle(u'Ang Probinsyano: Éxtra!'), userdata.normalizeTitle('ang probinsyano extra'))

    def test_replace_my_list_id(self):
        self.ud.addToMyList('old', 'Title')
        self.assertTrue(self.ud.replaceMyListId('old', 'new'))
        self.assertEqual([('new', 'Title')], self.ud.getMyList())
        self.assertFalse(self.ud.replaceMyListId('old', 'other'))


class LegacyImportTest(unittest.TestCase):

    def legacyDb(self, path, table, rows, myList=False):
        db = sqlite3.connect(path)
        db.execute('CREATE TABLE %s (ID TEXT PRIMARY KEY, TITLE TEXT, VIEWS INTEGER, RATING INTEGER, VOTES INTEGER%s)'
                   % (table, ', MYLIST TEXT' if myList else ''))
        for row in rows:
            db.execute('INSERT INTO %s VALUES (%s)' % (table, ','.join('?' * len(row))), row)
        db.commit()
        db.close()

    def test_import_once(self):
        d = tempfile.mkdtemp()
        showsPath, episodesPath = os.path.join(d, 'shows.db'), os.path.join(d, 'episodes.db')
        self.legacyDb(showsPath, 'SHOW', [('a', 'A', 5, 0, 0, 'true'), ('b', 'B', 0, 0, 0, 'false'), ('c', 'C', 0, 0, 0, None)], True)
        self.legacyDb(episodesPath, 'EPISODE', [('e1', 'E1', 2, 3, 4), ('e2', 'E2', 0, 0, 0)])
        ud = userdata.UserData(os.path.join(d, 'userdata.db'))
        self.assertEqual(3, ud.importLegacy(showsPath, episodesPath))
        self.assertEqual([('a', 'A')], ud.getMyList())
        self.assertEqual({'a': (5, 0, 0)}, ud.getStats(userdata.SHOW, ['a', 'b']))
        self.assertEqual({'e1': (2, 3, 4)}, ud.getStats(userdata.EPISODE, ['e1', 'e2']))
        # a second import changes nothing: an item removed from My List must not come back
        ud.removeFromMyList('a')
        self.assertEqual(0, ud.importLegacy(showsPath, episodesPath))
        self.assertEqual([], ud.getMyList())

    def test_missing_databases(self):
        d = tempfile.mkdtemp()
        ud = userdata.UserData(os.path.join(d, 'userdata.db'))
        self.assertEqual(0, ud.importLegacy(os.path.join(d, 'none1.db'), os.path.join(d, 'none2.db')))
        self.assertFalse(os.path.exists(os.path.join(d, 'none1.db')))


if __name__ == '__main__':
    unittest.main()
