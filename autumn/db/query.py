from autumn.db import escape
from autumn.db.connection import autumn_db

class Query(object):
    '''
    Gives quick access to database by setting attributes (query conditions, et
    cetera), or by the sql methods.
    
    Instance Methods
    ----------------
    
    Creating a Query object requires a Model class at the bare minimum. The 
    doesn't run until results are pulled using a slice, ``list()`` or iterated
    over.
    
    For example::
    
        q = Query(model=MyModel)
        
    This sets up a basic query without conditions. We can set conditions using
    the ``filter`` method::
        
        q.filter(name='John', age=30)
        
    We can also chain the ``filter`` method::
    
        q.filter(name='John').filter(age=30)
        
    In both cases the ``WHERE`` clause will become::
    
        WHERE `name` = 'John' AND `age` = 30
    
    You can also order using ``order_by`` to sort the results::
    
        # The second arg is optional and will default to ``ASC``
        q.order_by('column', 'DESC')
    
    You can limit result sets by slicing the Query instance as if it were a 
    list. Query is smart enough to translate that into the proper ``LIMIT`` 
    clause when the query hasn't yet been run::
    
        q = Query(model=MyModel).filter(name='John')[:10]   # LIMIT 0, 10
        q = Query(model=MyModel).filter(name='John')[10:20] # LIMIT 10, 10
        q = Query(model=MyModel).filter(name='John')[0]    # LIMIT 0, 1
    
    Simple iteration::
    
        for obj in Query(model=MyModel).filter(name='John'):
            # Do something here
            
    Counting results is easy with the ``count`` method. If used on a ``Query``
    instance that has not yet retrieve results, it will perform a ``SELECT
    COUNT(*)`` instead of a ``SELECT *``. ``count`` returns an integer::
        
        count = Query(model=MyModel).filter=(name='John').count()
            
    Class Methods
    -------------
    
    ``Query.raw_sql(sql, values)`` returns a database cursor. Usage::
    
        query = 'SELECT * FROM `users` WHERE id = ?'
        values = (1,) # values must be a tuple or list
        
        # Now we have the database cursor to use as we wish
        cursor = Query.raw_swl(query, values)
        
    ``Query.sql(sql, values)`` has the same syntax as ``Query.raw_sql``, but 
    it returns a dictionary of the result, the field names being the keys.
    
    '''
    
    def __init__(self, query_type='SELECT *', conditions={}, model=None, db=None):
        from autumn.model import Model
        self.type = query_type
        self.conditions = conditions
        self.order = ''
        self.limit = ()
        self.cache = None
        if not issubclass(model, Model):
            raise Exception('Query objects must be created with a model class.')
        self.model = model
        if db:
            self.db = db
        elif model:
            self.db = model.db
        
    def __getitem__(self, k):
        if self.cache != None:
            return self.cache[k]
        
        if isinstance(k, (int, long)):
            self.limit = (k,1)
            lst = self.get_data()
            if not lst:
                return None
            return lst[0]
        elif isinstance(k, slice):
            if k.start is not None:
                assert k.stop is not None, "Limit must be set when an offset is present"
                assert k.stop >= k.start, "Limit must be greater than or equal to offset"
                self.limit = k.start, (k.stop - k.start)
            elif k.stop is not None:
                self.limit = 0, k.stop
        
        return self.get_data()
        
    def __len__(self):
        return len(self.get_data())
        
    def __iter__(self):
        return iter(self.get_data())
        
    def __repr__(self):
        return repr(self.get_data())
        
    def count(self):
        if self.cache is None:
            self.type = 'SELECT COUNT(*)'
            return self.execute_query().fetchone()[0]
        else:
            return len(self.cache)
        
    def filter(self, **kwargs):
        self.conditions.update(kwargs)
        return self
        
    def order_by(self, field, direction='ASC'):
        self.order = 'ORDER BY %s %s' % (escape(field), direction)
        return self
        
    def extract_condition_keys(self):
        if len(self.conditions):
            return 'WHERE %s' % ' AND '.join("%s=%s" % (escape(k), self.db.conn.placeholder) for k in self.conditions)
        
    def extract_condition_values(self):
        return list(self.conditions.itervalues())
        
    def query_template(self):
        return '%s FROM %s %s %s %s' % (
            self.type,
            self.model.Meta.table_safe,
            self.extract_condition_keys() or '',
            self.order,
            self.extract_limit() or '',
        )
        
    def extract_limit(self):
        if len(self.limit):
            return 'LIMIT %s' % ', '.join(str(l) for l in self.limit)
        
    def get_data(self):
        if self.cache is None:
            self.cache = list(self.iterator())
        return self.cache
        
    def iterator(self):        
        for row in self.execute_query().fetchall():
            obj = self.model(*row)
            obj._new_record = False
            yield obj
            
    def execute_query(self):
        values = self.extract_condition_values()
        return Query.raw_sql(self.query_template(), values, self.db)
        
    @classmethod
    def get_db(cls, db=None):
        if not db:
            db = getattr(cls, "db", autumn_db)
        return db
        
    @classmethod
    def get_cursor(cls, db=None):
        db = db or cls.get_db()
        return db.conn.connection.cursor()
        
    @classmethod
    def sql(cls, sql, values=(), db=None):
        db = db or cls.get_db()
        cursor = Query.raw_sql(sql, values, db)
        fields = [f[0] for f in cursor.description]
        return [dict(zip(fields, row)) for row in cursor.fetchall()]
            
    @classmethod
    def raw_sql(cls, sql, values=(), db=None):
        db = db or cls.get_db()
        cursor = cls.get_cursor(db)
        try:
            cursor.execute(sql, values)
            if db.b_commit:
                db.conn.connection.commit()
        except BaseException, ex:
            if db.b_debug:
                print "raw_sql: exception: ", ex
                print "sql:", sql
                print "values:", values
            raise
        return cursor

    @classmethod
    def raw_sqlscript(cls, sql, db=None):
        db = db or cls.get_db()
        cursor = cls.get_cursor(db)
        try:
            cursor.executescript(sql)
            if db.b_commit:
                db.conn.connection.commit()
        except BaseException, ex:
            if db.b_debug:
                print "raw_sqlscript: exception: ", ex
                print "sql:", sql
            raise
        return cursor



# begin() and commit() for SQL transaction control
# This has only been tested with SQLite3 with default isolation level.
# http://www.python.org/doc/2.5/lib/sqlite3-Controlling-Transactions.html

    @classmethod
    def begin(cls, db=None):
        """
        begin() and commit() let you explicitly specify an SQL transaction.
        Be sure to call commit() after you call begin().
        """
        db = db or cls.get_db()
        db.b_commit = False

    @classmethod
    def commit(cls, db=None):
        """
        begin() and commit() let you explicitly specify an SQL transaction.
        Be sure to call commit() after you call begin().
        """
        cursor = None
        try:
            db = db or cls.get_db()
            db.conn.connection.commit()
        finally:
            db.b_commit = True
        return cursor
