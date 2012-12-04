# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################
from testSlapOSCloudConstraint import TestSlapOSConstraintMixin
from Products.ERP5Type.Base import WorkflowMethod
from Products.SlapOS.tests.testSlapOSMixin import withAbort
from Products.ERP5Type.tests.backportUnittest import skip

import transaction

class TestHostingSubscription(TestSlapOSConstraintMixin):

  # use decrator in order to avoid fixing consistency of new object
  @WorkflowMethod.disable
  def _createHostingSubscription(self):
    self.subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription')

  def afterSetUp(self):
    super(TestHostingSubscription, self).afterSetUp()
    self._createHostingSubscription()

  def beforeTearDown(self):
    transaction.abort()
    super(TestHostingSubscription, self).beforeTearDown()

  def test_periodicity_hour_list_value(self):
    value = 7
    message = 'Attribute periodicity_hour_list value is [7] but should be [0]'
    self.assertFalse(message in self.getMessageList(self.subscription))

    self.subscription.setPeriodicityHour(value)
    self.assertTrue(message in self.getMessageList(self.subscription))

    self.subscription.setPeriodicityHour(0)

    self.assertFalse(any([
        q.startswith('Attribute periodicity_hour_list value is') \
        for q in self.getMessageList(self.subscription)]))

  def test_periodicity_minute_list_value(self):
    value = 7
    message = 'Attribute periodicity_minute_list value is [7] but should be [0]'
    self.assertFalse(message in self.getMessageList(self.subscription))

    self.subscription.setPeriodicityMinute(value)
    self.assertTrue(message in self.getMessageList(self.subscription))

    self.subscription.setPeriodicityMinute(0)

    self.assertFalse(any([
        q.startswith('Attribute periodicity_minute_list value is') \
        for q in self.getMessageList(self.subscription)]))

  def test_periodicity_month_day_list_lenght(self):
    message = 'There was too many objects in periodicity_month_day_list'
    self.assertFalse(message in self.getMessageList(self.subscription))

    self.subscription.setPeriodicityMonthDayList([1, 2])
    self.assertTrue(message in self.getMessageList(self.subscription))

    self.subscription.setPeriodicityMonthDayList([1])
    self.assertFalse(message in self.getMessageList(self.subscription))

  def test_periodicity_month_day_value_range(self):
    message = 'The periodicity_month_day value is not between 1 and 28 '\
        'inclusive'
    self.assertFalse(message in self.getMessageList(self.subscription))

    self.subscription.setPeriodicityMonthDay(0)
    self.assertTrue(message in self.getMessageList(self.subscription))

    self.subscription.setPeriodicityMonthDay(29)
    self.assertTrue(message in self.getMessageList(self.subscription))

    self.subscription.setPeriodicityMonthDay(28)
    self.assertFalse(message in self.getMessageList(self.subscription))

    self.subscription.setPeriodicityMonthDay(1)
    self.assertFalse(message in self.getMessageList(self.subscription))

    self.subscription.setPeriodicityMonthDay(15)
    self.assertFalse(message in self.getMessageList(self.subscription))

    self.subscription.setPeriodicityMonthDay(None)
    self.assertFalse(message in self.getMessageList(self.subscription))

  def test_periodicity_property(self):
    template = 'Property existence error for property %s, this '\
        'document has no such property or the property has never been set'
    self._test_property_existence(self.subscription, 'periodicity_hour',
      template % 'periodicity_hour', empty_string=False)
    self._test_property_existence(self.subscription, 'periodicity_minute',
      template % 'periodicity_minute', empty_string=False)
    self._test_property_existence(self.subscription, 'periodicity_month_day',
      template % 'periodicity_month_day', empty_string=False)

class TestSaleInvoiceTransaction(TestSlapOSConstraintMixin):
  @withAbort
  def _test_currency(self, invoice, setter, message):
    self.assertTrue(message in self.getMessageList(invoice))

    currency = self.portal.currency_module.newContent(portal_type='Currency')
    setter(currency.getRelativeUrl())

    self.assertFalse(message in self.getMessageList(invoice))

    resource = self.portal.service_module.newContent(portal_type='Service')
    setter(resource.getRelativeUrl())
    self.assertTrue(message in self.getMessageList(invoice))

  def test_price_currency(self):
    invoice = self.portal.accounting_module.newContent(
        portal_type='Sale Invoice Transaction')
    message = "Arity Error for Relation ['price_currency'], arity is equal "\
        "to 0 but should be between 1 and 1"
    self._test_currency(invoice, invoice.setPriceCurrency, message)

  def test_resource(self):
    invoice = self.portal.accounting_module.newContent(
        portal_type='Sale Invoice Transaction')
    message = "Arity Error for Relation ['resource'], arity is equal "\
        "to 0 but should be between 1 and 1"
    self._test_currency(invoice, invoice.setResource, message)

  @withAbort
  def test_sale_invoice_specialise_sale_trade_condition_constraint(self):
    invoice = self.portal.accounting_module.newContent(
        portal_type='Sale Invoice Transaction')
    setter = invoice.setSpecialise
    message = "Arity Error for Relation ['specialise'], arity is equal "\
        "to 0 but should be at least 1"
    self.assertTrue(message in self.getMessageList(invoice))

    sale_condition = self.portal.sale_trade_condition_module.newContent(
        portal_type='Sale Trade Condition')
    setter(sale_condition.getRelativeUrl())

    self.assertFalse(message in self.getMessageList(invoice))

    purchase_condition = self.portal.purchase_trade_condition_module.newContent(
        portal_type='Purchase Trade Condition')
    setter(purchase_condition.getRelativeUrl())
    self.assertTrue(message in self.getMessageList(invoice))

  @withAbort
  def test_specialise_value(self):
    invoice = self.portal.accounting_module.newContent(
        portal_type='Sale Invoice Transaction')
    message = "Only SlapOS trade condition is allowed"
    self.assertTrue(message in self.getMessageList(invoice))

    sale_condition = self.portal.sale_trade_condition_module.newContent(
        portal_type='Sale Trade Condition')
    invoice.setSpecialise(sale_condition.getRelativeUrl())

    self.assertTrue(message in self.getMessageList(invoice))

    invoice.setSpecialise('sale_trade_condition_module/slapos_aggregated_trade_condition')
    self.assertFalse(message in self.getMessageList(invoice))

  @withAbort
  def test_total_price_equal_accounting(self):
    message = "Total price of invoice does not match accounting"
    invoice = self.portal.accounting_module.newContent(
        portal_type='Sale Invoice Transaction',
        price_currency='currency_module/EUR')
    invoice.newContent(portal_type='Invoice Line', quantity=1., price=1.)

    self.assertFalse(message in self.getMessageList(invoice))
    self.portal.portal_workflow._jumpToStateFor(invoice, 'confirmed')
    self.assertTrue(message in self.getMessageList(invoice))

    invoice.receivable.setQuantity(-1.0)
    invoice.income.setQuantity(1.0)
    self.assertFalse(message in self.getMessageList(invoice))

  @withAbort
  def test_trade_model_match_lines(self):
    message = "Defined Trade Model does not match Lines definition"
    invoice = self.portal.accounting_module.newContent(
        portal_type='Sale Invoice Transaction',
        price_currency='currency_module/EUR',
        specialise='sale_trade_condition_module/slapos_aggregated_trade_condition')
    invoice.newContent(portal_type='Invoice Line', quantity=1., price=1.,
        base_contribution='base_amount/invoicing/taxable')

    self.assertFalse(message in self.getMessageList(invoice))
    self.portal.portal_workflow._jumpToStateFor(invoice, 'confirmed')
    self.assertTrue(message in self.getMessageList(invoice))

    invoice.newContent(portal_type='Invoice Line', quantity=1., price=.196,
        use='trade/tax',
        )
    self.assertFalse(message in self.getMessageList(invoice))

  @withAbort
  def test_use_trade_sale_total_price_matches_delivery_constraint(self):
    message = "Total price does not match related Sale Packing List"
    delivery = self.portal.sale_packing_list_module.newContent(
      portal_type='Sale Packing List')
    delivery.newContent(portal_type='Sale Packing List Line',
      use='trade/sale', quantity=1., price=1.)
    invoice = self.portal.accounting_module.newContent(
        portal_type='Sale Invoice Transaction',
        causality=delivery.getRelativeUrl())
    invoice_line = invoice.newContent(portal_type='Invoice Line', quantity=2.,
        price=1., use='trade/sale')

    self.assertFalse(message in self.getMessageList(invoice))
    self.portal.portal_workflow._jumpToStateFor(invoice, 'confirmed')
    self.assertFalse(message in self.getMessageList(invoice))
    invoice.setSpecialise('sale_trade_condition_module/slapos_aggregated_trade_condition')
    self.assertTrue(message in self.getMessageList(invoice))
    invoice_line.setQuantity(1.)
    self.assertFalse(message in self.getMessageList(invoice))
    invoice.newContent(portal_type='Invoice Line', quantity=2.,
        price=1.)
    self.assertFalse(message in self.getMessageList(invoice))

class TestSalePackingList(TestSlapOSConstraintMixin):
  @withAbort
  def test_lines(self):
    message = 'Sale Packing List Line is not defined'
    delivery = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List')

    self.assertTrue(message in self.getMessageList(delivery))
    delivery.newContent(portal_type='Sale Packing List Line')
    self.assertFalse(message in self.getMessageList(delivery))

  @withAbort
  def test_reference_not_empty(self):
    message = 'Reference must be defined'
    delivery = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List')

    self.assertFalse(message in self.getMessageList(delivery))
    delivery.setReference(None)
    self.assertTrue(message in self.getMessageList(delivery))

  @withAbort
  def test_price_currency(self):
    message = 'Exactly one Currency shall be selected'
    delivery = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List')
    self.assertTrue(message in self.getMessageList(delivery))

    resource = self.portal.service_module.newContent(portal_type='Service')
    delivery.setPriceCurrency(resource.getRelativeUrl())
    self.assertTrue(message in self.getMessageList(delivery))

    currency_1 = self.portal.currency_module.newContent(portal_type='Currency')
    currency_2 = self.portal.currency_module.newContent(portal_type='Currency')
    delivery.setPriceCurrencyList([currency_1.getRelativeUrl(),
      currency_2.getRelativeUrl()])
    self.assertTrue(message in self.getMessageList(delivery))

    delivery.setPriceCurrency(currency_1.getRelativeUrl())
    self.assertFalse(message in self.getMessageList(delivery))

  @withAbort
  def _test_category_arrow(self, category):
    message = "Arity Error for Relation ['%s'], arity is equal to "\
        "0 but should be between 1 and 1" % category
    message_2 = "Arity Error for Relation ['%s'], arity is equal to "\
        "2 but should be between 1 and 1" % category
    delivery = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List')
    resource = self.portal.service_module.newContent(
        portal_type='Service').getRelativeUrl()
    person = self.portal.person_module.newContent(
        portal_type='Person').getRelativeUrl()
    organisation = self.portal.organisation_module.newContent(
        portal_type='Organisation').getRelativeUrl()

    key = '%s_list' % category
    self.assertTrue(message in self.getMessageList(delivery))
    delivery.edit(**{key: [resource]})
    self.assertTrue(message in self.getMessageList(delivery))
    delivery.edit(**{key: [person, organisation]})
    self.assertTrue(message_2 in self.getMessageList(delivery))
    delivery.edit(**{key: [person]})
    self.assertFalse(message in self.getMessageList(delivery))
    self.assertFalse(message_2 in self.getMessageList(delivery))
    delivery.edit(**{key: [organisation]})
    self.assertFalse(message in self.getMessageList(delivery))
    self.assertFalse(message_2 in self.getMessageList(delivery))

  def test_destination(self):
    self._test_category_arrow('destination')

  def test_destination_section(self):
    self._test_category_arrow('destination_section')

  def test_destination_decision(self):
    self._test_category_arrow('destination_decision')

  def test_source(self):
    self._test_category_arrow('source')

  def test_source_section(self):
    self._test_category_arrow('source_section')

  @withAbort
  def test_specialise(self):
    category = 'specialise'
    message = "Arity Error for Relation ['%s'], arity is equal to "\
        "0 but should be between 1 and 1" % category
    message_2 = "Arity Error for Relation ['%s'], arity is equal to "\
        "2 but should be between 1 and 1" % category
    delivery = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List')
    resource = self.portal.service_module.newContent(
        portal_type='Service').getRelativeUrl()
    stc_1 = self.portal.sale_trade_condition_module.newContent(
        portal_type='Sale Trade Condition').getRelativeUrl()
    stc_2 = self.portal.sale_trade_condition_module.newContent(
        portal_type='Sale Trade Condition').getRelativeUrl()

    key = '%s_list' % category
    self.assertTrue(message in self.getMessageList(delivery))
    delivery.edit(**{key: [resource]})
    self.assertTrue(message in self.getMessageList(delivery))
    delivery.edit(**{key: [stc_1, stc_2]})
    self.assertTrue(message_2 in self.getMessageList(delivery))
    delivery.edit(**{key: [stc_1]})
    self.assertFalse(message in self.getMessageList(delivery))
    self.assertFalse(message_2 in self.getMessageList(delivery))

  @withAbort
  def test_start_date(self):
    message = 'Property start_date must be defined'
    delivery = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List')
    self.assertTrue(message in self.getMessageList(delivery))
    delivery.setStartDate('2012/01/01')
    self.assertFalse(message in self.getMessageList(delivery))

class TestSalePackingListLine(TestSlapOSConstraintMixin):
  @withAbort
  def test_property_existence(self):
    message = 'Property existence error for property %s, this document has '\
        'no such property or the property has never been set'
    message_price = message % 'price'
    message_quantity = message % 'quantity'
    delivery_line = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List').newContent(
        portal_type='Sale Packing List Line')
    self.assertTrue(message_price in self.getMessageList(delivery_line))
    self.assertTrue(message_quantity in self.getMessageList(delivery_line))
    delivery_line.setQuantity(1.0)
    self.assertTrue(message_price in self.getMessageList(delivery_line))
    self.assertFalse(message_quantity in self.getMessageList(delivery_line))
    delivery_line.setPrice(1.0)
    self.assertFalse(message_price in self.getMessageList(delivery_line))
    self.assertFalse(message_quantity in self.getMessageList(delivery_line))

  @withAbort
  def test_resource_arity(self):
    category = 'resource'
    message = "Arity Error for Relation ['%s'], arity is equal to "\
        "0 but should be between 1 and 1" % category
    message_2 = "Arity Error for Relation ['%s'], arity is equal to "\
        "2 but should be between 1 and 1" % category
    delivery_line = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List').newContent(
        portal_type='Sale Packing List Line')
    product = self.portal.product_module.newContent(
        portal_type='Product').getRelativeUrl()
    service_1 = self.portal.service_module.newContent(
        portal_type='Service').getRelativeUrl()
    service_2 = self.portal.service_module.newContent(
        portal_type='Service').getRelativeUrl()

    key = '%s_list' % category
    self.assertTrue(message in self.getMessageList(delivery_line))
    delivery_line.edit(**{key: [product]})
    self.assertTrue(message in self.getMessageList(delivery_line))
    delivery_line.edit(**{key: [service_1, service_2]})
    self.assertTrue(message_2 in self.getMessageList(delivery_line))
    delivery_line.edit(**{key: [service_1]})
    self.assertFalse(message in self.getMessageList(delivery_line))
    self.assertFalse(message_2 in self.getMessageList(delivery_line))

class TestSalePackingListLineConsumption(TestSlapOSConstraintMixin):
  @withAbort
  def _test_aggregate(self, message, aggregate_1, aggregate_2):
    category = 'aggregate'
    delivery = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List')
    delivery_line = delivery.newContent(portal_type='Sale Packing List Line')
    product = self.portal.product_module.newContent(
        portal_type='Product').getRelativeUrl()

    key = '%s_list' % category
    self.assertFalse(message in self.getMessageList(delivery_line))
    delivery.edit(specialise='sale_trade_condition_module/slapos_consumption_trade_condition')
    self.assertTrue(message in self.getMessageList(delivery_line))
    delivery_line.edit(**{key: [product]})
    self.assertTrue(message in self.getMessageList(delivery_line))
    delivery_line.edit(**{key: [aggregate_1, aggregate_2]})
    self.assertTrue(message in self.getMessageList(delivery_line))
    delivery_line.edit(**{key: [aggregate_1]})
    self.assertFalse(message in self.getMessageList(delivery_line))

  def test_aggregate_hosting_subscription(self):
    self._test_aggregate("There should be one Hosting Subscription related",
      self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription').getRelativeUrl(),
      self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription').getRelativeUrl())

  def test_aggregate_software_instance(self):
    self._test_aggregate("There should be one Software or Slave Instance related",
      self.portal.software_instance_module.newContent(
        portal_type='Software Instance').getRelativeUrl(),
      self.portal.software_instance_module.newContent(
        portal_type='Software Instance').getRelativeUrl())
    self._test_aggregate("There should be one Software or Slave Instance related",
      self.portal.software_instance_module.newContent(
        portal_type='Slave Instance').getRelativeUrl(),
      self.portal.software_instance_module.newContent(
        portal_type='Slave Instance').getRelativeUrl())

class TestSalePackingListConsumption(TestSlapOSConstraintMixin):
  @skip('Not critical')
  def test(self):
    raise NotImplementedError

class TestSalePackingListLineSubscription(TestSlapOSConstraintMixin):
  @skip('Not critical')
  def test(self):
    raise NotImplementedError

class TestSalePackingListLineAggregated(TestSlapOSConstraintMixin):
  @skip('Not critical')
  def test(self):
    raise NotImplementedError

class TestSalePackingListSubscription(TestSlapOSConstraintMixin):
  @skip('Not critical')
  def test(self):
    raise NotImplementedError

class TestSalePackingListAggregated(TestSlapOSConstraintMixin):
  @skip('Not critical')
  def test(self):
    raise NotImplementedError
