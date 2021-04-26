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
import six

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..',
                     'software%s.cfg' % ("-py2" if six.PY2 else ""))))

class FluentdTestCase(SlapOSInstanceTestCase):
  __partition_reference__ = 'fluentd'

  def test_process(self):
    expected_process_name_list = [
      'fluentd-service-on-watch',
    ]

    with self.slap.instance_supervisor_rpc as supervisor:
      process_names = [process['name']
                       for process in supervisor.getAllProcessInfo()]

    for expected_process_name in expected_process_name_list:
      self.assertIn(expected_process_name, process_names)
