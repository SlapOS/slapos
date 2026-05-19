##############################################################################
#
# Copyright (c) 2026 Nexedi SA and Contributors. All Rights Reserved.
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

import json
import os
import ssl
import urllib.parse
import urllib.request

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'software.cfg'))
)


class OMailGwPublishTestCase(SlapOSInstanceTestCase):
  __partition_reference__ = 'O'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'default'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      '_': json.dumps({
        'fluentd-port': 24229,
      })
    }

  def test_omailgw_connection_info_is_published(self):
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()['_'])
    self.assertEqual(parameter_dict['root-user'], 'root@omailgw.local')
    self.assertTrue(parameter_dict['root-password'])
    self.assertTrue(parameter_dict['api-url'].endswith('/api'))
    self.assertTrue(parameter_dict['ui-url'].endswith('/ui/'))
    self.assertTrue(parameter_dict['fluentd-host'])
    self.assertEqual(parameter_dict['fluentd-port'], '24229')
    self.assertTrue(parameter_dict['fluentd-shared-key'])

  def test_omailgw_api_login_and_user_me(self):
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()['_'])
    api_url = parameter_dict['api-url']
    root_user = parameter_dict['root-user']
    root_password = parameter_dict['root-password']

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    login_url = '%s/user/login?%s' % (
      api_url,
      urllib.parse.urlencode({
        'email': root_user,
        'password': root_password,
      }),
    )
    login_request = urllib.request.Request(login_url, method='POST')
    with urllib.request.urlopen(login_request, context=ssl_context) as response:
      login_payload = json.load(response)

    token = login_payload.get('token')
    self.assertTrue(token, 'oMailGw login should return a token')

    user_me_request = urllib.request.Request(
      '%s/user/me' % api_url,
      headers={'Authorization': 'Bearer %s' % token},
    )
    with urllib.request.urlopen(user_me_request, context=ssl_context) as response:
      user_me_payload = json.load(response)

    self.assertEqual(user_me_payload['email'], root_user)