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
