# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Nexedi SA and Contributors. All Rights Reserved.
#                    Romain Courteaud <romain@nexedi.com>
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
import transaction
from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
from AccessControl.SecurityManagement import newSecurityManager, \
  getSecurityManager, setSecurityManager
from Products.ERP5Type.tests.utils import DummyMailHost
import os
from Products.ERP5Type.Utils import convertToUpperCase

class testVifibMixin(ERP5TypeTestCase):
  """
  Mixin class for unit test of Vifib.
  """
  run_all_test = 1

  def getBusinessTemplateList(self):
    """
    Install the business templates.
    """
    result = [
      'erp5_core_proxy_field_legacy',
      'erp5_full_text_myisam_catalog',
      'erp5_ingestion_mysql_innodb_catalog',
      'erp5_base',
      'erp5_jquery',
      'erp5_ingestion',
      'erp5_web',
      'erp5_simulation',
      'erp5_pdm',
      'erp5_dms',
      'erp5_crm',
      'erp5_content_translation',
      'erp5_trade',
      'erp5_accounting',
      'erp5_jquery_ui',
      'erp5_xhtml_jquery_style',
      'erp5_software_pdm',
      'erp5_computer_immobilisation',
      'erp5_item',
      'erp5_invoicing',
      'erp5_secure_payment',
      'erp5_knowledge_pad',
      'erp5_credential',
      'erp5_tax_resource',
      'erp5_web_download_theme',
      'slapos_cloud',
      'erp5_open_trade',
      'erp5_tiosafe_core',
      'erp5_system_event',
      'erp5_simplified_invoicing',
      'erp5_rss_style',
      'erp5_project',
      'erp5_payzen_secure_payment',
      'erp5_ooo_import',
      'erp5_odt_style',
      'erp5_ods_style',
      'erp5_l10n_fr',
      'erp5_km',
      'erp5_forge',
      'erp5_discount_resource',
      'erp5_dhtml_style',
      'erp5_credential_oauth2',
      'erp5_commerce',
      'erp5_bearer_token',
      'erp5_administration',
      'erp5_accounting_l10n_fr',
      'erp5_web_shacache',
      'erp5_data_set',
      'slapos_accounting',
      'vifib_base',
      'erp5_workflow',
      'erp5_web_shadir',
      'vifib_slap',
      'slapos_rest_api_tool_portal_type',
      'erp5_configurator',
      'slapos_cache',
      'slapos_slap_tool',
      'slapos_category',
      'slapos_payzen',
      'slapos_pdm',
      'erp5_upgrader',
      'slapos_rest_api',
      'vifib_data',
      'slapos_configurator',
      'erp5_ui_test_core',
      'slapos_erp5',
      'slapos_web',
      'vifib_upgrader',
      'vifib_slapos_accounting',
      'vifib_configurator',
      'erp5_ui_test',
      # All business templates above are the dependency
      # tree of vifib_erp5, so if you mofify this list
      # make sure you also update dependency of bt.
      # You can use portal_templates.resolveBusinessTemplateListDependency(["vifib_erp5"])
      # in order to check this list.
      'vifib_erp5',
      'vifib_test',
      'vifib_web_ui_test',
    ]
    return result

  def getUserFolder(self):
    """
    Return the user folder
    """
    return getattr(self.getPortal(), 'acl_users', None)

  def loginDefaultUser(self, quiet=0):
    """
    Most of the time, we need to login before doing anything
    """
    uf = self.getUserFolder()
    uf._doAddUser('default_user', 'default_user',
                  ['Assignee', 'Assignor',
                   'Associate', 'Auditor', 'Author',
                  ], [])
    user = uf.getUserById('default_user').__of__(uf)
    newSecurityManager(None, user)

  def isLiveTest(self):
    return 'ERP5TypeLiveTestCase' in [q.__name__ for q in self.__class__.mro()]

  def setupPayZenInterface(self):
    payzen = self.portal.portal_secure_payments.vifib_payzen
    # avoid resetting prepared site
    if payzen.getServiceUsername() is None:
      payzen.setServiceUsername('12345')
    if payzen.getServicePassword() == '':
      payzen.setServicePassword('09876')

  def setupPortalAlarms(self):
    if not self.portal.portal_alarms.isSubscribed():
      self.portal.portal_alarms.subscribe()
    self.assertTrue(self.portal.portal_alarms.isSubscribed())

  def setupPortalCertificateAuthority(self):
    """Sets up portal_certificate_authority"""
    if not self.portal.hasObject('portal_certificate_authority'):
      self.portal.manage_addProduct['ERP5'].manage_addTool(
        'ERP5 Certificate Authority Tool', None)
    self.portal.portal_certificate_authority.certificate_authority_path = \
        os.environ['TEST_CA_PATH']
    transaction.commit()
    # reset test CA to have it always count from 0
    open(os.path.join(os.environ['TEST_CA_PATH'], 'serial'), 'w').write('01')
    open(os.path.join(os.environ['TEST_CA_PATH'], 'crlnumber'), 'w').write(
        '01')
    open(os.path.join(os.environ['TEST_CA_PATH'], 'index.txt'), 'w').write('')

  def createAlarmStep(self):
    def makeCallAlarm(alarm):
      def callAlarm(*args, **kwargs):
        sm = getSecurityManager()
        self.login()
        try:
          alarm.activeSense(params=kwargs)
          transaction.commit()
        finally:
          setSecurityManager(sm)
      return callAlarm
    for alarm in self.portal.portal_alarms.contentValues():
      if alarm.isEnabled():
        setattr(self, 'stepCall' + convertToUpperCase(alarm.getId()) \
          + 'Alarm', makeCallAlarm(alarm))

  def setUpMemcached(self):
    from Products.ERP5Type.tests.ERP5TypeTestCase import\
           _getVolatileMemcachedServerDict, _getPersistentMemcachedServerDict
    memcached_tool = self.getPortal().portal_memcached
    # setup default volatile distributed memcached
    connection_dict = _getVolatileMemcachedServerDict()
    url_string = '%(hostname)s:%(port)s' % connection_dict
    memcached_tool.default_memcached_plugin.setUrlString(url_string)
    # setup default persistent distributed memcached
    connection_dict = _getPersistentMemcachedServerDict()
    url_string = '%(hostname)s:%(port)s' % connection_dict
    memcached_tool.persistent_memcached_plugin.setUrlString(url_string)

  def afterSetUp(self, quiet=1, run=run_all_test):
    """
    Create ERP5 user.
    This has to be called only once.
    """
    # setup new active process for this test, in order have
    # consistency report local for one test
    sm = getSecurityManager()
    self.login()
    try:
      self.portal.portal_alarms.vifib_check_consistency.newActiveProcess()
    finally:
      setSecurityManager(sm)
    import random
    self.portal.portal_caches.erp5_site_global_id = '%s' % random.random()
    self.portal.portal_caches._p_changed = 1
    transaction.commit()
    self.portal.portal_caches.updateCache()
    self.createAlarmStep()
    if getattr(self.portal, 'set_up_once_called', 0):
      return
    else:
      self.portal.set_up_once_called = 1
      self.bootstrapSite()
      self.portal._p_changed = 1
      transaction.commit()
    self.stabiliseAccounting()

  def stabiliseAccounting(self):
      self.stepCallSlaposUpdateDeliveryCausalityStateAlarm()
      self.tic()
      self.stepCallVifibSolveAutomaticallyAlarm()
      self.tic()
      self.stepCallVifibExpandDeliveryLineAlarm()
      self.tic()
      self.stepCallSlaposTriggerBuildAlarm()
      self.tic()
      self.stepCallSlaposUpdateDeliveryCausalityStateAlarm()
      self.tic()
      self.stepCallVifibSolveAutomaticallyAlarm()
      self.tic()
      self.stepCallVifibExpandDeliveryLineAlarm()
      self.tic()
      self.stepCallSlaposTriggerBuildAlarm()
      self.tic()
      self.stepCallSlaposUpdateDeliveryCausalityStateAlarm()
      self.tic()
      self.stepCallVifibSolveAutomaticallyAlarm()
      self.tic()
      self.stepCallStopConfirmedSaleInvoiceTransactionAlarm()
      self.tic()
      self.stepCallVifibExpandDeliveryLineAlarm()
      self.tic()
      self.stepCallSlaposTriggerBuildAlarm()
      self.tic()
      self.stepCallSlaposUpdateDeliveryCausalityStateAlarm()
      self.tic()
      self.stepCallVifibSolveAutomaticallyAlarm()
      self.tic()

  def getDefaultSitePreferenceId(self):
    """Default id, usefull method to override
    """
    return "slapos_default_system_preference"

  def prepareTestUsers(self):
    """
    Prepare test users.
    """
    isTransitionPossible = self.portal.portal_workflow.isTransitionPossible
    for person in self.portal.portal_catalog(
                                  portal_type="Person",
                                  id="test_%",
                                  ):

      person = person.getObject()
      if isTransitionPossible(person, 'validate'):
        person.validate()
      for assignment in person.contentValues(portal_type='Assignment'):
        if isTransitionPossible(assignment, 'open'):
          assignment.open()

  def markManualCreation(self, document):
    self.portal.portal_workflow.doActionFor(document, 'edit_action',
      comment='Manually created by test.')

  def bootstrapSite(self):
    """
    Manager has to create an administrator user first.
    """
    if self.isLiveTest():
      # nothing to do in Live Test
      return
    self.setupPortalAlarms()
    self.setupPortalCertificateAuthority()
    self.setupPayZenInterface()
    self.setUpMemcached()
    portal = self.getPortal()
    if 'MailHost' in portal.objectIds():
      portal.manage_delObjects(['MailHost'])
    portal._setObject('MailHost', DummyMailHost('MailHost'))

    portal.email_from_address = 'romain@nexedi.com'
    portal.email_to_address = 'romain@nexedi.com'

    self.clearCache()

    self.logMessage("Bootstrap Vifib Without Security...")
    self.login()
    # Invoke Post-configurator script, this invokes all 
    # alarms related to configuration.
    self.portal.BusinessConfiguration_invokePromiseAlarmList()
    self.prepareTestUsers()
    transaction.commit()
    self.tic()
    self.logout()
    self.loginDefaultUser()

  def clearCache(self):
    self.portal.portal_caches.clearAllCache()
    self.portal.portal_workflow.refreshWorklistCache()

  # access related steps
  def stepLoginDefaultUser(self, **kw):
    self.login('default_user')

  def stepLoginTestHrAdmin(self, **kw):
    self.login('test_hr_admin')

  def stepLoginTestUpdatedVifibUser(self, **kw):
    self.login('test_updated_vifib_user')

  def stepLoginTestVifibAdmin(self, **kw):
    self.login('test_vifib_admin')

  def stepLoginTestVifibCustomer(self, **kw):
    self.login('test_vifib_customer')

  def stepLoginTestVifibCustomerA(self, **kw):
    self.login('test_vifib_customer_a')

  def stepLoginTestVifibDeveloper(self, **kw):
    self.login('test_vifib_developer')

  def stepLoginTestVifibMember(self, **kw):
    self.login('test_vifib_member')

  def stepLoginTestVifibUserAdmin(self, **kw):
    self.login('test_vifib_user_admin')

  def stepLoginTestVifibUserDeveloper(self, **kw):
    self.login('test_vifib_user_developer')

  def stepLoginERP5TypeTestCase(self, **kw):
    self.login('ERP5TypeTestCase')

  def stepLogout(self, **kw):
    self.logout()

  def checkDivergency(self):
    # there shall be no divergency
    current_skin = self.app.REQUEST.get('portal_skin', 'View')
    try:
      # Note: Worklists are cached, so in order to have next correct result
      # clear cache
      self.clearCache()
      self.changeSkin('RSS')
      diverged_document_list = self.portal.portal_catalog(
        portal_type=self.portal.getPortalDeliveryTypeList(),
        causality_state='!= solved'
      )
      self.assertFalse('to Solve' in self.portal.ERP5Site_viewWorklist(),
        'There are unsolved deliveries: %s' % ','.join([
          ' '.join((q.getTitle(), q.getPath(), q.getCausalityState())) \
          for q in diverged_document_list]))
    finally:
      self.changeSkin(current_skin)

  def stepCheckSiteConsistency(self, **kw):
    self.portal.portal_alarms.vifib_check_consistency.activeSense()
    transaction.commit()
    self.tic()
    self.assertEqual([], self.portal.portal_alarms.vifib_check_consistency\
        .Alarm_getConsistencyCheckReportLineList())
    self.assertFalse(self.portal.portal_alarms.vifib_check_consistency.sense())
    self.checkDivergency()

  def stepCleanTic(self, **kw):
    self.tic()

  def stepTic(self, **kw):
    def activateAlarm():
      sm = getSecurityManager()
      self.login()
      try:
        for alarm in self.portal.portal_alarms.contentValues():
          if alarm.isEnabled() and (alarm.getId() not in \
              ('vifib_check_consistency',)):
            alarm.activeSense()
      finally:
        setSecurityManager(sm)

    if kw.get('sequence', None) is None:
      # in case of using not in sequence commit transaction
      transaction.commit()
    # trigger activateAlarm before tic
    activateAlarm()
    transaction.commit()

    self.tic()

    # retrigger activateAlarm after tic
    activateAlarm()
    transaction.commit()

    # tic after activateAlarm
    self.tic()

    try:
      self.checkDivergency()
    except AssertionError:
      # try last time to solve deliveries
      sm = getSecurityManager()
      self.login()
      try:
        self.portal.portal_alarms.vifib_update_delivery_causality_state\
          .activeSense()
        transaction.commit()
        self.tic()
        self.portal.portal_alarms.vifib_solve_automatically.activeSense()
        transaction.commit()
        self.tic()
      finally:
        setSecurityManager(sm)
      self.checkDivergency()

