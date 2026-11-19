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


from operator import itemgetter
from resources import config
from resources.lib.indexers.listing import Listing, episodeTitle
from resources.lib.libraries import control
from resources.lib.sources import tfctv

logger = control.logger


class navigator(Listing):

    def root(self):
        if control.setting('useProxy') == 'true':
            tfctv.checkProxy()
            
        if control.setting('addonNewInstall') == 'true':
            self.firstInstall()
        else:
            self.showMainMenu()
    
    def myAccountShown(self):
        return control.setting('displayMyAccountMenu') == 'true' and control.setting('emailAddress') != ''

    def showMainMenu(self):
        logger.logInfo('called function')
        self.addDirectoryItem(control.lang(30204), config.uri.get('base'), config.SEARCHMENU, control.addonFolderIcon(control.lang(30204)), isFolder=True, **self.formatMenu())

        # if not logged in, ask to log in
        if not tfctv.isLoggedIn():
            if control.setting('loginType') == 'TFC.tv' and control.setting('emailAddress') != '':
                if (control.confirm('%s\n%s' % (control.lang(37007), control.lang(37008) % control.setting('emailAddress')))):
                    (account, logged) = tfctv.checkAccountChange(True)
            else:
                if (control.confirm('%s\n%s' % (control.lang(37007), control.lang(37051)))):
                    tfctv.login()
        
        if tfctv.isLoggedIn() and control.setting('displayMyList') == 'true':
            self.addDirectoryItem(control.lang(30200), config.uri.get('base'), config.MYLIST, control.addonFolderIcon(control.lang(30200)), isFolder=True, **self.formatMenu())
        
        if control.setting('displayContinueWatching') != 'false':
            self.addDirectoryItem(control.lang(30218), config.uri.get('base'), config.CONTINUEWATCHING, control.addonFolderIcon(control.lang(30218)), isFolder=True, **self.formatMenu())

        if control.setting('displayViewHistory') != 'false' and not self.myAccountShown():
            # without the My account menu, the history stays in the main menu
            self.addDirectoryItem(control.lang(30216), config.uri.get('base'), config.VIEWHISTORY, control.addonFolderIcon(control.lang(30216)), isFolder=True, **self.formatMenu())

        if control.setting('displayLiveTV') != 'false':
            self.addDirectoryItem(control.lang(30271), config.uri.get('base'), config.LIVETV, control.addonFolderIcon(control.lang(30271)), isFolder=True, **self.formatMenu())

        self.addDirectoryItem(control.lang(30257), config.uri.get('base'), config.TOPPICKS, control.addonFolderIcon(control.lang(30257)), isFolder=True, **self.formatMenu())

        if control.setting('displayWebsiteSections') == 'true':
            self.addDirectoryItem(control.lang(30201), config.uri.get('base'), config.CATEGORIES, control.addonFolderIcon(control.lang(30201)), isFolder=True, **self.formatMenu())
        else:
            self.showCategories()
            
        if control.setting('displayWebsiteSections') == 'true':
            # control.showNotification(control.lang(37020), control.lang(30008))
            collections = tfctv.getWebsiteCollections()
            for c in collections:
                self.addDirectoryItem(c['title'].title(), str(c['collectionId']), config.COLLECTIONCONTENT, control.addonFolderIcon(c['title'].title()), isFolder=True, **self.formatMenu())

        if self.myAccountShown():
            self.addDirectoryItem(control.lang(30202), config.uri.get('base'), config.MYACCOUNT, control.addonFolderIcon(control.lang(30202)), isFolder=True, **self.formatMenu())

        if control.setting('exportToLibrary') == 'true':
            self.addDirectoryItem(control.lang(36023), config.uri.get('base'), config.EXPORTEDSHOWS, control.addonFolderIcon(control.lang(36023)), isFolder=True, **self.formatMenu())
        
        if control.setting('displayTools') == 'true':
            self.addDirectoryItem(control.lang(30203), config.uri.get('base'), config.TOOLS, control.addonFolderIcon(control.lang(30203)))
            
        self.endDirectory()
        
        if not tfctv.isLoggedIn():
            control.infoDialog(control.lang(37017), control.lang(30002), time=8000)

    def showCollectionContent(self, url):
        logger.logInfo('called function')
        sections = tfctv.getCollectionContent(url)
        for s in sections:
            self.addDirectoryItem(s['name'].title(), str(s['id']), config.SECTIONCONTENT, control.addonFolderIcon(s['name'].title()), isFolder=True, **self.formatMenu())
        self.endDirectory()

    def showSeasons(self, showId):
        logger.logInfo('called function')
        seasons = tfctv.getSeasons(showId)
        for s in seasons:
            self.addDirectoryItem(s['name'].title(), str(s['showId']), config.SHOWEPISODES, control.addonFolderIcon(s['name'].title()), isFolder=True, query={'season': s['id']}, **self.formatMenu())
        self.endDirectory()

    def showMyList(self):
        logger.logInfo('called function')
        self.addDirectoryItem(control.lang(30213), '/', config.MYLISTSHOWLASTEPISODES, control.addonFolderIcon(control.lang(30213)), isFolder=True, **self.formatMenu())
        self.addDirectoryItem(control.lang(30214), '/', config.LISTCATEGORY, control.addonFolderIcon(control.lang(30214)), isFolder=True, **self.formatMenu())
        self.endDirectory()

    def showMyListShowLastEpisodes(self):   
        logger.logInfo('called function') 
        episodes = tfctv.getMylistShowLastEpisodes()
        for e in episodes:
            title = episodeTitle(e.get('title'), e.get('show'))
            self.addDirectoryItem(title, str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query={'title': title}, **self.formatVideoInfo(e, addToList=False))
        self.endDirectory(content='episodes', sortMethods=('unsorted', 'lastplayed'))

    def showMyListCategory(self, url):   
        logger.logInfo('called function')
        items = tfctv.getMyList()
        for item in items:
            image = item.get('logo') if control.setting('useShowLogo') == 'true' else item.get('image')
            self.addDirectoryItem(item.get('name'), str(item.get('id')), self.showMode(item), image, isFolder=True, query={'parentid' : str(item.get('parentid')), 'year' : item.get('year')}, **self.formatShowInfo(item, addToList=False))
        self.endDirectory(content='tvshows', sortMethods=('unsorted', 'title', 'year'))
            

    def showViewHistory(self, page=1):
        logger.logInfo('called function')
        itemsPerPage = int(control.setting('itemsPerPage'))
        episodes = tfctv.getViewHistory(page, itemsPerPage)
        self.addPlayableEpisodes(episodes, {'history': True, 'goToShow': True})
        if tfctv.hasNextViewHistoryPage(page, itemsPerPage):
            self.addDirectoryItem(control.lang(36008), config.uri.get('base'), config.VIEWHISTORY, '', page + 1)
        if len(episodes) > 0 and int(page) == 1:
            self.addDirectoryItem(control.lang(36026), config.uri.get('base'), config.CLEARHISTORY, control.addonFolderIcon(control.lang(36026)), **self.actionItem())
        self.endDirectory(content='episodes', sortMethods=('unsorted', 'lastplayed'))

    def showContinueWatching(self, page=1):
        logger.logInfo('called function')
        itemsPerPage = int(control.setting('itemsPerPage'))
        self.addPlayableEpisodes(tfctv.getContinueWatching(page, itemsPerPage), {'goToShow': True})
        if tfctv.hasNextContinueWatchingPage(page, itemsPerPage):
            self.addDirectoryItem(control.lang(36008), config.uri.get('base'), config.CONTINUEWATCHING, '', page + 1)
        self.endDirectory(content='episodes', sortMethods=('unsorted', 'lastplayed'))

    def clearViewHistory(self):
        logger.logInfo('called function')
        if control.confirm(control.lang(37060), control.lang(36026)):
            tfctv.clearViewHistory()
            control.showNotification(control.lang(37061), control.lang(30010))
            control.refresh()

    def removeFromViewHistory(self, episodeId, name=None):
        logger.logInfo('called function')
        tfctv.removeFromViewHistory(episodeId)
        control.showNotification(control.lang(37062) % (name or ''), control.lang(30010))
        control.refresh()

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
                self.addDirectoryItem(e.get('name'), str(e.get('id')), self.showMode(e), image, isFolder=True, **self.formatShowInfo(e))
            elif e['ltype'] in ('movie', 'episode', 'documentary', 'livestream') and e.get('isPlayable', True):
                title = episodeTitle(e.get('name'), e.get('show'))
                self.addDirectoryItem(title, str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query={'ltype': e['ltype'], 'title': title}, **self.formatVideoInfo(e))
        if len(content) == itemsPerPage:
            self.addDirectoryItem(control.lang(36008), section, config.SECTIONCONTENT, '', page + 1)
        self.endDirectory(content='videos', sortMethods=('unsorted', 'title', 'year'))

    def showTopPicks(self):
        logger.logInfo('called function')
        self.displayShows(tfctv.getTopPicks(), keepOrder=True)

    def showLiveTV(self):
        logger.logInfo('called function')
        self.displayShows(tfctv.getLiveTV(), keepOrder=True)

    def displayShows(self, shows, keepOrder=False):
        logger.logInfo('called function')
        sortedShowInfos = []
        for show in shows:
            image = show['logo'] if control.setting('useShowLogo') == 'true' else show['image']
            if show['ltype'] == 'show':
                sortedShowInfos.append((show.get('name').lower(), show.get('name'), str(show.get('id')), self.showMode(show), image, True, {'parentid' : str(show.get('parentid')), 'year' : show.get('year')}, self.formatShowInfo(show)))
            elif show['ltype'] in ('movie', 'episode', 'documentary', 'livestream'):
                title = show.get('name')
                sortedShowInfos.append((title.lower(), title, str(show.get('id')), config.PLAY, show.get('image'), False, {'ltype': show['ltype'], 'title': title}, self.formatVideoInfo(show)))
        
        if not keepOrder:  # the order of the website (top picks) or by title
            sortedShowInfos = sorted(sortedShowInfos, key = itemgetter(0))
        for info in sortedShowInfos:
            self.addDirectoryItem(info[1], info[2], info[3], info[4], isFolder=info[5], query=info[6], **info[7])
                
        self.endDirectory(content='tvshows', sortMethods=('unsorted', 'title', 'year'))
        
    def showEpisodes(self, showId, season='1', page=1):
        logger.logInfo('called function')
        itemsPerPage = int(control.setting('itemsPerPage'))
        (episodes, nextPage) = tfctv.getEpisodesPerPage(showId, season, page, itemsPerPage)
        episodes = sorted(episodes, key=lambda item: item['episodenumber'], reverse=True)
        for e in episodes:
            title = episodeTitle(e.get('title'), e.get('show'))
            self.addDirectoryItem(title, str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query={'ltype': e.get('ltype'), 'title': e.get('title')}, **self.formatVideoInfo(e, addToList=False))
        if len(episodes) == itemsPerPage or nextPage:
            self.addDirectoryItem(control.lang(36008), showId, config.SHOWEPISODES, '', page + 1, query={'season': season})
        self.endDirectory(content='episodes', sortMethods=('unsorted', 'episode', 'title', 'lastplayed'))

    def showSearchMenu(self, category):    
        logger.logInfo('called function')
        if category == 'movieshow':
            self.addDirectoryItem(control.lang(30208), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30208)), isFolder=True, query='category=%s&type=%s' % (category, 'title'), **self.formatMenu())
            self.addDirectoryItem(control.lang(30209), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30209)), isFolder=True, query='category=%s&type=%s' % (category, 'category'), **self.formatMenu())
            self.addDirectoryItem(control.lang(30210), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30210)), isFolder=True, query='category=%s&type=%s' % (category, 'cast'), **self.formatMenu())
            self.addDirectoryItem(control.lang(30212), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30212)), isFolder=True, query='category=%s&type=%s' % (category, 'year'), **self.formatMenu())
        elif category == 'episode':
            self.addDirectoryItem(control.lang(30208), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30208)), isFolder=True, query='category=%s&type=%s' % (category, 'title'), **self.formatMenu())
            self.addDirectoryItem(control.lang(30211), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30211)), isFolder=True, query='category=%s&type=%s' % (category, 'date'), **self.formatMenu())
        elif category == 'celebrity':
            control.showNotification(control.lang(37026), control.lang(30001))
        else:
            self.addDirectoryItem(control.lang(30256), config.uri.get('base'), config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30256)), isFolder=True, query='category=%s&type=%s' % ('movieshow', 'online'), **self.formatMenu())
            self.addDirectoryItem(control.lang(30205), config.uri.get('base'), config.SEARCHMENU, control.addonFolderIcon(control.lang(30205)), isFolder=True, query='category=%s' % 'movieshow', **self.formatMenu())
            self.addDirectoryItem(control.lang(30206), config.uri.get('base'), config.SEARCHMENU, control.addonFolderIcon(control.lang(30206)), isFolder=True, query='category=%s' % 'episode', **self.formatMenu())
            # self.addDirectoryItem(control.lang(30207), config.uri.get('base'), config.SEARCHMENU, control.addonFolderIcon(control.lang(30207)), isFolder=True, query='category=%s' % 'celebrity', **self.formatMenu())
        self.endDirectory()

    def executeSearch(self, category, type):
        logger.logInfo('called function')
        if category and type:
            result = tfctv.enterSearch(category, type)
            if len(result) > 0:
                if category == 'movieshow':
                    self.displayShows(result)
                    return True
                elif category == 'episode':
                    for e in sorted(result, key=lambda episode: episode['show']):
                        title = episodeTitle(e.get('title'), e.get('show'))
                        self.addDirectoryItem(title, str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query={'title' : title}, **self.formatVideoInfo(e, addToList=False))
        self.endDirectory()
            
    def showMyAccount(self):
        logger.logInfo('called function')
        tfctv.checkAccountChange(False)
        categories = [
            # { 'name' : control.lang(36004), 'url' : config.uri.get('profile'), 'mode' : config.MYINFO },
            # { 'name' : control.lang(36005), 'url' : config.uri.get('base'), 'mode' : config.MYSUBSCRIPTIONS },
            # { 'name' : control.lang(36006), 'url' : config.uri.get('base'), 'mode' : config.MYTRANSACTIONS }
        ]
        for c in categories:
            self.addDirectoryItem(c.get('name'), c.get('url'), c.get('mode'), control.addonFolderIcon(c.get('name')))
        if control.setting('displayViewHistory') != 'false':
            self.addDirectoryItem(control.lang(30216), config.uri.get('base'), config.VIEWHISTORY, control.addonFolderIcon(control.lang(30216)), isFolder=True, **self.formatMenu())
        self.addDirectoryItem(control.lang(36007), config.uri.get('base'), config.LOGOUT, control.addonFolderIcon('Logout'), **self.actionItem())    
        self.endDirectory()
    
    def showMyInfo(self):
        logger.logInfo('called function')
        loggedIn = tfctv.isLoggedIn()
        message = control.lang(37002)
        if loggedIn:
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
            except (Exception) as e:
                logger.logError('Error occurred while fetching user info: %s' % e)
                
        control.showMessage(message, control.lang(36001))
    
    def showMySubscription(self):
        logger.logInfo('called function')
        sub = tfctv.getUserSubscription()
        message = ''
        if sub:
            message += '%s' % (sub.get('details'))
        else:
            message = control.lang(37002)
        control.showMessage(message, control.lang(36002))
        
    def showMyTransactions(self):
        logger.logInfo('called function')
        transactions = tfctv.getUserTransactions()
        message = ''
        if len(transactions) > 0:
            for t in transactions:
                message += t + "\n"
        else:
            message = control.lang(37002)
        control.showMessage(message, control.lang(36003))

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
        self.addDirectoryItem(control.lang(36021), config.uri.get('base'), config.IMPORTALLDB, control.addonFolderIcon(control.lang(36021)), **self.actionItem())
        if tfctv.isLoggedIn():
            self.addDirectoryItem(control.lang(30258), config.uri.get('base'), config.SYNCWATCHLIST, control.addonFolderIcon(control.lang(30258)), **self.actionItem())
        self.addDirectoryItem(control.lang(30215), config.uri.get('base'), config.CHECKFORUPDATES, control.addonFolderIcon(control.lang(30215)), **self.actionItem())
        self.addDirectoryItem(control.lang(36009), config.uri.get('base'), config.RELOADCATALOG, control.addonFolderIcon(control.lang(36009)), **self.actionItem())
        self.addDirectoryItem(control.lang(36018), config.uri.get('base'), config.RESETCATALOG, control.addonFolderIcon(control.lang(36018)), **self.actionItem())
        self.addDirectoryItem(control.lang(36017), config.uri.get('base'), config.CHECKLIBRARYUPDATES, control.addonFolderIcon(control.lang(36017)), **self.actionItem())
        self.addDirectoryItem(control.lang(36010), config.uri.get('base'), config.CLEANCOOKIES, control.addonFolderIcon(control.lang(36010)), **self.actionItem())
        self.addDirectoryItem(control.lang(36022), config.uri.get('base'), config.FIRSTINSTALL, control.addonFolderIcon(control.lang(36022)), **self.actionItem())
        self.endDirectory()
            
    def firstInstall(self):
        logger.logInfo('called function')
        if control.setting('showWelcomeMessage') == 'true':
            control.showMessage(control.lang(37016), control.lang(37018))
            control.setSetting('showWelcomeMessage', 'false')
        
        self.addDirectoryItem(control.lang(36025), config.uri.get('base'), config.LOGINWITHTFC, control.addonIcon(), **self.actionItem())
        if control.setting('FBAppID') != '' or control.setting('FBClientToken') != '':
            self.addDirectoryItem(control.lang(36024), config.uri.get('base'), config.LOGINWITHFB, control.facebookIcon(), **self.actionItem())
        self.endDirectory()

    def loginWithTFC(self):
        logger.logInfo('called function')
        control.setSetting('loginType', 'TFC.tv')
        if control.setting('emailAddress') == '':
            if control.setting('showEnterCredentials') == 'true':
                self.enterCredentials()
                # self.addDirectoryItem(control.lang(36011), config.uri.get('base'), config.ENTERCREDENTIALS, control.addonFolderIcon(control.lang(36011)))
            # self.addDirectoryItem(control.lang(36012) % (' ' if control.setting('showPersonalize') == 'true' else 'x'), config.uri.get('base'), config.PERSONALIZESETTINGS, control.addonFolderIcon(control.lang(36012)))
            # self.addDirectoryItem(control.lang(36013) % (' ' if control.setting('showUpdateCatalog') == 'true' else 'x'), config.uri.get('base'), config.IMPORTALLDB, control.addonFolderIcon(control.lang(36013)))
            # self.addDirectoryItem(control.lang(36014) % (control.lang(36015) if control.setting('showEnterCredentials') == 'true' else control.lang(36016)), config.uri.get('base'), config.ENDSETUP, control.addonFolderIcon('Skip'))
            # self.endDirectory()
        #else:
        self.endSetup()
        
    def enterCredentials(self):
        logger.logInfo('called function')
        if tfctv.enterCredentials():
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
        
        
            
            

