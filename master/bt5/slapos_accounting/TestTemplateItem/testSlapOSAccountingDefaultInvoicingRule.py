# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from DateTime import DateTime
import transaction
import functools

def withAbort(func):
  @functools.wraps(func)
  def wrapped(self, *args, **kwargs):
    try:
      func(self, *args, **kwargs)
    finally:
      transaction.abort()
  return wrapped

class TestDefaultInvoicingRule(testSlapOSMixin):
  @withAbort
  def test_simulation(self):
    from Products.ERP5.Document.SimulationMovement import SimulationMovement
    SimulationMovement.original_getSimulationState = SimulationMovement\
        .getSimulationState
    try:
      def getSimulationStatePlanned(self, *args, **kwargs):
        return 'planned'
      SimulationMovement.getSimulationState = getSimulationStatePlanned

      source = self.portal.person_module.template_member\
          .Base_createCloneDocument(batch_mode=1)
      destination = self.portal.person_module.template_member\
          .Base_createCloneDocument(batch_mode=1)
      aggregate = self.portal.hosting_subscription_module\
          .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
      resource = self.portal.service_module.slapos_instance_subscription
      start_date = DateTime('2011/02/16')
      stop_date = DateTime('2011/03/16')

      root_applied_rule = self.portal.portal_simulation.newContent(
          specialise_value=self.portal.portal_rules\
              .slapos_subscription_item_rule,
          portal_type='Applied Rule')

      root_simulation_movement = root_applied_rule.newContent(
          id='root_simulation_movement',
          portal_type='Simulation Movement',
          price=2.4,
          quantity=4.6,
          source_value=source,
          source_section_value=source,
          destination_value=destination,
          destination_section_value=destination,
          resource_value=resource,
          aggregate_value=aggregate,
          start_date=start_date,
          stop_date=stop_date,
          base_contribution_list=['base_amount/invoicing/discounted',
              'base_amount/invoicing/taxable'],
          price_currency='currency_module/EUR',
          use='trade/sale',
          trade_phase='slapos/delivery',
          quantity_unit='unit/piece',
          specialise='sale_trade_condition_module/slapos_trade_condition',
          causality_list=['business_process_module/slapos_sale_business_p'
              'rocess/delivery_path', 'business_process_module/slapos_sale_'
              'business_process/deliver'])

      self.assertEqual('planned',
          root_simulation_movement.getSimulationState())
      root_simulation_movement.expand(expand_policy='immediate')

      applied_rule_list = root_simulation_movement.contentValues(
          portal_type='Applied Rule')

      # movement is in final state, it shall be expanded
      self.assertEqual(1, len(applied_rule_list))

      applied_rule = applied_rule_list[0]
      self.assertEqual('default_invoicing_rule',
          applied_rule.getSpecialiseReference())
      simulation_movement_list = applied_rule.contentValues(
          portal_type='Simulation Movement')
      self.assertEqual(1, len(simulation_movement_list))
      simulation_movement = simulation_movement_list[0]
      self.assertEqual('planned', simulation_movement.getSimulationState())
      self.assertEqual(root_simulation_movement.getSource(),
          simulation_movement.getSource())
      self.assertEqual(root_simulation_movement.getSourceSection(),
          simulation_movement.getSourceSection())
      self.assertEqual(root_simulation_movement.getDestination(),
          simulation_movement.getDestination())
      self.assertEqual(root_simulation_movement.getDestinationSection(),
          simulation_movement.getDestinationSection())
      self.assertEqual(root_simulation_movement.getPrice(),
          simulation_movement.getPrice())
      self.assertEqual(root_simulation_movement.getQuantity(),
          simulation_movement.getQuantity())
      self.assertEqual(root_simulation_movement.getResource(),
          simulation_movement.getResource())
      self.assertEqual(root_simulation_movement.getAggregateList(),
          simulation_movement.getAggregateList())
      self.assertEqual(root_simulation_movement.getStartDate(),
          simulation_movement.getStartDate())
      self.assertEqual(root_simulation_movement.getStopDate(),
          simulation_movement.getStopDate())
      self.assertEqual(root_simulation_movement.getBaseContributionList(),
          simulation_movement.getBaseContributionList())
      self.assertEqual(root_simulation_movement.getPriceCurrency(),
          simulation_movement.getPriceCurrency())
      self.assertEqual(root_simulation_movement.getUse(),
          simulation_movement.getUse())
      self.assertEqual('slapos/invoicing',
          simulation_movement.getTradePhase())
      self.assertEqual(root_simulation_movement.getQuantityUnit(),
          simulation_movement.getQuantityUnit())
      self.assertEqual(root_simulation_movement.getSpecialise(),
          simulation_movement.getSpecialise())
      self.assertEqual(['business_process_module/slapos_sale_business_p'
          'rocess/invoice_path', 'business_process_module/slapos_sale_b'
          'usiness_process/invoice'], simulation_movement.getCausalityList())
      # check children rules' type
      child_applied_rule_type_list = [q.getSpecialiseReference() for q in \
          simulation_movement.contentValues(portal_type='Applied Rule')]
      self.assertSameSet(
          ['default_invoice_transaction_rule', 'default_trade_model_rule'],
          child_applied_rule_type_list)
    finally:
      SimulationMovement.getSimulationState = SimulationMovement\
        .original_getSimulationState
