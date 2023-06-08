import os
import shutil
import tempfile
import time
import unittest

try:
  import subprocess32 as subprocess
except ImportError:
  import subprocess

import psycopg2
import zc.buildout.testing


class PostgresTest(unittest.TestCase):
  ipv4 = os.environ['SLAPOS_TEST_IPV4']
  ipv6 = os.environ['SLAPOS_TEST_IPV6']
  port = 5432

  def setUp(self):
    self.buildout = buildout = zc.buildout.testing.Buildout()
    self.pgdata_directory = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.pgdata_directory)
    self.services_directory = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.services_directory)

    self.postgres_bin_directory = os.environ['SLAPOS_TEST_POSTGRESQL_PREFIX'] + '/bin'
    buildout['postgres'] = {
      'bin': self.postgres_bin_directory,
      'dbname': 'dbname',
      'ipv4': self.ipv4,
      'ipv6': self.ipv6,
      'port': self.port,
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

  def start_postgres_server(self):
    server_process = subprocess.Popen(
        [ os.path.join(self.services_directory, 'postgres-start') ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    self.addCleanup(server_process.wait)
    self.addCleanup(server_process.terminate)

    # wait for server to accept connections
    for i in range(10):
      time.sleep(i)
      try:
        psycopg2.connect(self.buildout['postgres']['url']).close()
      except psycopg2.OperationalError as e:
        pass
      else:
        break

  def test_options(self):
    self.assertEqual(
        self.buildout['postgres']['url'],
        'postgresql://superuser:secret@[{self.ipv6}]:{self.port}/dbname'.format(self=self),
    )

  def test_install(self):
    installed = self.recipe.install()

    pgdata_directory = os.path.join(self.pgdata_directory, 'pgdata')
    self.assertIn('postgresql.conf', os.listdir(pgdata_directory))
    self.assertIn('pg_hba.conf', os.listdir(pgdata_directory))
    self.assertIn('postgres-start', os.listdir(self.services_directory))

    self.assertEqual(
        sorted(installed),
        sorted([
            os.path.join(pgdata_directory, 'postgresql.conf'),
            os.path.join(pgdata_directory, 'pg_hba.conf'),
            os.path.join(self.services_directory, 'postgres-start')]))

    self.start_postgres_server()
    with psycopg2.connect(self.buildout['postgres']['url']) as cnx:
      with cnx.cursor() as cursor:
        cursor.execute("SELECT 1+1")
        self.assertEqual(cursor.fetchone(), (2,))
    cnx.close()

  def test_restart_server(self):
    self.recipe.install()
    pgdata_directory = os.path.join(self.pgdata_directory, 'pgdata')
    postmaster_pid_file =os.path.join(pgdata_directory, 'postmaster.pid')
    with open(postmaster_pid_file, 'w') as file:
      file.write('This is some content written to the file.\n')

    self.start_postgres_server()

    self.recipe.install()


  def test_update_password(self):
    self.recipe.install()
    self.start_postgres_server()
    self.recipe.options['password'] = 'new'
    self.recipe.install()

    dsn = self.buildout['postgres']['url']
    with psycopg2.connect(psycopg2.extensions.make_dsn(dsn, password='new')) as cnx:
      with cnx.cursor() as cursor:
        cursor.execute("SELECT 1+1")
        self.assertEqual(cursor.fetchone(), (2,))
    cnx.close()

    # old password can no longer connect
    with self.assertRaisesRegexp(
        psycopg2.OperationalError,
        'password authentication failed'
    ):
      psycopg2.connect(dsn)


class PostgresTestNonStandardPort(PostgresTest):
  port = 5433


class PostgresTestEmptyPort(PostgresTest):
  port = ''
