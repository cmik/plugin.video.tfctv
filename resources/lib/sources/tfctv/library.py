# -*- coding: utf-8 -*-

"""
Kodi library management
"""

import os
import datetime
from resources import config
from resources.lib.libraries import control
from resources.lib.models import library
from .catalog import getEpisodesPerPage, episodeDB, showDB

logger = control.logger
libraryDB = library.Library(control.libraryFile)

def showExportedShowsToLibrary():
    """Show exported shows"""
    data = []
    temp = {}
    exported = libraryDB.getAll()
    for d in exported:
        if 'id' in d:
            temp[d.get('id')] = d
    if len(temp) > 0:
        shows = showDB.get(list(temp.keys()))
        for s in shows:
            temp[s.get('id')].update(s)
            data.append(temp.get(s.get('id')))
    return data

def removeFromLibrary(id, name):
    """Remove show from library"""
    data = libraryDB.get(id)
    if len(data) > 0:
        if logger.logInfo(libraryDB.delete(data[0])):
            path = os.path.join(control.showsLibPath, name, '')
            logger.logInfo(path)
            if logger.logInfo(control.pathExists(path)):
                if control.confirm('%s\n%s' % (control.lang(37041), control.lang(37042)), title=name) is False:
                    control.deleteFolder(path, True)
            control.showNotification(control.lang(37043) % name, control.lang(30010))
        else:
            control.showNotification(control.lang(37044), control.lang(30004))
    else:
        control.showNotification(control.lang(37045), control.lang(30001))

def addToLibrary(id, name, parentId=-1, year='', updateOnly=False):
    """Add show to Kodi library"""
    logger.logInfo('called function with param (%s, %s, %s, %s)' % (id, name, parentId, year))
    from resources.lib.indexers import navigator
    status = True
    updated = False
    nbUpdated = 0
    nbEpisodes = int(control.setting('exportLastNbEpisodes'))
    (episodes, n) = getEpisodesPerPage(id, page=1, itemsPerPage=nbEpisodes)
    
    if len(episodes) > 0:
    
        path = os.path.join(control.showsLibPath, name)
        control.makePath(path)
        
        # Show NFO file
        try:
            e = episodes[0]
            show = e.get('showObj')
            res = libraryDB.get(show.get('id'))
            lib = res[0] if len(res) == 1 else {}
            control.writeFile(logger.logNotice(str(os.path.join(path, 'tvshow.nfo'))), str(generateShowNFO(show, path)))
        except Exception as err:
            logger.logError(err)
            status = False
        
        if status is True:
            
            mostRecentEpisodeNumber = lastEpisodeNumber = int(lib.get('compare', '0'))
            lastCheck = lib.get('lastCheck', datetime.datetime(1900, 1, 1))
            logger.logNotice('last check date : %s' % lastCheck.strftime('%Y-%m-%d %H:%M:%S'))
            for e in sorted(episodes, key=lambda item: item['episodenumber'], reverse=False):
                filePath = os.path.join(path, '%s.strm' % e.get('title'))
                logger.logNotice('Last episode number : %s' % e.get('compare'))
                episodeNumber = int(e.get('episodenumber', '0'))
                if lastEpisodeNumber < episodeNumber:
                    updated = True
                    nbUpdated += 1
                    if mostRecentEpisodeNumber < episodeNumber:
                        mostRecentEpisodeNumber = episodeNumber
                    
                if not updateOnly or updated:
                    try:
                        # Episode STRM / NFO files
                        control.writeFile(logger.logNotice(os.path.join(path, '%s.nfo' % e.get('title'))), generateEpisodeNFO(e, path, filePath))
                        control.writeFile(logger.logNotice(filePath), navigator.navigator().generateActionUrl(e.get('id'), config.PLAY, '%s - %s' % (e.get('show'), e.get('title')), e.get('image')))
                    except Exception as err:
                        logger.logError(err)
                        status = False
                        break
    else:
        status = False
            
    if status is True:
        if not updateOnly:
            control.showNotification(control.lang(37034) % name, control.lang(30010))
        libraryDB.set({
            'id': show.get('id'),
            'name': show.get('name'),
            'parentid': show.get('parentid'),
            'year': show.get('year'),
            'compare': mostRecentEpisodeNumber
            })
    else:
        if not updateOnly:
            control.showNotification(control.lang(37033), control.lang(30004))
    return {'status': status, 'updated': updated, 'nb': nbUpdated}

def generateShowNFO(info, path):
    """Generate show NFO file"""
    logger.logInfo('called function')
    nfoString = ''
    nfoString += '<title>%s</title>' % info.get('name')
    nfoString += '<sorttitle>%s</sorttitle>' % info.get('name')
    nfoString += '<episode>%s</episode>' % info.get('nbEpisodes')
    nfoString += '<plot>%s</plot>' % info.get('description')
    nfoString += '<aired>%s</aired>' % info.get('dateaired')
    nfoString += '<year>%s</year>' % info.get('year')
    nfoString += '<thumb aspect="poster">%s</thumb>' % info.get('image')
    nfoString += '<fanart url=""><thumb dim="1280x720" colors="" preview="%s">%s</thumb></fanart>' % (info.get('fanart'), info.get('fanart'))
    nfoString += '<genre>%s</genre>' % info.get('parentname')
    nfoString += '<path>%s</path>' % path
    nfoString += '<filenameandpath></filenameandpath>'
    nfoString += '<basepath>%s</basepath>' % path
    for c in info.get('casts', []):
        nfoString += '<actor><name>%s</name><order>%d</order><thumb>%s</thumb></actor>' % (c.get('name'), c.get('order'), c.get('thumbnail'))
    
    return u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?> \
<!-- created on %s - by TFC.tv addon --> \
<tvshow> \
    %s \
</tvshow>' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nfoString)
    
def generateEpisodeNFO(info, path, filePath):
    """Generate episode NFO file"""
    logger.logInfo('called function')
    nfoString = ''
    nfoString += '<title>%s</title>' % info.get('title')
    nfoString += '<showtitle>%s</showtitle>' % info.get('show')
    nfoString += '<sorttitle>%s</sorttitle>' % info.get('dateaired')
    nfoString += '<episode>%s</episode>' % info.get('episodenumber')
    nfoString += '<plot>%s</plot>' % info.get('description')
    nfoString += '<aired>%s</aired>' % info.get('dateaired')
    nfoString += '<year>%s</year>' % info.get('year')
    nfoString += '<thumb>%s</thumb>' % info.get('image')
    nfoString += '<art><banner>%s</banner><fanart>%s</fanart></art>' % (info.get('fanart'), info.get('fanart'))
    nfoString += '<path>%s</path>' % path
    nfoString += '<filenameandpath>%s</filenameandpath>' % filePath
    nfoString += '<basepath>%s</basepath>' % filePath
    nfoString += '<studio>ABS-CBN</studio>'
    
    return u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?> \
<!-- created on %s - by TFC.tv addon --> \
<episodedetails> \
    %s \
</episodedetails>' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nfoString)

def checkLibraryUpdates(quiet=False):
    """Check for library updates"""
    logger.logInfo('called function')
    items = libraryDB.getAll()
    for show in items:
        logger.logNotice('check for update for show %s' % show.get('name'))
        result = addToLibrary(show.get('id'), show.get('name'), show.get('parentid'), show.get('year'), updateOnly=True)
        if result.get('updated', False):
            logger.logNotice('Updated %s episodes' % str(result.get('nb')))
            if not quiet:
                control.showNotification(control.lang(37037) % (str(result.get('nb')), show.get('name')), control.lang(30011))
        else:
            logger.logNotice('No updates for show %s' % show.get('name'))
    return True
