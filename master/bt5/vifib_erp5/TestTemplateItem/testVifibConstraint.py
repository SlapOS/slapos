##############################################################################
#
# Copyright (c) 2002-2011 Nexedi SA and Contributors. All Rights Reserved.
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

import random
def rndstr():
  return str(random.random())

def getMessageList(o):
  return [str(q.getMessage()) for q in o.checkConsistency()]

class TestVifibSoftwareProductConstraint(testVifibMixin):
  def getTitle(self):
    return "Vifib Software Product Constraint checks"

  def test_title_not_empty(self):
    software_product = self.portal.software_product_module.newContent(
      portal_type='Software Product')
    consistency_message = 'Title should be defined'
    self.assertTrue(consistency_message in getMessageList(software_product))

    software_product.edit(title=rndstr())
    self.assertFalse(consistency_message in getMessageList(software_product))

  def test_title_unique(self):
    title = rndstr()
    title_2 = rndstr()
    consistency_message = 'Title already exists'

    software_product = self.portal.software_product_module.newContent(
      portal_type='Software Product', title=title)
    software_product_2 = self.portal.software_product_module.newContent(
      portal_type='Software Product', title=title)

    self.stepTic()

    self.assertTrue(consistency_message in getMessageList(software_product))
    self.assertTrue(consistency_message in getMessageList(software_product_2))

    software_product_2.setTitle(title_2)

    self.stepTic()

    self.assertFalse(consistency_message in getMessageList(software_product))
    self.assertFalse(consistency_message in getMessageList(software_product_2))

class TestVifibAssignmentConstraint(testVifibMixin):
  def getTitle(self):
    return "Vifib Assignment Constraint checks"

  def test_parent_person_validated(self):
    person = self.portal.person_module.newContent(portal_type='Person')
    assignment = person.newContent(portal_type='Assignment')

    consistency_message = 'The person document has to be validated to start '\
      'assignment'
    self.assertTrue(consistency_message in getMessageList(assignment))

    person.validate()

    self.assertFalse(consistency_message in getMessageList(assignment))

class TestVifibComputerConstraint(testVifibMixin):
  def getTitle(self):
    return "Vifib Computer Constraint checks"

  def test_title_not_empty(self):
    computer = self.portal.computer_module.newContent(portal_type='Computer')
    consistency_message = 'Title must be defined'

    self.assertTrue(consistency_message in getMessageList(computer))

    computer.setTitle(rndstr())

    self.assertFalse(consistency_message in getMessageList(computer))

  def test_reference_not_empty(self):
    computer = self.portal.computer_module.newContent(portal_type='Computer')
    consistency_message = 'Reference must be defined'

    self.assertTrue(consistency_message in getMessageList(computer))

    computer.setReference(rndstr())

    self.assertFalse(consistency_message in getMessageList(computer))

  def test_reference_unique(self):
    reference = rndstr()
    reference_2 = rndstr()
    computer = self.portal.computer_module.newContent(portal_type='Computer',
      reference=reference)
    computer_2 = self.portal.computer_module.newContent(portal_type='Computer',
      reference=reference)
    consistency_message = 'Reference must be unique'

    self.stepTic()

    self.assertTrue(consistency_message in getMessageList(computer))
    self.assertTrue(consistency_message in getMessageList(computer_2))

    computer_2.setReference(reference_2)
    self.stepTic()

    self.assertFalse(consistency_message in getMessageList(computer))
    self.assertFalse(consistency_message in getMessageList(computer_2))

class TestVifibEmailConstraint(testVifibMixin):
  def getTitle(self):
    return "Vifib Email Constraint checks"

  def test_url_string_not_empty(self):
    email = self.portal.person_module.newContent(portal_type='Person'
      ).newContent(portal_type='Email')
    consistency_message = 'Email must be defined'

    self.assertTrue(consistency_message in getMessageList(email))

    email.setUrlString(rndstr())

    self.assertFalse(consistency_message in getMessageList(email))

  def test_url_string_unique(self):
    url_string = rndstr()
    url_string_2 = rndstr()
    email = self.portal.person_module.newContent(portal_type='Person'
      ).newContent(portal_type='Email', url_string=url_string)
    email_2 = self.portal.person_module.newContent(portal_type='Person'
      ).newContent(portal_type='Email', url_string=url_string)
    consistency_message = 'Email must be unique'

    self.stepTic()
    self.assertTrue(consistency_message in getMessageList(email))
    self.assertTrue(consistency_message in getMessageList(email_2))

    email_2.setUrlString(url_string_2)
    self.stepTic()
    self.assertFalse(consistency_message in getMessageList(email))
    self.assertFalse(consistency_message in getMessageList(email_2))

class TestVifibInternalPackingListConstraint(testVifibMixin):
  def getTitle(self):
    return "Vifib Internal Packing List Constraint checks"

  def test_reference_not_empty(self):
    ipl = self.portal.internal_packing_list_module.newContent(
      portal_type='Internal Packing List')
    # reference is set during object creation, set reset it
    ipl.setReference(None)
    consistency_message = 'Reference must be defined'

    self.assertTrue(consistency_message in getMessageList(ipl))

    ipl.setReference(rndstr())

    self.assertFalse(consistency_message in getMessageList(ipl))

  def test_start_date_not_empty(self):
    ipl = self.portal.internal_packing_list_module.newContent(
      portal_type='Internal Packing List')
    consistency_message = 'Property start_date must be defined'

    self.assertTrue(consistency_message in getMessageList(ipl))

    ipl.setStartDate('2011/01/01')

    self.assertFalse(consistency_message in getMessageList(ipl))

  def test_destination_not_empty(self):
    ipl = self.portal.internal_packing_list_module.newContent(
      portal_type='Internal Packing List')
    destination = self.portal.organisation_module.newContent(
      portal_type='Organisation')
    consistency_message = 'Destination must be defined'

    self.assertTrue(consistency_message in getMessageList(ipl))

    ipl.setDestination(destination.getRelativeUrl())

    self.assertFalse(consistency_message in getMessageList(ipl))

  def test_destination_validated(self):
    destination = self.portal.organisation_module.newContent(
      portal_type='Organisation')
    ipl = self.portal.internal_packing_list_module.newContent(
      portal_type='Internal Packing List',
      destination=destination.getRelativeUrl())
    consistency_message = 'Destination must be validated'

    self.assertTrue(consistency_message in getMessageList(ipl))
    destination.validate()
    self.assertFalse(consistency_message in getMessageList(ipl))

  def test_source_validated(self):
    source = self.portal.organisation_module.newContent(
      portal_type='Organisation')
    ipl = self.portal.internal_packing_list_module.newContent(
      portal_type='Internal Packing List',
      source=source.getRelativeUrl())
    consistency_message = 'Source must be validated'

    self.assertTrue(consistency_message in getMessageList(ipl))
    source.validate()
    self.assertFalse(consistency_message in getMessageList(ipl))

  def test_lines_existance(self):
    ipl = self.portal.internal_packing_list_module.newContent(
      portal_type='Internal Packing List')
    ipl.confirm()
    consistency_message = 'Internal Packing List Line is not defined'

    self.assertTrue(consistency_message in getMessageList(ipl))
    ipl.newContent(portal_type='Internal Packing List Line')
    self.assertFalse(consistency_message in getMessageList(ipl))

class TestVifibInternalPackingListLineConstraint(testVifibMixin):
  def getTitle(self):
    return "Vifib Internal Packing List Line Constraint checks"

  def test_quantity_existence(self):
    ipl = self.portal.internal_packing_list_module.newContent(
      portal_type='Internal Packing List')
    ipl.confirm()
    line = ipl.newContent(portal_type='Internal Packing List Line')

    consistency_message = 'Property quantity must be defined'

    self.assertTrue(consistency_message in getMessageList(line))

    line.setQuantity(1.0)

    self.assertFalse(consistency_message in getMessageList(line))

  def test_resource(self):
    ipl = self.portal.internal_packing_list_module.newContent(
      portal_type='Internal Packing List')
    ipl.confirm()
    line = ipl.newContent(portal_type='Internal Packing List Line')

    consistency_message = 'Resource must be defined'

    self.assertTrue(consistency_message in getMessageList(line))

    resource = self.portal.service_module.newContent(portal_type='Service')
    line.setResource(resource.getRelativeUrl())

    self.assertFalse(consistency_message in getMessageList(line))

  def test_aggregate_computer(self):
    ipl = self.portal.internal_packing_list_module.newContent(
      portal_type='Internal Packing List')
    ipl.confirm()
    line = ipl.newContent(portal_type='Internal Packing List Line')

    consistency_message = 'There should be exactly one Computer present in Items'

    self.assertTrue(consistency_message in getMessageList(line))

    aggregate = self.portal.computer_module.newContent(portal_type='Computer')
    line.setAggregate(aggregate.getRelativeUrl())

    self.assertFalse(consistency_message in getMessageList(line))

class TestVifibPersonConstraint(testVifibMixin):
  def getTitle(self):
    return "Vifib Person Constraint checks"

  def test_last_name_existence(self):
    person = self.portal.person_module.newContent(portal_type='Person')
    consistency_message = 'Property last_name must be defined'

    self.assertTrue(consistency_message in getMessageList(person))

    person.setLastName(rndstr())

    self.assertFalse(consistency_message in getMessageList(person))

  def test_role(self):
    person = self.portal.person_module.newContent(portal_type='Person')
    consistency_message = 'One role should be defined'
    self.assertTrue(consistency_message in getMessageList(person))

    role_id_list = list(self.portal.portal_categories.role.objectIds())
    self.assertTrue(len(role_id_list) >= 2)
    person.setRole(role_id_list[0])
    self.assertFalse(consistency_message in getMessageList(person))

    person.setRoleList(role_id_list)
    self.assertTrue(consistency_message in getMessageList(person))
    person.setRole(role_id_list[0])
    self.assertFalse(consistency_message in getMessageList(person))

  def test_subordination_state(self):
    organisation = self.portal.organisation_module.newContent(
      portal_type='Organisation')
    person = self.portal.person_module.newContent(portal_type='Person',
      subordination=organisation.getRelativeUrl())
    consistency_message = 'The Organisation is not validated'

    self.assertTrue(consistency_message in getMessageList(person))

    organisation.validate()

    self.assertFalse(consistency_message in getMessageList(person))

  def test_email(self):
    person = self.portal.person_module.newContent(portal_type='Person')
    consistency_message = 'Person have to contain an Email'

    self.assertTrue(consistency_message in getMessageList(person))

    person.newContent(portal_type='Email')

    self.assertFalse(consistency_message in getMessageList(person))

class TestVifibPurchasePackingListConstraint(testVifibMixin):
  def getTitle(self):
    return "Vifib Purchase Packing List Constraint checks"

  def test_reference_not_empty(self):
    ppl = self.portal.purchase_packing_list_module.newContent(
      portal_type='Purchase Packing List')
    consistency_message = 'Reference must be defined'

    # reset reference, as set during object creation
    ppl.setReference(None)

    self.assertTrue(consistency_message in getMessageList(ppl))

    ppl.setReference(rndstr())

    self.assertFalse(consistency_message in getMessageList(ppl))

  def test_start_date_existence(self):
    ppl = self.portal.purchase_packing_list_module.newContent(
      portal_type='Purchase Packing List')
    consistency_message = 'Property start_date must be defined'

    self.assertTrue(consistency_message in getMessageList(ppl))

    ppl.setStartDate('2011/01/01')

    self.assertFalse(consistency_message in getMessageList(ppl))

  def test_lines(self):
    ppl = self.portal.purchase_packing_list_module.newContent(
      portal_type='Purchase Packing List')
    consistency_message = 'Purchase Packing List Line is not defined'

    self.assertTrue(consistency_message in getMessageList(ppl))

    ppl.newContent(portal_type='Purchase Packing List Line')

    self.assertFalse(consistency_message in getMessageList(ppl))

class TestVifibPurchasePackingListLineConstraint(testVifibMixin):
  def getTitle(self):
    return "Vifib Purchase Packing List Line Constraint checks"

  def test_aggregate_computer(self):
    consistency_message_existence = 'There should be exactly one Computer '\
      'present in Items'
    consistency_message_state = 'Computer must be validated'

    line = self.portal.purchase_packing_list_module.newContent(
      portal_type='Purchase Packing List').newContent(
        portal_type='Purchase Packing List Line',
        resource=self.portal.portal_preferences\
          .getPreferredSoftwareSetupResource())

    self.assertTrue(consistency_message_existence in getMessageList(line))

    computer = self.portal.computer_module.newContent(portal_type='Computer')

    line.setAggregate(computer.getRelativeUrl())

    self.assertFalse(consistency_message_existence in getMessageList(line))
    self.assertTrue(consistency_message_state in getMessageList(line))

    computer.validate()
    self.assertFalse(consistency_message_state in getMessageList(line))

  def test_aggregate_software_release(self):
    consistency_message_existence = 'There should be exactly one Software '\
      'Release present in Items'
    consistency_message_state = 'Software Release must be validated'

    line = self.portal.purchase_packing_list_module.newContent(
      portal_type='Purchase Packing List').newContent(
        portal_type='Purchase Packing List Line',
        resource=self.portal.portal_preferences\
          .getPreferredSoftwareSetupResource())

    self.assertTrue(consistency_message_existence in getMessageList(line))

    software_release = self.portal.software_release_module.newContent(
      portal_type='Software Release')

    line.setAggregate(software_release.getRelativeUrl())

    self.assertFalse(consistency_message_existence in getMessageList(line))
    self.assertTrue(consistency_message_state in getMessageList(line))

    software_release.publish()
    self.assertFalse(consistency_message_state in getMessageList(line))

  def test_resource(self):
    consistency_message_existence = 'Resource must be defined'
    consistency_message_state = 'Resource must be validated'

    line = self.portal.purchase_packing_list_module.newContent(
      portal_type='Purchase Packing List').newContent(
        portal_type='Purchase Packing List Line')

    self.assertTrue(consistency_message_existence in getMessageList(line))

    resource = self.portal.service_module.newContent(portal_type='Service')

    line.setResource(resource.getRelativeUrl())

    self.assertFalse(consistency_message_existence in getMessageList(line))
    self.assertTrue(consistency_message_state in getMessageList(line))

    resource.validate()
    self.assertFalse(consistency_message_state in getMessageList(line))

  def test_quantity(self):
    consistency_message = 'Property quantity must be defined'

    ppl = self.portal.purchase_packing_list_module.newContent(
      portal_type='Purchase Packing List')
    ppl.confirm()

    line = ppl.newContent(
        portal_type='Purchase Packing List Line')

    self.assertTrue(consistency_message in getMessageList(line))

    line.setQuantity(1.0)

    self.assertFalse(consistency_message in getMessageList(line))

class TestVifibSoftwareReleaseConstraint(testVifibMixin):
  def test_aggregate(self):
    consistency_message_existence = 'One Software Product must be defined'
    consistency_message_state = 'Software Product must be validated'

    software_release = self.portal.software_release_module.newContent(
      portal_type='Software Release')
    software_release.publish()

    self.assertTrue(consistency_message_existence in getMessageList(
      software_release))

    software_product = self.portal.software_product_module.newContent(
      portal_type='Software Product')

    software_release.setAggregate(software_product.getRelativeUrl())

    self.assertFalse(consistency_message_existence in getMessageList(
      software_release))

    software_product_2 = self.portal.software_product_module.newContent(
      portal_type='Software Product')

    software_release.setAggregateList([software_product.getRelativeUrl(),
      software_product_2.getRelativeUrl()])

    self.assertTrue(consistency_message_existence in getMessageList(
      software_release))

    software_release.setAggregate(software_product.getRelativeUrl())

    self.assertTrue(consistency_message_state in getMessageList(
      software_release))

    software_product.validate()

    self.assertFalse(consistency_message_state in getMessageList(
      software_release))

  def test_contributor(self):
    consistency_message_existence = 'One Contributor must be defined'
    consistency_message_state = 'Contributor must be validated'

    software_release = self.portal.software_release_module.newContent(
      portal_type='Software Release')

    self.assertTrue(consistency_message_existence in getMessageList(
      software_release))

    person = self.portal.person_module.newContent(
      portal_type='Person')

    #XXX: Conflict: contributor is category and dublin core property
    #software_release.setContributor(person.getRelativeUrl())
    software_release.setContributorValue(person)

    self.assertFalse(consistency_message_existence in getMessageList(
      software_release))

    person_2 = self.portal.person_module.newContent(
      portal_type='Person')

    #XXX: Conflict: contributor is category and dublin core property
    #software_release.setContributorList([person.getRelativeUrl(),
    #  person_2.getRelativeUrl()])
    software_release.setContributorValueList([person, person_2])

    self.assertTrue(consistency_message_existence in getMessageList(
      software_release))

    #XXX: Conflict: contributor is category and dublin core property
    #software_release.setContributor(person.getRelativeUrl())
    software_release.setContributorValue(person)

    self.assertTrue(consistency_message_state in getMessageList(
      software_release))

    person.validate()

    self.assertFalse(consistency_message_state in getMessageList(
      software_release))

  def test_reference(self):
    consistency_message = 'Reference must be defined'

    software_release = self.portal.software_release_module.newContent(
      portal_type='Software Release')

    self.assertTrue(consistency_message in getMessageList(software_release))

    software_release.setReference(rndstr())

    self.assertFalse(consistency_message in getMessageList(software_release))

  def test_language(self):
    consistency_message = 'Language should be defined'

    software_release = self.portal.software_release_module.newContent(
      portal_type='Software Release')

    self.assertTrue(consistency_message in getMessageList(software_release))

    software_release.setLanguage(rndstr())

    self.assertFalse(consistency_message in getMessageList(software_release))

  def test_version(self):
    consistency_message_existence = 'Version should be defined'
    consistency_message_unicity = 'Version already exists'
    reference = rndstr()

    software_release = self.portal.software_release_module.newContent(
      portal_type='Software Release', reference=reference)

    self.assertTrue(consistency_message_existence in getMessageList(
      software_release))

    version = rndstr()

    software_release.setVersion(version)

    self.assertFalse(consistency_message_existence in getMessageList(
      software_release))

    software_release_2 = self.portal.software_release_module.newContent(
      portal_type='Software Release', version=version, reference=reference)

    software_release.publish()
    software_release_2.publish()
    self.stepTic()

    self.assertTrue(consistency_message_unicity in getMessageList(
      software_release))
    self.assertTrue(consistency_message_unicity in getMessageList(
      software_release_2))

    software_release_2.setVersion(rndstr())

    self.stepTic()

    self.assertFalse(consistency_message_unicity in getMessageList(
      software_release))
    self.assertFalse(consistency_message_unicity in getMessageList(
      software_release_2))
