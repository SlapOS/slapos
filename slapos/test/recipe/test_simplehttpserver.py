import os
import shutil
import tempfile
import unittest
import subprocess
import time

from six.moves.urllib import parse as urlparse
import requests

from slapos.recipe import simplehttpserver
from slapos.test.utils import makeRecipe


class SimpleHTTPServerTest(unittest.TestCase):
  process = None

  def setUp(self):
    self.base_path = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.base_path)
    self.install_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.install_dir)
    self.wrapper = os.path.join(self.install_dir, 'server')
    host, port = os.environ['SLAPOS_TEST_IPV4'], 9999
    self.server_url = 'http://{host}:{port}'.format(host=host, port=port)
    self.recipe = makeRecipe(
        simplehttpserver.Recipe,
        options={
            'base-path': self.base_path,
            'host': host,
            'port': port,
            'log-file': os.path.join(self.install_dir, 'simplehttpserver.log'),
            'wrapper': self.wrapper,
        },
        name='simplehttpserver',
    )

  def tearDown(self):
    if self.process:
      self.process.terminate()
      self.process.wait()

  def test_options(self):
    self.assertNotEqual(self.recipe.options['path'], '')
    self.assertEqual(
        self.recipe.options['root-dir'],
        os.path.join(
            self.base_path,
            self.recipe.options['path'],
        ))

  def test_install(self):
    self.assertEqual(self.recipe.install(), [self.wrapper])
    self.process = subprocess.Popen(
        self.wrapper,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    server_base_url = urlparse.urljoin(
        self.server_url,
        self.recipe.options['path'],
    )
    for _ in range(10):
      try:
        resp = requests.get(server_base_url)
        break
      except requests.exceptions.ConnectionError:
        time.sleep(.1)
    else:
      self.fail('server did not start')
    self.assertIn('Directory listing for /', resp.text)

    resp = requests.post(
        server_base_url,
        files={
            'path': 'hello.txt',
            'content': b'hello',
        },
    )
    self.assertEqual(resp.status_code, requests.codes.ok)
    with open(
        os.path.join(self.base_path, self.recipe.options['path'],
                     'hello.txt')) as f:
      self.assertEqual(f.read(), 'hello')

    self.assertIn('hello.txt', requests.get(server_base_url).text)
    self.assertEqual(
        requests.get(server_base_url + '/hello.txt').text, 'hello')
