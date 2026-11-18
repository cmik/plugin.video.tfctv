# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik

    Synchronisation of My List (Kodi) with the watchlist of the iWant website: what to do for each way to settle
    the differences. No Kodi nor network here, the ids are the ids of the shows and movies.
'''

MERGE = 'merge'      # both lists get everything of the other one, nothing is removed
KODI = 'kodi'        # Kodi's My List becomes the one of iWant
IWANT = 'iwant'      # the watchlist of iWant becomes Kodi's My List


def differences(local, remote):
    """(ids only in Kodi, ids only on iWant), each in a stable order"""
    local, remote = list(dict.fromkeys(local)), list(dict.fromkeys(remote))
    return [i for i in local if i not in set(remote)], [i for i in remote if i not in set(local)]


def plan(mode, local, remote):
    """What to change for `mode`: {'localAdd', 'localRemove', 'remoteAdd', 'remoteRemove'} (lists of ids)"""
    onlyLocal, onlyRemote = differences(local, remote)
    changes = {'localAdd': [], 'localRemove': [], 'remoteAdd': [], 'remoteRemove': []}
    if mode == MERGE:
        changes['localAdd'], changes['remoteAdd'] = onlyRemote, onlyLocal
    elif mode == KODI:
        changes['localAdd'], changes['localRemove'] = onlyRemote, onlyLocal
    elif mode == IWANT:
        changes['remoteAdd'], changes['remoteRemove'] = onlyLocal, onlyRemote
    else:
        raise ValueError('unknown mode %s' % mode)
    return changes
