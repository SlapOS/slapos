##############################################################################
#
# Copyright (c) 2018 Nexedi SA and Contributors. All Rights Reserved.
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
import time
import requests
import json

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.testing.utils import CrontabMixin

setUpModule, Re6stnetTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestRe6stnetRegistry(Re6stnetTestCase):
  def test_listen(self):
    connection_parameters = self.computer_partition.getConnectionParameterDict()
    registry_url = connection_parameters['re6stry-local-url']

    _ = requests.get(registry_url)


class TestPortRedirection(Re6stnetTestCase):
  def test_portredir_config(self):
    portredir_config_path = os.path.join(
        self.computer_partition_root_path, '.slapos-port-redirect')
    with open(portredir_config_path) as f:
      portredir_config = json.load(f)

    self.assertDictContainsSubset(
        {
            'srcPort': 9201,
            'destPort': 9201,
        }, portredir_config[0])


class TestTokens(Re6stnetTestCase, CrontabMixin):

  partition_reference = "SOFTINST-1"

  @classmethod
  def requestDefaultInstance(self, state='started'):
    default_instance = super(
      Re6stnetTestCase, self).requestDefaultInstance(state=state)
    self.requestSlaveInstance()
    return default_instance

  @classmethod
  def requestSlaveInstance(self):
    software_url = self.getSoftwareURL()
    self.logger.debug('requesting slave "%s"', self.partition_reference)
    return self.slap.request(
      software_release=software_url,
      partition_reference=self.partition_reference,
      partition_parameter_kw={},
      shared=True,
    )

  def test_tokens(self):
    self._executeCrontabAtDate('re6stnet-check-token', '+10min')
    self.slap.waitForInstance() # Wait until publish is done

    s = self.requestSlaveInstance()

    self.assertEqual("Token is ready for use", s.getConnectionParameterDict()['1_info'])
