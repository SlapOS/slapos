# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import unittest
import random
import transaction
from AccessControl import getSecurityManager
from testSlapOSCloudSecurityGroup import TestSlapOSSecurityMixin

class TestSlapOSShadowPerson(TestSlapOSSecurityMixin):
  def test_active(self):
    password = str(random.random())
    reference = self._generateRandomUniqueReference('Person')
    shadow_reference = 'SHADOW-%s' % reference
    person = self.portal.person_module.newContent(portal_type='Person',
      reference=reference, password=password)
    person.newContent(portal_type='Assignment').open()

    transaction.commit()
    person.recursiveImmediateReindexObject()

    self._assertUserExists(reference, password)
    self._assertUserExists(shadow_reference, None)

    self.login(shadow_reference)
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-SHADOW-PERSON', 'SHADOW-%s' % reference],
      user.getGroups())

  def test_inactive(self):
    password = str(random.random())
    reference = self._generateRandomUniqueReference('Person')
    shadow_reference = 'SHADOW-%s' % reference
    person = self.portal.person_module.newContent(portal_type='Person',
      reference=reference, password=password)

    transaction.commit()
    person.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(reference, password)
    self._assertUserDoesNotExists(shadow_reference, None)

class TestSlapOSShadowComputer(TestSlapOSSecurityMixin):
  def test_active(self):
    reference = self._generateRandomUniqueReference('Computer')
    shadow_reference = 'SHADOW-%s' % reference

    computer = self.portal.computer_module.newContent(portal_type='Computer',
      reference=reference)
    computer.validate()
    computer.recursiveImmediateReindexObject()

    self._assertUserExists(reference, None)
    self._assertUserExists(shadow_reference, None)

    self.login(shadow_reference)
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-SHADOW-COMPUTER', 'SHADOW-%s' % reference],
      user.getGroups())

  def test_inactive(self):
    reference = self._generateRandomUniqueReference('Computer')
    shadow_reference = 'SHADOW-%s' % reference

    computer = self.portal.computer_module.newContent(portal_type='Computer',
      reference=reference)
    computer.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(reference, None)
    self._assertUserDoesNotExists(shadow_reference, None)

class TestSlapOSShadowSoftwareInstance(TestSlapOSSecurityMixin):
  portal_type = 'Software Instance'
  def test_active(self):
    reference = self._generateRandomUniqueReference(self.portal_type)
    shadow_reference = 'SHADOW-%s' % reference

    instance = self.portal.getDefaultModule(portal_type=self.portal_type)\
      .newContent(portal_type=self.portal_type, reference=reference)
    instance.validate()
    instance.recursiveImmediateReindexObject()

    self._assertUserExists(reference, None)
    self._assertUserExists(shadow_reference, None)

    self.login(shadow_reference)
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-SHADOW-SOFTWAREINSTANCE', 'SHADOW-%s' % reference],
      user.getGroups())

  def test_inactive(self):
    reference = self._generateRandomUniqueReference(self.portal_type)
    shadow_reference = 'SHADOW-%s' % reference

    instance = self.portal.getDefaultModule(portal_type=self.portal_type)\
      .newContent(portal_type=self.portal_type, reference=reference)
    instance.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(reference, None)
    self._assertUserDoesNotExists(shadow_reference, None)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestSlapOSShadowPerson))
  suite.addTest(unittest.makeSuite(TestSlapOSShadowComputer))
  suite.addTest(unittest.makeSuite(TestSlapOSShadowSoftwareInstance))
  return suite
