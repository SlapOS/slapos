# Copyright (c) 2013 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from zExceptions import Unauthorized
from DateTime import DateTime
from functools import wraps
from Products.ERP5Type.tests.utils import createZODBPythonScript
import difflib

def simulate(script_id, params_string, code_string):
  def upperWrap(f):
    @wraps(f)
    def decorated(self, *args, **kw):
      if script_id in self.portal.portal_skins.custom.objectIds():
        raise ValueError('Precondition failed: %s exists in custom' % script_id)
      createZODBPythonScript(self.portal.portal_skins.custom,
                          script_id, params_string, code_string)
      try:
        result = f(self, *args, **kw)
      finally:
        if script_id in self.portal.portal_skins.custom.objectIds():
          self.portal.portal_skins.custom.manage_delObjects(script_id)
        transaction.commit()
      return result
    return decorated
  return upperWrap


class TestSlapOSPerson_checkToCreateRegularisationRequest(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPerson(self):
    new_id = self.generateNewId()
    return self.portal.person_module.newContent(
      portal_type='Person',
      title="Person %s" % new_id,
      reference="TESTPERS-%s" % new_id,
      )

  @simulate('Entity_statBalance', '*args, **kwargs', 'return "1"')
  def test_addRegularisationRequest_payment_requested(self):
    for preference in \
      self.portal.portal_catalog(portal_type="System Preference"):
      preference = preference.getObject()
      if preference.getPreferenceState() == 'global':
        preference.setPreferredSlaposWebSiteUrl('http://foobar.org/')

    person = self.createPerson()
    before_date = DateTime()
    ticket, event = person.Person_checkToCreateRegularisationRequest()
    after_date = DateTime()
    self.assertEquals(ticket.getPortalType(), 'Regularisation Request')
    self.assertEquals(ticket.getSimulationState(), 'suspended')
    self.assertEquals(ticket.getSourceProject(), person.getRelativeUrl())
    self.assertEquals(ticket.getResource(),
                      'service_module/slapos_crm_acknowledgement')
    self.assertEquals(ticket.getTitle(),
           'Account regularisation expected for "%s"' % person.getTitle())
    self.assertEquals(ticket.getDestination(),
                      person.getRelativeUrl())
    self.assertEquals(ticket.getDestinationDecision(),
                      person.getRelativeUrl())
    self.assertEquals(event.getPortalType(), 'Mail Message')
    self.assertEquals(event.getResource(),
                      'service_module/slapos_crm_acknowledgement')
    self.assertTrue(event.getStartDate() >= before_date)
    self.assertTrue(event.getStopDate() <= after_date)
    self.assertEquals(event.getTitle(), "Invoice payment requested")
    self.assertEquals(event.getDestination(),
                      person.getRelativeUrl())
    self.assertEquals(event.getSource(),
                      ticket.getSource())
    expected_text_content = """Dear user,

A new invoice has been generated. 
You can access it in your invoice section at http://foobar.org/.

Do not hesitate to visit the web forum (http://community.slapos.org/forum) in case of question.

Regards,
The slapos team
"""
    self.assertEquals(event.getTextContent(), expected_text_content,
                      '\n'.join([x for x in difflib.unified_diff(
                                           event.getTextContent().splitlines(),
                                           expected_text_content.splitlines())]))
    self.assertEquals(event.getSimulationState(), 'delivered')


#   def test_addRegularisationRequest_do_not_duplicate_ticket(self):
#     person = self.createPerson()
#     ticket = person.Person_checkToCreateRegularisationRequest()
#     ticket2 = person.Person_checkToCreateRegularisationRequest()
#     self.assertEquals(ticket.getRelativeUrl(), ticket2.getRelativeUrl())

  @simulate('Entity_statBalance', '*args, **kwargs', 'return "1"')
  def test_addRegularisationRequest_do_not_duplicate_ticket_if_not_reindexed(self):
    person = self.createPerson()
    ticket, event = person.Person_checkToCreateRegularisationRequest()
    transaction.commit()
    ticket2, event2 = person.Person_checkToCreateRegularisationRequest()
    self.assertNotEquals(ticket, None)
    self.assertNotEquals(event, None)
    self.assertEquals(ticket2, None)
    self.assertEquals(event2, None)

  @simulate('Entity_statBalance', '*args, **kwargs', 'return "0"')
  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_addRegularisationRequest_balance_ok(self):
    person = self.createPerson()
    ticket, event = person.Person_checkToCreateRegularisationRequest()
    self.assertEquals(ticket, None)
    self.assertEquals(event, None)

  @simulate('Entity_statBalance', '*args, **kwargs', 'return "1"')
  def test_addRegularisationRequest_existing_suspended_ticket(self):
    person = self.createPerson()
    ticket, event = person.Person_checkToCreateRegularisationRequest()
    transaction.commit()
    self.tic()
    ticket2, event2 = person.Person_checkToCreateRegularisationRequest()
    self.assertNotEquals(ticket, None)
    self.assertNotEquals(event, None)
    self.assertEquals(ticket2.getRelativeUrl(), ticket.getRelativeUrl())
    self.assertEquals(event2, None)

  @simulate('Entity_statBalance', '*args, **kwargs', 'return "1"')
  def test_addRegularisationRequest_existing_validated_ticket(self):
    person = self.createPerson()
    ticket, event = person.Person_checkToCreateRegularisationRequest()
    ticket.validate()
    transaction.commit()
    self.tic()
    ticket2, event2 = person.Person_checkToCreateRegularisationRequest()
    self.assertNotEquals(ticket, None)
    self.assertNotEquals(event, None)
    self.assertEquals(ticket2.getRelativeUrl(), ticket.getRelativeUrl())
    self.assertEquals(event2, None)

  @simulate('Entity_statBalance', '*args, **kwargs', 'return "1"')
  def test_addRegularisationRequest_existing_invalidated_ticket(self):
    person = self.createPerson()
    ticket, event = person.Person_checkToCreateRegularisationRequest()
    ticket.invalidate()
    transaction.commit()
    self.tic()
    ticket2, event2 = person.Person_checkToCreateRegularisationRequest()
    self.assertNotEquals(ticket2.getRelativeUrl(), ticket.getRelativeUrl())
    self.assertNotEquals(event2, None)

  def test_addRegularisationRequest_REQUEST_disallowed(self):
    date = DateTime()
    person = self.createPerson()
    self.assertRaises(
      Unauthorized,
      person.Person_checkToCreateRegularisationRequest,
      REQUEST={})


class TestSlapOSRegularisationRequest_invalidateIfPersonBalanceIsOk(
                                                         testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPerson(self):
    new_id = self.generateNewId()
    return self.portal.person_module.newContent(
      portal_type='Person',
      title="Person %s" % new_id,
      reference="TESTPERS-%s" % new_id,
      )

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      )

  def test_invalidateIfPersonBalanceIsOk_REQUEST_disallowed(self):
    ticket = self.createRegularisationRequest()
    self.assertRaises(
      Unauthorized,
      ticket.RegularisationRequest_invalidateIfPersonBalanceIsOk,
      REQUEST={})

  @simulate('Entity_statBalance', '*args, **kwargs', 'return "0"')
  def test_invalidateIfPersonBalanceIsOk_matching_case(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(source_project_value=person)
    ticket.validate()
    ticket.suspend()
    ticket.RegularisationRequest_invalidateIfPersonBalanceIsOk()
    self.assertEquals(ticket.getSimulationState(), 'invalidated')

  @simulate('Entity_statBalance', '*args, **kwargs', 'return "0"')
  def test_invalidateIfPersonBalanceIsOk_not_suspended(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(source_project_value=person)
    ticket.validate()
    ticket.RegularisationRequest_invalidateIfPersonBalanceIsOk()
    self.assertEquals(ticket.getSimulationState(), 'validated')

  @simulate('Entity_statBalance', '*args, **kwargs', 'return "0"')
  def test_invalidateIfPersonBalanceIsOk_no_person(self):
    ticket = self.createRegularisationRequest()
    ticket.validate()
    ticket.suspend()
    ticket.RegularisationRequest_invalidateIfPersonBalanceIsOk()
    self.assertEquals(ticket.getSimulationState(), 'suspended')

  @simulate('Entity_statBalance', '*args, **kwargs', 'return "1"')
  def test_invalidateIfPersonBalanceIsOk_wrong_balance(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(source_project_value=person)
    ticket.validate()
    ticket.suspend()
    ticket.RegularisationRequest_invalidateIfPersonBalanceIsOk()
    self.assertEquals(ticket.getSimulationState(), 'suspended')

class TestSlapOSRegularisationRequest_checkToSendUniqEvent(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPerson(self):
    new_id = self.generateNewId()
    return self.portal.person_module.newContent(
      portal_type='Person',
      title="Person %s" % new_id,
      reference="TESTPERS-%s" % new_id,
      )

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      resource='foo/bar',
      )

  def test_checkToSendUniqEvent_no_event(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(
      source='organisation_module/slapos',
      destination_value=person,
      source_project_value=person)
    ticket.validate()
    ticket.suspend()
    before_date = DateTime()
    event = ticket.RegularisationRequest_checkToSendUniqEvent(
      'service_module/slapos_crm_spam', 'foo title', 'foo content', 'foo comment')
    after_date = DateTime()

    self.assertEquals(ticket.getSimulationState(), 'suspended')
    self.assertEquals(ticket.getResource(), 'service_module/slapos_crm_spam')

    self.assertEquals(event.getPortalType(), 'Mail Message')
    self.assertEquals(event.getSimulationState(), 'delivered')
    self.assertTrue(event.getStartDate() >= before_date)
    self.assertTrue(event.getStopDate() <= after_date)
    self.assertEquals(event.getTitle(), "foo title")
    self.assertEquals(event.getResource(), 'service_module/slapos_crm_spam')
    self.assertEquals(event.getFollowUp(), ticket.getRelativeUrl())
    self.assertEquals(event.getSource(), "organisation_module/slapos")
    self.assertEquals(event.getDestination(), person.getRelativeUrl())
    self.assertEquals(event.getTextContent(), 'foo content')

  def test_checkToSendUniqEvent_service_required(self):
    ticket = self.createRegularisationRequest()
    self.assertRaises(
      AssertionError,
      ticket.RegularisationRequest_checkToSendUniqEvent,
      ticket.getRelativeUrl(), '', '', ''
      )

  def test_checkToSendUniqEvent_call_twice_with_tic(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(
      source='organisation_module/slapos',
      destination_value=person,
      source_project_value=person)
    ticket.validate()
    ticket.suspend()
    event = ticket.RegularisationRequest_checkToSendUniqEvent(
      'service_module/slapos_crm_spam', 'foo title', 'foo content', 'foo comment')
    self.tic()

    event2 = ticket.RegularisationRequest_checkToSendUniqEvent(
      'service_module/slapos_crm_spam', 'foo2 title', 'foo2 content', 'foo2 comment')
    self.assertEquals(event.getTitle(), "foo title")
    self.assertEquals(event.getTextContent(), 'foo content')
    self.assertEquals(event.getRelativeUrl(), event2.getRelativeUrl())

  def test_checkToSendUniqEvent_manual_event(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(
      source='organisation_module/slapos',
      destination_value=person,
      source_project_value=person)
    ticket.validate()
    ticket.suspend()
    event = self.portal.event_module.newContent(
      portal_type="Mail Message",
      follow_up=ticket.getRelativeUrl(),
      resource='service_module/slapos_crm_spam',
      )
    self.tic()

    event2 = ticket.RegularisationRequest_checkToSendUniqEvent(
      'service_module/slapos_crm_spam', 'foo2 title', 'foo2 content', 'foo2 comment')

    self.assertEquals(ticket.getResource(), 'foo/bar')
    self.assertNotEquals(event.getTitle(), 'foo2 title')
    self.assertEquals(event.getTextContent(), None)
    self.assertEquals(event.getSimulationState(), 'draft')
    self.assertEquals(event.getRelativeUrl(), event2.getRelativeUrl())

  def test_checkToSendUniqEvent_not_suspended(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(
      source='organisation_module/slapos',
      destination_value=person,
      source_project_value=person)
    ticket.validate()

    event = ticket.RegularisationRequest_checkToSendUniqEvent(
      'service_module/slapos_crm_spam', 'foo2 title', 'foo2 content', 'foo2 comment')
    self.assertEquals(event, None)

  def test_checkToSendUniqEvent_event_not_reindexed(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(
      source='organisation_module/slapos',
      destination_value=person,
      source_project_value=person)
    ticket.validate()
    ticket.suspend()
    event = ticket.RegularisationRequest_checkToSendUniqEvent(
      'service_module/slapos_crm_spam', 'foo title', 'foo content', 'foo comment')
    transaction.commit()
    event2 = ticket.RegularisationRequest_checkToSendUniqEvent(
      'service_module/slapos_crm_spam', 'foo2 title', 'foo2 content', 'foo2 comment')
    self.assertNotEquals(event, event2)
    self.assertEquals(event2, None)

  def test_checkToSendUniqEvent_REQUEST_disallowed(self):
    ticket = self.createRegularisationRequest()
    self.assertRaises(
      Unauthorized,
      ticket.RegularisationRequest_checkToSendUniqEvent,
      '', '', '', '',
      REQUEST={})

class TestSlapOSRegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty(
                                                         testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPerson(self):
    new_id = self.generateNewId()
    return self.portal.person_module.newContent(
      portal_type='Person',
      title="Person %s" % new_id,
      reference="TESTPERS-%s" % new_id,
      )

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      resource='foo/bar',
      )

  def createOpenOrder(self):
    new_id = self.generateNewId()
    return self.portal.open_sale_order_module.newContent(
      portal_type='Open Sale Order',
      title="Test Open Order %s" % new_id,
      reference="TESTOPENORDER-%s" % new_id,
      )

  def createSaleInvoiceTransaction(self):
    new_id = self.generateNewId()
    return self.portal.accounting_module.newContent(
      portal_type='Sale Invoice Transaction',
      title="Test Sale Invoice %s" % new_id,
      reference="TESTSALEINVOICE-%s" % new_id,
      )

  def createPaymentTransaction(self):
    new_id = self.generateNewId()
    return self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Test Payment %s" % new_id,
      reference="TESTPAYMENT-%s" % new_id,
      )

  def test_cancelInvoiceIfPersonOpenOrderIsEmpty_REQUEST_disallowed(self):
    ticket = self.createRegularisationRequest()
    self.assertRaises(
      Unauthorized,
      ticket.RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty,
      REQUEST={})

  @simulate('SaleInvoiceTransaction_createReversalPayzenTransaction', 
            '*args, **kwargs',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by SaleInvoiceTransaction_createReversalPayzenTransaction")')
  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            'service_relative_url, title, text_content, comment, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by RegularisationRequest_checkToSendUniqEvent ' \
  '%s %s %s %s" % (service_relative_url, title, text_content, comment))\n' \
  'return "fooevent"')
  def test_cancelInvoiceIfPersonOpenOrderIsEmpty_invoice_to_cancel(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(
      destination_value=person,
      source_project_value=person)
    ticket.validate()
    ticket.suspend()
    order = self.createOpenOrder()
    order.edit(destination_decision_value=person)
    self.portal.portal_workflow._jumpToStateFor(order, 'validated')

    invoice = self.createSaleInvoiceTransaction()
    invoice.edit(
      payment_mode="payzen",
    )
    payment = self.createPaymentTransaction()
    payment.edit(
      payment_mode="payzen",
      causality_value=invoice,
      destination_section_value=person)
    self.portal.portal_workflow._jumpToStateFor(payment, 'started')

    self.tic()

    event, invoice_list = \
      ticket.RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty()

    expected_service = 'service_module/slapos_crm_invoice_cancellation'
    expected_title = 'Cancellation of your bill'
    expected_text= """Hello,

Thank you to have used our decentralized Cloud Computing service slapos.org.

We noticed that all your instances have been removed upon receiving your bill, so we conclude that the instances that you requested were not being used but probably ordered then forgotten.

To not to charge our first users a "non use" of our service, we have choosen to cancel your bill. That's mean: *You have nothing to pay us.*

We hope to see you using our services in the future.

Regards,
The slapos team
"""
    expected_comment = 'Cancelled payment.'

    self.assertEqual(
      'Visited by RegularisationRequest_checkToSendUniqEvent %s %s %s %s' % \
      (expected_service, expected_title, expected_text, expected_comment),
      ticket.workflow_history['edit_workflow'][-1]['comment'])

    self.assertEqual(
      'Visited by SaleInvoiceTransaction_createReversalPayzenTransaction',
      invoice.workflow_history['edit_workflow'][-1]['comment'])

    self.assertEqual(event, "fooevent")
    self.assertEqual(invoice_list, [invoice.getRelativeUrl()])

  @simulate('SaleInvoiceTransaction_createReversalPayzenTransaction', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_cancelInvoiceIfPersonOpenOrderIsEmpty_not_suspended_ticket(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(
      destination_value=person,
      source_project_value=person)
    ticket.validate()

    event, invoice_list = \
      ticket.RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty()

    self.assertEqual(event, None)
    self.assertEqual(invoice_list, [])

  @simulate('SaleInvoiceTransaction_createReversalPayzenTransaction', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_cancelInvoiceIfPersonOpenOrderIsEmpty_no_person_related(self):
    ticket = self.createRegularisationRequest()
    ticket.validate()
    ticket.suspend()

    event, invoice_list = \
      ticket.RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty()

    self.assertEqual(event, None)
    self.assertEqual(invoice_list, [])

  @simulate('SaleInvoiceTransaction_createReversalPayzenTransaction', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_cancelInvoiceIfPersonOpenOrderIsEmpty_no_open_order(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(
      destination_value=person,
      source_project_value=person)
    ticket.validate()
    ticket.suspend()

    event, invoice_list = \
      ticket.RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty()

    self.assertEqual(event, None)
    self.assertEqual(invoice_list, [])

  @simulate('SaleInvoiceTransaction_createReversalPayzenTransaction', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_cancelInvoiceIfPersonOpenOrderIsEmpty_with_open_order_line(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(
      destination_value=person,
      source_project_value=person)
    ticket.validate()
    ticket.suspend()
    order = self.createOpenOrder()
    order.edit(destination_decision_value=person)
    order.newContent(portal_type="Open Sale Order Line")
    self.portal.portal_workflow._jumpToStateFor(order, 'validated')

    self.tic()

    event, invoice_list = \
      ticket.RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty()

    self.assertEqual(event, None)
    self.assertEqual(invoice_list, [])

  @simulate('SaleInvoiceTransaction_createReversalPayzenTransaction', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            'service_relative_url, title, text_content, comment, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by RegularisationRequest_checkToSendUniqEvent ' \
  '%s %s %s %s" % (service_relative_url, title, text_content, comment))\n' \
  'return "fooevent"')
  def test_cancelInvoiceIfPersonOpenOrderIsEmpty_no_invoice(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    ticket.edit(
      destination_value=person,
      source_project_value=person)
    ticket.validate()
    ticket.suspend()
    order = self.createOpenOrder()
    order.edit(destination_decision_value=person)
    self.portal.portal_workflow._jumpToStateFor(order, 'validated')

    self.tic()

    event, invoice_list = \
      ticket.RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty()

    self.assertEqual(event, "fooevent")
    self.assertEqual(invoice_list, [])
