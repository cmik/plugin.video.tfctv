# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

import os
from resources import config
from resources.lib.libraries import control

logger = control.logger

def importUserData():
    """Move My List and the counters of the previous versions out of the catalog databases
    (once). Call it before anything that replaces or drops these databases."""
    from resources.lib.models import userdata
    try:
        return userdata.UserData(control.userDataFile).importLegacy(control.showsFile, control.episodesFile)
    except Exception as e:
        logger.logError('Can\'t import the user data: %s' % str(e))
        return 0

def importDBFiles():
    """Install the catalog seed (ready-made shows, episodes and celebrities databases)"""
    from resources.lib.libraries import seed
    control.showNotification(control.lang(37056), control.lang(30005))
    importUserData()  # before the catalog databases are replaced
    result = seed.installCatalogSeed(
        control.setting('catalogSeedURL'),
        {'shows.db': control.showsFile, 'episodes.db': control.episodesFile, 'celebrities.db': control.celebritiesFile},
        control.userDataFile,
        lambda percent: control.showNotification('%d%%' % percent, control.lang(37056), time=1000) if percent % 25 == 0 else None
    )
    if result is None:
        control.showNotification(control.lang(37058), control.lang(30004), time=8000)
        return False
    notFound, manifest = result
    control.setSetting('showUpdateCatalog', 'false')
    control.setSetting('catalogSeedVersion', manifest.get('catalogVersion', ''))
    control.showNotification(control.lang(37057), control.lang(30010))
    if notFound:
        control.showMessage(control.lang(37059) % '\n'.join(notFound), control.lang(30002))
    # look for what is new since the seed was made, in the background
    control.execute('RunPlugin(plugin://%s/?mode=%d&caller=seed)' % (control.addonInfo('id'), config.CATCHUPCATALOG))
    return True

def checkInstallDB(refresh=False):
    control.showNotification(control.lang(30005))
    if refresh == True or isDBInstalled() == False:
        importDBFiles()

def isDBInstalled():
    if control.setting('showUpdateCatalog') == 'false' and os.path.exists(control.episodesFile) and os.path.exists(control.showsFile):
        return True
    return False
