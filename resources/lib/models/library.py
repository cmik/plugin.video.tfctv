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

class Library(model.Model):
    
    _columns = ('ID', 'NAME', 'PARENTID', 'YEAR', 'COMPARE', 'LASTCHECK')
    _select = "SELECT ID, \
            NAME, \
            PARENTID, \
            YEAR, \
            COMPARE, \
            LASTCHECK \
            FROM LIBRARY_SHOW"

    def _getStructure(self, data):
        logger.logDebug(len(data))
        logger.logDebug(data)
        if len(data) == 6:
            try:
                lastCheck = time.strptime(data[5], '%Y-%m-%d %H:%M:%S')
            except TypeError:
                lastCheck = datetime.datetime(1900, 1, 1)
            return {
                'id' : data[0], 
                'name' : data[1], 
                'parentid' : data[2],
                'year' : data[3],
                'compare' : data[4],
                'lastCheck' : lastCheck,
                'inLibrary' : True
                }
        return {}
      
    def _retrieveAll(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            NAME, \
            PARENTID, \
            YEAR, \
            COMPARE, \
            LASTCHECK \
            FROM LIBRARY_SHOW"))
        return logger.logDebug(dbcur.fetchall())
      
    def _retrieve(self, mixed, key):
        return logger.logDebug(self._selectBy(self._select, key, mixed))

    def _save(self, mixed):
        return self._replace(mixed)

    def _replace(self, mixed):
        ids = [str(data['id']) for data in mixed if 'id' in data]
        if len(ids) > 0:
            self.checkIfTableExists()
            dbcur = self.getCursor()
            dbcur.execute('PRAGMA encoding="UTF-8";')
            self._deleteByIds(dbcur, 'LIBRARY_SHOW', ids)
            for data in mixed:
                dbcur.execute(logger.logDebug("INSERT INTO LIBRARY_SHOW VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" % (
                    data.get('id'), 
                    data.get('name').replace('\'', '\'\''), 
                    data.get('parentid'),
                    data.get('year'), 
                    data.get('compare', '0'), 
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'))))
            self._dbcon.commit()
            return True
        return False

    def _remove(self, mixed):
        logger.logDebug(mixed)
        ids = [str(data['id']) for data in mixed if 'id' in data]
        if len(ids) > 0:
            dbcur = self.getCursor()
            try: 
                self._deleteByIds(dbcur, 'LIBRARY_SHOW', ids)
                self._dbcon.commit()
                return True
            except: 
                pass
        return False

    def _drop(self):
        dbcur = self.getCursor()
        try: 
            dbcur.execute(logger.logDebug("DROP TABLE LIBRARY_SHOW"))
            self._dbcon.commit()
            return Trues
        except: 
            return False

    def checkIfTableExists(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("CREATE TABLE IF NOT EXISTS LIBRARY_SHOW (\
            ID TEXT PRIMARY KEY, \
            NAME TEXT, \
            PARENTID TEXT, \
            YEAR TEXT, \
            COMPARE TEXT, \
            LASTCHECK TEXT)"))
        self._dbcon.commit()
        return True

    def getStatistics(self):
        stats = {}
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT COUNT(*) FROM LIBRARY_SHOW"))
        stats['count'] = dbcur.fetchone()
        return stats

