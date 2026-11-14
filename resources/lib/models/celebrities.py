# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

from resources.lib.models import model
from resources.lib.libraries import control

logger = control.logger

class Actor(model.Model):
    
    _columns = ('ID', 'NAME', 'THUMBNAIL', 'FANART', 'BANNER', 'URL', 'DESCRIPTION', 'BIRTHDAY', 'BIRTHPLACE')
    _select = "SELECT ID, \
            NAME, \
            THUMBNAIL, \
            FANART, \
            BANNER, \
            URL, \
            DESCRIPTION, \
            BIRTHDAY, \
            BIRTHPLACE \
            FROM ACTOR"

    def _getStructure(self, data):
        logger.logDebug(len(data))
        logger.logDebug(data)
        if len(data) == 9:
            return {
                'id' : data[0],
                'name' : data[1],
                'thumbnail' : data[2],
                'fanart' : data[3],
                'banner' : data[4],
                'url' : data[5],
                'description' : data[6],
                'birthday' : data[7],
                'birthplace' : data[8]
                }
        return {}
         
    def _retrieveAll(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            NAME, \
            THUMBNAIL, \
            FANART, \
            BANNER, \
            URL, \
            DESCRIPTION, \
            BIRTHDAY, \
            BIRTHPLACE \
            FROM ACTOR"))
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
                self._updateRow(dbcur, 'ACTOR', data.get('id'), [
                    ('NAME', data.get('name')),
                    ('THUMBNAIL', data.get('logo')),
                    ('FANART', data.get('image')),
                    ('BANNER', data.get('banner')),
                    ('URL', data.get('url')),
                    ('DESCRIPTION', data.get('description')),
                    ('BIRTHDAY', data.get('birthday')),
                    ('BIRTHPLACE', data.get('birthplace'))
                ])
        self._dbcon.commit()
        return True

    def _replace(self, mixed):
        logger.logDebug(mixed)
        ids = [str(data['id']) for data in mixed if 'id' in data]
        if len(ids) > 0:
            self.checkIfTableExists()
            dbcur = self.getCursor()
            dbcur.execute('PRAGMA encoding="UTF-8";')
            self._deleteByIds(dbcur, 'ACTOR', ids)
            for data in mixed:
                self._exec(dbcur, "INSERT INTO ACTOR VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                    data.get('id'),
                    data.get('name'),
                    data.get('thumbnail'),
                    data.get('fanart'),
                    data.get('banner'),
                    data.get('url'),
                    data.get('description'),
                    data.get('birthday'),
                    data.get('birthplace')))
            self._dbcon.commit()
            return True
        return False

    def _remove(self, mixed):
        logger.logDebug(mixed)
        ids = [str(data['id']) for data in mixed if 'id' in data]
        if len(ids) > 0:
            dbcur = self.getCursor()
            try: 
                self._deleteByIds(dbcur, 'ACTOR', ids)
                self._dbcon.commit()
                return True
            except: pass
        return False

    def _drop(self):
        dbcur = self.getCursor()
        try: 
            dbcur.execute(logger.logDebug("DROP TABLE ACTOR"))
            self._dbcon.commit()
            return True
        except: 
            return False

    def checkIfTableExists(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("CREATE TABLE IF NOT EXISTS ACTOR (\
            ID TEXT PRIMARY KEY, \
            NAME TEXT, \
            THUMBNAIL TEXT, \
            FANART TEXT, \
            BANNER TEXT, \
            URL TEXT, \
            DESCRIPTION TEXT, \
            BIRTHDAY TEXT, \
            BIRTHPLACE TEXT)"))
        return self._dbcon.commit()
            
    def getStatistics(self):
        stats = {}
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT COUNT(*) FROM ACTOR"))
        stats['count'] = dbcur.fetchone()
        return stats