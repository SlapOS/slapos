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
from Products.SlapOS.tests.SlapOSMixin import testSlapOSMixin

class TestSlapOSShadow(testSlapOSMixin):
  def _generateRandomUniqueReference(self, portal_type):
    reference = None
    while reference is None:
      random_reference = "test_%s" % random.random()
      result_list = self.portal.portal_catalog(
          portal_type=portal_type,
          reference=random_reference,
          )
      if not len(result_list):
        reference = random_reference
    return reference

  def _assertUserExists(self, login, password):
    """Checks that a user with login and password exists and can log in to the
    system.
    """
    from Products.PluggableAuthService.interfaces.plugins import\
                                                      IAuthenticationPlugin
    uf = self.getUserFolder()
    self.assertNotEquals(uf.getUserById(login, None), None)
    for plugin_name, plugin in uf._getOb('plugins').listPlugins(
                                IAuthenticationPlugin ):
      if plugin.authenticateCredentials(
                  {'login':login,
                   'password':password,
                   'machine_login': login}) is not None:
        break
    else:
      self.fail("No plugin could authenticate '%s' with password '%s'" %
              (login, password))

  def _assertUserDoesNotExists(self, login, password):
    """Checks that a user with login and password does not exists and cannot
    log in to the system.
    """
    from Products.PluggableAuthService.interfaces.plugins import\
                                                        IAuthenticationPlugin
    uf = self.getUserFolder()
    for plugin_name, plugin in uf._getOb('plugins').listPlugins(
                              IAuthenticationPlugin ):
      if plugin.authenticateCredentials(
                {'login':login,
                 'password':password,
                 'machine_login': login}) is not None:
        self.fail(
           "Plugin %s should not have authenticated '%s' with password '%s'" %
           (plugin_name, login, password))

class TestSlapOSShadowPerson(TestSlapOSShadow):
  def test_shadow_Person(self):
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

  def test_shadow_Person_inactive(self):
    password = str(random.random())
    reference = self._generateRandomUniqueReference('Person')
    shadow_reference = 'SHADOW-%s' % reference
    person = self.portal.person_module.newContent(portal_type='Person',
      reference=reference, password=password)

    transaction.commit()
    person.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(reference, password)
    self._assertUserDoesNotExists(shadow_reference, None)

class TestSlapOSShadowComputer(TestSlapOSShadow):
  def test_shadow_Computer(self):
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

  def test_shadow_Computer_inactive(self):
    reference = self._generateRandomUniqueReference('Computer')
    shadow_reference = 'SHADOW-%s' % reference

    computer = self.portal.computer_module.newContent(portal_type='Computer',
      reference=reference)
    computer.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(reference, None)
    self._assertUserDoesNotExists(shadow_reference, None)

class TestSlapOSShadowSoftwareInstance(TestSlapOSShadow):
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
