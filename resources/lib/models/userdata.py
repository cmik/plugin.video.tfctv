# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

import os
import re
import time
import unicodedata

try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from resources.lib.models import model
from resources.lib.libraries import control

logger = control.logger

SHOW = 'show'
EPISODE = 'episode'


def normalizeTitle(title):
    """Title without case, accents and punctuation, to find the same show again under another id"""
    title = unicodedata.normalize('NFKD', u'%s' % (title or ''))
    title = ''.join(c for c in title if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '', title.lower())


class UserData(model.Model):
    """Data that belongs to the user (My List, views...), kept apart from the catalog databases
    (shows, episodes) so that replacing or resetting the catalog never loses it."""

    _columns = ('SHOWID', 'TITLE', 'ADDED', 'KIND', 'ITEMID', 'EPISODEID')

    def __init__(self, databasePath):
        model.Model.__init__(self, databasePath)
        self.checkIfTablesExist()

    def checkIfTablesExist(self):
        dbcur = self.getCursor()
        for sql in (
            "CREATE TABLE IF NOT EXISTS MYLIST (\
                SHOWID TEXT PRIMARY KEY, \
                TITLE TEXT, \
                ADDED TEXT)",
            "CREATE TABLE IF NOT EXISTS STATS (\
                KIND TEXT NOT NULL, \
                ITEMID TEXT NOT NULL, \
                VIEWS INTEGER NOT NULL DEFAULT 0, \
                RATING INTEGER NOT NULL DEFAULT 0, \
                VOTES INTEGER NOT NULL DEFAULT 0, \
                PRIMARY KEY (KIND, ITEMID))",
            "CREATE TABLE IF NOT EXISTS META (\
                KEY TEXT PRIMARY KEY, \
                VALUE TEXT)",
            "CREATE TABLE IF NOT EXISTS HISTORY (\
                ID INTEGER PRIMARY KEY AUTOINCREMENT, \
                EPISODEID TEXT NOT NULL, \
                SHOWID TEXT, \
                TITLE TEXT, \
                SHOWNAME TEXT, \
                THUMBNAIL TEXT, \
                LTYPE TEXT, \
                VIEWED TEXT)",
            "CREATE INDEX IF NOT EXISTS HISTORY_EPISODE ON HISTORY (EPISODEID)",
            "CREATE TABLE IF NOT EXISTS PROGRESS (\
                EPISODEID TEXT PRIMARY KEY, \
                POSITION INTEGER NOT NULL DEFAULT 0, \
                TOTAL INTEGER NOT NULL DEFAULT 0, \
                UPDATED TEXT)"
        ):
            self._exec(dbcur, sql)
        self._dbcon.commit()

    # --- meta

    def getMeta(self, key, default=None):
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT VALUE FROM META WHERE KEY = ?', (key,))
        row = dbcur.fetchone()
        return default if row is None else row[0]

    def setMeta(self, key, value):
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM META WHERE KEY = ?', (key,))
        self._exec(dbcur, 'INSERT INTO META (KEY, VALUE) VALUES (?, ?)', (key, str(value)))
        self._dbcon.commit()

    # --- My List

    def addToMyList(self, showId, title=''):
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM MYLIST WHERE SHOWID = ?', (str(showId),))
        self._exec(dbcur, 'INSERT INTO MYLIST (SHOWID, TITLE, ADDED) VALUES (?, ?, ?)',
                   (str(showId), title or '', time.strftime('%Y-%m-%d %H:%M:%S')))
        self._dbcon.commit()
        return True

    def removeFromMyList(self, showId):
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM MYLIST WHERE SHOWID = ?', (str(showId),))
        self._dbcon.commit()
        return True

    def getMyList(self):
        """The (show id, title) pairs of My List, oldest first"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT SHOWID, TITLE FROM MYLIST ORDER BY ADDED, SHOWID')
        return [(r[0], r[1]) for r in dbcur.fetchall()]

    def getMyListIds(self, ids=None):
        """The ids of My List (restricted to `ids` when given)"""
        if ids is None:
            return [r[0] for r in self.getMyList()]
        found = set(r[0] for r in self._selectBy('SELECT SHOWID FROM MYLIST', 'SHOWID', ids))
        return [str(i) for i in ids if str(i) in found]

    def replaceMyListId(self, oldId, newId, title=None):
        """Point an entry of My List to another show id"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT TITLE, ADDED FROM MYLIST WHERE SHOWID = ?', (str(oldId),))
        row = dbcur.fetchone()
        if row is None:
            return False
        self._exec(dbcur, 'DELETE FROM MYLIST WHERE SHOWID IN (?, ?)', (str(oldId), str(newId)))
        self._exec(dbcur, 'INSERT INTO MYLIST (SHOWID, TITLE, ADDED) VALUES (?, ?, ?)',
                   (str(newId), title or row[0], row[1]))
        self._dbcon.commit()
        return True

    # --- views, rating, votes

    def getStats(self, kind, ids):
        """{id: (views, rating, votes)} for the ids that have stored stats"""
        rows = self._selectBy('SELECT ITEMID, VIEWS, RATING, VOTES FROM STATS', 'ITEMID', ids,
                              where='KIND = ?', params=(str(kind),)) if ids else []
        return dict((r[0], (int(r[1]), int(r[2]), int(r[3]))) for r in rows)

    def setStats(self, kind, itemId, views=None, rating=None, votes=None):
        """Store the given counters of an item (the others are kept)"""
        values = [('VIEWS', views), ('RATING', rating), ('VOTES', votes)]
        values = [(c, int(v)) for c, v in values if v is not None]
        if not values:
            return False
        dbcur = self.getCursor()
        self._exec(dbcur, 'UPDATE STATS SET %s WHERE KIND = ? AND ITEMID = ?' % ', '.join('%s = ?' % c for c, v in values),
                   [v for c, v in values] + [str(kind), str(itemId)])
        if dbcur.rowcount < 1:
            fields = dict(values)
            self._exec(dbcur, 'INSERT INTO STATS (KIND, ITEMID, VIEWS, RATING, VOTES) VALUES (?, ?, ?, ?, ?)',
                       (str(kind), str(itemId), fields.get('VIEWS', 0), fields.get('RATING', 0), fields.get('VOTES', 0)))
        self._dbcon.commit()
        return True

    # --- view history: what the user played, with what is needed to list it even when the catalog is replaced

    # the oldest views are dropped beyond this
    historyLimit = 2000

    def addToHistory(self, episodeId, showId='', title='', show='', thumbnail='', ltype='', viewed=None):
        """Record a view of an episode (or a movie)"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'INSERT INTO HISTORY (EPISODEID, SHOWID, TITLE, SHOWNAME, THUMBNAIL, LTYPE, VIEWED) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (str(episodeId), str(showId or ''), title or '', show or '', thumbnail or '', ltype or '',
                    time.strftime('%Y-%m-%d %H:%M:%S') if viewed is None else viewed))
        self._exec(dbcur, 'DELETE FROM HISTORY WHERE ID <= (SELECT ID FROM HISTORY ORDER BY ID DESC LIMIT 1 OFFSET ?)', (self.historyLimit,))
        self._dbcon.commit()
        return True

    def getHistory(self, limit=100, offset=0):
        """The episodes viewed, the last viewed first; an episode viewed several times is listed once (its last view)"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT EPISODEID, SHOWID, TITLE, SHOWNAME, THUMBNAIL, LTYPE, VIEWED FROM HISTORY '
                          'WHERE ID IN (SELECT MAX(ID) FROM HISTORY GROUP BY EPISODEID) '
                          'ORDER BY VIEWED DESC, ID DESC LIMIT ? OFFSET ?', (int(limit), int(offset)))
        return [{'episodeid': r[0], 'showid': r[1], 'title': r[2], 'show': r[3], 'thumbnail': r[4], 'ltype': r[5], 'viewed': r[6]}
                for r in dbcur.fetchall()]

    def getLastViewed(self, ids):
        """{episode id: date of its last view} for the episodes that were viewed on a known date"""
        rows = self._selectBy('SELECT EPISODEID, VIEWED FROM HISTORY', 'EPISODEID', ids, where="VIEWED <> ''") if ids else []
        last = {}
        for episodeId, viewed in rows:
            if viewed and viewed > last.get(episodeId, ''):
                last[episodeId] = viewed
        return last

    def countHistory(self):
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT COUNT(DISTINCT EPISODEID) FROM HISTORY')
        return dbcur.fetchone()[0]

    def getHistoryIds(self):
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT DISTINCT EPISODEID FROM HISTORY')
        return [r[0] for r in dbcur.fetchall()]

    def removeFromHistory(self, episodeId):
        """Forget an episode: it isn't listed anymore and its viewed flag goes with it"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM HISTORY WHERE EPISODEID = ?', (str(episodeId),))
        self._exec(dbcur, 'DELETE FROM PROGRESS WHERE EPISODEID = ?', (str(episodeId),))
        self._exec(dbcur, 'UPDATE STATS SET VIEWS = 0 WHERE KIND = ? AND ITEMID = ?', (EPISODE, str(episodeId)))
        self._dbcon.commit()
        return True

    def clearHistory(self):
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM HISTORY')
        self._exec(dbcur, 'DELETE FROM PROGRESS')
        self._exec(dbcur, 'UPDATE STATS SET VIEWS = 0 WHERE KIND = ?', (EPISODE,))
        self._dbcon.commit()
        return True

    # --- playback progress: where to resume an episode that wasn't finished

    def setProgress(self, episodeId, position, total):
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM PROGRESS WHERE EPISODEID = ?', (str(episodeId),))
        self._exec(dbcur, 'INSERT INTO PROGRESS (EPISODEID, POSITION, TOTAL, UPDATED) VALUES (?, ?, ?, ?)',
                   (str(episodeId), int(position), int(total), time.strftime('%Y-%m-%d %H:%M:%S')))
        self._dbcon.commit()
        return True

    def clearProgress(self, episodeId):
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM PROGRESS WHERE EPISODEID = ?', (str(episodeId),))
        self._dbcon.commit()
        return True

    def getProgress(self, ids):
        """{episode id: (position, total)} in seconds, for the episodes that can be resumed"""
        rows = self._selectBy('SELECT EPISODEID, POSITION, TOTAL FROM PROGRESS', 'EPISODEID', ids) if ids else []
        return dict((r[0], (int(r[1]), int(r[2]))) for r in rows)

    def getProgressList(self, limit=100, offset=0):
        """The episodes that can be resumed, the last played first, with what was kept of the last view"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT p.EPISODEID, p.POSITION, p.TOTAL, p.UPDATED, h.SHOWID, h.TITLE, h.SHOWNAME, h.THUMBNAIL, h.LTYPE '
                          'FROM PROGRESS p LEFT JOIN HISTORY h ON h.ID = (SELECT MAX(ID) FROM HISTORY WHERE EPISODEID = p.EPISODEID) '
                          'ORDER BY p.UPDATED DESC, p.EPISODEID LIMIT ? OFFSET ?', (int(limit), int(offset)))
        return [{'episodeid': r[0], 'position': r[1], 'total': r[2], 'viewed': r[3], 'showid': r[4] or '', 'title': r[5] or '',
                 'show': r[6] or '', 'thumbnail': r[7] or '', 'ltype': r[8] or ''} for r in dbcur.fetchall()]

    def countProgress(self):
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT COUNT(*) FROM PROGRESS')
        return dbcur.fetchone()[0]

    def getViewedEpisodeIds(self):
        """The episodes that have a view count (played before the view history existed, or whose history was lost)"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT ITEMID FROM STATS WHERE KIND = ? AND VIEWS > 0', (EPISODE,))
        return [r[0] for r in dbcur.fetchall()]

    def getViews(self, kind, itemId):
        """How many times an item was played"""
        return self.getStats(kind, [itemId]).get(str(itemId), (0, 0, 0))[0]

    # --- one-time import of what the old versions stored in the catalog databases

    def importLegacy(self, showsPath, episodesPath):
        """Move My List and the counters stored in the SHOW/EPISODE columns of the catalog
        databases of the previous versions here. Done once: the flag prevents an item removed
        from My List from coming back. Returns the number of imported rows."""
        if self.getMeta('legacyImported') == '1':
            return 0
        count = 0
        count += self._importLegacyTable(showsPath, 'SHOW', SHOW)
        count += self._importLegacyTable(episodesPath, 'EPISODE', EPISODE)
        self.setMeta('legacyImported', 1)
        logger.logNotice('User data imported from the catalog databases: %d rows' % count)
        return count

    def _importLegacyTable(self, path, table, kind):
        count = 0
        if not os.path.exists(path):
            return 0
        try:
            legacy = database.connect(path)
        except Exception as e:
            logger.logError('Can\'t open %s: %s' % (path, str(e)))
            return 0
        try:
            cur = legacy.cursor()
            columns = [r[1].upper() for r in cur.execute('PRAGMA table_info(%s)' % table).fetchall()]
            if not columns:
                return 0
            if kind == SHOW and 'MYLIST' in columns:
                for row in cur.execute("SELECT ID, TITLE FROM SHOW WHERE MYLIST = 'true'").fetchall():
                    if row[0] not in self.getMyListIds([row[0]]):
                        self.addToMyList(row[0], row[1])
                        count += 1
            if all(c in columns for c in ('VIEWS', 'RATING', 'VOTES')):
                dbcur = self.getCursor()
                for row in cur.execute('SELECT ID, VIEWS, RATING, VOTES FROM %s WHERE VIEWS > 0 OR RATING > 0 OR VOTES > 0' % table).fetchall():
                    self._exec(dbcur, 'INSERT OR IGNORE INTO STATS (KIND, ITEMID, VIEWS, RATING, VOTES) VALUES (?, ?, ?, ?, ?)',
                               (kind, str(row[0]), int(row[1] or 0), int(row[2] or 0), int(row[3] or 0)))
                    count += 1
                self._dbcon.commit()
        except Exception as e:
            logger.logError('Can\'t import the user data of %s: %s' % (table, str(e)))
        finally:
            legacy.close()
        return count
