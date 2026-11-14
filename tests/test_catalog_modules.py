# -*- coding: utf-8 -*-
"""Tests of the catalog modules (db, formatters, graphql, rails, catalog) with the Kodi side faked"""

import importlib
import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402  (fakes the Kodi control module)

ROOT = test_userdata.ROOT
PACKAGE = 'resources.lib.sources.tfctv'


def load():
    """Import the catalog modules without the rest of the tfctv package (it needs Kodi)"""
    directory = tempfile.mkdtemp()
    control = test_userdata.control
    for name in ('episodesFile', 'showsFile', 'celebritiesFile', 'userDataFile'):
        setattr(control, name, os.path.join(directory, name + '.db'))
    control.setting = lambda key: ''
    control.lang = lambda number: ''
    cache = types.ModuleType('resources.lib.libraries.cache')
    package = types.ModuleType(PACKAGE)
    package.__path__ = [os.path.join(ROOT, 'resources', 'lib', 'sources', 'tfctv')]
    api = types.ModuleType(PACKAGE + '.api')
    api.callJsonApi = api.callGraphQLApi = lambda *a, **k: {}
    utils = types.ModuleType(PACKAGE + '.utils')
    utils.unicodetoascii = lambda text: text
    utils.removeDuplicates = lambda items: items
    user = types.ModuleType(PACKAGE + '.user')
    user.getCountryCode = lambda: 'PH'
    user.getServiceIds = lambda: []
    fakes = {'resources.lib.libraries.cache': cache, PACKAGE: package, PACKAGE + '.api': api, PACKAGE + '.utils': utils, PACKAGE + '.user': user}
    saved = dict((k, sys.modules.get(k)) for k in fakes)
    sys.modules.update(fakes)
    try:
        return dict((name, importlib.import_module('%s.%s' % (PACKAGE, name))) for name in ('db', 'formatters', 'graphql', 'rails', 'catalog'))
    finally:
        for key, module in saved.items():
            if module is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = module


MODULES = load()
catalog = MODULES['catalog']

# what the rest of the add-on (playback, library, utils, tfctv/__init__) takes from the catalog module
PUBLIC = {
    'db': ['episodeDB', 'showDB', 'castDB'],
    'formatters': ['formatToShow', 'formatAssetToEpisode', 'formatAssetToShow', 'formatItemsToEpisodes', 'getSeasonFilters'],
    'graphql': ['getAppLaunchDetails', 'searchCatalog', 'getCollection', 'getTVShowEpisodes', 'getAsset'],
    'rails': ['getWebsiteCollections', 'getCachedCollection', 'getCollectionContent', 'getCollectionShowIds', 'getCatalogShowIds',
              'findCollectionRail', 'getWebsiteSectionContent', 'SHOW_ASSET_TYPES'],
    'catalog': ['getCategories', 'getShows', 'getMyList', 'getMyListShows', 'getMylistShowLastEpisodes', 'addToMyList', 'removeFromMyList',
                'getSettings', 'loadSettings', 'refreshCatalogShows', 'checkCatalogUpdates', 'getSeasons', 'getShowEpisodeItems', 'getShow',
                'getShowWithEpisodes', 'getEpisodesPerPage', 'getEpisode', 'enterSearch', 'storeEpisodes', 'repairShowCategories'],
}

ASSET = {
    'id': 'show-1', 'assetType': 'tvshow', 'title': 'A Show', 'shortDescription': 'About', 'releaseDate': '2020-05-01',
    'genres': ['Drama', 'Romance'], 'cast': ['Coco Martin', 'Vice Ganda'],
    'images': {'portrait': 'p', 'landscape': 'l', 'landscapeHero': 'h', 'title': 't'},
    'slugUrl': 'a-show', 'durationInSeconds': 60, 'rating': 'G',
}


class CatalogModulesTest(unittest.TestCase):

    def test_public_names_stay_importable_from_catalog(self):
        for module, names in PUBLIC.items():
            for name in names:
                self.assertTrue(hasattr(catalog, name), '%s (from %s) is missing from catalog' % (name, module))
                self.assertIs(getattr(catalog, name), getattr(MODULES[module], name), name)

    def test_each_function_is_defined_in_one_module_only(self):
        seen = {}
        for module in ('db', 'formatters', 'graphql', 'rails', 'catalog'):
            for name, value in vars(MODULES[module]).items():
                if isinstance(value, types.FunctionType) and value.__module__ == MODULES[module].__name__:
                    self.assertNotIn(name, seen, '%s is defined in %s and %s' % (name, seen.get(name), module))
                    seen[name] = module

    def test_show_categories_are_the_genres(self):
        show = MODULES['formatters'].formatAssetToShow(ASSET)
        self.assertEqual('Drama|Romance', show['parentname'])
        self.assertEqual('tvshow', show['parentid'])
        self.assertEqual(['Coco Martin', 'Vice Ganda'], [c['name'] for c in show['casts']])
        self.assertEqual(['coco-martin', 'vice-ganda'], [c['actorid'] for c in show['casts']])

    def test_show_without_genres(self):
        self.assertEqual('', MODULES['formatters'].formatAssetToShow(dict(ASSET, genres=None))['parentname'])

    def test_not_an_asset(self):
        self.assertEqual({}, MODULES['formatters'].formatAssetToShow(None))
        self.assertEqual({}, MODULES['formatters'].formatToShow({'title': 'no id'}))

    def test_graphql_functions_survive_an_empty_answer(self):
        self.assertEqual({}, MODULES['graphql'].getAsset('x'))
        self.assertEqual({}, MODULES['graphql'].getCollection('x'))


if __name__ == '__main__':
    unittest.main()
