# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

from resources.lib.models import model
from resources.lib.libraries import control
from datetime import datetime
import time

logger = control.logger

class ViewedHistory(model.Model):
    
    _columns = ('ID', 'EPISODEID', 'SHOWID', 'DATEVIEWED')
    _select = "SELECT ID, \
            EPISODEID, \
            SHOWID, \
            DATEVIEWED \
            FROM VIEWEDHISTORY"

    def _getStructure(self, data):
        logger.logDebug(len(data))
        logger.logDebug(data)
        if len(data) == 18:
            """try:
                dateaired = datetime.strptime(data[3], '%Y-%m-%d %H:%M:%S')
            except TypeError:
                dateaired = datetime(*(time.strptime(data[3], '%Y-%m-%d')[0:6]))"""
            return {
                'id' : data[0], 
                'episode' : data[1], 
                'show' : data[2], 
                'date' : data[3]
                }
        return {}
    
    def _search(self, search, limit):
        return logger.logDebug(self._selectLike(self._select, search, limit))

    def _retrieveAll(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            EPISODEID, \
            SHOWID, \
            DATEVIEWED \
            FROM VIEWEDHISTORY"))
        return logger.logDebug(dbcur.fetchall())
         
    def _retrieve(self, mixed, key):
        return logger.logDebug(self._selectBy(self._select, key, mixed))

    def _save(self, mixed):
        logger.logDebug(mixed)
        self.checkIfTableExists()
        for data in mixed:
            if 'id' in data:
                dbcur = self.getCursor()
                dbcur.execute('PRAGMA encoding="UTF-8";')
                self._updateRow(dbcur, 'VIEWEDHISTORY', data.get('id'), [
                    ('EPISODEID', data.get('episode')),
                    ('SHOWID', data.get('show')),
                    ('DATEVIEWED', data.get('date'))
                ])
        self._dbcon.commit()
        return True

    def _replace(self, mixed):
        ids = [str(data['id']) for data in mixed if 'id' in data]
        if len(ids) > 0:
            self.checkIfTableExists()
            dbcur = self.getCursor()
            dbcur.execute('PRAGMA encoding="UTF-8";')
            self._deleteByIds(dbcur, 'VIEWEDHISTORY', ids)
            for data in mixed:
                dbcur.execute(logger.logDebug("INSERT INTO VIEWEDHISTORY VALUES ('%s', '%s', '%s', '%s')" % (
                    datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"), 
                    data.get('episode'),    
                    data.get('show'),  
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))))
            self._dbcon.commit()
            return True
        return False

    def _remove(self, mixed):
        logger.logDebug(mixed)
        ids = [str(data['id']) for data in mixed if 'id' in data]
        if len(ids) > 0:
            dbcur = self.getCursor()
            try: 
                self._deleteByIds(dbcur, 'VIEWEDHISTORY', ids)
                self._dbcon.commit()
                return True
            except: pass
        return False

    def _drop(self):
        dbcur = self.getCursor()
        try: 
            dbcur.execute(logger.logDebug("DROP TABLE VIEWEDHISTORY"))
            self._dbcon.commit()
            return True
        except: 
            return False

    def searchByEpisode(self, title, limit=100):
        return self.search({'EPISODEID' : title}, limit)
    
    def searchByShow(self, title, limit=100):
        return self.search({'SHOWID' : title}, limit)

    def searchByDate(self, date, limit=100):
        return self.search({'DATEVIEWED' : date}, limit)

    def checkIfTableExists(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("CREATE TABLE IF NOT EXISTS VIEWEDHISTORY (\
            ID TEXT PRIMARY KEY, \
            EPISODEID TEXT, \
            SHOWID TEXT, \
            DATEVIEWED TEXT)"))
        self._dbcon.commit()
        return True
    

    def getStatistics(self):
        stats = {}
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT COUNT(*) FROM VIEWEDHISTORY"))
        stats['count'] = dbcur.fetchone()
        return stats

