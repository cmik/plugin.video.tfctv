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
        dbcur = self.getCursor()
        where = ["%s LIKE '%%%s%%'" % (str(k), str(v)) for k,v in search.items()]
        first = 'LIMIT %d' % int(limit) if limit != False else ''
        dbcur.execute(logger.logInfo("SELECT ID, \
            EPISODEID, \
            SHOWID, \
            DATEVIEWED \
            FROM VIEWEDHISTORY \
            WHERE %s %s" % (' AND '.join(where), first)))
        return logger.logDebug(dbcur.fetchall())

    def _retrieveAll(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            EPISODEID, \
            SHOWID, \
            DATEVIEWED \
            FROM VIEWEDHISTORY"))
        return logger.logDebug(dbcur.fetchall())
         
    def _retrieve(self, mixed, key):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            EPISODEID, \
            SHOWID, \
            DATEVIEWED \
            FROM VIEWEDHISTORY \
            WHERE %s IN ('%s')" % (key, "','".join(str(v) for v in mixed))))
        return logger.logDebug(dbcur.fetchall())

        
    def _save(self, mixed):
        logger.logDebug(mixed)
        self.checkIfTableExists()
        for data in mixed:
            if 'id' in data:
                dbcur = self.getCursor()
                dbcur.execute('PRAGMA encoding="UTF-8";')
                for k, e in data.items():
                    query = "UPDATE VIEWEDHISTORY SET "
                    query += "EPISODEID = '%s', " % data.get('episode').replace('\'', '\'\'') if data.get('episode', False) else "EPISODEID = EPISODEID, "
                    query += "SHOWID = '%s', " % data.get('show') if data.get('show', False) else "SHOWID = SHOWID, "
                    query += "DATEVIEWED = '%s' " % data.get('date') if data.get('date', False) else "DATEVIEWED = DATEVIEWED "
                    query += "WHERE ID = '%s'" % data.get('id')
                    dbcur.execute(logger.logDebug(query))
        self._dbcon.commit()
        return True
        
    def _replace(self, mixed):
        ids = [str(data['id']) for data in mixed if 'id' in data]
        if len(ids) > 0:
            self.checkIfTableExists()
            dbcur = self.getCursor()
            dbcur.execute('PRAGMA encoding="UTF-8";')
            dbcur.execute(logger.logDebug("DELETE FROM VIEWEDHISTORY WHERE ID in ('%s')" % "','".join(ids)))
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
                dbcur.execute(logger.logDebug("DELETE FROM VIEWEDHISTORY WHERE ID in ('%s')" % "','".join(ids)))
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
            DATEVIEWED TEXT \)"))
        self._dbcon.commit()
        return True
    

    def getStatistics(self):
        stats = {}
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT COUNT(*) FROM VIEWEDHISTORY"))
        stats['count'] = dbcur.fetchone()
        return stats

