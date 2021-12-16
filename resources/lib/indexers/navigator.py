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


import os,sys,urlparse,urllib,xbmc,time,re
from resources import config
from resources.lib.libraries import control
from resources.lib.libraries import cache
from resources.lib.sources import tfctv
from operator import itemgetter

artPath = control.artPath()
addonFanart = control.addonFanart()
logger = control.logger

try: 
    action = dict(urlparse.parse_qsl(sys.argv[2].replace('?','')))['action']
except:
    action = None

sysaddon = sys.argv[0]
thisPlugin = int(sys.argv[1])

class navigator:

    def root(self):
        if control.setting('useProxy') == 'true':
            tfctv.checkProxy()
            
        if control.setting('addonNewInstall') == 'true':
            self.firstInstall()
        else:
            self.showMainMenu()
    
    def showMainMenu(self):
        logger.logInfo('called function')
        self.addDirectoryItem(control.lang(50204), config.uri.get('base'), config.SEARCHMENU, control.addonFolderIcon(control.lang(50204)), isFolder=True, **self.formatMenu())

        # if not logged in, ask to log in
        if tfctv.isLoggedIn() == False:
            if control.setting('loginType') == 'TFC.tv' and control.setting('emailAddress') != '':
                if (control.confirm(control.lang(57007), line1=control.lang(57008) % control.setting('emailAddress'))):
                    (account, logged) = tfctv.checkAccountChange(True)
            else:
                if (control.confirm(control.lang(57007), line1=control.lang(57051))):
                    tfctv.login()
        
        if tfctv.isLoggedIn() == True and control.setting('displayMyList') == 'true':
            self.addDirectoryItem(control.lang(50200), config.uri.get('base'), config.MYLIST, control.addonFolderIcon(control.lang(50200)), isFolder=True, **self.formatMenu())
        
        if control.setting('displayWebsiteSections') == 'true':
            self.addDirectoryItem(control.lang(50201), config.uri.get('base'), config.CATEGORIES, control.addonFolderIcon(control.lang(50201)), isFolder=True, **self.formatMenu())
        else:
            self.showCategories()
            
        if control.setting('displayWebsiteSections') == 'true':
            control.showNotification(control.lang(57020), control.lang(50008))
            sections = tfctv.getWebsiteHomeSections()
            for s in sections:
                self.addDirectoryItem(s['name'].title(), str(s['id']), config.SECTIONCONTENT, control.addonFolderIcon(s['name'].title()), isFolder=True, **self.formatMenu())
            
        # if control.setting('displayMyAccountMenu') == 'true' and control.setting('emailAddress') != '':
        #     self.addDirectoryItem(control.lang(50202), config.uri.get('base'), config.MYACCOUNT, control.addonFolderIcon(control.lang(50202)), isFolder=True, **self.formatMenu())

        if control.setting('exportToLibrary') == 'true':
            self.addDirectoryItem(control.lang(56023), config.uri.get('base'), config.EXPORTEDSHOWS, control.addonFolderIcon(control.lang(56023)), isFolder=True, **self.formatMenu())
        
        if control.setting('displayTools') == 'true':
            self.addDirectoryItem(control.lang(50203), config.uri.get('base'), config.TOOLS, control.addonFolderIcon(control.lang(50203)))
            
        self.endDirectory()
        
        if tfctv.isLoggedIn() == False:
            control.infoDialog(control.lang(57017), control.lang(50002), time=8000)
            
    def showMyList(self):
        logger.logInfo('called function')
        self.addDirectoryItem(control.lang(50213), '/', config.MYLISTSHOWLASTEPISODES, control.addonFolderIcon(control.lang(50213)), isFolder=True, **self.formatMenu())
        self.addDirectoryItem(control.lang(50214), '/', config.LISTCATEGORY, control.addonFolderIcon(control.lang(50214)), isFolder=True, **self.formatMenu())
        self.endDirectory()

    def showMyListShowLastEpisodes(self):
        logger.logInfo('called function') 
        episodes = tfctv.getMylistShowLastEpisodes()
        for e in episodes:
            title = e.get('title')
            title_match = re.compile('S(\d+)E(\d+) (.+)', re.IGNORECASE).search(e.get('title'))
            if title_match:
                title = '%s | Episode %s | %s' % (e.get('show'), title_match.group(2), title_match.group(3))
            self.addDirectoryItem(title, str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query={'title': title}, **self.formatVideoInfo(e, addToList=False))
        self.endDirectory()

    def showMyListCategory(self, url):
        logger.logInfo('called function')
        items = tfctv.getMyList()
        for item in items:
            image = item.get('logo') if control.setting('useShowLogo') == 'true' else item.get('image')
            self.addDirectoryItem(item.get('name'), str(item.get('id')), config.SHOWEPISODES, image, isFolder=True, query={'parentid' : str(item.get('parentid')), 'year' : item.get('year')}, **self.formatShowInfo(item, addToList=False))
        self.endDirectory()
            
    def showCategories(self):
        logger.logInfo('called function')
        categories = tfctv.getCategories()
        for c in categories:
            self.addDirectoryItem(c.get('name'), str(c.get('id')), config.SUBCATEGORYSHOWS, control.addonFolderIcon(c.get('name')), isFolder=True, **self.formatMenu())
            
        if control.setting('displayWebsiteSections') == 'true':
            self.endDirectory()
       
    def showSubCategoryShows(self, subCategoryId):
        logger.logInfo('called function')
        shows = tfctv.getShows(subCategoryId)
        if len(shows) > 0:
            self.displayShows(shows)
        else:
            self.endDirectory()
        
    def showWebsiteSectionContent(self, section, page=1):
        logger.logInfo('called function')
        itemsPerPage = int(control.setting('itemsPerPage'))
        content = tfctv.getWebsiteSectionContent(section, page, itemsPerPage)
        for e in content:
            if e['ltype'] == 'show':
                image = e.get('logo') if control.setting('useShowLogo') == 'true' else e.get('image')
                self.addDirectoryItem(e.get('name'), str(e.get('id')), config.SHOWEPISODES, image, isFolder=True, **self.formatShowInfo(e))
            elif e['ltype'] in ('movie', 'episode', 'documentary', 'livestream'):
                title = e.get('name')
                title_match = re.compile('S(\d+)E(\d+) (.+)', re.IGNORECASE).search(e.get('name'))
                if title_match:
                    title = '%s | Episode %s | %s' % (e.get('show'), title_match.group(2), title_match.group(3))
                self.addDirectoryItem(title, str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query={'ltype': e['ltype'], 'title': title}, **self.formatVideoInfo(e))
        if len(content) == itemsPerPage:
            self.addDirectoryItem(control.lang(56008), section, config.SECTIONCONTENT, '', page + 1)
        self.endDirectory()

    def displayShows(self, shows):
        logger.logInfo('called function')
        sortedShowInfos = []
        for show in shows:
            image = show['logo'] if control.setting('useShowLogo') == 'true' else show['image']
            if show['ltype'] == 'show':
                sortedShowInfos.append((show.get('name').lower(), show.get('name'), str(show.get('id')), config.SHOWEPISODES, image, True, {'parentid' : str(show.get('parentid')), 'year' : show.get('year')}, self.formatShowInfo(show)))
            elif show['ltype'] in ('movie', 'episode', 'documentary', 'livestream'):
                title = show.get('name')
                sortedShowInfos.append((title.lower(), title, str(show.get('id')), config.PLAY, show.get('image'), False, {'ltype': show['ltype'], 'title': title}, self.formatVideoInfo(show)))
        
        sortedShowInfos = sorted(sortedShowInfos, key = itemgetter(0))
        for info in sortedShowInfos:
            self.addDirectoryItem(info[1], info[2], info[3], info[4], isFolder=info[5], query=info[6], **info[7])
                
        self.endDirectory()
        
    def showEpisodes(self, showId, page=1):
        logger.logInfo('called function')
        itemsPerPage = int(control.setting('itemsPerPage'))
        (episodes, nextPage) = tfctv.getEpisodesPerPage(showId, page, itemsPerPage)
        episodes = sorted(episodes, key=lambda item: item['title'], reverse=True)
        for e in episodes:
            title = e.get('title')
            title_match = re.compile('S(\d+)E(\d+) (.+)', re.IGNORECASE).search(e.get('title'))
            if title_match:
                title = '%s | Episode %s | %s' % (e.get('show'), title_match.group(2), title_match.group(3))
            self.addDirectoryItem(title, str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query={'ltype': e.get('ltype'), 'title': e.get('title')}, **self.formatVideoInfo(e, addToList=False))
        if len(episodes) == itemsPerPage or nextPage == True:
            self.addDirectoryItem(control.lang(56008), showId, config.SHOWEPISODES, '', page + 1)
        self.endDirectory()

    def chooseBandwidth(self, episodeId, title, type, thumbnail):
        logger.logInfo('called function')
        bandwidths = tfctv.getEpisodeBandwidthList(episodeId, title, type, thumbnail)
        for e in bandwidths: # sorted(bandwidths, key = itemgetter('bandwidth')):
            title = e.get('title')
            title_match = re.compile('S(\d+)E(\d+) (.+)', re.IGNORECASE).search(e.get('title'))
            if title_match:
                title = '%s | Episode %s | %s' % (e.get('show'), title_match.group(2), title_match.group(3))
            self.addDirectoryItem('%s | %sp | %s' % (title, e.get('resolution').split('x')[1], e.get('resolution')), str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query={'ltype': e.get('ltype'), 'title': e.get('title'), 'bandwidth': e.get('bandwidth')}, **self.formatVideoInfo(e))
        self.endDirectory()

    def showSearchMenu(self, category):    
        logger.logInfo('called function')
        if category == 'movieshow':
            self.addDirectoryItem(control.lang(50208), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(50208)), isFolder=True, query='category=%s&type=%s' % (category, 'title'), **self.formatMenu())
            self.addDirectoryItem(control.lang(50209), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(50209)), isFolder=True, query='category=%s&type=%s' % (category, 'category'), **self.formatMenu())
            self.addDirectoryItem(control.lang(50210), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(50210)), isFolder=True, query='category=%s&type=%s' % (category, 'cast'), **self.formatMenu())
            self.addDirectoryItem(control.lang(50212), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(50212)), isFolder=True, query='category=%s&type=%s' % (category, 'year'), **self.formatMenu())
        elif category == 'episode':
            self.addDirectoryItem(control.lang(50208), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(50208)), isFolder=True, query='category=%s&type=%s' % (category, 'title'), **self.formatMenu())
            self.addDirectoryItem(control.lang(50211), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(50211)), isFolder=True, query='category=%s&type=%s' % (category, 'date'), **self.formatMenu())
        elif category == 'celebrity':
            control.showNotification(control.lang(57026), control.lang(50001))
        else:
             self.addDirectoryItem(control.lang(50205), config.uri.get('base'), config.SEARCHMENU, control.addonFolderIcon(control.lang(50205)), isFolder=True, query='category=%s' % 'movieshow', **self.formatMenu())
             self.addDirectoryItem(control.lang(50206), config.uri.get('base'), config.SEARCHMENU, control.addonFolderIcon(control.lang(50206)), isFolder=True, query='category=%s' % 'episode', **self.formatMenu())
            #  self.addDirectoryItem(control.lang(50207), config.uri.get('base'), config.SEARCHMENU, control.addonFolderIcon(control.lang(50207)), isFolder=True, query='category=%s' % 'celebrity', **self.formatMenu())
        self.endDirectory()

    def executeSearch(self, category, type):
        logger.logInfo('called function')
        if category != False and type != False:
            result = tfctv.enterSearch(category, type)
            if len(result) > 0:
                if category == 'movieshow':
                    self.displayShows(result)
                    return True
                elif category == 'episode':
                    for e in sorted(result, key=lambda episode: episode['show']):
                        title = e.get('title')
                        title_match = re.compile('S(\d+)E(\d+) (.+)', re.IGNORECASE).search(e.get('title'))
                        if title_match:
                            title = '%s | Episode %s | %s' % (e.get('show'), title_match.group(2), title_match.group(3))
                        self.addDirectoryItem(title, str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query={'title' : title}, **self.formatVideoInfo(e, addToList=False))
        self.endDirectory()
            
    def showMyAccount(self):
        logger.logInfo('called function')
        tfctv.checkAccountChange(False)
        categories = [
            { 'name' : control.lang(56004), 'url' : config.uri.get('profile'), 'mode' : config.MYINFO },
            { 'name' : control.lang(56005), 'url' : config.uri.get('base'), 'mode' : config.MYSUBSCRIPTIONS },
            { 'name' : control.lang(56006), 'url' : config.uri.get('base'), 'mode' : config.MYTRANSACTIONS }
        ]
        for c in categories:
            self.addDirectoryItem(c.get('name'), c.get('url'), c.get('mode'), control.addonFolderIcon(c.get('name')))
        self.addDirectoryItem(control.lang(56007), config.uri.get('base'), config.LOGOUT, control.addonFolderIcon('Logout'), isFolder = False)    
        self.endDirectory()
    
    def showMyInfo(self):
        logger.logInfo('called function')
        loggedIn = tfctv.isLoggedIn()
        message = control.lang(57002)
        if loggedIn == True:
            try:
                user = tfctv.getUserInfo()
                message = 'First name: %s\nLast name: %s\nEmail: %s\nState: %s\nCountry: %s\nMember since: %s\n\n' % (
                    user.get('firstName', ''),
                    user.get('lastName', ''), 
                    user.get('email', ''), 
                    user.get('state', ''),
                    user.get('country', ''), 
                    user.get('memberSince', '')
                    )
            except:
                pass
        control.showMessage(message, control.lang(56001))
    
    def showMySubscription(self):
        logger.logInfo('called function')
        sub = tfctv.getUserSubscription()
        message = ''
        if sub:
            message += '%s' % (sub.get('details'))
        else:
            message = control.lang(57002)
        control.showMessage(message, control.lang(56002))
        
    def showMyTransactions(self):
        logger.logInfo('called function')
        transactions = tfctv.getUserTransactions()
        message = ''
        if len(transactions) > 0:
            for t in transactions:
                message += t + "\n"
        else:
            message = control.lang(57002)
        control.showMessage(message, control.lang(56003))

    def showExportedShows(self):
        logger.logInfo('called function')
        exported = tfctv.showExportedShowsToLibrary()
        self.displayShows(exported)

    def removeShowFromLibrary(self, id, name):
        logger.logInfo('called function')
        tfctv.removeFromLibrary(id, name)
        control.refresh()
            
    def showTools(self):
        logger.logInfo('called function')
        self.addDirectoryItem(control.lang(56021), config.uri.get('base'), config.IMPORTALLDB, control.addonFolderIcon(control.lang(56021)))
        self.addDirectoryItem(control.lang(56019), config.uri.get('base'), config.IMPORTSHOWDB, control.addonFolderIcon(control.lang(56019)))
        self.addDirectoryItem(control.lang(56020), config.uri.get('base'), config.IMPORTEPISODEDB, control.addonFolderIcon(control.lang(56020)))
        self.addDirectoryItem(control.lang(50215), config.uri.get('base'), config.CHECKFORUPDATES, control.addonFolderIcon(control.lang(50215)))
        self.addDirectoryItem(control.lang(56009), config.uri.get('base'), config.RELOADCATALOG, control.addonFolderIcon(control.lang(56009)))
        self.addDirectoryItem(control.lang(56018), config.uri.get('base'), config.RESETCATALOG, control.addonFolderIcon(control.lang(56018)))
        self.addDirectoryItem(control.lang(56017), config.uri.get('base'), config.CHECKLIBRARYUPDATES, control.addonFolderIcon(control.lang(56017)))
        self.addDirectoryItem(control.lang(56010), config.uri.get('base'), config.CLEANCOOKIES, control.addonFolderIcon(control.lang(56010)))
        self.addDirectoryItem(control.lang(56022), config.uri.get('base'), config.FIRSTINSTALL, control.addonFolderIcon(control.lang(56022)))
        self.endDirectory()
            
    def firstInstall(self):
        logger.logInfo('called function')
        if control.setting('showWelcomeMessage') == 'true':
            control.showMessage(control.lang(57016), control.lang(57018))
            control.setSetting('showWelcomeMessage', 'false')
        
        self.addDirectoryItem(control.lang(56025), config.uri.get('base'), config.LOGINWITHTFC, control.addonIcon())
        if control.setting('FBAppID') != '' or control.setting('FBClientToken') != '':
            self.addDirectoryItem(control.lang(56024), config.uri.get('base'), config.LOGINWITHFB, control.facebookIcon())
        self.endDirectory()

    def loginWithTFC(self):
        logger.logInfo('called function')
        control.setSetting('loginType', 'TFC.tv')
        if control.setting('emailAddress') == '':
            if control.setting('showEnterCredentials') == 'true':
                self.enterCredentials()
                self.addDirectoryItem(control.lang(56011), config.uri.get('base'), config.ENTERCREDENTIALS, control.addonFolderIcon(control.lang(56011)))
            # self.addDirectoryItem(control.lang(56012) % (' ' if control.setting('showPersonalize') == 'true' else 'x'), config.uri.get('base'), config.PERSONALIZESETTINGS, control.addonFolderIcon(control.lang(56012)))
            # self.addDirectoryItem(control.lang(56013) % (' ' if control.setting('showUpdateCatalog') == 'true' else 'x'), config.uri.get('base'), config.IMPORTALLDB, control.addonFolderIcon(control.lang(56013)))
            self.addDirectoryItem(control.lang(56014) % (control.lang(56015) if control.setting('showEnterCredentials') == 'true' else control.lang(56016)), config.uri.get('base'), config.ENDSETUP, control.addonFolderIcon('Skip'))
            self.endDirectory()
        # else:
        self.endSetup()
        
    def enterCredentials(self):
        logger.logInfo('called function')
        if tfctv.enterCredentials() == True:
            control.setSetting('showEnterCredentials', 'false')
            self.endSetup()

    def loginWithFB(self):
        logger.logInfo('called function')
        control.setSetting('loginType', 'Facebook')
        self.endSetup()
        
    def optimizeLibrary(self):
        logger.logInfo('called function')
        tfctv.reloadCatalogCache()
        control.setSetting('showUpdateCatalog', 'false')
        control.refresh()
        
    def personalizeSettings(self):
        logger.logInfo('called function')
        control.openSettings()
        control.setSetting('showPersonalize', 'false')
        control.refresh()
        
    def endSetup(self):
        logger.logInfo('called function')
        control.setSetting('addonNewInstall', 'false')
        # control.refresh()
        self.showMainMenu()
        
    def formatMenu(self, bgImage=''):
        if bgImage == '': bgImage = control.setting('defaultBG')
        data = { 
            'listArts' : { 'fanart' : bgImage, 'banner' : bgImage }
            }
        return data
        
    def formatShowInfo(self, info, addToList=True, options = {}):
        contextMenu = {}
        # add to mylist / remove from mylist
        add = { control.lang(50300) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.ADDTOLIST, info.get('name'), query={'ltype': info.get('ltype'), 'type': info.get('type')}) } 
        remove = { control.lang(50301) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.REMOVEFROMLIST, info.get('name'), query={'ltype': info.get('ltype'), 'type': info.get('type')}) } 
        if addToList == True: 
            contextMenu.update(add)
        else:
            contextMenu.update(remove)
        # export to library
        if control.setting('exportToLibrary') == 'true':
            addToLibrary = { control.lang(50302) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.ADDTOLIBRARY, info.get('name'), query={'parentid': str(info.get('parentid')), 'year' : info.get('year'), 'ltype' : info.get('ltype'), 'type' : info.get('type')}) }
            removeFromLibrary = { control.lang(50304) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.REMOVEFROMLIBRARY, info.get('name'), query={'parentid': str(info.get('parentid')), 'year' : info.get('year'), 'ltype' : info.get('ltype'), 'type' : info.get('type')}) }
            if info.get('inLibrary', False) == True:
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
        if info.get('bandwidth') == None:
            # add to mylist / remove from mylist
            add = { control.lang(50300) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.ADDTOLIST, info.get('title'), query={'ltype': info.get('ltype'), 'type': info.get('ltype')}) } 
            remove = { control.lang(50301) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.REMOVEFROMLIST, info.get('title'), query={'ltype': info.get('ltype'), 'type': info.get('ltype')}) } 
            if addToList == True: 
                contextMenu.update(add)
            else:
                contextMenu.update(remove)
            # Choose resolution
            contextMenu.update({ control.lang(50303) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.CHOOSEBANDWIDTH, info.get('title'), info.get('image'), query={'title': info.get('title')})})

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
                    'votes': info.get('votes', 0)
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
        liz = control.item(label=name, iconImage="DefaultFolder.png", thumbnailImage=thumbnail)
        liz.setInfo(type="Video", infoLabels={"Title": name})
        for k, v in kwargs.iteritems():
            if k == 'listProperties':
                for listPropertyKey, listPropertyValue in v.iteritems():
                    liz.setProperty(listPropertyKey, listPropertyValue)
            if k == 'listInfos':
                for listInfoKey, listInfoValue in v.iteritems():
                    liz.setInfo(listInfoKey, listInfoValue)
            if k == 'listArts':
                liz.setArt(v)
            if k == 'listCasts':
                try:liz.setCast(v)
                except:pass
            if k == 'contextMenu':
                menuItems = []
                for label, action in v.iteritems():
                    menuItems.append((label, action))
                if len(menuItems) > 0: liz.addContextMenuItems(menuItems)
        return control.addItem(handle=thisPlugin, url=u, listitem=liz, isFolder=isFolder)

    def generateActionUrl(self, url, mode, name=None, thumbnail='', page=1, query=''):
        url = '%s?url=%s&mode=%s' % (sysaddon, urllib.quote_plus(url), str(mode))
        try: 
            if name != None: url += '&name=%s' % urllib.quote_plus(name)
        except: 
            pass
        try: 
            if int(page) >= 0: url += '&page=%s' % str(page)
        except: 
            pass
        try: 
            if thumbnail != '': url += '&thumbnail=%s' % urllib.quote_plus(thumbnail)
        except: 
            pass    
        try: 
            if query != '' and query != None: 
                if isinstance(query, dict): query = urllib.urlencode(query)
                url += "&" + query
        except: 
            pass
        return logger.logDebug(url)

    def endDirectory(self, cacheToDisc=True):
        control.directory(int(sys.argv[1]), cacheToDisc=cacheToDisc)


