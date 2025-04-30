##############################################################################
#
# Copyright (c) 2025 Nexedi SA and Contributors. All Rights Reserved.
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

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'software.cfg')
  )
)


class WendelinTelecomTestCase(SlapOSInstanceTestCase):
  __partition_reference__ = 'WT-' # Short name to avoid HAProxy UNIX socket name length error
  instance_max_retry = 20 # Needs time to be ready

  @classmethod
  def getGatewayHost(cls) -> str:
    return 'placeholder-host-address'

  @classmethod
  def getInstanceParameterDict(cls) -> dict:
    return {'gateway-host': cls.getGatewayHost()}

  @classmethod
  def getSharedInstanceConfigurations(cls) -> dict:
    return {
      "ors-no-parameters": {},
      "ors-valid-tag": {'fluentbit-tag': 'ors000_COMP-0000_e0x00000'}
    }

  @classmethod
  def requestDefaultInstance(cls, state='started'):
    default_instance =  super(
      SlapOSInstanceTestCase, cls).requestDefaultInstance(state=state)
    cls.requestSharedInstances()
    return default_instance

  @classmethod
  def requestSharedInstance(cls, partition_reference, partition_parameter_kw, state='started'):
    software_url = cls.getSoftwareURL()
    cls.logger.debug('Requesting shared "%s"', partition_reference)
    return cls.slap.request(
      software_release=software_url,
      software_type='default',
      partition_reference=partition_reference,
      partition_parameter_kw=partition_parameter_kw,
      shared=True,
      state=state
    )

  @classmethod
  def requestSharedInstances(cls):
    shared_instance_parameter_dict = cls.getSharedInstanceConfigurations()
    for partition_reference, partition_parameter_kw in shared_instance_parameter_dict.items():
      cls.requestSharedInstance(partition_reference, partition_parameter_kw)

  def test_ors_registration_no_parameters(self):
    self.slap.waitForInstance(self.instance_max_retry) # Wait until publish is complete

    shared_instance_configuration_dict = self.getSharedInstanceConfigurations()
    shared_instance = self.requestSharedInstance(
      "ors-no-parameters",
      shared_instance_configuration_dict['ors-no-parameters']
    )

    connection_parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()['_'])
    self.assertEqual(
      str(len(shared_instance_configuration_dict)),
      connection_parameter_dict['slave-amount']
    )
    self.assertEqual(
      {'1_information': "Parameter 'fluentbit-tag' not found, cannot register"},
      shared_instance.getConnectionParameterDict()
    )

  def test_ors_registration_valid_parameters(self):
    self.slap.waitForInstance(self.instance_max_retry) # Wait until publish is complete

    shared_instance_configuration_dict = self.getSharedInstanceConfigurations()
    shared_instance = self.requestSharedInstance(
      "ors-valid-tag",
      shared_instance_configuration_dict['ors-valid-tag']
    )

    connection_parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()['_'])
    self.assertEqual(
      str(len(shared_instance_configuration_dict)),
      connection_parameter_dict['slave-amount']
    )
    # XXX: Cannot test successful registration as ERP5/Wendelin cannot be installed
    # The registration script therefore doesn't exist
    self.assertEqual(
      {'1_information': "Registration request failed with status code 404 Not Found"},
      shared_instance.getConnectionParameterDict()
    )
