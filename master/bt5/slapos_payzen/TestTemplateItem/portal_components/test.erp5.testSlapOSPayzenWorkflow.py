# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from unittest import expectedFailure
from Products.ERP5Type.Errors import UnsupportedWorkflowMethod
from AccessControl.SecurityManagement import getSecurityManager, \
             setSecurityManager
from DateTime import DateTime
from Products.ERP5Type.tests.utils import createZODBPythonScript
import difflib
from functools import wraps

HARDCODED_PRICE = 99.6

vads_url_cancel = 'http://example.org/cancel'
vads_url_error = 'http://example.org/error'
vads_url_referral = 'http://example.org/referral'
vads_url_refused = 'http://example.org/refused'
vads_url_success = 'http://example.org/success'
vads_url_return = 'http://example.org/return'

class TestSlapOSPayzenInterfaceWorkflow(testSlapOSMixin):

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

  def _simulatePaymentTransaction_getTotalPayablePrice(self):
    script_name = 'PaymentTransaction_getTotalPayablePrice'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\nreturn %f' % HARDCODED_PRICE)

  def _dropPaymentTransaction_getTotalPayablePrice(self):
    script_name = 'PaymentTransaction_getTotalPayablePrice'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)

  def test_generateManualPaymentPage_mandatoryParameters(self):
    event = self.createPayzenEvent()
    # vads_url_cancel
    self.assertRaises(TypeError, event.generateManualPaymentPage,
      vads_url_error=vads_url_error,
      vads_url_referral=vads_url_referral,
      vads_url_refused=vads_url_refused,
      vads_url_success=vads_url_success,
      vads_url_return=vads_url_return,
    )
    # vads_url_error
    self.assertRaises(TypeError, event.generateManualPaymentPage,
      vads_url_cancel=vads_url_cancel,
      vads_url_referral=vads_url_referral,
      vads_url_refused=vads_url_refused,
      vads_url_success=vads_url_success,
      vads_url_return=vads_url_return,
    )
    # vads_url_referral
    self.assertRaises(TypeError, event.generateManualPaymentPage,
      vads_url_cancel=vads_url_cancel,
      vads_url_error=vads_url_error,
      vads_url_refused=vads_url_refused,
      vads_url_success=vads_url_success,
      vads_url_return=vads_url_return,
    )
    # vads_url_refused
    self.assertRaises(TypeError, event.generateManualPaymentPage,
      vads_url_cancel=vads_url_cancel,
      vads_url_error=vads_url_error,
      vads_url_referral=vads_url_referral,
      vads_url_success=vads_url_success,
      vads_url_return=vads_url_return,
    )
    # vads_url_success
    self.assertRaises(TypeError, event.generateManualPaymentPage,
      vads_url_cancel=vads_url_cancel,
      vads_url_error=vads_url_error,
      vads_url_referral=vads_url_referral,
      vads_url_refused=vads_url_refused,
      vads_url_return=vads_url_return,
    )
    # vads_url_return
    self.assertRaises(TypeError, event.generateManualPaymentPage,
      vads_url_cancel=vads_url_cancel,
      vads_url_error=vads_url_error,
      vads_url_referral=vads_url_referral,
      vads_url_refused=vads_url_refused,
      vads_url_success=vads_url_success,
    )

  def test_generateManualPaymentPage_noAccountingTransaction(self):
    event = self.createPayzenEvent()
    self.assertRaises(AttributeError, event.generateManualPaymentPage,
      vads_url_cancel=vads_url_cancel,
      vads_url_error=vads_url_error,
      vads_url_referral=vads_url_referral,
      vads_url_refused=vads_url_refused,
      vads_url_success=vads_url_success,
      vads_url_return=vads_url_return,
    )

  def test_generateManualPaymentPage_registeredTransaction(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)
    transaction_date, payzen_id = payment.PaymentTransaction_generatePayzenId()
    self.assertRaises(ValueError, event.generateManualPaymentPage,
      vads_url_cancel=vads_url_cancel,
      vads_url_error=vads_url_error,
      vads_url_referral=vads_url_referral,
      vads_url_refused=vads_url_refused,
      vads_url_success=vads_url_success,
      vads_url_return=vads_url_return,
    )

  def test_generateManualPaymentPage_noPaymentService(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(destination_value=payment)
    self.assertRaises(AttributeError, event.generateManualPaymentPage,
      vads_url_cancel=vads_url_cancel,
      vads_url_error=vads_url_error,
      vads_url_referral=vads_url_referral,
      vads_url_refused=vads_url_refused,
      vads_url_success=vads_url_success,
      vads_url_return=vads_url_return,
    )

  def test_generateManualPaymentPage_noCurrency(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(
      destination_value=payment,
      source="portal_secure_payments/slapos_payzen_test",
    )
    self.assertRaises(AttributeError, event.generateManualPaymentPage,
      vads_url_cancel=vads_url_cancel,
      vads_url_error=vads_url_error,
      vads_url_referral=vads_url_referral,
      vads_url_refused=vads_url_refused,
      vads_url_success=vads_url_success,
      vads_url_return=vads_url_return,
    )

  def test_generateManualPaymentPage_defaultUseCase(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    payment.edit(
      resource="currency_module/EUR",
    )
    event.edit(
      destination_value=payment,
      source="portal_secure_payments/slapos_payzen_test",
    )

    before_date = DateTime()
    self._simulatePaymentTransaction_getTotalPayablePrice()
    try:
      event.generateManualPaymentPage(
        vads_url_cancel=vads_url_cancel,
        vads_url_error=vads_url_error,
        vads_url_referral=vads_url_referral,
        vads_url_refused=vads_url_refused,
        vads_url_success=vads_url_success,
        vads_url_return=vads_url_return,
      )
    finally:
      self._dropPaymentTransaction_getTotalPayablePrice()
    after_date = DateTime()

    # Payment start date is modified
    self.assertTrue(payment.getStartDate() >= before_date)
    self.assertTrue(payment.getStopDate() <= after_date)

    # Payment is registered
    transaction_date, transaction_id = \
      payment.PaymentTransaction_getPayzenId()
    self.assertNotEquals(transaction_date, None)
    self.assertNotEquals(transaction_id, None)

    # Event state
    self.assertEquals(event.getValidationState(), "acknowledged")

    data_dict = {
      'vads_language': 'en',
      'vads_url_cancel': vads_url_cancel,
      'vads_url_error': vads_url_error,
      'vads_url_referral': vads_url_referral,
      'vads_url_refused': vads_url_refused,
      'vads_url_success': vads_url_success,
      'vads_url_return': vads_url_return,
      'vads_trans_date': payment.getStartDate().toZone('UTC')\
                           .asdatetime().strftime('%Y%m%d%H%M%S'),
      'vads_amount': str(int(HARDCODED_PRICE * -100)),
      'vads_currency': 978,
      'vads_trans_id': transaction_id,
      'vads_site_id': 'foo',
    }
    # Calculate the signature...
    self.portal.portal_secure_payments.slapos_payzen_test._getFieldList(data_dict)
    data_dict['action'] = 'https://secure.payzen.eu/vads-payment/'

    expected_html_page = \
      '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w'\
      '3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n<html xmlns="http://www.w3.or'\
      'g/1999/xhtml" xml:lang="en" lang="en">\n<head>\n  <meta http-equiv="Co'\
      'ntent-Type" content="text/html; charset=utf-8" />\n  <meta http-equiv='\
      '"Content-Script-Type" content="text/javascript" />\n  <meta http-equiv'\
      '="Content-Style-Type" content="text/css" />\n  <title>title</title>\n<'\
      '/head>\n<body onload="document.payment.submit();">\n<form method="POST'\
      '" id="payment" name="payment"\n      action="%(action)s">\n\n  <input '\
      'type="hidden" name="vads_url_return"\n         value="'\
      '%(vads_url_return)s">\n\n\n  <input type="hidden" name="vads_site_id" '\
      'value="%(vads_site_id)s">\n\n\n  <input type="hidden" name="vads_url_e'\
      'rror"\n         value="%(vads_url_error)s">\n\n\n  <input type="hidden'\
      '" name="vads_trans_id" value="%(vads_trans_id)s">\n\n\n  <input type="'\
      'hidden" name="vads_action_mode"\n         value="INTERACTIVE">\n\n\n  '\
      '<input type="hidden" name="vads_url_success"\n         value="'\
      '%(vads_url_success)s">\n\n\n  <input type="hidden" name="vads_url_refe'\
      'rral"\n         value="%(vads_url_referral)s">\n\n\n  <input type="hid'\
      'den" name="vads_page_action"\n         value="PAYMENT">\n\n\n  <input '\
      'type="hidden" name="vads_trans_date"\n         value="'\
      '%(vads_trans_date)s">\n\n\n  <input type="hidden" name="vads_url_refus'\
      'ed"\n         value="%(vads_url_refused)s">\n\n\n  <input type="hidden'\
      '" name="vads_url_cancel"\n         value="%(vads_url_cancel)s">\n\n\n '\
      ' <input type="hidden" name="vads_ctx_mode" value="TEST">\n\n\n  <input '\
      'type="hidden" name="vads_payment_config"\n         value="SINGLE">\n\n'\
      '\n  <input type="hidden" name="vads_contrib" value="ERP5">\n\n\n  <inp'\
      'ut type="hidden" name="signature"\n         value="%(signature)s">\n\n'\
      '\n  <input type="hidden" name="vads_language" value="%(vads_language)s">\n\n\n  <inpu'\
      't type="hidden" name="vads_currency" value="%(vads_currency)s">\n\n\n '\
      ' <input type="hidden" name="vads_amount" value="%(vads_amount)s">\n\n\n'\
      '  <input type="hidden" name="vads_version" value="V2">\n\n<input type="s'\
      'ubmit" value="Click to pay">\n</form>\n</body>\n</html>' % data_dict

    # Event message state
    event_message_list = event.contentValues(portal_type="Payzen Event Message")
    self.assertEquals(len(event_message_list), 1)
    message = event_message_list[0]
    self.assertEqual(message.getTitle(), 'Shown Page')
    self.assertEqual(message.getTextContent(), expected_html_page,
      '\n'.join([q for q in difflib.unified_diff(expected_html_page.split('\n'),
        message.getTextContent().split('\n'))]))

  def test_updateStatus_noAccountingTransaction(self):
    event = self.createPayzenEvent()
    self.assertRaises(AttributeError, event.updateStatus)

  def test_updateStatus_notRegisteredTransaction(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(
      destination_value=payment,
    )
    self.assertRaises(ValueError, event.updateStatus)

  def test_updateStatus_noPaymentService(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(
      destination_value=payment,
    )
    transaction_date, payzen_id = payment.PaymentTransaction_generatePayzenId()
    self.assertRaises(AttributeError, event.updateStatus)

  def mockSoapGetInfo(self, method_to_call, expected_args, result_tuple):
    payment_service = self.portal.portal_secure_payments.slapos_payzen_test
    def mocksoad_getInfo(arg1, arg2):
      self.assertEquals(arg1, expected_args[0])
      self.assertEquals(arg2, expected_args[1])
      return result_tuple
    setattr(payment_service, 'soap_getInfo', mocksoad_getInfo)
    try:
      return method_to_call()
    finally:
      del payment_service.soap_getInfo

  def _simulatePayzenEvent_processUpdate(self):
    script_name = 'PayzenEvent_processUpdate'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by PayzenEvent_processUpdate') """ )
    transaction.commit()

  def _dropPayzenEvent_processUpdate(self):
    script_name = 'PayzenEvent_processUpdate'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_updateStatus_defaultUseCase(self):
    event = self.createPayzenEvent()
    payment = self.createPaymentTransaction()
    event.edit(
      destination_value=payment,
      source="portal_secure_payments/slapos_payzen_test",
    )
    transaction_date, transaction_id = \
      payment.PaymentTransaction_generatePayzenId()

    mocked_data_kw = 'mocked_data_kw'
    mocked_signature = 'mocked_signature'
    mocked_sent_text = 'mocked_sent_text'
    mocked_received_text = 'mocked_received_text'

    self._simulatePayzenEvent_processUpdate()
    try:
      self.mockSoapGetInfo(
        event.updateStatus,
        (transaction_date.toZone('UTC').asdatetime(), transaction_id),
        (mocked_data_kw, mocked_signature, mocked_sent_text, mocked_received_text),
      )
    finally:
      self._dropPayzenEvent_processUpdate()

    event_message_list = event.contentValues(portal_type="Payzen Event Message")
    self.assertEquals(len(event_message_list), 2)

    sent_message = [x for x in event_message_list \
                    if x.getTitle() == 'Sent SOAP'][0]
    self.assertEquals(sent_message.getTextContent(), mocked_sent_text)

    received_message = [x for x in event_message_list \
                        if x.getTitle() == 'Received SOAP'][0]
    self.assertEquals(received_message.getPredecessor(), 
                      sent_message.getRelativeUrl())
    self.assertEquals(received_message.getTextContent(), mocked_received_text)

    self.assertEqual(
        'Visited by PayzenEvent_processUpdate',
        event.workflow_history['edit_workflow'][-1]['comment'])

