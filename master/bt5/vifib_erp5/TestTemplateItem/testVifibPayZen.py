# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
import unittest
from Products.Vifib.tests.testVifibSlapWebService import \
  TestVifibSlapWebServiceMixin
from Products.ERP5Type.tests.Sequence import SequenceList
from ZTUtils import make_query
import difflib

class TestVifibPayZen(TestVifibSlapWebServiceMixin):

  def fakeSlapAuth(self):
    pass

  def unfakeSlapAuth(self):
    pass

  def stepCheckRelatedSystemEvent(self, sequence):
    # use catalog to select exactly interesting events
    # as there might be more because of running alarms
    event = self.portal.portal_catalog(
       portal_type='Payzen Event',
       default_destination_uid=sequence['payment'].getUid(),
       limit=2)
    self.assertEqual(1, len(event))
    event = event[0]
    self.assertEqual(event.getValidationState(), 'acknowledged')
    message = event.objectValues()
    self.assertEqual(1, len(message))
    message = message[0]
    self.assertEqual(message.getTitle(), 'Shown Page')
    self.assertEqual(message.getTextContent(), sequence['payment_page'])

  def stepCheckPaymentPage(self, sequence):
    callback = self.portal.web_site_module.hosting.payzen_callback
    query = make_query(dict(transaction=sequence['payment'].getRelativeUrl()))
    integration_site = self.portal.restrictedTraverse(self.portal\
      .portal_preferences.getPreferredPayzenIntegrationSite())
    vads_url_cancel=callback.cancel.absolute_url() + '?' + query
    vads_url_error=callback.error.absolute_url() + '?' + query
    vads_url_referral=callback.referral.absolute_url() + '?' + query
    vads_url_refused=callback.refused.absolute_url() + '?' + query
    vads_url_success=callback.success.absolute_url() + '?' + query
    vads_url_return=getattr(callback, 'return').absolute_url() + '?' + query
    data_dict = dict(
      vads_language='en',
      vads_url_cancel=vads_url_cancel,
      vads_url_error=vads_url_error,
      vads_url_referral=vads_url_referral,
      vads_url_refused=vads_url_refused,
      vads_url_success=vads_url_success,
      vads_url_return=vads_url_return,
      vads_trans_date=sequence['payment'].getStartDate().toZone('UTC')\
        .asdatetime().strftime('%Y%m%d%H%M%S'),
      vads_amount=str(int(round((sequence['payment']\
        .PaymentTransaction_getTotalPayablePrice() * -100), 0))),
      vads_currency=integration_site.getMappingFromCategory(
        'resource/currency_module/%s' % sequence[
          'payment'].getResourceReference()).split('/')[-1],
      vads_trans_id=integration_site.getMappingFromCategory('causality/%s'
        % sequence['payment'].getRelativeUrl()).split('_')[1],
      vads_site_id=self.portal.portal_secure_payments.vifib_payzen.getServiceUsername()
    )

    self.portal.portal_secure_payments.vifib_payzen._getFieldList(data_dict)
    data_dict['action'] = self.portal.portal_secure_payments\
      .vifib_payzen.default_link.getUrlString()
    expected = \
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
    self.assertEqual(sequence['payment_page'], expected,
      '\n'.join([q for q in difflib.unified_diff(expected.split('\n'),
        sequence['payment_page'].split('\n'))]))

  def stepCallStartPaymentOnConfirmedPayment(self, sequence, **kw):
    current_skin = self.app.REQUEST.get('portal_skin', 'View')
    try:
      self.changeSkin('Hosting')
      sequence['payment'] = self.portal.portal_catalog.getResultValue(
        portal_type="Payment Transaction", simulation_state="started")
      sequence['payment_page'] = sequence['payment'].__of__(
        self.portal.web_site_module.hosting
          ).AccountingTransaction_startPayment()
    finally:
      self.changeSkin(current_skin)

  def stepCallUpdateStatusOnPlannedPayment(self, sequence, **kw):
    sequence['payment'] = self.portal.portal_catalog.getResultValue(
      portal_type="Payment Transaction", simulation_state="planned")
    sequence['payment'].PaymentTransaction_updateStatus()

  def test_AccountingTransaction_startPayment(self):
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      LoginWebUser \
      CallStartPaymentOnConfirmedPayment \
      CleanTic \
      Logout \
      LoginERP5TypeTestCase \
      CheckPaymentPage \
      CheckRelatedSystemEvent \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckPlannedUnknownPayment(self, sequence):
    self.assertEqual(sequence['payment'].getSimulationState(), 'planned')
    self.assertEqual(self.portal.portal_catalog.countResults(portal_type='Payzen Event',
      default_destination_uid=sequence['payment'].getUid(),
      limit=1)[0][0], 0)

  def test_PaymentTransaction_updateStatus_planned_unknown(self):
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      LoginWebUser \
      CallUpdateStatusOnPlannedPayment \
      Tic \
      Logout \
      LoginERP5TypeTestCase \
      CheckPlannedUnknownPayment \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckPlannedRegisteredPayment(self, sequence):
    self.assertEqual(sequence['payment'].getSimulationState(), 'confirmed')
    self.assertEqual(self.portal.portal_catalog.countResults(portal_type='Payzen Event',
      default_destination_uid=sequence['payment'].getUid(),
      limit=3)[0][0], 2)
    raise NotImplementedError('Not finished checks.')

  def test_PaymentTransaction_updateStatus_planned_registered(self):
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      LoginWebUser \
      CallStartPaymentOnConfirmedPayment \
      CleanTic \
      Logout \
      LoginERP5TypeTestCase \
      CheckPaymentPage \
      CleanTic \
      CheckRelatedSystemEvent \
      Logout \
      LoginWebUser \
      CallUpdateStatusOnPlannedPayment \
      CleanTic \
      Logout \
      LoginERP5TypeTestCase \
      CheckPlannedRegisteredPayment \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_PaymentTransaction_updateStatus_confirmed_no_change(self):
    raise NotImplementedError

  def test_PaymentTransaction_updateStatus_confirmed_paid(self):
    raise NotImplementedError


def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibPayZen))
  return suite
