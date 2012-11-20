# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from DateTime import DateTime
from Products.ERP5Type.DateUtils import addToDate
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
        self.assertEqual(root_simulation_movement.getPriceCurrency(),
            simulation_movement.getResource())
        self.assertEqual([], simulation_movement.getAggregateList())
        self.assertEqual(root_simulation_movement.getStopDate(),
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
        self.assertSameSet(child_rule_reference_list,
            [q.getSpecialiseReference() for q in simulation_movement\
                .contentValues(portal_type='Applied Rule')])

      checkSimulationMovement(debit_movement, 'account_module/receivable',
          'account_module/payable', -1, ['default_payment_rule'])
      checkSimulationMovement(credit_movement, 'account_module/sales',
          'account_module/purchase', 1, [])
    finally:
      SimulationMovement.getSimulationState = SimulationMovement\
        .original_getSimulationState

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

class TestDefaultPaymentRule(testSlapOSMixin):
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

class TestHostingSubscriptionSimulation(testSlapOSMixin):
  def _prepare(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    self.initial_date = DateTime('2011/02/16')
    stop_date = DateTime('2011/04/16')
    self.subscription.edit(
      periodicity_hour=0,
      periodicity_minute=0,
      periodicity_month_day=self.initial_date.day(),
      destination_section=person.getRelativeUrl()
    )
    self.portal.portal_workflow._jumpToStateFor(self.subscription, 'validated')

    open_sale_order_template = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredOpenSaleOrderTemplate())
    open_sale_order_line_template = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredOpenSaleOrderLineTemplate())
    open_order = open_sale_order_template.Base_createCloneDocument(
        batch_mode=1)
    open_order.edit(
        destination_decision=person.getRelativeUrl(),
        destination_section=person.getRelativeUrl(),
        destination=person.getRelativeUrl(),
        effective_date=self.initial_date,
        expiration_date=self.initial_date + 1,
    )
    self.portal.portal_workflow._jumpToStateFor(open_order, 'validated')

    self.open_order_line = open_sale_order_line_template.Base_createCloneDocument(
        batch_mode=1, destination=open_order)
    self.open_order_line.edit(
        aggregate=self.subscription.getRelativeUrl(),
        start_date=self.initial_date,
        stop_date=stop_date
    )
    self.tic()

    applied_rule_list = self.portal.portal_catalog(portal_type='Applied Rule',
        causality_uid=self.subscription.getUid())
    self.assertEqual(0, len(applied_rule_list))

    self.subscription.updateSimulation(expand_root=1)
    self.tic()

  def test_simulation(self):
    self._prepare()
    applied_rule_list = self.portal.portal_catalog(portal_type='Applied Rule',
        causality_uid=self.subscription.getUid())
    self.assertEqual(1, len(applied_rule_list))

    applied_rule = applied_rule_list[0].getObject()
    rule = applied_rule.getSpecialiseValue()

    self.assertEqual('Subscription Item Root Simulation Rule',
        rule.getPortalType())
    self.assertEqual('default_subscription_item_rule', rule.getReference())

    simulation_movement_list = self.portal.portal_catalog(
        portal_type='Simulation Movement',
        parent_uid=applied_rule.getUid(),
        sort_on=(('movement.start_date', 'ASC'),)
    )

    # There are 2 movements, for February and March
    self.assertEqual(2, len(simulation_movement_list))

    # Check the list of expected simulation
    idx = 0
    for simulation_movement in simulation_movement_list:
      simulation_movement = simulation_movement.getObject()
      movement_start_date = addToDate(self.initial_date, to_add=dict(month=idx))
      movement_stop_date = addToDate(self.initial_date, to_add=dict(month=idx+1))
      # Check simulation movement property
      self.assertEqual(movement_start_date, simulation_movement.getStartDate())
      self.assertEqual(movement_stop_date, simulation_movement.getStopDate())
      self.assertEquals(self.open_order_line.getQuantity(),
        simulation_movement.getQuantity())
      self.assertEquals(self.open_order_line.getQuantityUnit(),
        simulation_movement.getQuantityUnit())
      self.assertEquals(self.open_order_line.getPrice(),
        simulation_movement.getPrice())
      self.assertEquals(self.open_order_line.getPriceCurrency(),
        simulation_movement.getPriceCurrency())
      self.assertEquals(self.open_order_line.getSource(),
        simulation_movement.getSource())
      self.assertEquals(self.open_order_line.getSourceSection(),
        simulation_movement.getSourceSection())
      self.assertEquals(self.open_order_line.getDestination(),
        simulation_movement.getDestination())
      self.assertEquals(self.open_order_line.getDestinationSection(),
        simulation_movement.getDestinationSection())
      self.assertEquals(self.open_order_line.getSpecialise(),
        simulation_movement.getSpecialise())
      self.assertEquals(self.open_order_line.getResource(),
        simulation_movement.getResource())
      self.assertEquals(applied_rule.getSpecialiseValue().getTradePhaseList(),
        simulation_movement.getTradePhaseList())
      self.assertSameSet(self.open_order_line.getAggregateList(),
        simulation_movement.getAggregateList())
      self.assertEqual('planned', simulation_movement.getSimulationState())
      self.assertEqual(None, simulation_movement.getDelivery())

      applied_rule_list_level_2 = simulation_movement.contentValues(
          portal_type='Applied Rule')
      self.assertEqual(1, len(applied_rule_list_level_2))
      # check next simulation movement
      idx += 1

  def test_increaseOpenOrderCoverage(self):
    self._prepare()
    applied_rule_list = self.portal.portal_catalog(portal_type='Applied Rule',
        causality_uid=self.subscription.getUid())
    self.assertEqual(1, len(applied_rule_list))

    applied_rule = applied_rule_list[0].getObject()
    rule = applied_rule.getSpecialiseValue()

    self.assertEqual('Subscription Item Root Simulation Rule',
        rule.getPortalType())
    self.assertEqual('default_subscription_item_rule', rule.getReference())

    simulation_movement_list = self.portal.portal_catalog(
        portal_type='Simulation Movement',
        parent_uid=applied_rule.getUid(),
        sort_on=(('movement.start_date', 'ASC'),)
    )

    # There are 2 movements, for February and March
    self.assertEqual(2, len(simulation_movement_list))

    self.open_order_line.edit(stop_date=DateTime('2011/05/16'))
    self.tic()

    self.subscription.updateSimulation(expand_root=1)
    self.tic()

    simulation_movement_list = self.portal.portal_catalog(
        portal_type='Simulation Movement',
        parent_uid=applied_rule.getUid(),
        sort_on=(('movement.start_date', 'ASC'),)
    )

    # There are 3 movements, for February, March and April
    self.assertEqual(3, len(simulation_movement_list))

  def test_update_frozen_simulation(self):
    self._prepare()
    applied_rule_list = self.portal.portal_catalog(portal_type='Applied Rule',
        causality_uid=self.subscription.getUid())
    self.assertEqual(1, len(applied_rule_list))

    applied_rule = applied_rule_list[0].getObject()
    rule = applied_rule.getSpecialiseValue()

    self.assertEqual('Subscription Item Root Simulation Rule',
        rule.getPortalType())
    self.assertEqual('default_subscription_item_rule', rule.getReference())

    simulation_movement_list = self.portal.portal_catalog(
        portal_type='Simulation Movement',
        parent_uid=applied_rule.getUid(),
        sort_on=(('movement.start_date', 'ASC'),)
    )

    # There are 2 movements, for February and March
    self.assertEqual(2, len(simulation_movement_list))

    # Check the list of expected simulation
    idx = 0
    for simulation_movement in simulation_movement_list:
      simulation_movement = simulation_movement.getObject()
      movement_start_date = addToDate(self.initial_date, to_add=dict(month=idx))
      movement_stop_date = addToDate(self.initial_date, to_add=dict(month=idx+1))
      # Check simulation movement property
      self.assertEqual(movement_start_date, simulation_movement.getStartDate())
      self.assertEqual(movement_stop_date, simulation_movement.getStopDate())
      self.assertEquals(self.open_order_line.getQuantity(),
        simulation_movement.getQuantity())
      self.assertEquals(self.open_order_line.getQuantityUnit(),
        simulation_movement.getQuantityUnit())
      self.assertEquals(self.open_order_line.getPrice(),
        simulation_movement.getPrice())
      self.assertEquals(self.open_order_line.getPriceCurrency(),
        simulation_movement.getPriceCurrency())
      self.assertEquals(self.open_order_line.getSource(),
        simulation_movement.getSource())
      self.assertEquals(self.open_order_line.getSourceSection(),
        simulation_movement.getSourceSection())
      self.assertEquals(self.open_order_line.getDestination(),
        simulation_movement.getDestination())
      self.assertEquals(self.open_order_line.getDestinationSection(),
        simulation_movement.getDestinationSection())
      self.assertEquals(self.open_order_line.getSpecialise(),
        simulation_movement.getSpecialise())
      self.assertEquals(self.open_order_line.getResource(),
        simulation_movement.getResource())
      self.assertEquals(applied_rule.getSpecialiseValue().getTradePhaseList(),
        simulation_movement.getTradePhaseList())
      self.assertSameSet(self.open_order_line.getAggregateList(),
        simulation_movement.getAggregateList())
      self.assertEqual('planned', simulation_movement.getSimulationState())
      self.assertEqual(None, simulation_movement.getDelivery())

      # check children rules' type
      child_applied_rule_type_list = [q.getSpecialiseReference() for q in \
          simulation_movement.contentValues(portal_type='Applied Rule')]
      self.assertSameSet( ['default_invoicing_rule'],
          child_applied_rule_type_list)

      # check next simulation movement
      idx += 1
    def isFrozen(*args, **kwargs):
      return True
    try:
      from Products.ERP5.Document.SimulationMovement import SimulationMovement
      SimulationMovement.originalIsFrozen = SimulationMovement.isFrozen
      SimulationMovement.isFrozen = isFrozen

      # reexpanding non changed will work correctly
      applied_rule.expand(expand_policy='immediate')
      self.tic()

      # reexpanding with change on frozen movement will raise
      self.subscription.edit(periodicity_month_day=self.subscription\
          .getPeriodicityMonthDay() - 1)
      self.tic()
      self.assertRaises(NotImplementedError,
          applied_rule.expand, expand_policy='immediate')
    finally:
      SimulationMovement.isFrozen = SimulationMovement.originalIsFrozen
      delattr(SimulationMovement, 'originalIsFrozen')

class TestDefaultTradeModelRule(testSlapOSMixin):
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

class TestDefaultDeliveryRule(testSlapOSMixin):
  def test(self):
    raise NotImplementedError
