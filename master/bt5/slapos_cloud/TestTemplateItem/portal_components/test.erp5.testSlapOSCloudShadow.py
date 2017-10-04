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
from AccessControl import getSecurityManager
from erp5.component.test.testSlapOSCloudSecurityGroup import TestSlapOSSecurityMixin

class TestSlapOSShadowPerson(TestSlapOSSecurityMixin):
  def test_active(self):
    password = str(random.random())
    reference = self._generateRandomUniqueReference('Person')
    user_id = self._generateRandomUniqueUserId('Person')
    shadow_user_id = 'SHADOW-%s' % user_id

    person = self.portal.person_module.newContent(
      portal_type='Person')
    person.setUserId(user_id)
    person.newContent(portal_type='Assignment').open()

    person.newContent(portal_type='ERP5 Login',
          reference=reference, password=password).validate()
    self.commit()
    person.recursiveImmediateReindexObject()

    self._assertUserExists(user_id, reference, password)

    # XXX shadow user cannot login himself.
    self._assertUserExists(shadow_user_id, reference, None)

    self.login(shadow_user_id)
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-SHADOW-PERSON', 'SHADOW-%s' % user_id],
      user.getGroups())

  def test_inactive(self):
    password = str(random.random())
    reference = self._generateRandomUniqueReference('Person')
    user_id = self._generateRandomUniqueUserId('Person')

    shadow_user_id = 'SHADOW-%s' % user_id
    person = self.portal.person_module.newContent(
      portal_type='Person')
    person.setUserId(user_id)

    self.commit()
    person.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(user_id, reference, password)
    self._assertUserDoesNotExists(shadow_user_id, reference, None)

class TestSlapOSShadowComputer(TestSlapOSSecurityMixin):
  def test_active(self):
    reference = self._generateRandomUniqueReference('Computer')
    user_id = self._generateRandomUniqueUserId('Computer')

    shadow_user_id = 'SHADOW-%s' % user_id

    computer = self.portal.computer_module.newContent(portal_type='Computer',
      reference=reference)
    computer.setUserId(user_id)

    computer.newContent(portal_type='ERP5 Login',
          reference=reference).validate()

    computer.validate()
    computer.recursiveImmediateReindexObject()

    self._assertUserExists(user_id, reference, None)
    self._assertUserExists(shadow_user_id, reference, None)

    self.login(shadow_user_id)
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-SHADOW-COMPUTER', 'SHADOW-%s' % user_id],
      user.getGroups())

  def test_inactive(self):
    reference = self._generateRandomUniqueReference('Computer')
    user_id = self._generateRandomUniqueUserId('Computer')

    shadow_reference = 'SHADOW-%s' % reference

    computer = self.portal.computer_module.newContent(portal_type='Computer',
      reference=reference)
    computer.setUserId(user_id)

    computer.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(user_id, reference, None)
    self._assertUserDoesNotExists(user_id, shadow_reference, None)

class TestSlapOSShadowSoftwareInstance(TestSlapOSSecurityMixin):
  portal_type = 'Software Instance'
  def test_active(self):
    reference = self._generateRandomUniqueReference(self.portal_type)
    user_id = self._generateRandomUniqueUserId(self.portal_type)

    shadow_user_id = 'SHADOW-%s' % user_id

    instance = self.portal.getDefaultModule(portal_type=self.portal_type)\
      .newContent(portal_type=self.portal_type, reference=reference)
    instance.setUserId(user_id)
    instance.newContent(portal_type='ERP5 Login',
          reference=reference).validate()
    instance.validate()
    instance.recursiveImmediateReindexObject()

    self._assertUserExists(user_id, reference, None)
    self._assertUserExists(shadow_user_id, reference, None)

    self.login(shadow_user_id)
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-SHADOW-SOFTWAREINSTANCE', 'SHADOW-%s' % user_id],
      user.getGroups())

  def test_inactive(self):
    reference = self._generateRandomUniqueReference(self.portal_type)
    user_id = self._generateRandomUniqueUserId(self.portal_type)

    shadow_reference = 'SHADOW-%s' % reference

    instance = self.portal.getDefaultModule(portal_type=self.portal_type)\
      .newContent(portal_type=self.portal_type, reference=reference)
    instance.setUserId(user_id)
    instance.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(user_id, reference, None)
    self._assertUserDoesNotExists(user_id, shadow_reference, None)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestSlapOSShadowPerson))
  suite.addTest(unittest.makeSuite(TestSlapOSShadowComputer))
  suite.addTest(unittest.makeSuite(TestSlapOSShadowSoftwareInstance))
  return suite
