# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import os

class TestSlapOSConfigurator(testSlapOSMixin):

  def testConfiguredModuleGeneratorIDViaConstraint(self):
    """ Make sure Generator ID is well configured, in this
        case we trust on promise outcome."""
    self.assertEquals(self.portal.portal_ids.checkConsistency(), [])

  def testConfiguredShacacheWebSite(self):
    """ Make sure Shacache WebSite is setuped by Alarm
        case we trust on promise outcome."""
    self.assertEquals(self.portal.web_site_module.checkConsistency(), [])

  def testConfiguredCacheViaConstraint(self):
    """ Make sure Volitile and Persistent Cache was configured well,
        invoking the consistency to check """
    self.assertEquals(self.portal.portal_memcached.checkConsistency(), [])

  def testConfiguredConversionServerViaConstraint(self):
    """ Make sure Conversion Server was configured well,
        invoking checkConsistency """
    self.assertEquals(self.portal.portal_preferences.checkConsistency(), [])

  def testConfiguredCertificateAuthoringConstraint(self):
    """Make sure Certificate Authoring was configured well,
       invoking checkConsistency.

       Make sure PAS is well configured."""
    self.assertEquals(self.portal.portal_certificate_authority.checkConsistency(), [])

  def testConfiguredTemplateToolViaConstraint(self):
    """ Make sure Template Tool Repositories was configured well,
        invoking checkConsistency """
    self.assertEquals(
        [ i for i in self.portal.portal_templates.checkConsistency()
                     if "(reinstall)" not in i.message], [])


  def testConfiguredVolatileCache(self):
    """  Make sure Memcached is configured
    """
    if self.isLiveTest():
      # This test is redundant with testConfiguredVolatileCacheViaPromise
      # and it is only aims to verify if test environment is behaving as
      # expected, nothing else, and if alamrs were invoked.
      return
    from Products.ERP5Type.tests.ERP5TypeTestCase import \
                                         _getVolatileMemcachedServerDict

    memcached_tool = self.getPortal().portal_memcached
    connection_dict = _getVolatileMemcachedServerDict()
    url_string = 'erp5-memcached-volatile:%(port)s' % connection_dict
    self.assertEquals(memcached_tool.default_memcached_plugin.getUrlString(),
                      url_string)

  def testConfiguredPersistentCache(self):
    """ Make sure Kumofs is configured
    """
    if self.isLiveTest():
      # This test is redundant with testConfiguredVolatileCacheViaPromise
      # and it is only aims to verify if test environment is behaving as
      # expected, nothing else, and if alamrs were invoked.
      return

    from Products.ERP5Type.tests.ERP5TypeTestCase import\
            _getPersistentMemcachedServerDict
    memcached_tool = self.getPortal().portal_memcached
    connection_dict = _getPersistentMemcachedServerDict()
    url_string = 'erp5-memcached-persistent:%(port)s' % connection_dict
    self.assertEquals(memcached_tool.persistent_memcached_plugin.getUrlString(),
                      url_string)

  def testConfiguredConversionServer(self):
    """ Make sure Conversion Server (Cloudooo) is
        well configured """
    if self.isLiveTest():
      # This test is redundant with testConfiguredConversionServerViaConstraint
      # and it is only aims to verify if test environment is behaving as
      # expected, nothing else, and if alamrs were invoked.
      return

    from Products.ERP5Type.tests.ERP5TypeTestCase import\
           _getConversionServerUrl
    # set preference
    preference_tool = self.portal.portal_preferences
    conversion_url = _getConversionServerUrl()
    self.assertEquals(preference_tool.getPreferredDocumentConversionServerUrl(), conversion_url)

  def testConfiguredCertificateAuthoring(self):
    """ Make sure Certificate Authoting is
        well configured. """

    if self.isLiveTest():
      # This test is redundant with testConfiguredVolatileCacheViaPromise
      # and it is only aims to verify if test environment is behaving as
      # expected, nothing else, and if alamrs were invoked.
      return

    self.assertTrue(self.portal.hasObject('portal_certificate_authority'))
    self.assertEquals(os.environ['TEST_CA_PATH'],
          self.portal.portal_certificate_authority.certificate_authority_path)

  def testConfiguredBusinessTemplateList(self):
    """ Make sure Installed business Templates are
        what it is expected.  """

    expected_business_template_list = [
      'erp5_core',
      'erp5_xhtml_style',
      'erp5_property_sheets',
      'erp5_mysql_innodb_catalog',
      'erp5_upgrader',
      'slapos_upgrader',
      'erp5_full_text_myisam_catalog',
      'erp5_core_proxy_field_legacy',
      'erp5_base',
      'erp5_administration',
      'erp5_workflow',
      'erp5_configurator',
      'slapos_configurator',
      'erp5_simulation',
      'erp5_pdm',
      'erp5_trade',
      'erp5_tiosafe_core',
      'erp5_item',
      'erp5_forge',
      'erp5_ingestion_mysql_innodb_catalog',
      'erp5_ingestion',
      'erp5_crm',
      'erp5_system_event',
      'erp5_secure_payment',
      'erp5_payzen_secure_payment',
      'erp5_ooo_import',
      'erp5_odt_style',
      'erp5_ods_style',
      'erp5_jquery',
      'erp5_jquery_plugin_colorpicker',
      'erp5_jquery_plugin_elastic',
      'erp5_jquery_plugin_jqchart',
      'erp5_jquery_plugin_mbmenu',
      'erp5_jquery_plugin_sheet',
      'erp5_jquery_sheet_editor',
      'erp5_jquery_ui',
      'erp5_dhtml_style',
      'erp5_knowledge_pad',
      'erp5_web',
      'erp5_rss_style',
      'erp5_dms',
      'erp5_content_translation',
      'erp5_software_pdm',
      'erp5_svg_editor',
      'erp5_computer_immobilisation',
      'erp5_open_trade',
      'erp5_accounting',
      'erp5_commerce',
      'erp5_credential',
      'erp5_km',
      'erp5_web_download_theme',
      'erp5_web_shacache',
      'erp5_data_set',
      'erp5_web_shadir',
      'erp5_invoicing',
      'erp5_simplified_invoicing',
      'erp5_credential_oauth2',
      'erp5_accounting_l10n_fr',
      'erp5_ace_editor',
      'erp5_code_mirror',
      'erp5_font',
      'erp5_hal_json_style',
      'erp5_l10n_fr',
      'erp5_l10n_zh',
      'erp5_movement_table_catalog',
      'erp5_web_renderjs_ui',
      'erp5_web_service',
      'slapos_ecoallocation',
	    'slapos_jio',
      'slapos_l10n_zh',
      'slapos_trial_request',
      'erp5_bearer_token',
      'erp5_access_token',
      'erp5_project',
      'slapos_cache',
      'slapos_cloud',
      'slapos_slap_tool',
      'slapos_category',
      'slapos_rest_api_tool_portal_type',
      'slapos_rest_api',
      'slapos_pdm',
      'slapos_crm',
      'slapos_accounting',
      'slapos_payzen',
      'slapos_web',
      'slapos_erp5',
    ]
    self.assertSameSet(expected_business_template_list,
      self.portal.portal_templates.getInstalledBusinessTemplateTitleList())
