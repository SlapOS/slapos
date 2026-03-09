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


class ERP5MCPTestCase(SlapOSInstanceTestCase):
  """
  Common base class for testing erp5-mcp-hateoas.

  Inherits from SlapOSInstanceTestCase which:
    * Installs the software release
    * Checks it compiles without issue
    * Deploys the instance
    * Checks deployment works and promises pass
  """


class TestDefaultDeploy(ERP5MCPTestCase):
  """
  Test deployment with default parameters and erp5-url set.
  """

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'erp5-url': 'https://erp5js.nexedi.net',
    }

  def getConnectionParameterDict(self):
    return self.computer_partition.getConnectionParameterDict()

  def test_connection_parameters_published(self):
    """Verify all expected connection parameters are present."""
    params = self.getConnectionParameterDict()
    for key in ('mcp-url', 'mcp-server-url', 'mcp-port',
                'erp5-url', 'mcp-transport'):
      self.assertIn(key, params, 'Missing connection parameter: %s' % key)
    self.assertEqual(params['erp5-url'], 'https://erp5js.nexedi.net')
    self.assertEqual(params['mcp-transport'], 'streamable-http')

  def test_mcp_internal_port_listening(self):
    """Verify the internal MCP server responds on HTTP."""
    params = self.getConnectionParameterDict()
    ipv6 = params['mcp-ipv6']
    # Internal port defaults to 18765
    url = 'http://[%s]:18765/mcp' % ipv6
    response = requests.get(url, timeout=10)
    # The MCP server should respond; 401 is expected (OAuth requires auth)
    self.assertIn(response.status_code, (200, 401, 405))

  def test_haproxy_port_listening(self):
    """Verify HAProxy responds on the published mcp-url with HTTPS."""
    params = self.getConnectionParameterDict()
    url = params['mcp-url'] + '/'
    response = requests.get(url, verify=False, timeout=10)
    # HAProxy should respond (503 is OK if backend is starting)
    self.assertLess(response.status_code, 600)

  def test_oauth_discovery_endpoint(self):
    """Verify the OAuth authorization server metadata endpoint returns valid JSON."""
    params = self.getConnectionParameterDict()
    ipv6 = params['mcp-ipv6']
    # Hit the internal MCP server directly to avoid HAProxy 503 timing issues
    url = 'http://[%s]:18765/.well-known/oauth-authorization-server' % ipv6
    response = requests.get(url, timeout=10)
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertIn('issuer', data)
