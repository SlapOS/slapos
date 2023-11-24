##############################################################################
#
# Copyright (c) 2021 Nexedi SA and Contributors. All Rights Reserved.
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

import base64
import os
import ssl
import urllib.parse

import requests
import websocket

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../software.cfg')))


class TestHeadlessChromium(SlapOSInstanceTestCase):
  def setUp(self):
    self.connection_parameters = self.computer_partition.getConnectionParameterDict()

  def test_remote_debugging_port(self):
    # The headless browser should respond at /json with a nonempty list
    # of available pages, each of which has a webSocketDebuggerUrl and a
    # devtoolsFrontendUrl.
    url = self.connection_parameters['remote-debug-url']
    response = requests.get(urllib.parse.urljoin(url, '/json'))

    # Check that request was successful and the response was a nonempty
    # list.
    self.assertEqual(requests.codes['ok'], response.status_code)
    self.assertTrue(len(response.json()) > 0)

    # Check that the first page has the correct fields.
    first_page = response.json()[0]
    self.assertIn('devtoolsFrontendUrl', first_page)
    websocket.create_connection(first_page['webSocketDebuggerUrl'], sslopt={"cert_reqs": ssl.CERT_NONE}).close()

  def test_devtools_frontend_ok(self):
    param = self.computer_partition.getConnectionParameterDict()

    # when accessed through RapidCDN, frontend rewrite WSS URLs with the host header but without port.
    page, = requests.get(
      urllib.parse.urljoin(param['proxy-url'], '/json'),
      auth=(param['username'], param['password']),
      headers={
        'Host': 'hostname'
      },
      verify=False).json()
    ws_debug_url = urllib.parse.urlparse(page['webSocketDebuggerUrl'])
    self.assertEqual(
      (ws_debug_url.scheme, ws_debug_url.netloc), ('wss', 'hostname'))

    devtools_frontend_url = dict(
      urllib.parse.parse_qsl(page['devtoolsFrontendUrl'].split('?')[1]))
    # devtoolsFrontendUrl is a relative URL, like this:
    # 'devtoolsFrontendUrl': '/devtools/inspector.html?wss=[::1]:9442/devtools/page/22C91CF307002BFA22DF0B4E34D2D026'
    # and the query string argument wss must also have been rewritten:
    self.assertTrue(
      devtools_frontend_url['wss'].startswith('hostname/devtools/page/'))

    requests.get(
        urllib.parse.urljoin(param['proxy-url'], page['devtoolsFrontendUrl']),
        auth=(param['username'], param['password']),
        headers={
          'Host': 'hostname'
        },
        verify=False).raise_for_status()

    # when accessed directly, the :port is kept, as a consequence the debugger interface can
    # be accessed directly from the nginx ipv6
    page, = requests.get(
      urllib.parse.urljoin(param['proxy-url'], '/json'),
      auth=(param['username'], param['password']),
      verify=False).json()
    ws_debug_url = urllib.parse.urlparse(page['webSocketDebuggerUrl'])
    self.assertEqual(ws_debug_url.port, 9224)

    devtools_frontend_url = dict(urllib.parse.parse_qsl(page['devtoolsFrontendUrl'].split('?')[1]))
    # devtoolsFrontendUrl is not rewritten
    self.assertEqual(f"wss://{devtools_frontend_url['wss']}", page['webSocketDebuggerUrl'])

    requests.get(
        urllib.parse.urljoin(param['proxy-url'], page['devtoolsFrontendUrl']),
        auth=(param['username'], param['password']),
        verify=False).raise_for_status()

    # the websocket is usable
    websocket.create_connection(
      page['webSocketDebuggerUrl'],
      sslopt={"cert_reqs": ssl.CERT_NONE},
      header={'Authorization': 'Basic ' + base64.b64encode(
        f"{param['username']}:{param['password']}".encode()).strip().decode()}).close()


class TestHeadlessChromiumParameters(SlapOSInstanceTestCase):

  instance_parameter_dict = {
    # this website echoes the get request for debugging purposes
    'target-url': 'https://httpbin.org/get?a=6&b=4',
    # TODO: this does not work, this software uses 'xml' serialisation and only support strings
    'incognito': True,
    "block-new-web-contents": False,
    "window-size": "900,600"
  }

  @classmethod
  def getInstanceParameterDict(cls):
    return cls.instance_parameter_dict

  def setUp(self):
    self.connection_parameters = self.requestDefaultInstance().getConnectionParameterDict()

  def test_chromium_loads_target_url_parameter(self):
    url = self.connection_parameters['remote-debug-url']
    response = requests.get('%s/json' % url)
    loaded_url = response.json()[0]['url']
    self.assertEqual(loaded_url, self.instance_parameter_dict['target-url'])
