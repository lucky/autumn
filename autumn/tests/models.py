from autumn.db.connection import autumn_db
from autumn.model import Model
from autumn.db.relations import ForeignKey, OneToMany
from autumn import validators
import datetime

#autumn_db.conn.connect('sqlite3', '/tmp/example.db')
autumn_db.conn.connect('mysql', user='root', db='autumn')
    
class Author(Model):
    books = OneToMany('Book')
    
    class Meta:
        defaults = {'bio': 'No bio available'}
        validations = {'first_name': validators.Length(),
                       'last_name': (validators.Length(), lambda x: x != 'BadGuy!')}
    
class Book(Model):
    author = ForeignKey(Author)
    
    class Meta:
        table = 'books'
