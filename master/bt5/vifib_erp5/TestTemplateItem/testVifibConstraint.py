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
