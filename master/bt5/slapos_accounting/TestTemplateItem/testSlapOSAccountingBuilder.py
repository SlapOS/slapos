# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from DateTime import DateTime

def convertCategoryList(base, l):
  return ['%s/%s' % (base, q) for q in l]

class TestSlapOSSalePackingListBuilder(testSlapOSMixin):
  def checkSimulationMovement(self, simulation_movement):
    self.assertEqual(1.0, simulation_movement.getDeliveryRatio())
    self.assertEqual(0.0, simulation_movement.getDeliveryError())
    self.assertNotEqual(None, simulation_movement.getDeliveryValue())

  def checkDeliveryLine(self, simulation_movement, delivery_line,
      line_portal_type, cell_portal_type):
    self.assertEqual(line_portal_type, delivery_line.getPortalType())
    self.assertSameSet([
        'resource/service_module/slapos_instance_subscription',
        'use/trade/sale',
        'quantity_unit/unit/piece',
        'base_contribution/base_amount/invoicing/discounted',
        'base_contribution/base_amount/invoicing/taxable'] \
          + convertCategoryList('aggregate',
            simulation_movement.getAggregateList()),
      delivery_line.getCategoryList()
    )
    self.assertEqual(simulation_movement.getQuantity(),
        delivery_line.getQuantity())
    self.assertEqual(simulation_movement.getPrice(),
        delivery_line.getPrice())
    self.assertFalse(delivery_line.hasStartDate())
    self.assertFalse(delivery_line.hasStopDate())
    self.assertEqual([], delivery_line.contentValues(
        portal_type=cell_portal_type))

  def checkDelivery(self, simulation_movement, delivery, delivery_portal_type,
        category_list, simulation_state='delivered'):
    self.assertEqual(delivery_portal_type, delivery.getPortalType())
    self.assertEqual(simulation_state, delivery.getSimulationState())
    self.assertEqual('building', delivery.getCausalityState())
    delivery.updateCausalityState(solve_automatically=False)
    self.assertEqual('solved', delivery.getCausalityState())
    self.assertEqual(simulation_movement.getStartDate(),
      delivery.getStartDate())
    self.assertEqual(simulation_movement.getStopDate(),
      delivery.getStopDate())
    self.assertSameSet([
          'source/organisation_module/slapos',
          'source_section/organisation_module/slapos',
          'price_currency/currency_module/EUR',
          'specialise/sale_trade_condition_module/slapos_trade_condition'] \
            + convertCategoryList('destination',
                simulation_movement.getDestinationList()) \
            + convertCategoryList('destination_section',
                simulation_movement.getDestinationSectionList()) \
            + convertCategoryList('destination_decision',
                simulation_movement.getDestinationDecisionList()) \
            + category_list,
      delivery.getCategoryList())

  def test(self):
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    applied_rule = self.portal.portal_simulation.newContent(
      portal_type='Applied Rule',
      causality=hosting_subscription.getRelativeUrl(),
      specialise='portal_rules/slapos_subscription_item_rule'
    )
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    simulation_movement_kw = dict(
        portal_type='Simulation Movement',
        aggregate=hosting_subscription.getRelativeUrl(),
        base_contribution=['base_amount/invoicing/discounted',
            'base_amount/invoicing/taxable'],
        causality=['business_process_module/slapos_sale_business_process'
            '/deliver', 'business_process_module/slapos_sale_business_pr'
            'ocess/delivery_path'],
        destination=person.getRelativeUrl(),
        destination_decision=person.getRelativeUrl(),
        destination_section=person.getRelativeUrl(),
        price_currency='currency_module/EUR',
        quantity_unit='unit/piece',
        resource='service_module/slapos_instance_subscription',
        source='organisation_module/slapos',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        trade_phase='slapos/delivery',
        use='trade/sale',
    )
    simulation_movement_1 = applied_rule.newContent(
        quantity=1.2,
        price=3.4,
        start_date=DateTime('2012/01/01'),
        stop_date=DateTime('2012/02/01'),
        **simulation_movement_kw
    )
    simulation_movement_2 = applied_rule.newContent(
        quantity=5.6,
        price=7.8,
        start_date=DateTime('2012/03/01'),
        stop_date=DateTime('2012/04/01'),
        **simulation_movement_kw
    )

    self.tic()

    self.portal.portal_deliveries.slapos_sale_packing_list_builder.build(
        path='%s/%%' % applied_rule.getPath())
    self.tic()

    self.checkSimulationMovement(simulation_movement_1)
    self.checkSimulationMovement(simulation_movement_2)

    delivery_line_1 = simulation_movement_1.getDeliveryValue()
    delivery_line_2 = simulation_movement_2.getDeliveryValue()
    self.assertNotEqual(delivery_line_1.getRelativeUrl(),
        delivery_line_2.getRelativeUrl())

    line_kw = dict(line_portal_type='Sale Packing List Line',
        cell_portal_type='Sale Packing List Cell')
    self.checkDeliveryLine(simulation_movement_1, delivery_line_1, **line_kw)
    self.checkDeliveryLine(simulation_movement_2, delivery_line_2, **line_kw)

    delivery_1 = delivery_line_1.getParentValue()
    delivery_2 = delivery_line_2.getParentValue()

    self.assertNotEqual(delivery_1.getRelativeUrl(),
        delivery_2.getRelativeUrl())

    delivery_kw = dict(delivery_portal_type='Sale Packing List',
        category_list=convertCategoryList('causality',
          simulation_movement_1.getParentValue().getCausalityList()))
    self.checkDelivery(simulation_movement_1, delivery_1, **delivery_kw)
    self.checkDelivery(simulation_movement_2, delivery_2, **delivery_kw)

class TestSlapOSSaleInvoiceBuilder(TestSlapOSSalePackingListBuilder):
  def test(self):
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    applied_rule = self.portal.portal_simulation.newContent(
      portal_type='Applied Rule',
      causality=hosting_subscription.getRelativeUrl(),
      specialise='portal_rules/slapos_subscription_item_rule'
    )
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    delivery_kw = dict(
        portal_type='Sale Packing List',
        causality=hosting_subscription.getRelativeUrl(),
        price_currency='currency_module/EUR',
        source='organisation_module/slapos',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
    )
    delivery_line_kw = dict(
        portal_type='Sale Packing List Line',
        resource='service_module/slapos_instance_subscription',
        use='trade/sale',
        quantity_unit='unit/piece',
        base_contribution_list=['base_amount/invoicing/discounted',
            'base_amount/invoicing/taxable'],
        aggregate=hosting_subscription.getRelativeUrl(),
    )
    delivery_1 = self.portal.sale_packing_list_module.newContent(
        destination=person.getRelativeUrl(),
        destination_decision=person.getRelativeUrl(),
        destination_section=person.getRelativeUrl(),
        start_date=DateTime('2012/01/01'),
        stop_date=DateTime('2012/02/01'),
        **delivery_kw
    )
    self.portal.portal_workflow._jumpToStateFor(delivery_1, 'delivered')
    self.portal.portal_workflow._jumpToStateFor(delivery_1, 'calculating')
    delivery_line_1 = delivery_1.newContent(
        quantity=1.2,
        price=3.4,
        **delivery_line_kw
    )
    delivery_2 = self.portal.sale_packing_list_module.newContent(
        destination=person.getRelativeUrl(),
        destination_decision=person.getRelativeUrl(),
        destination_section=person.getRelativeUrl(),
        start_date=DateTime('2012/01/01'),
        stop_date=DateTime('2012/02/01'),
        **delivery_kw
    )
    self.portal.portal_workflow._jumpToStateFor(delivery_2, 'delivered')
    self.portal.portal_workflow._jumpToStateFor(delivery_2, 'calculating')
    delivery_line_2 = delivery_2.newContent(
        quantity=5.6,
        price=7.8,
        **delivery_line_kw
    )
    simulation_movement_kw = dict(
        portal_type='Simulation Movement',
        aggregate=hosting_subscription.getRelativeUrl(),
        base_contribution=['base_amount/invoicing/discounted',
            'base_amount/invoicing/taxable'],
        causality=['business_process_module/slapos_sale_business_process'
            '/deliver', 'business_process_module/slapos_sale_business_pr'
            'ocess/delivery_path'],
        destination=person.getRelativeUrl(),
        destination_decision=person.getRelativeUrl(),
        destination_section=person.getRelativeUrl(),
        price_currency='currency_module/EUR',
        quantity_unit='unit/piece',
        resource='service_module/slapos_instance_subscription',
        source='organisation_module/slapos',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        trade_phase='slapos/delivery',
        use='trade/sale',
        delivery_ratio=1.0
    )
    simulation_movement_1 = applied_rule.newContent(
        quantity=delivery_line_1.getQuantity(),
        price=delivery_line_1.getPrice(),
        start_date=delivery_1.getStartDate(),
        stop_date=delivery_1.getStopDate(),
        delivery=delivery_line_1.getRelativeUrl(),
        **simulation_movement_kw
    )
    simulation_movement_2 = applied_rule.newContent(
        quantity=delivery_line_2.getQuantity(),
        price=delivery_line_2.getPrice(),
        start_date=delivery_2.getStartDate(),
        stop_date=delivery_2.getStopDate(),
        delivery=delivery_line_2.getRelativeUrl(),
        **simulation_movement_kw
    )

    self.tic()
    delivery_1.updateCausalityState(solve_automatically=False)
    delivery_2.updateCausalityState(solve_automatically=False)
    self.tic()

    # test the test
    self.assertEqual('solved', delivery_1.getCausalityState())
    self.assertEqual('solved', delivery_2.getCausalityState())

    # create new simulation movements
    invoice_movement_kw = simulation_movement_kw.copy()
    invoice_movement_kw.update(
        causality=[
            'business_process_module/slapos_sale_business_process/invoice',
            'business_process_module/slapos_sale_business_process/invoice_path'
        ],
        trade_phase='slapos/invoicing'
    )
    invoice_rule_1 = simulation_movement_1.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_simulation_rule')
    invoice_movement_1 = invoice_rule_1.newContent(
        start_date=delivery_1.getStartDate(),
        stop_date=delivery_1.getStopDate(),
        quantity=delivery_line_1.getQuantity(),
        price=delivery_line_1.getPrice(),
        **invoice_movement_kw)

    invoice_rule_2 = simulation_movement_2.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_simulation_rule')
    invoice_movement_2 = invoice_rule_2.newContent(
        start_date=delivery_2.getStartDate(),
        stop_date=delivery_2.getStopDate(),
        quantity=delivery_line_2.getQuantity(),
        price=delivery_line_2.getPrice(),
        **invoice_movement_kw)
    self.tic()

    self.portal.portal_deliveries.slapos_sale_invoice_builder.build(
        path='%s/%%' % applied_rule.getPath())
    self.tic()

    self.checkSimulationMovement(invoice_movement_1)
    self.checkSimulationMovement(invoice_movement_2)

    invoice_line_1 = invoice_movement_1.getDeliveryValue()
    invoice_line_2 = invoice_movement_2.getDeliveryValue()
    self.assertNotEqual(invoice_line_1.getRelativeUrl(),
        invoice_line_2.getRelativeUrl())

    line_kw = dict(line_portal_type='Invoice Line',
        cell_portal_type='Invoice Cell')
    self.checkDeliveryLine(invoice_movement_1, invoice_line_1, **line_kw)
    self.checkDeliveryLine(invoice_movement_2, invoice_line_2, **line_kw)

    invoice_1 = invoice_line_1.getParentValue()
    invoice_2 = invoice_line_2.getParentValue()

    self.assertNotEqual(invoice_1.getRelativeUrl(),
        invoice_2.getRelativeUrl())

    invoice_kw = dict(delivery_portal_type='Sale Invoice Transaction',
        simulation_state='confirmed')
    category_list = ['resource/currency_module/EUR']
    self.checkDelivery(invoice_movement_1, invoice_1,
        category_list=category_list + convertCategoryList('causality',
          [delivery_1.getRelativeUrl()]), **invoice_kw)
    self.checkDelivery(invoice_movement_2, invoice_2,
        category_list=category_list + convertCategoryList('causality',
          [delivery_2.getRelativeUrl()]), **invoice_kw)

class TestSlapOSSaleInvoiceTransactionBuilder(TestSlapOSSalePackingListBuilder):
  def test(self):
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    applied_rule = self.portal.portal_simulation.newContent(
      portal_type='Applied Rule',
      causality=hosting_subscription.getRelativeUrl(),
      specialise='portal_rules/slapos_subscription_item_rule'
    )
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    simulation_movement_1 = applied_rule.newContent(
        portal_type='Simulation Movement'
    )
    simulation_movement_2 = applied_rule.newContent(
        portal_type='Simulation Movement'
    )

    # linked invoice
    invoice_kw = dict(
      portal_type='Sale Invoice Transaction',
      source='organisation_module/slapos',
      source_section='organisation_module/slapos',
      price_currency='currency_module/EUR',
      resource='currency_module/EUR',
      specialise='sale_trade_condition_module/slapos_trade_condition',
      created_by_builder=1
    )
    invoice_line_kw = dict(
      portal_type='Invoice Line',
      use='trade/sale',
      resource='service_module/slapos_instance_subscription',
      quantity_unit='unit/piece',
      base_contribution=['base_amount/invoicing/discounted',
          'base_amount/invoicing/taxable'],
    )

    invoice_1 = self.portal.accounting_module.newContent(
      start_date=DateTime('2012/01/01'),
      stop_date=DateTime('2012/02/01'),
      destination=person.getRelativeUrl(),
      destination_section=person.getRelativeUrl(),
      destination_decision=person.getRelativeUrl(),
      **invoice_kw
    )
    invoice_line_1 = invoice_1.newContent(
      aggregate=hosting_subscription.getRelativeUrl(),
      price=1.2,
      quantity=3.4,
      **invoice_line_kw
    )
    invoice_2 = self.portal.accounting_module.newContent(
      start_date=DateTime('2012/01/01'),
      stop_date=DateTime('2012/02/01'),
      destination=person.getRelativeUrl(),
      destination_section=person.getRelativeUrl(),
      destination_decision=person.getRelativeUrl(),
      **invoice_kw
    )
    invoice_line_2 = invoice_2.newContent(
      aggregate=hosting_subscription.getRelativeUrl(),
      price=5.6,
      quantity=7.8,
      **invoice_line_kw
    )
    self.portal.portal_workflow._jumpToStateFor(invoice_1, 'confirmed')
    self.portal.portal_workflow._jumpToStateFor(invoice_1, 'calculating')
    self.portal.portal_workflow._jumpToStateFor(invoice_2, 'confirmed')
    self.portal.portal_workflow._jumpToStateFor(invoice_2, 'calculating')

    # create new simulation movements
    invoice_movement_kw = dict(
        causality=[
            'business_process_module/slapos_sale_business_process/invoice',
            'business_process_module/slapos_sale_business_process/invoice_path'
        ],
        trade_phase='slapos/invoicing',
        delivery_ratio=1.0,
        delivery_error=0.0,
        portal_type='Simulation Movement',
        aggregate=hosting_subscription.getRelativeUrl(),
        base_contribution=['base_amount/invoicing/discounted',
            'base_amount/invoicing/taxable'],
        destination=person.getRelativeUrl(),
        destination_decision=person.getRelativeUrl(),
        destination_section=person.getRelativeUrl(),
        price_currency='currency_module/EUR',
        quantity_unit='unit/piece',
        resource='service_module/slapos_instance_subscription',
        source='organisation_module/slapos',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        use='trade/sale',
    )
    invoice_rule_1 = simulation_movement_1.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_simulation_rule')
    invoice_movement_1 = invoice_rule_1.newContent(
        start_date=invoice_1.getStartDate(),
        stop_date=invoice_1.getStopDate(),
        quantity=invoice_line_1.getQuantity(),
        price=invoice_line_1.getPrice(),
        delivery=invoice_line_1.getRelativeUrl(),
        **invoice_movement_kw)

    invoice_rule_2 = simulation_movement_2.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_simulation_rule')
    invoice_movement_2 = invoice_rule_2.newContent(
        start_date=invoice_2.getStartDate(),
        stop_date=invoice_2.getStopDate(),
        quantity=invoice_line_2.getQuantity(),
        price=invoice_line_2.getPrice(),
        delivery=invoice_line_2.getRelativeUrl(),
        **invoice_movement_kw)
    self.tic()

    invoice_1.updateCausalityState(solve_automatically=False)
    invoice_2.updateCausalityState(solve_automatically=False)
    self.tic()

    # test the test
    self.assertEqual('solved', invoice_1.getCausalityState())
    self.assertEqual('solved', invoice_2.getCausalityState())

    transaction_rule_1 = invoice_movement_1.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_transaction_simulation_rule'
    )
    transaction_movement_1_rec = transaction_rule_1.newContent(
      portal_type='Simulation Movement',
      causality=['business_process_module/slapos_sale_business_process/account',
          'business_process_module/slapos_sale_business_process/account_debi'
            't_path'],
      destination=['account_module/payable'],
      destination_decision=invoice_movement_1.getDestinationDecision(),
      destination_section=invoice_movement_1.getDestinationSection(),
      quantity_unit='unit/piece',
      resource='currency_module/EUR',
      source='account_module/receivable',
      source_section='organisation_module/slapos',
      specialise='sale_trade_condition_module/slapos_trade_condition',
      trade_phase='slapos/accounting',
      price=1.0,
      quantity=invoice_movement_1.getTotalPrice() * -1,
    )
    transaction_movement_1_rec_bis = transaction_movement_1_rec\
        .Base_createCloneDocument(batch_mode=1)
    transaction_movement_1_sal = transaction_rule_1.newContent(
      portal_type='Simulation Movement',
      causality=['business_process_module/slapos_sale_business_process/account',
          'business_process_module/slapos_sale_business_process/account_cred'
            'it_path'],
      destination=['account_module/purchase'],
      destination_decision=invoice_movement_1.getDestinationDecision(),
      destination_section=invoice_movement_1.getDestinationSection(),
      quantity_unit='unit/piece',
      resource='currency_module/EUR',
      source='account_module/receivable',
      source_section='organisation_module/slapos',
      specialise='sale_trade_condition_module/slapos_trade_condition',
      trade_phase='slapos/accounting',
      price=1.0,
      quantity=invoice_movement_1.getTotalPrice(),
    )

    transaction_rule_2 = invoice_movement_2.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_transaction_simulation_rule'
    )
    transaction_movement_2_rec = transaction_rule_2.newContent(
      portal_type='Simulation Movement',
      causality=['business_process_module/slapos_sale_business_process/account',
          'business_process_module/slapos_sale_business_process/account_debi'
            't_path'],
      destination=['account_module/payable'],
      destination_decision=invoice_movement_2.getDestinationDecision(),
      destination_section=invoice_movement_2.getDestinationSection(),
      quantity_unit='unit/piece',
      resource='currency_module/EUR',
      source='account_module/receivable',
      source_section='organisation_module/slapos',
      specialise='sale_trade_condition_module/slapos_trade_condition',
      trade_phase='slapos/accounting',
      price=1.0,
      quantity=invoice_movement_2.getTotalPrice() * -1,
    )
    transaction_movement_2_sal = transaction_rule_2.newContent(
      portal_type='Simulation Movement',
      causality=['business_process_module/slapos_sale_business_process/account',
          'business_process_module/slapos_sale_business_process/account_cred'
            'it_path'],
      destination=['account_module/purchase'],
      destination_decision=invoice_movement_2.getDestinationDecision(),
      destination_section=invoice_movement_2.getDestinationSection(),
      quantity_unit='unit/piece',
      resource='currency_module/EUR',
      source='account_module/receivable',
      source_section='organisation_module/slapos',
      specialise='sale_trade_condition_module/slapos_trade_condition',
      trade_phase='slapos/accounting',
      price=1.0,
      quantity=invoice_movement_2.getTotalPrice(),
    )
    self.tic()

    self.portal.portal_deliveries.slapos_sale_invoice_transaction_builder.build(
        path='%s/%%' % applied_rule.getPath())
    self.tic()

    self.checkSimulationMovement(transaction_movement_1_rec)
    self.checkSimulationMovement(transaction_movement_1_rec_bis)
    self.checkSimulationMovement(transaction_movement_1_sal)
    self.checkSimulationMovement(transaction_movement_2_rec)
    self.checkSimulationMovement(transaction_movement_2_sal)

    transaction_line_1_rec = transaction_movement_1_rec.getDeliveryValue()
    transaction_line_1_rec_bis = transaction_movement_1_rec_bis.getDeliveryValue()
    transaction_line_1_sal = transaction_movement_1_sal.getDeliveryValue()
    transaction_line_2_rec = transaction_movement_2_rec.getDeliveryValue()
    transaction_line_2_sal = transaction_movement_2_sal.getDeliveryValue()

    def checkTransactionLine(simulation_movement, transaction_line,
          category_list):
      self.assertEqual('Sale Invoice Transaction Line',
          transaction_line.getPortalType())
      self.assertSameSet([
          'resource/currency_module/EUR'] + category_list,
        transaction_line.getCategoryList()
      )
      self.assertEqual(simulation_movement.getQuantity(),
          transaction_line.getQuantity())
      self.assertEqual(simulation_movement.getPrice(),
          transaction_line.getPrice())
      self.assertFalse(transaction_line.hasStartDate())
      self.assertFalse(transaction_line.hasStopDate())
      self.assertEqual([], transaction_line.contentValues(
          portal_type='Delivery Cell'))

    checkTransactionLine(transaction_movement_1_rec, transaction_line_1_rec,
        ['source/account_module/receivable',
            'destination/account_module/payable'])
    checkTransactionLine(transaction_movement_1_rec_bis,
        transaction_line_1_rec_bis,
        ['source/account_module/receivable',
            'destination/account_module/payable'])
    checkTransactionLine(transaction_movement_1_sal, transaction_line_1_sal,
        ['destination/account_module/purchase',
            'source/account_module/receivable'])
    checkTransactionLine(transaction_movement_2_rec, transaction_line_2_rec,
        ['source/account_module/receivable',
            'destination/account_module/payable'])
    checkTransactionLine(transaction_movement_2_sal, transaction_line_2_sal,
        ['destination/account_module/purchase',
            'source/account_module/receivable'])

    self.assertEqual(invoice_1.getRelativeUrl(),
        transaction_line_1_rec.getParentValue().getRelativeUrl())
    self.assertEqual(invoice_1.getRelativeUrl(),
        transaction_line_1_rec_bis.getParentValue().getRelativeUrl())
    self.assertEqual(invoice_1.getRelativeUrl(),
        transaction_line_1_sal.getParentValue().getRelativeUrl())
    self.assertEqual(invoice_2.getRelativeUrl(),
        transaction_line_2_rec.getParentValue().getRelativeUrl())
    self.assertEqual(invoice_2.getRelativeUrl(),
        transaction_line_2_sal.getParentValue().getRelativeUrl())

    def checkTransactionedInvoice(invoice):
      self.assertEqual('confirmed', invoice.getSimulationState())
      self.assertEqual('building', invoice.getCausalityState())
      invoice.updateCausalityState(solve_automatically=False)
      self.assertEqual('solved', invoice.getCausalityState())

    checkTransactionedInvoice(invoice_1)
    checkTransactionedInvoice(invoice_2)

    transaction_movement_1_rec_bis2 = transaction_movement_1_rec\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()
    self.portal.portal_deliveries.slapos_sale_invoice_transaction_builder.build(
        path='%s/%%' % applied_rule.getPath())
    self.tic()
    self.checkSimulationMovement(transaction_movement_1_rec_bis2)
    transaction_line_1_rec_bis2 = transaction_movement_1_rec_bis2\
        .getDeliveryValue()
    checkTransactionLine(transaction_movement_1_rec_bis2,
        transaction_line_1_rec_bis2,
        ['source/account_module/receivable',
            'destination/account_module/payable'])
    self.assertEqual(invoice_1.getRelativeUrl(),
        transaction_line_1_rec_bis2.getParentValue().getRelativeUrl())

class TestSlapOSSaleInvoiceTransactionTradeModelBuilder(TestSlapOSSalePackingListBuilder):
  def test(self):
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    applied_rule = self.portal.portal_simulation.newContent(
      portal_type='Applied Rule',
      causality=hosting_subscription.getRelativeUrl(),
      specialise='portal_rules/slapos_subscription_item_rule'
    )
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    simulation_movement_1 = applied_rule.newContent(
        portal_type='Simulation Movement'
    )
    simulation_movement_2 = applied_rule.newContent(
        portal_type='Simulation Movement'
    )

    # linked invoice
    invoice_kw = dict(
      portal_type='Sale Invoice Transaction',
      source='organisation_module/slapos',
      source_section='organisation_module/slapos',
      price_currency='currency_module/EUR',
      resource='currency_module/EUR',
      specialise='sale_trade_condition_module/slapos_trade_condition',
      created_by_builder=1
    )
    invoice_line_kw = dict(
      portal_type='Invoice Line',
      use='trade/sale',
      resource='service_module/slapos_instance_subscription',
      quantity_unit='unit/piece',
      base_contribution=['base_amount/invoicing/discounted',
          'base_amount/invoicing/taxable'],
    )

    invoice_1 = self.portal.accounting_module.newContent(
      start_date=DateTime('2012/01/01'),
      stop_date=DateTime('2012/02/01'),
      destination=person.getRelativeUrl(),
      destination_section=person.getRelativeUrl(),
      destination_decision=person.getRelativeUrl(),
      **invoice_kw
    )
    invoice_line_1 = invoice_1.newContent(
      aggregate=hosting_subscription.getRelativeUrl(),
      price=1.2,
      quantity=3.4,
      **invoice_line_kw
    )
    invoice_2 = self.portal.accounting_module.newContent(
      start_date=DateTime('2012/01/01'),
      stop_date=DateTime('2012/02/01'),
      destination=person.getRelativeUrl(),
      destination_section=person.getRelativeUrl(),
      destination_decision=person.getRelativeUrl(),
      **invoice_kw
    )
    invoice_line_2 = invoice_2.newContent(
      aggregate=hosting_subscription.getRelativeUrl(),
      price=5.6,
      quantity=7.8,
      **invoice_line_kw
    )
    self.portal.portal_workflow._jumpToStateFor(invoice_1, 'confirmed')
    self.portal.portal_workflow._jumpToStateFor(invoice_1, 'calculating')
    self.portal.portal_workflow._jumpToStateFor(invoice_2, 'confirmed')
    self.portal.portal_workflow._jumpToStateFor(invoice_2, 'calculating')

    # create new simulation movements
    invoice_movement_kw = dict(
        causality=[
            'business_process_module/slapos_sale_business_process/invoice',
            'business_process_module/slapos_sale_business_process/invoice_path'
        ],
        trade_phase='slapos/invoicing',
        delivery_ratio=1.0,
        delivery_error=0.0,
        portal_type='Simulation Movement',
        aggregate=hosting_subscription.getRelativeUrl(),
        base_contribution=['base_amount/invoicing/discounted',
            'base_amount/invoicing/taxable'],
        destination=person.getRelativeUrl(),
        destination_decision=person.getRelativeUrl(),
        destination_section=person.getRelativeUrl(),
        price_currency='currency_module/EUR',
        quantity_unit='unit/piece',
        resource='service_module/slapos_instance_subscription',
        source='organisation_module/slapos',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        use='trade/sale',
    )
    invoice_rule_1 = simulation_movement_1.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_simulation_rule')
    invoice_movement_1 = invoice_rule_1.newContent(
        start_date=invoice_1.getStartDate(),
        stop_date=invoice_1.getStopDate(),
        quantity=invoice_line_1.getQuantity(),
        price=invoice_line_1.getPrice(),
        delivery=invoice_line_1.getRelativeUrl(),
        **invoice_movement_kw)

    invoice_rule_2 = simulation_movement_2.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_simulation_rule')
    invoice_movement_2 = invoice_rule_2.newContent(
        start_date=invoice_2.getStartDate(),
        stop_date=invoice_2.getStopDate(),
        quantity=invoice_line_2.getQuantity(),
        price=invoice_line_2.getPrice(),
        delivery=invoice_line_2.getRelativeUrl(),
        **invoice_movement_kw)
    self.tic()

    invoice_1.updateCausalityState(solve_automatically=False)
    invoice_2.updateCausalityState(solve_automatically=False)
    self.tic()

    # test the test
    self.assertEqual('solved', invoice_1.getCausalityState())
    self.assertEqual('solved', invoice_2.getCausalityState())

    model_movement_kw = dict(
      base_application='base_amount/invoicing/taxable',
      price_currency='currency_module/EUR',
      quantity_unit='unit/piece',
      source='organisation_module/slapos',
      source_section='organisation_module/slapos',
      specialise='sale_trade_condition_module/slapos_trade_condition',
      portal_type='Simulation Movement',
    )
    model_rule_1 = invoice_movement_1.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_trade_model_simulation_rule'
    )
    model_movement_1_tax = model_rule_1.newContent(
      destination=invoice_movement_1.getDestination(),
      destination_section=invoice_movement_1.getDestinationSection(),
      destination_decision=invoice_movement_1.getDestinationDecision(),
      resource='service_module/slapos_tax',
      trade_phase='slapos/tax',
      causality=['business_process_module/slapos_sale_business_process/tax',
          'business_process_module/slapos_sale_business_process/trade_model_path',
          'causality/sale_trade_condition_module/slapos_trade_condition/1',
      ],
      price=.196,
      quantity=invoice_movement_1.getTotalPrice(),
      **model_movement_kw
    )

    model_rule_2 = invoice_movement_2.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_trade_model_simulation_rule'
    )
    model_movement_2_tax = model_rule_2.newContent(
      destination=invoice_movement_2.getDestination(),
      destination_section=invoice_movement_2.getDestinationSection(),
      destination_decision=invoice_movement_2.getDestinationDecision(),
      resource='service_module/slapos_tax',
      trade_phase='slapos/tax',
      causality=['business_process_module/slapos_sale_business_process/tax',
          'business_process_module/slapos_sale_business_process/trade_model_path',
          'causality/sale_trade_condition_module/slapos_trade_condition/1',
      ],
      price=.196,
      quantity=invoice_movement_2.getTotalPrice(),
      **model_movement_kw
    )
    self.tic()

    self.portal.portal_deliveries\
        .slapos_sale_invoice_transaction_trade_model_builder.build(
        path='%s/%%' % applied_rule.getPath())
    self.tic()

    self.checkSimulationMovement(model_movement_1_tax)
    self.checkSimulationMovement(model_movement_2_tax)

    model_line_1_tax = model_movement_1_tax.getDeliveryValue()
    model_line_2_tax = model_movement_2_tax.getDeliveryValue()

    def checkModelLine(simulation_movement, transaction_line, category_list):
      self.assertEqual('Invoice Line',
          transaction_line.getPortalType())
      self.assertSameSet([
          'quantity_unit/unit/piece'
          ] + category_list,
        transaction_line.getCategoryList()
      )
      self.assertEqual(simulation_movement.getQuantity(),
          transaction_line.getQuantity())
      self.assertEqual(simulation_movement.getPrice(),
          transaction_line.getPrice())
      self.assertFalse(transaction_line.hasStartDate())
      self.assertFalse(transaction_line.hasStopDate())
      self.assertEqual([], transaction_line.contentValues(
          portal_type='Delivery Cell'))

    checkModelLine(model_movement_1_tax, model_line_1_tax, [
        'base_application/base_amount/invoicing/taxable',
        'resource/service_module/slapos_tax',
         'use/trade/tax'])
    checkModelLine(model_movement_2_tax, model_line_2_tax, [
        'base_application/base_amount/invoicing/taxable',
        'resource/service_module/slapos_tax',
         'use/trade/tax'])

    self.assertEqual(invoice_1.getRelativeUrl(),
        model_line_1_tax.getParentValue().getRelativeUrl())
    self.assertEqual(invoice_2.getRelativeUrl(),
        model_line_2_tax.getParentValue().getRelativeUrl())

    def checkModeledInvoice(invoice):
      self.assertEqual('confirmed', invoice.getSimulationState())
      self.assertEqual('building', invoice.getCausalityState())
      invoice.updateCausalityState(solve_automatically=False)
      self.assertEqual('solved', invoice.getCausalityState())

    checkModeledInvoice(invoice_1)
    checkModeledInvoice(invoice_2)

    model_movement_1_tax_bis = model_movement_1_tax.Base_createCloneDocument(
        batch_mode=1)
    self.tic()
    self.portal.portal_deliveries\
        .slapos_sale_invoice_transaction_trade_model_builder.build(
        path='%s/%%' % applied_rule.getPath())
    self.tic()
    self.checkSimulationMovement(model_movement_1_tax_bis)
    model_line_1_tax_bis = model_movement_1_tax_bis.getDeliveryValue()
    checkModelLine(model_movement_1_tax_bis,
        model_line_1_tax_bis)
    self.assertEqual(invoice_1.getRelativeUrl(),
        model_line_1_tax_bis.getParentValue().getRelativeUrl())


class TestSlapOSPaymentTransactionBuilder(testSlapOSMixin):
  def test(self):
    raise NotImplementedError

