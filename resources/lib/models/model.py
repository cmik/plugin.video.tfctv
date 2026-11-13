# -*- coding: utf-8 -*-

'''
    Tfc.tv Add-on
    Copyright (C) 2018 cmik
'''

try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from resources.lib.libraries import control
logger = control.logger
    
class Model():
    
    _dbcon = None
    # columns usable as a search/lookup key (the model subclasses set it)
    _columns = ()
    # max values per "IN (...)" (SQLite older than 3.32 accepts 999 variables)
    _chunkSize = 500

    def __init__(self, databasePath):
        self._dbcon = database.connect(logger.logDebug(databasePath))
        return None
        
    def _getStructure(self, data):
        return {}
        
    def _search(self, limit):
        return []

    def _retrieveAll(self):
        return []
        
    def _retrieve(self, mixed):
        return []
        
    def _save(self, mixed):
        return False        

    def _replace(self, mixed):
        return False
       
    def getCursor(self):
        return self._dbcon.cursor()

    # --- parameterized SQL helpers: values are always passed as parameters, never formatted in the query ---

    def _exec(self, dbcur, sql, params=()):
        logger.logDebug('%s %s' % (sql, repr(params)))
        return dbcur.execute(sql, params)

    def _column(self, name):
        """Check a column name against the model columns (a name can't be a parameter)"""
        name = str(name).upper()
        if name not in self._columns:
            raise ValueError('Unknown column %s' % name)
        return name

    def _selectBy(self, select, key, values):
        """Run `select` (a SELECT ... FROM table query) filtered by `key IN (values)`"""
        key = self._column(key)
        values = [str(v) for v in values]
        dbcur = self.getCursor()
        rows = []
        for i in range(0, len(values), self._chunkSize):
            chunk = values[i:i + self._chunkSize]
            self._exec(dbcur, '%s WHERE %s IN (%s)' % (select, key, ','.join('?' * len(chunk))), chunk)
            rows += dbcur.fetchall()
        return rows

    def _selectLike(self, select, search, limit):
        """Run `select` with a `column LIKE %value%` filter for each item of the `search` dict"""
        where = []
        params = []
        for k, v in search.items():
            where.append("%s LIKE ? ESCAPE '!'" % self._column(k))
            params.append('%%%s%%' % str(v).replace('!', '!!').replace('%', '!%').replace('_', '!_'))
        sql = '%s WHERE %s' % (select, ' AND '.join(where))
        if limit != False:
            sql += ' LIMIT %d' % int(limit)
        dbcur = self.getCursor()
        self._exec(dbcur, sql, params)
        return dbcur.fetchall()

    def _deleteByIds(self, dbcur, table, ids):
        ids = [str(i) for i in ids]
        for i in range(0, len(ids), self._chunkSize):
            chunk = ids[i:i + self._chunkSize]
            self._exec(dbcur, 'DELETE FROM %s WHERE ID IN (%s)' % (table, ','.join('?' * len(chunk))), chunk)

    def _updateRow(self, dbcur, table, rowId, fields):
        """UPDATE only the given (column, value) pairs of the row `rowId`; empty values are ignored"""
        fields = [(c, v) for c, v in fields if v]
        if not fields:
            return
        self._exec(
            dbcur,
            'UPDATE %s SET %s WHERE ID = ?' % (table, ', '.join('%s = ?' % c for c, v in fields)),
            [v for c, v in fields] + [str(rowId)]
        )
    
    def search(self, search, limit=False):
        items = []
        if isinstance(search, dict):
            try:
                results = self._search(search, limit)
                for d in results:
                    items.append(self._getStructure(d))
            except (Exception) as e:
                logger.logError('[%s] Exception: %s for data %s' % (self.__class__.__name__, str(e), repr(search)))
                pass

        return items

    def getAll(self):
        items = []
        try:
            results = self._retrieveAll()
            for d in results:
                items.append(self._getStructure(d))
        except (Exception) as e:
            logger.logError('Exception: %s' % str(e))
            pass

        return items

    def get(self, mixed, key='ID'):
        search = mixed if isinstance(mixed, list) else [mixed]
        items = []
        try:
            results = self._retrieve(search, key)
            for d in results:
                items.append(self._getStructure(d))
        except (Exception) as e:
            logger.logError('Exception: %s for data %s' % (str(e), repr(mixed)))
            pass

        return items
        
    def set(self, mixed):
        data = mixed if isinstance(mixed, list) else [mixed]
        try:            
            return self._replace(data)
        except (Exception) as e:
            logger.logError('[%s] Exception: %s for data %s' % (self.__class__.__name__, str(e), repr(mixed)))
            return False
        
    def update(self, mixed):
        data = mixed if isinstance(mixed, list) else [mixed]
        try:            
            return self._save(data)
        except (Exception) as e:
            logger.logError('[%s] Exception: %s for data %s' % (self.__class__.__name__, str(e), repr(mixed)))
            return False

    def delete(self, mixed):
        search = mixed if isinstance(mixed, list) else [mixed]
        try:
            return self._remove(search)
        except:
            return False
            
    def drop(self):
        try:
            return self._drop()
        except:
            return False

    def execute(self, mixed):
        queries = mixed if isinstance(mixed, list) else [mixed]
        results = []
        try: 
            dbcur = self.getCursor()
            for query in queries:
                dbcur.execute(logger.logDebug(query))
                results.append(dbcur.fetchall())
            return results
        except: 
            return False 

    def executeUpdate(self, mixed):
        queries = mixed if isinstance(mixed, list) else [mixed]
        try: 
            dbcur = self.getCursor()
            for query in queries:
                dbcur.execute(logger.logDebug(query))
            return self._dbcon.commit()
        except: 
            return False 


