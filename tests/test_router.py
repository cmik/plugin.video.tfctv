# -*- coding: utf-8 -*-
"""Tests of the plugin router: each mode calls what the former if/elif chain of default.py called"""

import json
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402  (fakes the Kodi control module)

CALLS = []


class Recorder(object):
    def __init__(self, prefix):
        self.prefix = prefix

    def __getattr__(self, name):
        def call(*args, **kwargs):
            CALLS.append([self.prefix + name, list(args), [list(i) for i in sorted(kwargs.items())]])
        return call


control = test_userdata.control
control.showMessage = lambda *a: CALLS.append(['control.showMessage', list(a), []])
control.lang = lambda i: 'lang%s' % i


class Tools(object):
    installed = True

    def isDBInstalled(self):
        return self.installed

    def __getattr__(self, name):
        return Recorder('tools.').__getattr__(name)


tools = Tools()
navigatorModule = types.ModuleType('resources.lib.indexers.navigator')
navigatorModule.navigator = lambda: Recorder('navigator.')
sourcesModule = types.ModuleType('resources.lib.sources.tfctv')
sourcesModule.__getattr__ = lambda name: Recorder('tfctv.').__getattr__(name)
sys.modules['resources.lib.libraries.tools'] = tools
test_userdata.libraries.tools = tools
sys.modules['resources.lib.indexers.navigator'] = navigatorModule
sys.modules['resources.lib.sources.tfctv'] = sourcesModule

from resources import config, router  # noqa: E402

QUERY = '?url=U&name=N&title=T&show=S&ltype=L&type=TY&thumbnail=th%2Fx&page=3&season=2&deviceId=D&category=C&bandwidth=B&parentid=P&year=Y'

# mode -> the calls it makes with QUERY
EXPECTED = {
    config.CHECKFORUPDATES: [["tfctv.checkCatalogUpdates", [], []]],
    config.SUBCATEGORYSHOWS: [["navigator.showSubCategoryShows", ["U"], []]],
    config.SHOWEPISODES: [["navigator.showEpisodes", ["U", "2", 3], []]],
    config.PLAY: [["tfctv.playEpisode", ["U", "T", "L", "th/x", "B"], []]],
    config.PLAYDISABLED: [["control.showMessage", ["lang37032", "lang30002"], []]],
    config.CHOOSEBANDWIDTH: [["navigator.chooseBandwidth", ["U", "T", "L", "th/x"], []]],
    config.CATEGORIES: [["navigator.showCategories", [], []]],
    config.SEASONS: [["navigator.showSeasons", ["U"], []]],
    config.COLLECTIONCONTENT: [["navigator.showCollectionContent", ["U"], []]],
    config.SECTIONCONTENT: [["navigator.showWebsiteSectionContent", ["U", 3], []]],
    config.MYACCOUNT: [["navigator.showMyAccount", [], []]],
    config.MYINFO: [["navigator.showMyInfo", [], []]],
    config.MYSUBSCRIPTIONS: [["navigator.showMySubscription", [], []]],
    config.MYTRANSACTIONS: [["navigator.showMyTransactions", [], []]],
    config.LOGOUT: [["tfctv.logout", [], [["quiet", False]]]],
    config.MYLISTSHOWLASTEPISODES: [["navigator.showMyListShowLastEpisodes", [], []]],
    config.MYLIST: [["navigator.showMyList", [], []]],
    config.LISTCATEGORY: [["navigator.showMyListCategory", ["U"], []]],
    config.ADDTOLIST: [["tfctv.addToMyList", ["U", "N", "L", "TY"], []]],
    config.REMOVEFROMLIST: [["tfctv.removeFromMyList", ["U", "N", "L", "TY"], []]],
    config.ADDTOLIBRARY: [["tfctv.addToLibrary", ["U", "N", "P", "Y"], []]],
    config.REMOVEFROMLIBRARY: [["navigator.removeShowFromLibrary", ["U", "N"], []]],
    config.CHECKLIBRARYUPDATES: [["tfctv.checkLibraryUpdates", [False], []]],
    config.EXPORTEDSHOWS: [["navigator.showExportedShows", [], []]],
    config.SEARCHMENU: [["navigator.showSearchMenu", ["C"], []]],
    config.EXECUTESEARCH: [["navigator.executeSearch", ["C", "TY"], []]],
    config.TOOLS: [["navigator.showTools", [], []]],
    config.RELOADCATALOG: [["tfctv.reloadCatalogCache", [], []]],
    config.CLEANCOOKIES: [["tfctv.cleanCookies", [], []]],
    config.OPENSETTINGS: [],
    config.ENTERCREDENTIALS: [["navigator.enterCredentials", [], []]],
    config.PERSONALIZESETTINGS: [["navigator.personalizeSettings", [], []]],
    config.OPTIMIZELIBRARY: [["navigator.optimizeLibrary", [], []]],
    config.RESETCATALOG: [["tfctv.resetCatalogCache", [], []]],
    config.IMPORTSHOWDB: [["tools.importShowDB", [], []]],
    config.IMPORTEPISODEDB: [["tools.importEpisodeDB", [], []]],
    config.IMPORTALLDB: [["tools.importDBFiles", [], []]],
    config.LOGINWITHTFC: [["navigator.loginWithTFC", [], []]],
    config.LOGINWITHFB: [["navigator.loginWithFB", [], []]],
    config.CATCHUPCATALOG: [["tfctv.catchUpCatalog", [], []]],
    config.FIRSTINSTALL: [["navigator.firstInstall", [], []]],
    config.ENDSETUP: [["navigator.endSetup", [], []]],
}


def run(query):
    del CALLS[:]
    router.route(router.Request(query))
    return json.loads(json.dumps(CALLS))


class RouterTest(unittest.TestCase):

    def setUp(self):
        tools.installed = True

    def test_every_mode(self):
        for mode, calls in EXPECTED.items():
            self.assertEqual(calls, run('%s&mode=%d' % (QUERY, mode)), 'mode %d' % mode)

    def test_every_mode_of_the_config_is_known(self):
        modes = set(v for k, v in vars(config).items() if k.isupper() and isinstance(v, int) and not isinstance(v, bool))
        self.assertEqual(modes, set(EXPECTED))  # a new mode must be added to the table and here

    def test_no_mode_is_the_root_menu(self):
        self.assertEqual([['navigator.root', [], []]], run(QUERY))

    def test_unknown_mode_does_nothing(self):
        self.assertEqual([], run(QUERY + '&mode=999'))

    def test_defaults(self):
        self.assertEqual([['navigator.showEpisodes', [None, '1', 1], []]], run('?mode=%d' % config.SHOWEPISODES))
        self.assertEqual([['navigator.chooseBandwidth', [None, None, 'SS', ''], []]], run('?mode=%d&show=SS' % config.CHOOSEBANDWIDTH))
        self.assertEqual([['navigator.executeSearch', [False, False], []]], run('?mode=%d' % config.EXECUTESEARCH))
        self.assertEqual([['tfctv.addToLibrary', [None, None, -1, ''], []]], run('?mode=%d' % config.ADDTOLIBRARY))

    def test_library_check(self):
        self.assertEqual([['tfctv.checkLibraryUpdates', [False], []]], run('?mode=%d' % config.CHECKLIBRARYUPDATES))
        self.assertEqual([['tfctv.checkLibraryUpdates', [True], []]], run('?mode=%d&caller=service' % config.CHECKLIBRARYUPDATES))
        tools.installed = False
        self.assertEqual([], run('?mode=%d' % config.CHECKLIBRARYUPDATES))


if __name__ == '__main__':
    unittest.main()
