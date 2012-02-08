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

class TestVifibPersonSecurity(testVifibMixin):
  """
  Test Vifib Person security
  """

  def getTitle(self):
    return "Test Vifib Person security"

  def test_base_HRAdminCanCreateDeletePerson(self):
    """
    Check if HR Admin can create and delete person document.
    """
    self.login(user_name='test_hr_admin')
    # Try to acceed the person module through restrictedTraverse
    # This will test the security of the module
    person_module_id = self.portal.getDefaultModuleId(portal_type='Person')
    person_module = self.portal.restrictedTraverse(person_module_id)
    # Create a user
    new_person = person_module.newContent(portal_type="Person")
    new_person.portal_workflow.doActionFor(new_person, "create_user_action", 
                                           reference="test_created_user", 
                                           password="test_created_password",
                                           password_confirm="test_created_password",
    )
    new_person.delete()

  def test_base_HRAdminCanInvalidatePerson(self):
    """
    Check if HR Admin can invalidate person document.
    """
    self.login(user_name='test_hr_admin')
    # Try to acceed the person module through restrictedTraverse
    # This will test the security of the module
    person_module_id = self.portal.getDefaultModuleId(portal_type='Person')
    person_module = self.portal.restrictedTraverse(person_module_id)
    # Create a user
    new_person = person_module.newContent(portal_type="Person",
                                          first_name='Test', 
                                          last_name='Invalidated Vifib User',
                                         )
    # open assignment in order to trigger open order creation
    assignment = new_person.newContent(portal_type='Assignment')
    assignment.portal_workflow.doActionFor(assignment, "open_action")
    # tic to have open order created and indexed
    self.stepTic()
    new_person.edit(career_role='client', default_email_text="test@example.com")
    new_person.portal_workflow.doActionFor(new_person, "validate_action")
    new_person.portal_workflow.doActionFor(new_person, "invalidate_action")

  def test_base_HRAdminCanCreateAssignment(self):
    """
    Check if HR Admin can access a person profile and create/update/close assignment.
    """
    self.login(user_name='test_hr_admin')
    # Try to acceed the person module through restrictedTraverse
    # This will test the security of the module
    person_module_id = self.portal.getDefaultModuleId(portal_type='Person')
    person_module = self.portal.restrictedTraverse(person_module_id)
    # Search a user
    new_person = person_module.searchFolder(id='test_updated_vifib_user')
    new_person = new_person[0].getObject()
    # Modify the user
    new_person.edit(first_name='Test', last_name='Updated Vifib User')
    # Create an assignment
    assignment = new_person.newContent(portal_type='Assignment')
    # Update the assignment
    assignment.edit(title='Test assignment')
    # Open the assignment
    assignment.portal_workflow.doActionFor(assignment, "open_action")
    # Update the assignment
    assignment.portal_workflow.doActionFor(assignment, "update_action")
    assignment.edit(title="Test Edition")
    # Open the assignment
    assignment.portal_workflow.doActionFor(assignment, "open_action")
    # Close the assignment
    assignment.portal_workflow.doActionFor(assignment, "close_action")
