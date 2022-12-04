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

import json
import os

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


_setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'test.cfg')))


setup_module_executed = False
def setUpModule():
  # slapos.testing.testcase's only need to be executed once
  global setup_module_executed
  if not setup_module_executed:
    _setUpModule()
  setup_module_executed = True


class ERP5InstanceTestCase(SlapOSInstanceTestCase):
  """ERP5 base test case
  """
  @classmethod
  def getRootPartitionConnectionParameterDict(cls):
    """Return the output paramters from the root partition"""
    return json.loads(
        cls.computer_partition.getConnectionParameterDict()['_'])

  @classmethod
  def getComputerPartition(cls, partition_reference):
    for computer_partition in cls.slap.computer.getComputerPartitionList():
      if partition_reference == computer_partition.getInstanceParameter(
          'instance_title'):
        return computer_partition

  @classmethod
  def getComputerPartitionPath(cls, partition_reference):
    partition_id = cls.getComputerPartition(partition_reference).getId()
    return os.path.join(cls.slap._instance_root, partition_id)
