# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin

class TestSlapOSCurrency_getIntegrationMapping(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def test_integratedCurrency(self):
    currency = self.portal.currency_module.EUR
    self.assertEquals(currency.Currency_getIntegrationMapping(), '978')

  def test_notIntegratedCurrency(self):
    new_id = self.generateNewId()
    currency = self.portal.currency_module.newContent(
      portal_type='Currency',
      title="Currency %s" % new_id,
      reference="TESTCUR-%s" % new_id,
      )
    self.assertRaises(
      AssertionError, 
      currency.Currency_getIntegrationMapping)
