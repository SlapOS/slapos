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

  def _internal_url(self, path=''):
    """Build an HTTP URL to the internal MCP server (bypasses HAProxy)."""
    params = self.computer_partition.getConnectionParameterDict()
    return 'http://[%s]:18765%s' % (params['mcp-ipv6'], path)

  def _oauth_metadata(self):
    """Fetch and return the OAuth authorization server metadata."""
    response = requests.get(
        self._internal_url('/.well-known/oauth-authorization-server'),
        timeout=10)
    response.raise_for_status()
    return response.json()

  def _register_oauth_client(self):
    """Register a dynamic OAuth client and return its metadata."""
    metadata = self._oauth_metadata()
    # The registration endpoint in metadata points to the external HAProxy URL,
    # but the test accesses the internal HTTP server directly to avoid
    # self-signed certificate issues with HAProxy.
    from urllib.parse import urlparse
    parsed = urlparse(metadata['registration_endpoint'])
    reg_url = self._internal_url(parsed.path)
    response = requests.post(reg_url, json={
        'redirect_uris': ['http://localhost:9999/callback'],
        'client_name': 'integration-test',
        'grant_types': ['authorization_code', 'refresh_token'],
        'response_types': ['code'],
        'token_endpoint_auth_method': 'client_secret_post',
    }, timeout=10)
    if not response.ok:
      raise AssertionError(
        'OAuth registration failed: %s %s' % (response.status_code, response.text))
    return response.json()


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
    data = self._oauth_metadata()
    self.assertIn('issuer', data)
    self.assertIn('authorization_endpoint', data)
    self.assertIn('token_endpoint', data)
    self.assertIn('registration_endpoint', data)

  def test_oauth_client_registration(self):
    """Verify dynamic OAuth client registration succeeds."""
    client_info = self._register_oauth_client()
    self.assertIn('client_id', client_info)
    self.assertIn('client_secret', client_info)

  def test_mcp_post_unauthenticated_returns_401(self):
    """MCP tool calls without a Bearer token must return 401."""
    response = requests.post(
        self._internal_url('/mcp'),
        json={
            'jsonrpc': '2.0',
            'method': 'initialize',
            'params': {
                'protocolVersion': '2025-03-26',
                'capabilities': {},
                'clientInfo': {'name': 'test', 'version': '0.1'},
            },
            'id': 1,
        },
        headers={'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'},
        timeout=10,
    )
    self.assertEqual(response.status_code, 401)

  def test_mcp_startup_script_sets_tmpdir(self):
    """Verify the startup script sets TMPDIR to the partition tmp directory.

    This ensures erp5_download writes temporary files inside the partition
    (via tempfile.gettempdir()), not to the system-wide /tmp/.
    """
    # Read the generated startup script from the partition
    partition_path = self.computer_partition_root_path
    startup_script = os.path.join(partition_path, 'etc', 'erp5-mcp-start.sh')
    with open(startup_script) as f:
      content = f.read()
    self.assertIn('export TMPDIR=', content)
    self.assertNotIn("TMPDIR=/tmp", content)
