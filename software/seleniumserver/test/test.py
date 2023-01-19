##############################################################################
#
# Copyright (c) 2018 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import cgi
import json
import multiprocessing
import os
import tempfile
import unittest
import urllib.parse
import base64
import hashlib
import logging
import contextlib
from http.server import BaseHTTPRequestHandler

from io import BytesIO

import paramiko
import requests
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import urllib3

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.testing.utils import findFreeTCPPort, ImageComparisonTestCase, ManagedHTTPServer

setUpModule, SeleniumServerTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))



class WebServer(ManagedHTTPServer):
  class RequestHandler(BaseHTTPRequestHandler):
    """Request handler for our test server.

    The implemented server is:
      - submit q and you'll get a page with q as title
      - upload a file and the file content will be displayed in div.uploadedfile
    """
    def do_GET(self):
      self.send_response(200)
      self.end_headers()
      self.wfile.write(
          b'''
        <html>
          <title>Test page</title>
          <body>
            <style> p { font-family: Arial; } </style>
            <form action="/" method="POST" enctype="multipart/form-data">
              <input name="q" type="text"></input>
              <input name="f" type="file" ></input>
              <input type="submit" value="I'm feeling lucky"></input>
            </form>
            <p>the quick brown fox jumps over the lazy dog</p>
          </body>
        </html>''')

    def do_POST(self):
      form = cgi.FieldStorage(
          fp=self.rfile,
          headers=self.headers,
          environ={
              'REQUEST_METHOD': 'POST',
              'CONTENT_TYPE': self.headers['Content-Type'],
          })
      self.send_response(200)
      self.end_headers()
      file_data = 'no file'
      if 'f' in form:
        file_data = form['f'].file.read().decode()
      self.wfile.write(
          ('''
        <html>
          <title>%s</title>
          <div>%s</div>
        </html>
      ''' % (form['q'].value, file_data)).encode())

    log_message = logging.getLogger(__name__ + '.WebServer').info


class WebServerMixin(object):
  """Mixin class which provides a simple web server reachable at self.server_url
  """
  def setUp(self):
    self.server_url = self.getManagedResource('web_server', WebServer).url


class BrowserCompatibilityMixin(WebServerMixin):
  """Mixin class to run validation tests on a specific browser
  """
  desired_capabilities = NotImplemented
  user_agent = NotImplemented

  def setUp(self):
    super(BrowserCompatibilityMixin, self).setUp()
    self.driver = webdriver.Remote(
        command_executor=self.computer_partition.getConnectionParameterDict()
        ['backend-url'],
        desired_capabilities=self.desired_capabilities)

  def tearDown(self):
    self.driver.quit()
    super(BrowserCompatibilityMixin, self).tearDown()

  def test_user_agent(self):
    self.assertIn(
        self.user_agent,
        self.driver.execute_script('return navigator.userAgent'))

  def test_simple_submit_scenario(self):
    self.driver.get(self.server_url)
    input_element = WebDriverWait(self.driver, 3).until(
        EC.visibility_of_element_located((By.NAME, 'q')))
    input_element.send_keys(self.id())
    input_element.submit()
    WebDriverWait(self.driver, 3).until(EC.title_is(self.id()))

  def test_upload_file(self):
    f = tempfile.NamedTemporaryFile(delete=False, mode='w')
    f.write(self.id())
    f.close()
    self.addCleanup(lambda: os.remove(f.name))

    self.driver.get(self.server_url)
    self.driver.find_element_by_xpath('//input[@name="f"]').send_keys(f.name)
    self.driver.find_element_by_xpath('//input[@type="submit"]').click()

    self.assertEqual(self.id(), self.driver.find_element_by_xpath('//div').text)

  def test_screenshot(self):
    self.driver.get(self.server_url)
    screenshot = Image.open(BytesIO(self.driver.get_screenshot_as_png()))
    reference_filename = os.path.join(
        os.path.dirname(__file__), "data",
        self.id() + ".png")

    # save the screenshot somewhere in a path that will be in snapshot folder.
    # XXX we could use a better folder name ...
    screenshot.save(
        os.path.join(self.slap.instance_directory, 'etc',
                     self.id() + ".png"))

    reference = Image.open(reference_filename)
    self.assertImagesSame(screenshot, reference)

  def test_window_and_screen_size(self):
    size = json.loads(
        self.driver.execute_script(
            '''
      return JSON.stringify({
        'screen.width': window.screen.width,
        'screen.height': window.screen.height,
        'screen.pixelDepth': window.screen.pixelDepth,
        'innerWidth': window.innerWidth,
        'innerHeight': window.innerHeight
      })'''))
    # Xvfb is configured like this
    self.assertEqual(1024, size['screen.width'])
    self.assertEqual(768, size['screen.height'])
    self.assertEqual(24, size['screen.pixelDepth'])

    # window size must not be 0 (wrong firefox integration report this)
    self.assertGreater(size['innerWidth'], 0)
    self.assertGreater(size['innerHeight'], 0)

  def test_resize_window(self):
    self.driver.set_window_size(800, 900)
    size = json.loads(
        self.driver.execute_script(
            '''
      return JSON.stringify({
        'outerWidth': window.outerWidth,
        'outerHeight': window.outerHeight
        })'''))
    self.assertEqual(800, size['outerWidth'])
    self.assertEqual(900, size['outerHeight'])

  def test_multiple_clients(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    webdriver_url = parameter_dict['backend-url']

    queue = multiprocessing.Queue()

    def _test(q, server_url):
      driver = webdriver.Remote(
          command_executor=webdriver_url,
          desired_capabilities=self.desired_capabilities)
      try:
        driver.get(server_url)
        q.put(driver.title == 'Test page')
      finally:
        driver.quit()

    nb_workers = 10
    workers = []
    for _ in range(nb_workers):
      worker = multiprocessing.Process(
          target=_test, args=(queue, self.server_url))

      worker.start()
      workers.append(worker)
    del worker  # pylint
    _ = [worker.join(timeout=30) for worker in workers]

    # terminate workers if they are still alive after 30 seconds
    _ = [worker.terminate() for worker in workers if worker.is_alive()]
    _ = [worker.join() for worker in workers]

    del _  # pylint
    self.assertEqual(
        [True] * nb_workers, [queue.get() for _ in range(nb_workers)])


class TestBrowserSelection(WebServerMixin, SeleniumServerTestCase):
  """Test browser can be selected by `desiredCapabilities``
  """
  def test_chrome(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    webdriver_url = parameter_dict['backend-url']

    driver = webdriver.Remote(
        command_executor=webdriver_url,
        desired_capabilities=DesiredCapabilities.CHROME)

    driver.get(self.server_url)
    self.assertEqual('Test page', driver.title)

    self.assertIn('Chrome', driver.execute_script('return navigator.userAgent'))
    self.assertNotIn(
        'Firefox', driver.execute_script('return navigator.userAgent'))
    driver.quit()

  def test_firefox(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    webdriver_url = parameter_dict['backend-url']

    driver = webdriver.Remote(
        command_executor=webdriver_url,
        desired_capabilities=DesiredCapabilities.FIREFOX)

    driver.get(self.server_url)
    self.assertEqual('Test page', driver.title)

    self.assertIn(
        'Firefox', driver.execute_script('return navigator.userAgent'))
    driver.quit()

  def test_firefox_desired_version(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    webdriver_url = parameter_dict['backend-url']

    desired_capabilities = DesiredCapabilities.FIREFOX.copy()
    desired_capabilities['version'] = '60.0.2esr'
    driver = webdriver.Remote(
        command_executor=webdriver_url,
        desired_capabilities=desired_capabilities)
    self.assertIn(
        'Gecko/20100101 Firefox/60.0',
        driver.execute_script('return navigator.userAgent'))
    driver.quit()
    desired_capabilities['version'] = '52.9.0esr'
    driver = webdriver.Remote(
        command_executor=webdriver_url,
        desired_capabilities=desired_capabilities)
    self.assertIn(
        'Gecko/20100101 Firefox/52.0',
        driver.execute_script('return navigator.userAgent'))
    driver.quit()


class TestFrontend(WebServerMixin, SeleniumServerTestCase):
  """Test hub's https frontend.
  """
  def test_admin(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    admin_url = parameter_dict['admin-url']

    parsed = urllib.parse.urlparse(admin_url)
    self.assertEqual('admin', parsed.username)
    self.assertTrue(parsed.password)
    self.assertEqual(
      requests.get(
        parsed._replace(netloc=f"[{parsed.hostname}]:{parsed.port}").geturl(),
        verify=False).status_code,
      requests.codes.unauthorized
    )

    self.assertIn('Grid Console', requests.get(admin_url, verify=False).text)

  def test_browser_use_hub(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    webdriver_url = parameter_dict['url']
    parsed = urllib.parse.urlparse(webdriver_url)
    self.assertEqual('selenium', parsed.username)
    self.assertTrue(parsed.password)
    self.assertEqual(
      requests.get(
        parsed._replace(netloc=f"[{parsed.hostname}]:{parsed.port}").geturl(),
        verify=False).status_code,
      requests.codes.unauthorized
    )

    # XXX we are using a self signed certificate, but selenium 3.141.0 does
    # not expose API to ignore certificate verification
    executor = RemoteConnection(webdriver_url, keep_alive=True)
    executor._conn = urllib3.PoolManager(cert_reqs='CERT_NONE', ca_certs=None)

    driver = webdriver.Remote(
        command_executor=executor,
        desired_capabilities=DesiredCapabilities.CHROME)

    driver.get(self.server_url)
    self.assertEqual('Test page', driver.title)
    driver.quit()


class TestSSHServer(SeleniumServerTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    cls.ssh_key = paramiko.ECDSAKey.generate(bits=384)
    return {'ssh-authorized-key': 'ecdsa-sha2-nistp384 {}'.format(cls.ssh_key.get_base64())}

  def test_connect(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    ssh_url = parameter_dict['ssh-url']
    parsed = urllib.parse.urlparse(ssh_url)
    self.assertEqual('ssh', parsed.scheme)

    client = paramiko.SSHClient()

    class TestKeyPolicy(object):
      """Accept server key and keep it in self.key for inspection
      """
      def missing_host_key(self, client, hostname, key):
        self.key = key

    key_policy = TestKeyPolicy()
    client.set_missing_host_key_policy(key_policy)

    with contextlib.closing(client):
      client.connect(
          username=urllib.parse.urlparse(ssh_url).username,
          hostname=urllib.parse.urlparse(ssh_url).hostname,
          port=urllib.parse.urlparse(ssh_url).port,
          pkey=self.ssh_key,
      )

      # Check fingerprint from server matches the published one.
      # The publish format is the raw output of ssh-keygen and is something like this:
      #   521 SHA256:9aZruv3LmFizzueIFdkd78eGtzghDoPSCBXFkkrHqXE user@hostname (ECDSA)
      # we only want to parse SHA256:9aZruv3LmFizzueIFdkd78eGtzghDoPSCBXFkkrHqXE
      _, fingerprint_string, _, key_type = parameter_dict[
          'ssh-fingerprint'].split()
      self.assertEqual(key_type, '(ECDSA)')

      fingerprint_algorithm, fingerprint = fingerprint_string.split(':', 1)
      self.assertEqual(fingerprint_algorithm, 'SHA256')
      # Paramiko does not allow to get the fingerprint as SHA256 easily yet
      # https://github.com/paramiko/paramiko/pull/1103
      self.assertEqual(
          fingerprint.encode(),
          # XXX with sha256, we need to remove that trailing =
          base64.b64encode(
              hashlib.new(fingerprint_algorithm,
                          key_policy.key.asbytes()).digest())[:-1])

      channel = client.invoke_shell()
      channel.settimeout(30)
      received = b''
      while True:
        r = channel.recv(1024)
        if not r:
          break
        received += r
        if b'Selenium Server.' in received:
          break
      self.assertIn(b"Welcome to SlapOS Selenium Server.", received)


class TestFirefox60(
    BrowserCompatibilityMixin,
    SeleniumServerTestCase,
    ImageComparisonTestCase,
):
  desired_capabilities = dict(DesiredCapabilities.FIREFOX, version='60.0.2esr')
  user_agent = 'Gecko/20100101 Firefox/60.0'


class TestFirefox68(
    BrowserCompatibilityMixin,
    SeleniumServerTestCase,
    ImageComparisonTestCase,
):
  desired_capabilities = dict(DesiredCapabilities.FIREFOX, version='68.0.2esr')
  user_agent = 'Gecko/20100101 Firefox/68.0'


class TestFirefox78(
    BrowserCompatibilityMixin,
    SeleniumServerTestCase,
    ImageComparisonTestCase,
):
  desired_capabilities = dict(DesiredCapabilities.FIREFOX, version='78.1.0esr')
  user_agent = 'Gecko/20100101 Firefox/78.0'


class TestFirefox115(
    BrowserCompatibilityMixin,
    SeleniumServerTestCase,
    ImageComparisonTestCase,
):
  desired_capabilities = dict(DesiredCapabilities.FIREFOX, version='115.3.1esr')
  user_agent = 'Gecko/20100101 Firefox/115.0'

  # resizing window does not work, but we don't really depend on it
  @unittest.expectedFailure
  def test_resize_window(self):
    super().test_resize_window()


class TestChrome69(
    BrowserCompatibilityMixin,
    SeleniumServerTestCase,
    ImageComparisonTestCase,
):
  desired_capabilities = dict(DesiredCapabilities.CHROME, version='69.0.3497.0')
  user_agent = 'Chrome/69.0.3497.0'


class TestChrome91(
    BrowserCompatibilityMixin,
    SeleniumServerTestCase,
    ImageComparisonTestCase,
):
  desired_capabilities = dict(DesiredCapabilities.CHROME, version='91.0.4472.114')
  user_agent = 'Chrome/91.0.4472.0'
