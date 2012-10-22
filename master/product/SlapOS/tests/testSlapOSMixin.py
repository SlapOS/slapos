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

import unittest
import Products.Vifib.tests.VifibMixin

class testSlapOSMixin(Products.Vifib.tests.VifibMixin.testVifibMixin):
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
      'erp5_workflow',
      'erp5_configurator',
      'vifib_configurator',
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
      'vifib_slapos_rest_api_tool_portal_type',
      'vifib_slapos_rest_api',
      'vifib_slapos_rest_api_v1',
      'vifib_slapos_accounting',
      'vifib_mysql_innodb_catalog',
      'vifib_base',
      'vifib_open_trade',
      'vifib_slap',
      'vifib_forge_release',
      'vifib_software_pdm',
      'vifib_payzen',
      'vifib_web',
      'vifib_web_ui_test',
      'vifib_l10n_fr',
      'vifib_data',
      'vifib_data_category',
      'vifib_data_web',
      'vifib_data_payzen',
      'vifib_data_simulation',
      'vifib_agent',
      'vifib_slapos_capacity',
      'vifib_erp5',
      'vifib_test',
      'vifib_slapos_rest_api_v1_test',
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
