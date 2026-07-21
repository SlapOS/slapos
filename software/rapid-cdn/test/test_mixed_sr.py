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

Each test brings up a single cluster where the control plane and
``caddy-frontend-1`` run the NEW software release under test (the local
checkout) while ``caddy-frontend-2`` runs an OLD, previously-released tag.

The supported mixed-SR window has a lower bound, so there are two kinds of
test:

* SERVES (``SERVES_SOFTWARE_RELEASE_URL_DICT``) -- the OLD frontend is recent
  enough to share the current master<->frontend parameter contract: it
  instantiates and serves traffic (with a certificate from the NEW kedifa),
  and the slave propagates to both frontends.
* REJECTED (``REJECTED_SOFTWARE_RELEASE_URL_DICT``) -- the OLD frontend
  predates parameters the current master now sends (the error-page-manager
  integration and related options landed after 1.0.469); its input schema has
  ``additionalProperties: false`` and rejects them, so the OLD frontend cannot
  instantiate. The test asserts this rejection, pinning the lower bound of the
  supported window.

Bump the pinned tags as releases advance (same convention as
``software/theia/test/upgrade_tests.py``); move a tag from REJECTED to SERVES
if a change makes an older frontend compatible again.
"""

import glob
import http.client
import json
import os

from slapos.slap.standalone import SlapOSNodeInstanceError
from slapos.testing.testcase import installSoftwareUrlList

import test
from test import fakeHTTPSResult


# Previously-released tags a frontend node may still run during a rolling
# upgrade of the cluster control plane. Two buckets, because the supported
# mixed-SR window has a lower bound:
#
# * SERVES -- releases recent enough to share the current master<->frontend
#   parameter contract: the OLD frontend instantiates and serves traffic.
# * REJECTED -- releases predating parameters the current master now sends
#   (the error-page-manager integration and related options landed after
#   1.0.469); their frontend input schema has ``additionalProperties: false``
#   and rejects those parameters, so the OLD frontend cannot instantiate. This
#   pins the lower bound of the supported window.
#
# Bump these as releases advance (same convention as
# ``software/theia/test/upgrade_tests.py``).
SERVES_SOFTWARE_RELEASE_URL_DICT = {
  '1.0.496':
    'https://lab.nexedi.com/nexedi/slapos/raw/1.0.496'
    '/software/rapid-cdn/software.cfg',
}
REJECTED_SOFTWARE_RELEASE_URL_DICT = {
  '1.0.469':
    'https://lab.nexedi.com/nexedi/slapos/raw/1.0.469'
    '/software/rapid-cdn/software.cfg',
}


def setUpModule():
  installSoftwareUrlList(
    test.SlapOSInstanceTestCase,
    [test.SlapOSInstanceTestCase.getSoftwareURL()]
    + list(SERVES_SOFTWARE_RELEASE_URL_DICT.values())
    + list(REJECTED_SOFTWARE_RELEASE_URL_DICT.values()),
    debug=test.SlapOSInstanceTestCase._debug,
  )


class _MixedFrontendSoftwareReleaseMixin(object):
  """Shared setup for the mixed-SR tests: a cluster whose control plane (root,
  kedifa, error-page-manager) and ``caddy-frontend-1`` run the NEW software
  release under test, while ``caddy-frontend-2`` runs an OLD, previously
  released tag set by ``old_software_release_url``.

  Not collected by ``unittest`` on its own -- it is a plain object, not a
  TestCase; only the concrete subclasses at the bottom run.
  """

  # set by concrete subclasses
  old_software_release_url = None

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

  def _requestMixedCluster(self, frontend_1_state, frontend_2_state):
    """Request the 2-frontend cluster with ``caddy-frontend-2`` on the OLD SR
    and the two frontends in the given states."""
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
    """The control plane and caddy-frontend-1 run the NEW SR, caddy-frontend-2
    is the one requested on the OLD SR."""
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


class _MixedFrontendServesTestMixin(_MixedFrontendSoftwareReleaseMixin):
  """The OLD frontend shares the current parameter contract: it instantiates
  and serves traffic in the mixed cluster."""

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
    # The test environment has a single test IPv4, so the two frontends cannot
    # both bind the HTTPS port at once. As ReplicateSlaveMixin does, only one
    # frontend is started at a time; a stopped frontend can leave a red promise,
    # which is tolerated unless frontends collide on IPv6 too.
    ipv6_collision = not self.frontends1And2HaveDifferentIPv6()

    # Phase 1: bring up the 2-node cluster with caddy-frontend-2 on the OLD SR,
    # and make it the frontend bound to the test IPv4 by stopping the NEW
    # caddy-frontend-1. This builds both partitions and lets us drive live
    # traffic through the OLD-SR frontend.
    self._requestMixedCluster('stopped', 'started')
    try:
      self.slap.waitForInstance(self.instance_max_retry)
    except Exception:
      if ipv6_collision:
        raise

    # Structural assurance: each partition runs the expected software release.
    self._assertControlPlaneRunsNewSoftwareRelease()

    # Structural assurance: the slave propagated to both frontend nodes,
    # proving the master<->frontend contract is compatible across SR versions.
    frontend_haproxy_cfg_list = self._frontendHaproxyCfgList()
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
    self._requestMixedCluster('started', 'stopped')
    for _ in range(3):
      try:
        self.slap.waitForInstance(self.instance_max_retry)
      except Exception:
        if ipv6_collision:
          raise
    self._assertLiveAccess(domain)


class _MixedFrontendRejectedTestMixin(_MixedFrontendSoftwareReleaseMixin):
  """The OLD frontend predates parameters the current master sends; its input
  schema (``additionalProperties: false``) rejects them, so it cannot
  instantiate. This documents and guards the lower bound of the supported
  mixed-SR window."""

  # parameters the current master sends that the OLD frontend's schema rejects
  rejected_parameter_list = (
    'error-page-base-url',
    'shared-error-page-information',
  )

  def test_old_frontend_rejected(self):
    # Keep the NEW caddy-frontend-1 running; the OLD caddy-frontend-2 fails its
    # buildout at parameter validation, so it never binds a port -- no IPv4
    # clash with frontend-1.
    self._requestMixedCluster('started', 'started')

    # The OLD frontend takes a couple of node cycles to be allocated and have
    # its buildout attempted; once it is, parameter validation fails
    # persistently. Run single cycles until that specific error surfaces (the
    # first cycles fail on the master's frontend-node-2 promise instead, as the
    # OLD frontend has not published anything yet).
    message = ''
    for _ in range(self.instance_max_retry):
      try:
        self.slap.waitForInstance(max_retry=0)
      except SlapOSNodeInstanceError as instance_error:
        message = str(instance_error)
        if 'Additional properties are not allowed' in message:
          break
      else:
        break  # unexpected: the mixed cluster converged
    self.assertIn('Additional properties are not allowed', message)
    for parameter in self.rejected_parameter_list:
      self.assertIn(parameter, message)

    # The rest of the cluster is unaffected: control plane + caddy-frontend-1
    # on the NEW SR, caddy-frontend-2 requested on the OLD SR.
    self._assertControlPlaneRunsNewSoftwareRelease()

    # Only the NEW caddy-frontend-1 rendered its configuration; the OLD
    # caddy-frontend-2 never got that far.
    self.assertEqual(1, len(self._frontendHaproxyCfgList()))


class TestMixedFrontendSoftwareRelease1_0_496(
    _MixedFrontendServesTestMixin,
    test.SlaveHttpFrontendTestCase, test.ReplicateSlaveMixin):
  old_software_release_url = SERVES_SOFTWARE_RELEASE_URL_DICT['1.0.496']
  instance_parameter_dict = {
    'domain': 'example.com',
    'port': test.HTTPS_PORT,
    'plain_http_port': test.HTTP_PORT,
    'kedifa_port': test.KEDIFA_PORT,
    'caucase_port': test.CAUCASE_PORT,
  }


class TestMixedFrontendSoftwareReleaseRejected1_0_469(
    _MixedFrontendRejectedTestMixin,
    test.SlaveHttpFrontendTestCase, test.ReplicateSlaveMixin):
  old_software_release_url = REJECTED_SOFTWARE_RELEASE_URL_DICT['1.0.469']
  instance_parameter_dict = {
    'domain': 'example.com',
    'port': test.HTTPS_PORT,
    'plain_http_port': test.HTTP_PORT,
    'kedifa_port': test.KEDIFA_PORT,
    'caucase_port': test.CAUCASE_PORT,
  }
