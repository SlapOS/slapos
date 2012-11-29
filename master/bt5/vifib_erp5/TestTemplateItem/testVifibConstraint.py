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

  def test_aggregate_software_installation(self):
    consistency_message_existence = 'There should be exactly one Software '\
      'Installation present in Items'

    line = self.portal.purchase_packing_list_module.newContent(
      portal_type='Purchase Packing List').newContent(
        portal_type='Purchase Packing List Line',
        resource=self.portal.portal_preferences\
          .getPreferredSoftwareSetupResource())

    self.assertTrue(consistency_message_existence in getMessageList(line))

    software_installation = self.portal.software_installation_module.newContent(
      portal_type='Software Installation')

    line.setAggregate(software_installation.getRelativeUrl())

    self.assertFalse(consistency_message_existence in getMessageList(line))

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
