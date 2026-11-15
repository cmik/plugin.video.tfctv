# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik

    Live channels: what the playback request of a channel needs more than the one of an episode.
    The website sends, for a channel, the id again with the country and the platform in the address, and the
    rail it was chosen from: without them the server answers 400 "Invalid asset id".
'''

from urllib.parse import urlencode

LIVE = 'livestream'

# where the website lists the channels (the rail the user picked it in)
LIVE_REFERRAL = {
    'railTitle': 'Live Channels',
    'railType': 'Circle',
    'railSubType': 'not_available',
    'pageName': 'page_content_browser_home'
}


def isLive(ltype):
    return ltype == LIVE


def startPath(path, contentId, ltype, country='FR', platform='web', subPlatform='firefox'):
    """The address of the playback request: with the parameters the website adds for a channel"""
    if not isLive(ltype):
        return path
    return '%s?%s' % (path, urlencode([('offline', 'false'), ('country', country or 'FR'), ('contentId', contentId),
                                       ('platform', platform), ('subPlatform', subPlatform)]))


def withReferral(body, ltype):
    """The body of the playback request: with the rail of the channels for a channel"""
    if not isLive(ltype):
        return body
    return dict(body, referralProperties=dict(LIVE_REFERRAL))
