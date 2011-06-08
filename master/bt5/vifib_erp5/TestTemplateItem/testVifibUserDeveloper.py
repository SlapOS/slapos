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

class TestVifibUserDeveloper(testVifibMixin):
  """
  Test Vifib User: developer access to the system
  """

  def getTitle(self):
    return "Test Vifib User Developer security"

  def test_base_UserDeveloperCanCreateSoftwareRelease(self):
    """
    Check if developer can create software release
    """
    login_id = 'test_vifib_user_developer'
    self.login(user_name=login_id)
    # Try to acceed the software release module through restrictedTraverse
    # This will test the security of the module
    software_release_module_id = self.portal.getDefaultModuleId(portal_type='Software Release')
    software_release_module = self.portal.restrictedTraverse(software_release_module_id)
    # Add software_release
    software_release = software_release_module.newContent(portal_type='Software Release')
    # User has to access his person profile
    person_module_id = self.portal.getDefaultModuleId(portal_type='Person')
    person_module = self.portal.restrictedTraverse(person_module_id)
    person_value = person_module.restrictedTraverse(login_id)
    # Edit the computer
    software_release.edit(
      title='Test Vifib Software Release',
      reference='test_software_release',
      version=1,
      language='en',
      url_string='http://example.com/live_test_software_release.cfg',
      contributor_value=person_value,
    )
    # Submit software release
    software_release.portal_workflow.doActionFor(software_release, 'submit_action')
    # Check if he can still access it
    self.portal.restrictedTraverse(software_release.getRelativeUrl())

    self.logout()
    self.login(user_name='test_vifib_developer')
    # Try to acceed the software product module through restrictedTraverse
    # This will test the security of the module
    software_product_module_id = self.portal.getDefaultModuleId(portal_type='Software Product')
    software_product_module = self.portal.restrictedTraverse(software_product_module_id)
    # Add software_release
    software_product = software_product_module.newContent(portal_type='Software Product')
    # Put some information
    software_product.edit(
      title='test software product',
    )
    software_product.portal_workflow.doActionFor(software_product, 'publish_action')
    # Edit software release
    software_release.edit(
      aggregate_value=software_product,
    )
    # Accept software release
    software_release.portal_workflow.doActionFor(software_release, 'publish_action')

