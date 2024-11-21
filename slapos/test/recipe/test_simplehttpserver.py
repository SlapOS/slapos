import errno
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
    self.process = None

  def setUpRecipe(self, opt=()):
    host, port = os.environ['SLAPOS_TEST_IPV4'], 9999
    options = {
        'base-path': self.base_path,
        'host': host,
        'port': port,
        'log-file': os.path.join(self.install_dir, 'simplehttpserver.log'),
        'wrapper': self.wrapper,
    }
    options.update(opt)
    self.recipe = makeRecipe(
        simplehttpserver.Recipe,
        options=options,
        name='simplehttpserver',
    )
    self.server_url = 'http://{host}:{port}'.format(host=host, port=port)

  def startServer(self):
    self.assertEqual(self.recipe.install(), self.wrapper)
    self.process = subprocess.Popen(
        self.wrapper,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    root_path = self.recipe.options.get('root-path')
    if root_path:
      root_relpath = os.path.relpath(root_path, self.base_path)
      server_ok_url = urlparse.urljoin(self.server_url, root_relpath)
    else:
      server_ok_url = self.server_url
    for i in range(16):
      try:
        resp = requests.get(server_ok_url)
        break
      except requests.exceptions.ConnectionError:
        time.sleep(i * .1)
    else:
      self.fail(
          'server did not start.\nout: %s error: %s' % self.process.communicate())
    self.assertIn('Directory listing for /', resp.text)
    return self.server_url

  def tearDown(self):
    if self.process:
      self.process.terminate()
      self.process.wait()
      self.process.communicate() # close pipes
      self.process = None

  def write_should_fail(self, url, hack_path, hack_content):
    # post with multipart/form-data encoding
    resp = requests.post(
        url,
        files={
            'path': hack_path,
            'content': hack_content,
        },
    )
    # First check for actual access to forbidden files
    try:
      with open(hack_path) as f:
        content = f.read()
      if content == hack_content:
        self.fail(content)
      self.fail("%s should not have been created" % hack_path)
    except IOError as e:
      if e.errno != errno.ENOENT:
        raise
    # Now check for proper response
    self.assertEqual(resp.status_code, requests.codes.forbidden)
    self.assertEqual(resp.text, 'Forbidden')

  def test_write_outside_base_path_should_fail(self):
    self.setUpRecipe({'allow-write': 'true'})
    server_base_url = self.startServer()

    # A file outside the server's root directory
    hack_path = os.path.join(self.install_dir, 'forbidden', 'hack.txt')
    hack_content = "You should not be able to write to hack.txt"

    self.write_should_fail(server_base_url, hack_path, hack_content)
    self.assertFalse(os.path.exists(os.path.dirname(hack_path)))

  def test_write(self):
    self.setUpRecipe({'allow-write': 'true'})
    server_base_url = self.startServer()

    # post with multipart/form-data encoding
    resp = requests.post(
        server_base_url,
        files={
            'path': 'hello-form-data.txt',
            'content': 'hello-form-data',
        },
    )
    self.assertEqual(resp.status_code, requests.codes.ok)
    self.assertEqual(resp.text, 'Content written to hello-form-data.txt')
    with open(
        os.path.join(self.base_path, 'hello-form-data.txt')) as f:
      self.assertEqual(f.read(), 'hello-form-data')

    self.assertIn('hello-form-data.txt', requests.get(server_base_url).text)
    self.assertEqual(
        requests.get(server_base_url + '/hello-form-data.txt').text, 'hello-form-data')

    # post as application/x-www-form-urlencoded
    resp = requests.post(
        server_base_url,
        data={
            'path': 'hello-form-urlencoded.txt',
            'content': 'hello-form-urlencoded',
        },
    )
    self.assertEqual(resp.status_code, requests.codes.ok)
    with open(
        os.path.join(self.base_path, 'hello-form-urlencoded.txt')) as f:
      self.assertEqual(f.read(), 'hello-form-urlencoded')

    self.assertIn('hello-form-urlencoded.txt', requests.get(server_base_url).text)
    self.assertEqual(resp.text, 'Content written to hello-form-urlencoded.txt')
    self.assertEqual(
        requests.get(server_base_url + '/hello-form-urlencoded.txt').text, 'hello-form-urlencoded')

    # incorrect paths are refused
    for path in '/hello.txt', '../hello.txt':
      resp = requests.post(
          server_base_url,
          files={
              'path': path,
              'content': b'hello',
          },
      )
      self.assertEqual(resp.status_code, requests.codes.forbidden)

  def test_readonly(self):
    self.setUpRecipe()

    indexpath = os.path.join(self.base_path, 'index.txt')
    indexcontent = "This file is served statically and readonly"
    with open(indexpath, 'w') as f:
      f.write(indexcontent)

    server_base_url = self.startServer()
    indexurl = os.path.join(server_base_url, 'index.txt')

    resp = requests.get(indexurl)
    self.assertEqual(resp.status_code, requests.codes.ok)
    self.assertEqual(resp.text, indexcontent)

    resp = requests.post(
        server_base_url,
        files={
            'path': 'index.txt',
            'content': 'Not readonly after all',
        },
    )
    self.assertEqual(resp.status_code, requests.codes.forbidden)
    with open(indexpath) as f:
      self.assertEqual(f.read(), indexcontent)
