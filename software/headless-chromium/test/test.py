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

import os
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../software.cfg')))

class TestHeadlessChromium(SlapOSInstanceTestCase):
  def setUp(self):
    self.connection_parameters = self.requestDefaultInstance().getConnectionParameterDict()

  def test_remote_debugging_port(self):
    # The headless browser should respond at /json with a nonempty list
    # of available pages, each of which has a webSocketDebuggerUrl and a
    # devtoolsFrontendUrl.
    url = self.connection_parameters['remote-debug-url']
    response = requests.get('%s/json' % url)

    # Check that request was successful and the response was a nonempty
    # list.
    self.assertEqual(requests.codes['ok'], response.status_code)
    self.assertTrue(len(response.json()) > 0)

    # Check that the first page has the correct fields.
    first_page = response.json()[0]
    self.assertIn('webSocketDebuggerUrl', first_page)
    self.assertIn('devtoolsFrontendUrl', first_page)

  def test_devtools_frontend_ok(self):
    # The proxy should serve the DevTools frontend from
    # /serve_file/@{hash}/inspector.html, where {hash} is a 5-32 digit
    # hash.
    proxyURL = self.connection_parameters['proxy-url']
    username = self.connection_parameters['username']
    password = self.connection_parameters['password']
    frontend = '/serve_file/@aaaaa/inspector.html'

    response = requests.get(proxyURL + frontend, verify=False,
                            auth=(username, password))
    self.assertEqual(requests.codes['ok'], response.status_code)

class TestHeadlessChromiumParameters(SlapOSInstanceTestCase):

  instance_parameter_dict = {
    # this website echoes the get request for debugging purposes
    'target-url': 'https://httpbin.org/get?a=6&b=4',
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
