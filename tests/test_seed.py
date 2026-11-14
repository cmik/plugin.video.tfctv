# -*- coding: utf-8 -*-
"""Tests of the catalog seed: build_seed.py, then the installation of the seed it made"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402  (fakes the Kodi control module)
from test_userdata import show, episode  # noqa: E402

from resources.lib.libraries import seed  # noqa: E402
from resources.lib.models import episodes, shows, showcast, userdata  # noqa: E402

ROOT = test_userdata.ROOT


def makeProfile(directory, idPrefix, nbShows=120, nbEpisodes=1100):
    """A profile folder with catalog databases of the previous layout (user data in the columns)"""
    os.makedirs(directory, exist_ok=True)
    s = shows.Show(os.path.join(directory, 'shows.db'))
    e = episodes.Episode(os.path.join(directory, 'episodes.db'))
    c = showcast.ShowCast(os.path.join(directory, 'celebrities.db'))
    s.set([dict(show(i, 'Show %d' % i), id='%s%d' % (idPrefix, i)) for i in range(nbShows)])
    e.set([dict(episode(i), id='%se%d' % (idPrefix, i)) for i in range(nbEpisodes)])
    c.set([{'showid': 's1', 'castid': 'a1', 'name': 'Name', 'role': 'Role', 'thumbnail': 't', 'order': 1, 'url': 'u'}])
    for db in (s, e, c):
        db._dbcon.close()
    # what the previous versions stored in the catalog columns
    db = sqlite3.connect(os.path.join(directory, 'shows.db'))
    db.execute("UPDATE SHOW SET MYLIST = 'true', VIEWS = 9 WHERE ID = '%s1'" % idPrefix)
    db.commit()
    db.close()
    return directory


class SeedTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.source = makeProfile(os.path.join(self.tmp, 'source'), 'new-')
        self.out = os.path.join(self.tmp, 'out')
        subprocess.check_call([sys.executable, os.path.join(ROOT, '.github', 'scripts', 'build_seed.py'), self.source, self.out,
                               '--catalog-version', '2026-01-01'], stdout=subprocess.DEVNULL)
        self.url = 'file://%s/' % self.out
        # profile of a user of the previous version: other ids, My List and views in the columns
        self.profile = makeProfile(os.path.join(self.tmp, 'profile'), 'old-')
        self.targets = dict((n, os.path.join(self.profile, n)) for n in ('shows.db', 'episodes.db', 'celebrities.db'))
        self.userDataFile = os.path.join(self.profile, 'userdata.db')

    def titles(self, path):
        db = sqlite3.connect(path)
        try:
            return [r[0] for r in db.execute('SELECT ID FROM SHOW ORDER BY ID LIMIT 2')]
        finally:
            db.close()

    def test_manifest(self):
        manifest = json.load(open(os.path.join(self.out, 'manifest.json')))
        self.assertEqual((1, '2026-01-01', 120, 1100), (manifest['format'], manifest['catalogVersion'], manifest['counts']['shows'], manifest['counts']['episodes']))
        self.assertEqual(seed.fetchManifest(self.url)['sha256'], manifest['sha256'])

    def test_seed_has_no_user_data_and_source_is_untouched(self):
        with zipfile.ZipFile(os.path.join(self.out, 'catalog-seed.zip')) as z:
            z.extract('shows.db', self.tmp)
        db = sqlite3.connect(os.path.join(self.tmp, 'shows.db'))
        self.assertEqual(0, db.execute("SELECT COUNT(*) FROM SHOW WHERE MYLIST = 'true'").fetchone()[0])
        self.assertEqual(0, db.execute('SELECT SUM(VIEWS) FROM SHOW').fetchone()[0])
        db.close()
        db = sqlite3.connect(os.path.join(self.source, 'shows.db'))
        self.assertEqual(1, db.execute("SELECT COUNT(*) FROM SHOW WHERE MYLIST = 'true'").fetchone()[0])
        db.close()

    def test_install_remaps_my_list_by_title(self):
        # same titles, other ids: the show of My List is found again
        ud = userdata.UserData(self.userDataFile)
        ud.addToMyList('old-1', 'Show 1')
        ud.addToMyList('old-gone', 'A show that does not exist anymore')
        ud._dbcon.close()
        notFound, manifest = seed.installCatalogSeed(self.url, self.targets, self.userDataFile)
        self.assertEqual(['A show that does not exist anymore'], notFound)
        self.assertEqual('2026-01-01', manifest['catalogVersion'])
        self.assertTrue(self.titles(self.targets['shows.db'])[0].startswith('new-'))
        ud = userdata.UserData(self.userDataFile)
        self.assertEqual({'new-1', 'old-gone'}, set(ud.getMyListIds()))
        self.assertTrue(os.path.exists(self.targets['shows.db'] + '.bak'))
        self.assertEqual([], [f for f in os.listdir(self.profile) if f.startswith('tfctv-seed-')])

    def test_corrupted_download_leaves_databases_alone(self):
        zipPath = os.path.join(self.out, 'catalog-seed.zip')
        with open(zipPath, 'ab') as f:
            f.write(b'garbage')
        before = self.titles(self.targets['shows.db'])
        self.assertIsNone(seed.installCatalogSeed(self.url, self.targets, self.userDataFile))
        self.assertEqual(before, self.titles(self.targets['shows.db']))
        self.assertEqual([], [f for f in os.listdir(self.profile) if f.startswith('tfctv-seed-')])

    def test_unreachable_seed(self):
        self.assertIsNone(seed.installCatalogSeed('file://%s/nothing/' % self.tmp, self.targets, self.userDataFile))

    def test_failed_install_restores_the_databases(self):
        # the episodes database can't be replaced: the shows one, already replaced, goes back
        before = self.titles(self.targets['shows.db'])
        files = {'shows.db': os.path.join(self.tmp, 'a.db'), 'episodes.db': os.path.join(self.tmp, 'missing.db')}
        shutil.copyfile(os.path.join(self.source, 'shows.db'), files['shows.db'])
        with self.assertRaises(Exception):
            seed.install(files, self.targets)
        self.assertEqual(before, self.titles(self.targets['shows.db']))

    def test_reason(self):
        self.assertEqual('install', seed.seedReason(''))
        self.assertEqual('major', seed.seedReason('2.1.0'))
        self.assertEqual('major', seed.seedReason('1.6.1'))
        self.assertIsNone(seed.seedReason('3.0.2'))
        self.assertIsNone(seed.seedReason('3.1.0'))


if __name__ == '__main__':
    unittest.main()
