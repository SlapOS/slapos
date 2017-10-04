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
from Products.PluggableAuthService.interfaces.plugins import\
                                                      IAuthenticationPlugin

class TestSlapOSSecurityMixin(testSlapOSMixin):

  def _generateRandomUniqueUserId(self, portal_type, search_key="user_id"):
    user_id = None
    while user_id is None:
      random_user_id = "test_%s_%s" % (
        portal_type.replace(" ", "_").lower(), random.random())
      result_list = self.portal.portal_catalog(
          portal_type=portal_type,
          **{search_key: random_user_id}
          )
      if not len(result_list):
        user_id = random_user_id
    return user_id

  def _generateRandomUniqueReference(self, portal_type):
    return self._generateRandomUniqueUserId(portal_type, "reference")

  def _assertUserExists(self, user_id, login, password):
    """Checks that a user with login and password exists and can log in to the
    system.
    """
    uf = self.getUserFolder()
    self.assertNotEquals(uf.getUserById(user_id, None), None)
    for _, plugin in uf._getOb('plugins').listPlugins(
                                IAuthenticationPlugin ):
      if plugin.authenticateCredentials(
                  {'login_portal_type': 'ERP5 Login',
                   'external_login': login}) is not None:
        break
    else:
      self.fail("No plugin could authenticate '%s' with password '%s'" %
              (login, password))

  def _assertUserDoesNotExists(self, user_id, login, password):
    """Checks that a user with login and password does not exists and cannot
    log in to the system.
    """
    uf = self.getUserFolder()
    for plugin_name, plugin in uf._getOb('plugins').listPlugins(
                              IAuthenticationPlugin ):
      if plugin.authenticateCredentials(
                {'login_portal_type': 'ERP5 Login',
                 'external_login': login}) is not None:
        self.fail(
           "Plugin %s should not have authenticated '%s' with password '%s'" %
           (plugin_name, login, password))

class TestSlapOSComputerSecurity(TestSlapOSSecurityMixin):
  def test_active(self):
    user_id = self._generateRandomUniqueUserId('Computer')
    reference = self._generateRandomUniqueReference('Computer')

    computer = self.portal.computer_module.newContent(
      portal_type='Computer', reference=reference)
    computer.setUserId(user_id)
    computer.validate()
    computer.newContent(portal_type='ERP5 Login',
                      reference=reference).validate()

    computer.recursiveImmediateReindexObject()

    self._assertUserExists(user_id, reference, None)

    self.login(user_id)
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-COMPUTER'],
      user.getGroups())

  def test_inactive(self):
    user_id = self._generateRandomUniqueUserId('Computer')
    reference = self._generateRandomUniqueReference('Computer')

    computer = self.portal.computer_module.newContent(
      portal_type='Computer', reference=reference)
    computer.setUserId(user_id)
    computer.newContent(portal_type='ERP5 Login',
                      reference=reference)
    computer.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(user_id, reference, None)

class TestSlapOSSoftwareInstanceSecurity(TestSlapOSSecurityMixin):
  portal_type = 'Software Instance'
  def test_active(self):
    user_id = self._generateRandomUniqueUserId(self.portal_type)
    reference = self._generateRandomUniqueReference(self.portal_type)

    instance = self.portal.getDefaultModule(portal_type=self.portal_type)\
      .newContent(portal_type=self.portal_type, reference=reference)
    instance.setUserId(user_id)
    instance.validate()
    instance.newContent(portal_type='ERP5 Login',
                      reference=reference).validate()
    instance.recursiveImmediateReindexObject()

    self._assertUserExists(user_id, reference, None)

    # instance w/o subscription is loggable and it has some roles
    self.login(user_id)
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-INSTANCE'],
      user.getGroups())

    self.login()
    subscription_reference = self._generateRandomUniqueReference(
        'Hosting Suscription')
    subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription',
        reference=subscription_reference)
    subscription.validate()
    instance.setSpecialise(subscription.getRelativeUrl())
    subscription.recursiveImmediateReindexObject()
    instance.recursiveImmediateReindexObject()

    # clear cache in order to reset calculation
    self.portal.portal_caches.clearAllCache()
    self.login(user_id)
    user = getSecurityManager().getUser()
    self.assertTrue('Authenticated' in user.getRoles())
    self.assertSameSet(['R-INSTANCE', subscription_reference],
      user.getGroups())

  def test_inactive(self):
    user_id = self._generateRandomUniqueUserId(self.portal_type)
    reference = self._generateRandomUniqueReference(self.portal_type)

    instance = self.portal.getDefaultModule(portal_type=self.portal_type)\
      .newContent(portal_type=self.portal_type, reference=reference)
    instance.setUserId(user_id)
    instance.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(user_id, reference, None)

class TestSlapOSPersonSecurity(TestSlapOSSecurityMixin):
  def test_active(self):
    password = str(random.random())
    reference = self._generateRandomUniqueReference('Person')
    user_id = self._generateRandomUniqueUserId('Person')

    person = self.portal.person_module.newContent(
      portal_type='Person',
      reference=reference, password=password)
    person.setUserId(user_id)

    person.newContent(portal_type='Assignment').open()
    person.newContent(portal_type='ERP5 Login',
      reference=reference, password=password).validate()

    self.commit()
    person.recursiveImmediateReindexObject()

    self._assertUserExists(user_id, reference, password)

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
    user_id = self._generateRandomUniqueReference('Person')
    
    person = self.portal.person_module.newContent(portal_type='Person',
      reference=reference, password=password)

    self.commit()
    person.recursiveImmediateReindexObject()

    self._assertUserDoesNotExists(user_id, reference, password)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestSlapOSComputerSecurity))
  suite.addTest(unittest.makeSuite(TestSlapOSSoftwareInstanceSecurity))
  suite.addTest(unittest.makeSuite(TestSlapOSPersonSecurity))
  return suite
