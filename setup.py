from distutils.core import setup
from autumn import version

version = '.'.join([str(x) for x in version])

setup(name='autumn',
      version=version,
      description="A minimal ORM",
      author="Jared Kuolt",
      author_email="me@superjared.com",
      url="http://autumn-orm.org",
      packages = ['autumn', 'autumn.db', 'autumn.tests'],
      )
