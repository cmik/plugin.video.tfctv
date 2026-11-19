# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''



"""
The building blocks of the directory listings: the list items (titles, art, infos, context menus), the plugin URLs
and the end of a directory. `navigator` (the menus and the lists) inherits them.
"""

import re
import sys
from urllib.parse import quote_plus, urlencode
from resources import config
from resources.lib.libraries import control
from resources.lib.sources import tfctv

logger = control.logger
sysaddon = control.sysaddon
thisPlugin = control.thisPlugin

EPISODE_TITLE = re.compile(r'S(\d+)E(\d+) (.+)', re.IGNORECASE)


def episodeTitle(title, show):
    """How an episode is listed: "S1E2 Name" becomes "Show | Episode 2 | Name", the other titles are kept"""
    found = EPISODE_TITLE.search(title or '')
    return '%s | Episode %s | %s' % (show, found.group(2), found.group(3)) if found else title


class Listing(object):

    def showMode(self, show):
        """A show with several seasons offers the choice of the season before its episodes"""
        return config.SEASONS if (show.get('nbSeasons') or 0) > 1 else config.SHOWEPISODES

    def traktEntry(self, showId, title, year):
        """The context menu entry that links a show to its show on Trakt (none when the show is not known)"""
        if not showId or not title:
            return {}
        return { control.lang(30248) : 'RunPlugin(%s)' % self.generateActionUrl(str(showId), config.TRAKTLINK, title, query={'year': year or ''}) }

    def showTarget(self, info):
        """The URL that opens the show of an episode: its seasons when it has several, else its episodes
        (None for movies and when the show is not known)"""
        showId = info.get('parentid')
        if not showId or str(showId) == str(info.get('id')) or info.get('ltype') in ('movie', 'documentary', 'livestream', 'channel'):
            return None
        show = info.get('showObj') or {}
        mode = self.showMode(show)
        query = {'parentid': str(show.get('parentid', '')), 'year': show.get('year', '')} if mode == config.SHOWEPISODES else ''
        return self.generateActionUrl(str(showId), mode, info.get('show') or show.get('name') or '', show.get('image') or '', query=query)

    def actionItem(self):
        """What an entry that runs an action (not a listing) needs: Kodi runs the plugin without waiting for a listing
        (a folder entry logs "GetDirectory - Error getting plugin", also when the plugin ends the directory as failed)"""
        return {'isFolder': False, 'listProperties': {'IsPlayable': 'false'}}

    def addPlayableEpisodes(self, episodes, options={}):
        """List episodes (or movies) that can be played, with the same title format as the episode lists"""
        for e in episodes:
            title = episodeTitle(e.get('title'), e.get('show'))
            self.addDirectoryItem(title, str(e.get('id')), config.PLAY, e.get('image'), isFolder=False, query={'ltype': e.get('ltype'), 'title': title}, **self.formatVideoInfo(e, options=options))

    def formatMenu(self, bgImage=''):
        if bgImage == '':
            bgImage = control.setting('defaultBG')
        data = { 
            'listArts' : { 'fanart' : bgImage, 'banner' : bgImage }
            }
        return data

    def formatShowInfo(self, info, addToList=True, options = {}):
        contextMenu = {}
        # add to mylist / remove from mylist
        add = { control.lang(30300) : 'RunPlugin(%s)' % self.generateActionUrl(str(info.get('id')), config.ADDTOLIST, info.get('name'), query={'ltype': info.get('ltype'), 'type': info.get('type')}) } 
        remove = { control.lang(30301) : 'RunPlugin(%s)' % self.generateActionUrl(str(info.get('id')), config.REMOVEFROMLIST, info.get('name'), query={'ltype': info.get('ltype'), 'type': info.get('type')}) } 
        if addToList:
            if info.get('ltype') not in ('livestream', 'channel', 'unknown'):  # a channel can't be in My List (nor on iWant)
                contextMenu.update(add)
        else:
            contextMenu.update(remove)
        if control.setting('traktScrobble') == 'true' and info.get('ltype') == 'show':
            contextMenu.update(self.traktEntry(info.get('id'), info.get('name'), info.get('year')))
        # export to library
        if control.setting('exportToLibrary') == 'true':
            addToLibrary = { control.lang(30302) : 'RunPlugin(%s)' % self.generateActionUrl(str(info.get('id')), config.ADDTOLIBRARY, info.get('name'), query={'parentid': str(info.get('parentid')), 'year' : info.get('year'), 'ltype' : info.get('ltype'), 'type' : info.get('type')}) }
            removeFromLibrary = { control.lang(30304) : 'RunPlugin(%s)' % self.generateActionUrl(str(info.get('id')), config.REMOVEFROMLIBRARY, info.get('name'), query={'parentid': str(info.get('parentid')), 'year' : info.get('year'), 'ltype' : info.get('ltype'), 'type' : info.get('type')}) }
            if info.get('inLibrary', False):
                contextMenu.update(removeFromLibrary)
            else:
                contextMenu.update(addToLibrary)
            
        
        data = { 
            'listArts' : { 
                'clearlogo' : info.get('logo'), 
                'fanart' : info.get('fanart'), 
                'banner' : info.get('banner'), 
                'tvshow.poster': info.get('banner'), 
                'season.poster': info.get('banner'), 
                'tvshow.banner': info.get('banner'), 
                'season.banner': info.get('banner') 
                }, 
            'listInfos' : { 
                'video' : { 
                    'sorttitle': info.get('name'),
                    'plot' : info.get('description'), 
                    'year' : info.get('year'),
                    'mediatype' : 'tvshow',
                    'studio': 'ABS-CBN', 
                    'duration': info.get('duration', 0), 
                    'rating': info.get('rating', 0), 
                    'votes': info.get('votes', 0), 
                    } 
                },
            'contextMenu' : contextMenu
            }
        
        if info.get('casts', False):    
            data['listCasts'] = info.get('casts')
        
        return logger.logDebug(data)

    def formatVideoInfo(self, info, addToList=True, options = {}):

        contextMenu = {}
        # add to mylist / remove from mylist
        add = { control.lang(30300) : 'RunPlugin(%s)' % self.generateActionUrl(str(info.get('id')), config.ADDTOLIST, info.get('title'), query={'ltype': info.get('ltype'), 'type': info.get('ltype')}) } 
        remove = { control.lang(30301) : 'RunPlugin(%s)' % self.generateActionUrl(str(info.get('id')), config.REMOVEFROMLIST, info.get('title'), query={'ltype': info.get('ltype'), 'type': info.get('ltype')}) } 
        if addToList:
            if info.get('ltype') not in ('livestream', 'channel', 'unknown'):  # a channel can't be in My List (nor on iWant)
                contextMenu.update(add)
        else:
            contextMenu.update(remove)
        if options.get('goToShow') and self.showTarget(info):
            contextMenu.update({ control.lang(30306) : 'Container.Update(%s)' % self.showTarget(info) })
        if control.setting('traktScrobble') == 'true' and info.get('parentid') and info.get('ltype') not in ('movie', 'documentary', 'livestream', 'channel'):
            show = info.get('showObj') or {}
            contextMenu.update(self.traktEntry(info.get('parentid'), info.get('show') or show.get('name'), show.get('year') or info.get('year')))
        if options.get('history'):
            contextMenu.update({ control.lang(30305) : 'RunPlugin(%s)' % self.generateActionUrl(str(info.get('id')), config.REMOVEFROMHISTORY, info.get('title')) })

        data = { 
            'listArts' : { 
                'fanart' : info.get('fanart'), 
                'banner' : info.get('fanart')
                }, 
            'listProperties' : { 'IsPlayable' : 'true' } , 
            'listInfos' : { 
                'video' : { 
                    'sorttitle' : info.get('dateaired'), 
                    'tvshowtitle' : info.get('show'), 
                    'episode' : info.get('episodenumber'), 
                    'tracknumber' : info.get('episodenumber'), 
                    'plot' : info.get('description'), 
                    'aired' : info.get('dateaired'), 
                    'premiered' : info.get('dateaired'), 
                    'year' : info.get('year'), 
                    'mediatype' : info.get('type'),
                    'studio': 'ABS-CBN', 
                    'duration': info.get('duration', 0), 
                    'rating': info.get('rating', 0), 
                    'votes': info.get('votes', 0),
                    # what was played is flagged as viewed
                    'playcount': info['views'] if info.get('views') is not None else tfctv.getEpisodeViews(info.get('id')),
                    'lastplayed': info.get('dateviewed', ''),
                    'resumetime': info.get('resumeposition', 0),
                    'totaltime': info.get('totaltime', 0)
                    } 
                },
            'contextMenu' : contextMenu
            }

        if info.get('showObj', False):
            data['listArts'].update({
                'poster': info.get('showObj').get('banner'), 
                'tvshow.banner': info.get('showObj').get('banner'), 
                'season.banner': info.get('showObj').get('banner'),
                'tvshow.poster': info.get('showObj').get('banner'), 
                'season.poster': info.get('showObj').get('banner')
                })
            data['listInfos']['video'].update({
                'genre': info.get('showObj').get('parentname'),
                })
            if info.get('showObj').get('casts', False):    
                data['listCasts'] = info.get('showObj').get('casts')
        
        return logger.logDebug(data)

    def addDirectoryItem(self, name, url, mode, thumbnail, page=1, isFolder=True, query='', **kwargs):
        u = self.generateActionUrl(url, mode, name, thumbnail, page, query)
        item = control.item(label=name)
        tag = item.getVideoInfoTag()
        tag.setTitle(name)
        item.setArt({'icon':"DefaultFolder.png", 'thumb':thumbnail})
        for k, v in kwargs.items():
            if k == 'listProperties':
                for listPropertyKey, listPropertyValue in v.items():
                    item.setProperty(listPropertyKey, listPropertyValue)
            if k == 'listInfos':
                for listInfoKey, listInfoValue in v.items():
                    if listInfoKey == 'video':
                        infoLabels = listInfoValue
                        if 'title' in infoLabels: tag.setTitle(infoLabels['title'])
                        if 'plot' in infoLabels: tag.setPlot(infoLabels['plot'])
                        if 'genre' in infoLabels: tag.setGenres([infoLabels['genre']] if isinstance(infoLabels['genre'], str) else infoLabels['genre'])
                        if 'year' in infoLabels: tag.setYear(int(infoLabels['year']) if str(infoLabels['year']).isdigit() else 0)
                        if 'episode' in infoLabels: tag.setEpisode(int(infoLabels['episode']) if str(infoLabels['episode']).isdigit() else 0)
                        if 'season' in infoLabels: tag.setSeason(int(infoLabels['season']) if str(infoLabels['season']).isdigit() else 0)
                        if 'tvshowtitle' in infoLabels: tag.setTvShowTitle(infoLabels['tvshowtitle'])
                        if 'aired' in infoLabels: tag.setFirstAired(infoLabels['aired'])
                        if 'duration' in infoLabels: tag.setDuration(int(infoLabels['duration']) if str(infoLabels['duration']).isdigit() else 0)
                        if 'mediatype' in infoLabels: tag.setMediaType(infoLabels['mediatype'])
                        if 'playcount' in infoLabels: tag.setPlaycount(int(infoLabels['playcount']) if str(infoLabels['playcount']).isdigit() else 0)
                        if infoLabels.get('lastplayed'): tag.setLastPlayed(infoLabels['lastplayed'])
                        # Kodi shows the progress bar and offers its own Resume / Play from beginning, and applies them
                        if infoLabels.get('resumetime'): tag.setResumePoint(float(infoLabels['resumetime']), float(infoLabels.get('totaltime') or 0))
                    else:
                        item.setInfo(listInfoKey, listInfoValue)
            if k == 'listArts':
                item.setArt(v)
            if k == 'listCasts':
                try:
                    import xbmc
                    tag.setCast([xbmc.Actor(castMember.get('name', ''), order=castMember.get('order', 0)) for castMember in v])
                except Exception as e:
                    logger.logError('Error occurred while setting cast: %s' % e)
                    logger.logDebug(v)
            if k == 'contextMenu':
                menuItems = []
                for label, action in v.items():
                    menuItems.append((label, action))
                if len(menuItems) > 0: item.addContextMenuItems(menuItems)
        return control.addItem(handle=thisPlugin, url=u, listitem=item, isFolder=isFolder)

    def generateActionUrl(self, url, mode, name=None, thumbnail='', page=1, query=''):
        url = '%s?url=%s&mode=%s' % (sysaddon, quote_plus(url), str(mode))
        try: 
            if name is not None: 
                url += '&name=%s' % quote_plus(name)
        except Exception as e: 
            logger.logError('Error occurred while generating action URL (name): %s' % e)
        try: 
            if int(page) >= 0: 
                url += '&page=%s' % str(page)
        except Exception as e: 
            logger.logError('Error occurred while generating action URL (page): %s' % e)
        try: 
            if thumbnail != '': 
                url += '&thumbnail=%s' % quote_plus(thumbnail)
        except Exception as e: 
            logger.logError('Error occurred while generating action URL (thumbnail): %s' % e)
        try: 
            if query != '' and query is not None: 
                if isinstance(query, dict): 
                    query = urlencode(query)
                url += "&" + query
        except Exception as e: 
            logger.logError('Error occurred while generating action URL (query): %s' % e)
        return logger.logDebug(url)

    def endDirectory(self, cacheToDisc=True, content=None, sortMethods=('unsorted',)):
        control.setListing(int(sys.argv[1]), content, sortMethods)
        control.directory(int(sys.argv[1]), cacheToDisc=cacheToDisc)
