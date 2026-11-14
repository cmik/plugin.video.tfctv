# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

from resources import config
from resources.lib.libraries import control
from resources.lib.libraries import tools
from resources.lib.models import episodes
from resources.lib.models import shows
from resources.lib.models import library
from resources.lib.models import showcast

logger = control.logger

def upgradeDB():

    logger.logNotice('Updating from version %s to %s' % (control.setting('lastVersion'), control.addonInfo('version')))

    # My List and the counters must leave the catalog databases before anything replaces them
    tools.importUserData()

    # first installation or update from a version whose catalog can't be used anymore: install the catalog seed
    from resources.lib.libraries import seed
    if seed.seedReason(control.setting('lastVersion')):
        logger.logNotice('Installing the catalog')
        tools.checkInstallDB(True)
    elif control.setting('lastVersion') == '3.1.0':
        # 3.1.0 stored the shows without categories: load their details again in the background
        control.execute('RunPlugin(plugin://%s/?mode=%d&caller=upgrade)' % (control.addonInfo('id'), config.CATCHUPCATALOG))
    # keep the actors of the old catalog that can be attached to the shows of the current one
    from resources.lib.libraries import legacycast
    try:
        legacycast.importLegacyCast(showcast.ShowCast(control.celebritiesFile))
    except Exception as e:
        logger.logError('Can\'t import the legacy cast: %s' % str(e))
    if control.setting('lastVersion')[:1] in ('', '1', '2'):
        upgradeSettings()
        control.setSetting('lastVersion', control.addonInfo('version'))
    # episodeDB = episodes.Episode(control.episodesFile)
    # showDB = shows.Show(control.showsFile)
    # showViews = logger.logInfo(episodeDB.execute(['select showid, sum(views) from EPISODE where views > 0 group by showid']))
    # updateQueries = []
    # if (showViews and len(showViews) > 0):
    #     for data in showViews[0]:
    #         updateQueries.append('UPDATE SHOW SET VIEWS = %d WHERE ID = %d' % (int(data[1]), int(data[0])))
    #     showDB.executeUpdate(logger.logInfo(updateQueries))
        

def upgradeSettings():
    if control.addonInfo('version') == '3.0.0': 
        control.setSetting('proxyStreamingUrl', 'http://%s:%s/?url=%s%s')
        control.showMessage(control.lang(37047), control.lang(30002))