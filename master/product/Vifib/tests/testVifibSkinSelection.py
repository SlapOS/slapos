# -*- coding: utf-8 -*-
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
import unittest
from VifibMixin import testVifibMixin

import difflib

class TestVifibSkinSelection(testVifibMixin):
  run_all_test = 1

  def getTitle(self):
    return "Vifib Skin Selection"

  def test_01_defaultSkin(self, quiet=0, run=run_all_test):
    """
    Check default skin
    """
    if not run: return
    self.assertSameSet(
        self.portal.portal_skins.getDefaultSkin(),
        'View')

  def test_01_availableSkin(self, quiet=0, run=run_all_test):
    """
    Check that available skins are the same than production server
    """
    if not run: return
    portal = self.getPortal()
    self.assertSameSet(
        [x[0] for x in portal.portal_skins.getSkinPaths()],
        [
          'Cash',
          'Download',
          'Fiber',
          'Hosting',
          'KM',
          'Multiflex',
          'ODS',
          'ODT',
          'RSS',
          'View',
        ]
    )

  def assertSameSkinSelection(self, skin_name, selection_string_list):
    if selection_string_list.startswith('\n'):
      selection_string_list = selection_string_list[1:]
    if selection_string_list.endswith('\n'):
      selection_string_list = selection_string_list[:-1]

    installed_selection_string_list = \
      self.portal.portal_skins.getSkinPath(skin_name)

    selection_string_list = selection_string_list.split('\n')
    installed_selection_string_list = \
                            installed_selection_string_list.split(',')
    if selection_string_list != installed_selection_string_list:
      message = '\nSkin "%s" is different from production server:\n' % skin_name
      for line in difflib.unified_diff(
              selection_string_list,
              installed_selection_string_list
      ):
        message += '\t%s\n' % line

      message += '\n'
      message += 'Removed skin folder:\n'
      for i in [x for x in selection_string_list if x not in
          installed_selection_string_list]:
        message += '\t - %s\n' % i
      message += 'Added skin folder:\n'
      for i in [x for x in installed_selection_string_list if x not in
          selection_string_list]:
        message += '\t + %s\n' % i
      self.fail(message)

  def test_03_Cash_selection(self, quiet=0, run=run_all_test):
    """
    Check the skin folder order
    """
    if not run: return

    skin_name = 'Cash'
    selection_string_list = \
"""
custom
vifib_upgrader
vifib_base
vifib_cash
vifib_core
vifib_crm
vifib_forge_release
vifib_jauks_theme
vifib_jauks_widget_library
vifib_open_trade
vifib_payzen
vifib_simulation
vifib_slap
vifib_software_pdm
vifib_test
vifib_web
vifib_web_ui_test
erp5_km_theme
erp5_knowledge_pad
erp5_simulation
erp5_dms_base
erp5_dms_web
erp5_legacy_tax_system
erp5_accounting_l10n_fr
erp5_upgrader
erp5_access_tab
erp5_accounting
erp5_accounting_bbb
erp5_administration
erp5_base
erp5_commerce
erp5_commerce_widget_library
erp5_computer_immobilisation
erp5_content_translation
erp5_core
erp5_core_proxy_field_legacy
erp5_credential
erp5_crm
erp5_dhtml_style
erp5_discount_resource
erp5_dms
erp5_fckeditor
erp5_forge
erp5_forge_release
erp5_gadget
erp5_glossary
erp5_ingestion
erp5_ingestion_test
erp5_integration
erp5_invoicing
erp5_item
erp5_item_trade
erp5_jquery
erp5_ods_core
erp5_odt_core
erp5_ooo_import
erp5_open_trade
erp5_payzen_secure_payment
erp5_pdm
erp5_project
erp5_project_trade
erp5_rss_core
erp5_secure_payment
erp5_simplified_invoicing
erp5_software_pdm
erp5_system_event
erp5_tax_resource
erp5_toolbox
erp5_trade
erp5_vcs
erp5_web
erp5_web_crm
erp5_web_minimal_theme
erp5_web_widget_library
erp5_xhtml_jquery_style
erp5_xhtml_style
external_method
Images
activity
zpt_content
zpt_control
zpt_generic
"""
    self.assertSameSkinSelection(skin_name, selection_string_list)

  def test_04_Fiber_selection(self, quiet=0, run=run_all_test):
    """
    Check the skin folder order
    """
    if not run: return

    skin_name = 'Fiber'
    selection_string_list = \
"""
custom
vifib_upgrader
vifib_base
vifib_core
vifib_crm
vifib_fiber_theme
vifib_forge_release
vifib_jauks_theme
vifib_jauks_widget_library
vifib_open_trade
vifib_payzen
vifib_simulation
vifib_slap
vifib_software_pdm
vifib_test
vifib_web
vifib_web_ui_test
erp5_free_fiber_request
erp5_km_theme
erp5_knowledge_pad
erp5_simulation
erp5_dms_base
erp5_dms_web
erp5_legacy_tax_system
erp5_accounting_l10n_fr
erp5_upgrader
erp5_access_tab
erp5_accounting
erp5_accounting_bbb
erp5_administration
erp5_base
erp5_commerce
erp5_commerce_widget_library
erp5_computer_immobilisation
erp5_content_translation
erp5_core
erp5_core_proxy_field_legacy
erp5_credential
erp5_crm
erp5_dhtml_style
erp5_discount_resource
erp5_dms
erp5_fckeditor
erp5_forge
erp5_forge_release
erp5_gadget
erp5_glossary
erp5_ingestion
erp5_ingestion_test
erp5_integration
erp5_invoicing
erp5_item
erp5_item_trade
erp5_jquery
erp5_ods_core
erp5_odt_core
erp5_ooo_import
erp5_open_trade
erp5_payzen_secure_payment
erp5_pdm
erp5_project
erp5_project_trade
erp5_rss_core
erp5_secure_payment
erp5_simplified_invoicing
erp5_software_pdm
erp5_system_event
erp5_tax_resource
erp5_toolbox
erp5_trade
erp5_vcs
erp5_web
erp5_web_crm
erp5_web_minimal_theme
erp5_web_widget_library
erp5_xhtml_jquery_style
erp5_xhtml_style
external_method
Images
activity
zpt_content
zpt_control
zpt_generic
"""
    self.assertSameSkinSelection(skin_name, selection_string_list)

  def test_05_Hosting_selection(self, quiet=0, run=run_all_test):
    """
    Check the skin folder order
    """
    if not run: return

    skin_name = 'Hosting'
    selection_string_list = \
"""
custom
vifib_upgrader
vifib_base
vifib_core
vifib_crm
vifib_forge_release
vifib_hosting
vifib_hosting_theme
vifib_jauks_theme
vifib_jauks_widget_library
vifib_open_trade
vifib_payzen
vifib_simulation
vifib_slap
vifib_software_pdm
vifib_test
vifib_web
vifib_web_ui_test
erp5_km_theme
erp5_knowledge_pad
erp5_simulation
erp5_dms_base
erp5_dms_web
erp5_legacy_tax_system
erp5_accounting_l10n_fr
erp5_upgrader
erp5_access_tab
erp5_accounting
erp5_accounting_bbb
erp5_administration
erp5_base
erp5_commerce
erp5_commerce_widget_library
erp5_computer_immobilisation
erp5_content_translation
erp5_core
erp5_core_proxy_field_legacy
erp5_credential
erp5_crm
erp5_dhtml_style
erp5_discount_resource
erp5_dms
erp5_fckeditor
erp5_forge
erp5_forge_release
erp5_gadget
erp5_glossary
erp5_ingestion
erp5_ingestion_test
erp5_integration
erp5_invoicing
erp5_item
erp5_item_trade
erp5_jquery
erp5_ods_core
erp5_odt_core
erp5_ooo_import
erp5_open_trade
erp5_payzen_secure_payment
erp5_pdm
erp5_project
erp5_project_trade
erp5_rss_core
erp5_secure_payment
erp5_simplified_invoicing
erp5_software_pdm
erp5_system_event
erp5_tax_resource
erp5_toolbox
erp5_trade
erp5_vcs
erp5_web
erp5_web_crm
erp5_web_minimal_theme
erp5_web_widget_library
erp5_xhtml_jquery_style
erp5_xhtml_style
external_method
Images
activity
zpt_content
zpt_control
zpt_generic
"""
    self.assertSameSkinSelection(skin_name, selection_string_list)

  def test_06_ODS_selection(self, quiet=0, run=run_all_test):
    """
    Check the skin folder order
    """
    if not run: return

    skin_name = 'ODS'
    selection_string_list = \
"""
custom
vifib_upgrader
vifib_base
vifib_core
vifib_crm
vifib_forge_release
vifib_open_trade
vifib_payzen
vifib_simulation
vifib_slap
vifib_software_pdm
vifib_test
vifib_web_ui_test
erp5_knowledge_pad
erp5_simulation
erp5_dms_base
erp5_dms_web
erp5_legacy_tax_system
erp5_ods_style
erp5_accounting_l10n_fr
erp5_upgrader
erp5_access_tab
erp5_accounting
erp5_accounting_bbb
erp5_administration
erp5_base
erp5_commerce
erp5_commerce_widget_library
erp5_computer_immobilisation
erp5_content_translation
erp5_core
erp5_core_proxy_field_legacy
erp5_credential
erp5_crm
erp5_dhtml_style
erp5_discount_resource
erp5_dms
erp5_fckeditor
erp5_forge
erp5_forge_release
erp5_gadget
erp5_glossary
erp5_ingestion
erp5_ingestion_test
erp5_integration
erp5_invoicing
erp5_item
erp5_item_trade
erp5_ods_core
erp5_odt_core
erp5_ooo_import
erp5_open_trade
erp5_payzen_secure_payment
erp5_pdm
erp5_project
erp5_project_trade
erp5_rss_core
erp5_secure_payment
erp5_simplified_invoicing
erp5_software_pdm
erp5_system_event
erp5_tax_resource
erp5_toolbox
erp5_trade
erp5_vcs
erp5_web
erp5_web_crm
erp5_web_minimal_theme
erp5_web_widget_library
erp5_xhtml_jquery_style
external_method
Images
activity
zpt_content
zpt_control
zpt_generic
"""
    self.assertSameSkinSelection(skin_name, selection_string_list)

  def test_07_ODT_selection(self, quiet=0, run=run_all_test):
    """
    Check the skin folder order
    """
    if not run: return

    skin_name = 'ODT'
    selection_string_list = \
"""
custom
vifib_upgrader
vifib_base
vifib_core
vifib_crm
vifib_forge_release
vifib_open_trade
vifib_payzen
vifib_simulation
vifib_slap
vifib_software_pdm
vifib_test
vifib_web_ui_test
erp5_knowledge_pad
erp5_simulation
erp5_dms_base
erp5_dms_web
erp5_legacy_tax_system
erp5_odt_style
erp5_accounting_l10n_fr
erp5_upgrader
erp5_access_tab
erp5_accounting
erp5_accounting_bbb
erp5_administration
erp5_base
erp5_commerce
erp5_commerce_widget_library
erp5_computer_immobilisation
erp5_content_translation
erp5_core
erp5_core_proxy_field_legacy
erp5_credential
erp5_crm
erp5_dhtml_style
erp5_discount_resource
erp5_dms
erp5_fckeditor
erp5_forge
erp5_forge_release
erp5_gadget
erp5_glossary
erp5_ingestion
erp5_ingestion_test
erp5_integration
erp5_invoicing
erp5_item
erp5_item_trade
erp5_ods_core
erp5_odt_core
erp5_ooo_import
erp5_open_trade
erp5_payzen_secure_payment
erp5_pdm
erp5_project
erp5_project_trade
erp5_rss_core
erp5_secure_payment
erp5_simplified_invoicing
erp5_software_pdm
erp5_system_event
erp5_tax_resource
erp5_toolbox
erp5_trade
erp5_vcs
erp5_web
erp5_web_crm
erp5_web_minimal_theme
erp5_web_widget_library
erp5_xhtml_jquery_style
external_method
Images
activity
zpt_content
zpt_control
zpt_generic
"""
    self.assertSameSkinSelection(skin_name, selection_string_list)

  def test_08_View_selection(self, quiet=0, run=run_all_test):
    """
    Check the skin folder order
    """
    if not run: return

    skin_name = 'View'
    selection_string_list = \
"""
custom
vifib_upgrader
vifib_base
vifib_core
vifib_crm
vifib_forge_release
vifib_open_trade
vifib_payzen
vifib_simulation
vifib_slap
vifib_software_pdm
vifib_test
vifib_web
vifib_web_ui_test
erp5_free_fiber_request
erp5_knowledge_pad
erp5_simulation
erp5_dms_base
erp5_dms_web
erp5_legacy_tax_system
erp5_accounting_l10n_fr
erp5_upgrader
erp5_access_tab
erp5_accounting
erp5_accounting_bbb
erp5_administration
erp5_base
erp5_commerce
erp5_commerce_widget_library
erp5_computer_immobilisation
erp5_content_translation
erp5_core
erp5_core_proxy_field_legacy
erp5_credential
erp5_crm
erp5_dhtml_style
erp5_discount_resource
erp5_dms
erp5_fckeditor
erp5_forge
erp5_forge_release
erp5_gadget
erp5_glossary
erp5_html_compatibility
erp5_ingestion
erp5_ingestion_test
erp5_integration
erp5_invoicing
erp5_item
erp5_item_trade
erp5_jquery
erp5_ods_core
erp5_odt_core
erp5_ooo_import
erp5_open_trade
erp5_payzen_secure_payment
erp5_pdm
erp5_project
erp5_project_trade
erp5_rss_core
erp5_secure_payment
erp5_simplified_invoicing
erp5_software_pdm
erp5_system_event
erp5_tax_resource
erp5_toolbox
erp5_trade
erp5_vcs
erp5_web
erp5_web_crm
erp5_web_minimal_theme
erp5_web_widget_library
erp5_xhtml_jquery_style
erp5_xhtml_style
external_method
Images
activity
zpt_content
zpt_control
zpt_generic
"""
    self.assertSameSkinSelection(skin_name, selection_string_list)

  def test_10_KM_selection(self, quiet=0, run=run_all_test):
    """
    Check the skin folder order
    """
    if not run: return

    skin_name = 'KM'
    selection_string_list = \
"""
custom
vifib_upgrader
vifib_base
vifib_core
vifib_crm
vifib_forge_release
vifib_open_trade
vifib_payzen
vifib_simulation
vifib_slap
vifib_software_pdm
vifib_test
vifib_web_ui_test
erp5_km
erp5_km_theme
erp5_knowledge_pad
erp5_simulation
erp5_dms_base
erp5_dms_web
erp5_legacy_tax_system
erp5_accounting_l10n_fr
erp5_upgrader
erp5_access_tab
erp5_accounting
erp5_accounting_bbb
erp5_administration
erp5_base
erp5_commerce
erp5_commerce_widget_library
erp5_computer_immobilisation
erp5_content_translation
erp5_core
erp5_core_proxy_field_legacy
erp5_credential
erp5_crm
erp5_dhtml_style
erp5_discount_resource
erp5_dms
erp5_fckeditor
erp5_forge
erp5_forge_release
erp5_gadget
erp5_glossary
erp5_ingestion
erp5_ingestion_test
erp5_integration
erp5_invoicing
erp5_item
erp5_item_trade
erp5_jquery
erp5_km_widget_library
erp5_ods_core
erp5_odt_core
erp5_ooo_import
erp5_open_trade
erp5_payzen_secure_payment
erp5_pdm
erp5_project
erp5_project_trade
erp5_rss_core
erp5_secure_payment
erp5_simplified_invoicing
erp5_software_pdm
erp5_system_event
erp5_tax_resource
erp5_toolbox
erp5_trade
erp5_vcs
erp5_web
erp5_web_crm
erp5_web_minimal_theme
erp5_web_widget_library
erp5_xhtml_jquery_style
erp5_xhtml_style
external_method
Images
activity
zpt_content
zpt_control
zpt_generic
"""
    self.assertSameSkinSelection(skin_name, selection_string_list)

  def test_11_Multiflex_selection(self, quiet=0, run=run_all_test):
    """
    Check the skin folder order
    """
    if not run: return

    skin_name = 'Multiflex'
    selection_string_list = \
"""
custom
vifib_upgrader
vifib_base
vifib_core
vifib_crm
vifib_forge_release
vifib_open_trade
vifib_payzen
vifib_simulation
vifib_slap
vifib_software_pdm
vifib_test
vifib_web_ui_test
erp5_commerce_multiflex_layout
erp5_knowledge_pad
erp5_simulation
erp5_dms_base
erp5_dms_web
erp5_legacy_tax_system
erp5_accounting_l10n_fr
erp5_upgrader
erp5_access_tab
erp5_accounting
erp5_accounting_bbb
erp5_administration
erp5_base
erp5_commerce
erp5_commerce_widget_library
erp5_computer_immobilisation
erp5_content_translation
erp5_core
erp5_core_proxy_field_legacy
erp5_credential
erp5_crm
erp5_dhtml_style
erp5_discount_resource
erp5_dms
erp5_fckeditor
erp5_forge
erp5_forge_release
erp5_gadget
erp5_glossary
erp5_ingestion
erp5_ingestion_test
erp5_integration
erp5_invoicing
erp5_item
erp5_item_trade
erp5_ods_core
erp5_odt_core
erp5_ooo_import
erp5_open_trade
erp5_payzen_secure_payment
erp5_pdm
erp5_project
erp5_project_trade
erp5_rss_core
erp5_secure_payment
erp5_simplified_invoicing
erp5_software_pdm
erp5_system_event
erp5_tax_resource
erp5_toolbox
erp5_trade
erp5_vcs
erp5_web
erp5_web_crm
erp5_web_minimal_theme
erp5_web_widget_library
erp5_xhtml_jquery_style
external_method
Images
activity
zpt_content
zpt_control
zpt_generic
"""
    self.assertSameSkinSelection(skin_name, selection_string_list)

  def test_12_Download_selection(self, quiet=0, run=run_all_test):
    """
    Check the skin folder order
    """
    if not run: return

    skin_name = 'Download'
    selection_string_list = \
"""
custom
vifib_upgrader
vifib_base
vifib_core
vifib_crm
vifib_forge_release
vifib_open_trade
vifib_payzen
vifib_simulation
vifib_slap
vifib_software_pdm
vifib_test
vifib_web_ui_test
erp5_web_download_theme
erp5_knowledge_pad
erp5_simulation
erp5_dms_base
erp5_dms_web
erp5_legacy_tax_system
erp5_accounting_l10n_fr
erp5_upgrader
erp5_access_tab
erp5_accounting
erp5_accounting_bbb
erp5_administration
erp5_base
erp5_commerce
erp5_commerce_widget_library
erp5_computer_immobilisation
erp5_content_translation
erp5_core
erp5_core_proxy_field_legacy
erp5_credential
erp5_crm
erp5_dhtml_style
erp5_discount_resource
erp5_dms
erp5_fckeditor
erp5_forge
erp5_forge_release
erp5_gadget
erp5_glossary
erp5_ingestion
erp5_ingestion_test
erp5_integration
erp5_invoicing
erp5_item
erp5_item_trade
erp5_ods_core
erp5_odt_core
erp5_ooo_import
erp5_open_trade
erp5_payzen_secure_payment
erp5_pdm
erp5_project
erp5_project_trade
erp5_rss_core
erp5_secure_payment
erp5_simplified_invoicing
erp5_software_pdm
erp5_system_event
erp5_tax_resource
erp5_toolbox
erp5_trade
erp5_vcs
erp5_web
erp5_web_crm
erp5_web_minimal_theme
erp5_web_widget_library
erp5_xhtml_jquery_style
erp5_xhtml_style
external_method
Images
activity
zpt_content
zpt_control
zpt_generic
"""
    self.assertSameSkinSelection(skin_name, selection_string_list)

  def test_13_RSS_selection(self):
    """
    Check the skin folder order
    """
    skin_name = 'RSS'
    selection_string_list = \
"""
custom
vifib_upgrader
vifib_base
vifib_core
vifib_crm
vifib_forge_release
vifib_open_trade
vifib_payzen
vifib_simulation
vifib_slap
vifib_software_pdm
vifib_test
vifib_web_ui_test
erp5_rss_style
erp5_knowledge_pad
erp5_simulation
erp5_dms_base
erp5_dms_web
erp5_legacy_tax_system
erp5_accounting_l10n_fr
erp5_upgrader
erp5_access_tab
erp5_accounting
erp5_accounting_bbb
erp5_administration
erp5_base
erp5_commerce
erp5_commerce_widget_library
erp5_computer_immobilisation
erp5_content_translation
erp5_core
erp5_core_proxy_field_legacy
erp5_credential
erp5_crm
erp5_dhtml_style
erp5_discount_resource
erp5_dms
erp5_fckeditor
erp5_forge
erp5_forge_release
erp5_gadget
erp5_glossary
erp5_ingestion
erp5_ingestion_test
erp5_integration
erp5_invoicing
erp5_item
erp5_item_trade
erp5_ods_core
erp5_odt_core
erp5_ooo_import
erp5_open_trade
erp5_payzen_secure_payment
erp5_pdm
erp5_project
erp5_project_trade
erp5_rss_core
erp5_secure_payment
erp5_simplified_invoicing
erp5_software_pdm
erp5_system_event
erp5_tax_resource
erp5_toolbox
erp5_trade
erp5_vcs
erp5_web
erp5_web_crm
erp5_web_minimal_theme
erp5_web_widget_library
erp5_xhtml_jquery_style
external_method
Images
activity
zpt_content
zpt_control
zpt_generic
"""
    self.assertSameSkinSelection(skin_name, selection_string_list)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSkinSelection))
  return suite
