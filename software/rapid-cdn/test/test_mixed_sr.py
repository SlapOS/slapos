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
checkout) while ``caddy-frontend-2`` runs an OLD software release. There are
three concepts:

* REJECTED (1.0.469) -- an OLD frontend predating parameters the current master
  now sends (the error-page-manager integration and related options landed
  after 1.0.469); its input schema has ``additionalProperties: false`` and
  rejects them, so the OLD frontend cannot instantiate. This pins the lower
  bound of the supported window.
* FIXED (1.0.469 + patch) -- the same OLD release with the proposed fix applied
  (relax the sub-instance input schemas to ``additionalProperties: true``, see
  ``PATCH_FILENAME``) now instantiates in the mixed cluster. The patch is
  applied to a checkout materialised from the tag at test time (see
  ``_materialisePatchedCheckout``), so the fix stays a single visible file.
* UPGRADE (1.0.469 -> NEW) -- an operator on 1.0.469 must be able to upgrade
  that frontend directly to the current release. This asserts a zero-downtime
  rolling upgrade: the OLD frontend serves traffic, then moves to the NEW SR in
  place and keeps serving. It shares the REJECTED lower bound, so this is
  expected to fail until that bound is fixed.

Bump the pinned tags as releases advance (same convention as
``software/theia/test/upgrade_tests.py``).
"""

import glob
import http.client
import json
import os
import shutil
import subprocess
import unittest

from slapos.slap.standalone import SlapOSNodeInstanceError
from slapos.testing.testcase import installSoftwareUrlList

import test
from test import fakeHTTPSResult


REJECTED_SOFTWARE_RELEASE_URL = (
  'https://lab.nexedi.com/nexedi/slapos/raw/1.0.469'
  '/software/rapid-cdn/software.cfg')

# The FIXED release is 1.0.469 with the schema-relaxation patch applied. Its
# source can't be a tag URL (a URL can't be patched), so it is materialised at
# test time: a checkout is extracted from the tag and patched with the committed
# file below. Requires the tag to be present in the git clone.
FIXED_SOFTWARE_RELEASE_TAG = '1.0.469'
PATCH_FILENAME = 'rapid-cdn-1.0.469-relax-subinstance-schemas.patch'
_REPO_ROOT = os.path.abspath(os.path.join(
  os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
_PATCH_PATH = os.path.join(os.path.dirname(__file__), PATCH_FILENAME)
_PATCHED_CHECKOUT_DIR = os.path.join(
  os.path.realpath(os.environ.get(
    'SLAPOS_TEST_WORKING_DIR', os.path.join(os.getcwd(), '.slapos'))),
  'rapid-cdn-1.0.469-patched')
FIXED_SOFTWARE_RELEASE_URL = os.path.join(
  _PATCHED_CHECKOUT_DIR, 'software', 'rapid-cdn', 'software.cfg')


def _fixedSoftwareReleaseTagAvailable():
  try:
    subprocess.check_call(
      ['git', '-C', _REPO_ROOT, 'rev-parse', '--verify', '--quiet',
       FIXED_SOFTWARE_RELEASE_TAG + '^{commit}'],
      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
  except (OSError, subprocess.CalledProcessError):
    return False
  return True


def _materialisePatchedCheckout():
  """Extract the FIXED tag with ``git archive`` and apply the committed patch,
  yielding a full, patched on-disk checkout to build the FIXED release from."""
  if os.path.exists(_PATCHED_CHECKOUT_DIR):
    shutil.rmtree(_PATCHED_CHECKOUT_DIR)
  os.makedirs(_PATCHED_CHECKOUT_DIR)
  archive = subprocess.Popen(
    ['git', '-C', _REPO_ROOT, 'archive', FIXED_SOFTWARE_RELEASE_TAG],
    stdout=subprocess.PIPE)
  try:
    subprocess.check_call(
      ['tar', '-x', '-C', _PATCHED_CHECKOUT_DIR], stdin=archive.stdout)
  finally:
    archive.stdout.close()
    archive.wait()
  if archive.returncode != 0:
    raise subprocess.CalledProcessError(archive.returncode, 'git archive')
  # git apply rejects the extracted absolute paths (not a repo), so use patch
  subprocess.check_call(
    ['patch', '-p1', '-d', _PATCHED_CHECKOUT_DIR, '-i', _PATCH_PATH])


def setUpModule():
  software_url_list = [
    test.SlapOSInstanceTestCase.getSoftwareURL(),
    REJECTED_SOFTWARE_RELEASE_URL,
  ]
  if _fixedSoftwareReleaseTagAvailable():
    _materialisePatchedCheckout()
    software_url_list.append(FIXED_SOFTWARE_RELEASE_URL)
  installSoftwareUrlList(
    test.SlapOSInstanceTestCase,
    software_url_list,
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

  def _requestMixedCluster(
      self, frontend_1_state, frontend_2_state,
      frontend_2_software_release_url=None):
    """Request the 2-frontend cluster with the two frontends in the given
    states. ``caddy-frontend-2`` runs ``frontend_2_software_release_url``,
    defaulting to the OLD SR; the upgrade test passes the NEW SR here to move
    that frontend across releases in place."""
    if frontend_2_software_release_url is None:
      frontend_2_software_release_url = self.old_software_release_url
    self.instance_parameter_dict.update({
      '-frontend-quantity': 2,
      '-sla-2-computer_guid': self.slap._computer_id,
      '-frontend-2-software-release-url': frontend_2_software_release_url,
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


class _MixedFrontendFixedTestMixin(_MixedFrontendSoftwareReleaseMixin):
  """The OLD frontend, patched to relax its sub-instance input schema
  (``additionalProperties: true``, per the forum proposal), now instantiates in
  the mixed cluster. A lighter check: it asserts the patched OLD frontend builds
  -- i.e. no longer hits the schema rejection (see the REJECTED test) -- without
  driving live traffic."""

  def test_patched_old_frontend_instantiates(self):
    ipv6_collision = not self.frontends1And2HaveDifferentIPv6()
    # frontend-2 (patched OLD) started, NEW frontend-1 stopped to avoid the
    # single-IPv4 clash; a stopped frontend can leave a red promise, tolerated
    # unless the frontends also collide on IPv6.
    self._requestMixedCluster('stopped', 'started')
    try:
      self.slap.waitForInstance(self.instance_max_retry)
    except Exception:
      if ipv6_collision:
        raise

    # Both frontends rendered their configuration -> the patched OLD frontend
    # built, where the unpatched one is rejected (see the REJECTED test).
    self.assertEqual(2, len(self._frontendHaproxyCfgList()))
    self._assertControlPlaneRunsNewSoftwareRelease()


class _MixedFrontendUpgradeTestMixin(_MixedFrontendSoftwareReleaseMixin):
  """Assert an in-place rolling upgrade of a frontend FROM the OLD release TO
  the NEW release under test.

  An operator stuck on 1.0.469 must be able to upgrade that frontend straight to
  the current release. A zero-downtime rolling upgrade requires the OLD frontend
  to first run and serve, then move to the NEW SR without losing service -- so
  this drives live traffic before and after moving ``caddy-frontend-2`` from the
  OLD SR to the NEW SR in place.
  """

  def test_upgrade_old_frontend_to_new(self):
    # Single test IPv4, so only one frontend serves at a time; a stopped
    # frontend can leave a red promise, tolerated unless they also collide on
    # IPv6 (as in the other mixed-SR tests).
    ipv6_collision = not self.frontends1And2HaveDifferentIPv6()

    # Pre-upgrade: caddy-frontend-2 runs the OLD SR and serves; the NEW
    # caddy-frontend-1 is stopped.
    self._requestMixedCluster('stopped', 'started')
    try:
      self.slap.waitForInstance(self.instance_max_retry)
    except Exception:
      if ipv6_collision:
        raise
    self._assertControlPlaneRunsNewSoftwareRelease()
    self.updateSlaveConnectionParameterDictDict()
    domain = self.parseSlaveParameterDict('mixed')['domain']
    self._assertLiveAccess(domain)

    # Upgrade in place: move caddy-frontend-2 to the NEW SR; it must keep serving.
    self._requestMixedCluster(
      'stopped', 'started',
      frontend_2_software_release_url=self.getSoftwareURL())
    try:
      self.slap.waitForInstance(self.instance_max_retry)
    except Exception:
      if ipv6_collision:
        raise
    self.assertEqual(
      self.getSoftwareURL(),
      self._getPartitionSoftwareUrlDict().get('caddy-frontend-2'),
      'caddy-frontend-2 must run the NEW software release after the upgrade')
    self._assertLiveAccess(domain)


class TestMixedFrontendSoftwareReleaseRejected1_0_469(
    _MixedFrontendRejectedTestMixin,
    test.SlaveHttpFrontendTestCase, test.ReplicateSlaveMixin):
  old_software_release_url = REJECTED_SOFTWARE_RELEASE_URL
  instance_parameter_dict = {
    'domain': 'example.com',
    'port': test.HTTPS_PORT,
    'plain_http_port': test.HTTP_PORT,
    'kedifa_port': test.KEDIFA_PORT,
    'caucase_port': test.CAUCASE_PORT,
  }


@unittest.skipUnless(
  _fixedSoftwareReleaseTagAvailable(),
  'git tag %s not available in the checkout, cannot build the patched release'
  % FIXED_SOFTWARE_RELEASE_TAG)
class TestMixedFrontendSoftwareReleaseFixed1_0_469(
    _MixedFrontendFixedTestMixin,
    test.SlaveHttpFrontendTestCase, test.ReplicateSlaveMixin):
  old_software_release_url = FIXED_SOFTWARE_RELEASE_URL
  instance_parameter_dict = {
    'domain': 'example.com',
    'port': test.HTTPS_PORT,
    'plain_http_port': test.HTTP_PORT,
    'kedifa_port': test.KEDIFA_PORT,
    'caucase_port': test.CAUCASE_PORT,
  }


class TestMixedFrontendSoftwareReleaseUpgradeFrom1_0_469(
    _MixedFrontendUpgradeTestMixin,
    test.SlaveHttpFrontendTestCase, test.ReplicateSlaveMixin):
  old_software_release_url = REJECTED_SOFTWARE_RELEASE_URL
  instance_parameter_dict = {
    'domain': 'example.com',
    'port': test.HTTPS_PORT,
    'plain_http_port': test.HTTP_PORT,
    'kedifa_port': test.KEDIFA_PORT,
    'caucase_port': test.CAUCASE_PORT,
  }
