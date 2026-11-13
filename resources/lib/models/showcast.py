# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

from resources.lib.models import model
from resources.lib.libraries import control

logger = control.logger

class ShowCast(model.Model):
    
    idFormat = '%s-%s'

    _columns = ('ID', 'SHOWID', 'ACTORID', 'NAME', 'ROLE', 'THUMBNAIL', 'ORDR', 'URL')
    _select = "SELECT ID, \
            SHOWID, \
            ACTORID, \
            NAME, \
            ROLE, \
            THUMBNAIL, \
            ORDR, \
            URL \
            FROM SHOW_CAST"

    def _getStructure(self, data):
        logger.logDebug(len(data))
        logger.logDebug(data)
        if len(data) == 8:
            return {
                'id' : data[0],
                'showid' : data[1],
                'actorid' : data[2],
                'name' : data[3],
                'role' : data[4],
                'thumbnail' : data[5],
                'order' : data[6],
                'castUrl' : data[7]
                }
        return {}
    
    def _search(self, search, limit):
        return logger.logDebug(self._selectLike(self._select, search, limit))

    def _retrieveAll(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            SHOWID, \
            ACTORID, \
            NAME, \
            ROLE, \
            THUMBNAIL, \
            ORDR, \
            URL \
            FROM SHOW_CAST"))
        return logger.logDebug(dbcur.fetchall())
         
    def _retrieve(self, mixed, key):
        return logger.logDebug(self._selectBy(self._select, key, mixed))

    def _save(self, mixed):
        logger.logDebug(mixed)
        self.checkIfTableExists()
        for data in mixed:
            if 'name' in data and data.get('name', '') == '':
                logger.logError("Missing required field 'name'")
                continue
            if 'id' in data or ('showid' in data and 'castid' in data):
                dbcur = self.getCursor()
                dbcur.execute('PRAGMA encoding="UTF-8";')
                self._updateRow(dbcur, 'SHOW_CAST', data.get('id', self.idFormat % (data.get('showid'), data.get('castid'))), [
                    ('SHOWID', data.get('showid')),
                    ('ACTORID', data.get('castid')),
                    ('NAME', data.get('name')),
                    ('ROLE', data.get('role')),
                    ('THUMBNAIL', data.get('thumbnail')),
                    ('ORDR', data.get('order')),
                    ('URL', data.get('url'))
                ])
        self._dbcon.commit()
        return True

    def _replace(self, mixed):
        logger.logDebug(mixed)
        ids = [str(data.get('id', self.idFormat % (data.get('showid'), data.get('castid')))) for data in mixed if 'id' in data or ('showid' in data and 'castid' in data)]
        if len(ids) > 0:
            self.checkIfTableExists()
            dbcur = self.getCursor()
            dbcur.execute('PRAGMA encoding="UTF-8";')
            self._deleteByIds(dbcur, 'SHOW_CAST', ids)
            for data in mixed:
                self._exec(dbcur, "INSERT INTO SHOW_CAST VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                    data.get('id', self.idFormat % (data.get('showid'), data.get('castid'))),
                    data.get('showid'),
                    data.get('castid'),
                    data.get('name'),
                    data.get('role'),
                    data.get('thumbnail'),
                    int(data.get('order') or 0),
                    data.get('url')))
            self._dbcon.commit()
            return True
        return False

    def _remove(self, mixed):
        logger.logDebug(mixed)
        ids = [str(data.get('id', self.idFormat % (data.get('showid'), data.get('castid')))) for data in mixed if 'id' in data or ('showid' in data and 'castid' in data)]
        if len(ids) > 0:
            dbcur = self.getCursor()
            try: 
                self._deleteByIds(dbcur, 'SHOW_CAST', ids)
                self._dbcon.commit()
                return True
            except: pass
        return False

    def _drop(self):
        dbcur = self.getCursor()
        try: 
            dbcur.execute(logger.logDebug("DROP TABLE SHOW_CAST"))
            self._dbcon.commit()
            return True
        except: 
            return False

    def getByShow(self, mixed, limit=100):
        return self.get(mixed, 'SHOWID')

    def searchByActorName(self, name, limit=100):
        return self.search({'NAME' : name})

    def checkIfTableExists(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("CREATE TABLE IF NOT EXISTS SHOW_CAST (\
            ID TEXT PRIMARY KEY, \
            SHOWID TEXT, \
            ACTORID TEXT, \
            NAME TEXT, \
            ROLE TEXT, \
            THUMBNAIL TEXT, \
            ORDR INTEGER, \
            URL TEXT)"))
        return self._dbcon.commit()
            
    def getStatistics(self):
        stats = {}
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT COUNT(*) FROM SHOW_CAST"))
        stats['count'] = dbcur.fetchone()
        return stats