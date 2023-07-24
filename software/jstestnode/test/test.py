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


import glob
import json
import os
import subprocess

import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestJSTestNode(InstanceTestCase):

  def test(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    self.assertTrue('_' in parameter_dict)
    try:
      connection_dict = json.loads(parameter_dict['_'])
    except Exception as e:
      self.fail("Can't parse json in %s, error %s" % (parameter_dict['_'], e))

    self.assertEqual(
      {
        'nginx': 'http://[%s]:9443/' % (self.computer_partition_ipv6_address, )
      },
      connection_dict
    )

    # jio tests
    result = requests.get(
      '%sjio/test/tests.html' % (connection_dict['nginx'], ), allow_redirects=False)
    self.assertEqual(
      [requests.codes.ok, False],
      [result.status_code, result.is_redirect]
    )

    # rjs tests
    result = requests.get(
      '%srenderjs/test/' % (connection_dict['nginx'], ), allow_redirects=False)
    self.assertEqual(
      [requests.codes.ok, False],
      [result.status_code, result.is_redirect]
    )

    # rsvp tests
    result = requests.get(
      '%srsvp/test/index.html' % (connection_dict['nginx'], ), allow_redirects=False)
    self.assertEqual(
      [requests.codes.ok, False],
      [result.status_code, result.is_redirect]
    )

    # Default access
    result = requests.get(
      'http://[%s]:9443' % (self.computer_partition_ipv6_address, ), allow_redirects=False)
    self.assertEqual(
      [requests.codes.forbidden, False],
      [result.status_code, result.is_redirect]
    )

  def test_runTestSuite(self):
    runTestSuite_output = subprocess.check_output(
      [
        os.path.join(
          self.computer_partition_root_path,
          'bin',
          'runTestSuite',
        ),
       '--help',
      ])
    self.assertTrue(runTestSuite_output)
