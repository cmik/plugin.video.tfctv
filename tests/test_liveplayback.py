# -*- coding: utf-8 -*-
"""Tests of the playback request of the live channels"""

import os
import sys
import unittest
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402,F401  (fakes the Kodi control module)

from resources.lib.libraries import liveplayback  # noqa: E402

PATH = '/entitlement/playback/start/99ce7148'
BODY = {'platform': 'web', 'deviceId': 'D'}


class LivePlaybackTest(unittest.TestCase):

    def test_only_the_channels_are_live(self):
        self.assertTrue(liveplayback.isLive('livestream'))
        for ltype in ('show', 'movie', 'documentary', 'episode', None, ''):
            self.assertFalse(liveplayback.isLive(ltype))

    def test_an_episode_keeps_its_request(self):
        self.assertEqual(PATH, liveplayback.startPath(PATH, '99ce7148', 'show', 'FR'))
        self.assertEqual(BODY, liveplayback.withReferral(BODY, 'show'))

    def test_a_channel_sends_the_parameters_of_the_website(self):
        url = urlsplit(liveplayback.startPath(PATH, '99ce7148', 'livestream', 'FR'))
        self.assertEqual(PATH, url.path)
        self.assertEqual({'offline': ['false'], 'country': ['FR'], 'contentId': ['99ce7148'],
                          'platform': ['web'], 'subPlatform': ['firefox']}, parse_qs(url.query))
        # the order of the website
        self.assertEqual('offline=false&country=FR&contentId=99ce7148&platform=web&subPlatform=firefox', url.query)

    def test_country_of_the_user_and_default(self):
        self.assertIn('country=PH', liveplayback.startPath(PATH, 'x', 'livestream', 'PH'))
        self.assertIn('country=FR', liveplayback.startPath(PATH, 'x', 'livestream', ''))

    def test_a_channel_names_its_rail(self):
        body = liveplayback.withReferral(BODY, 'livestream')
        self.assertEqual('Live Channels', body['referralProperties']['railTitle'])
        self.assertEqual('Circle', body['referralProperties']['railType'])
        self.assertNotIn('referralProperties', BODY)  # the body given is not changed
        body['referralProperties']['railTitle'] = 'changed'
        self.assertEqual('Live Channels', liveplayback.LIVE_REFERRAL['railTitle'])


if __name__ == '__main__':
    unittest.main()
