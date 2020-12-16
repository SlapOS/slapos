import unittest
import tempfile
import shutil
import os.path
import zc.buildout.testing


class PostgresTest(unittest.TestCase):
  def setUp(self):
    self.buildout = buildout = zc.buildout.testing.Buildout()
    self.pgdata_directory = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.pgdata_directory)
    self.services_directory = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.services_directory)
    buildout['postgres'] = {
      'bin': 'software/parts/postgres/bin/',
      'dbname': 'dbname',
      'ipv4': '127.0.0.1',
      'ipv6': '::1',
      'port': '5443',
      'pgdata-directory': self.pgdata_directory,
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

    self.assertIn('postgresql.conf', os.listdir(self.pgdata_directory))
    self.assertIn('pg_hba.conf', os.listdir(self.pgdata_directory))
    self.assertIn('postgres-start', os.listdir(self.services_directory))

    self.assertEqual(
        sorted(installed),
        sorted([
            os.path.join(self.pgdata_directory, 'postgresql.conf'),
            os.path.join(self.pgdata_directory, 'pg_hba.conf'),
            os.path.join(self.services_directory, 'postgres-start')]))
