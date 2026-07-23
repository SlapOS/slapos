# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2026 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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
"""Assure a rapid-cdn cluster can mix software releases across frontend nodes.

Bump the pinned OLD tag as releases advance (same convention as
``software/theia/test/upgrade_tests.py``).
"""

import glob
import http.client
import json
import os
import subprocess
import sys

from slapos.grid.utils import md5digest
from slapos.testing.testcase import installSoftwareUrlList

sys.path.insert(0, os.path.abspath(
  os.path.join(os.path.dirname(__file__), os.pardir, 'test')))

import test
from test import fakeHTTPSResult


OLD_SOFTWARE_RELEASE_URL = (
  'https://lab.nexedi.com/nexedi/slapos/raw/1.0.469'
  '/software/rapid-cdn/software.cfg')

# Hotfix specific to 1.0.469, which was before this mix-sr test
PATCH_FILENAME = 'rapid-cdn-1.0.469-relax-frontend-schema.patch'
_PATCH_PATH = os.path.join(os.path.dirname(__file__), PATCH_FILENAME)


def setUpModule():
  installSoftwareUrlList(
    test.SlapOSInstanceTestCase,
    [
      test.SlapOSInstanceTestCase.getSoftwareURL(),
      OLD_SOFTWARE_RELEASE_URL,
    ],
    debug=test.SlapOSInstanceTestCase._debug,
  )


class TestMixedFrontendSoftwareRelease(
    test.SlaveHttpFrontendTestCase, test.ReplicateSlaveMixin):

  old_software_release_url = OLD_SOFTWARE_RELEASE_URL
  instance_parameter_dict = {
    'domain': 'example.com',
    'port': test.HTTPS_PORT,
    'plain_http_port': test.HTTP_PORT,
    'kedifa_port': test.KEDIFA_PORT,
    'caucase_port': test.CAUCASE_PORT,
  }

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      '_': json.dumps(cls.instance_parameter_dict)
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'mixed': {
        'url': cls.backend_url,
      },
    }

  def _hotfixCompiledOldSoftwareRelease(self):
    software_dir = os.path.join(
      self.slap.software_directory, md5digest(self.old_software_release_url))
    schema_list = glob.glob(
      os.path.join(software_dir, '**', 'instance-frontend-input-schema.json'),
      recursive=True)
    self.assertEqual(
      1, len(schema_list),
      'expected one frontend input schema under %s, found %r'
      % (software_dir, schema_list))
    schema = schema_list[0]
    with open(schema) as fh:
      if '"additionalProperties": true' in fh.read():
        return  # already hotfixed: the software directory is reused across runs
    subprocess.check_call(['patch', schema, '-i', _PATCH_PATH])

  def _requestMixedCluster(self, frontend_1_state, frontend_2_state):
    self.instance_parameter_dict.update({
      '-frontend-quantity': 2,
      '-sla-2-computer_guid': self.slap._computer_id,
      '-frontend-2-software-release-url': self.old_software_release_url,
      '-frontend-1-state': frontend_1_state,
      '-frontend-2-state': frontend_2_state,
    })
    self.updateDefaultInstanceParameterDict(self.instance_parameter_dict)
    self.requestDefaultInstance()
    self.requestSlaves()

  def _getPartitionSoftwareUrlDict(self):
    computer = self.slap._slap.registerComputer('local')
    partition_software_url_dict = {}
    for partition in computer.getComputerPartitionList():
      if partition.getState() == 'destroyed':
        continue
      try:
        instance_title = partition.getInstanceParameterDict()['instance_title']
        partition_software_url_dict[instance_title] = \
          partition.getSoftwareRelease().getURI()
      except Exception:
        # partitions not (yet) allocated to a software release
        continue
    return partition_software_url_dict

  def _assertControlPlaneRunsNewSoftwareRelease(self):
    partition_software_url_dict = self._getPartitionSoftwareUrlDict()
    new_software_url = self.getSoftwareURL()
    for instance_title in (
        'testing partition 0',  # the root / master partition
        'caddy-frontend-1', 'kedifa', 'error-page-manager'):
      self.assertEqual(
        new_software_url,
        partition_software_url_dict.get(instance_title),
        '%s must run the NEW software release' % (instance_title,))
    self.assertEqual(
      self.old_software_release_url,
      partition_software_url_dict.get('caddy-frontend-2'),
      'caddy-frontend-2 must run the OLD software release')

  def _frontendHaproxyCfgList(self):
    return glob.glob(
      os.path.join(self.instance_path, '*', 'etc', 'frontend-haproxy.cfg'))

  def _assertLiveAccess(self, domain):
    self.waitForSlave()
    result = fakeHTTPSResult(domain, 'test-path')
    self.assertEqual(http.client.OK, result.status_code)
    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_mixed_software_release(self):
    self._hotfixCompiledOldSoftwareRelease()

    ipv6_collision = not self.frontends1And2HaveDifferentIPv6()

    self._requestMixedCluster('stopped', 'started')
    try:
      self.slap.waitForInstance(self.instance_max_retry)
    except Exception:
      if ipv6_collision:
        raise

    self._assertControlPlaneRunsNewSoftwareRelease()

    frontend_haproxy_cfg_list = self._frontendHaproxyCfgList()
    self.assertEqual(2, len(frontend_haproxy_cfg_list))
    for frontend_haproxy_cfg in frontend_haproxy_cfg_list:
      with open(frontend_haproxy_cfg) as fh:
        self.assertIn('backend _mixed-http', fh.read())

    self.updateSlaveConnectionParameterDictDict()
    domain = self.parseSlaveParameterDict('mixed')['domain']
    self._assertLiveAccess(domain)

    self._requestMixedCluster('started', 'stopped')
    for _ in range(3):
      try:
        self.slap.waitForInstance(self.instance_max_retry)
      except Exception:
        if ipv6_collision:
          raise
    self._assertLiveAccess(domain)
