# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik

    Plugin router: maps the `mode` of a plugin URL to what handles it.
'''

from urllib.parse import parse_qsl, unquote_plus
from resources import config
from resources.lib.libraries import control
from resources.lib.libraries import tools


class Request(object):
    """The parameters of a plugin URL (sys.argv[2])"""

    def __init__(self, query):
        self.params = dict(parse_qsl(query.replace('?', '')))
        p = self.params
        self.action = p.get('action')
        self.mode = int(p.get('mode')) if p.get('mode') else None
        self.page = int(p.get('page')) if p.get('page') else 1
        self.category = p.get('category')
        self.name = p.get('name')
        self.title = p.get('title')
        self.year = p.get('year')
        self.show = p.get('show')
        self.episode = p.get('episode')
        self.url = p.get('url')
        self.image = p.get('image')
        self.caller = p.get('caller', 'addon')
        self.thumbnail = unquote_plus(p.get('thumbnail', ''))

    def get(self, key, default=None):
        return self.params.get(key, default)


# The modules are imported when a mode needs them: loading all of them for every plugin call is slow.

def navigator():
    from resources.lib.indexers import navigator
    return navigator.navigator()


def tfctv():
    from resources.lib.sources import tfctv
    return tfctv


# mode -> function(request). Modes that are not in the table do nothing.
ROUTES = {
    # navigation
    config.SUBCATEGORYSHOWS: lambda r: navigator().showSubCategoryShows(r.url),
    config.SHOWEPISODES: lambda r: navigator().showEpisodes(r.url, r.get('season', '1'), r.page),
    config.CHOOSEBANDWIDTH: lambda r: navigator().chooseBandwidth(r.url, r.title, r.get('ltype', r.show), r.thumbnail),
    config.CATEGORIES: lambda r: navigator().showCategories(),
    config.COLLECTIONCONTENT: lambda r: navigator().showCollectionContent(r.url),
    config.SEASONS: lambda r: navigator().showSeasons(r.url),
    config.SECTIONCONTENT: lambda r: navigator().showWebsiteSectionContent(r.url, r.page),
    config.MYACCOUNT: lambda r: navigator().showMyAccount(),
    config.MYINFO: lambda r: navigator().showMyInfo(),
    config.MYSUBSCRIPTIONS: lambda r: navigator().showMySubscription(),
    config.MYTRANSACTIONS: lambda r: navigator().showMyTransactions(),
    config.MYDEVICES: lambda r: navigator().showMyDevices(),
    config.INFODEVICE: lambda r: navigator().showMyDeviceInfo(r.get('deviceId')),
    config.MYLIST: lambda r: navigator().showMyList(),
    config.MYLISTSHOWLASTEPISODES: lambda r: navigator().showMyListShowLastEpisodes(),
    config.LISTCATEGORY: lambda r: navigator().showMyListCategory(r.url),
    config.EXPORTEDSHOWS: lambda r: navigator().showExportedShows(),
    config.SEARCHMENU: lambda r: navigator().showSearchMenu(r.get('category', False)),
    config.EXECUTESEARCH: lambda r: navigator().executeSearch(r.get('category', False), r.get('type', False)),
    config.TOOLS: lambda r: navigator().showTools(),
    # actions
    config.CHECKFORUPDATES: lambda r: tfctv().checkCatalogUpdates(),
    config.PLAY: lambda r: tfctv().playEpisode(r.url, r.title, r.get('ltype', r.show), r.thumbnail, r.get('bandwidth', False)),
    config.PLAYDISABLED: lambda r: control.showMessage(control.lang(37032), control.lang(30002)),
    config.LOGOUT: lambda r: tfctv().logout(quiet=False),
    config.ADDTOLIST: lambda r: tfctv().addToMyList(r.url, r.name, r.get('ltype'), r.get('type')),
    config.REMOVEFROMLIST: lambda r: tfctv().removeFromMyList(r.url, r.name, r.get('ltype'), r.get('type')),
    config.ADDTOLIBRARY: lambda r: tfctv().addToLibrary(r.url, r.name, r.get('parentid', -1), r.get('year', '')),
    config.REMOVEFROMLIBRARY: lambda r: navigator().removeShowFromLibrary(r.url, r.name),
    config.CHECKLIBRARYUPDATES: lambda r: tfctv().checkLibraryUpdates(r.caller != 'addon') if tools.isDBInstalled() else None,
    config.CLEANCOOKIES: lambda r: tfctv().cleanCookies(),
    # login and setup
    config.ENTERCREDENTIALS: lambda r: navigator().enterCredentials(),
    config.LOGINWITHTFC: lambda r: navigator().loginWithTFC(),
    config.LOGINWITHFB: lambda r: navigator().loginWithFB(),
    config.PERSONALIZESETTINGS: lambda r: navigator().personalizeSettings(),
    config.OPTIMIZELIBRARY: lambda r: navigator().optimizeLibrary(),
    config.ENDSETUP: lambda r: navigator().endSetup(),
    config.FIRSTINSTALL: lambda r: navigator().firstInstall(),
    # catalog and databases
    config.RELOADCATALOG: lambda r: tfctv().reloadCatalogCache(),
    config.RESETCATALOG: lambda r: tfctv().resetCatalogCache(),
    config.CATCHUPCATALOG: lambda r: tfctv().catchUpCatalog(),
    config.IMPORTSHOWDB: lambda r: tools.importShowDB(),
    config.IMPORTEPISODEDB: lambda r: tools.importEpisodeDB(),
    config.IMPORTALLDB: lambda r: tools.importDBFiles(),
}


def route(request):
    """Run what handles the mode of the request (the root menu when there is no mode)"""
    if request.mode is None:
        return navigator().root()
    handler = ROUTES.get(request.mode)
    if handler is not None:
        return handler(request)
