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

import os

import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class SlaposSrTestingTestCase(SlapOSInstanceTestCase):
  def test_software_web_server_serves_checkout(self):
    # the software-web-server serves the software checkout over HTTP, so that
    # Software Releases are built from an URL. It must serve the raw tree,
    # including the nested paths a profile's extends and downloads reach.
    base_url = self.computer_partition.getConnectionParameterDict()[
      'software-web-server-url']
    for path in (
        'software/slapos-sr-testing/software.cfg',
        'stack/slapos.cfg',
        'component/git/buildout.cfg',
    ):
      response = requests.get('%s/%s' % (base_url, path))
      self.assertEqual(response.status_code, 200, path)
    self.assertIn(
      b'[buildout]',
      requests.get(
        '%s/software/slapos-sr-testing/software.cfg' % base_url).content)
    self.assertEqual(
      requests.get(
        '%s/software/not-a-software-release/software.cfg' % base_url).status_code,
      404)

  def test_services_running(self):
    with self.slap.instance_supervisor_rpc as supervisor:
      process_info_list = supervisor.getAllProcessInfo()
    process_state_dict = {
      process_info['name']: process_info['statename']
      for process_info in process_info_list
      if 'watchdog' not in (process_info['name'], process_info['group'])
    }
    # software-web-server serves the checkout for the whole test session, so it
    # must stay up (see instance.cfg); match by substring to tolerate a hash or
    # -on-watch suffix in the process name.
    web_server_state_dict = {
      name: state for name, state in process_state_dict.items()
      if 'software-web-server' in name
    }
    self.assertEqual(
      list(web_server_state_dict.values()), ['RUNNING'], process_state_dict)
    self.assertNotIn('FATAL', process_state_dict.values(), process_state_dict)
    self.assertNotIn('BACKOFF', process_state_dict.values(), process_state_dict)
