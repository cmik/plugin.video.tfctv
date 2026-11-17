# -*- coding: utf-8 -*-

"""
Trakt: connection of the account (the scrobbling itself is done by the service, see libraries/trakt.py)
"""

import xbmc

from resources.lib.libraries import control
from resources.lib.libraries import trakt as traktLibrary
from resources.lib.models import userdata

logger = control.logger


def getTraktClient(store=None):
    """The Trakt client of the add-on, or of the application the user gave in the settings"""
    return traktLibrary.fromSettings(store or userdata.UserData(control.userDataFile))


def connectTrakt():
    """Device flow: show a code to enter on trakt.tv and wait until it is entered"""
    client = getTraktClient()
    code = client.deviceCode()
    if not code:
        control.alert(control.lang(30238), title=control.lang(30231))
        return False
    interval = max(int(code.get('interval', 5)), 1)
    expires = max(int(code.get('expires_in', 600)), interval)
    message = control.lang(30239) % (code.get('verification_url', 'https://trakt.tv/activate'), code.get('user_code', ''))
    dialog = control.progressDialog
    dialog.create(control.lang(30231), message)
    monitor = xbmc.Monitor()
    waited, result = 0, 'pending'
    try:
        while waited < expires and not dialog.iscanceled() and not monitor.abortRequested():
            dialog.update(int(waited * 100 / expires), message)
            if monitor.waitForAbort(interval):
                break
            waited += interval
            result = client.pollToken(code['device_code'])
            if result == 'slow':
                interval += 1
            elif result != 'pending':
                break
    finally:
        dialog.close()
    if result == 'connected':
        control.showNotification(control.lang(30240), control.lang(30231))
        return True
    if result == 'failed' or waited >= expires:
        control.alert(control.lang(30241), title=control.lang(30231))
    return False


def disconnectTrakt():
    client = getTraktClient()
    if not client.isConnected():
        control.showNotification(control.lang(30242), control.lang(30231))
        return False
    client.disconnect()
    control.showNotification(control.lang(30243), control.lang(30231))
    return True


def chooseTraktShow(showId, title, year=None):
    """Lets the user choose which show of Trakt is a show of the add-on (the 5 most likely ones, a search with
    another title, or "not on Trakt"); the choice is kept and used for the scrobbling of its episodes"""
    if not showId or not title:
        return False
    client = getTraktClient()
    query = title
    while True:
        found = client.suggestions(query, year)
        if found is None:
            control.alert(control.lang(30238), title=control.lang(30231))
            return False
        labels = ['%s (%s)' % (c['title'], c['year']) if c.get('year') else c['title'] for c in found]
        labels += [control.lang(30251), control.lang(30252)]
        choice = control.selectDialog(labels, control.lang(30250) % query)
        if choice < 0:
            return False
        if choice < len(found):
            client.chooseShow(showId, found[choice]['id'])
            control.showNotification(control.lang(30253) % (title, found[choice]['title']), control.lang(30231))
            return True
        if choice == len(found):
            typed = control.inputText(control.lang(30255), query)
            if typed and typed.strip():
                query = typed.strip()
            continue
        client.chooseShow(showId, None)
        control.showNotification(control.lang(30254) % title, control.lang(30231))
        return True
