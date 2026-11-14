# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

import sys
import time
from resources import router
from resources.lib.libraries import control

# Debug 
logger = control.logger 
if control.setting('debug') == 'true':
    logger.enable(True)
    try:
        debug_level = control.setting('debugLevel')
        newLevel = getattr(logger, f'LOG{debug_level}', logger.LOGINFO)
        logger.setLevel(newLevel)
    except (AttributeError, TypeError) as e:
        logger.logError(f"Failed to set debug level: {e}")
        pass

exec_start = time.time()

logger.logInfo(sys.argv[2])

request = router.Request(sys.argv[2])

if request.caller == 'addon' and control.setting('lastVersion') != control.addonInfo('version'):
    from resources import upgrade
    logger.logInfo(control.lang(37023))
    control.showMessage(control.lang(37023) % control.addonInfo('version'), control.lang(30002))
    upgrade.upgradeDB()
    upgrade.upgradeSettings()
    control.setSetting('lastVersion', control.addonInfo('version'))

router.route(request)

logger.logNotice('Finished in %s' % str(time.time() - exec_start))
