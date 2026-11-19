# -*- coding: utf-8 -*-
"""Tests of the GraphQL queries of the website (queries.py) and of the calls that send them (graphql.py)"""

import importlib
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_catalog_modules  # noqa: E402  (loads the catalog modules with the Kodi side faked)

graphql = test_catalog_modules.MODULES['graphql']
queries = importlib.import_module(test_catalog_modules.PACKAGE + '.queries')

NAMES = ('SEARCH', 'WATCHLIST', 'APP_LAUNCH_DETAILS', 'COLLECTION', 'TV_SHOW_EPISODES', 'ASSET')


class QueriesTest(unittest.TestCase):

    def test_every_query_is_a_named_operation_with_balanced_braces(self):
        for name in NAMES:
            text = getattr(queries, name)
            self.assertTrue(re.match(r'\s*query \w+', text), name)
            for opening, closing in ('{}', '()', '[]'):
                self.assertEqual(text.count(opening), text.count(closing), '%s: %s%s' % (name, opening, closing))

    def test_the_queries_ask_what_the_formatters_read(self):
        for name in ('SEARCH', 'COLLECTION', 'ASSET', 'WATCHLIST'):
            text = getattr(queries, name)
            for field in ('assetType', 'isPlayable', 'images'):
                self.assertIn(field, text, '%s lacks %s' % (name, field))

    def test_nothing_else_than_queries_is_in_the_module(self):
        public = sorted(n for n in vars(queries) if n.isupper())
        self.assertEqual(sorted(NAMES), public)


class CallsTest(unittest.TestCase):

    def setUp(self):
        self.calls = []
        self.original = graphql.callGraphQLApi
        graphql.callGraphQLApi = lambda query, variables=None, *a, **k: self.calls.append((query, variables, a, k)) or {}

    def tearDown(self):
        graphql.callGraphQLApi = self.original

    def test_each_function_sends_its_query(self):
        graphql.searchCatalog('sigabo')
        graphql.getWatchlist([('Authorization', 'x')])
        graphql.getAppLaunchDetails()
        graphql.getCollection('c1')
        graphql.getTVShowEpisodes('s1')
        graphql.getAsset('a1')
        self.assertEqual([getattr(queries, n) for n in NAMES], [c[0] for c in self.calls])

    def test_the_search_sends_the_text_and_the_services(self):
        graphql.searchCatalog('sigabo')
        variables = self.calls[0][1]
        self.assertEqual(('sigabo', 'GSE'), (variables['query'], variables['apiCode']))
        self.assertIn('skus', variables)

    def test_the_watchlist_keeps_its_headers_and_is_not_cached(self):
        headers = [('Authorization', 'x')]
        graphql.getWatchlist(headers)
        query, variables, args, kwargs = self.calls[0]
        self.assertEqual(headers, args[0])
        self.assertFalse(kwargs.get('useCache', True))


if __name__ == '__main__':
    unittest.main()
