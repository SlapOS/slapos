# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin, withAbort
from zExceptions import Unauthorized
from DateTime import DateTime
import os
import time

class TestSlapOSConfigurator(testSlapOSMixin):

  def testConfiguredVolatileCache(self):
    """
      Make sure Memcached is configured
    """
    from Products.ERP5Type.tests.ERP5TypeTestCase import \
                                         _getVolatileMemcachedServerDict

    memcached_tool = self.getPortal().portal_memcached
    connection_dict = _getVolatileMemcachedServerDict()
    url_string = '%(hostname)s:%(port)s' % connection_dict
    self.assertEquals(memcached_tool.default_memcached_plugin.getUrlString(),
                      url_string)

  def testConfiguredPersistentCache(self):
    """
      Make sure Kumofs is configured
    """
    from Products.ERP5Type.tests.ERP5TypeTestCase import\
            _getPersistentMemcachedServerDict
    memcached_tool = self.getPortal().portal_memcached
    connection_dict = _getPersistentMemcachedServerDict()
    url_string = '%(hostname)s:%(port)s' % connection_dict
    self.assertEquals(memcached_tool.persistent_memcached_plugin.getUrlString(),
                      url_string)
 
  def testConfiguredConversionServer(self):
    """
      Make sure Conversion Server (Cloudooo) is 
      well configured
    """
    from Products.ERP5Type.tests.ERP5TypeTestCase import\
            _getConversionServerDict
    # set preference
    preference_tool = self.portal.portal_preferences
    conversion_dict = _getConversionServerDict()
    self.assertEquals(preference_tool.getPreferredOoodocServerAddress(),conversion_dict['hostname'])
    self.assertEquals(preference_tool.getPreferredOoodocServerPortNumber(), conversion_dict['port'])

  def testConfiguredCertificateAuthoring(self):
    """
      Make sure Certificate Authoting is
      well configured.
    """
    self.assertTrue(self.portal.hasObject('portal_certificate_authority'))
    self.assertEquals(os.environ['TEST_CA_PATH'],
          self.portal.portal_certificate_authority.certificate_authority_path)

  def testConfiguredBusinessTemplateList(self):
    """
      Make sure Installed business Templates are
      what it is expected.
    """
    expected_business_template_list = [
      'erp5_core',
      'erp5_xhtml_style',
      'erp5_property_sheets',
      'erp5_mysql_innodb_catalog',
      'erp5_promise',
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
      'erp5_jquery_ui',
      'erp5_dhtml_style',
      'erp5_knowledge_pad',
      'erp5_web',
      'erp5_rss_style',
      'erp5_dms',
      'erp5_content_translation',
      'erp5_software_pdm',
      'erp5_computer_immobilisation',
      'erp5_open_trade',
      'erp5_accounting',
      'erp5_commerce',
      'erp5_xhtml_jquery_style',
      'erp5_credential',
      'erp5_km',
      'erp5_web_download_theme',
      'erp5_web_shacache',
      'erp5_data_set',
      'erp5_web_shadir',
      'erp5_accounting',
      'erp5_invoicing',
      'erp5_simplified_invoicing',
      'erp5_credential_oauth2',
      'erp5_accounting_l10n_fr',
      'erp5_bearer_token',
      'erp5_access_token',
      'erp5_project',
      'slapos_cache',
      'slapos_cloud',
      'slapos_slap_tool',
      'slapos_category',
      'slapos_rest_api_tool_portal_type',
      'slapos_rest_api',
      'slapos_hypermedia',
      'slapos_pdm',
      'slapos_crm',
      'slapos_accounting',
      'slapos_payzen',
      'slapos_web',
      'slapos_erp5',
    ]
    self.assertSameSet(expected_business_template_list,
      self.portal.portal_templates.getInstalledBusinessTemplateTitleList())
