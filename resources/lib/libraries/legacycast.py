# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik

    The show/actor links of the old catalog (before the iWantTFC redesign) that the new API doesn't
    give anymore: resources/data/legacy_cast.json (built by .github/scripts/build_legacy_cast.py),
    merged once into the cast database next to what the API provides.
'''

import json
import os

from resources.lib.libraries import control

logger = control.logger

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'legacy_cast.json')
FLAG = 'legacyCastImported'


def importLegacyCast(castDB, path=DATA):
    """Replace the cast rows of the old catalog (stored without a source, they point to shows that don't
    exist anymore) with the links that could be attached to a show of the current catalog.
    Done once. Returns the number of added links."""
    userData = castDB.getUserData()
    if userData.getMeta(FLAG) == '1':
        return 0
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    purged = castDB.purgeUnsourced()
    added = castDB.addLegacyCast([(showId, name, order) for showId, names in data.get('shows', {}).items() for name, order in names])
    userData.setMeta(FLAG, 1)
    logger.logNotice('Legacy cast: %d old rows removed, %d links added' % (max(purged, 0), added))
    return added
