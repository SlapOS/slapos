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
import pathlib
import ssl
import urllib.parse
import urllib.request

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'software.cfg'))
)


class OMailGwPublishTestCase(SlapOSInstanceTestCase):
  __partition_reference__ = 'O'
  api_revision = '972dc8e701b810dcab11707447561c4fae0406ad'
  ui_revision = '4690200544029c97baed443266777dcd17d27316'

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

  def getConnectionParameterDict(self):
    return json.loads(self.computer_partition.getConnectionParameterDict()['_'])

  def apiRequest(self, path, method='GET', token=None, payload=None):
    parameter_dict = self.getConnectionParameterDict()
    header_dict = {'Accept': 'application/json'}
    if token:
      header_dict['Authorization'] = 'Bearer %s' % token
    data = None
    if payload is not None:
      data = json.dumps(payload).encode()
      header_dict['Content-Type'] = 'application/json'
    request = urllib.request.Request(
      '%s%s' % (parameter_dict['api-url'], path),
      data=data,
      headers=header_dict,
      method=method,
    )
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(request, context=ssl_context) as response:
      return json.load(response)

  def loginRoot(self):
    parameter_dict = self.getConnectionParameterDict()
    login_path = '/user/login?%s' % urllib.parse.urlencode({
      'email': parameter_dict['root-user'],
      'password': parameter_dict['root-password'],
    })
    token = self.apiRequest(login_path, method='POST').get('token')
    self.assertTrue(token, 'oMailGw login should return a token')
    return token

  @staticmethod
  def readAppKey(env_path):
    with env_path.open() as env_file:
      for line in env_file:
        if line.startswith('APP_KEY='):
          return line.rstrip('\n').split('=', 1)[1]
    raise AssertionError('APP_KEY is missing from %s' % env_path)

  def test_omailgw_connection_info_is_published(self):
    parameter_dict = self.getConnectionParameterDict()
    self.assertEqual(parameter_dict['root-user'], 'root@omailgw.local')
    self.assertTrue(parameter_dict['root-password'])
    self.assertTrue(parameter_dict['api-url'].endswith('/api'))
    self.assertTrue(parameter_dict['ui-url'].endswith('/ui/'))
    self.assertTrue(parameter_dict['fluentd-host'])
    self.assertEqual(parameter_dict['fluentd-port'], '24229')
    self.assertTrue(parameter_dict['fluentd-shared-key'])

  def test_omailgw_api_login_and_user_me(self):
    parameter_dict = self.getConnectionParameterDict()
    user_me_payload = self.apiRequest('/user/me', token=self.loginRoot())
    self.assertEqual(user_me_payload['email'], parameter_dict['root-user'])

  def test_omailgw_upgrade_replaces_code_and_preserves_state(self):
    partition_path = pathlib.Path(self.computer_partition_root_path)
    api_path = partition_path / 'srv' / 'omailgw-api'
    ui_path = api_path / 'public' / 'ui'
    env_path = api_path / '.env'
    app_key_path = partition_path / 'var' / 'omailgw-app-key'
    storage_sentinel = api_path / 'storage' / 'app' / 'upgrade-sentinel'
    api_file = api_path / 'README.md'
    ui_file = ui_path / 'ajaxTest.html'
    api_stale_file = api_path / 'stale-api-file'
    ui_stale_file = ui_path / 'stale-ui-file'
    ui_settings_path = ui_path / 'js' / 'settings.js'
    api_marker = partition_path / 'var' / 'deployment' / 'omailgw-api'
    ui_marker = partition_path / 'var' / 'deployment' / 'omailgw-ui'

    app_key = self.readAppKey(env_path)
    self.assertTrue(app_key)
    api_file_content = api_file.read_bytes()
    ui_file_content = ui_file.read_bytes()

    token = self.loginRoot()
    original_preference = self.apiRequest(
      '/user/me', token=token)['rapport_include_soft_bounces']
    updated_preference = not original_preference
    self.apiRequest(
      '/user/me',
      method='POST',
      token=token,
      payload={'rapport_include_soft_bounces': updated_preference},
    )
    self.assertEqual(
      self.apiRequest('/user/me', token=token)['rapport_include_soft_bounces'],
      updated_preference,
    )

    storage_sentinel.write_text('persistent state')
    api_file.write_text('modified API code')
    ui_file.write_text('modified UI code')
    api_stale_file.write_text('stale')
    ui_stale_file.write_text('stale')
    env_path.write_text(
      env_path.read_text().replace('APP_DEBUG=false', 'APP_DEBUG=true'))
    ui_settings_path.write_text('modified generated UI settings')
    api_marker.write_text('outdated')
    ui_marker.write_text('outdated')
    app_key_path.unlink()

    (partition_path / '.timestamp').unlink()
    self.waitForInstance()

    self.assertEqual(api_file.read_bytes(), api_file_content)
    self.assertEqual(ui_file.read_bytes(), ui_file_content)
    self.assertFalse(api_stale_file.exists())
    self.assertFalse(ui_stale_file.exists())
    self.assertTrue(api_marker.read_text().startswith(self.api_revision + ':'))
    self.assertTrue(ui_marker.read_text().startswith(self.ui_revision + ':'))
    self.assertEqual(self.readAppKey(env_path), app_key)
    self.assertEqual(app_key_path.read_text(), app_key)
    self.assertIn('APP_DEBUG=false', env_path.read_text())
    self.assertEqual(storage_sentinel.read_text(), 'persistent state')

    settings = ui_settings_path.read_text()
    self.assertIn(self.getConnectionParameterDict()['api-url'], settings)
    user_me_payload = self.apiRequest('/user/me', token=self.loginRoot())
    self.assertEqual(
      user_me_payload['rapport_include_soft_bounces'], updated_preference)
