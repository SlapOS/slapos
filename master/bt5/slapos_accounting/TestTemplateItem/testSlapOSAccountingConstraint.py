# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################
from testSlapOSCloudConstraint import TestSlapOSConstraintMixin
from Products.ERP5Type.Base import WorkflowMethod

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
  def test_price_currency(self):
    raise NotImplementedError

  def test_resource(self):
    raise NotImplementedError

  def test_sale_invoice_specialise_sale_trade_condition_constraint(self):
    raise NotImplementedError

  def test_specialise_value(self):
    raise NotImplementedError

  def test_total_price_equal_accounting(self):
    raise NotImplementedError

  def test_trade_model_match_lines(self):
    raise NotImplementedError
