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

class TestDefaultInvoiceTransactionRule(testSlapOSMixin):
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
              .slapos_invoice_simulation_rule,
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
          trade_phase='slapos/invoicing',
          quantity_unit='unit/piece',
          specialise='sale_trade_condition_module/slapos_trade_condition',
          causality_list=['business_process_module/slapos_sale_business_p'
          'rocess/invoice_path', 'business_process_module/slapos_sale_b'
          'usiness_process/invoice'],
          delivery_value=self.portal.accounting_module.newContent(
              portal_type='Sale Invoice Transaction').newContent(
                  portal_type='Invoice Line')
          )

      self.assertEqual('planned',
          root_simulation_movement.getSimulationState())
      root_simulation_movement.expand(expand_policy='immediate')

      applied_rule_list = [q for q in root_simulation_movement.contentValues(
          portal_type='Applied Rule') if q.getSpecialiseReference() == \
              'default_trade_model_rule']

      # movement is in final state, it shall be expanded
      self.assertEqual(1, len(applied_rule_list))

      applied_rule = applied_rule_list[0]
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
      self.assertEqual(root_simulation_movement.getTotalPrice(),
          simulation_movement.getQuantity())
      self.assertEqual(root_simulation_movement.getPriceCurrency(),
          simulation_movement.getPriceCurrency())
      self.assertEqual([], simulation_movement.getAggregateList())
      self.assertEqual(root_simulation_movement.getStopDate(),
          simulation_movement.getStartDate())
      self.assertEqual(root_simulation_movement.getStopDate(),
          simulation_movement.getStopDate())
      self.assertEqual(None, simulation_movement.getUse())

      trade_model_line_list = simulation_movement.getCausalityValueList(
          portal_type='Trade Model Line')
      self.assertEqual(1, len(trade_model_line_list))
      trade_model_line = trade_model_line_list[0]
      self.assertEqual(trade_model_line.getPrice(),
          simulation_movement.getPrice())
      self.assertEqual(trade_model_line.getResource(),
          simulation_movement.getResource())
      self.assertEqual([], simulation_movement.getBaseContributionList())
      self.assertEqual('slapos/tax',
          simulation_movement.getTradePhase())
      self.assertEqual(root_simulation_movement.getQuantityUnit(),
          simulation_movement.getQuantityUnit())
      self.assertEqual(root_simulation_movement.getSpecialise(),
          simulation_movement.getSpecialise())
    finally:
      SimulationMovement.getSimulationState = SimulationMovement\
        .original_getSimulationState
