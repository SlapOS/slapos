# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from erp5.component.test.SlapOSTestCaseMixin import SlapOSTestCaseMixinWithAbort

from DateTime import DateTime
from zExceptions import Unauthorized
from Products.ERP5Type.tests.utils import createZODBPythonScript

class TestSlapOSCurrency_getIntegrationMapping(SlapOSTestCaseMixinWithAbort):

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


class TestSlapOSAccountingTransaction_updateStartDate(SlapOSTestCaseMixinWithAbort):

  def createPaymentTransaction(self):
    new_id = self.generateNewId()
    return self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      )

  def test_date_changed(self):
    date = DateTime("2001/01/01")
    payment_transaction = self.createPaymentTransaction()
    payment_transaction.AccountingTransaction_updateStartDate(date)
    self.assertEquals(payment_transaction.getStartDate(), date)

  def test_REQUEST_disallowed(self):
    date = DateTime()
    payment_transaction = self.createPaymentTransaction()
    self.assertRaises(
      Unauthorized,
      payment_transaction.AccountingTransaction_updateStartDate,
      date, REQUEST={})


class TestSlapOSPaymentTransaction_getPayzenId(SlapOSTestCaseMixinWithAbort):

  def test_getPayzenId_newPaymentTransaction(self):
    payment_transaction = self.createPaymentTransaction()
    self.assertEquals(payment_transaction.PaymentTransaction_getPayzenId(), (None, None))

  def test_getPayzenId_mappedPaymentTransaction(self):
    payment_transaction = self.createPaymentTransaction()
    transaction_date, payzen_id = payment_transaction.PaymentTransaction_generatePayzenId()
    transaction_date2, payzen_id2 = payment_transaction.PaymentTransaction_getPayzenId()
    self.assertEquals(payzen_id, payzen_id2)
    self.assertEquals(transaction_date, transaction_date2)

  def test_getPayzenId_manualMappedPaymentTransaction(self):
    payment_transaction = self.createPaymentTransaction()
    integration_site = self.portal.restrictedTraverse(
      self.portal.portal_preferences.getPreferredPayzenIntegrationSite())

    try:
      integration_site.getCategoryFromMapping(
        'Causality/%s' % payment_transaction.getId().replace('-', '_'),
      create_mapping_line=True,
      create_mapping=True)
    except ValueError:
      pass
    integration_site.Causality[payment_transaction.getId().replace('-', '_')].\
      setDestinationReference("20010101_123456")

    transaction_date, payzen_id = payment_transaction.PaymentTransaction_getPayzenId()
    self.assertEquals(payzen_id, "123456")
    self.assertEquals(transaction_date, DateTime("20010101"))

  def test_getPayzenId_REQUEST_disallowed(self):
    payment_transaction = self.createPaymentTransaction()
    self.assertRaises(
      Unauthorized,
      payment_transaction.PaymentTransaction_getPayzenId,
      REQUEST={})


class TestSlapOSPaymentTransaction_generatePayzenId(SlapOSTestCaseMixinWithAbort):

  def test_generatePayzenId_newPaymentTransaction(self):
    payment_transaction = self.createPaymentTransaction()
    transaction_url = payment_transaction.getId().replace('-', '_')

    integration_site = self.portal.restrictedTraverse(
      self.portal.portal_preferences.getPreferredPayzenIntegrationSite())

    # Integration tool returns category value as mapping if nothing is set
    mapping = integration_site.getCategoryFromMapping(
      'Causality/%s' % transaction_url)
    self.assertEquals(mapping, 'causality/%s' % transaction_url)
    category = integration_site.getMappingFromCategory(mapping)
    self.assertEquals(category, 'Causality/%s' % transaction_url)

    transaction_date, payzen_id = payment_transaction.PaymentTransaction_generatePayzenId()

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
    payment_transaction = self.createPaymentTransaction()
    payment_transaction.PaymentTransaction_generatePayzenId()
    payzen_id = payment_transaction.PaymentTransaction_generatePayzenId()
    self.assertEquals(payzen_id, (None, None))

  def test_generatePayzenId_increasePaymentId(self):
    payment_transaction = self.createPaymentTransaction()
    payment_transaction2 = self.createPaymentTransaction()
    date, payzen_id = payment_transaction.PaymentTransaction_generatePayzenId()
    date2, payzen_id2 = payment_transaction2.PaymentTransaction_generatePayzenId()
    self.assertEquals(date.asdatetime().strftime('%Y%m%d'),
                      date2.asdatetime().strftime('%Y%m%d'))
    self.assertNotEquals(payzen_id, payzen_id2)
    self.assertTrue(int(payzen_id) < int(payzen_id2))

  def test_generatePayzenId_REQUEST_disallowed(self):
    payment_transaction = self.createPaymentTransaction()
    self.assertRaises(
      Unauthorized,
      payment_transaction.PaymentTransaction_generatePayzenId,
      REQUEST={})


class TestSlapOSPaymentTransaction_createPayzenEvent(SlapOSTestCaseMixinWithAbort):

  def test_createPayzenEvent_REQUEST_disallowed(self):
    payment_transaction = self.createPaymentTransaction()
    self.assertRaises(
      Unauthorized,
      payment_transaction.PaymentTransaction_createPayzenEvent,
      REQUEST={})

  def test_createPayzenEvent_newPayment(self):
    payment_transaction = self.createPaymentTransaction()
    payzen_event = payment_transaction.PaymentTransaction_createPayzenEvent()
    self.assertEquals(payzen_event.getPortalType(), "Payzen Event")
    self.assertEquals(payzen_event.getSource(),
      "portal_secure_payments/slapos_payzen_test")
    self.assertEquals(payzen_event.getDestination(), payment_transaction.getRelativeUrl())

  def test_createPayzenEvent_kwParameter(self):
    payment_transaction = self.createPaymentTransaction()
    payzen_event = payment_transaction.PaymentTransaction_createPayzenEvent(
      title='foo')
    self.assertEquals(payzen_event.getPortalType(), "Payzen Event")
    self.assertEquals(payzen_event.getSource(),
      "portal_secure_payments/slapos_payzen_test")
    self.assertEquals(payzen_event.getDestination(), payment_transaction.getRelativeUrl())
    self.assertEquals(payzen_event.getTitle(), "foo")


class TestSlapOSPayzenEvent_processUpdate(SlapOSTestCaseMixinWithAbort):

  def test_processUpdate_REQUEST_disallowed(self):
    event = self.createPayzenEvent()
    self.assertRaises(
      Unauthorized,
      event.PayzenEvent_processUpdate,
      'a', 'b',
      REQUEST={})

  def test_processUpdate_noTransaction(self):
    event = self.createPayzenEvent()
    self.assertRaises(
      AttributeError,
      event.PayzenEvent_processUpdate,
      'a', 'b')

  def test_processUpdate_signatureBoolean(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)
    self.assertRaises(
      AssertionError,
      event.PayzenEvent_processUpdate,
      'a', 'b')

  def test_processUpdate_falseSignature(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)

    event.PayzenEvent_processUpdate('a', False)
    self.assertEquals(event.getValidationState(), "confirmed")
    self.assertEqual(
        'Signature does not match',
        event.workflow_history['system_event_workflow'][-1]['comment'])

  def test_processUpdate_wrongDataDictionnary(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)
    self.assertRaises(
      TypeError,
      event.PayzenEvent_processUpdate,
      'a', True)

  def test_processUpdate_unknownErrorCode(self):
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

class TestSlapOSPayzenBase_getPayzenServiceRelativeUrl(SlapOSTestCaseMixinWithAbort):

  def test_getPayzenServiceRelativeUrl_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Base_getPayzenServiceRelativeUrl,
      REQUEST={})

  def test_getPayzenServiceRelativeUrl_default_result(self):
    result = self.portal.Base_getPayzenServiceRelativeUrl()
    self.assertEquals(result, 'portal_secure_payments/slapos_payzen_test')

class TestSlapOSPayzenAccountingTransaction_getPaymentState(
                                                    SlapOSTestCaseMixinWithAbort):

  def test_AccountingTransaction_getPaymentState_draft_payment(self):
    invoice = self.createSaleInvoiceTransaction()
    self.assertEquals("Cancelled", invoice.AccountingTransaction_getPaymentState())

  def test_AccountingTransaction_getPaymentState_deleted_payment(self):
    invoice = self.createSaleInvoiceTransaction()
    invoice.delete()
    self.assertEquals("Cancelled", invoice.AccountingTransaction_getPaymentState())

  def test_AccountingTransaction_getPaymentState_cancelled_payment(self):
    invoice = self.createSaleInvoiceTransaction()
    invoice.cancel()
    self.assertEquals("Cancelled", invoice.AccountingTransaction_getPaymentState())

  def test_AccountingTransaction_getPaymentState_planned_payment(self):
    invoice = self.createSaleInvoiceTransaction()
    invoice.plan()
    self.assertEquals("Ongoing", invoice.AccountingTransaction_getPaymentState())

  def test_AccountingTransaction_getPaymentState_confirmed_payment(self):
    invoice = self.createSaleInvoiceTransaction()
    invoice.setStartDate(DateTime())
    invoice.confirm()
    self.assertEquals("Ongoing", invoice.AccountingTransaction_getPaymentState())

  def test_AccountingTransaction_getPaymentState_started_payment(self):
    invoice = self.createSaleInvoiceTransaction()
    invoice.start()
    self.assertEquals("Ongoing", invoice.AccountingTransaction_getPaymentState())

  def test_AccountingTransaction_getPaymentState_reversed_payment(self):
    invoice =  self.createPayzenSaleInvoiceTransaction()
    self.tic()
    reversal = invoice.SaleInvoiceTransaction_createReversalPayzenTransaction()
    self.tic()
    self.assertEquals("Cancelled", invoice.AccountingTransaction_getPaymentState())
    self.assertEquals(0, invoice.getTotalPrice() + reversal.getTotalPrice())

  def test_AccountingTransaction_getPaymentState_free_payment(self):
    invoice =  self.createPayzenSaleInvoiceTransaction(price=0)
    self.tic()
    self.assertEquals("Free!", invoice.AccountingTransaction_getPaymentState())

  def test_AccountingTransaction_getPaymentState_unpaid_payment(self):
    invoice =  self.createPayzenSaleInvoiceTransaction()
    # If payment is not indexed or not started the state should be unpaid
    self.assertEquals("Unpaid", invoice.AccountingTransaction_getPaymentState())

  def test_AccountingTransaction_getPaymentState_paynow_payment(self):
    person = self.makePerson()
    invoice =  self.createPayzenSaleInvoiceTransaction(
      destination_section=person.getRelativeUrl())
    self.tic()
    self.login(person.getUserId())
    self.assertEquals("Pay now", invoice.AccountingTransaction_getPaymentState())

  def test_AccountingTransaction_getPaymentState_waiting_payment(self):
    person = self.makePerson()
    invoice =  self.createPayzenSaleInvoiceTransaction(
      destination_section=person.getRelativeUrl())
    self.tic()
    payment = invoice.SaleInvoiceTransaction_getPayzenPaymentRelatedValue()
    payment.PaymentTransaction_generatePayzenId()
    self.login(person.getUserId())
    self.assertEquals("Waiting for payment confirmation",
                      invoice.AccountingTransaction_getPaymentState())

  def test_AccountingTransaction_getPaymentState_paid_payment(self):
    invoice =  self.createPayzenSaleInvoiceTransaction()
    self.tic()
    for line in invoice.getMovementList(self.portal.getPortalAccountingMovementTypeList()):
      node_value = line.getSourceValue(portal_type='Account')
      if node_value.getAccountType() == 'asset/receivable':
        line.setGroupingReference("TEST%s" % self.new_id)
    self.assertEquals("Paid", invoice.AccountingTransaction_getPaymentState())

class TestSlapOSPayzenPaymentTransaction_redirectToManualPayzenPayment(
                                                    SlapOSTestCaseMixinWithAbort):


  def test_PaymentTransaction_redirectToManualPayzenPayment(self):
    payment = self.createPaymentTransaction()
    self.assertRaises(ValueError, payment.PaymentTransaction_redirectToManualPayzenPayment)

  def _simulatePaymentTransaction_getVADSUrlDict(self):
    script_name = 'PaymentTransaction_getVADSUrlDict'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""payment_transaction_url = context.getRelativeUrl()
return dict(vads_url_already_registered="%s/already_registered" % (payment_transaction_url),
  vads_url_cancel="%s/cancel" % (payment_transaction_url),
  vads_url_error="%s/error" % (payment_transaction_url),
  vads_url_referral="%s/referral" % (payment_transaction_url),
  vads_url_refused="%s/refused" % (payment_transaction_url),
  vads_url_success="%s/success" % (payment_transaction_url),
  vads_url_return="%s/return" % (payment_transaction_url),
)""")

  def _dropPaymentTransaction_getVADSUrlDict(self):
    script_name = 'PaymentTransaction_getVADSUrlDict'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)


  def test_PaymentTransaction_redirectToManualPayzenPayment_unauthorzied(self):
    payment = self.createPaymentTransaction()
    self._simulatePaymentTransaction_getVADSUrlDict()
    try:
      self.assertRaises(Unauthorized, payment.PaymentTransaction_redirectToManualPayzenPayment)
    finally:
      self._dropPaymentTransaction_getVADSUrlDict()

  def test_PaymentTransaction_redirectToManualPayzenPayment_redirect(self):
    person = self.makePerson()
    invoice =  self.createPayzenSaleInvoiceTransaction(
      destination_section=person.getRelativeUrl())
    self.tic()
    payment = invoice.SaleInvoiceTransaction_getPayzenPaymentRelatedValue()
    payment.setResourceValue(self.portal.currency_module.EUR)
    self.tic()
    self.login(person.getUserId())
    self._simulatePaymentTransaction_getVADSUrlDict()
    try:
      text_content = payment.PaymentTransaction_redirectToManualPayzenPayment()
    finally:
      self._dropPaymentTransaction_getVADSUrlDict()

    payment_transaction_url = payment.getRelativeUrl()
    for item in ["vads_site_id",
                 payment_transaction_url,
                 "vads_url_cancel",
                 "%s/cancel" % (payment_transaction_url),
                 "vads_url_error",
                 "%s/error" % (payment_transaction_url),
                 "vads_url_referral",
                 "%s/referral" % (payment_transaction_url),
                 "vads_url_refused",
                 "%s/refused" % (payment_transaction_url),
                 "vads_url_success",
                 "%s/success" % (payment_transaction_url),
                 "vads_url_return",
                 "%s/return" % (payment_transaction_url)]:
      self.assertTrue(item in text_content,
        "%s not in %s" % (item, text_content))


  def test_PaymentTransaction_redirectToManualPayzenPayment_already_registered(self):
    person = self.makePerson()
    invoice =  self.createPayzenSaleInvoiceTransaction(
      destination_section=person.getRelativeUrl())
    self.tic()
    payment = invoice.SaleInvoiceTransaction_getPayzenPaymentRelatedValue()
    payment.setResourceValue(self.portal.currency_module.EUR)
    payment.PaymentTransaction_generatePayzenId()
    self.tic()
    self.login(person.getUserId())
    self._simulatePaymentTransaction_getVADSUrlDict()
    try:
      redirect = payment.PaymentTransaction_redirectToManualPayzenPayment()
    finally:
      self._dropPaymentTransaction_getVADSUrlDict()

    self.assertEquals("%s/already_registered" % payment.getRelativeUrl(),
                      redirect)

class TestSlapOSPayzenSaleInvoiceTransaction_getPayzenPaymentRelatedValue(
                                                    SlapOSTestCaseMixinWithAbort):

  def test_SaleInvoiceTransaction_getPayzenPaymentRelatedValue(self):
    invoice =  self.createPayzenSaleInvoiceTransaction()
    self.tic()
    payment = invoice.SaleInvoiceTransaction_getPayzenPaymentRelatedValue()
    self.assertNotEquals(None, payment)
    self.assertEquals(payment.getSimulationState(), "started")
    self.assertEquals(payment.getCausalityValue(), invoice)
    self.assertEquals(payment.getPaymentModeUid(),
      self.portal.portal_categories.payment_mode.payzen.getUid())

    payment.setStartDate(DateTime())
    payment.stop()
    payment.immediateReindexObject()
    payment = invoice.SaleInvoiceTransaction_getPayzenPaymentRelatedValue()
    self.assertEquals(None, payment)

class TestSlapOSPayzenSaleInvoiceTransaction_createReversalPayzenTransaction(
                                                    SlapOSTestCaseMixinWithAbort):

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

