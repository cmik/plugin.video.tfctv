# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

from urllib.parse import parse_qsl,unquote_plus
import sys,time
from resources import config
from resources.lib.libraries import control
from resources.lib.libraries import tools

# Debug 
logger = control.logger 
if control.setting('debug') == 'true':
    logger.enable(True)
    try:
        exec('newLevel = logger.LOG%s' %(control.setting('debugLevel')))
        logger.setLevel(newLevel)
    except:
        pass

exec_start=time.time()
    
logger.logInfo(sys.argv[2])

params = dict(parse_qsl(sys.argv[2].replace('?','')))

action = params.get('action')

mode = int(params.get('mode')) if params.get('mode') else None

page = int(params.get('page')) if params.get('page') else 1

category = params.get('category')

name = params.get('name')

title = params.get('title')

year = params.get('year')

show = params.get('show')

episode = params.get('episode')

url = params.get('url')

image = params.get('image')

caller = params.get('caller', 'addon')

thumbnail = unquote_plus(params.get('thumbnail', ''))


# if caller == 'addon' and control.setting('addonNewInstall') == 'true' and control.setting('lastVersion') != control.addonInfo('version'):
if caller == 'addon' and control.setting('lastVersion') != control.addonInfo('version'):
    from resources import upgrade
    logger.logInfo(control.lang(37023))
    control.showMessage(control.lang(37023) % control.addonInfo('version'), control.lang(30002))
    upgrade.upgradeDB()
    upgrade.upgradeSettings()
    control.setSetting('lastVersion', control.addonInfo('version'))

if mode == None:
    from resources.lib.indexers import navigator
    navigator.navigator().root()
elif mode == config.CHECKFORUPDATES:
    from resources.lib.sources import tfctv
    tfctv.checkCatalogUpdates()
elif mode == config.SUBCATEGORYSHOWS:
    from resources.lib.indexers import navigator
    navigator.navigator().showSubCategoryShows(url)
elif mode == config.SHOWEPISODES:
    from resources.lib.indexers import navigator
    navigator.navigator().showEpisodes(url, page)
elif mode == config.CHOOSEBANDWIDTH:
    from resources.lib.indexers import navigator
    navigator.navigator().chooseBandwidth(url, title, params.get('ltype', show), thumbnail)
elif mode == config.PLAY:
    from resources.lib.sources import tfctv
    tfctv.playEpisode(url, title, params.get('ltype', show), thumbnail, params.get('bandwidth', False))
elif mode == config.CATEGORIES:
    from resources.lib.indexers import navigator
    navigator.navigator().showCategories()
elif mode == config.SECTIONCONTENT:
    from resources.lib.indexers import navigator
    navigator.navigator().showWebsiteSectionContent(url, page)
elif mode == config.MYACCOUNT:
    from resources.lib.indexers import navigator
    navigator.navigator().showMyAccount()
elif mode == config.MYINFO:
    from resources.lib.indexers import navigator
    navigator.navigator().showMyInfo()
elif mode == config.MYSUBSCRIPTIONS:
    from resources.lib.indexers import navigator
    navigator.navigator().showMySubscription()
elif mode == config.MYTRANSACTIONS:
    from resources.lib.indexers import navigator
    navigator.navigator().showMyTransactions()
elif mode == config.MYDEVICES:
    from resources.lib.indexers import navigator
    navigator.navigator().showMyDevices()
elif mode == config.INFODEVICE:
    from resources.lib.indexers import navigator
    navigator.navigator().showMyDeviceInfo(params.get('deviceId'))
elif mode == config.LOGOUT:
    from resources.lib.sources import tfctv
    tfctv.logout(quiet=False)
elif mode == config.MYLIST:
    from resources.lib.indexers import navigator
    navigator.navigator().showMyList()
elif mode == config.MYLISTSHOWLASTEPISODES:
    from resources.lib.indexers import navigator
    navigator.navigator().showMyListShowLastEpisodes()
elif mode == config.LISTCATEGORY:
    from resources.lib.indexers import navigator
    navigator.navigator().showMyListCategory(url)
elif mode == config.EXPORTEDSHOWS:
    from resources.lib.indexers import navigator
    navigator.navigator().showExportedShows()
elif mode == config.ADDTOLIST:
    from resources.lib.sources import tfctv
    tfctv.addToMyList(url, name, params.get('ltype'), params.get('type'))
elif mode == config.REMOVEFROMLIST:
    from resources.lib.sources import tfctv
    tfctv.removeFromMyList(url, name, params.get('ltype'), params.get('type'))
elif mode == config.ADDTOLIBRARY:
    from resources.lib.sources import tfctv
    tfctv.addToLibrary(url, name, params.get('parentid', -1), params.get('year', ''))
elif mode == config.REMOVEFROMLIBRARY:
    from resources.lib.indexers import navigator
    navigator.navigator().removeShowFromLibrary(url, name)
elif mode == config.SEARCHMENU:
    from resources.lib.indexers import navigator
    navigator.navigator().showSearchMenu(params.get('category', False))
elif mode == config.EXECUTESEARCH:
    from resources.lib.indexers import navigator
    navigator.navigator().executeSearch(params.get('category', False), params.get('type', False))
elif mode == config.ENTERCREDENTIALS:
    from resources.lib.indexers import navigator
    navigator.navigator().enterCredentials()
elif mode == config.LOGINWITHTFC:
    from resources.lib.indexers import navigator
    navigator.navigator().loginWithTFC()
elif mode == config.LOGINWITHFB:
    from resources.lib.indexers import navigator
    navigator.navigator().loginWithFB()
elif mode == config.PERSONALIZESETTINGS:
    from resources.lib.indexers import navigator
    navigator.navigator().personalizeSettings()
elif mode == config.OPTIMIZELIBRARY:
    from resources.lib.indexers import navigator
    navigator.navigator().optimizeLibrary()
elif mode == config.ENDSETUP:
    from resources.lib.indexers import navigator
    navigator.navigator().endSetup()
elif mode == config.TOOLS:
    from resources.lib.indexers import navigator
    navigator.navigator().showTools()
elif mode == config.RELOADCATALOG:
    from resources.lib.sources import tfctv
    tfctv.reloadCatalogCache()
elif mode == config.RESETCATALOG:
    from resources.lib.sources import tfctv
    tfctv.resetCatalogCache()
elif mode == config.CHECKLIBRARYUPDATES and tools.isDBInstalled() == True:
    from resources.lib.sources import tfctv
    tfctv.checkLibraryUpdates(True if caller!='addon' else False)
elif mode == config.CLEANCOOKIES:
    from resources.lib.sources import tfctv
    tfctv.cleanCookies()
elif mode == config.IMPORTSHOWDB:
    tools.importShowDB()
elif mode == config.IMPORTEPISODEDB:
    tools.importEpisodeDB()
elif mode == config.IMPORTALLDB:
    tools.importDBFiles()
elif mode == config.FIRSTINSTALL:
    from resources.lib.indexers import navigator
    navigator.navigator().firstInstall()
# elif mode == 99:
    # cookieJar.clear()

logger.logNotice('Finished in %s' % str(time.time()-exec_start))