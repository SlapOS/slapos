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
import Products.Vifib.tests.VifibMixin
from Products.ERP5Type.tests.utils import DummyMailHost

class testSlapOSMixin(Products.Vifib.tests.VifibMixin.testVifibMixin):
  def afterSetUp(self):
    if self.isLiveTest():
      # nothing to do in Live Test
      return
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

  def bootstrapSite(self):
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

    self.login()
    # Invoke Post-configurator script, this invokes all 
    # alarms related to configuration.
    self.portal.BusinessConfiguration_invokePromiseAlarmList()
    transaction.commit()
    self.tic()
    self.logout()
    self.loginDefaultUser()

  def getBusinessTemplateList(self):
    """
    Install the business templates.
    """
    result = [
      'erp5_upgrader',
      'vifib_upgrader', # XXX: rebrand
      'erp5_full_text_myisam_catalog',
      'erp5_core_proxy_field_legacy',
      'erp5_base',
      'erp5_workflow',
      'erp5_configurator',
      'vifib_configurator', # XXX: rebrand
      'erp5_simulation',
      'erp5_administration',
      'erp5_pdm',
      'erp5_trade',
      'erp5_item',
      'erp5_open_trade',
      'erp5_forge',
      'erp5_ingestion_mysql_innodb_catalog',
      'erp5_ingestion',
      'erp5_crm',
      'erp5_jquery',
      'erp5_jquery_ui',
      'erp5_dhtml_style',
      'erp5_knowledge_pad',
      'erp5_web',
      'erp5_dms',
      'erp5_l10n_fr',
      'erp5_content_translation',
      'erp5_software_pdm',
      'erp5_computer_immobilisation',
      'erp5_accounting',
      'erp5_accounting_l10n_fr',
      'erp5_bearer_token',
      'erp5_tax_resource',
      'erp5_discount_resource',
      'erp5_invoicing',
      'erp5_ods_style',
      'erp5_odt_style',
      'erp5_rss_style',
      'erp5_ooo_import',
      'erp5_simplified_invoicing',
      'erp5_commerce',
      'erp5_project',
      'erp5_xhtml_jquery_style',
      'erp5_credential',
      'erp5_credential_oauth2',
      'erp5_km',
      'erp5_web_download_theme',
      'erp5_tiosafe_core',
      'erp5_system_event',
      'erp5_secure_payment',
      'erp5_payzen_secure_payment',
      'erp5_ui_test_core',
      'erp5_ui_test',
      'slapos_cloud',
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
