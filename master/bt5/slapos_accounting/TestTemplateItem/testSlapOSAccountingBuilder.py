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
    self.assertSameSet([simulation_movement.getRelativeUrl()],
        delivery_line.getDeliveryRelatedList(
            portal_type='Simulation Movement'))

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

    model_line_kw = dict(
      portal_type='Invoice Line',
      use='use/trade/tax',
      resource='service_module/slapos_tax',
      base_application='base_amount/invoicing/taxable'
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
    invoice_line_1_tax = invoice_1.newContent(
      price=.196,
      quantity=invoice_line_1.getTotalPrice(),
      **model_line_kw
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
    invoice_line_2_tax = invoice_2.newContent(
      price=.196,
      quantity=invoice_line_2.getTotalPrice(),
      **model_line_kw
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

    trade_movement_kw = dict(
        portal_type='Simulation Movement',
        price=.196,
        delivery_ratio=1.,
        delivery_error=0.,
        price_currency='currency_module/EUR',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        resource='service_module/slapos_tax',
        base_application='base_amount/invoicing/taxable',
        use='trade/tax',
        causality=['business_process_module/slapos_sale_business_process/tax',
            'business_process_module/slapos_sale_business_process/trade_model_path',
            'sale_trade_condition_module/slapos_trade_condition/1'],
    )
    trade_model_rule_1 = invoice_movement_1.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_trade_model_simulation_rule'
    )
    trade_movement_1 = trade_model_rule_1.newContent(
        source=invoice_movement_1.getSource(),
        destination=invoice_movement_1.getDestination(),
        source_section=invoice_movement_1.getSourceSection(),
        destination_section=invoice_movement_1.getDestinationSection(),
        quantity=invoice_movement_1.getTotalPrice(),
        delivery=invoice_line_1_tax.getRelativeUrl(),
        **trade_movement_kw
    )
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
    trade_model_rule_2 = invoice_movement_2.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_trade_model_simulation_rule'
    )
    trade_movement_2 = trade_model_rule_2.newContent(
        source=invoice_movement_2.getSource(),
        destination=invoice_movement_2.getDestination(),
        source_section=invoice_movement_2.getSourceSection(),
        destination_section=invoice_movement_2.getDestinationSection(),
        quantity=invoice_movement_2.getTotalPrice(),
        delivery=invoice_line_2_tax.getRelativeUrl(),
        **trade_movement_kw
    )
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
    transaction_movement_1_rec_bis.edit(delivery=None, delivery_ratio=1.0)
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

    transation_model_rule_1 = trade_movement_1.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_transaction_simulation_rule'
    )
    transation_model_movement_1_rec = transation_model_rule_1.newContent(
      portal_type='Simulation Movement',
      causality=['business_process_module/slapos_sale_business_process/account',
          'business_process_module/slapos_sale_business_process/accounting_tax2'],
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
      quantity=trade_movement_1.getTotalPrice() * -1,
    )
    transation_model_movement_1_rec_bis = transation_model_movement_1_rec\
        .Base_createCloneDocument(batch_mode=1)
    transation_model_movement_1_rec_bis.edit(delivery=None, delivery_ratio=1.0)
    transation_model_movement_1_sal = transation_model_rule_1.newContent(
      portal_type='Simulation Movement',
      causality=['business_process_module/slapos_sale_business_process/account',
          'business_process_module/slapos_sale_business_process/accounting_tax1'],
      destination=['account_module/refundable_vat'],
      destination_decision=invoice_movement_1.getDestinationDecision(),
      destination_section=invoice_movement_1.getDestinationSection(),
      quantity_unit='unit/piece',
      resource='currency_module/EUR',
      source='account_module/coll_vat',
      source_section='organisation_module/slapos',
      specialise='sale_trade_condition_module/slapos_trade_condition',
      trade_phase='slapos/accounting',
      price=1.0,
      quantity=trade_movement_1.getTotalPrice(),
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

    transation_model_rule_2 = trade_movement_2.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_transaction_simulation_rule'
    )
    transation_model_movement_2_rec = transation_model_rule_2.newContent(
      portal_type='Simulation Movement',
      causality=['business_process_module/slapos_sale_business_process/account',
          'business_process_module/slapos_sale_business_process/accounting_tax2'],
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
      quantity=trade_movement_2.getTotalPrice() * -1,
    )
    transation_model_movement_2_sal = transation_model_rule_2.newContent(
      portal_type='Simulation Movement',
      causality=['business_process_module/slapos_sale_business_process/account',
          'business_process_module/slapos_sale_business_process/accounting_tax1'],
      destination=['account_module/refundable_vat'],
      destination_decision=invoice_movement_2.getDestinationDecision(),
      destination_section=invoice_movement_2.getDestinationSection(),
      quantity_unit='unit/piece',
      resource='currency_module/EUR',
      source='account_module/coll_vat',
      source_section='organisation_module/slapos',
      specialise='sale_trade_condition_module/slapos_trade_condition',
      trade_phase='slapos/accounting',
      price=1.0,
      quantity=trade_movement_2.getTotalPrice(),
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

    self.checkSimulationMovement(transation_model_movement_1_rec)
    self.checkSimulationMovement(transation_model_movement_1_rec_bis)
    self.checkSimulationMovement(transation_model_movement_1_sal)
    self.checkSimulationMovement(transation_model_movement_2_rec)
    self.checkSimulationMovement(transation_model_movement_2_sal)

    transaction_line_1_rec = transaction_movement_1_rec.getDeliveryValue()
    transaction_line_1_rec_bis = transaction_movement_1_rec_bis.getDeliveryValue()
    transaction_line_1_sal = transaction_movement_1_sal.getDeliveryValue()
    transaction_line_2_rec = transaction_movement_2_rec.getDeliveryValue()
    transaction_line_2_sal = transaction_movement_2_sal.getDeliveryValue()

    transation_model_line_1_rec = transation_model_movement_1_rec.getDeliveryValue()
    transation_model_line_1_rec_bis = transation_model_movement_1_rec_bis.getDeliveryValue()
    transation_model_line_1_sal = transation_model_movement_1_sal.getDeliveryValue()
    transation_model_line_2_rec = transation_model_movement_2_rec.getDeliveryValue()
    transation_model_line_2_sal = transation_model_movement_2_sal.getDeliveryValue()

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
      self.assertSameSet([simulation_movement.getRelativeUrl()],
          transaction_line.getDeliveryRelatedList(
              portal_type='Simulation Movement'))

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

    checkTransactionLine(transation_model_movement_1_rec, transation_model_line_1_rec,
        ['source/account_module/receivable',
            'destination/account_module/payable'])
    checkTransactionLine(transation_model_movement_1_rec_bis,
        transation_model_line_1_rec_bis,
        ['source/account_module/receivable',
            'destination/account_module/payable'])
    checkTransactionLine(transation_model_movement_1_sal, transation_model_line_1_sal,
        ['destination/account_module/refundable_vat',
            'source/account_module/coll_vat'])
    checkTransactionLine(transation_model_movement_2_rec, transation_model_line_2_rec,
        ['source/account_module/receivable',
            'destination/account_module/payable'])
    checkTransactionLine(transation_model_movement_2_sal, transation_model_line_2_sal,
        ['destination/account_module/refundable_vat',
            'source/account_module/coll_vat'])

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

    self.assertEqual(invoice_1.getRelativeUrl(),
        transation_model_line_1_rec.getParentValue().getRelativeUrl())
    self.assertEqual(invoice_1.getRelativeUrl(),
        transation_model_line_1_rec_bis.getParentValue().getRelativeUrl())
    self.assertEqual(invoice_1.getRelativeUrl(),
        transation_model_line_1_sal.getParentValue().getRelativeUrl())
    self.assertEqual(invoice_2.getRelativeUrl(),
        transation_model_line_2_rec.getParentValue().getRelativeUrl())
    self.assertEqual(invoice_2.getRelativeUrl(),
        transation_model_line_2_sal.getParentValue().getRelativeUrl())

    def checkTransactionedInvoice(invoice):
      self.assertEqual('confirmed', invoice.getSimulationState())
      self.assertEqual('building', invoice.getCausalityState())
      invoice.updateCausalityState(solve_automatically=False)
      self.assertEqual('solved', invoice.getCausalityState())

    checkTransactionedInvoice(invoice_1)
    checkTransactionedInvoice(invoice_2)

    transaction_movement_1_rec_bis2 = transaction_movement_1_rec\
        .Base_createCloneDocument(batch_mode=1)
    transaction_movement_1_rec_bis2.edit(delivery=None, delivery_ratio=1.0)
    transation_model_movement_1_rec_bis2 = transation_model_movement_1_rec\
        .Base_createCloneDocument(batch_mode=1)
    transation_model_movement_1_rec_bis2.edit(delivery=None, delivery_ratio=1.0)
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

    self.checkSimulationMovement(transation_model_movement_1_rec_bis2)
    transation_model_line_1_rec_bis2 = transation_model_movement_1_rec_bis2\
        .getDeliveryValue()
    checkTransactionLine(transation_model_movement_1_rec_bis2,
        transation_model_line_1_rec_bis2,
        ['source/account_module/receivable',
            'destination/account_module/payable'])
    self.assertEqual(invoice_1.getRelativeUrl(),
        transation_model_line_1_rec_bis2.getParentValue().getRelativeUrl())

    checkTransactionedInvoice(invoice_1)
    self.assertEqual('solved', invoice_2.getCausalityState())
    self.assertEqual('confirmed', invoice_2.getSimulationState())

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
          'sale_trade_condition_module/slapos_trade_condition/1',
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
          'sale_trade_condition_module/slapos_trade_condition/1',
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
      self.assertSameSet([simulation_movement.getRelativeUrl()],
          transaction_line.getDeliveryRelatedList(
              portal_type='Simulation Movement'))

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
    model_movement_1_tax_bis.edit(delivery=None, delivery_ratio=1.0)
    self.tic()
    self.portal.portal_deliveries\
        .slapos_sale_invoice_transaction_trade_model_builder.build(
        path='%s/%%' % applied_rule.getPath())
    self.tic()
    self.checkSimulationMovement(model_movement_1_tax_bis)
    model_line_1_tax_bis = model_movement_1_tax_bis.getDeliveryValue()
    checkModelLine(model_movement_1_tax_bis, model_line_1_tax_bis, [
        'base_application/base_amount/invoicing/taxable',
        'resource/service_module/slapos_tax',
         'use/trade/tax'])
    self.assertEqual(invoice_1.getRelativeUrl(),
        model_line_1_tax_bis.getParentValue().getRelativeUrl())

class TestSlapOSPaymentTransactionBuilder(TestSlapOSSalePackingListBuilder):
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

    invoice_rule_1 = simulation_movement_1.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_simulation_rule')
    invoice_movement_1 = invoice_rule_1.newContent(
        portal_type='Simulation Movement'
    )
    trade_model_rule_1 = invoice_movement_1.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_trade_model_simulation_rule'
    )
    trade_movement_1 = trade_model_rule_1.newContent(
        portal_type='Simulation Movement'
    )
    invoice_rule_2 = simulation_movement_2.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_simulation_rule')
    invoice_movement_2 = invoice_rule_2.newContent(
        portal_type='Simulation Movement'
    )
    transaction_rule_1 = invoice_movement_1.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_transaction_simulation_rule'
    )
    invoice_1 = self.portal.accounting_module.newContent(
        portal_type='Sale Invoice Transaction')
    transaction_movement_1_rec = transaction_rule_1.newContent(
      portal_type='Simulation Movement',
      delivery=invoice_1.newContent(
          portal_type='Sale Invoice Transaction Line').getRelativeUrl()
    )

    transation_model_rule_1 = trade_movement_1.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_transaction_simulation_rule'
    )
    transation_model_movement_1_rec = transation_model_rule_1.newContent(
        portal_type='Simulation Movement',
        delivery=invoice_1.newContent(
          portal_type='Sale Invoice Transaction Line').getRelativeUrl()
    )

    transaction_rule_2 = invoice_movement_2.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_transaction_simulation_rule'
    )
    invoice_2 = self.portal.accounting_module.newContent(
        portal_type='Sale Invoice Transaction')
    transaction_movement_2_rec = transaction_rule_2.newContent(
      portal_type='Simulation Movement',
      delivery=invoice_2.newContent(
          portal_type='Sale Invoice Transaction Line').getRelativeUrl()
    )

    transation_model_rule_2 = invoice_movement_2.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_invoice_transaction_simulation_rule'
    )
    transation_model_movement_2_rec = transation_model_rule_2.newContent(
        portal_type='Simulation Movement',
        delivery=invoice_2.newContent(
          portal_type='Sale Invoice Transaction Line').getRelativeUrl()
    )

    # payment part of tree

    payment_rule_1_rec = transaction_movement_1_rec.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_payment_simulation_rule')
    payment_movement_1_rec_bank = payment_rule_1_rec.newContent(
        portal_type='Simulation Movement',
        price=1.0,
        quantity=-10.0,
        start_date=DateTime('2012/01/01'),
        stop_date=DateTime('2012/01/10'),
        causality=['business_process_module/slapos_sale_business_process/pay',
            'business_process_module/slapos_sale_business_process/payment_debit_path'],
        destination='account_module/bank',
        destination_section=person.getRelativeUrl(),
        quantity_unit='unit/piece',
        resource='currency_module/EUR',
        source='account_module/bank',
        source_payment='organisation_module/slapos/bank_account',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        trade_phase='slapos/payment'
    )
    payment_movement_1_rec_bank_bis = payment_movement_1_rec_bank.Base_createCloneDocument(
        batch_mode=1)
    payment_movement_1_rec_rec = payment_rule_1_rec.newContent(
        portal_type='Simulation Movement',
        price=1.0,
        quantity=10.0,
        start_date=DateTime('2012/01/01'),
        stop_date=DateTime('2012/01/10'),
        causality=['business_process_module/slapos_sale_business_process/pay',
            'business_process_module/slapos_sale_business_process/payment_credit_path'],
        destination='account_module/payable',
        destination_section=person.getRelativeUrl(),
        quantity_unit='unit/piece',
        resource='currency_module/EUR',
        source='account_module/receivable',
        source_payment='organisation_module/slapos/bank_account',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        trade_phase='slapos/payment'
    )
    payment_rule_model_1 = transation_model_movement_1_rec.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_payment_simulation_rule')
    payment_model_movement_1_rec_bank = payment_rule_model_1.newContent(
        portal_type='Simulation Movement',
        price=1.0,
        quantity=-10.0,
        start_date=DateTime('2012/01/01'),
        stop_date=DateTime('2012/01/10'),
        causality=['business_process_module/slapos_sale_business_process/pay',
            'business_process_module/slapos_sale_business_process/payment_debit_path'],
        destination='account_module/bank',
        destination_section=person.getRelativeUrl(),
        quantity_unit='unit/piece',
        resource='currency_module/EUR',
        source='account_module/bank',
        source_payment='organisation_module/slapos/bank_account',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        trade_phase='slapos/payment'
    )
    payment_model_movement_1_rec_rec = payment_rule_1_rec.newContent(
        portal_type='Simulation Movement',
        price=1.0,
        quantity=10.0,
        start_date=DateTime('2012/01/01'),
        stop_date=DateTime('2012/01/10'),
        causality=['business_process_module/slapos_sale_business_process/pay',
            'business_process_module/slapos_sale_business_process/payment_credit_path'],
        destination='account_module/payable',
        destination_section=person.getRelativeUrl(),
        quantity_unit='unit/piece',
        resource='currency_module/EUR',
        source='account_module/receivable',
        source_payment='organisation_module/slapos/bank_account',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        trade_phase='slapos/payment'
    )
    payment_rule_2_rec = transaction_movement_2_rec.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_payment_simulation_rule')
    payment_movement_2_rec_bank = payment_rule_2_rec.newContent(
        portal_type='Simulation Movement',
        price=1.0,
        quantity=-10.0,
        start_date=DateTime('2012/01/01'),
        stop_date=DateTime('2012/01/10'),
        causality=['business_process_module/slapos_sale_business_process/pay',
            'business_process_module/slapos_sale_business_process/payment_debit_path'],
        destination='account_module/bank',
        destination_section=person.getRelativeUrl(),
        quantity_unit='unit/piece',
        resource='currency_module/EUR',
        source='account_module/bank',
        source_payment='organisation_module/slapos/bank_account',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        trade_phase='slapos/payment'
    )
    payment_movement_2_rec_rec = payment_rule_2_rec.newContent(
        portal_type='Simulation Movement',
        price=1.0,
        quantity=10.0,
        start_date=DateTime('2012/01/01'),
        stop_date=DateTime('2012/01/10'),
        causality=['business_process_module/slapos_sale_business_process/pay',
            'business_process_module/slapos_sale_business_process/payment_credit_path'],
        destination='account_module/payable',
        destination_section=person.getRelativeUrl(),
        quantity_unit='unit/piece',
        resource='currency_module/EUR',
        source='account_module/receivable',
        source_payment='organisation_module/slapos/bank_account',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        trade_phase='slapos/payment'
    )
    payment_rule_model_2 = transation_model_movement_2_rec.newContent(
        portal_type='Applied Rule',
        specialise='portal_rules/slapos_payment_simulation_rule')
    payment_model_movement_2_rec_bank = payment_rule_model_2.newContent(
        portal_type='Simulation Movement',
        price=1.0,
        quantity=-10.0,
        start_date=DateTime('2012/01/01'),
        stop_date=DateTime('2012/01/10'),
        causality=['business_process_module/slapos_sale_business_process/pay',
            'business_process_module/slapos_sale_business_process/payment_debit_path'],
        destination='account_module/bank',
        destination_section=person.getRelativeUrl(),
        quantity_unit='unit/piece',
        resource='currency_module/EUR',
        source='account_module/bank',
        source_payment='organisation_module/slapos/bank_account',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        trade_phase='slapos/payment'
    )
    payment_model_movement_2_rec_rec = payment_rule_2_rec.newContent(
        portal_type='Simulation Movement',
        price=1.0,
        quantity=10.0,
        start_date=DateTime('2012/01/01'),
        stop_date=DateTime('2012/01/10'),
        causality=['business_process_module/slapos_sale_business_process/pay',
            'business_process_module/slapos_sale_business_process/payment_credit_path'],
        destination='account_module/payable',
        destination_section=person.getRelativeUrl(),
        quantity_unit='unit/piece',
        resource='currency_module/EUR',
        source='account_module/receivable',
        source_payment='organisation_module/slapos/bank_account',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        trade_phase='slapos/payment'
    )
    self.tic()
    self.portal.portal_deliveries.slapos_payment_transaction_builder.build(
        path='%s/%%' % applied_rule.getPath())
    self.tic()
    self.checkSimulationMovement(payment_movement_1_rec_bank)
    self.checkSimulationMovement(payment_movement_1_rec_bank_bis)
    self.checkSimulationMovement(payment_movement_1_rec_rec)
    self.checkSimulationMovement(payment_movement_2_rec_bank)
    self.checkSimulationMovement(payment_movement_2_rec_rec)
    self.checkSimulationMovement(payment_model_movement_1_rec_bank)
    self.checkSimulationMovement(payment_model_movement_1_rec_rec)
    self.checkSimulationMovement(payment_model_movement_2_rec_bank)
    self.checkSimulationMovement(payment_model_movement_2_rec_rec)

    transaction_line_1_rec_bank = payment_movement_1_rec_bank.getDeliveryValue()
    transaction_line_1_rec_bank_bis = payment_movement_1_rec_bank_bis.getDeliveryValue()
    transaction_line_1_rec_rec = payment_movement_1_rec_rec.getDeliveryValue()
    transaction_line_2_rec_bank = payment_movement_2_rec_bank.getDeliveryValue()
    transaction_line_2_rec_rec = payment_movement_2_rec_rec.getDeliveryValue()

    transaction_model_line_1_rec_bank = payment_model_movement_1_rec_bank.getDeliveryValue()
    transaction_model_line_1_rec_rec = payment_model_movement_1_rec_rec.getDeliveryValue()
    transaction_model_line_2_rec_bank = payment_model_movement_2_rec_bank.getDeliveryValue()
    transaction_model_line_2_rec_rec = payment_model_movement_2_rec_rec.getDeliveryValue()

    def checkTransactionLine(simulation_movement, transaction_line,
          category_list):
      self.assertEqual('Accounting Transaction Line',
          transaction_line.getPortalType())
      self.assertSameSet(category_list, transaction_line.getCategoryList())
      self.assertEqual(simulation_movement.getQuantity(),
          transaction_line.getQuantity())
      self.assertEqual(simulation_movement.getPrice(),
          transaction_line.getPrice())
      self.assertFalse(transaction_line.hasStartDate())
      self.assertFalse(transaction_line.hasStopDate())
      self.assertEqual([], transaction_line.contentValues(
          portal_type='Delivery Cell'))
      self.assertSameSet([simulation_movement.getRelativeUrl()],
          transaction_line.getDeliveryRelatedList(
              portal_type='Simulation Movement'))
      self.assertFalse(transaction_line.hasStartDate())
      self.assertFalse(transaction_line.hasStopDate())

    checkTransactionLine(payment_movement_1_rec_bank, transaction_line_1_rec_bank,
        ['destination/account_module/bank',
         'source/account_module/bank',
         'source_payment/organisation_module/slapos/bank_account'])
    checkTransactionLine(payment_movement_1_rec_bank_bis, transaction_line_1_rec_bank_bis,
        ['destination/account_module/bank',
         'source/account_module/bank',
         'source_payment/organisation_module/slapos/bank_account'])
    checkTransactionLine(payment_movement_1_rec_rec, transaction_line_1_rec_rec,
        ['destination/account_module/payable',
         'source/account_module/receivable',
         'source_payment/organisation_module/slapos/bank_account'])
    checkTransactionLine(payment_movement_2_rec_bank, transaction_line_2_rec_bank,
        ['destination/account_module/bank',
         'source/account_module/bank',
         'source_payment/organisation_module/slapos/bank_account'])
    checkTransactionLine(payment_movement_2_rec_rec, transaction_line_2_rec_rec,
        ['destination/account_module/payable',
         'source/account_module/receivable',
         'source_payment/organisation_module/slapos/bank_account'])

    checkTransactionLine(payment_model_movement_1_rec_bank, transaction_model_line_1_rec_bank,
        ['destination/account_module/bank',
         'source/account_module/bank',
         'source_payment/organisation_module/slapos/bank_account'])
    checkTransactionLine(payment_model_movement_1_rec_rec, transaction_model_line_1_rec_rec,
        ['destination/account_module/payable',
         'source/account_module/receivable',
         'source_payment/organisation_module/slapos/bank_account'])
    checkTransactionLine(payment_model_movement_2_rec_bank, transaction_model_line_2_rec_bank,
        ['destination/account_module/bank',
         'source/account_module/bank',
         'source_payment/organisation_module/slapos/bank_account'])
    checkTransactionLine(payment_model_movement_2_rec_rec, transaction_model_line_2_rec_rec,
        ['destination/account_module/payable',
         'source/account_module/receivable',
         'source_payment/organisation_module/slapos/bank_account'])

    self.assertEqual(transaction_line_1_rec_bank.getParentValue(),
        transaction_model_line_1_rec_bank.getParentValue())
    self.assertEqual(transaction_line_1_rec_bank_bis.getParentValue(),
        transaction_model_line_1_rec_bank.getParentValue())
    self.assertEqual(transaction_line_2_rec_bank.getParentValue(),
        transaction_model_line_2_rec_bank.getParentValue())
    self.assertEqual(transaction_line_1_rec_bank.getParentValue(),
        transaction_line_1_rec_rec.getParentValue())
    self.assertEqual(transaction_line_2_rec_bank.getParentValue(),
        transaction_line_2_rec_rec.getParentValue())
    self.assertEqual(transaction_model_line_1_rec_bank.getParentValue(),
        transaction_model_line_1_rec_rec.getParentValue())
    self.assertEqual(transaction_model_line_2_rec_bank.getParentValue(),
        transaction_model_line_2_rec_rec.getParentValue())

    self.assertNotEqual(transaction_line_1_rec_bank.getParentValue(),
        transaction_line_2_rec_bank.getParentValue())
    self.assertNotEqual(transaction_model_line_1_rec_bank.getParentValue(),
        transaction_model_line_2_rec_bank.getParentValue())

    def checkPayment(simulation_movement, payment):
      category_list = ['resource/currency_module/EUR',
         'source_section/organisation_module/slapos',
         'specialise/sale_trade_condition_module/slapos_trade_condition']
      category_list.append('causality/%s' % simulation_movement.getParentValue()\
            .getParentValue().getDeliveryValue().getParentValue().getRelativeUrl())
      category_list.append('destination_section/%s' %
          simulation_movement.getDestinationSection())
      self.assertSameSet(category_list, payment.getCategoryList())
      self.assertEqual(simulation_movement.getStartDate(),
          payment.getStartDate())
      self.assertEqual(simulation_movement.getStopDate(),
          payment.getStopDate())
      self.assertEqual('delivered', payment.getSimulationState())
      self.assertEqual('building', payment.getCausalityState())
      payment.updateCausalityState(solve_automatically=False)
      self.assertEqual('solved', payment.getCausalityState())

    checkPayment(payment_movement_1_rec_bank, transaction_line_1_rec_bank.getParentValue())
    checkPayment(payment_movement_2_rec_bank, transaction_line_2_rec_bank.getParentValue())

class TestSlapOSPaymentTransactionOrderBuilder(testSlapOSMixin):
  def sumReceivable(self, transaction):
    quantity = .0
    default_source_uid = self.portal.restrictedTraverse(
        'account_module/receivable').getUid()
    for line in transaction.searchFolder(
        portal_type=self.portal.getPortalAccountingMovementTypeList(),
        default_source_uid=default_source_uid):
      quantity += line.getQuantity()
    return quantity

  def assertPayment(self, payment, invoice):
    self.assertEqual(self.sumReceivable(invoice), payment\
        .PaymentTransaction_getTotalPayablePrice())
    self.assertEqual('auto_planned', payment.getSimulationState())
    self.assertSameSet([], payment.checkConsistency())
    self.assertSameSet([invoice], payment.getCausalityValueList())
    self.assertSameSet([], payment.getCausalityRelatedValueList(
        portal_type='Applied Rule'))
    expected_set = [
      'causality/%s' % invoice.getRelativeUrl(),
      'destination_section/%s' % invoice.getDestinationSection(),
      'price_currency/%s' % invoice.getPriceCurrency(),
      'resource/%s' % invoice.getResource(),
      'source_payment/organisation_module/slapos/bank_account',
      'source_section/%s' % invoice.getSourceSection(),
    ]
    self.assertSameSet(expected_set, payment.getCategoryList())
    self.assertEqual(invoice.getStartDate(), payment.getStartDate())
    self.assertEqual(invoice.getStopDate(), payment.getStopDate())

    movement_list = payment.getMovementList()
    self.assertEqual(2, len(movement_list))
    bank_list = [q for q in movement_list
        if q.getSource() == 'account_module/bank']
    rec_list = [q for q in movement_list
        if q.getSource() == 'account_module/receivable']
    self.assertEqual(1, len(bank_list))
    self.assertEqual(1, len(rec_list))

    def assertLine(line, quantity, category_list):
      self.assertFalse(line.hasStartDate())
      self.assertFalse(line.hasStopDate())
      self.assertEqual(quantity, line.getQuantity())
      self.assertSameSet(category_list, line.getCategoryList())

    invoice_amount = self.sumReceivable(invoice)
    assertLine(bank_list[0], invoice_amount, [
        'destination/account_module/bank',
        'source/account_module/bank'])
    assertLine(rec_list[0], -1 * invoice_amount, [
        'destination/account_module/payable',
        'source/account_module/receivable'])

  def emptyBuild(self, **kw):
    delivery_list = self._build(**kw)
    self.assertSameSet([], delivery_list)
    return delivery_list

  def fullBuild(self, **kw):
    delivery_list = self._build(**kw)
    self.assertNotEqual([], delivery_list)
    return delivery_list

  def _build(self, **kw):
    return self.portal.portal_orders.slapos_payment_transaction_builder.build(
        **kw)

  def test(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice.edit(destination_section=person.getRelativeUrl())
    invoice.confirm()
    invoice.stop()
    self.tic()
    payment_list = self.fullBuild(uid=invoice.getUid())
    self.tic()

    self.assertEqual(1, len(payment_list))

    payment = payment_list[0].getObject()
    self.assertPayment(payment, invoice)

  def test_twice(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice.edit(destination_section=person.getRelativeUrl())
    invoice.confirm()
    invoice.stop()
    self.tic()
    payment_list = self.fullBuild(uid=invoice.getUid())
    self.tic()
    self.emptyBuild(uid=invoice.getUid())

    self.assertEqual(1, len(payment_list))

    payment = payment_list[0].getObject()
    self.assertPayment(payment, invoice)

  def test_twice_transaction(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice.edit(destination_section=person.getRelativeUrl())
    invoice.confirm()
    invoice.stop()
    self.tic()
    payment_list = self.fullBuild(uid=invoice.getUid())
    self.emptyBuild(uid=invoice.getUid())
    self.tic()

    self.assertEqual(1, len(payment_list))

    payment = payment_list[0].getObject()
    self.assertPayment(payment, invoice)

  def test_twice_indexation(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice.edit(destination_section=person.getRelativeUrl())
    invoice.confirm()
    invoice.stop()
    self.tic()
    payment_list = self.fullBuild(uid=invoice.getUid())
    transaction.commit()
    # the payment transaction is immediately indexed
    self.assertEqual(1, len(payment_list))

    self.emptyBuild(uid=invoice.getUid())
    self.tic()


    payment = payment_list[0].getObject()
    self.assertPayment(payment, invoice)

  def test_two_invoices(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice_1 = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice_1.edit(destination_section=person.getRelativeUrl())
    invoice_1.confirm()
    invoice_1.stop()
    invoice_2 = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice_2.edit(destination_section=person.getRelativeUrl())
    invoice_2.confirm()
    invoice_2.stop()
    self.tic()
    payment_list = self.fullBuild(uid=[invoice_1.getUid(), invoice_2.getUid()])
    self.tic()

    self.assertEqual(2, len(payment_list))

    payment_1_list = [q for q in payment_list
        if q.getCausalityValue() == invoice_1]
    payment_2_list = [q for q in payment_list
        if q.getCausalityValue() == invoice_2]
    self.assertEqual(1, len(payment_1_list))
    self.assertEqual(1, len(payment_2_list))
    payment_1 = payment_1_list[0]
    payment_2 = payment_2_list[0]
    self.assertPayment(payment_1, invoice_1)
    self.assertPayment(payment_2, invoice_2)

  def test_two_lines(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice.edit(destination_section=person.getRelativeUrl())
    self.tic()
    default_source_uid = self.portal.restrictedTraverse(
        'account_module/receivable').getUid()
    modified = False
    for line in invoice.searchFolder(
        portal_type=self.portal.getPortalAccountingMovementTypeList(),
        default_source_uid=default_source_uid):
      quantity = line.getQuantity() / 2
      line.edit(quantity=quantity)
      line.getObject().Base_createCloneDocument(batch_mode=1).edit(
          quantity=quantity)
      modified = True
      break
    self.assertTrue(modified)

    invoice.confirm()
    invoice.stop()
    self.tic()
    payment_list = self.fullBuild(uid=[invoice.getUid()])
    self.tic()

    self.assertEqual(1, len(payment_list))

    payment = payment_list[0].getObject()
    self.assertPayment(payment, invoice)
