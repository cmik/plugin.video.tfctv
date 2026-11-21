# -*- coding: utf-8 -*-
"""My List > My Shows Last Episodes: the last episode is the one of the latest season"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_catalog_modules  # noqa: E402  (loads the catalog modules with the Kodi side faked)

catalog = test_catalog_modules.MODULES['catalog']


class FakeEpisodes(object):
    def __init__(self):
        self.stored = {}

    def get(self, key):
        return [dict(self.stored[key])] if key in self.stored else []

    def set(self, episode):
        self.stored[episode['id']] = episode

    def applyUserData(self, items):
        return items


class LastEpisodeTest(unittest.TestCase):

    def setUp(self):
        self.saved = (catalog.episodeDB, catalog.getShowWithEpisodes)
        catalog.episodeDB = self.db = FakeEpisodes()

    def tearDown(self):
        catalog.episodeDB, catalog.getShowWithEpisodes = self.saved

    def run_with(self, titles):
        episodes = [{'id': 'e%d' % i, 'title': t, 'episodenumber': n} for i, (t, n) in enumerate(titles)]
        asked = []
        catalog.getShowWithEpisodes = lambda showId, season='1': asked.append(season) or {'id': showId, 'episodes': episodes}
        episode = catalog.lastEpisodeOf({'id': 'show', 'ltype': 'show'})
        return episode, asked

    def test_latest_season_wins_over_the_highest_number(self):
        episode, asked = self.run_with([('S1 E30', 30), ('S2 E3', 3), ('S2 E2', 2)])
        self.assertEqual('e1', episode['id'])
        self.assertEqual(['all'], asked)  # all the seasons are read
        self.assertEqual('show', episode['showObj']['id'])

    def test_the_stored_episode_keeps_what_the_database_holds(self):
        self.db.set({'id': 'e1', 'title': 'S2 E3', 'views': 4})
        episode, _ = self.run_with([('S1 E30', 30), ('S2 E3', 3)])
        self.assertEqual(4, episode['views'])

    def test_a_show_without_episodes(self):
        self.assertIsNone(self.run_with([])[0])

    def test_the_list_is_sorted_by_title(self):
        saved = catalog.getMyListShows
        catalog.getMyListShows = lambda: [{'id': 'a'}, {'id': 'b'}]
        titles = {'a': 'S1 E2', 'b': 'S1 E1'}
        catalog.getShowWithEpisodes = lambda showId, season='1': {'id': showId, 'episodes': [{'id': showId, 'title': titles[showId], 'episodenumber': 1}]}
        try:
            self.assertEqual(['b', 'a'], [e['id'] for e in catalog.getMylistShowLastEpisodes()])
        finally:
            catalog.getMyListShows = saved


if __name__ == '__main__':
    unittest.main()
