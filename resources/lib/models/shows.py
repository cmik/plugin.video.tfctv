# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

from resources.lib.models import model
from resources.lib.models import userdata
from resources.lib.libraries import control

logger = control.logger

class Show(model.Model):
    
    _columns = ('ID', 'TITLE', 'PARENTID', 'PARENTNAME', 'THUMBNAIL', 'IMAGE', 'FANART', 'BANNER', 'URL', 'DESCRIPTION', 'SHORTDESCRIPTION', 'YEAR', 'TYPE', 'DURATION', 'VIEWS', 'RATING', 'VOTES', 'MYLIST')
    _select = "SELECT ID, \
            TITLE, \
            PARENTID, \
            PARENTNAME, \
            THUMBNAIL, \
            IMAGE, \
            FANART, \
            BANNER, \
            URL, \
            DESCRIPTION, \
            SHORTDESCRIPTION, \
            YEAR, \
            TYPE, \
            DURATION, \
            VIEWS, \
            RATING, \
            VOTES, \
            MYLIST \
            FROM SHOW"

    def _getStructure(self, data):
        logger.logDebug(len(data))
        logger.logDebug(data)
        if len(data) == 18:
            return {
                'id' : data[0],
                'name' : data[1],
                'parentid' : data[2],
                'parentname' : data[3],
                'logo' : data[4],
                'image' : data[5],
                'fanart' : data[6],
                'banner' : data[7],
                'url' : data[8],
                'description' : data[9],
                'shortdescription' : data[10],
                'year' : data[11],
                'ltype' : data[12],
                'duration' : int(data[13]),
                'views' : int(data[14]),
                'rating' : int(data[15]),
                'votes' : int(data[16]),
                'mylist' : data[17],
                'type' : 'show'
                }
        return {}
    
    def _applyUserData(self, items):
        """My List and the counters come from the user data database"""
        if not items:
            return items
        ids = [item['id'] for item in items if item.get('id')]
        ud = self.getUserData()
        stats = ud.getStats(userdata.SHOW, ids)
        myList = set(ud.getMyListIds(ids))
        for item in items:
            item['views'], item['rating'], item['votes'] = stats.get(item.get('id'), (0, 0, 0))
            item['mylist'] = 'true' if item.get('id') in myList else 'false'
        return items

    def _saveUserData(self, data):
        """Store the user data fields (mylist, views, rating, votes) of an item"""
        ud = self.getUserData()
        if data.get('mylist') in ('true', 'false'):
            if data['mylist'] == 'true':
                title = data.get('name') or ''
                if not title:
                    found = self.get(data['id'])
                    title = found[0].get('name', '') if found else ''
                ud.addToMyList(data['id'], title)
            else:
                ud.removeFromMyList(data['id'])
        ud.setStats(userdata.SHOW, data['id'], data.get('views'), data.get('rating'), data.get('votes'))

    def _search(self, search, limit):
        return logger.logDebug(self._selectLike(self._select, search, limit))

    def _retrieveAll(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            TITLE, \
            PARENTID, \
            PARENTNAME, \
            THUMBNAIL, \
            IMAGE, \
            FANART, \
            BANNER, \
            URL, \
            DESCRIPTION, \
            SHORTDESCRIPTION, \
            YEAR, \
            TYPE, \
            DURATION, \
            VIEWS, \
            RATING, \
            VOTES, \
            MYLIST \
            FROM SHOW"))
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
            if 'id' in data:
                dbcur = self.getCursor()
                dbcur.execute('PRAGMA encoding="UTF-8";')
                self._updateRow(dbcur, 'SHOW', data.get('id'), [
                    ('TITLE', data.get('name')),
                    ('PARENTID', data.get('parentid')),
                    ('PARENTNAME', data.get('parentname')),
                    ('THUMBNAIL', data.get('logo')),
                    ('IMAGE', data.get('image')),
                    ('FANART', data.get('fanart')),
                    ('BANNER', data.get('banner')),
                    ('URL', data.get('url')),
                    ('DESCRIPTION', data.get('description')),
                    ('SHORTDESCRIPTION', data.get('shortdescription')),
                    ('YEAR', data.get('year')),
                    ('TYPE', data.get('ltype')),
                    ('DURATION', data.get('duration'))
                ])
                self._saveUserData(data)
        self._dbcon.commit()
        return True

    def _replace(self, mixed):
        logger.logDebug(mixed)
        ids = [str(data['id']) for data in mixed if 'id' in data]
        if len(ids) > 0:
            self.checkIfTableExists()
            dbcur = self.getCursor()
            dbcur.execute('PRAGMA encoding="UTF-8";')
            self._deleteByIds(dbcur, 'SHOW', ids)
            for data in mixed:
                self._exec(dbcur, "INSERT INTO SHOW VALUES (%s)" % ','.join('?' * 18), (
                    data.get('id'),
                    data.get('name'),
                    data.get('parentid'),
                    data.get('parentname'),
                    data.get('logo'),
                    data.get('image'),
                    data.get('fanart'),
                    data.get('banner'),
                    data.get('url'),
                    data.get('description'),
                    data.get('shortdescription'),
                    data.get('year'),
                    data.get('ltype'),
                    int(data.get('duration', 0)),
                    0,
                    0,
                    0,
                    'false'))  # views, rating, votes, mylist: kept in the user data database
            self._dbcon.commit()
            return True
        return False

    def _remove(self, mixed):
        ids = []
        logger.logDebug(mixed)
        for data in mixed:
            if 'id' in data:
                ids.append(str(data.get('id')))
        if len(ids) > 0:
            dbcur = self.getCursor()
            try: 
                self._deleteByIds(dbcur, 'SHOW', ids)
                self._dbcon.commit()
                return True
            except: pass
        return False

    def _drop(self):
        dbcur = self.getCursor()
        try: 
            dbcur.execute(logger.logDebug("DROP TABLE SHOW"))
            self._dbcon.commit()
            return True
        except: 
            return False

    def searchByTitle(self, title, limit=100):
        return self.search({'TITLE' : title}, limit)

    def searchByCategory(self, category, limit=100):
        return self.search({'PARENTNAME' : category}, limit)

    def searchByYear(self, year, limit=100):
        return self.search({'YEAR' : year}, limit)

    def getMyList(self, limit=100):
        """The shows of My List that are in the catalog database"""
        ids = self.getUserData().getMyListIds()
        if limit != False:
            ids = ids[:int(limit)]
        return self.get(ids) if ids else []

    def getAllCategories(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT DISTINCT PARENTNAME FROM SHOW"))
        ret = []
        for data in logger.logDebug(dbcur.fetchall()):
            ret.append(data[0])
        return ret 

    def checkIfTableExists(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("CREATE TABLE IF NOT EXISTS SHOW (\
            ID TEXT PRIMARY KEY, \
            TITLE TEXT, \
            PARENTID TEXT, \
            PARENTNAME TEXT, \
            THUMBNAIL TEXT, \
            IMAGE TEXT, \
            FANART TEXT, \
            BANNER TEXT, \
            URL TEXT, \
            DESCRIPTION TEXT, \
            SHORTDESCRIPTION TEXT, \
            YEAR TEXT, \
            TYPE TEXT, \
            DURATION INTEGER NOT NULL DEFAULT 0, \
            VIEWS INTEGER NOT NULL DEFAULT 0, \
            RATING INTEGER NOT NULL DEFAULT 0, \
            VOTES INTEGER NOT NULL DEFAULT 0, \
            MYLIST TEXT)"))
        self._dbcon.commit()
        return True
            
    def getStatistics(self):
        stats = {}
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT COUNT(*) FROM SHOW"))
        stats['count'] = dbcur.fetchone()
        return stats


