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
from Products.SlapOS.tests.testSlapOSMixin import testSlapOSMixin

class TestSlapOSSecurityMixin(testSlapOSMixin):
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

class TestSlapOSComputerSecurity(TestSlapOSSecurityMixin):
  def test_active(self):
    reference = self._generateRandomUniqueReference('Computer')

    computer = self.portal.computer_module.newContent(portal_type='Computer',
      reference=reference)
    computer.validate()
    computer.recursiveImmediateReindexObject()

    self._assertUserExists(reference, None)

    self.login(reference)
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-COMPUTER'],
      user.getGroups())

  def test_inactive(self):
    reference = self._generateRandomUniqueReference('Computer')

    computer = self.portal.computer_module.newContent(portal_type='Computer',
      reference=reference)
    computer.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(reference, None)

class TestSlapOSSoftwareInstanceSecurity(TestSlapOSSecurityMixin):
  portal_type = 'Software Instance'
  def test_active(self):
    reference = self._generateRandomUniqueReference(self.portal_type)

    instance = self.portal.getDefaultModule(portal_type=self.portal_type)\
      .newContent(portal_type=self.portal_type, reference=reference)
    instance.validate()
    instance.recursiveImmediateReindexObject()

    self._assertUserExists(reference, None)

    # instance w/o subscription is loggable and it has some roles
    self.login(reference)
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-INSTANCE'],
      user.getGroups())

    self.login()
    subscription_reference = self._generateRandomUniqueReference(
        'Hosting Suscription')
    subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription', reference=subscription_reference)
    subscription.validate()
    instance.setSpecialise(subscription.getRelativeUrl())
    subscription.recursiveImmediateReindexObject()
    instance.recursiveImmediateReindexObject()

    # clear cache in order to reset calculation
    self.portal.portal_caches.clearAllCache()
    self.login(reference)
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-INSTANCE', subscription_reference],
      user.getGroups())

  def test_inactive(self):
    reference = self._generateRandomUniqueReference(self.portal_type)

    instance = self.portal.getDefaultModule(portal_type=self.portal_type)\
      .newContent(portal_type=self.portal_type, reference=reference)
    instance.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(reference, None)

class TestSlapOSPersonSecurity(TestSlapOSSecurityMixin):
  def test_active(self):
    password = str(random.random())
    reference = self._generateRandomUniqueReference('Person')
    person = self.portal.person_module.newContent(portal_type='Person',
      reference=reference, password=password)
    person.newContent(portal_type='Assignment').open()

    self.commit()
    person.recursiveImmediateReindexObject()

    self._assertUserExists(reference, password)

    self.login(person.getUserId())
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet([], user.getGroups())


    # add to group category
    self.login()
    person.newContent(portal_type='Assignment', group='company').open()
    self.commit()
    person.recursiveImmediateReindexObject()


    self.tic()
    self.portal.portal_caches.clearAllCache()
    self.login(person.getUserId())
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['G-COMPANY'], user.getGroups())

    # add to role category
    self.login()
    person.newContent(portal_type='Assignment', role='member').open()
    person.recursiveImmediateReindexObject()

    self.portal.portal_caches.clearAllCache()
    self.login(person.getUserId())
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-MEMBER', 'G-COMPANY'], user.getGroups())

  def test_inactive(self):
    password = str(random.random())
    reference = self._generateRandomUniqueReference('Person')
    person = self.portal.person_module.newContent(portal_type='Person',
      reference=reference, password=password)

    self.commit()
    person.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(reference, password)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestSlapOSComputerSecurity))
  suite.addTest(unittest.makeSuite(TestSlapOSSoftwareInstanceSecurity))
  suite.addTest(unittest.makeSuite(TestSlapOSPersonSecurity))
  return suite
