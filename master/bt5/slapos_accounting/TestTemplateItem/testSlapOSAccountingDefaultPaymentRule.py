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
      resource = self.portal.currency_module.EUR
      start_date = DateTime('2011/02/16')
      stop_date = DateTime('2011/03/16')

      root_applied_rule = self.portal.portal_simulation.newContent(
          specialise_value=self.portal.portal_rules\
              .slapos_invoice_transaction_simulation_rule,
          portal_type='Applied Rule')

      root_simulation_movement = root_applied_rule.newContent(
          id='root_simulation_movement',
          portal_type='Simulation Movement',
          price=1,
          quantity=-4.6,
          source='account_module/receivable',
          source_section_value=source,
          destination='account_module/payable',
          destination_section_value=destination,
          resource_value=resource,
          start_date=start_date,
          stop_date=stop_date,
          use='trade/sale',
          trade_phase='slapos/accounting',
          quantity_unit='unit/piece',
          specialise='sale_trade_condition_module/slapos_trade_condition',
          causality_list=['business_process_module/slapos_sale_busines'
              's_process/pay'],
          delivery_value=self.portal.accounting_module.newContent(
              portal_type='Sale Invoice Transaction').newContent(
                  portal_type='Invoice Line')
          )

      self.assertEqual('planned',
          root_simulation_movement.getSimulationState())
      root_simulation_movement.expand(expand_policy='immediate')

      applied_rule_list = root_simulation_movement.contentValues(
          portal_type='Applied Rule')

      # movement is in final state, it shall be expanded
      self.assertEqual(1, len(applied_rule_list))

      applied_rule = applied_rule_list[0]
      self.assertEqual('default_payment_rule',
          applied_rule.getSpecialiseReference())
      simulation_movement_list = applied_rule.contentValues(
          portal_type='Simulation Movement')
      self.assertEqual(2, len(simulation_movement_list))
      debit_movement_list = [q for q in simulation_movement_list if \
          q.getCausality() == 'business_process_module/slapos_sale_busines'
              's_process/payment_debit_path']
      credit_movement_list = [q for q in simulation_movement_list if \
          q.getCausality() == 'business_process_module/slapos_sale_busines'
              's_process/payment_credit_path']
      self.assertEqual(1, len(debit_movement_list))
      self.assertEqual(1, len(credit_movement_list))
      debit_movement = debit_movement_list[0]
      credit_movement = credit_movement_list[0]
      def checkSimulationMovement(simulation_movement, source, destination,
            quantity_sign, child_rule_reference_list):
        self.assertEqual('planned', simulation_movement.getSimulationState())
        self.assertEqual(source, simulation_movement.getSource())
        self.assertEqual(root_simulation_movement.getSourceSection(),
            simulation_movement.getSourceSection())
        self.assertEqual(destination, simulation_movement.getDestination())
        self.assertEqual(root_simulation_movement.getDestinationSection(),
            simulation_movement.getDestinationSection())
        self.assertEqual(1, simulation_movement.getPrice())
        self.assertEqual(root_simulation_movement.getTotalPrice() *\
            quantity_sign, simulation_movement.getQuantity())
        self.assertEqual(root_simulation_movement.getResource(),
            simulation_movement.getResource())
        self.assertEqual([], simulation_movement.getAggregateList())
        self.assertEqual(root_simulation_movement.getStartDate(),
            simulation_movement.getStartDate())
        self.assertEqual(root_simulation_movement.getStopDate(),
            simulation_movement.getStopDate())
        self.assertEqual([], simulation_movement.getBaseContributionList())
        self.assertEqual(None, simulation_movement.getPriceCurrency())
        self.assertEqual(None, simulation_movement.getUse())
        self.assertEqual('slapos/payment',
            simulation_movement.getTradePhase())
        self.assertEqual(root_simulation_movement.getQuantityUnit(),
            simulation_movement.getQuantityUnit())
        self.assertEqual(root_simulation_movement.getSpecialise(),
            simulation_movement.getSpecialise())
        self.assertEqual(0, len(simulation_movement.contentValues(
            portal_type='Applied Rule')))

      checkSimulationMovement(debit_movement, 'account_module/bank',
          'account_module/bank', 1, ['default_payment_rule'])
      checkSimulationMovement(credit_movement, 'account_module/receivable',
          'account_module/payable', -1, [])
    finally:
      SimulationMovement.getSimulationState = SimulationMovement\
        .original_getSimulationState
