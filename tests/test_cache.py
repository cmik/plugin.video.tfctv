# -*- coding: utf-8 -*-
"""Tests of the cache: the time limit of what is kept (libraries/cache.py) and what the catalog keeps, and for how long"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_catalog_modules  # noqa: E402  (loads the catalog modules with the Kodi side faked)

from resources import config  # noqa: E402
from resources.lib.libraries import cache  # noqa: E402

rails = test_catalog_modules.MODULES['rails']
catalog = test_catalog_modules.MODULES['catalog']


class Clock(object):
    def __init__(self):
        self.now = 1000000.0

    def __call__(self):
        return self.now


class CacheTest(unittest.TestCase):

    def setUp(self):
        cache.execCache.clear()
        self.clock = Clock()
        self.realTime = cache.time.time
        cache.time.time = self.clock
        self.calls = []

    def tearDown(self):
        cache.time.time = self.realTime
        cache.execCache.clear()

    def make(self, value='v'):
        def func():
            self.calls.append(1)
            return value
        return func

    def test_a_value_is_kept_until_its_time_is_up(self):
        for _ in range(3):
            self.assertEqual('v', cache.getCached(cache.shortCache, 'k', self.make(), ttl=60))
        self.assertEqual(1, len(self.calls))
        self.clock.now += 59
        cache.getCached(cache.shortCache, 'k', self.make(), ttl=60)
        self.assertEqual(1, len(self.calls))
        self.clock.now += 2
        cache.getCached(cache.shortCache, 'k', self.make(), ttl=60)
        self.assertEqual(2, len(self.calls))

    def test_the_caller_chooses_how_long_it_accepts(self):
        cache.getCached(cache.shortCache, 'k', self.make(), ttl=3600)
        self.clock.now += 600
        cache.getCached(cache.shortCache, 'k', self.make(), ttl=3600)
        self.assertEqual(1, len(self.calls))
        cache.getCached(cache.shortCache, 'k', self.make(), ttl=300)  # 10 minutes old: too old for this one
        self.assertEqual(2, len(self.calls))

    def test_without_a_limit_it_is_kept(self):
        cache.getCached(cache.shortCache, 'k', self.make())
        self.clock.now += 10 ** 7
        cache.getCached(cache.shortCache, 'k', self.make())
        self.assertEqual(1, len(self.calls))

    def test_a_value_kept_without_a_date_is_made_again(self):
        cache.shortCache.set('k', 'old')
        self.assertEqual('v', cache.getCached(cache.shortCache, 'k', self.make(), ttl=60))

    def test_refresh_forgets(self):
        cache.getCached(cache.shortCache, 'k', self.make(), ttl=60)
        cache.getCached(cache.shortCache, 'k', self.make(), refresh=True, ttl=60)
        self.assertEqual(2, len(self.calls))

    def test_json_values_and_failed_answers(self):
        data = lambda: {'rails': [1, 2]}
        self.assertEqual({'rails': [1, 2]}, cache.getCachedJson(cache.shortCache, 'j', data, ttl=60))
        self.assertEqual({'rails': [1, 2]}, cache.getCachedJson(cache.shortCache, 'j', lambda: 1 / 0, ttl=60))  # kept: not called
        self.assertFalse(cache.getCachedJson(cache.shortCache, 'bad', lambda: {}, ttl=60))
        self.assertEqual({'x': 1}, cache.getCachedJson(cache.shortCache, 'bad', lambda: {'x': 1}, ttl=60))  # a failed call is not kept

    # ---- what the catalog keeps

    def test_the_ttls(self):
        ttls = config.cacheTTLs
        self.assertLess(ttls['live'], ttls['rails'])
        self.assertLess(ttls['rails'], ttls['menu'])
        self.assertLess(ttls['live'], ttls['picks'])

    def stub(self, module, name, value):
        original = getattr(module, name)
        self.addCleanup(setattr, module, name, original)
        setattr(module, name, value)

    def test_the_collections_of_the_website_are_asked_once_for_hours(self):
        self.stub(rails, 'getAppLaunchDetails', lambda: self.calls.append(1) or {'menu': {'collections': [{'collectionId': 'home'}]}})
        for _ in range(3):
            self.assertEqual([{'collectionId': 'home'}], rails.getWebsiteCollections())
        self.assertEqual(1, len(self.calls))
        self.clock.now += config.cacheTTLs['menu'] + 1
        rails.getWebsiteCollections()
        self.assertEqual(2, len(self.calls))

    def test_no_collections_is_not_kept(self):
        self.stub(rails, 'getAppLaunchDetails', lambda: self.calls.append(1) or {})
        self.assertEqual([], rails.getWebsiteCollections())
        self.assertEqual([], rails.getWebsiteCollections())
        self.assertEqual(2, len(self.calls))

    def test_a_collection_is_kept_an_hour_and_live_tv_five_minutes(self):
        self.stub(rails, 'getCollection', lambda c: self.calls.append(c) or {'rails': [{'id': 'r'}]})
        rails.getCachedCollection('home')
        self.clock.now += 400  # more than the live limit, less than the hour
        rails.getCachedCollection('home')
        self.assertEqual(1, len(self.calls))
        rails.getCachedCollection('home', ttl=config.cacheTTLs['live'])
        self.assertEqual(2, len(self.calls))  # the live list wants it newer

    def test_a_failed_collection_is_not_kept(self):
        self.stub(rails, 'getCollection', lambda c: self.calls.append(c) or {})
        self.assertEqual({}, rails.getCachedCollection('home'))
        rails.getCachedCollection('home')
        self.assertEqual(2, len(self.calls))

    def test_the_rails_are_kept_by_country(self):
        self.stub(rails, 'getCollection', lambda c: self.calls.append(c) or {'rails': [{'id': 'r'}]})
        country = ['FR']
        self.stub(rails, 'getCountryCode', lambda: country[0])
        rails.getCachedCollection('home')
        country[0] = 'PH'  # a VPN: the website lists other channels
        rails.getCachedCollection('home')
        self.assertEqual(2, len(self.calls))
        country[0] = 'FR'
        rails.getCachedCollection('home')
        self.assertEqual(2, len(self.calls))

    def test_top_picks_are_kept_but_not_the_search(self):
        self.stub(catalog, 'searchCatalog', lambda query: self.calls.append(query) or {'search': {'rails': []}})
        self.stub(catalog, 'keepFound', lambda found: found)
        catalog.getTopPicks()
        catalog.getTopPicks()
        self.assertEqual([''], self.calls)
        self.clock.now += config.cacheTTLs['picks'] + 1
        catalog.getTopPicks()
        self.assertEqual(['', ''], self.calls)


if __name__ == '__main__':
    unittest.main()
