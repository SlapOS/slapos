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
"""error-page-manager scale test, run as its own suite.

Kept out of the main ``rapid-cdn`` suite so its long many-slave provisioning
does not inflate that test line. Reuses the ``../test`` package for the client
mixin, the module set-up (software installation) and the test-case base.
"""

import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.abspath(
  os.path.join(os.path.dirname(__file__), os.pardir, 'test')))

from test import ErrorPageManagerClientMixin, SlapOSInstanceTestCase, mimikra
# setUpModule installs the Rapid.CDN software release; unittest calls it.
from test import setUpModule  # noqa: F401


class TestErrorPageManagerScale(
    ErrorPageManagerClientMixin, SlapOSInstanceTestCase):
  """Scalability test: the /sync manifest stays flat as the shared-list grows.

  The pre-rewrite EPM materialised one per-slave page per shared instance at
  startup, so /sync was O(shared-instances) -- the scalability half of bug
  bug_module/20260722-9BC510.  The rewrite makes the manifest O(overrides):
  it lists the seven cluster defaults plus a shared/<ref>/<code>.http key only
  where a slave actually overrides a code.  This test requests a large
  shared-list and asserts the manifest is independent of the slave count, and
  that resilience still holds at scale.

  The EPM is a standalone partition (no frontend/kedifa/master parts), so this
  scales cheaply.  The slave count defaults to a CI-friendly 200 and is
  overridable for manual / nightly large runs:

      RAPIDCDN_TEST_EPM_SLAVE_COUNT=10000 python -m ...TestErrorPageManagerScale

  At large counts the dominant cost is instance time (buildout emits one token
  section per slave), borne by waitForInstance(); the manifest under test stays
  flat regardless.
  """

  __partition_reference__ = 'EPMSC'
  _EPM_MONITOR_PORT = 25103
  SLAVE_COUNT = int(os.environ.get('RAPIDCDN_TEST_EPM_SLAVE_COUNT', '200'))
  SLAVE_REF_TEMPLATE = 'scale-slave-%d'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'error-page-manager'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      '_': json.dumps({
        'monitor-password': 'test-monitor-password',
        'monitor-httpd-port': cls._EPM_MONITOR_PORT,
        'shared-list': [
          {'slave_reference': cls.SLAVE_REF_TEMPLATE % i}
          for i in range(cls.SLAVE_COUNT)
        ],
      }),
    }

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    # Widen the readiness poll: the manager builds an N-entry token map at
    # startup, which grows with the shared-list.
    cls._setUpErrorPageManagerClient(timeout=max(120, cls.SLAVE_COUNT // 5))

  def test_sync_manifest_is_flat_regardless_of_slave_count(self):
    """With no overrides the manifest is exactly the 7 cluster defaults and
    zero per-slave keys, no matter how many slaves are shared."""
    manifest = json.loads(self._get(self.sync_url).text)
    cluster = sorted(k for k in manifest if k.startswith('cluster/'))
    self.assertEqual(
      cluster, sorted('cluster/%s.http' % c for c in self.SUPPORTED_CODES))
    self.assertEqual(
      [k for k in manifest if k.startswith('shared/')], [],
      'no per-slave file must be published while no slave overrides a page')
    self.assertEqual(
      len(manifest), len(self.SUPPORTED_CODES),
      'manifest must carry only the %d cluster defaults for %d slaves'
      % (len(self.SUPPORTED_CODES), self.SLAVE_COUNT))

  def test_sync_manifest_byte_size_independent_of_slave_count(self):
    """The manifest carries zero per-slave bytes, so its size is a function
    only of the seven builtin entries -- not of the slave count."""
    raw = self._get(self.sync_url).text
    for i in (0, self.SLAVE_COUNT // 2, self.SLAVE_COUNT - 1):
      ref = self.SLAVE_REF_TEMPLATE % i
      self.assertNotIn(
        ref, raw, 'slave ref %s leaked into the manifest' % ref)
    # A flat 7-entry manifest is well under 8 KiB for any slave count.
    self.assertLess(
      len(raw.encode('utf-8')), 8192,
      'manifest is %d bytes for %d slaves -- it should not grow with slaves'
      % (len(raw.encode('utf-8')), self.SLAVE_COUNT))

  def test_single_override_adds_exactly_one_shared_key(self):
    """One slave override adds exactly one shared key; removing it returns the
    manifest to the flat state -- the O(overrides) property."""
    ref = self.SLAVE_REF_TEMPLATE % 0
    upload_base = self.slave_info[ref]['upload-url']
    key = 'shared/%s/503.http' % ref
    try:
      self.assertEqual(
        self._put(upload_base + '503', '<html>o</html>').status_code, 204)
      manifest = json.loads(self._get(self.sync_url).text)
      self.assertEqual(
        [k for k in manifest if k.startswith('shared/')], [key])
      self.assertEqual(
        len([k for k in manifest if k.startswith('cluster/')]),
        len(self.SUPPORTED_CODES))
    finally:
      self._delete(upload_base + '503')
    manifest = json.loads(self._get(self.sync_url).text)
    self.assertEqual([k for k in manifest if k.startswith('shared/')], [])

  def test_stalled_client_does_not_wedge_manager_at_scale(self):
    """Stalled clients must not wedge /sync even with a large shared-list."""
    stalled = []
    try:
      for _ in range(10):
        stalled.append(self._open_stalled_connection())
      ok = 0
      begin = time.time()
      while time.time() - begin < 30:
        result = mimikra.get(
          self.sync_url, verify=self._EPM_CERT_FILE, timeout=10)
        self.assertEqual(result.status_code, 200)
        ok += 1
        if ok >= 5:
          break
      self.assertGreaterEqual(
        ok, 5, 'sync did not stay responsive at scale while clients stalled '
        '(only %d probes)' % ok)
    finally:
      for tls in stalled:
        try:
          tls.close()
        except Exception:
          pass

  def test_concurrent_sync_requests_at_scale(self):
    """Many simultaneous /sync clients are all served without error at scale."""
    WORKERS = 20
    DURATION_SECONDS = 10
    stop_event = threading.Event()
    counters = {'ok': 0, 'err': 0}
    lock = threading.Lock()

    def worker():
      while not stop_event.is_set():
        try:
          r = mimikra.get(
            self.sync_url, verify=self._EPM_CERT_FILE, timeout=30)
          with lock:
            counters['ok' if r.status_code == 200 else 'err'] += 1
        except Exception:
          with lock:
            counters['err'] += 1

    threads = [threading.Thread(target=worker) for _ in range(WORKERS)]
    for t in threads:
      t.daemon = True
      t.start()
    try:
      time.sleep(DURATION_SECONDS)
    finally:
      stop_event.set()
      for t in threads:
        t.join(timeout=60)

    self.assertGreater(counters['ok'], 0, 'no successful concurrent /sync')
    self.assertEqual(
      counters['err'], 0,
      'concurrent /sync produced %d errors (ok=%d) at scale'
      % (counters['err'], counters['ok']))
