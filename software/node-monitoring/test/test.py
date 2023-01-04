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
import json

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))

param_dict = {
    'promise_cpu_temperature_threshold': 90,
    'promise_cpu_avg_temperature_threshold': 80,
    'promise_cpu_avg_temperature_threshold_duration': 600,
    'promise_ram_available_threshold': 500e6,
    'promise_ram_avg_available_threshold': 1e9,
    'promise_ram_avg_available_threshold_duration': 600,
    'promise_network_errors_threshold': 100,
    'promise_network_lost_packets_threshold': 100,
    'promise_network_transit_recv_threshold': 100,
    'promise_network_transit_sent_threshold': 100,
    'promise_network_transit_duration': 600,
    'promise_cpu_load_threshold': 1.5,
    'promise_partition_space_threshold': 0.08,
    'promise_free_disk_space_threshold': 0.08,
    'promise_free_disk_space_nb_days_predicted': 10,
    'promise_free_disk_space_display_partition': True,
    'promise_free_disk_space_display_prediction': True
}

class TestNodeMonitoring(SlapOSInstanceTestCase):
    """
    This class test the instance
    """
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(param_dict)}

    @classmethod
    def getInstanceSoftwareType(cls):
        return "default"

    def test_instance(self):
        pass
