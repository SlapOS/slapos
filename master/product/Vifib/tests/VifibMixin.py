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
from AccessControl.SecurityManagement import newSecurityManager
from Products.ERP5Type.tests.utils import DummyMailHost
import os

REQUIRED_RULE_REFERENCE_LIST = [
  'default_delivering_rule',
  'default_delivery_rule',
  'default_invoice_rule',
  'default_invoice_transaction_rule',
  'default_invoicing_rule',
  'default_order_rule',
]

REQUIRED_NOTIFICATION_MESSAGE_REFERENCE_LIST = [
  'crendential_request-confirmation-without-password',
]

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
      'erp5_upgrader',
      'vifib_upgrader',
      'erp5_full_text_myisam_catalog',
      'erp5_core_proxy_field_legacy',
      'erp5_base',
      'erp5_simulation',
      'erp5_administration',
      'erp5_pdm',
      'erp5_trade',
      'erp5_simulation_test',
      'erp5_item',
      'erp5_open_trade',
      'erp5_forge',
      'erp5_ingestion_mysql_innodb_catalog',
      'erp5_ingestion',
      'erp5_crm',
      'erp5_jquery',
      'erp5_jquery_ui',
      'erp5_knowledge_pad',
      'erp5_web',
      'erp5_dms',
      'erp5_l10n_fr',
      'erp5_content_translation',
      'erp5_software_pdm',
      'erp5_computer_immobilisation',
      'erp5_accounting',
      'erp5_accounting_l10n_fr',
      'erp5_tax_resource',
      'erp5_discount_resource',
      'erp5_invoicing',
      'erp5_ods_style',
      'erp5_odt_style',
      'erp5_ooo_import',
      'erp5_simplified_invoicing',
      'erp5_legacy_tax_system',
      'erp5_commerce',
      'erp5_project',
      'erp5_credential',
      'erp5_km',
      'erp5_web_download_theme',
      'vifib_mysql_innodb_catalog',
      'vifib_core',
      'vifib_base',
      'vifib_slap',
      'vifib_crm',
      'vifib_forge_release',
      'vifib_software_pdm',
      'vifib_web',
      'vifib_open_trade',
      'vifib_l10n_fr',
      'vifib_datas',
      'vifib_erp5',
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

  def setupPortalCertificateAuthority(self):
    """Sets up portal_certificate_authority"""
    if not self.portal.hasObject('portal_certificate_authority'):
      self.portal.manage_addProduct['Vifib'].manage_addTool(
        'ERP5 Certificate Authority Tool', None)
    self.portal.portal_certificate_authority.certificate_authority_path = \
        os.environ['TEST_CA_PATH']
    self.portal.portal_certificate_authority.openssl_binary = os.environ[
        'OPENSSL_BINARY']
    transaction.commit()
    # reset test CA to have it always count from 0
    open(os.path.join(os.environ['TEST_CA_PATH'], 'serial'), 'w').write('01')
    open(os.path.join(os.environ['TEST_CA_PATH'], 'crlnumber'), 'w').write(
        '01')
    open(os.path.join(os.environ['TEST_CA_PATH'], 'index.txt'), 'w').write('')

  def afterSetUp(self, quiet=1, run=run_all_test):
    """
    Create ERP5 user.
    This has to be called only once.
    """
    self.setupPortalCertificateAuthority()
    import random
    self.portal.portal_caches.erp5_site_global_id = '%s' % random.random()
    self.portal.portal_caches._p_changed = 1
    transaction.commit()
    self.portal.portal_caches.updateCache()
    if getattr(self.portal, 'set_up_once_called', 0):
      return
    else:
      self.portal.set_up_once_called = 1
      self.bootstrapSite()
      self.portal._p_changed = 1
      transaction.commit()

  def setPreference(self):
    # Enable default preference
    preference = self.portal.portal_preferences.default_site_preference
    # XXX-Luke: checking for preference state is no op (in such early state
    # this preference is disabled anyway), but in my environment enable does
    # not work, UNTIL getPreferenceState is called. Possibly cache/
    # /configuration issue, to be checked later
    if preference.getPreferenceState() == 'disabled':
      preference.enable()

  def getDefaultSitePreferenceId(self):
    """Default id, usefull method to override
    """
    return "vifib_default_system_preference"

  def setSystemPreference(self):
    """Configures and enables default system preference"""
    default_system_preference = self.portal.portal_preferences\
        .restrictedTraverse(self.getDefaultSitePreferenceId())
    default_system_preference.edit(
      preferred_credential_recovery_automatic_approval=1,
      preferred_credential_request_automatic_approval=1,
      preferred_subscription_assignment_category=['function/customer',
        'role/internal'],
    )
    if default_system_preference.getPreferenceState() == 'disabled':
      default_system_preference.enable()

  def setupNotificationModule(self):
    module = self.portal.notification_message_module
    isTransitionPossible = self.portal.portal_workflow.isTransitionPossible

    for reference in REQUIRED_NOTIFICATION_MESSAGE_REFERENCE_LIST:
      for message in module.searchFolder(portal_type='Notification Message',
        reference=reference):
        message = message.getObject()
        if isTransitionPossible(message, 'validate'):
          message.validate()

  def setupRuleTool(self):
    """Validates newest version of each rule from REQUIRED_RULE_REFERENCE_LIST"""
    rule_tool = self.portal.portal_rules
    isTransitionPossible = self.portal.portal_workflow.isTransitionPossible
    for rule_reference in REQUIRED_RULE_REFERENCE_LIST:
      rule_list = rule_tool.searchFolder(
        reference=rule_reference,
        limit=1,
        sort_on=(('version', 'DESC'),)
      )
      self.assertEqual(1, len(rule_list), '%s not found' % rule_reference)
      rule = rule_list[0].getObject()
      if isTransitionPossible(rule, 'validate'):
        rule.validate()

  def openAssignments(self):
    """
    Change workflow state of test data imported by the bt5
    """
    for person in self.portal.portal_catalog(
                                  portal_type="Person",
                                  id="test_%",
                                  ):
      person = person.getObject()
      for assignment in person.contentValues(portal_type='Assignment'):
        assignment.open()

  def setupVifibMachineAuthenticationPlugin(self):
    """Sets up Vifib Authentication plugin"""
    pas = self.getPortal().acl_users
    vifib_auth_list = [q for q in pas.objectValues() \
        if q.meta_type == 'Vifib Machine Authentication Plugin']
    if len(vifib_auth_list) == 0:
      vifib_dispacher = pas.manage_addProduct['Vifib']
      vifib_dispacher.addVifibMachineAuthenticationPlugin('vifib_auth')
      vifib_auth = pas.vifib_auth
    else:
      if len(vifib_auth_list) > 1:
        raise ValueError('More then one Vifib authentication')
      vifib_auth = vifib_auth_list[0]
    vifib_auth.manage_activateInterfaces(('IAuthenticationPlugin',
        'IExtractionPlugin', 'IGroupsPlugin', 'IUserEnumerationPlugin'))

  def bootstrapSite(self):
    """
    Manager has to create an administrator user first.
    """
    portal = self.getPortal()
    if 'MailHost' in portal.objectIds():
      portal.manage_delObjects(['MailHost'])
    portal._setObject('MailHost', DummyMailHost('MailHost'))

    portal.email_from_address = 'romain@nexedi.com'
    portal.email_to_address = 'romain@nexedi.com'

    self.clearCache()

    # Change module ID generator
    for module_id in portal.objectIds(spec=('ERP5 Folder',)) + \
          ["portal_simulation", "portal_activities"]:
      module = portal.restrictedTraverse(module_id)
      module.setIdGenerator('_generatePerDayId')

    self.logMessage("Bootstrap Vifib Without Security...")
    self.login()
    self.setupVifibMachineAuthenticationPlugin()
    self.setPreference()
    self.setSystemPreference()
    self.setupRuleTool()
    self.setupNotificationModule()
    self.openAssignments()
    transaction.commit()
    self.tic()
    self.logout()
    self.loginDefaultUser()

  def clearCache(self):
    self.portal.portal_caches.clearAllCache()
    self.portal.portal_workflow.refreshWorklistCache()

  def stepClearCache(self, sequence=None, sequence_list=None, **kw):
    self.clearCache()

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
