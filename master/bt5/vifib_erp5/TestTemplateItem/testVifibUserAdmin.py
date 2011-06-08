##############################################################################
#
# Copyright (c) 2002-2010 Nexedi SA and Contributors. All Rights Reserved.
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
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################

from VifibMixin import testVifibMixin
import uuid
from DateTime import DateTime
import transaction

class TestVifibUserAdmin(testVifibMixin):
  """
  Test Vifib User: admin access to the system
  """

  def getTitle(self):
    return "Test Vifib User Admin security"

  def afterSetUp(self):
    testVifibMixin.afterSetUp(self)
    portal_activities = self.portal.portal_activities
    if portal_activities.isSubscribed():
      self.activity_tool_was_subscribed = 1
      portal_activities.unsubscribe()

  def beforeTearDown(self):
    if getattr(self, 'activity_tool_was_subscribed', 0):
      portal_activities = self.portal.portal_activities
      portal_activities.subscribe()
    testVifibMixin.beforeTearDown(self)

  def test_base_UseradminCanCreateComputer(self):
    """
    Check if Administrator should be able to register new computer
    """
    login_id = 'test_vifib_user_admin'
    self.login(user_name=login_id)
    # Try to acceed the person module through restrictedTraverse
    # This will test the security of the module
    computer_module_id = self.portal.getDefaultModuleId(portal_type='Computer')
    computer_module = self.portal.restrictedTraverse(computer_module_id)
    # Add computer
    computer = computer_module.newContent(portal_type='Computer')
    # Edit the computer
    computer.edit(
      title='Test Vifib Computer',
      reference='test_%s' % uuid.uuid4().hex,
    )

    # Access internal packing list module
    internal_packing_list_id = self.portal.getDefaultModuleId(portal_type='Internal Packing List')
    internal_packing_list_module = self.portal.restrictedTraverse(internal_packing_list_id)
    # Create the IPL
    internal_packing_list = internal_packing_list_module.newContent(
      portal_type='Internal Packing List',
    )
    # User has to access his person profile
    person_module_id = self.portal.getDefaultModuleId(portal_type='Person')
    person_module = self.portal.restrictedTraverse(person_module_id)
    person_value = person_module.restrictedTraverse(login_id)
    # Edit IPL data
    internal_packing_list.edit(
      start_date=DateTime(),
      source_administration_value=person_value,
      destination_value=person_value,
      destination_section_value=person_value,
    )
    # Access service
    service_module_id = self.portal.getDefaultModuleId(portal_type='Service')
    service_module = self.portal.restrictedTraverse(service_module_id)
    service_value = service_module.restrictedTraverse('computer_registration')
    # Edit line
    internal_packing_list_line = internal_packing_list.newContent(
      portal_type='Internal Packing List Line',
      resource_value=service_value,
      quantity=1,
      aggregate_value=computer,
    )
    # Deliver IPL
    internal_packing_list.portal_workflow.doActionFor(internal_packing_list, 'confirm_action')
    internal_packing_list.portal_workflow.doActionFor(internal_packing_list, 'stop_action')
    self.assertEquals('building', internal_packing_list.getCausalityState())
    transaction.commit()
    self.stepTic()
    transaction.commit()

    self.logout()
    # Computer registration has to be validated by a Vifib System Administrator
    self.login(user_name='test_vifib_admin')
    self.assertEquals('solved', internal_packing_list.getCausalityState())
    internal_packing_list.portal_workflow.doActionFor(internal_packing_list, 'deliver_action')

    self.logout()
    self.login(user_name=login_id)

    # Validate computer
    computer.portal_workflow.doActionFor(computer, 'validate_action')
    # Invalidate Computer
    computer.portal_workflow.doActionFor(computer, 'invalidate_action')


  def test_base_UseradminCanRequestSoftwareInstallation(self):
    login_id = 'test_vifib_user_admin'
    self.login(user_name=login_id)

    # Try to acceed the person module through restrictedTraverse
    # This will test the security of the module
    computer_module_id = self.portal.getDefaultModuleId(portal_type='Computer')
    computer_module = self.portal.restrictedTraverse(computer_module_id)
    # Add computer
    computer = computer_module.newContent(portal_type='Computer')
    # Edit the computer
    computer.edit(
      title='Test Vifib Computer',
      reference='test_%s' % uuid.uuid4().hex,
    )

    # Access internal packing list module
    internal_packing_list_id = self.portal.getDefaultModuleId(portal_type='Internal Packing List')
    internal_packing_list_module = self.portal.restrictedTraverse(internal_packing_list_id)
    # Create the IPL
    internal_packing_list = internal_packing_list_module.newContent(
      portal_type='Internal Packing List',
    )
    # User has to access his person profile
    person_module_id = self.portal.getDefaultModuleId(portal_type='Person')
    person_module = self.portal.restrictedTraverse(person_module_id)
    person_value = person_module.restrictedTraverse(login_id)
    # Edit IPL data
    internal_packing_list.edit(
      start_date=DateTime(),
      source_administration_value=person_value,
      destination_value=person_value,
      destination_section_value=person_value,
    )
    # Access service
    service_module_id = self.portal.getDefaultModuleId(portal_type='Service')
    service_module = self.portal.restrictedTraverse(service_module_id)
    service_value = service_module.restrictedTraverse('computer_registration')
    # Edit line
    internal_packing_list_line = internal_packing_list.newContent(
      portal_type='Internal Packing List Line',
      resource_value=service_value,
      quantity=1,
      aggregate_value=computer,
    )
    # Deliver IPL
    internal_packing_list.portal_workflow.doActionFor(internal_packing_list, 'confirm_action')
    internal_packing_list.portal_workflow.doActionFor(internal_packing_list, 'stop_action')
    self.assertEquals('building', internal_packing_list.getCausalityState())
    transaction.commit()
    self.stepTic()
    transaction.commit()

    self.logout()
    # Computer registration has to be validated by a Vifib System Administrator
    self.login(user_name='test_vifib_admin')
    self.assertEquals('solved', internal_packing_list.getCausalityState())
    internal_packing_list.portal_workflow.doActionFor(internal_packing_list, 'deliver_action')

    self.logout()
    self.login(user_name=login_id)

    # Access software release to install
    software_release_module_id = self.portal.getDefaultModuleId(portal_type='Software Release')
    software_release_module = self.portal.restrictedTraverse(software_release_module_id)
    software_release = software_release_module.restrictedTraverse('test_software_release')

    # User has to access his person profile
    person_module_id = self.portal.getDefaultModuleId(portal_type='Person')
    person_module = self.portal.restrictedTraverse(person_module_id)
    person_value = person_module.restrictedTraverse(login_id)

    # Access purchase packing list module
    purchase_packing_list_module_id = self.portal.getDefaultModuleId(portal_type='Purchase Packing List')
    purchase_packing_list_module = self.portal.restrictedTraverse(purchase_packing_list_module_id)
    # Create PPL
    purchase_packing_list = purchase_packing_list_module.newContent(
      portal_type='Purchase Packing List')
    purchase_packing_list.edit(
      start_date=DateTime(),
      destination_decision_value=person_value,
    )

    # Access service
    service_module_id = self.portal.getDefaultModuleId(portal_type='Service')
    service_module = self.portal.restrictedTraverse(service_module_id)
    service_value = service_module.restrictedTraverse(self.portal.portal_preferences.getPreferredInstanceHostingResource())

    # Create PPLL
    purchase_packing_list_line = purchase_packing_list.newContent(
      portal_type='Purchase Packing List Line')
    purchase_packing_list_line.edit(
      resource_value=service_value,
      aggregate_value_list=[computer, software_release],
    )
    purchase_packing_list.portal_workflow.doActionFor(purchase_packing_list, 'confirm_action')
