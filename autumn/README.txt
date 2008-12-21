Autumn 0.5


This is a modified version of the Autumn ORM.

http://autumn-orm.org/

http://pypi.python.org/pypi/autumn



This is version 0.5 of Autumn, modified to work with multi-threaded SQLite.
The modifications include:

* Prior version use a global "db" object, which is a database connection
object.  This modified version replaces "db" with "db.conn", and stores
this new object in a class.

* Storing db.conn inside a class lets you have more than one connection
object.  This is to allow having multiple SQLite database files
open at one time.  To use more than one connection object, create a new
class for each connection object.  Make your Autumn model class inherit
from the new connection object class before it inherits from Autumn's
"Model" class, so that the new db.conn object will be found first.

* The connection object, now called "conn", is now stored in a container
called "db".  The default container is a trivial class, but it is now
possible to use a threading.local() object as the container; this will
allow multiple threads to each have their own connection object, as is
required by SQLite.

* An "autumn.util" module is added.  It includes some convenience
functions, and a class called AutoConn.  AutoConn sets up a db object
that will automatically initialize thread-local .conn members as needed.
When using AutoConn, the whole thread-local storage requirement just works
and you don't need to pay any attention to it.   There are comments at the
end of the util module, with example code showing how to use AutoConn.

* Some bugs were fixed.

* A version number and version string was added to __init__.py.

* Added Query.begin() and Query.commit(), for bracketing multiple
SQL operations and making them into a single transaction.



How to use Autumn with multi-threaded SQLite:

* Set up a class for each SQLite database file you wish to use.

* In each class, set an AutoConn() object specifying the SQLite .DB file.

* Set up a single lock object to control access to SQLite.  Two threads
cannot use SQLite at the same time; if one thread is using SQLite the
other thread must wait.  The lock object makes sure that only one thread
at a time tries to use SQLite.

db_lock = threading.RLock()

* Before doing anything with the database, get the lock.  Release the
lock when done.  The best way to do this is to use the Python 2.5 and
newer "with" statement feature.  In Python 2.5 you must import it from
__future__.  Example code:


from __future__ import with_statement

db_lock = threading.RLock()

# in code that will use the database:

    with db_lock:
        row = MyModel.get(1)



It is easy with this modified Autumn to use as many SQLite database
files as you wish, with as many threads as you wish, and without ever
getting any "database is busy" exceptions.

Ideally, Autumn could be modified in future to have optional lock support
built-in.  Multithreaded SQLite users could enable the lock, and not have
to explicitly get and release the lock; other users would not enable it.
But it's not hard to add the "with db_lock:" code now.

P.S. The Storm ORM basically cannot be used for multi-threaded SQLite.
Storm requires one store per database; SQLite requires one connection
per thread.  These requirements conflict, so Storm basically requires
that you do all your database activity in a single thread.  Autumn is
thus a much better choice for multi-threaded SQLite.
