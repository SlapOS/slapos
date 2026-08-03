##############################################################################
#
# Copyright (c) 2025 Nexedi SA and Contributors. All Rights Reserved.
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
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class OpenWebUITestCase(SlapOSInstanceTestCase):
  """
  Common base class for testing OpenWebUI.
  """


class TestDefaultDeploy(OpenWebUITestCase):
  """
  Test deployment with default parameters (all optional).
  """

  def getConnectionParameterDict(self):
    return self.computer_partition.getConnectionParameterDict()

  def test_connection_parameters_published(self):
    """Verify all expected connection parameters are present."""
    params = self.getConnectionParameterDict()
    for key in ('url', 'port', 'ipv6'):
      self.assertIn(key, params, 'Missing connection parameter: %s' % key)

  def test_openwebui_port_listening(self):
    """Verify the internal OpenWebUI server responds on HTTP."""
    params = self.getConnectionParameterDict()
    ipv6 = params['ipv6']
    url = 'http://[%s]:18080/' % ipv6
    response = requests.get(url, timeout=30, allow_redirects=False)
    self.assertIn(response.status_code, (200, 301, 302, 307))

  def test_haproxy_port_listening(self):
    """Verify HAProxy responds on the published url with HTTPS."""
    params = self.getConnectionParameterDict()
    url = params['url'] + '/'
    response = requests.get(url, verify=False, timeout=30)
    self.assertLess(response.status_code, 600)

  def test_health_endpoint(self):
    """Verify the /health endpoint returns 200."""
    params = self.getConnectionParameterDict()
    ipv6 = params['ipv6']
    url = 'http://[%s]:18080/health' % ipv6
    response = requests.get(url, timeout=30)
    self.assertEqual(response.status_code, 200)
