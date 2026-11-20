# -*- coding: utf-8 -*-
"""My List > My Shows Last Episodes: read from the stored episodes, the website is asked once per TTL"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_catalog_modules  # noqa: E402  (loads the catalog modules with the Kodi side faked)

catalog = test_catalog_modules.MODULES['catalog']
cache = catalog.cache


class FakeEpisodes(object):
    def __init__(self, stored):
        self.stored = stored

    def get(self, key, by='ID'):
        field = 'parentid' if by == 'SHOWID' else 'id'
        return [dict(e) for e in self.stored if e.get(field) == key]


def ep(i, show, title, number=1):
    return {'id': i, 'parentid': show, 'title': title, 'episodenumber': number, 'show': 'S'}


class LastEpisodesTest(unittest.TestCase):

    def setUp(self):
        self.saved = (catalog.episodeDB, catalog.getShow, catalog.getEpisodesPerPage)
        self.reads = []
        self.stored = []
        catalog.episodeDB = FakeEpisodes(self.stored)
        catalog.getShow = lambda showId, season='1', withEpisodes=False: self.reads.append((showId, season)) or {'id': showId}
        for key in list(cache.execCache) if hasattr(cache, 'execCache') else []:
            del cache.execCache[key]
        self.key = 0

    def tearDown(self):
        catalog.episodeDB, catalog.getShow, catalog.getEpisodesPerPage = self.saved

    def show(self, **k):
        self.key += 1
        return dict({'id': 'show-last-%s-%s' % (id(self), self.key), 'name': 'A show', 'ltype': 'show'}, **k)

    def test_the_last_episode_is_the_one_of_the_latest_season(self):
        show = self.show()
        self.stored += [ep('a', show['id'], 'S1 E30', 30), ep('b', show['id'], 'S2 E3', 3), ep('c', show['id'], 'S2 E2', 2)]
        self.assertEqual('b', catalog.lastEpisodeOf(show)['id'])

    def test_stored_episodes_are_read_from_the_website_once(self):
        show = self.show()
        self.stored.append(ep('a', show['id'], 'S1 E1'))
        catalog.lastEpisodeOf(show)
        catalog.lastEpisodeOf(show)
        self.assertEqual([(show['id'], 'all')], self.reads)  # all the seasons, once: the second opening reads the database only

    def test_nothing_stored_asks_the_website_each_time(self):
        show = self.show()
        self.assertIsNone(catalog.lastEpisodeOf(show))
        catalog.lastEpisodeOf(show)
        self.assertEqual(2, len(self.reads))

    def test_a_movie_comes_from_the_database(self):
        show = self.show(ltype='movie', name='A movie')
        self.stored.append({'id': show['id'], 'parentid': show['id'], 'title': 'x', 'episodenumber': 7})
        episode = catalog.lastEpisodeOf(show)
        self.assertEqual(('A movie', 1), (episode['title'], episode['episodenumber']))
        self.assertEqual([], self.reads)

    def test_list_is_sorted_by_title_and_leaves_out_shows_without_episode(self):
        shows = [self.show(), self.show(), self.show()]
        self.stored += [ep('z', shows[0]['id'], 'Zed'), ep('a', shows[1]['id'], 'Alpha')]
        saved = catalog.getMyListShows
        catalog.getMyListShows = lambda: shows
        try:
            self.assertEqual(['a', 'z'], [e['id'] for e in catalog.getMylistShowLastEpisodes()])
        finally:
            catalog.getMyListShows = saved


if __name__ == '__main__':
    unittest.main()
