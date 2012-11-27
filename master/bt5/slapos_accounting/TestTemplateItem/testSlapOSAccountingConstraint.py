# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################
from testSlapOSCloudConstraint import TestSlapOSConstraintMixin
from Products.ERP5Type.Base import WorkflowMethod
from Products.SlapOS.tests.testSlapOSMixin import withAbort

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
