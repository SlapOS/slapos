import errno
import os
import shutil
import tempfile
import unittest
import socket
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

  def setUpRecipe(self, opt=None):
    opt = opt or {}
    if not 'socketpath' in opt and not 'abstract' in opt:
      opt['host'] = host = os.environ['SLAPOS_TEST_IPV4']
      opt['port'] = port = 9999
      self.server_url = 'http://{host}:{port}'.format(host=host, port=port)
    else:
      self.server_url = None
    options = {
        'base-path': self.base_path,
        'log-file': os.path.join(self.install_dir, 'simplehttpserver.log'),
        'wrapper': self.wrapper,
    }
    options.update(opt)
    self.recipe = makeRecipe(
        simplehttpserver.Recipe,
        options=options,
        name='simplehttpserver',
    )

  def startServer(self):
    self.assertEqual(self.recipe.install(), self.wrapper)
    self.process = subprocess.Popen(
        self.wrapper,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if self.server_url:
      def check_connection():
        resp = requests.get(self.server_url)
        self.assertIn('Directory listing for /', resp.text)
      ConnectionError = requests.exceptions.ConnectionError
      cleanup = None
    else:
      address = self.recipe.options['address']
      s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      def check_connection():
        s.connect(address)
      ConnectionError = socket.error
      cleanup = lambda: s.close()
    try:
      for i in range(16):
        try:
          check_connection()
          break
        except ConnectionError:
          time.sleep(i * .1)
      else:
        # Kill process in case it did not crash
        # otherwise .communicate() may hang forever.
        self.process.terminate()
        self.process.wait()
        self.fail(
          "Server did not start\n"
          "out: %s\n"
          "err: %s"
          % self.process.communicate())
    finally:
      if cleanup:
        cleanup()
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

  def test_socketpath(self):
    socketpath = os.path.join(self.install_dir, 'http.sock')
    self.setUpRecipe({'socketpath': socketpath})
    self.assertEqual(socketpath, self.recipe.options['address'])
    self.startServer()

  def test_abstract(self):
    abstract = os.path.join(self.install_dir, 'abstract.http')
    self.setUpRecipe({'abstract': abstract})
    self.assertEqual('\0' + abstract, self.recipe.options['address'])
    self.startServer()
