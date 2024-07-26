##############################################################################
# coding: utf-8
#
# Copyright (c) 2022 Nexedi SA and Contributors. All Rights Reserved.
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
import psutil

from slapos.testing.testcase import installSoftwareUrlList, makeModuleSetUpAndTestCaseClass

oi_sensor_software_release_url = os.path.abspath(
  os.path.join(os.path.dirname(__file__), '..', 'software.cfg'))

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(oi_sensor_software_release_url),
    # skip software checks
    skip_software_check = True)

class OISensorTestCase(SlapOSInstanceTestCase):

  @classmethod
  def requestDefaultInstance(cls, state='started'):
    osie_coupler_instance = cls.slap.request(
      software_release=oi_sensor_software_release_url,
      partition_reference='oi-sensor',
      partition_parameter_kw={'headless': 1, 'mode':1, 'port': 4840},
      state=state,
    )
    return super().requestDefaultInstance(state=state)

  @classmethod
  def getInstanceParameterDict(cls):
    return {}

  def test_process(self):
    with self.slap.instance_supervisor_rpc as supervisor:
      print(supervisor.getAllProcessInfo())
      process_names = [process['name']
                       for process in supervisor.getAllProcessInfo()]
    self.assertIn('oi-sensor-service-on-watch', process_names)

  def check_connection(self, ip, port):
    connection_list = [] # test node debug
    print(psutil.net_connections(kind='tcp4'))
    for connection in psutil.net_connections(kind='tcp4'):
      # test node debug
      if connection.laddr.port == port:
        connection_list.append(connection)
      # debug end
      if connection.laddr.ip == ip and connection.laddr.port == port and connection.status == 'ESTABLISHED':
        return True
    return False

  def test_opc_ua(self):
    self.assertTrue(self.check_connection('0.0.0.0', 4840))
