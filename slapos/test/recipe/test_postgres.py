import os
import shutil
import tempfile
import textwrap
import unittest

import zc.buildout.testing


class PostgresTest(unittest.TestCase):

  def setUp(self):
    self.buildout = buildout = zc.buildout.testing.Buildout()
    self.pgdata_directory = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.pgdata_directory)
    self.services_directory = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.services_directory)
    self.software_bin_dir = tempfile.mkdtemp()

    # create fake programs
    self.addCleanup(shutil.rmtree, self.software_bin_dir)
    initdb = os.path.join(self.software_bin_dir, 'initdb')
    with open(initdb, 'w') as f:
      f.write(textwrap.dedent('''\
        #!/bin/sh
        if [ ! "$1" = -D ]
        then
          echo Wrong arguments, expecting -D datadir ... got: "$@"
          exit 1
        fi
        mkdir "$2"
      '''))
    os.chmod(initdb, 0o775)

    postgres = os.path.join(self.software_bin_dir, 'postgres')
    with open(postgres, 'w') as f:
      f.write(textwrap.dedent('''\
        #!/bin/sh
        exec cat > %s/postgres.sql
      ''') % os.path.join(self.pgdata_directory, 'pgdata'))
    os.chmod(postgres, 0o775)

    psql = os.path.join(self.software_bin_dir, 'psql')
    with open(psql, 'w') as f:
      f.write(textwrap.dedent('''\
        #!/bin/sh -xe
        exec cat > %s/psql.sql
      ''') % os.path.join(self.pgdata_directory, 'pgdata'))
    os.chmod(psql, 0o775)

    buildout['postgres'] = {
      'bin': self.software_bin_dir,
      'dbname': 'dbname',
      'ipv4': '127.0.0.1',
      'ipv6': '::1',
      'port': '5443',
      'pgdata-directory': os.path.join(self.pgdata_directory, 'pgdata'),
      'services': self.services_directory,
      'superuser': 'superuser',
      'password': 'secret',
    }
    from slapos.recipe import postgres
    self.recipe = postgres.Recipe(
        buildout,
        'postgres',
        buildout['postgres'])

  def test_options(self):
    self.assertEqual(
        'postgresql://superuser:secret@[::1]:5443/dbname',
        self.buildout['postgres']['url'])

  def test_install(self):
    installed = self.recipe.install()

    pgdata_directory = os.path.join(self.pgdata_directory, 'pgdata')
    self.assertIn('postgresql.conf', os.listdir(pgdata_directory))
    self.assertIn('pg_hba.conf', os.listdir(pgdata_directory))
    self.assertIn('postgres-start', os.listdir(self.services_directory))

    with open(os.path.join(pgdata_directory, 'postgres.sql')) as f:
      self.assertEqual(
          f.read(),
          'ALTER USER "superuser" ENCRYPTED PASSWORD \'md53992d9240b8f81ebd7e1f9a9fafeb06b\'\n'
      )
    self.assertEqual(
        sorted(installed),
        sorted([
            os.path.join(pgdata_directory, 'postgresql.conf'),
            os.path.join(pgdata_directory, 'pg_hba.conf'),
            os.path.join(self.services_directory, 'postgres-start')]))


  def test_update_password(self):
    self.recipe.install()

    # simulate a running server
    pgdata_directory = os.path.join(self.pgdata_directory, 'pgdata')
    open(os.path.join(pgdata_directory, 'postmaster.pid'), 'w').close()

    self.recipe.options['password'] = 'new'
    self.recipe.install()

    with open(os.path.join(pgdata_directory, 'psql.sql')) as f:
      self.assertEqual(
          f.read(),
          'ALTER USER "superuser" ENCRYPTED PASSWORD \'md5442311d398491b7f6b512757b51ae9d8\'\n'
      )
