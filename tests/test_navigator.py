# -*- coding: utf-8 -*-
"""Tests of the navigator (the directory listings): the real module runs against a fake Kodi (`control`, `xbmc`) and
a fake `tfctv` that answers what each test needs; what it adds to the listing is read back from the fake Kodi."""

import importlib.util
import os
import sys
import types
import unittest
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_userdata  # noqa: E402  (fakes the Kodi control module for the models)

from resources import config  # noqa: E402

ROOT = test_userdata.ROOT


class Str(str):
    """A localized string: it ignores the values it is formatted with (`lang(37062) % name`)"""

    def __mod__(self, other):
        return str(self)


class Tag(object):
    def __init__(self):
        self.values = {}

    def __getattr__(self, name):
        if not name.startswith('set'):
            raise AttributeError(name)
        return lambda *a: self.values.__setitem__(name[3:], a[0] if len(a) == 1 else a)


class Item(object):
    def __init__(self, label=None, path=None):
        self.label, self.props, self.art, self.tag, self.menu, self.info = label, {}, {}, Tag(), [], {}

    def getVideoInfoTag(self):
        return self.tag

    def setProperty(self, key, value):
        self.props[key] = value

    def setArt(self, art):
        self.art.update(art)

    def setInfo(self, kind, values):
        self.info[kind] = values

    def addContextMenuItems(self, items):
        self.menu = list(items)


class Control(object):
    """The part of resources.lib.libraries.control the navigator uses, recording what it is asked"""

    def __init__(self):
        self.logger = test_userdata._Logger()
        self.sysaddon = 'plugin://plugin.video.tfctv/'
        self.thisPlugin = 1
        self.settings, self.listing, self.calls, self.answer = {}, [], [], True

    def artPath(self):
        return 'art'

    def addonFanart(self):
        return 'fanart'

    def setting(self, key):
        return self.settings.get(key, '')

    def lang(self, i):
        return Str('L%d' % i)

    def item(self, label=None, path=None):
        return Item(label, path)

    def addItem(self, handle, url, listitem, isFolder):
        self.listing.append({'url': url, 'item': listitem, 'folder': isFolder})
        return True

    def addonFolderIcon(self, name):
        return 'icon:%s' % name

    def setListing(self, handle, content, sortMethods):
        self.calls.append(('listing', content, tuple(sortMethods)))

    def directory(self, handle, cacheToDisc=True):
        self.calls.append(('end',))

    def confirm(self, *args):
        self.calls.append(('confirm',) + args)
        return self.answer

    def infoDialog(self, *args, **kwargs):
        self.calls.append(('infoDialog', args[0]))

    def showNotification(self, *args):
        self.calls.append(('notification', args[0]))

    def refresh(self):
        self.calls.append(('refresh',))

    def setSetting(self, key, value):
        self.settings[key] = value

    def showMessage(self, message, title=None):
        self.calls.append(('message', message, title))

    def addonIcon(self):
        return 'icon'

    def facebookIcon(self):
        return 'fb'

    def openSettings(self):
        self.calls.append(('settings',))


class Tfctv(object):
    """The tfctv package: what a test sets is answered, the rest is an empty answer"""

    def __init__(self):
        self.calls = []
        self.loggedIn = True

    def isLoggedIn(self):
        return self.loggedIn

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return lambda *a, **k: self.calls.append((name, a)) or []


def loadNavigator(control, tfctv):
    """The real navigator module, bound to the fakes (the modules it imports are put back afterwards)"""
    xbmc = types.ModuleType('xbmc')
    xbmc.Actor = lambda name, order=0: (name, order)
    libraries = types.ModuleType('resources.lib.libraries')
    libraries.control = control
    libraries.__path__ = []
    sources = types.ModuleType('resources.lib.sources')
    sources.tfctv = tfctv
    sources.__path__ = []
    fakes = {'xbmc': xbmc, 'resources.lib.libraries': libraries, 'resources.lib.libraries.control': control,
             'resources.lib.sources': sources, 'resources.lib.sources.tfctv': tfctv}
    saved = dict((k, sys.modules.get(k)) for k in fakes)
    sys.modules.update(fakes)
    try:
        spec = importlib.util.spec_from_file_location('navigator_under_test', os.path.join(ROOT, 'resources', 'lib', 'indexers', 'navigator.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


control, tfctv = Control(), Tfctv()
navigatorModule = loadNavigator(control, tfctv)


def modeOf(url):
    return int(parse_qs(urlparse(url).query).get('mode', ['-1'])[0])


def query(url):
    return dict((k, v[0]) for k, v in parse_qs(urlparse(url).query).items())


class NavigatorTest(unittest.TestCase):

    def setUp(self):
        self.argv = sys.argv
        sys.argv = ['plugin://plugin.video.tfctv/', '1', '']
        del control.listing[:]
        del control.calls[:]
        control.settings.clear()
        control.settings.update({'itemsPerPage': '3', 'displayMyList': 'true', 'displayTools': 'false', 'displayWebsiteSections': 'false',
                                 'displayMyAccountMenu': 'false', 'loginType': 'TFC.tv', 'emailAddress': 'me@example.com'})
        control.answer = True
        tfctv.__dict__.clear()
        tfctv.calls = []
        tfctv.loggedIn = True
        self.nav = navigatorModule.navigator()

    def tearDown(self):
        sys.argv = self.argv

    def entries(self):
        return [{'label': e['item'].label, 'mode': modeOf(e['url']), 'folder': e['folder'], 'props': e['item'].props,
                 'menu': dict(e['item'].menu), 'url': e['url'], 'item': e['item']} for e in control.listing]

    def labels(self):
        return [e['label'] for e in self.entries()]

    def modes(self):
        return [e['mode'] for e in self.entries()]

    # ---- the main menu

    def test_main_menu_of_a_signed_in_user(self):
        tfctv.getCategories = lambda: [{'id': 'c1', 'name': 'Drama'}]
        self.nav.showMainMenu()
        self.assertEqual([config.SEARCHMENU, config.MYLIST, config.CONTINUEWATCHING, config.VIEWHISTORY, config.LIVETV, config.TOPPICKS,
                          config.SUBCATEGORYSHOWS], self.modes())
        self.assertEqual(('end',), control.calls[-1])

    def test_each_entry_can_be_turned_off(self):
        control.settings.update({'displayMyList': 'false', 'displayContinueWatching': 'false', 'displayViewHistory': 'false', 'displayLiveTV': 'false'})
        self.nav.showMainMenu()
        self.assertEqual([config.SEARCHMENU, config.TOPPICKS], self.modes())

    def test_the_history_moves_under_my_account(self):
        control.settings['displayMyAccountMenu'] = 'true'
        self.nav.showMainMenu()
        self.assertNotIn(config.VIEWHISTORY, self.modes())
        self.assertIn(config.MYACCOUNT, self.modes())

    def test_my_account_needs_an_email_address(self):
        control.settings.update({'displayMyAccountMenu': 'true', 'emailAddress': ''})
        self.nav.showMainMenu()
        self.assertNotIn(config.MYACCOUNT, self.modes())
        self.assertIn(config.VIEWHISTORY, self.modes())

    def test_website_sections_and_the_other_entries(self):
        control.settings.update({'displayWebsiteSections': 'true', 'displayTools': 'true', 'exportToLibrary': 'true'})
        tfctv.getWebsiteCollections = lambda: [{'title': 'home', 'collectionId': 7}]
        self.nav.showMainMenu()
        modes = self.modes()
        self.assertEqual([config.CATEGORIES, config.COLLECTIONCONTENT], modes[modes.index(config.CATEGORIES):modes.index(config.CATEGORIES) + 2])
        self.assertEqual([config.EXPORTEDSHOWS, config.TOOLS], modes[-2:])
        self.assertIn('Home', self.labels())

    def test_a_visitor_has_no_my_list_and_is_told(self):
        tfctv.loggedIn = False
        control.answer = False
        self.nav.showMainMenu()
        self.assertNotIn(config.MYLIST, self.modes())
        self.assertIn(('infoDialog', 'L37017'), control.calls)
        self.assertTrue(any(c[0] == 'confirm' for c in control.calls))

    def test_root_is_the_first_install_or_the_menu(self):
        self.nav.showMainMenu = lambda: control.calls.append(('menu',))
        self.nav.firstInstall = lambda: control.calls.append(('first',))
        self.nav.root()
        control.settings['addonNewInstall'] = 'true'
        self.nav.root()
        self.assertEqual([('menu',), ('first',)], control.calls)

    # ---- entries that run an action

    def test_tools_are_actions_not_folders(self):
        self.nav.showTools()
        entries = self.entries()
        self.assertEqual({config.IMPORTALLDB, config.SYNCWATCHLIST, config.CHECKFORUPDATES, config.RELOADCATALOG, config.RESETCATALOG,
                          config.CHECKLIBRARYUPDATES, config.CLEANCOOKIES, config.FIRSTINSTALL}, set(e['mode'] for e in entries))
        for e in entries:  # a folder entry that runs an action logs "GetDirectory - Error getting plugin"
            self.assertFalse(e['folder'], e['label'])
            self.assertEqual('false', e['props'].get('IsPlayable'), e['label'])

    def test_the_synchronization_is_for_signed_in_users(self):
        tfctv.loggedIn = False
        self.nav.showTools()
        self.assertNotIn(config.SYNCWATCHLIST, self.modes())

    def test_the_history_page_offers_to_clear_it_once(self):
        episode = {'id': 'e1', 'title': 'S1E2 Pilot', 'show': 'Show', 'image': 'i', 'ltype': 'show', 'views': 1}
        tfctv.getViewHistory = lambda page, n: [episode]
        tfctv.hasNextViewHistoryPage = lambda page, n: page == 1
        self.nav.showViewHistory(1)
        entries = self.entries()
        self.assertEqual(['Show | Episode 2 | Pilot', 'L36008', 'L36026'], [e['label'] for e in entries])
        clear = entries[-1]
        self.assertEqual((config.CLEARHISTORY, False, 'false'), (clear['mode'], clear['folder'], clear['props']['IsPlayable']))
        self.assertEqual(('listing', 'episodes', ('unsorted', 'lastplayed')), control.calls[0])
        del control.listing[:]
        self.nav.showViewHistory(2)
        self.assertNotIn(config.CLEARHISTORY, self.modes())

    def test_clearing_the_history_asks_first(self):
        control.answer = False
        self.nav.clearViewHistory()
        self.assertNotIn(('refresh',), control.calls)
        self.assertFalse(any(c[0] == 'clearViewHistory' for c in tfctv.calls))
        control.answer = True
        self.nav.clearViewHistory()
        self.assertIn(('clearViewHistory', ()), tfctv.calls)
        self.assertEqual(('refresh',), control.calls[-1])

    def test_removing_an_entry_refreshes_the_list(self):
        self.nav.removeFromViewHistory('e1', 'Pilot')
        self.assertIn(('removeFromViewHistory', ('e1',)), tfctv.calls)
        self.assertEqual(('refresh',), control.calls[-1])

    # ---- the context menus

    def show(self, **kwargs):
        return dict({'id': 'sh1', 'name': 'Show', 'ltype': 'show', 'type': 'show', 'year': '2020'}, **kwargs)

    def test_a_show_can_be_added_to_my_list(self):
        menu = self.nav.formatShowInfo(self.show())['contextMenu']
        self.assertEqual(['L30300'], list(menu))
        self.assertTrue(menu['L30300'].startswith('RunPlugin('))  # RunPlugin: the entries are actions, not listings
        self.assertEqual(str(config.ADDTOLIST), query(menu['L30300'][len('RunPlugin('):-1])['mode'])

    def test_a_show_of_my_list_can_be_removed(self):
        menu = self.nav.formatShowInfo(self.show(), addToList=False)['contextMenu']
        self.assertEqual(['L30301'], list(menu))
        self.assertEqual(str(config.REMOVEFROMLIST), query(menu['L30301'][len('RunPlugin('):-1])['mode'])

    def test_a_channel_can_not_be_added_to_my_list(self):
        for kind in ('channel', 'livestream', 'unknown'):
            self.assertEqual({}, self.nav.formatShowInfo(self.show(ltype=kind))['contextMenu'], kind)
            self.assertEqual({}, self.nav.formatVideoInfo(self.show(ltype=kind, title='T'))['contextMenu'], kind)

    def test_export_to_the_library_entries(self):
        control.settings['exportToLibrary'] = 'true'
        self.assertEqual(['L30300', 'L30302'], list(self.nav.formatShowInfo(self.show())['contextMenu']))
        self.assertEqual(['L30300', 'L30304'], list(self.nav.formatShowInfo(self.show(inLibrary=True))['contextMenu']))

    def test_trakt_entry_only_for_the_shows_when_scrobbling(self):
        self.assertNotIn('L30248', self.nav.formatShowInfo(self.show())['contextMenu'])
        control.settings['traktScrobble'] = 'true'
        self.assertIn('L30248', self.nav.formatShowInfo(self.show())['contextMenu'])
        self.assertNotIn('L30248', self.nav.formatShowInfo(self.show(ltype='movie'))['contextMenu'])
        self.assertEqual(str(config.TRAKTLINK), query(self.nav.traktEntry('x', 'T', 2020)['L30248'][len('RunPlugin('):-1])['mode'])
        self.assertEqual({}, self.nav.traktEntry(None, 'T', 2020))

    def episode(self, **kwargs):
        return dict({'id': 'e1', 'title': 'S1E2 Pilot', 'show': 'Show', 'parentid': 'sh1', 'ltype': 'show', 'type': 'episode',
                     'views': 2, 'episodenumber': 2, 'image': 'i'}, **kwargs)

    def test_an_episode_is_playable_and_carries_what_was_viewed(self):
        data = self.nav.formatVideoInfo(self.episode(dateviewed='2026-11-01', resumeposition=95, totaltime=1500))
        self.assertEqual({'IsPlayable': 'true'}, data['listProperties'])
        video = data['listInfos']['video']
        self.assertEqual((2, '2026-11-01', 95, 1500), (video['playcount'], video['lastplayed'], video['resumetime'], video['totaltime']))

    def test_the_views_are_read_when_the_episode_does_not_carry_them(self):
        tfctv.getEpisodeViews = lambda episodeId: 5
        self.assertEqual(5, self.nav.formatVideoInfo(self.episode(views=None))['listInfos']['video']['playcount'])

    def test_history_entries_can_be_removed_and_lead_to_the_show(self):
        menu = self.nav.formatVideoInfo(self.episode(showObj={'id': 'sh1', 'nbSeasons': 1}), options={'history': True, 'goToShow': True})['contextMenu']
        self.assertEqual(['L30300', 'L30306', 'L30305'], list(menu))
        self.assertTrue(menu['L30306'].startswith('Container.Update('))  # the only entry that leaves the list
        self.assertTrue(menu['L30305'].startswith('RunPlugin('))

    def test_go_to_the_show(self):
        self.assertEqual(config.SHOWEPISODES, modeOf(self.nav.showTarget(self.episode())))
        self.assertEqual(config.SEASONS, modeOf(self.nav.showTarget(self.episode(showObj={'nbSeasons': 3}))))
        self.assertIsNone(self.nav.showTarget(self.episode(ltype='movie')))
        self.assertIsNone(self.nav.showTarget(self.episode(parentid=None)))
        self.assertIsNone(self.nav.showTarget(self.episode(parentid='e1')))  # a movie is its own parent

    def test_a_show_with_several_seasons_asks_the_season(self):
        self.assertEqual(config.SEASONS, self.nav.showMode({'nbSeasons': 2}))
        self.assertEqual(config.SHOWEPISODES, self.nav.showMode({'nbSeasons': 1}))
        self.assertEqual(config.SHOWEPISODES, self.nav.showMode({}))

    # ---- the lists

    def test_my_list(self):
        tfctv.getMyList = lambda: [self.show(id='a', parentid='p', logo='logo', image='img'), self.show(id='b', name='B', nbSeasons=2, image='img2')]
        self.nav.showMyListCategory('/')
        self.assertEqual([config.SHOWEPISODES, config.SEASONS], self.modes())
        self.assertEqual('img', self.entries()[0]['item'].art['thumb'])
        self.assertEqual(('listing', 'tvshows', ('unsorted', 'title', 'year')), control.calls[0])
        self.assertTrue(all(e['menu'].get('L30301') for e in self.entries()))  # removable from the list

    def test_my_list_shows_the_logo_when_asked(self):
        control.settings['useShowLogo'] = 'true'
        tfctv.getMyList = lambda: [self.show(logo='logo', image='img')]
        self.nav.showMyListCategory('/')
        self.assertEqual('logo', self.entries()[0]['item'].art['thumb'])

    def test_the_shows_are_sorted_by_title_and_the_picks_keep_the_website_order(self):
        shows = [self.show(id='1', name='Zeta', logo='l', image='i'), self.show(id='2', name='alpha', logo='l', image='i'),
                 {'id': '3', 'name': 'Mid', 'ltype': 'movie', 'logo': 'l', 'image': 'i'}]
        self.nav.displayShows(shows)
        self.assertEqual(['alpha', 'Mid', 'Zeta'], self.labels())
        del control.listing[:]
        self.nav.displayShows(shows, keepOrder=True)
        self.assertEqual(['Zeta', 'alpha', 'Mid'], self.labels())

    def test_movies_and_live_events_play_and_shows_open(self):
        shows = [self.show(id='1', name='A', logo='l', image='i'), {'id': '2', 'name': 'B', 'ltype': 'movie', 'logo': 'l', 'image': 'i'},
                 {'id': '3', 'name': 'C', 'ltype': 'livestream', 'logo': 'l', 'image': 'i'}, {'id': '4', 'name': 'D', 'ltype': 'channel', 'logo': 'l', 'image': 'i'}]
        self.nav.displayShows(shows)
        entries = self.entries()
        self.assertEqual([('A', config.SHOWEPISODES, True), ('B', config.PLAY, False), ('C', config.PLAY, False)], [(e['label'], e['mode'], e['folder']) for e in entries])
        self.assertEqual('livestream', query(entries[2]['url'])['ltype'])

    def test_top_picks_and_live_tv_keep_the_order(self):
        picks = [self.show(id='1', name='Zeta', logo='l', image='i'), self.show(id='2', name='Alpha', logo='l', image='i')]
        tfctv.getTopPicks = lambda: picks
        tfctv.getLiveTV = lambda: picks
        self.nav.showTopPicks()
        self.nav.showLiveTV()
        self.assertEqual(['Zeta', 'Alpha'] * 2, self.labels())

    def test_a_sub_category_without_shows_still_ends_the_directory(self):
        tfctv.getShows = lambda i: []
        self.nav.showSubCategoryShows('c1')
        self.assertEqual(('end',), control.calls[-1])
        self.assertEqual([], self.entries())

    def test_episodes_come_newest_first_with_the_page_after(self):
        eps = [self.episode(id='e%d' % n, title='S1E%d Name' % n, episodenumber=n) for n in (1, 3, 2)]
        tfctv.getEpisodesPerPage = lambda showId, season, page, n: (eps, False)
        self.nav.showEpisodes('sh1', '1', 1)
        entries = self.entries()
        self.assertEqual(['Show | Episode 3 | Name', 'Show | Episode 2 | Name', 'Show | Episode 1 | Name', 'L36008'], [e['label'] for e in entries])
        self.assertEqual([config.PLAY] * 3 + [config.SHOWEPISODES], [e['mode'] for e in entries])
        self.assertEqual(('2', '1'), (query(entries[-1]['url'])['page'], query(entries[-1]['url'])['season']))
        self.assertEqual(('listing', 'episodes', ('unsorted', 'episode', 'title', 'lastplayed')), control.calls[0])

    def test_a_title_without_season_and_episode_is_kept(self):
        tfctv.getEpisodesPerPage = lambda *a: ([self.episode(title='Ep 24th Oct 2026 - Episode 1')], False)
        self.nav.showEpisodes('sh1')
        self.assertEqual(['Ep 24th Oct 2026 - Episode 1'], self.labels())

    def test_the_last_page_has_no_next_entry(self):
        tfctv.getEpisodesPerPage = lambda *a: ([self.episode()], False)
        self.nav.showEpisodes('sh1')
        self.assertEqual(1, len(self.entries()))

    def test_a_section_lists_shows_and_playable_videos_only(self):
        content = [self.show(id='a', logo='l', image='i'),
                   {'id': 'b', 'name': 'S1E1 Film', 'show': 'F', 'ltype': 'movie', 'type': 'movie', 'image': 'i', 'views': 0},
                   {'id': 'c', 'name': 'Soon', 'ltype': 'movie', 'type': 'movie', 'isPlayable': False, 'image': 'i', 'views': 0},
                   {'id': 'd', 'name': 'Channel', 'ltype': 'channel', 'image': 'i'}]
        tfctv.getWebsiteSectionContent = lambda section, page, n: content
        self.nav.showWebsiteSectionContent('sec', 1)
        self.assertEqual([('Show', config.SHOWEPISODES), ('F | Episode 1 | Film', config.PLAY)], [(e['label'], e['mode']) for e in self.entries()])
        self.assertEqual(('listing', 'videos', ('unsorted', 'title', 'year')), control.calls[0])

    def test_a_full_page_of_a_section_has_a_next_page(self):
        control.settings['itemsPerPage'] = '1'
        tfctv.getWebsiteSectionContent = lambda section, page, n: [self.show(id='a', logo='l', image='i')]
        self.nav.showWebsiteSectionContent('sec', 2)
        entry = self.entries()[-1]
        self.assertEqual((config.SECTIONCONTENT, '3'), (entry['mode'], query(entry['url'])['page']))

    def test_continue_watching_pages(self):
        tfctv.getContinueWatching = lambda page, n: [self.episode()]
        tfctv.hasNextContinueWatchingPage = lambda page, n: True
        self.nav.showContinueWatching(1)
        self.assertEqual([config.PLAY, config.CONTINUEWATCHING], self.modes())
        self.assertEqual('2', query(self.entries()[-1]['url'])['page'])

    def test_collections_seasons_and_categories(self):
        tfctv.getCollectionContent = lambda url: [{'name': 'top shows', 'id': 5}]
        tfctv.getSeasons = lambda showId: [{'name': 'season 2', 'showId': 'sh1', 'id': 2}]
        self.nav.showCollectionContent('7')
        self.nav.showSeasons('sh1')
        self.assertEqual(['Top Shows', 'Season 2'], self.labels())
        self.assertEqual([config.SECTIONCONTENT, config.SHOWEPISODES], self.modes())
        self.assertEqual('2', query(self.entries()[1]['url'])['season'])

    def test_my_list_menu(self):
        self.nav.showMyList()
        self.assertEqual([config.MYLISTSHOWLASTEPISODES, config.LISTCATEGORY], self.modes())

    # ---- search

    def test_search_menus(self):
        self.nav.showSearchMenu(None)
        self.assertEqual([config.EXECUTESEARCH, config.SEARCHMENU, config.SEARCHMENU], self.modes())
        self.assertEqual('online', query(self.entries()[0]['url'])['type'])
        del control.listing[:]
        self.nav.showSearchMenu('movieshow')
        self.assertEqual(['title', 'category', 'cast', 'year'], [query(e['url'])['type'] for e in self.entries()])
        del control.listing[:]
        self.nav.showSearchMenu('episode')
        self.assertEqual(['title', 'date'], [query(e['url'])['type'] for e in self.entries()])

    def test_search_results(self):
        tfctv.enterSearch = lambda category, type: [self.show(id='1', name='B', logo='l', image='i'), self.show(id='2', name='A', logo='l', image='i')]
        self.assertTrue(self.nav.executeSearch('movieshow', 'title'))
        self.assertEqual(['A', 'B'], self.labels())
        del control.listing[:]
        tfctv.enterSearch = lambda category, type: [self.episode(id='x', show='Zed'), self.episode(id='y', show='Abe')]
        self.nav.executeSearch('episode', 'title')
        self.assertEqual(['Abe | Episode 2 | Pilot', 'Zed | Episode 2 | Pilot'], self.labels())

    def test_no_search_without_a_category_and_a_type(self):
        self.nav.executeSearch(False, False)
        self.assertFalse(any(c[0] == 'enterSearch' for c in tfctv.calls))
        self.assertEqual(('end',), control.calls[-1])

    # ---- account, library and set-up

    def test_my_account_has_the_history_and_the_logout_action(self):
        self.nav.showMyAccount()
        entries = self.entries()
        self.assertEqual([config.VIEWHISTORY, config.LOGOUT], [e['mode'] for e in entries])
        self.assertEqual((True, False, 'false'), (entries[0]['folder'], entries[1]['folder'], entries[1]['props']['IsPlayable']))
        self.assertIn(('checkAccountChange', (False,)), tfctv.calls)
        control.settings['displayViewHistory'] = 'false'
        del control.listing[:]
        self.nav.showMyAccount()
        self.assertEqual([config.LOGOUT], self.modes())

    def test_my_info(self):
        tfctv.getUserInfo = lambda: {'firstName': 'Ana', 'email': 'ana@example.com'}
        self.nav.showMyInfo()
        _, message, title = control.calls[-1]
        self.assertIn('First name: Ana', message)
        self.assertIn('Email: ana@example.com', message)
        self.assertEqual('L36001', title)

    def test_my_info_when_signed_out_or_when_the_website_fails(self):
        tfctv.loggedIn = False
        self.nav.showMyInfo()
        self.assertEqual(('message', 'L37002', 'L36001'), control.calls[-1])
        tfctv.loggedIn = True

        def fail():
            raise RuntimeError('down')
        tfctv.getUserInfo = fail
        self.nav.showMyInfo()
        self.assertEqual(('message', 'L37002', 'L36001'), control.calls[-1])

    def test_subscription_and_transactions(self):
        tfctv.getUserSubscription = lambda: {'details': 'Premium'}
        self.nav.showMySubscription()
        self.assertEqual(('message', 'Premium', 'L36002'), control.calls[-1])
        tfctv.getUserSubscription = lambda: None
        self.nav.showMySubscription()
        self.assertEqual(('message', 'L37002', 'L36002'), control.calls[-1])
        tfctv.getUserTransactions = lambda: ['one', 'two']
        self.nav.showMyTransactions()
        self.assertEqual(('message', 'one\ntwo\n', 'L36003'), control.calls[-1])
        tfctv.getUserTransactions = lambda: []
        self.nav.showMyTransactions()
        self.assertEqual(('message', 'L37002', 'L36003'), control.calls[-1])

    def test_exported_shows_and_removal_from_the_library(self):
        tfctv.showExportedShowsToLibrary = lambda: [self.show(id='1', name='A', logo='l', image='i')]
        self.nav.showExportedShows()
        self.assertEqual(['A'], self.labels())
        self.nav.removeShowFromLibrary('1', 'A')
        self.assertIn(('removeFromLibrary', ('1', 'A')), tfctv.calls)
        self.assertEqual(('refresh',), control.calls[-1])

    def test_first_install_offers_the_logins_as_actions(self):
        control.settings['showWelcomeMessage'] = 'true'
        self.nav.firstInstall()
        self.assertEqual('false', control.settings['showWelcomeMessage'])
        self.assertEqual([config.LOGINWITHTFC], self.modes())
        control.settings.update({'FBAppID': 'id', 'showWelcomeMessage': 'false'})
        del control.listing[:]
        self.nav.firstInstall()
        entries = self.entries()
        self.assertEqual([config.LOGINWITHTFC, config.LOGINWITHFB], [e['mode'] for e in entries])
        self.assertTrue(all(not e['folder'] and e['props']['IsPlayable'] == 'false' for e in entries))

    def test_logins_end_the_set_up(self):
        self.nav.loginWithFB()
        self.assertEqual(('Facebook', 'false'), (control.settings['loginType'], control.settings['addonNewInstall']))
        self.assertEqual(config.SEARCHMENU, self.modes()[0])  # the main menu follows
        control.settings.update({'emailAddress': '', 'showEnterCredentials': 'true', 'addonNewInstall': 'true'})
        tfctv.enterCredentials = lambda: True
        del control.listing[:]
        self.nav.loginWithTFC()
        self.assertEqual(('TFC.tv', 'false'), (control.settings['loginType'], control.settings['addonNewInstall']))
        self.assertEqual('false', control.settings['showEnterCredentials'])

    def test_the_catalog_is_loaded_again_by_the_set_up_and_the_settings_open(self):
        self.nav.optimizeLibrary()
        self.assertIn(('reloadCatalogCache', ()), tfctv.calls)
        self.assertEqual(('false', ('refresh',)), (control.settings['showUpdateCatalog'], control.calls[-1]))
        self.nav.personalizeSettings()
        self.assertIn(('settings',), control.calls)
        self.assertEqual('false', control.settings['showPersonalize'])

    # ---- the building blocks

    def test_action_urls(self):
        url = self.nav.generateActionUrl('a b', config.PLAY, 'Name é', 'http://x/y.jpg', 3, {'ltype': 'movie'})
        self.assertTrue(url.startswith('plugin://plugin.video.tfctv/?url=a+b&mode=%d' % config.PLAY))
        q = query(url)
        self.assertEqual(('a b', 'Name é', '3', 'http://x/y.jpg', 'movie'), (q['url'], q['name'], q['page'], q['thumbnail'], q['ltype']))
        q = query(self.nav.generateActionUrl('u', config.PLAY, None, '', -1, 'a=1&b=2'))
        self.assertEqual({'url': 'u', 'mode': str(config.PLAY), 'a': '1', 'b': '2'}, q)

    def test_a_directory_item(self):
        self.nav.addDirectoryItem('Name', 'u', config.PLAY, 'thumb', isFolder=False, **{
            'listProperties': {'IsPlayable': 'true'},
            'listInfos': {'video': {'plot': 'P', 'year': '2020', 'episode': 'x', 'genre': 'Drama', 'resumetime': 12, 'totaltime': 100}},
            'listArts': {'fanart': 'f'}, 'contextMenu': {'Label': 'RunPlugin(x)'}})
        entry = self.entries()[0]
        item = entry['item']
        self.assertFalse(entry['folder'])
        self.assertEqual('true', item.props['IsPlayable'])
        self.assertEqual([('Label', 'RunPlugin(x)')], item.menu)
        self.assertEqual({'icon': 'DefaultFolder.png', 'thumb': 'thumb', 'fanart': 'f'}, item.art)
        values = item.tag.values
        self.assertEqual(('Name', 'P', 2020, 0, ['Drama'], (12.0, 100.0)), (values['Title'], values['Plot'], values['Year'], values['Episode'], values['Genres'], values['ResumePoint']))

    def test_the_end_of_a_directory(self):
        self.nav.endDirectory(content='episodes', sortMethods=('unsorted', 'title'))
        self.assertEqual([('listing', 'episodes', ('unsorted', 'title')), ('end',)], control.calls)

    def test_the_menu_background(self):
        control.settings['defaultBG'] = 'bg.jpg'
        self.assertEqual({'listArts': {'fanart': 'bg.jpg', 'banner': 'bg.jpg'}}, self.nav.formatMenu())
        self.assertEqual({'listArts': {'fanart': 'x', 'banner': 'x'}}, self.nav.formatMenu('x'))


if __name__ == '__main__':
    unittest.main()
