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

import ast
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
from test import CurlException, fakeHTTPSResult, subprocess_status_output


OLD_SOFTWARE_RELEASE_URL = (
  'https://lab.nexedi.com/nexedi/slapos/-/raw/1.0.469'
  '/software/rapid-cdn/software.cfg')
NEW_SOFTWARE_RELEASE_URL = test.SlapOSInstanceTestCase.getSoftwareURL()

# Hotfix specific to 1.0.469, which was before this mix-sr test
PATCH_FILENAME = 'rapid-cdn-1.0.469-relax-frontend-schema.patch'
_PATCH_PATH = os.path.join(os.path.dirname(__file__), PATCH_FILENAME)

BASE_INSTANCE_PARAMETER_DICT = {
  'domain': 'example.com',
  'port': test.HTTPS_PORT,
  'plain_http_port': test.HTTP_PORT,
  'kedifa_port': test.KEDIFA_PORT,
  'caucase_port': test.CAUCASE_PORT,
}

UPGRADED_SLAVE_AMOUNT = 10
UPGRADE_INSTANCE_RUN_AMOUNT = 4


def setUpModule():
  installSoftwareUrlList(
    test.SlapOSInstanceTestCase,
    [
      NEW_SOFTWARE_RELEASE_URL,
      OLD_SOFTWARE_RELEASE_URL,
    ],
    debug=test.SlapOSInstanceTestCase._debug,
  )


class OldSoftwareReleaseTestCase(
    test.SlaveHttpFrontendTestCase, test.ReplicateSlaveMixin):

  old_software_release_url = OLD_SOFTWARE_RELEASE_URL

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      '_': json.dumps(cls.instance_parameter_dict)
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


class TestMixedFrontendSoftwareRelease(OldSoftwareReleaseTestCase):
  instance_parameter_dict = dict(BASE_INSTANCE_PARAMETER_DICT)

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'mixed': {
        'url': cls.backend_url,
      },
    }

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


class WholeClusterUpgradeTestCase(OldSoftwareReleaseTestCase):
  # the framework requests the root instance with getSoftwareURL(), so it has
  # to answer with the release the cluster is currently requested on
  current_software_release_url = OLD_SOFTWARE_RELEASE_URL
  # the slave requests carry their own release: upgrading a cluster on a real
  # master does not re-request the shared instances of its users
  slave_software_release_url = OLD_SOFTWARE_RELEASE_URL

  @classmethod
  def getSoftwareURL(cls):
    return cls.current_software_release_url

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'slave-%02i' % (i,): {
        'url': cls.backend_url,
      }
      for i in range(1, UPGRADED_SLAVE_AMOUNT + 1)
    }

  @classmethod
  def requestSlaveInstance(
    cls, partition_reference, partition_parameter_kw, state='started'):
    return cls.slap.request(
      software_release=cls.slave_software_release_url,
      software_type=cls.getInstanceSoftwareType(),
      partition_reference=partition_reference,
      partition_parameter_kw=partition_parameter_kw,
      shared=True,
      state=state,
    )

  @classmethod
  def getPartitionId(cls, instance_name):
    try:
      return super().getPartitionId(instance_name)
    except IndexError:
      if instance_name == 'error-page-manager':
        # setUpClass looks this partition up, and the old release has none
        return super().getPartitionId(cls.default_partition_reference)
      raise

  def _upgradeRootInstance(self):
    type(self).current_software_release_url = NEW_SOFTWARE_RELEASE_URL
    self.slap.request(
      software_release=NEW_SOFTWARE_RELEASE_URL,
      software_type=self.getInstanceSoftwareType(),
      partition_reference=self.default_partition_reference,
      partition_parameter_kw=self._instance_parameter_dict,
      state='started',
    )

  def _getMasterPartitionPath(self):
    # getMasterPartitionPath() globs for a rendered file, which is absent
    # while the upgrade rebuilds the master partition
    return os.path.join(
      self.instance_path,
      self.getPartitionId(self.default_partition_reference))

  def _getMasterSlaveInstanceList(self):
    computer = self.slap._slap.registerComputer('local')
    for partition in computer.getComputerPartitionList():
      try:
        parameter_dict = partition.getInstanceParameterDict()
      except Exception:
        # partitions not (yet) allocated to a software release
        continue
      if parameter_dict.get(
          'instance_title') != self.default_partition_reference:
        continue
      slave_instance_list = parameter_dict.get('slave_instance_list', [])
      if isinstance(slave_instance_list, str):
        slave_instance_list = json.loads(slave_instance_list)
      return slave_instance_list
    return []

  def _getPassedSlaveReferenceDict(self):
    result_dict = {}
    section = None
    with open(
      os.path.join(
        self._getMasterPartitionPath(), 'instance-master.cfg')) as fh:
      for line in fh:
        if line.startswith('['):
          section = line.strip()[1:-1]
        elif line.startswith('config-extra_slave_instance_list'):
          value = line.split('=', 1)[1].strip()
          if value.startswith('!py!'):
            value = ast.literal_eval(value[4:].strip())
          if isinstance(value, str):
            value = json.loads(value)
          result_dict[section] = sorted(
            slave['slave_reference'] for slave in value)
    return result_dict

  def _getSlaveDomain(self, slave_reference):
    return '%s.example.com' % (slave_reference.replace('-', ''),)

  def _getServedDomainList(self):
    served_domain_list = []
    for slave_reference in self.getSlaveParameterDictDict():
      domain = self._getSlaveDomain(slave_reference)
      try:
        status_code = fakeHTTPSResult(domain, 'test-path').status_code
      except CurlException:
        continue
      if status_code == http.client.OK:
        served_domain_list.append(domain)
    return sorted(served_domain_list)

  def assertSlaveListIntact(self, context):
    reference_list = sorted(
      slave['slave_reference']
      for slave in self._getMasterSlaveInstanceList())
    domain_list = sorted(
      self._getSlaveDomain(slave_reference)
      for slave_reference in self.getSlaveParameterDictDict())
    self.assertEqual(
      {
        'passed to the frontend nodes': {
          'request-caddy-frontend-1': reference_list},
        'served': domain_list,
      },
      {
        'passed to the frontend nodes': self._getPassedSlaveReferenceDict(),
        'served': self._getServedDomainList(),
      },
      context)

  def _processInstance(self):
    subprocess_status_output([
      self.slap._slapos_wrapper, 'node', 'instance',
      '--cfg', self.slap._slapos_config,
    ])


class TestUpgradeSlaveListNotEmptied(WholeClusterUpgradeTestCase):
  instance_parameter_dict = dict(BASE_INSTANCE_PARAMETER_DICT)

  def test_upgrade_slave_list_not_emptied(self):
    self._hotfixCompiledOldSoftwareRelease()
    self.assertSlaveListIntact('before the upgrade')

    self._upgradeRootInstance()
    for run_number in range(1, UPGRADE_INSTANCE_RUN_AMOUNT + 1):
      self._processInstance()
      self.assertSlaveListIntact(
        'after instance run %i of the upgrade' % (run_number,))
