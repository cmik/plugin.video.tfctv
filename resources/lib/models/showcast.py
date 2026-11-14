# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

from resources.lib.models import model
from resources.lib.models import userdata
from resources.lib.libraries import control

logger = control.logger

class ShowCast(model.Model):
    
    idFormat = '%s-%s'

    # where a row comes from: the website API (rewritten at each refresh of the show) or the old catalog
    API = 'api'
    LEGACY = 'legacy'

    _columns = ('ID', 'SHOWID', 'ACTORID', 'NAME', 'ROLE', 'THUMBNAIL', 'ORDR', 'URL', 'SOURCE')

    def __init__(self, databasePath):
        model.Model.__init__(self, databasePath)
        self.checkIfTableExists()

    _select = "SELECT ID, \
            SHOWID, \
            ACTORID, \
            NAME, \
            ROLE, \
            THUMBNAIL, \
            ORDR, \
            URL, \
            SOURCE \
            FROM SHOW_CAST"

    def _getStructure(self, data):
        logger.logDebug(len(data))
        logger.logDebug(data)
        if len(data) == 9:
            return {
                'id' : data[0],
                'showid' : data[1],
                'actorid' : data[2],
                'name' : data[3],
                'role' : data[4],
                'thumbnail' : data[5],
                'order' : data[6],
                'castUrl' : data[7],
                'source' : data[8]
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
            URL, \
            SOURCE \
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
                self._exec(dbcur, "INSERT INTO SHOW_CAST (ID, SHOWID, ACTORID, NAME, ROLE, THUMBNAIL, ORDR, URL, SOURCE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                    data.get('id', self.idFormat % (data.get('showid'), data.get('castid'))),
                    data.get('showid'),
                    data.get('castid'),
                    data.get('name'),
                    data.get('role'),
                    data.get('thumbnail'),
                    int(data.get('order') or 0),
                    data.get('url'),
                    data.get('source', self.API)))
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
            URL TEXT, \
            SOURCE TEXT)"))
        if 'SOURCE' not in [row[1].upper() for row in dbcur.execute('PRAGMA table_info(SHOW_CAST)').fetchall()]:
            dbcur.execute('ALTER TABLE SHOW_CAST ADD COLUMN SOURCE TEXT')  # databases of the previous versions
        return self._dbcon.commit()

    @staticmethod
    def actorId(name):
        return str(name).strip().lower().replace(' ', '-')

    def getCast(self, showId):
        """The cast of a show: what the API lists first, then the actors only the old catalog knows"""
        rows = self.getByShow(showId)
        return sorted(rows, key=lambda r: (r.get('source') == self.LEGACY, r.get('order') or 0, r.get('name') or ''))

    def replaceApiCast(self, showId, casts):
        """Store the cast the API gives for a show. The rows of the previous refresh are replaced, and
        the old-catalog rows of actors the API lists now are dropped (no duplicates)."""
        showId = str(showId)
        casts = [c for c in casts if userdata.normalizeTitle(c.get('name'))]
        self.checkIfTableExists()
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM SHOW_CAST WHERE SHOWID = ? AND SOURCE = ?', (showId, self.API))
        listed = set(userdata.normalizeTitle(c.get('name')) for c in casts)
        self._exec(dbcur, 'SELECT ID, NAME FROM SHOW_CAST WHERE SHOWID = ? AND SOURCE = ?', (showId, self.LEGACY))
        self._deleteByIds(dbcur, 'SHOW_CAST', [r[0] for r in dbcur.fetchall() if userdata.normalizeTitle(r[1]) in listed])
        for i, c in enumerate(casts):
            actorId = self.actorId(c.get('name'))
            self._exec(dbcur, "INSERT OR REPLACE INTO SHOW_CAST (ID, SHOWID, ACTORID, NAME, ROLE, THUMBNAIL, ORDR, URL, SOURCE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                self.idFormat % (showId, actorId), showId, actorId, c.get('name').strip(), c.get('role') or '',
                c.get('thumbnail') or '', int(c.get('order') or i), c.get('url') or '', self.API))
        self._dbcon.commit()
        return True

    def addLegacyCast(self, links):
        """Add the (show id, actor name, order) links of the old catalog; the ones a show already has are kept as they are"""
        self.checkIfTableExists()
        dbcur = self.getCursor()
        count = 0
        for showId, name, order in links:
            actorId = self.actorId(name)
            self._exec(dbcur, 'SELECT 1 FROM SHOW_CAST WHERE SHOWID = ? AND LOWER(NAME) = ?', (str(showId), name.strip().lower()))
            if dbcur.fetchone() is None:
                self._exec(dbcur, "INSERT OR IGNORE INTO SHOW_CAST (ID, SHOWID, ACTORID, NAME, ROLE, THUMBNAIL, ORDR, URL, SOURCE) VALUES (?, ?, ?, ?, '', '', ?, '', ?)",
                           (self.idFormat % (showId, actorId), str(showId), actorId, name.strip(), int(order or 0), self.LEGACY))
                count += 1
        self._dbcon.commit()
        return count

    def purgeUnsourced(self):
        """Delete the rows stored before the source was recorded: they link actors to shows of the old catalog"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM SHOW_CAST WHERE SOURCE IS NULL')
        self._dbcon.commit()
        return dbcur.rowcount

    def getStatistics(self):
        stats = {}
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT COUNT(*) FROM SHOW_CAST"))
        stats['count'] = dbcur.fetchone()
        return stats
