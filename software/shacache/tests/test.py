##############################################################################
#
# Copyright (c) 2026 Nexedi SA and Contributors. All Rights Reserved.
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

import base64
import contextlib
import hashlib
import http.client
import json
import os
import ssl
import time
import urllib.parse
import xmlrpc.client

import requests
import urllib3

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

UPLOADER_LOGIN = 'networkcache'
UPLOADER_PASSWORD = 'networkcache-password'

# Creates the Web Sites and the uploader user, as described in the README of
# the software release.
SETUP_SCRIPT = '''
portal = context.getPortalObject()
module = portal.web_site_module
for id_, skin in (('shacache', 'SHACACHE'), ('shadir', 'SHADIR')):
  if id_ not in module.objectIds():
    module.newContent(id=id_, portal_type='Web Site',
                      skin_selection_name=skin).publish()
if login not in portal.person_module.objectIds():
  person = portal.person_module.newContent(id=login, portal_type='Person',
                                           first_name=login)
  person.newContent(portal_type='ERP5 Login', reference=login,
                    password=password).validate()
  for group in ('shacache', 'shadir'):
    person.newContent(portal_type='Assignment', group=group).open()
return 'ok'
'''


class ShacacheTestCase(SlapOSInstanceTestCase):
  """Base class: deploy shacache and make it ready to use.

  XML-RPC is enabled on the default family to set up the site.
  """
  zope_parameter_dict = {}

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'family-override': {'default': {'xml-rpc': True}},
      'zope-partition-dict': {'1': cls.zope_parameter_dict},
    })}

  @classmethod
  def getRootPartitionConnectionParameterDict(cls):
    return json.loads(
      cls.computer_partition.getConnectionParameterDict()['_'])

  @classmethod
  def getComputerPartitionPath(cls, partition_reference):
    for computer_partition in cls.slap.computer.getComputerPartitionList():
      if partition_reference == computer_partition.getInstanceParameter(
          'instance_title'):
        return os.path.join(cls.slap._instance_root,
                            computer_partition.getId())
    raise KeyError(partition_reference)

  @classmethod
  def getSiteUrl(cls):
    param_dict = cls.getRootPartitionConnectionParameterDict()
    return urllib.parse.urljoin(
      param_dict['family-default'], param_dict['site-id'] + '/')

  @classmethod
  def getInitUserAuth(cls):
    param_dict = cls.getRootPartitionConnectionParameterDict()
    return param_dict['inituser-login'], param_dict['inituser-password']

  @classmethod
  @contextlib.contextmanager
  def getXMLRPCClient(cls):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    url = urllib.parse.urlparse(cls.getSiteUrl())
    url = url._replace(netloc='%s:%s@%s' % (
      cls.getInitUserAuth() + (url.netloc,))).geturl()
    client = xmlrpc.client.ServerProxy(url, context=ssl_context)
    with client:
      yield client

  @classmethod
  def waitForActivities(cls, timeout=1200):
    """Wait until the site exists and all the activities are done."""
    deadline = time.time() + timeout
    last_result = None
    while time.time() < deadline:
      with cls.getXMLRPCClient() as client:
        try:
          last_result = client.portal_activities.countMessage()
          if last_result == 0:
            return
        except (xmlrpc.client.ProtocolError, xmlrpc.client.Fault,
                http.client.HTTPException, OSError) as e:
          last_result = e
      time.sleep(5)
    raise AssertionError(
      'Timeout waiting for activities, last result: %r' % (last_result,))

  @classmethod
  def _setUpClass(cls):
    super()._setUpClass()
    cls.waitForActivities()

  def readZopeConf(self):
    with open(os.path.join(self.getComputerPartitionPath('zope-1'),
                           'etc', 'zope-0.conf')) as f:
      return f.read()

  def getDosProtection(self):
    conf = self.readZopeConf()
    start = conf.index('<dos_protection>') + len('<dos_protection>')
    return dict(line.split() for line in
                conf[start:conf.index('</dos_protection>')].splitlines()
                if line.strip())


class TestShacache(ShacacheTestCase):
  """Use shacache and shadir like the networkcache clients."""
  __partition_reference__ = 'sc'

  @classmethod
  def _setUpClass(cls):
    super()._setUpClass()
    with cls.getXMLRPCClient() as client:
      custom = client.portal_skins.custom
      try:
        custom.manage_addProduct.PythonScripts.manage_addPythonScript(
          'ShacacheTest_setup')
      except xmlrpc.client.ProtocolError as e:
        if e.errcode != 302:
          raise
      custom.ShacacheTest_setup.ZPythonScriptHTML_editAction(
        '', '', 'login, password', SETUP_SCRIPT)
    resp = requests.post(
      cls.getSiteUrl() + 'portal_skins/custom/ShacacheTest_setup',
      data={'login': UPLOADER_LOGIN, 'password': UPLOADER_PASSWORD},
      auth=cls.getInitUserAuth(), verify=False)
    resp.raise_for_status()
    cls.waitForActivities()
    cls.shacache_url = cls.getSiteUrl() + 'web_site_module/shacache'
    cls.shadir_url = cls.getSiteUrl() + 'web_site_module/shadir'

  def test_business_templates(self):
    with self.getXMLRPCClient() as client:
      title_list = client.portal_templates.getInstalledBusinessTemplateTitleList()
    for title in ('erp5_full_text_mroonga_catalog', 'networkcache_erp5',
                  'erp5_web_shacache', 'erp5_web_shadir'):
      self.assertIn(title, title_list)

  def test_dos_protection(self):
    self.assertEqual(self.getDosProtection(), {
      'form-memory-limit': '10MB',
      'form-disk-limit': '5GB',
    })

  def upload(self, data):
    return requests.post(
      self.shacache_url, data=data,
      headers={'Content-Type': 'application/octet-stream'},
      auth=(UPLOADER_LOGIN, UPLOADER_PASSWORD), verify=False)

  def checkUploadAndDownload(self, data):
    sha512 = hashlib.sha512(data).hexdigest()
    resp = self.upload(data)
    self.assertEqual(resp.status_code, requests.codes.created, resp.text)
    self.assertEqual(resp.text.strip(), sha512)
    # The download finds the file with the catalog.
    self.waitForActivities()
    resp = requests.get(self.shacache_url + '/' + sha512, verify=False)
    self.assertEqual(resp.status_code, requests.codes.ok)
    self.assertEqual(resp.headers['Content-Length'], str(len(data)))
    self.assertEqual(hashlib.sha512(resp.content).hexdigest(), sha512)

  def test_small_file(self):
    self.checkUploadAndDownload(b'small file ' + os.urandom(16))

  def test_big_file(self):
    # Bigger than the 10MB form-memory-limit, and stored in many Pdata.
    self.checkUploadAndDownload(os.urandom(30 * 1024 * 1024))

  def test_upload_without_login(self):
    data = b'anonymous ' + os.urandom(16)
    # ERP5 redirects an anonymous user to the login form.
    resp = requests.post(
      self.shacache_url, data=data,
      headers={'Content-Type': 'application/octet-stream'},
      allow_redirects=False, verify=False)
    self.assertNotEqual(resp.status_code, requests.codes.created)
    self.waitForActivities()
    resp = requests.get(
      self.shacache_url + '/' + hashlib.sha512(data).hexdigest(),
      verify=False)
    self.assertEqual(resp.status_code, requests.codes.not_found)

  def test_download_unknown_file(self):
    resp = requests.get(
      self.shacache_url + '/' + hashlib.sha512(os.urandom(16)).hexdigest(),
      verify=False)
    self.assertEqual(resp.status_code, requests.codes.not_found)

  def test_shadir(self):
    data = b'file of the shadir entry ' + os.urandom(16)
    self.assertEqual(self.upload(data).status_code, requests.codes.created)
    key = 'slapos-sr-test-' + os.urandom(8).hex()
    metadata = json.dumps({
      'sha512': hashlib.sha512(data).hexdigest(),
      'creation_date': '2026-01-01T00:00:00',
      'expiration_date': '2100-01-01T00:00:00',
      'software_url': 'https://lab.nexedi.com/nexedi/slapos/raw/1.0.400/'
                      'software/shacache/software.cfg',
      'os': ['debian', '13', ''],
      'machine': 'x86_64',
    })
    entry = [metadata, base64.b64encode(b'signature').decode()]
    resp = requests.put(
      self.shadir_url + '/' + key, data=json.dumps(entry),
      headers={'Content-Type': 'application/json'},
      auth=(UPLOADER_LOGIN, UPLOADER_PASSWORD), verify=False)
    self.assertEqual(resp.status_code, requests.codes.created, resp.text)
    self.waitForActivities()
    resp = requests.get(self.shadir_url + '/' + key, verify=False)
    self.assertEqual(resp.status_code, requests.codes.ok)
    self.assertEqual(resp.json(), [entry])


class TestFormDiskLimit(ShacacheTestCase):
  """A form-disk-limit in dos-protection has priority over the default of
  the software release, and limits the size of a request body."""
  __partition_reference__ = 'fdl'
  zope_parameter_dict = {'dos-protection': {'form-disk-limit': '1MB'}}

  def test_dos_protection(self):
    self.assertEqual(self.getDosProtection(), {'form-disk-limit': '1MB'})

  def test_request_body_too_big(self):
    resp = requests.post(
      self.getSiteUrl() + 'web_site_module/shacache',
      data=b'x' * (2 * 1024 * 1024),
      headers={'Content-Type': 'application/octet-stream'}, verify=False)
    self.assertEqual(resp.status_code, requests.codes.request_entity_too_large)
