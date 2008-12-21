#!/usr/bin/env python
import unittest
import datetime
from autumn.model import Model
from autumn.tests.models import Book, Author
from autumn.db.query import Query
from autumn.db import escape
from autumn import validators

class TestModels(unittest.TestCase):
        
    def testmodel(self):
        # Create tables
        
        ### MYSQL ###
        #
        # DROP TABLE IF EXISTS author;
        # CREATE TABLE author (
        #     id INT(11) NOT NULL auto_increment,
        #     first_name VARCHAR(40) NOT NULL,
        #     last_name VARCHAR(40) NOT NULL,
        #     bio TEXT,
        #     PRIMARY KEY (id)
        # );
        # DROP TABLE IF EXISTS books;
        # CREATE TABLE books (
        #     id INT(11) NOT NULL auto_increment,
        #     title VARCHAR(255),
        #     author_id INT(11),
        #     FOREIGN KEY (author_id) REFERENCES author(id),
        #     PRIMARY KEY (id)
        # );
        
        ### SQLITE ###
        #
        # DROP TABLE IF EXISTS author;
        # DROP TABLE IF EXISTS books;
        # CREATE TABLE author (
        #   id INTEGER PRIMARY KEY AUTOINCREMENT,
        #   first_name VARCHAR(40) NOT NULL,
        #   last_name VARCHAR(40) NOT NULL,
        #   bio TEXT
        # );
        # CREATE TABLE books (
        #   id INTEGER PRIMARY KEY AUTOINCREMENT,
        #   title VARCHAR(255),
        #   author_id INT(11),
        #   FOREIGN KEY (author_id) REFERENCES author(id)
        # );
        
        for table in ('author', 'books'):
            Query.raw_sql('DELETE FROM %s' % escape(table))
        
        # Test Creation
        james = Author(first_name='James', last_name='Joyce')
        james.save()
        
        kurt = Author(first_name='Kurt', last_name='Vonnegut')
        kurt.save()
        
        tom = Author(first_name='Tom', last_name='Robbins')
        tom.save()
        
        Book(title='Ulysses', author_id=james.id).save()
        Book(title='Slaughter-House Five', author_id=kurt.id).save()
        Book(title='Jitterbug Perfume', author_id=tom.id).save()
        slww = Book(title='Still Life with Woodpecker', author_id=tom.id)
        slww.save()
        
        # Test ForeignKey
        self.assertEqual(slww.author.first_name, 'Tom')
        
        # Test OneToMany
        self.assertEqual(len(list(tom.books)), 2)
        
        kid = kurt.id
        del(james, kurt, tom, slww)
        
        # Test retrieval
        b = Book.get(title='Ulysses')[0]
        
        a = Author.get(id=b.author_id)[0]
        self.assertEqual(a.id, b.author_id)
        
        a = Author.get(id=b.id)[:]
        self.assert_(isinstance(a, list))
        
        # Test update
        new_last_name = 'Vonnegut, Jr.'
        a = Author.get(id=kid)[0]
        a.last_name = new_last_name
        a.save()
        
        a = Author.get(kid)
        self.assertEqual(a.last_name, new_last_name)
        
        # Test count
        self.assertEqual(Author.get().count(), 3)
        
        self.assertEqual(len(Book.get()[1:4]), 3)
        
        # Test delete
        a.delete()
        self.assertEqual(Author.get().count(), 2)
        
        # Test validation
        a = Author(first_name='', last_name='Ted')
        try:
            a.save()
            raise Exception('Validation not caught')
        except Model.ValidationError:
            pass
        
        # Test defaults
        a.first_name = 'Bill and'
        a.save()
        self.assertEqual(a.bio, 'No bio available')
        
        try:
            Author(first_name='I am a', last_name='BadGuy!').save()
            raise Exception('Validation not caught')
        except Model.ValidationError:
            pass
            
    def testvalidators(self):
        ev = validators.Email()
        assert ev('test@example.com')
        assert not ev('adsf@.asdf.asdf')
        assert validators.Length()('a')
        assert not validators.Length(2)('a')
        assert validators.Length(max_length=10)('abcdegf')
        assert not validators.Length(max_length=3)('abcdegf')

        n = validators.Number(1, 5)
        assert n(2)
        assert not n(6)
        assert validators.Number(1)(100.0)
        assert not validators.Number()('rawr!')

        vc = validators.ValidatorChain(validators.Length(8), validators.Email())
        assert vc('test@example.com')
        assert not vc('a@a.com')
        assert not vc('asdfasdfasdfasdfasdf')
        
if __name__ == '__main__':
    unittest.main()
