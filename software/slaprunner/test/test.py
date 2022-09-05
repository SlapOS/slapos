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

import os
import unittest
import paramiko
import contextlib
import base64
import hashlib
import subprocess
import json
import time

from urllib.parse import urlparse
from urllib.parse import quote
from urllib.parse import urljoin
from configparser import ConfigParser
import requests

from slapos.recipe.librecipe import generateHashFromFiles
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.util import bytes2str

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))

class SlaprunnerTestCase(SlapOSInstanceTestCase):
  # Slaprunner uses unix sockets, so it needs short paths.
  __partition_reference__ = 's'

  def _openSoftwareRelease(self, software_release="erp5testnode/testsuite/dummy"):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    url = "%s/setCurrentProject" % parameter_dict['url']

    data = {
      "path": "workspace/slapos/software/%s" % software_release,
    }
    resp = self._postToSlaprunner(url, data)
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertNotEqual(json.loads(resp.text)['code'], 0,
       'Unexpecting result in call to setCurrentProject: %s' % resp.text)

  def _buildSoftwareRelease(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    url = "%s/runSoftwareProfile" % parameter_dict['url']
    resp = self._postToSlaprunner(url, {})
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertEqual(json.loads(resp.text)['result'], True,
       'Unexpecting result in call to runSoftwareProfile: %s' % resp.text)

  def _deployInstance(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    url = "%s/runInstanceProfile" % parameter_dict['url']
    resp = self._postToSlaprunner(url, {})
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertEqual(json.loads(resp.text)['result'], True,
       'Unexpecting result in call to runSoftwareProfile: %s' % resp.text)

  def _gitClone(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    url = "%s/cloneRepository" % parameter_dict['url']

    data = {
      "repo": "https://lab.nexedi.com/nexedi/slapos.git",
      "name": "workspace/slapos",
      "email": "slapos@slapos.org",
      "user": "slapos"
    }
    resp = self._postToSlaprunner(url, data)
    d = json.loads(resp.text)
    if d['code'] == 0:
      return "OK"

  def _isSoftwareReleaseReady(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    url = "%s/isSRReady" % parameter_dict['url']
    resp = self._getFromSlaprunner(url)
    if requests.codes.ok != resp.status_code:
      return -1
    return resp.text

  def _waitForSoftwareBuild(self, limit=5000):
    status = self._isSoftwareReleaseReady()
    while limit > 0 and status != "1":
      status = self._isSoftwareReleaseReady()
      limit -= 1
      if status == '0':
        self.logger.debug("Software release is Failing to Build. Sleeping...")
      else:
        self.logger.debug('Software is still building. Sleeping...')
      time.sleep(20)

  def _waitForInstanceDeploy(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    url = "%s/slapgridResult" % parameter_dict['url']
    data = {
      "position": 0,
      "log": ""
      }
    while True:
      time.sleep(25)
      resp = self._postToSlaprunner(url, data)
      if requests.codes.ok != resp.status_code:
        continue
      if json.loads(resp.text)["instance"]["state"] is False:
        break
      self.logger.info('Buildout is still running. Sleeping....')
    self.logger.info("Instance has been deployed.")

  def _getFromSlaprunner(self, url):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    return requests.get(
        url,
        verify=False,
        auth=(parameter_dict['init-user'], parameter_dict['init-password']))

  def _postToSlaprunner(self, url, data):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    return requests.post(
        url,
        verify=False,
        data=data,
        auth=(parameter_dict['init-user'], parameter_dict['init-password']))

  def _getFileContent(self, relative_path):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    url = "%s/getFileContent" % parameter_dict['url']

    data = {
      "file": relative_path
    }
    resp = self._postToSlaprunner(url, data)
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertNotEqual(json.loads(resp.text)['code'], 0,
       'Unexpecting result in call to getFileContent: %s' % resp.text)

    return json.loads(resp.text)["result"]

  def _waitForCloneToBeReadyForTakeover(self, scope="runner-1", limit=500):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    takeover_url = parameter_dict["takeover-%s-url" % scope]

    def getTakeoverPageContent():
      resp = requests.get(takeover_url, verify=True)
      self.assertEqual(requests.codes.ok, resp.status_code)
      return resp.text
    takeover_page_content = getTakeoverPageContent()
    while "<b>Last valid backup:</b> No backup downloaded yet, takeover should not happen now." in takeover_page_content:
      time.sleep(10)
      if limit < 0:
        raise Exception("Timeout: No valid Backup")
      takeover_page_content = getTakeoverPageContent()
      limit -= 1

    while "<b>Importer script(s) of backup in progress:</b> True" in takeover_page_content:
      time.sleep(10)
      if limit < 0:
        raise Exception("Timeout: Backup still in progress")
      takeover_page_content = getTakeoverPageContent()
      limit -= 1

  def _doTakeover(self, scope="runner-1"):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    takeover_url = parameter_dict["takeover-%s-url" % scope]
    takeover_password = parameter_dict["takeover-%s-password" % scope]

    resp = requests.get(
      f"{takeover_url}?password={takeover_password}",
      verify=True)
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertNotIn("Error", resp.text,
            "An Error occured: %s" % resp.text)
    self.assertIn("Success", resp.text,
            "An Success not in %s" % resp.text)
    return resp.text

class TestWebRunnerBasicUsage(SlaprunnerTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    return {
        'auto-deploy': 'true',
        'software-root': os.path.join(cls.slap._instance_root, "..", "soft"),
        'buildout-shared-folder': os.path.join(cls.slap._instance_root, "..", "shared"),
        "slapos-reference": 'slaprunner-basic-test-resiliency'
       }

  def test_open_software_release(self):
    self._openSoftwareRelease()

  def test_git_clone(self):
    self._gitClone()

  @unittest.skip('Skip as _getFileContent dont work for now')
  def test_basic_usage(self):
    self._openSoftwareRelease()
    self._buildSoftwareRelease()
    self._waitForSoftwareBuild()
    self._deployInstance()
    self._waitForInstanceDeploy()

    result = self._getFileContent(
      "instance_root/slappart0/var/log/log.log")

    self.assertTrue(result.startswith("Hello"),
      result)

class TestWebRunnerAutorun(SlaprunnerTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    return {
        # Auto deploy is required for the isSRReady works.
        'auto-deploy': 'true',
        'autorun': 'true',
        'software-root': os.path.join(cls.slap._instance_root, "..", "soft"),
        'buildout-shared-folder': os.path.join(cls.slap._instance_root, "..", "shared"),
        'slapos-software': 'software/erp5testnode/testsuite/dummy',
        # XXX HACK!
        "slapos-reference": 'slaprunner-basic-test-resiliency'
       }

  @unittest.skip('Skip as _getFileContent dont work for now')
  def test_basic_usage(self):
    self._openSoftwareRelease()
    self._waitForSoftwareBuild()
    self._waitForSoftwareBuild()
    self._waitForInstanceDeploy()
    self._waitForInstanceDeploy()

    result = self._getFileContent(
      "instance_root/slappart0/var/log/log.log")

    self.assertTrue(result.startswith("Hello"), result)

class TestWeb(SlaprunnerTestCase):
  def test_slaprunner(self):
    # slaprunner main interface is password protected
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    url = parameter_dict['url']
    resp = requests.get(url, verify=False)
    self.assertEqual(requests.codes.unauthorized, resp.status_code)
    resp = requests.get(
        url,
        verify=False,
        auth=(parameter_dict['init-user'], parameter_dict['init-password']))
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertIn('SlapOS', resp.text)

  def test_slaprunner_redirects(self):
    # redirects also work as expected. In this test we visit stopAllPartition
    # which should redirect to inspectInstance
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    url = parameter_dict['url']
    resp = requests.get(
        urljoin(url, '/stopAllPartition'),
        verify=False,
        auth=(parameter_dict['init-user'], parameter_dict['init-password']))
    self.assertEqual(resp.status_code, requests.codes.ok)
    self.assertEqual(resp.url, urljoin(url, '/inspectInstance'))

    # this also works behind a frontend
    resp = requests.get(
        urljoin(url, '/stopAllPartition'),
        verify=False,
        allow_redirects=False,
        headers={'Host': 'example.com:1234'},
        auth=(parameter_dict['init-user'], parameter_dict['init-password']))
    self.assertEqual(resp.status_code, requests.codes.found)
    self.assertEqual(resp.headers['Location'], 'https://example.com:1234/inspectInstance')

  def test_shellinabox(self):
    # shellinabox exists at /shellinabox and is password protected
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    url = urljoin(parameter_dict['url'], '/shellinabox')
    resp = requests.get(url, verify=False)
    self.assertEqual(requests.codes.unauthorized, resp.status_code)
    resp = requests.get(
        url,
        verify=False,
        auth=(parameter_dict['init-user'], parameter_dict['init-password']))
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertIn('ShellInABox', resp.text)
    self.assertNotIn('SlapOS', resp.text)

  def test_public_url(self):
    # ~/srv/runner/public/ is served over http
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    public_url = parameter_dict['public-url']

    hello_file = os.path.join(
        self.computer_partition_root_path,
        'srv',
        'runner',
        'public',
        'hello.html')
    self.addCleanup(os.remove, hello_file)
    with open(hello_file, 'w') as f:
      f.write('<b>Hello</b>')

    index = requests.get(public_url, verify=False)
    self.assertEqual(requests.codes.ok, index.status_code)
    self.assertIn('hello.html', index.text)

    hello = requests.get(urljoin(public_url, 'hello.html'), verify=False)
    self.assertEqual(requests.codes.ok, hello.status_code)
    self.assertIn('<b>Hello</b>', hello.text)


class TestSSH(SlaprunnerTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    cls.ssh_key_list = [paramiko.ECDSAKey.generate(bits=384) for i in range(2)]
    return {
        'user-authorized-key': 'ecdsa-sha2-nistp384 {}\necdsa-sha2-nistp384 {}'.format(
          *[key.get_base64() for key in cls.ssh_key_list]
          )
    }

  def test_connect(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    ssh_url = parameter_dict['ssh-url']
    parsed = urlparse(ssh_url)
    self.assertEqual('ssh', parsed.scheme)

    # username contain a fingerprint (only, so we simplify the parsing)
    #
    # relevant parts of the grammar defined in
    # https://tools.ietf.org/id/draft-salowey-secsh-uri-00.html
    #
    #   ssh-info      =  [ userinfo ] [";" c-param *("," c-param)]
    #   c-param       =  paramname "=" paramvalue
    ssh_info = parsed.username
    username, fingerprint_from_url = ssh_info.split(';fingerprint=')
    client = paramiko.SSHClient()

    self.assertTrue(fingerprint_from_url.startswith('ssh-rsa-'), fingerprint_from_url)
    fingerprint_from_url = fingerprint_from_url[len('ssh-rsa-'):]

    class KeyPolicy:
      """Accept server key and keep it in self.key for inspection
      """
      def missing_host_key(self, client, hostname, key):
        self.key = key

    key_policy = KeyPolicy()
    client.set_missing_host_key_policy(key_policy)

    for ssh_key in self.ssh_key_list:
      with contextlib.closing(client):
        client.connect(
            username=username,
            hostname=parsed.hostname,
            port=parsed.port,
            pkey=ssh_key,
        )
        # Check fingerprint from server matches the published one.
        # Paramiko does not allow to get the fingerprint as SHA256 easily yet
        # https://github.com/paramiko/paramiko/pull/1103
        self.assertEqual(
            fingerprint_from_url,
            quote(
                # base64 encoded fingerprint adds an extra = at the end
                base64.b64encode(
                    hashlib.sha256(key_policy.key.asbytes()).digest())[:-1],
                # also encode /
                safe=''))

        # Check shell is usable
        channel = client.invoke_shell()
        channel.settimeout(30)
        received = ''
        while True:
          r = bytes2str(channel.recv(1024))
          self.logger.debug("received >%s<", r)
          if not r:
            break
          received += r
          if 'slaprunner shell' in received:
            break
        self.assertIn("Welcome to SlapOS slaprunner shell", received)

        # simple commands can also be executed ( this would be like `ssh bash -c 'pwd'` )
        self.assertEqual(
            self.computer_partition_root_path,
            bytes2str(client.exec_command("pwd")[1].read(1000)).strip())


class TestSlapOS(SlaprunnerTestCase):
  def test_slapos_command(self):
    # in ~/bin/slapos there is a wrapper setting configuration to use slapos from
    # the web runner.
    slapos = os.path.join(self.computer_partition_root_path, 'bin', 'slapos')
    # ensure the node is formatted
    subprocess.check_call((slapos, 'node', 'format', '--now'), env={})
    proxy_show_output = subprocess.check_output((slapos, 'proxy', 'show'), env={})
    self.assertIn(b'slaprunner', proxy_show_output)
    # check hateoas cli support
    computer_list_output = subprocess.check_output((slapos, 'computer', 'list'), env={})
    self.assertIn(b'slaprunner', computer_list_output)

  def test_shared_part_list(self):
    # this slapos used shared_part_list
    cfg_parser = ConfigParser()
    with open(os.path.join(self.computer_partition_root_path,
                           'etc',
                           'slapos.cfg')) as f:
      cfg_parser.readfp(f)
    shared_part_list = cfg_parser.get('slapos', 'shared_part_list').splitlines()

    # web runner own shared parts. Note that there is intentionnaly a double
    # slash in this path, because slaprunner has double slash in paths since
    # early releases, including for the path of slapos repository that will be
    # used to develop and install software. If we fix this duplication, then
    # the URL of installed software will be different and it will get a different
    # hash and be reinstalled. To prevent this, we keep that // between srv and runner.
    self.assertEqual(
        '{}/srv//runner//shared'.format(self.computer_partition_root_path.rstrip('/')),
        shared_part_list[-1])

    # shared parts from outer slapos
    outer_shared_part_list = os.getenv('SLAPOS_TEST_SHARED_PART_LIST',
                                       '').split(os.pathsep)
    for outer_shared_part in outer_shared_part_list:
      self.assertIn(outer_shared_part, shared_part_list)


class ServicesTestCase(SlaprunnerTestCase):
  def test_hashes(self):
    hash_files = [
      'software_release/buildout.cfg',
    ]
    expected_process_names = [
      'slaprunner-supervisord-{hash}-on-watch',
      'runner-sshd-{hash}-on-watch',
      'slaprunner-httpd-{hash}-on-watch',
      'gunicorn-{hash}-on-watch',
      'nginx-frontend-{hash}-on-watch',
      'certificate_authority-{hash}-on-watch',
      'shellinaboxd-{hash}-on-watch',
      'supervisord-{hash}-on-watch',
    ]

    with self.slap.instance_supervisor_rpc as supervisor:
      process_names = [
          process['name'] for process in supervisor.getAllProcessInfo()
      ]

    hash_files = [os.path.join(self.computer_partition_root_path, path)
                  for path in hash_files]

    for name in expected_process_names:
      h = generateHashFromFiles(hash_files)
      expected_process_name = name.format(hash=h)

      self.assertIn(expected_process_name, process_names)

class TestCustomFrontend(SlaprunnerTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'custom-frontend-backend-url': 'https://www.erp5.com',
      'custom-frontend-backend-type': 'redirect',
    }

  def test(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    # slapproxy returns the backend URL when requesting a slave frontend
    self.assertEqual(
      parameter_dict['custom-frontend-url'],
      'https://www.erp5.com')

class TestResilientInstance(SlaprunnerTestCase):
  instance_max_retry = 20

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'resilient'

  def test(self):
    # just check that keys returned on requested partition are for resilient
    self.assertSetEqual(
      set(self.computer_partition.getConnectionParameterDict().keys()),
      {
        'backend-url',
        'feed-url-runner-1-pull',
        'feed-url-runner-1-push',
        'init-password',
        'init-user',
        'monitor-base-url',
        'monitor-setup-url',
        'public-url',
        'ssh-command',
        'takeover-runner-1-password',
        'takeover-runner-1-url',
        'url',
        'webdav-url'})

class TestResilientCustomFrontend(TestCustomFrontend):
  instance_max_retry = 20
  @classmethod
  def getInstanceSoftwareType(cls):
    return 'resilient'

class TestResilientWebInstance(TestWeb):
  instance_max_retry = 20
  @classmethod
  def getInstanceSoftwareType(cls):
    return 'resilient'

  def test_public_url(self):
    pass # Disable until we can write on runner0 rather them
         # on root partition

class TestResilientWebrunnerBasicUsage(TestWebRunnerBasicUsage):
  instance_max_retry = 20
  @classmethod
  def getInstanceSoftwareType(cls):
    return 'resilient'


class TestResilientWebrunnerAutorun(TestWebRunnerAutorun):
  instance_max_retry = 20
  @classmethod
  def getInstanceSoftwareType(cls):
    return 'resilient'

class TestResilientDummyInstance(SlaprunnerTestCase):
  instance_max_retry = 20
  @classmethod
  def getInstanceSoftwareType(cls):
    return 'resilient'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
        'resiliency-backup-periodicity': '*/6 * * * *',
        'auto-deploy-instance': 'false',
        'software-root': os.path.join(cls.slap._instance_root, "..", "soft"),
        'buildout-shared-folder': os.path.join(cls.slap._instance_root, "..", "shared"),
        'auto-deploy': 'true',
        # XXX HACK!
        "slapos-reference": 'slaprunner-erp5-resiliency',
        "slapos-httpd-port": '9687'
       }

  @unittest.skip('Skip as _getFileContent dont work for now')
  def test_basic_resilience(self):
    self._openSoftwareRelease()
    self._buildSoftwareRelease()
    self._waitForSoftwareBuild()
    self._deployInstance()
    self._waitForInstanceDeploy()

    result = self._getFileContent(
      "instance_root/slappart0/var/log/log.log")

    self.assertTrue(result.startswith("Hello"), result)

    # We should ensure here that the resilience was indeed
    # Propagates and test succeeded.
    time.sleep(900)

    self._waitForCloneToBeReadyForTakeover()
    self._doTakeover()
    self.slap.waitForInstance(20)

    previous_computer_partition = self.computer_partition
    self.computer_partition = self.requestDefaultInstance()


    result_after = self._getFileContent(
      "instance_root/slappart0/var/log/log.log")

    self.assertTrue(result_after.startswith("Hello"), result_after)

    self.assertIn(result, result_after,
            f"{result} not in {result_after}")

