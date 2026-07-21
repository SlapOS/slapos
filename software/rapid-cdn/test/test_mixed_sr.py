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

Rapid.CDN already lets each frontend partition run a different software release
than the cluster control plane, via the master's per-frontend
``-frontend-<i>-software-release-url`` parameter (see
``instance-master.cfg.in``). This supports rolling upgrades where the control
plane (root, kedifa, error-page-manager) is upgraded to a NEW release while
frontend nodes are still on an OLD release.

This test brings up a single cluster where the control plane and
``caddy-frontend-1`` run the NEW software release under test (the local
checkout) while ``caddy-frontend-2`` runs the OLD, previously-released tag, and
asserts that both frontends serve traffic correctly with certificates delivered
by the NEW kedifa.

``OLD_SOFTWARE_RELEASE_URL`` is pinned to the previous release tag and should be
bumped to the new previous release each cycle (same convention as
``software/theia/test/upgrade_tests.py``).
"""

import glob
import http.client
import json
import os

from slapos.testing.testcase import installSoftwareUrlList

import test
from test import fakeHTTPSResult


OLD_SOFTWARE_RELEASE_URL = (
  'https://lab.nexedi.com/nexedi/slapos/raw/1.0.496'
  '/software/rapid-cdn/software.cfg')


def setUpModule():
  installSoftwareUrlList(
    test.SlapOSInstanceTestCase,
    [test.SlapOSInstanceTestCase.getSoftwareURL(), OLD_SOFTWARE_RELEASE_URL],
    debug=test.SlapOSInstanceTestCase._debug,
  )


class TestMixedFrontendSoftwareRelease(
    test.SlaveHttpFrontendTestCase, test.ReplicateSlaveMixin):
  """Cluster with ``caddy-frontend-2`` on the OLD software release, the rest of
  the cluster on the NEW software release under test."""

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

  def _assertLiveAccess(self, domain):
    """A live HTTPS request to ``domain`` is served the backend response.

    The backend echoes the received path, so a GET on ``test-path`` must return
    ``{"Path": "/test-path"}`` with a 200 -- proving the currently-serving
    frontend delivers traffic with a certificate obtained from kedifa.
    """
    self.waitForSlave()
    result = fakeHTTPSResult(domain, 'test-path')
    self.assertEqual(http.client.OK, result.status_code)
    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_mixed_software_release(self):
    new_software_url = self.getSoftwareURL()
    # The test environment has a single test IPv4, so the two frontends cannot
    # both bind the HTTPS port at once. As ReplicateSlaveMixin does, only one
    # frontend is started at a time; a stopped frontend can leave a red promise,
    # which is tolerated unless frontends collide on IPv6 too.
    ipv6_collision = not self.frontends1And2HaveDifferentIPv6()

    # Phase 1: request the 2-node cluster with caddy-frontend-2 on the OLD SR,
    # and make it the frontend bound to the test IPv4 by stopping the NEW
    # caddy-frontend-1. This builds both partitions and lets us drive live
    # traffic through the OLD-SR frontend.
    self.instance_parameter_dict.update({
      '-frontend-quantity': 2,
      '-sla-2-computer_guid': self.slap._computer_id,
      '-frontend-2-software-release-url': OLD_SOFTWARE_RELEASE_URL,
      '-frontend-1-state': 'stopped',
      '-frontend-2-state': 'started',
    })
    self.updateDefaultInstanceParameterDict(self.instance_parameter_dict)
    self.requestDefaultInstance()
    self.requestSlaves()
    try:
      self.slap.waitForInstance(self.instance_max_retry)
    except Exception:
      if ipv6_collision:
        raise

    # Structural assurance: each partition runs the expected software release.
    computer = self.slap._slap.registerComputer('local')
    partition_software_url_dict = {}
    for partition in computer.getComputerPartitionList():
      if partition.getState() == 'destroyed':
        continue
      instance_title = partition.getInstanceParameterDict()['instance_title']
      partition_software_url_dict[instance_title] = \
        partition.getSoftwareRelease().getURI()

    for instance_title in (
        'testing partition 0',  # the root / master partition
        'caddy-frontend-1', 'kedifa', 'error-page-manager'):
      self.assertEqual(
        new_software_url,
        partition_software_url_dict.get(instance_title),
        '%s must run the NEW software release' % (instance_title,))
    self.assertEqual(
      OLD_SOFTWARE_RELEASE_URL,
      partition_software_url_dict.get('caddy-frontend-2'),
      'caddy-frontend-2 must run the OLD software release')

    # Structural assurance: the slave propagated to both frontend nodes,
    # proving the master<->frontend contract is compatible across SR versions.
    frontend_haproxy_cfg_list = glob.glob(
      os.path.join(self.instance_path, '*', 'etc', 'frontend-haproxy.cfg'))
    self.assertEqual(2, len(frontend_haproxy_cfg_list))
    for frontend_haproxy_cfg in frontend_haproxy_cfg_list:
      with open(frontend_haproxy_cfg) as fh:
        self.assertIn('backend _mixed-http', fh.read())

    # Live assurance: the OLD-SR frontend serves traffic with a certificate
    # delivered by the NEW kedifa.
    self.updateSlaveConnectionParameterDictDict()
    domain = self.parseSlaveParameterDict('mixed')['domain']
    self._assertLiveAccess(domain)

    # Phase 2: swap -- the NEW caddy-frontend-1 serves while the OLD
    # caddy-frontend-2 is stopped -- to assure the NEW frontend equally serves
    # in the mixed cluster.
    self.instance_parameter_dict.update({
      '-frontend-1-state': 'started',
      '-frontend-2-state': 'stopped',
    })
    self.updateDefaultInstanceParameterDict(self.instance_parameter_dict)
    self.requestDefaultInstance()
    self.requestSlaves()
    for _ in range(3):
      try:
        self.slap.waitForInstance(self.instance_max_retry)
      except Exception:
        if ipv6_collision:
          raise
    self._assertLiveAccess(domain)
