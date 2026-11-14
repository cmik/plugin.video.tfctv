# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

from resources.lib.models import model
from resources.lib.models import userdata
from resources.lib.libraries import control
from datetime import datetime
import time

logger = control.logger

class Episode(model.Model):
    
    _columns = ('ID', 'TITLE', 'SHOWID', 'SHOWNAME', 'THUMBNAIL', 'FANART', 'EPISODENUMBER', 'URL', 'DESCRIPTION', 'SHORTDESCRIPTION', 'DATEAIRED', 'YEAR', 'PARENTALADVISORY', 'TYPE', 'DURATION', 'VIEWS', 'RATING', 'VOTES')
    _select = "SELECT ID, \
            TITLE, \
            SHOWID, \
            SHOWNAME, \
            THUMBNAIL, \
            FANART, \
            EPISODENUMBER, \
            URL, \
            DESCRIPTION, \
            SHORTDESCRIPTION, \
            DATEAIRED, \
            YEAR, \
            PARENTALADVISORY, \
            TYPE, \
            DURATION, \
            VIEWS, \
            RATING, \
            VOTES \
            FROM EPISODE"

    def _getStructure(self, data):
        logger.logDebug(len(data))
        logger.logDebug(data)
        if len(data) == 18:
            """try:
                dateaired = datetime.strptime(data[10], '%Y-%m-%d')
            except TypeError:
                dateaired = datetime(*(time.strptime(data[10], '%Y-%m-%d')[0:6]))"""
            return {
                'id' : data[0], 
                'title' : data[1], 
                'parentid' : data[2],
                'parentname' : data[3],
                'show' : data[3], 
                'image' : data[4], 
                'fanart' : data[5],
                'episodenumber' : int(data[6]),
                'url' : data[7], 
                'description' : data[8],
                'shortdescription' : data[9],
                'dateaired' : '',# dateaired.strftime('%b %d, %Y'),
                'date' : data[10],
                'year' : data[11],
                'parentalAdvisory' : data[12],
                'ltype' : data[13],
                'duration' : int(data[14]),
                'views' : int(data[15]),
                'rating' : int(data[16]),
                'votes' : int(data[17]),
                'type' : 'episode'
                }
        return {}
    
    def _applyUserData(self, items):
        """The counters come from the user data database"""
        if not items:
            return items
        stats = self.getUserData().getStats(userdata.EPISODE, [item['id'] for item in items if item.get('id')])
        for item in items:
            item['views'], item['rating'], item['votes'] = stats.get(item.get('id'), (0, 0, 0))
        return items

    def _search(self, search, limit):
        return logger.logDebug(self._selectLike(self._select, search, limit))

    def _retrieveAll(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            TITLE, \
            SHOWID, \
            SHOWNAME, \
            THUMBNAIL, \
            FANART, \
            EPISODENUMBER, \
            URL, \
            DESCRIPTION, \
            SHORTDESCRIPTION, \
            DATEAIRED, \
            YEAR, \
            PARENTALADVISORY, \
            TYPE, \
            DURATION, \
            VIEWS, \
            RATING, \
            VOTES \
            FROM EPISODE"))
        return logger.logDebug(dbcur.fetchall())
         
    def _retrieve(self, mixed, key):
        return logger.logDebug(self._selectBy(self._select, key, mixed))

    def _save(self, mixed):
        logger.logDebug(mixed)
        self.checkIfTableExists()
        for data in mixed:
            if not isinstance(data, dict):
                logger.logDebug("Skipping invalid data: not a dictionary")
                continue
            if not data:
                logger.logDebug("Skipping empty data")
                continue

            # Validate integer fields
            int_fields = ['duration', 'views', 'rating', 'votes']
            for field in int_fields:
                if field in data and data[field] is not None:
                    try:
                        data[field] = int(data[field])
                    except (ValueError, TypeError):
                        logger.logError("Invalid integer value for field '%s', setting to 0" % field)
                        data[field] = 0
            if 'id' in data:
                dbcur = self.getCursor()
                dbcur.execute('PRAGMA encoding="UTF-8";')
                self._updateRow(dbcur, 'EPISODE', data.get('id'), [
                    ('TITLE', data.get('title', data.get('name'))),
                    ('SHOWID', data.get('parentid')),
                    ('SHOWNAME', data.get('show')),
                    ('THUMBNAIL', data.get('image')),
                    ('FANART', data.get('fanart')),
                    ('EPISODENUMBER', data.get('episodenumber')),
                    ('URL', data.get('url')),
                    ('DESCRIPTION', data.get('description')),
                    ('SHORTDESCRIPTION', data.get('shortdescription')),
                    ('DATEAIRED', data.get('date')),
                    ('YEAR', data.get('year')),
                    ('PARENTALADVISORY', data.get('parentalAdvisory')),
                    ('TYPE', data.get('ltype')),
                    ('DURATION', data.get('duration'))
                ])
                self.getUserData().setStats(userdata.EPISODE, data.get('id'), data.get('views'), data.get('rating'), data.get('votes'))
        self._dbcon.commit()
        return True

    def _replace(self, mixed):
        ids = [str(data['id']) for data in mixed if 'id' in data]
        if len(ids) > 0:
            self.checkIfTableExists()
            dbcur = self.getCursor()
            dbcur.execute('PRAGMA encoding="UTF-8";')
            self._deleteByIds(dbcur, 'EPISODE', ids)
            for data in mixed:
                self._exec(dbcur, "INSERT INTO EPISODE VALUES (%s)" % ','.join('?' * 18), (
                    data.get('id'),
                    data.get('title'),
                    data.get('parentid'),
                    data.get('show'),
                    data.get('image'),
                    data.get('fanart'),
                    data.get('episodenumber'),
                    data.get('url'),
                    data.get('description'),
                    data.get('shortdescription'),
                    data.get('date'),
                    data.get('year'),
                    data.get('parentalAdvisory'),
                    data.get('ltype'),
                    int(data.get('duration', 0)),
                    0,
                    0,
                    0))  # views, rating, votes: kept in the user data database
            self._dbcon.commit()
            return True
        return False

    def _remove(self, mixed):
        logger.logDebug(mixed)
        ids = [str(data['id']) for data in mixed if 'id' in data]
        if len(ids) > 0:
            dbcur = self.getCursor()
            try: 
                self._deleteByIds(dbcur, 'EPISODE', ids)
                self._dbcon.commit()
                return True
            except: pass
        return False

    def _drop(self):
        dbcur = self.getCursor()
        try: 
            dbcur.execute(logger.logDebug("DROP TABLE EPISODE"))
            self._dbcon.commit()
            return True
        except: 
            return False

    def searchByTitle(self, title, limit=100):
        return self.search({'TITLE' : title}, limit)

    def searchByDate(self, date, limit=100):
        return self.search({'DATEAIRED' : date}, limit)

    def checkIfTableExists(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("CREATE TABLE IF NOT EXISTS EPISODE (\
            ID TEXT PRIMARY KEY, \
            TITLE TEXT, \
            SHOWID TEXT, \
            SHOWNAME TEXT, \
            THUMBNAIL TEXT, \
            FANART TEXT, \
            EPISODENUMBER TEXT, \
            URL TEXT, \
            DESCRIPTION TEXT, \
            SHORTDESCRIPTION TEXT, \
            DATEAIRED TEXT, \
            YEAR TEXT, \
            PARENTALADVISORY TEXT, \
            TYPE TEXT, \
            DURATION INTEGER NOT NULL DEFAULT 0, \
            VIEWS INTEGER NOT NULL DEFAULT 0, \
            RATING INTEGER NOT NULL DEFAULT 0, \
            VOTES INTEGER NOT NULL DEFAULT 0)"))
        self._dbcon.commit()
        return True
    

    def getStatistics(self):
        stats = {}
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT COUNT(*) FROM EPISODE"))
        stats['count'] = dbcur.fetchone()
        return stats

