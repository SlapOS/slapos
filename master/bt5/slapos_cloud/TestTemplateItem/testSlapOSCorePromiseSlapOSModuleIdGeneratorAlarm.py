# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from Products.ERP5Type.tests.utils import createZODBPythonScript

class TestSlapOSCorePromiseSlapOSModuleIdGeneratorAlarm(testSlapOSMixin):
  def test_Module_assertIdGenerator(self):
    self.login()
    module = self.portal.newContent(portal_type='Person Module',
        id=str(self.generateNewId()),
        id_generator='bad_id_generator')

    self.assertEqual('bad_id_generator', module.getIdGenerator())

    # check positive response
    self.assertTrue(module.Module_assertIdGenerator('bad_id_generator', False))
    self.assertEqual('bad_id_generator', module.getIdGenerator())
    self.assertTrue(module.Module_assertIdGenerator('bad_id_generator', True))
    self.assertEqual('bad_id_generator', module.getIdGenerator())

    # check negative response and that no-op run does not modify
    self.assertFalse(module.Module_assertIdGenerator('good_id_generator', False))
    self.assertEqual('bad_id_generator', module.getIdGenerator())

    # check negative response with fixit request
    self.assertFalse(module.Module_assertIdGenerator('good_id_generator', True))
    self.assertEqual('good_id_generator', module.getIdGenerator())
    self.assertTrue(module.Module_assertIdGenerator('good_id_generator', False))
    self.assertEqual('good_id_generator', module.getIdGenerator())

    transaction.abort()

  def _simulateModule_assertIdGenerator(self):
    script_name = 'Module_assertIdGenerator'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        'id_generator, fixit, active_process=None',
                        '# Script body\n'
"""from Products.CMFActivity.ActiveResult import ActiveResult
active_result = ActiveResult()
active_result.edit(
  summary='Module_assertIdGenerator simulation',
  severity=0,
  detail=context.getPath())
active_process.postResult(active_result)
""" )
    transaction.commit()

  def _dropModule_assertIdGenerator(self):
    script_name = 'Module_assertIdGenerator'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm(self):
    alarm = self.portal.portal_alarms.promise_slapos_module_id_generator
    previous_active_process = self.portal.portal_catalog.getResultValue(
      portal_type='Active Process',
      causality_uid=alarm.getUid(),
      sort_on=(('creation_date', 'DESC'),)
    )
    self._simulateModule_assertIdGenerator()
    try:
      alarm.activeSense()
      self.tic()
    finally:
      self._dropModule_assertIdGenerator()
    active_process = self.portal.portal_catalog.getResultValue(
      portal_type='Active Process',
      causality_uid=alarm.getUid(),
      sort_on=(('creation_date', 'DESC'),)
    )

    self.assertNotEqual(previous_active_process.getPath(),
        active_process.getPath())

    visited_list = sorted([q.detail for q in active_process.getResultList() \
        if q.summary == 'Module_assertIdGenerator simulation'])

    expected_list = sorted([
      '/erp5/account_module',
      '/erp5/accounting_module',
      '/erp5/bar_module',
      '/erp5/bug_module',
      '/erp5/business_configuration_module',
      '/erp5/business_process_module',
      '/erp5/campaign_module',
      '/erp5/component_module',
      '/erp5/computer_model_module',
      '/erp5/computer_module',
      '/erp5/computer_network_module',
      '/erp5/credential_recovery_module',
      '/erp5/credential_request_module',
      '/erp5/credential_update_module',
      '/erp5/currency_module',
      '/erp5/data_set_module',
      '/erp5/discount_module',
      '/erp5/document_ingestion_module',
      '/erp5/document_module',
      '/erp5/event_module',
      '/erp5/external_source_module',
      '/erp5/foo_bar_module',
      '/erp5/foo_module',
      '/erp5/glossary_module',
      '/erp5/hosting_subscription_module',
      '/erp5/image_module',
      '/erp5/internal_order_module',
      '/erp5/internal_packing_list_module',
      '/erp5/internal_supply_module',
      '/erp5/internal_trade_condition_module',
      '/erp5/inventory_module',
      '/erp5/item_module',
      '/erp5/knowledge_pad_module',
      '/erp5/meeting_module',
      '/erp5/notification_message_module',
      '/erp5/open_internal_order_module',
      '/erp5/open_purchase_order_module',
      '/erp5/open_sale_order_module',
      '/erp5/organisation_module',
      '/erp5/person_module',
      '/erp5/portal_activities',
      '/erp5/portal_simulation',
      '/erp5/product_module',
      '/erp5/project_module',
      '/erp5/purchase_order_module',
      '/erp5/purchase_packing_list_module',
      '/erp5/purchase_supply_module',
      '/erp5/purchase_trade_condition_module',
      '/erp5/quantity_unit_conversion_module',
      '/erp5/query_module',
      '/erp5/requirement_module',
      '/erp5/returned_purchase_packing_list_module',
      '/erp5/returned_sale_packing_list_module',
      '/erp5/sale_opportunity_module',
      '/erp5/sale_order_module',
      '/erp5/sale_packing_list_module',
      '/erp5/sale_supply_module',
      '/erp5/sale_trade_condition_module',
      '/erp5/service_module',
      '/erp5/service_report_module',
      '/erp5/software_installation_module',
      '/erp5/software_instance_module',
      '/erp5/software_licence_module',
      '/erp5/software_product_module',
      '/erp5/software_publication_module',
      '/erp5/software_release_module',
      '/erp5/support_request_module',
      '/erp5/system_event_module',
      '/erp5/task_module',
      '/erp5/task_report_module',
      '/erp5/tax_module',
      '/erp5/transformation_module',
      '/erp5/web_page_module',
      '/erp5/web_site_module',
      '/erp5/workflow_module',
    ])

    self.assertSameSet(expected_list, visited_list)
