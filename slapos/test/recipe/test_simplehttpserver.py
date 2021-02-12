import os
import shutil
import tempfile
import unittest
import subprocess
import time

from six.moves.urllib import parse as urlparse
import requests
import zc.buildout.testing


class SimpleHTTPServerTest(unittest.TestCase):
  process = None

  def setUp(self):
    self.buildout = buildout = zc.buildout.testing.Buildout()
    self.base_path = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.base_path)
    self.install_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.install_dir)
    self.wrapper = os.path.join(self.install_dir, 'server')
    host, port = os.environ['SLAPOS_TEST_IPV4'], 9999
    buildout['simplehttpserver'] = {
        'base-path': self.base_path,
        'host': host,
        'port': port,
        'log-file': os.path.join(self.install_dir, 'simplehttpserver.log'),
        'wrapper': self.wrapper,
    }
    self.server_url = 'http://{host}:{port}'.format(host=host, port=port)

    from slapos.recipe import simplehttpserver
    self.recipe = simplehttpserver.Recipe(
        buildout,
        'simplehttpserver',
        buildout['simplehttpserver'],
    )

  def tearDown(self):
    if self.process:
      self.process.terminate()
      self.process.wait()

  def test_options(self):
    self.assertNotEqual(self.buildout['simplehttpserver']['path'], '')
    self.assertEqual(
        self.buildout['simplehttpserver']['root-dir'],
        os.path.join(
            self.base_path,
            self.buildout['simplehttpserver']['path'],
        ))

  def test_install(self):
    # XXX: install should return list of path
    self.assertEqual(self.recipe.install(), self.wrapper)
    self.process = subprocess.Popen(self.wrapper)

    server_base_url = urlparse.urljoin(
        self.server_url, self.buildout['simplehttpserver']['path'])
    for _ in range(10):
      try:
        resp = requests.get(server_base_url)
        break
      except requests.exceptions.ConnectionError:
        time.sleep(.1)
    else:
      self.fail('server did not start')
    self.assertIn('<h1>Directory listing for /', resp.text)

    resp = requests.post(
        server_base_url,
        files={
            'path': 'hello.txt',
            'content': b'hello',
        },
    )
    self.assertEqual(resp.status_code, requests.codes.ok)
    with open(
        os.path.join(self.base_path, self.buildout['simplehttpserver']['path'],
                     'hello.txt')) as f:
      self.assertEqual(f.read(), 'hello')

    self.assertIn('hello.txt', requests.get(server_base_url).text)
    self.assertEqual(
        requests.get(server_base_url + '/hello.txt').text, 'hello')
