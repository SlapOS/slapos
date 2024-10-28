##############################################################################
#
# Copyright (c) 2019 Nexedi SA and Contributors. All Rights Reserved.
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
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestBackupServer(InstanceTestCase):

  def test(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()

    # Check that there is a RSS feed
    self.assertTrue('rss' in parameter_dict)
    self.assertTrue(parameter_dict['rss'].startswith(
      f'https://[{self.computer_partition_ipv6_address}]:9443/'
    ))

    result = requests.get(
      parameter_dict['rss'], verify=False, allow_redirects=False)

    # XXX crontab not triggered yet
    self.assertEqual(
      [requests.codes.not_found, False],
      [result.status_code, result.is_redirect]
    )

    # Check monitor
    self.assertTrue('monitor-base-url' in parameter_dict)
    self.assertTrue('monitor-setup-url' in parameter_dict)

    result = requests.get(
      parameter_dict['monitor-base-url'], verify=False, allow_redirects=False)
    self.assertEqual(
      [requests.codes.unauthorized, False],
      [result.status_code, result.is_redirect]
    )
