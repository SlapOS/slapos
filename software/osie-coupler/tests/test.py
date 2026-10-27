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

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))

class OsieTestCase(SlapOSInstanceTestCase):


  MULTICAST_INTERFACE = 'lo'
  MULTICAST_GROUP_COUNT = 2
  MULTICAST_GROUP = '224.0.0.22'


  @classmethod
  def getInstanceParameterDict(cls):
    return {"mode": 1, "network_interface": "127.0.0.1", "heart_beat_id_list": "1"}

  def test(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    self.assertIn('url-ipv6', parameter_dict)

  def test_process(self):
    with self.slap.instance_supervisor_rpc as supervisor:
      process_names = [process['name']
                       for process in supervisor.getAllProcessInfo()]
    self.assertIn('coupler-opc-ua-on-watch', process_names)

  def IPV4_to_little_endian_hex_str(self, ipv4_str):
    hex_str_list = []
    for int_str in ipv4_str.split('.'):
      hex_str_list.append('%0.2X' % int(int_str))
    return ''.join(reversed(hex_str_list))

  def test_joined_multicast_grp(self):
    with open('/proc/net/igmp') as f:
      igmp_content = f.readlines()
      for igmp_line in (
        '1\t%s        :     %s      V3\n' % (self.MULTICAST_INTERFACE, self.MULTICAST_GROUP_COUNT),
        '\t\t\t\t%s     1 0:00000000\t\t0\n' % self.IPV4_to_little_endian_hex_str(self.MULTICAST_GROUP),
      ):
        self.assertIn(igmp_line, igmp_content)
