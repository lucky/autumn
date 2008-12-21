from autumn.db.query import Query
from autumn.model import cache

class Relation(object):
    
    def __init__(self, model, field=None):            
        self.model = model
        self.field = field
    
    def _set_up(self, instance, owner):
        if isinstance(self.model, basestring):
            self.model = cache.get(self.model)

class ForeignKey(Relation):
        
    def __get__(self, instance, owner):
        super(ForeignKey, self)._set_up(instance, owner)
        if not instance:
            return self.model
        if not self.field:
            self.field = '%s_id' % self.model.Meta.table
        conditions = {self.model.Meta.pk: getattr(instance, self.field)}
        return Query(model=self.model, conditions=conditions)[0]

class OneToMany(Relation):
    
    def __get__(self, instance, owner):
        super(OneToMany, self)._set_up(instance, owner)
        if not instance:
            return self.model
        if not self.field:
            self.field = '%s_id' % instance.Meta.table
        conditions = {self.field: getattr(instance, instance.Meta.pk)}
        return Query(model=self.model, conditions=conditions)