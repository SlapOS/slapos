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
              'default_invoice_transaction_rule']

      # movement is in final state, it shall be expanded
      self.assertEqual(1, len(applied_rule_list))

      applied_rule = applied_rule_list[0]
      simulation_movement_list = applied_rule.contentValues(
          portal_type='Simulation Movement')
      self.assertEqual(2, len(simulation_movement_list))
      debit_movement_list = [q for q in simulation_movement_list if \
          q.getCausality() == 'business_process_module/slapos_sale_busines'
              's_process/account_debit_path']
      credit_movement_list = [q for q in simulation_movement_list if \
          q.getCausality() == 'business_process_module/slapos_sale_busines'
              's_process/account_credit_path']
      self.assertEqual(1, len(debit_movement_list))
      self.assertEqual(1, len(credit_movement_list))
      debit_movement = debit_movement_list[0]
      credit_movement = credit_movement_list[0]
      def checkSimulationMovement(simulation_movement, source, destination,
            quantity_sign):
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
        self.assertEqual(root_simulation_movement.getPriceCurrency(),
            simulation_movement.getResource())
        self.assertEqual([], simulation_movement.getAggregateList())
        self.assertEqual(root_simulation_movement.getStartDate(),
            simulation_movement.getStartDate())
        self.assertEqual(root_simulation_movement.getStopDate(),
            simulation_movement.getStopDate())
        self.assertEqual([], simulation_movement.getBaseContributionList())
        self.assertEqual(None, simulation_movement.getPriceCurrency())
        self.assertEqual(None, simulation_movement.getUse())
        self.assertEqual('slapos/accounting',
            simulation_movement.getTradePhase())
        self.assertEqual(root_simulation_movement.getQuantityUnit(),
            simulation_movement.getQuantityUnit())
        self.assertEqual(root_simulation_movement.getSpecialise(),
            simulation_movement.getSpecialise())
      checkSimulationMovement(debit_movement, 'account_module/receivable',
          'account_module/payable', -1)
      checkSimulationMovement(credit_movement, 'account_module/sales',
          'account_module/purchase', 1)
    finally:
      SimulationMovement.getSimulationState = SimulationMovement\
        .original_getSimulationState
