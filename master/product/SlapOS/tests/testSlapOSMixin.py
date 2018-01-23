# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Vifib SA and Contributors. All Rights Reserved.
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

import random
import transaction
import unittest
from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
from Products.ERP5Type.tests.utils import DummyMailHost
from Products.ERP5Type.Utils import convertToUpperCase
import os
import glob
from AccessControl.SecurityManagement import getSecurityManager, \
    setSecurityManager
from App.config import getConfiguration

config = getConfiguration()

class testSlapOSMixin(ERP5TypeTestCase):

  abort_transaction = 0

  def clearCache(self):
    self.portal.portal_caches.clearAllCache()
    self.portal.portal_workflow.refreshWorklistCache()

  #def getDefaultSitePreferenceId(self):
  #  """Default id, usefull method to override
  #  """
  #  return "slapos_default_system_preference"

  def createAlarmStep(self):
    def makeCallAlarm(alarm):
      def callAlarm(*args, **kwargs):
        sm = getSecurityManager()
        self.login()
        try:
          alarm.activeSense(params=kwargs)
          self.commit()
        finally:
          setSecurityManager(sm)
      return callAlarm
    for alarm in self.portal.portal_alarms.contentValues():
      if alarm.isEnabled():
        setattr(self, 'stepCall' + convertToUpperCase(alarm.getId()) \
          + 'Alarm', makeCallAlarm(alarm))

  def createCertificateAuthorityFile(self):
    """Sets up portal_certificate_authority"""
    # reset test CA to have it always count from 0
    open(os.path.join(os.environ['TEST_CA_PATH'], 'serial'), 'w').write('01')
    open(os.path.join(os.environ['TEST_CA_PATH'], 'crlnumber'), 'w').write(
        '01')
    open(os.path.join(os.environ['TEST_CA_PATH'], 'index.txt'), 'w').write('')
    private_list = glob.glob('%s/*.key' % os.path.join(os.environ['TEST_CA_PATH'],
                              'private'))
    for private in private_list:
      os.remove(private)
    crl_list = glob.glob('%s/*' % os.path.join(os.environ['TEST_CA_PATH'],
                              'crl'))
    for crl in crl_list:
      os.remove(crl)
    certs_list = glob.glob('%s/*' % os.path.join(os.environ['TEST_CA_PATH'],
                              'certs'))
    for cert in certs_list:
      os.remove(cert)
    newcerts_list = glob.glob('%s/*' % os.path.join(os.environ['TEST_CA_PATH'],
                              'newcerts'))
    for newcert in newcerts_list:
      os.remove(newcert)


  def setupPortalAlarms(self):
    if not self.portal.portal_alarms.isSubscribed():
      self.portal.portal_alarms.subscribe()
    self.assertTrue(self.portal.portal_alarms.isSubscribed())

  def isLiveTest(self):
    #return 'ERP5TypeLiveTestCase' in [q.__name__ for q in self.__class__.mro()]
    # XXX - What is the better way to no if we are in live test mode ?
    return not os.environ.has_key('TEST_CA_PATH')

  def _setUpDummyMailHost(self):
    """Do not play with NON persistent replacement of MailHost"""
    if not self.isLiveTest():
      ERP5TypeTestCase._setUpDummyMailHost(self)

  def _restoreMailHost(self):
    """Do not play with NON persistent replacement of MailHost"""
    if not self.isLiveTest():
      ERP5TypeTestCase._restoreMailHost(self)

  def beforeTearDown(self):
    if self.isLiveTest():
      self.deSetUpPersistentDummyMailHost()
    if self.abort_transaction:
      transaction.abort()

  def getUserFolder(self):
    """
    Return the user folder
    """
    return getattr(self.getPortal(), 'acl_users', None)

  def setUpOnce(self):
    self.commit()
    self.portal.portal_templates.updateRepositoryBusinessTemplateList(
       repository_list=self.portal.portal_templates.getRepositoryList())
    self.commit()
    self.launchConfigurator()

  def afterSetUp(self):
    self.login()
    self.createAlarmStep()

    if self.isLiveTest():
      self.setUpPersistentDummyMailHost()
      return
    self.portal.portal_caches.erp5_site_global_id = '%s' % random.random()
    self.portal.portal_caches._p_changed = 1
    self.commit()
    self.portal.portal_caches.updateCache()

    try:
      initsite = config.product_config["initsite"]
    except KeyError:
      initsite = {}

    if initsite.get("cloudooo_url", None) is None:
      from Products.ERP5Type.tests.ERP5TypeTestCase import\
                  _getConversionServerUrl
      initsite["cloudooo_url"] = _getConversionServerUrl()

    config.product_config["initsite"] = initsite

    if not getattr(self.portal, 'is_site_bootstrapped', 0):
      self.portal.is_site_bootstrapped = 1
      self.bootstrapSite()
      self.portal._p_changed = 1
      self.commit()

  def deSetUpPersistentDummyMailHost(self):
    if 'MailHost' in self.portal.objectIds():
      self.portal.manage_delObjects(['MailHost'])
    self.portal.manage_addProduct['MailHost'].manage_addMailHost('MailHost')
    self.commit()

  def setUpPersistentDummyMailHost(self):
    if 'MailHost' in self.portal.objectIds():
      self.portal.manage_delObjects(['MailHost'])
    self.portal._setObject('MailHost', DummyMailHost('MailHost'))

    self.portal.email_from_address = 'romain@nexedi.com'
    self.portal.email_to_address = 'romain@nexedi.com'

  def getBusinessConfiguration(self):
    return self.portal.business_configuration_module[\
                          "slapos_master_configuration_workflow"]

  def launchConfigurator(self):
    self.login()
    # Create new Configuration 
    business_configuration  = self.getBusinessConfiguration()

    response_dict = {}
    while response_dict.get("command", "next") != "install":
      response_dict = self.portal.portal_configurator._next(
                            business_configuration, {})

    self.tic() 
    self.portal.portal_configurator.startInstallation(
                 business_configuration,REQUEST=self.portal.REQUEST)

  def bootstrapSite(self):
    self.setupPortalAlarms()
    self.createCertificateAuthorityFile()
    self.getDefaultSystemPreference().setPreferredHateoasUrl("http://dummy/")

    self.clearCache()
    self.tic()

  def getBusinessTemplateList(self):
    """
    Install the business templates.
    """
    result = [
      'erp5_full_text_myisam_catalog',
      'erp5_core_proxy_field_legacy',
      'erp5_base',
      'erp5_workflow',
      'erp5_configurator',
      'slapos_configurator',
      'erp5_ui_test_core'
    ]
    return result

class TestSlapOSDummy(testSlapOSMixin):
  run_all_test = 1
  def test(self):
    """Dummy test in order to fire up Business Template testing"""
    self.assertTrue(True)

  def getTitle(self):
    return "Dummy tests in order to have tests from BT5 run"

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestSlapOSDummy))
  return suite
