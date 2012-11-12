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
  detail=context.getRelativeUrl())
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
      'account_module',
      'accounting_module',
      'bug_module',
      'business_configuration_module',
      'business_process_module',
      'campaign_module',
      'component_module',
      'computer_model_module',
      'computer_module',
      'computer_network_module',
      'credential_recovery_module',
      'credential_request_module',
      'credential_update_module',
      'currency_module',
      'data_set_module',
      'document_ingestion_module',
      'document_module',
      'event_module',
      'external_source_module',
      'glossary_module',
      'hosting_subscription_module',
      'image_module',
      'internal_order_module',
      'internal_packing_list_module',
      'internal_supply_module',
      'internal_trade_condition_module',
      'inventory_module',
      'item_module',
      'knowledge_pad_module',
      'meeting_module',
      'notification_message_module',
      'open_internal_order_module',
      'open_purchase_order_module',
      'open_sale_order_module',
      'organisation_module',
      'person_module',
      'portal_activities',
      'portal_simulation',
      'product_module',
      'purchase_order_module',
      'purchase_packing_list_module',
      'purchase_supply_module',
      'purchase_trade_condition_module',
      'quantity_unit_conversion_module',
      'query_module',
      'returned_purchase_packing_list_module',
      'returned_sale_packing_list_module',
      'sale_opportunity_module',
      'sale_order_module',
      'sale_packing_list_module',
      'sale_supply_module',
      'sale_trade_condition_module',
      'service_module',
      'service_report_module',
      'software_installation_module',
      'software_instance_module',
      'software_licence_module',
      'software_product_module',
      'software_publication_module',
      'software_release_module',
      'support_request_module',
      'transformation_module',
      'web_page_module',
      'web_site_module',
      'workflow_module',
    ])

    self.assertSameSet(expected_list, visited_list)
