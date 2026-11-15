# -*- coding: utf-8 -*-
"""Tests of the Up Next data: which episode follows, what is sent and how"""

import base64
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402  (fakes the Kodi control module)
from test_userdata import episode, show  # noqa: E402
import test_catalog_modules  # noqa: E402  (loads the catalog modules with Kodi faked)

from resources.lib.libraries import upnext  # noqa: E402
from resources.lib.models import userdata  # noqa: E402

db = test_catalog_modules.MODULES['db']


def ep(title, number=1, **kwargs):
    # the episodes of a show are stored with the type of the show, as the catalog does
    return dict(episode(number), id=kwargs.pop('id', title), title=title, episodenumber=number, ltype=kwargs.pop('ltype', 'show'), **kwargs)


class OrderTest(unittest.TestCase):

    def test_season_then_episode(self):
        order = sorted([ep('S2 E1 - b'), ep('S1 E10 - c'), ep('S1 E2 - a'), ep('S1 E1 - z')], key=upnext.sortKey)
        self.assertEqual(['S1 E1 - z', 'S1 E2 - a', 'S1 E10 - c', 'S2 E1 - b'], [e['title'] for e in order])  # E10 after E2

    def test_titles_with_the_day(self):
        order = sorted([ep('Ep 2nd Nov 2026 - Episode 9'), ep('Ep 31st Oct 2026 - Episode 8'), ep('Ep 24th Oct 2026 - Episode 1'),
                        ep('Ep 1st Jan 2027 - Episode 10')], key=upnext.sortKey)
        self.assertEqual(['Ep 24th Oct 2026 - Episode 1', 'Ep 31st Oct 2026 - Episode 8', 'Ep 2nd Nov 2026 - Episode 9', 'Ep 1st Jan 2027 - Episode 10'],
                         [e['title'] for e in order])

    def test_other_titles_follow_the_episode_number(self):
        order = sorted([ep('Special 3', 3), ep('Special 1', 1), ep('Special 2', 2)], key=upnext.sortKey)
        self.assertEqual(['Special 1', 'Special 2', 'Special 3'], [e['title'] for e in order])

    def test_next_episode(self):
        episodes = [ep('S1 E1'), ep('S1 E2'), ep('S2 E1')]
        self.assertEqual('S1 E2', upnext.nextEpisode(episodes[0], episodes)['title'])
        self.assertEqual('S2 E1', upnext.nextEpisode(episodes[1], episodes)['title'])  # the next season
        self.assertIsNone(upnext.nextEpisode(episodes[2], episodes))  # the last one

    def test_a_gap_is_skipped(self):
        episodes = [ep('S1 E1'), ep('S1 E3')]
        self.assertEqual('S1 E3', upnext.nextEpisode(episodes[0], episodes)['title'])

    def test_season_and_episode(self):
        self.assertEqual((2, 10), upnext.seasonAndEpisode(ep('S2 E10 - x')))
        self.assertEqual((2, 10), upnext.seasonAndEpisode(ep('s2e10 - x')))
        self.assertEqual((1, 24), upnext.seasonAndEpisode(ep('Ep 24th Oct 2026 - Episode 1', 24)))


class DataTest(unittest.TestCase):

    def setUp(self):
        self.ud = userdata.UserData(os.path.join(tempfile.mkdtemp(), 'userdata.db'))
        for model in (db.showDB, db.episodeDB):
            model._userdata = self.ud
            model.drop()
        db.showDB.set([dict(show(1), name='A Show', fanart='fan', image='poster', banner='banner', logo='logo')])
        db.episodeDB.set([
            ep('S1 E1 - First', 1, id='e1', parentid='s1', show='A Show', image='t1', duration=1500, description='plot 1'),
            ep('S1 E2 - Second', 2, id='e2', parentid='s1', show='A Show', image='t2', duration=1600),
            ep('S2 E1 - Third', 1, id='e3', parentid='s1', show='A Show', image='t3'),
            ep('Another', 1, id='x1', parentid='s2', show='Other'),
            ep('Movie', 1, id='m1', parentid='m1', ltype='movie'),
        ])
        self.ud.setStats(userdata.EPISODE, 'e1', views=2)

    def build(self, episodeId):
        return upnext.buildData(db.episodeDB, db.showDB, episodeId, 'plugin.video.tfctv')

    def test_data_of_an_episode(self):
        data = self.build('e1')
        current, following = data['current_episode'], data['next_episode']
        self.assertEqual(('e1', 's1', 'A Show', '1', '1', 2, 1500), (current['episodeid'], current['tvshowid'], current['showtitle'], current['season'],
                                                                     current['episode'], current['playcount'], current['runtime']))
        self.assertEqual(('e2', 's1', 'S1 E2 - Second', '1', '2', 't2'), (following['episodeid'], following['tvshowid'], following['title'], following['season'],
                                                                           following['episode'], following['art']['thumb']))
        self.assertEqual(('fan', 'poster', 'banner', 'logo'), tuple(current['art'][k] for k in ('tvshow.fanart', 'tvshow.poster', 'tvshow.landscape', 'tvshow.clearlogo')))
        self.assertEqual('plot 1', current['plot'])
        for episodeInfo in (current, following):
            self.assertEqual({'episodeid', 'tvshowid', 'title', 'art', 'season', 'episode', 'showtitle', 'plot', 'playcount', 'rating', 'firstaired', 'runtime'}, set(episodeInfo))

    def test_play_url_plays_the_next_episode(self):
        url = self.build('e1')['play_url']
        self.assertTrue(url.startswith('plugin://plugin.video.tfctv/?url=e2&mode=4&'), url)
        self.assertIn('title=S1+E2+-+Second', url)
        self.assertIn('thumbnail=t2', url)
        self.assertIn('ltype=show', url)

    def test_the_next_season(self):
        self.assertEqual('e3', self.build('e2')['next_episode']['episodeid'])

    def test_nothing_to_offer(self):
        self.assertIsNone(self.build('e3'))  # the last episode
        self.assertIsNone(self.build('x1'))  # the only episode of its show
        self.assertIsNone(self.build('m1'))  # a movie
        self.assertIsNone(self.build('unknown'))

    def test_the_request_up_next_receives(self):
        request = json.loads(upnext.request({'play_url': 'plugin://x', 'n': 'é'}, 'plugin.video.tfctv'))
        self.assertEqual('JSONRPC.NotifyAll', request['method'])
        self.assertEqual(('plugin.video.tfctv.SIGNAL', 'upnext_data'), (request['params']['sender'], request['params']['message']))
        self.assertEqual({'play_url': 'plugin://x', 'n': 'é'}, json.loads(base64.b64decode(request['params']['data'][0]).decode('utf-8')))


if __name__ == '__main__':
    unittest.main()
