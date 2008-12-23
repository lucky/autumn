from autumn.db.query import Query
from autumn.db import escape
from autumn.db.connection import autumn_db, Database
from autumn.validators import ValidatorChain
    
class ModelCache(object):
    models = {}
    
    def add(self, model):
        self.models[model.__name__] = model
        
    def get(self, model_name):
        return self.models[model_name]
   
cache = ModelCache()
    
class Empty:
    pass

class ModelBase(type):
    '''
    Metaclass for Model
    
    Sets up default table name and primary key
    Adds fields from table as attributes
    Creates ValidatorChains as necessary
    
    '''
    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return super(ModelBase, cls).__new__(cls, name, bases, attrs)
            
        new_class = type.__new__(cls, name, bases, attrs)
        
        if not getattr(new_class, 'Meta', None):
            new_class.Meta = Empty
        
        if not getattr(new_class.Meta, 'table', None):
            new_class.Meta.table = name.lower()
        new_class.Meta.table_safe = escape(new_class.Meta.table)
        
        # Assume id is the default 
        if not getattr(new_class.Meta, 'pk', None):
            new_class.Meta.pk = 'id'
        
        # Create function to loop over iterable validations
        for k, v in getattr(new_class.Meta, 'validations', {}).iteritems():
            if isinstance(v, (list, tuple)):
                new_class.Meta.validations[k] = ValidatorChain(*v)
        
        # See cursor.description
        # http://www.python.org/dev/peps/pep-0249/
        if not hasattr(new_class, "db"):
            new_class.db = autumn_db
        db = new_class.db
        q = Query.raw_sql('SELECT * FROM %s LIMIT 1' % new_class.Meta.table_safe, db=new_class.db)
        new_class._fields = [f[0] for f in q.description]
        
        cache.add(new_class)
        return new_class

class Model(object):
    '''
    Allows for automatic attributes based on table columns.
    
    Syntax::
    
        from autumn.model import Model
        class MyModel(Model):
            class Meta:
                # If field is blank, this sets a default value on save
                defaults = {'field': 1}
            
                # Each validation must be callable
                # You may also place validations in a list or tuple which is
                # automatically converted int a ValidationChain
                validations = {'field': lambda v: v > 0}
            
                # Table name is lower-case model name by default
                # Or we can set the table name
                table = 'mytable'
        
        # Create new instance using args based on the order of columns
        m = MyModel(1, 'A string')
        
        # Or using kwargs
        m = MyModel(field=1, text='A string')
        
        # Saving inserts into the database (assuming it validates [see below])
        m.save()
        
        # Updating attributes
        m.field = 123
        
        # Updates database record
        m.save()
        
        # Deleting removes from the database 
        m.delete()
        
        # Purely saving with an improper value, checked against 
        # Model.Meta.validations[field_name] will raise Model.ValidationError
        m = MyModel(field=0)
        
        # 'ValidationError: Improper value "0" for "field"'
        m.save()
        
        # Or before saving we can check if it's valid
        if m.is_valid():
            m.save()
        else:
            # Do something to fix it here
        
        # Retrieval is simple using Model.get
        # Returns a Query object that can be sliced
        MyModel.get()
        
        # Returns a MyModel object with an id of 7
        m = MyModel.get(7)
        
        # Limits the query results using SQL's LIMIT clause
        # Returns a list of MyModel objects
        m = MyModel.get()[:5]   # LIMIT 0, 5
        m = MyModel.get()[10:15] # LIMIT 10, 5
        
        # We can get all objects by slicing, using list, or iterating
        m = MyModel.get()[:]
        m = list(MyModel.get())
        for m in MyModel.get():
            # do something here...
            
        # We can filter our Query
        m = MyModel.get(field=1)
        m = m.filter(another_field=2)
        
        # This is the same as
        m = MyModel.get(field=1, another_field=2)
        
        # Set the order by clause
        m = MyModel.get(field=1).order_by('field', 'DESC')
        # Removing the second argument defaults the order to ASC
        
    '''
    __metaclass__ = ModelBase
    
    debug = False

    def __init__(self, *args, **kwargs):
        'Allows setting of fields using kwargs'
        self.__dict__[self.Meta.pk] = None
        self._new_record = True
        [setattr(self, self._fields[i], arg) for i, arg in enumerate(args)]
        [setattr(self, k, v) for k, v in kwargs.iteritems()]
        self._changed = set()
        
    def __setattr__(self, name, value):
        'Records when fields have changed'
        if name != '_changed' and name in self._fields and hasattr(self, '_changed'):
            self._changed.add(name)
        self.__dict__[name] = value
        
    def _get_pk(self):
        'Sets the current value of the primary key'
        return getattr(self, self.Meta.pk, None)

    def _set_pk(self, value):
        'Sets the primary key'
        return setattr(self, self.Meta.pk, value)
        
    def _update(self):
        'Uses SQL UPDATE to update record'
        query = 'UPDATE %s SET ' % self.Meta.table_safe
        query += ', '.join(['%s = %s' % (escape(f), self.db.conn.placeholder) for f in self._changed])
        query += ' WHERE %s = %s ' % (escape(self.Meta.pk), self.db.conn.placeholder)
        
        values = [getattr(self, f) for f in self._changed]
        values.append(self._get_pk())
        
        cursor = Query.raw_sql(query, values, self.db)
        
    def _new_save(self):
        'Uses SQL INSERT to create new record'
        # if pk field is set, we want to insert it too
        # if pk field is None, we want to auto-create it from lastrowid
        auto_pk = 1 and (self._get_pk() is None) or 0
        fields=[
            escape(f) for f in self._fields 
            if f != self.Meta.pk or not auto_pk
        ]
        query = 'INSERT INTO %s (%s) VALUES (%s)' % (
               self.Meta.table_safe,
               ', '.join(fields),
               ', '.join([self.db.conn.placeholder] * len(fields) )
        )
        values = [getattr(self, f, None) for f in self._fields
               if f != self.Meta.pk or not auto_pk]
        cursor = Query.raw_sql(query, values, self.db)
       
        if self._get_pk() is None:
            self._set_pk(cursor.lastrowid)
        return True
        
    def _get_defaults(self):
        'Sets attribute defaults based on ``defaults`` dict'
        for k, v in getattr(self.Meta, 'defaults', {}).iteritems():
            if not getattr(self, k, None):
                if callable(v):
                    v = v()
                setattr(self, k, v)
        
    def delete(self):
        'Deletes record from database'
        query = 'DELETE FROM %s WHERE %s = %s' % (self.Meta.table_safe, self.Meta.pk, self.db.conn.placeholder)
        values = [getattr(self, self.Meta.pk)]
        Query.raw_sql(query, values, self.db)
        return True
        
    def is_valid(self):
        'Returns boolean on whether all ``validations`` pass'
        try:
            self._validate()
            return True
        except Model.ValidationError:
            return False
    
    def _validate(self):
        'Tests all ``validations``, raises ``Model.ValidationError``'
        for k, v in getattr(self.Meta, 'validations', {}).iteritems():
            assert callable(v), 'The validator must be callable'
            value = getattr(self, k)
            if not v(value):
                raise Model.ValidationError, 'Improper value "%s" for "%s"' % (value, k)
        
    def save(self):
        'Sets defaults, validates and inserts into or updates database'
        self._get_defaults()
        self._validate()
        if self._new_record:
            self._new_save()
            self._new_record = False
            return True
        else:
            return self._update()
            
    @classmethod
    def get(cls, _obj_pk=None, **kwargs):
        'Returns Query object'
        if _obj_pk is not None:
            return cls.get(**{cls.Meta.pk: _obj_pk})[0]

        return Query(model=cls, conditions=kwargs)
        
        
    class ValidationError(Exception):
        pass
