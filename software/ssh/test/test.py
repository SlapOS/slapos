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


class TestSSH(SlapOSInstanceTestCase):
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
