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

import os
import textwrap
import logging
import tempfile

import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))

bases = SlapOSInstanceTestCase.__bases__ 
bases[0]._instance_parameter_dict = {}


class TestProviewR(SlapOSInstanceTestCase):
  def setUp(self):
    self.connection_dict = self.computer_partition.getConnectionParameterDict()

  def test_http_get(self):
    resp = requests.get(self.connection_dict['backend-url'], verify=False)
    self.assertEqual(requests.codes.ok, resp.status_code)

    # Test Shellinabox backend URL, this is unauthorized
    resp = requests.get(self.connection_dict['shell-backend'], verify=False)
    self.assertEqual(requests.codes.unauthorized, resp.status_code)
