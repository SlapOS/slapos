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

beremiz_runtime_software_release_url = os.path.abspath(
  os.path.join(os.path.dirname(__file__), '..', 'software.cfg'))
osie_coupler_software_release_url = os.path.abspath(
  os.path.join(os.path.dirname(__file__), '..', '..', 'osie-coupler', 'software.cfg'))


_, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(beremiz_runtime_software_release_url))


def setUpModule():
  installSoftwareUrlList(
    SlapOSInstanceTestCase,
    [beremiz_runtime_software_release_url, osie_coupler_software_release_url],
    debug=bool(int(os.environ.get('SLAPOS_TEST_DEBUG', 0))),
  )


class BeremizRuntimeTestCase(SlapOSInstanceTestCase):

  @classmethod
  def requestDefaultInstance(cls, state='started'):
    osie_coupler_instance = cls.slap.request(
      software_release=osie_coupler_software_release_url,
      partition_reference='osie-coupler',
      partition_parameter_kw={'mode': 1},
      state=state,
    )
    return super().requestDefaultInstance(state=state)

  @classmethod
  def getInstanceParameterDict(cls):
    return {"runtime_plc_url": "https://lab.nexedi.com/nexedi/osie/-/raw/dd9aea8012376124ad216e3516e4f33945d14fc5/Beremiz/beremiz_test_opc_ua/bin/beremiz_test_opc_ua.tgz"}

  def test_process(self):
    with self.slap.instance_supervisor_rpc as supervisor:
      process_names = [process['name']
                       for process in supervisor.getAllProcessInfo()]
    self.assertIn('beremiz-runtime-on-watch', process_names)

  def check_connexion(self, ip, port):
    connexion_list = [] # test node debug
    for connexion in psutil.net_connections(kind='tcp4'):
      # test node debug
      if connexion.laddr.port == port:
        connexion_list.append(connexion)
      # debug end
      if connexion.laddr.ip == ip and connexion.laddr.port == port and connexion.status == 'ESTABLISHED':
        return True
    # test node debug
    print(connexion_list)
    test_path = self.computer_partition_root_path
    with open(os.path.join(test_path, '.' + os.path.basename(test_path) + '_beremiz-runtime.log')) as log_file:
      print(log_file.readlines()[-15:])
    # debug end
    return False

  def test_opc_ua(self):
    self.assertTrue(self.check_connexion('127.0.0.1', 4840))
