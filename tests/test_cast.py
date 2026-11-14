# -*- coding: utf-8 -*-
"""Tests of the cast: API cast, actors of the old catalog and their import"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402  (fakes the Kodi control module)
from test_userdata import show  # noqa: E402

from resources.lib.libraries import legacycast  # noqa: E402
from resources.lib.models import showcast, shows, userdata  # noqa: E402

ROOT = test_userdata.ROOT


def names(rows):
    return [(r['name'], r['source']) for r in rows]


class CastTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cast = showcast.ShowCast(os.path.join(self.dir, 'celebrities.db'))
        self.cast._userdata = userdata.UserData(os.path.join(self.dir, 'userdata.db'))

    def test_old_database_is_migrated_and_purged(self):
        path = os.path.join(self.dir, 'old.db')
        db = sqlite3.connect(path)
        db.execute('CREATE TABLE SHOW_CAST (ID TEXT PRIMARY KEY, SHOWID TEXT, ACTORID TEXT, NAME TEXT, ROLE TEXT, THUMBNAIL TEXT, ORDR INTEGER, URL TEXT)')
        db.execute("INSERT INTO SHOW_CAST VALUES ('onthejob-id_a', 'onthejob', 'id_a', 'A', '', '', 1, '')")
        db.commit()
        db.close()
        cast = showcast.ShowCast(path)
        cast._userdata = self.cast._userdata
        self.assertEqual([('A', None)], names(cast.getByShow('onthejob')))
        self.assertEqual(1, cast.purgeUnsourced())
        self.assertEqual([], cast.getByShow('onthejob'))

    def test_api_cast_replaces_the_previous_refresh_and_old_duplicates(self):
        self.cast.addLegacyCast([('s1', 'Coco Martin', 1), ('s1', 'Old Actor', 2)])
        self.cast.replaceApiCast('s1', [{'name': 'Coco Martin', 'order': 0}, {'name': 'New Actor', 'order': 1}])
        self.assertEqual([('Coco Martin', 'api'), ('New Actor', 'api'), ('Old Actor', 'legacy')], names(self.cast.getCast('s1')))
        self.cast.replaceApiCast('s1', [{'name': 'Other', 'order': 0}])  # the next refresh
        self.assertEqual([('Other', 'api'), ('Old Actor', 'legacy')], names(self.cast.getCast('s1')))

    def test_legacy_import_is_idempotent_and_keeps_api_actors(self):
        self.cast.replaceApiCast('s1', [{'name': 'coco martin', 'order': 0}])
        self.assertEqual(1, self.cast.addLegacyCast([('s1', 'Coco Martin', 1), ('s1', 'Vice Ganda', 2)]))
        self.assertEqual(0, self.cast.addLegacyCast([('s1', 'Coco Martin', 1), ('s1', 'Vice Ganda', 2)]))
        self.assertEqual([('coco martin', 'api'), ('Vice Ganda', 'legacy')], names(self.cast.getCast('s1')))

    def test_search_by_actor(self):
        self.cast.addLegacyCast([('s1', 'Coco Martin', 1), ('s2', 'Coco Martin', 1)])
        self.assertEqual({'s1', 's2'}, set(r['showid'] for r in self.cast.searchByActorName('Coco')))

    def test_import_once(self):
        path = os.path.join(self.dir, 'legacy.json')
        json.dump({'format': 1, 'shows': {'s1': [['A', 1], ['B', 2]]}}, open(path, 'w'))
        self.cast.set({'showid': 'gone', 'castid': 'x', 'name': 'Stale', 'order': 1, 'source': None})  # stored without a source
        self.assertEqual(2, legacycast.importLegacyCast(self.cast, path))
        self.assertEqual(['A', 'B'], [r['name'] for r in self.cast.getCast('s1')])
        self.assertEqual([], self.cast.getByShow('gone'))
        self.assertEqual(0, legacycast.importLegacyCast(self.cast, path))

    def test_shipped_data(self):
        data = json.load(open(legacycast.DATA))
        self.assertEqual(1, data['format'])
        self.assertTrue(data['shows'])
        for showId, links in data['shows'].items():
            self.assertEqual(36, len(showId))  # ids of the current catalog (uuid)
            self.assertTrue(all(name.strip() for name, order in links))


class BuildLegacyCastTest(unittest.TestCase):

    def test_matches_by_slug_and_by_old_title(self):
        d = tempfile.mkdtemp()
        db = sqlite3.connect(os.path.join(d, 'cast.db'))
        db.execute('CREATE TABLE SHOW_CAST (SHOWID TEXT, NAME TEXT, ORDR INTEGER)')
        db.executemany('INSERT INTO SHOW_CAST VALUES (?, ?, ?)', [
            ('onthejob', 'Piolo', 1), ('247inlove', 'Alice', 1), ('247inlove', 'ALICE', 2), ('gone', 'Nobody', 1), ('dup', 'X', 1), ('onthejob', ' ', 2)])
        db.commit()
        db.close()
        old = sqlite3.connect(os.path.join(d, 'oldshows.db'))
        old.execute('CREATE TABLE SHOW (ID TEXT, TITLE TEXT)')
        old.executemany('INSERT INTO SHOW VALUES (?, ?)', [('247inlove', '24/7 in Love'), ('gone', 'Gone')])
        old.commit()
        old.close()
        new = sqlite3.connect(os.path.join(d, 'new.db'))
        new.execute('CREATE TABLE SHOW (ID TEXT, TITLE TEXT)')
        new.executemany('INSERT INTO SHOW VALUES (?, ?)', [('id1', 'On the Job'), ('id2', '24/7 In Love'), ('id3', 'Dup'), ('id4', 'DUP')])
        new.commit()
        new.close()
        out = os.path.join(d, 'out.json')
        subprocess.check_call([sys.executable, os.path.join(ROOT, '.github', 'scripts', 'build_legacy_cast.py'), os.path.join(d, 'cast.db'),
                               os.path.join(d, 'oldshows.db'), os.path.join(d, 'new.db'), out], stdout=subprocess.DEVNULL)
        self.assertEqual({'id1': [['Piolo', 1]], 'id2': [['Alice', 1]]}, json.load(open(out))['shows'])


if __name__ == '__main__':
    unittest.main()
