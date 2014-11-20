# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from DateTime import DateTime
from zExceptions import Unauthorized
from Products.ERP5Type.tests.utils import createZODBPythonScript

class TestSlapOSCurrency_getIntegrationMapping(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def test_integratedCurrency(self):
    currency = self.portal.currency_module.EUR
    self.assertEquals(currency.Currency_getIntegrationMapping(), '978')

  def test_getIntegrationMapping_notIntegratedCurrency(self):
    new_id = self.generateNewId()
    currency = self.portal.currency_module.newContent(
      portal_type='Currency',
      title="Currency %s" % new_id,
      reference="TESTCUR-%s" % new_id,
      )
    self.assertRaises(
      AssertionError, 
      currency.Currency_getIntegrationMapping)


class TestSlapOSAccountingTransaction_updateStartDate(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPaymentTransaction(self):
    new_id = self.generateNewId()
    return self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      )

  def test_date_changed(self):
    date = DateTime("2001/01/01")
    transaction = self.createPaymentTransaction()
    transaction.AccountingTransaction_updateStartDate(date)
    self.assertEquals(transaction.getStartDate(), date)

  def test_REQUEST_disallowed(self):
    date = DateTime()
    transaction = self.createPaymentTransaction()
    self.assertRaises(
      Unauthorized,
      transaction.AccountingTransaction_updateStartDate,
      date, REQUEST={})


class TestSlapOSPaymentTransaction_getPayzenId(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPaymentTransaction(self):
    new_id = self.generateNewId()
    return self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      )

  def test_getPayzenId_newPaymentTransaction(self):
    transaction = self.createPaymentTransaction()
    self.assertEquals(transaction.PaymentTransaction_getPayzenId(), (None, None))

  def test_getPayzenId_mappedPaymentTransaction(self):
    transaction = self.createPaymentTransaction()
    transaction_date, payzen_id = transaction.PaymentTransaction_generatePayzenId()
    transaction_date2, payzen_id2 = transaction.PaymentTransaction_getPayzenId()
    self.assertEquals(payzen_id, payzen_id2)
    self.assertEquals(transaction_date, transaction_date2)

  def test_getPayzenId_manualMappedPaymentTransaction(self):
    transaction = self.createPaymentTransaction()
    integration_site = self.portal.restrictedTraverse(
      self.portal.portal_preferences.getPreferredPayzenIntegrationSite())

    try:
      mapping = integration_site.getCategoryFromMapping(
        'Causality/%s' % transaction.getId().replace('-', '_'),
      create_mapping_line=True,
      create_mapping=True)
    except ValueError:
      pass
    integration_site.Causality[transaction.getId().replace('-', '_')].\
      setDestinationReference("20010101_123456")

    transaction_date, payzen_id = transaction.PaymentTransaction_getPayzenId()
    self.assertEquals(payzen_id, "123456")
    self.assertEquals(transaction_date, DateTime("20010101"))

  def test_getPayzenId_REQUEST_disallowed(self):
    date = DateTime()
    transaction = self.createPaymentTransaction()
    self.assertRaises(
      Unauthorized,
      transaction.PaymentTransaction_getPayzenId,
      REQUEST={})


class TestSlapOSPaymentTransaction_generatePayzenId(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPaymentTransaction(self):
    new_id = self.generateNewId()
    return self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      )

  def test_generatePayzenId_newPaymentTransaction(self):
    transaction = self.createPaymentTransaction()
    transaction_url = transaction.getId().replace('-', '_')

    integration_site = self.portal.restrictedTraverse(
      self.portal.portal_preferences.getPreferredPayzenIntegrationSite())

    # Integration tool returns category value as mapping if nothing is set
    mapping = integration_site.getCategoryFromMapping(
      'Causality/%s' % transaction_url)
    self.assertEquals(mapping, 'causality/%s' % transaction_url)
    category = integration_site.getMappingFromCategory(mapping)
    self.assertEquals(category, 'Causality/%s' % transaction_url)

    transaction_date, payzen_id = transaction.PaymentTransaction_generatePayzenId()

    mapping = integration_site.getCategoryFromMapping(
      'Causality/%s' % transaction_url)
    self.assertEquals(mapping, "%s_%s" % (
      transaction_date.asdatetime().strftime('%Y%m%d'), payzen_id))
    category = integration_site.getMappingFromCategory('causality/%s' % mapping)
    # XXX Not indexed yet
#     self.assertEquals(category, 'Causality/%s' % transaction_url)

    self.assertNotEquals(payzen_id, None)
    self.assertEquals(len(payzen_id), 6)
    self.assertEquals(str(int(payzen_id)).zfill(6), payzen_id)

    self.assertNotEquals(transaction_date, None)
    self.assertEquals(transaction_date.timezone(), 'UTC')
    self.assertEquals(transaction_date.asdatetime().strftime('%Y%m%d'),
                      DateTime().toZone('UTC').asdatetime().strftime('%Y%m%d'))


  def test_generatePayzenId_mappedPaymentTransaction(self):
    transaction = self.createPaymentTransaction()
    transaction.PaymentTransaction_generatePayzenId()
    payzen_id = transaction.PaymentTransaction_generatePayzenId()
    self.assertEquals(payzen_id, (None, None))

  def test_generatePayzenId_increasePaymentId(self):
    transaction = self.createPaymentTransaction()
    transaction2 = self.createPaymentTransaction()
    date, payzen_id = transaction.PaymentTransaction_generatePayzenId()
    date2, payzen_id2 = transaction2.PaymentTransaction_generatePayzenId()
    self.assertEquals(date.asdatetime().strftime('%Y%m%d'),
                      date2.asdatetime().strftime('%Y%m%d'))
    self.assertNotEquals(payzen_id, payzen_id2)
    self.assertTrue(int(payzen_id) < int(payzen_id2))

  def test_generatePayzenId_REQUEST_disallowed(self):
    date = DateTime()
    transaction = self.createPaymentTransaction()
    self.assertRaises(
      Unauthorized,
      transaction.PaymentTransaction_generatePayzenId,
      REQUEST={})


class TestSlapOSPaymentTransaction_createPayzenEvent(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPaymentTransaction(self):
    new_id = self.generateNewId()
    return self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      )

  def test_createPayzenEvent_REQUEST_disallowed(self):
    date = DateTime()
    transaction = self.createPaymentTransaction()
    self.assertRaises(
      Unauthorized,
      transaction.PaymentTransaction_createPayzenEvent,
      REQUEST={})

  def test_createPayzenEvent_newPayment(self):
    date = DateTime()
    transaction = self.createPaymentTransaction()
    payzen_event = transaction.PaymentTransaction_createPayzenEvent()
    self.assertEquals(payzen_event.getPortalType(), "Payzen Event")
    self.assertEquals(payzen_event.getSource(), 
      "portal_secure_payments/slapos_payzen_test")
    self.assertEquals(payzen_event.getDestination(), transaction.getRelativeUrl())

  def test_createPayzenEvent_kwParameter(self):
    date = DateTime()
    transaction = self.createPaymentTransaction()
    payzen_event = transaction.PaymentTransaction_createPayzenEvent(
      title='foo')
    self.assertEquals(payzen_event.getPortalType(), "Payzen Event")
    self.assertEquals(payzen_event.getSource(), 
      "portal_secure_payments/slapos_payzen_test")
    self.assertEquals(payzen_event.getDestination(), transaction.getRelativeUrl())
    self.assertEquals(payzen_event.getTitle(), "foo")


class TestSlapOSPayzenEvent_processUpdate(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPaymentTransaction(self):
    new_id = self.generateNewId()
    return self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      )

  def createPayzenEvent(self):
    return self.portal.system_event_module.newContent(
        portal_type='Payzen Event',
        reference='PAY-%s' % self.generateNewId())

  def test_processUpdate_REQUEST_disallowed(self):
    date = DateTime()
    event = self.createPayzenEvent()
    self.assertRaises(
      Unauthorized,
      event.PayzenEvent_processUpdate,
      'a', 'b',
      REQUEST={})

  def test_processUpdate_noTransaction(self):
    date = DateTime()
    event = self.createPayzenEvent()
    self.assertRaises(
      AttributeError,
      event.PayzenEvent_processUpdate,
      'a', 'b')

  def test_processUpdate_signatureBoolean(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)
    self.assertRaises(
      AssertionError,
      event.PayzenEvent_processUpdate,
      'a', 'b')

  def test_processUpdate_falseSignature(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)

    event.PayzenEvent_processUpdate('a', False)
    self.assertEquals(event.getValidationState(), "confirmed")
    self.assertEqual(
        'Signature does not match',
        event.workflow_history['system_event_workflow'][-1]['comment'])

  def test_processUpdate_wrongDataDictionnary(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)
    self.assertRaises(
      TypeError,
      event.PayzenEvent_processUpdate,
      'a', True)

  def test_processUpdate_unknownErrorCode(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': 'foo',
    }

    event.PayzenEvent_processUpdate(data_kw, True)
    self.assertEquals(event.getValidationState(), "confirmed")
    self.assertEqual(
        "Unknown errorCode 'foo'",
        event.workflow_history['system_event_workflow'][-1]['comment'])

  def test_processUpdate_unknownTransactionStatus(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '0',
      'transactionStatus': 'foo',
    }

    event.PayzenEvent_processUpdate(data_kw, True)
    self.assertEquals(event.getValidationState(), "confirmed")
    self.assertEqual(
        "Unknown transactionStatus 'foo'",
        event.workflow_history['system_event_workflow'][-1]['comment'])

  def test_processUpdate_notSupportedTransactionStatus(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '0',
      'transactionStatus': '2',
    }

    event.PayzenEvent_processUpdate(data_kw, True)
    self.assertEquals(event.getValidationState(), "confirmed")
    self.assertEqual(
        "Transaction status '2' ('To be forced - Contact issuer') " \
        "is not supported",
        event.workflow_history['system_event_workflow'][-1]['comment'])

  def test_processUpdate_notProcessedTransactionStatus(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    payment.edit(start_date=DateTime())
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '0',
      'transactionStatus': '0',
    }

    event.PayzenEvent_processUpdate(data_kw, True)

    self.assertEquals(event.getValidationState(), "acknowledged")
    self.assertEqual(
        'Automatic acknowledge as result of correct communication',
        event.workflow_history['system_event_workflow'][-1]['comment'])

    self.assertEquals(payment.getSimulationState(), "confirmed")
    self.assertEqual(
        'Transaction status 0 (Initial (being treated)) did not changed ' \
        'the document state',
        payment.workflow_history['edit_workflow'][-1]['comment'])
    self.assertEqual(
        'Confirmed as really saw in PayZen.',
        payment.workflow_history['accounting_workflow'][-1]['comment'])

  def test_processUpdate_notProcessedTransactionStatusConfirmedPayment(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    payment.edit(start_date=DateTime())
    payment.confirm()
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '0',
      'transactionStatus': '0',
    }
    event.PayzenEvent_processUpdate(data_kw, True)

  def test_processUpdate_noAuthAmount(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    payment.edit(start_date=DateTime())
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '0',
      'transactionStatus': '6',
    }

    self.assertRaises(
      KeyError,
      event.PayzenEvent_processUpdate,
      data_kw, True)

  def test_processUpdate_noAuthDevise(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    payment.edit(start_date=DateTime())
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '0',
      'transactionStatus': '6',
      'authAmount': 1,
    }

    self.assertRaises(
      KeyError,
      event.PayzenEvent_processUpdate,
      data_kw, True)

  def test_processUpdate_differentAmount(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    payment.edit(start_date=DateTime())
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '0',
      'transactionStatus': '6',
      'authAmount': 1,
      'authDevise': 1,
    }

    self.assertEquals(payment.PaymentTransaction_getTotalPayablePrice(), 0)
    event.PayzenEvent_processUpdate(data_kw, True)

    self.assertEquals(event.getValidationState(), "confirmed")
    self.assertEqual(
        'Received amount (1) does not match stored on transaction (0)',
        event.workflow_history['system_event_workflow'][-1]['comment'])

  def test_processUpdate_differentDevise(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    payment.edit(
      resource='currency_module/EUR',
      start_date=DateTime())
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '0',
      'transactionStatus': '6',
      'authAmount': 0,
      'authDevise': "dollars",
    }

    self.assertEquals(payment.PaymentTransaction_getTotalPayablePrice(), 0)
    event.PayzenEvent_processUpdate(data_kw, True)

    self.assertEquals(event.getValidationState(), "confirmed")
    self.assertEqual(
        "Received devise ('dollars') does not match stored on transaction ('978')",
        event.workflow_history['system_event_workflow'][-1]['comment'])

  def test_processUpdate_cancelledTransaction(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    payment.edit(
      resource='currency_module/EUR',
      start_date=DateTime())
    payment.cancel()
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '0',
      'transactionStatus': '6',
      'authAmount': 0,
      'authDevise': '978',
    }

    event.PayzenEvent_processUpdate(data_kw, True)

    self.assertEquals(event.getValidationState(), "confirmed")
    self.assertEqual(
        'Expected to put transaction in stopped state, but achieved only ' \
        'cancelled state',
        event.workflow_history['system_event_workflow'][-1]['comment'])

  def test_processUpdate_defaultUseCase(self):
    date = DateTime()
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    payment.edit(
      resource='currency_module/EUR',
      start_date=DateTime())
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '0',
      'transactionStatus': '6',
      'authAmount': 0,
      'authDevise': '978',
    }

    event.PayzenEvent_processUpdate(data_kw, True)

    self.assertEquals(payment.getSimulationState(), "stopped")
    self.assertEquals(event.getValidationState(), "acknowledged")
    self.assertEqual(
        'Automatic acknowledge as result of correct communication',
        event.workflow_history['system_event_workflow'][-1]['comment'])

  def _simulatePaymentTransaction_getRecentPayzenId(self):
    script_name = 'PaymentTransaction_getPayzenId'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""return DateTime().toZone('UTC'), 'foo'""")

  def _simulatePaymentTransaction_getOldPayzenId(self):
    script_name = 'PaymentTransaction_getPayzenId'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""from Products.ERP5Type.DateUtils import addToDate
return addToDate(DateTime(), to_add={'day': -1, 'second': -1}).toZone('UTC'), 'foo'""")

  def _dropPaymentTransaction_getPayzenId(self):
    script_name = 'PaymentTransaction_getPayzenId'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)

  def test_processUpdate_recentNotFoundOnPayzenSide(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '2',
    }

    self._simulatePaymentTransaction_getRecentPayzenId()
    try:
      event.PayzenEvent_processUpdate(data_kw, True)
    finally:
      self._dropPaymentTransaction_getPayzenId()

    self.assertEquals(event.getValidationState(), "acknowledged")
    self.assertEqual(
        'Transaction not found on payzen side.',
        event.workflow_history['system_event_workflow'][-1]['comment'])
    self.assertNotEquals(payment.getSimulationState(), "cancelled")
    self.assertEqual(
        'Error code 2 (Not found) did not changed the document state.',
        payment.workflow_history['edit_workflow'][-1]['comment'])

  def test_processUpdate_oldNotFoundOnPayzenSide(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '2',
    }

    self._simulatePaymentTransaction_getOldPayzenId()
    try:
      event.PayzenEvent_processUpdate(data_kw, True)
    finally:
      self._dropPaymentTransaction_getPayzenId()

    self.assertEquals(event.getValidationState(), "acknowledged")
    self.assertEqual(
        'Transaction not found on payzen side.',
        event.workflow_history['system_event_workflow'][-1]['comment'])
    self.assertEquals(payment.getSimulationState(), "cancelled")
    self.assertEqual(
        'Aborting unknown payzen payment.',
        payment.workflow_history['accounting_workflow'][-1]['comment'])

  def test_processUpdate_refusedPayzenPayment(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)

    data_kw = {
      'errorCode': '0',
      'transactionStatus': '8',
    }

    event.PayzenEvent_processUpdate(data_kw, True)

    self.assertEquals(event.getValidationState(), "acknowledged")
    self.assertEqual(
        'Refused payzen payment.',
        event.workflow_history['system_event_workflow'][-1]['comment'])
    self.assertEquals(payment.getSimulationState(), "cancelled")
    self.assertEqual(
        'Aborting refused payzen payment.',
        payment.workflow_history['accounting_workflow'][-1]['comment'])

class TestSlapOSPayzenBase_getPayzenServiceRelativeUrl(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def test_getPayzenServiceRelativeUrl_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Base_getPayzenServiceRelativeUrl,
      REQUEST={})

  def test_getPayzenServiceRelativeUrl_default_result(self):
    result = self.portal.Base_getPayzenServiceRelativeUrl()
    self.assertEquals(result, 'portal_secure_payments/slapos_payzen_test')

class TestSlapOSPayzenSaleInvoiceTransaction_createReversalPayzenTransaction(
                                                    testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPayzenSaleInvoiceTransaction(self):
    new_title = self.generateNewId()
    new_reference = self.generateNewId()
    new_source_reference = self.generateNewId()
    new_destination_reference = self.generateNewId()
    invoice = self.portal.accounting_module.newContent(
      portal_type="Sale Invoice Transaction",
      title=new_title,
      start_date=DateTime(),
      reference=new_reference,
      source_reference=new_source_reference,
      destination_reference=new_destination_reference,
      payment_mode="payzen",
      specialise="sale_trade_condition_module/slapos_aggregated_trade_condition",
      created_by_builder=1 # to prevent init script to create lines
    )
    self.portal.portal_workflow._jumpToStateFor(invoice, 'stopped')
    invoice.newContent(
      title="",
      portal_type="Invoice Line",
      quantity=-2,
      price=2,
    )
    invoice.newContent(
      portal_type="Sale Invoice Transaction Line",
      source="account_module/receivable",
      quantity=-3,
    )

    payment = self.portal.accounting_module.newContent(
      portal_type="Payment Transaction",
      payment_mode="payzen",
      causality_value=invoice,
      created_by_builder=1 # to prevent init script to create lines
    )
    self.portal.portal_workflow._jumpToStateFor(payment, 'started')
    return invoice

  def test_createReversalPayzenTransaction_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.SaleInvoiceTransaction_createReversalPayzenTransaction,
      REQUEST={})

  def test_createReversalPayzenTransaction_bad_portal_type(self):
    self.assertRaises(
      AssertionError,
      self.portal.SaleInvoiceTransaction_createReversalPayzenTransaction)

  def test_createReversalPayzenTransaction_bad_payment_mode(self):
    invoice = self.createPayzenSaleInvoiceTransaction()
    invoice.edit(payment_mode="cash")
    self.tic()
    self.assertRaises(
      AssertionError,
      invoice.SaleInvoiceTransaction_createReversalPayzenTransaction)

  def test_createReversalPayzenTransaction_bad_state(self):
    invoice = self.createPayzenSaleInvoiceTransaction()
    self.portal.portal_workflow._jumpToStateFor(invoice, 'delivered')
    self.tic()
    self.assertRaises(
      AssertionError,
      invoice.SaleInvoiceTransaction_createReversalPayzenTransaction)

  def test_createReversalPayzenTransaction_zero_price(self):
    invoice = self.createPayzenSaleInvoiceTransaction()
    invoice.manage_delObjects(invoice.contentIds())
    self.tic()
    self.assertRaises(
      AssertionError,
      invoice.SaleInvoiceTransaction_createReversalPayzenTransaction)

  def test_createReversalPayzenTransaction_wrong_trade_condition(self):
    invoice = self.createPayzenSaleInvoiceTransaction()
    invoice.edit(specialise=None)
    self.tic()
    self.assertRaises(
      AssertionError,
      invoice.SaleInvoiceTransaction_createReversalPayzenTransaction)

  def test_createReversalPayzenTransaction_paid(self):
    invoice = self.createPayzenSaleInvoiceTransaction()
    line = invoice.contentValues(portal_type="Sale Invoice Transaction Line")[0]
    line.edit(grouping_reference="azerty")
    self.tic()
    self.assertRaises(
      AssertionError,
      invoice.SaleInvoiceTransaction_createReversalPayzenTransaction)

  def test_createReversalPayzenTransaction_no_payment(self):
    invoice = self.createPayzenSaleInvoiceTransaction()
    # Do not reindex payment. portal_catalog will not find it.
    self.assertRaises(
      AssertionError,
      invoice.SaleInvoiceTransaction_createReversalPayzenTransaction)

  def test_createReversalPayzenTransaction_no_payzen_payment(self):
    invoice = self.createPayzenSaleInvoiceTransaction()
    self.tic()
    payment = invoice.getCausalityRelatedValue()
    payment.edit(payment_mode="cash")
    self.assertRaises(
      AssertionError,
      invoice.SaleInvoiceTransaction_createReversalPayzenTransaction)

  def test_createReversalPayzenTransaction_no_payment_state(self):
    invoice = self.createPayzenSaleInvoiceTransaction()
    self.tic()
    payment = invoice.getCausalityRelatedValue()
    self.portal.portal_workflow._jumpToStateFor(payment, 'cancelled')
    self.assertRaises(
      AssertionError,
      invoice.SaleInvoiceTransaction_createReversalPayzenTransaction)

  def test_createReversalPayzenTransaction_registered_payment(self):
    invoice = self.createPayzenSaleInvoiceTransaction()
    self.tic()
    payment = invoice.getCausalityRelatedValue()
    payment.PaymentTransaction_generatePayzenId()
    self.assertRaises(
      AssertionError,
      invoice.SaleInvoiceTransaction_createReversalPayzenTransaction)

  def test_createReversalPayzenTransaction_ok(self):
    invoice = self.createPayzenSaleInvoiceTransaction()
    self.tic()
    payment = invoice.getCausalityRelatedValue()
    reversale_invoice = invoice.\
      SaleInvoiceTransaction_createReversalPayzenTransaction()

    self.assertEqual(invoice.getPaymentMode(""), "")
    self.assertEqual(payment.getPaymentMode(""), "")
    self.assertEqual(payment.getSimulationState(), "cancelled")
    self.assertEqual(reversale_invoice.getTitle(),
                     "Reversal Transaction for %s" % invoice.getTitle())
    self.assertEqual(reversale_invoice.getDescription(),
                     "Reversal Transaction for %s" % invoice.getTitle())
    self.assertEqual(reversale_invoice.getCausality(),
                     invoice.getRelativeUrl())
    self.assertEqual(reversale_invoice.getSimulationState(), "stopped")
    self.assertEqual(invoice.getSimulationState(), "stopped")

    invoice_line_id = invoice.contentValues(portal_type="Invoice Line")[0].getId()
    transaction_line_id = invoice.contentValues(
      portal_type="Sale Invoice Transaction Line")[0].getId()

    self.assertEqual(invoice[invoice_line_id].getQuantity(),
                     -reversale_invoice[invoice_line_id].getQuantity())
    self.assertEqual(reversale_invoice[invoice_line_id].getQuantity(), 2)
    
    self.assertEqual(invoice[transaction_line_id].getQuantity(),
                     -reversale_invoice[transaction_line_id].getQuantity())
    self.assertEqual(reversale_invoice[transaction_line_id].getQuantity(), 3)
    self.assertEqual(len(invoice.getMovementList()), 2)

    # Both invoice should have a grouping reference
    self.assertNotEqual(invoice[transaction_line_id].getGroupingReference(""),
                        "")
    self.assertEqual(
      invoice[transaction_line_id].getGroupingReference("1"),
      reversale_invoice[transaction_line_id].getGroupingReference("2"))

    # All references should be regenerated
    self.assertNotEqual(invoice.getReference(""),
                        reversale_invoice.getReference(""))
    self.assertNotEqual(invoice.getSourceReference(""),
                        reversale_invoice.getSourceReference(""))
    self.assertNotEqual(invoice.getDestinationReference(""),
                        reversale_invoice.getDestinationReference(""))

    # Another trade condition
    self.assertEqual(
      reversale_invoice.getSpecialise(),
      "sale_trade_condition_module/slapos_manual_accounting_trade_condition")
    self.tic()

