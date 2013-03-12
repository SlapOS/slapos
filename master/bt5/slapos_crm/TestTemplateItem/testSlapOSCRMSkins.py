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

class TestSlapOSRegularisationRequest_checkToTriggerNextEscalationStep(
                                                          testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      resource='foo/bar',
      )

  def test_checkToTriggerNextEscalationStep_service_required(self):
    ticket = self.createRegularisationRequest()
    self.assertRaises(
      AssertionError,
      ticket.RegularisationRequest_checkToTriggerNextEscalationStep,
      0, ticket.getRelativeUrl(), '', '', '', ''
      )

  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            'service_relative_url, title, text_content, comment, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by RegularisationRequest_checkToSendUniqEvent ' \
  '%s %s %s %s" % (service_relative_url, title, text_content, comment))\n' \
  'return "fooevent"')
  def test_checkToTriggerNextEscalationStep_matching_event(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_acknowledgement')
    ticket.validate()
    ticket.suspend()
    event = self.portal.event_module.newContent(
      portal_type="Mail Message",
      follow_up=ticket.getRelativeUrl(),
      resource='service_module/slapos_crm_acknowledgement',
      start_date=DateTime() - 8,
      )
    self.portal.portal_workflow._jumpToStateFor(event, 'delivered')
    self.tic()

    event2 = ticket.RegularisationRequest_checkToTriggerNextEscalationStep(
        7, 'service_module/slapos_crm_acknowledgement',
        'service_module/slapos_crm_spam', 
        'foo2 title', 'foo2 content', 'foo2 comment')

    self.assertEquals(event2, event.getRelativeUrl())
    self.assertEqual(
      'Visited by RegularisationRequest_checkToSendUniqEvent %s %s %s %s' % \
      ('service_module/slapos_crm_spam', 'foo2 title', 'foo2 content',
       'foo2 comment'),
      ticket.workflow_history['edit_workflow'][-1]['comment'])

  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_checkToTriggerNextEscalationStep_recent_event(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_acknowledgement')
    ticket.validate()
    ticket.suspend()
    event = self.portal.event_module.newContent(
      portal_type="Mail Message",
      follow_up=ticket.getRelativeUrl(),
      resource='service_module/slapos_crm_acknowledgement',
      start_date=DateTime() - 6,
      )
    self.portal.portal_workflow._jumpToStateFor(event, 'delivered')
    self.tic()

    event2 = ticket.RegularisationRequest_checkToTriggerNextEscalationStep(
        7, 'service_module/slapos_crm_acknowledgement',
        'service_module/slapos_crm_spam', 
        'foo2 title', 'foo2 content', 'foo2 comment')

    self.assertEquals(event2, None)

  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_checkToTriggerNextEscalationStep_other_ticket_event(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_acknowledgement')
    ticket.validate()
    ticket.suspend()
    event = self.portal.event_module.newContent(
      portal_type="Mail Message",
      resource='service_module/slapos_crm_acknowledgement',
      start_date=DateTime() - 2,
      )
    self.portal.portal_workflow._jumpToStateFor(event, 'delivered')
    self.tic()

    event2 = ticket.RegularisationRequest_checkToTriggerNextEscalationStep(
        1, 'service_module/slapos_crm_acknowledgement',
        'service_module/slapos_crm_spam', 
        'foo2 title', 'foo2 content', 'foo2 comment')

    self.assertEquals(event2, None)

  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_checkToTriggerNextEscalationStep_other_resource_event(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_acknowledgement')
    ticket.validate()
    ticket.suspend()
    event = self.portal.event_module.newContent(
      portal_type="Mail Message",
      follow_up=ticket.getRelativeUrl(),
      resource='service_module/slapos_crm_spam',
      start_date=DateTime() - 2,
      )
    self.portal.portal_workflow._jumpToStateFor(event, 'delivered')
    self.tic()

    event2 = ticket.RegularisationRequest_checkToTriggerNextEscalationStep(
        1, 'service_module/slapos_crm_acknowledgement',
        'service_module/slapos_crm_spam', 
        'foo2 title', 'foo2 content', 'foo2 comment')

    self.assertEquals(event2, None)

  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_checkToTriggerNextEscalationStep_no_current_event(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_acknowledgement')
    ticket.validate()
    ticket.suspend()
    self.tic()

    event2 = ticket.RegularisationRequest_checkToTriggerNextEscalationStep(
        1, 'service_module/slapos_crm_acknowledgement',
        'service_module/slapos_crm_spam', 
        'foo2 title', 'foo2 content', 'foo2 comment')

    self.assertEquals(event2, None)

  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_checkToTriggerNextEscalationStep_no_ticket_resource(self):
    ticket = self.createRegularisationRequest()
    ticket.validate()
    ticket.suspend()
    event = self.portal.event_module.newContent(
      portal_type="Mail Message",
      follow_up=ticket.getRelativeUrl(),
      resource='service_module/slapos_crm_acknowledgement',
      start_date=DateTime() - 2,
      )
    self.portal.portal_workflow._jumpToStateFor(event, 'delivered')
    self.tic()

    event2 = ticket.RegularisationRequest_checkToTriggerNextEscalationStep(
        1, 'service_module/slapos_crm_acknowledgement',
        'service_module/slapos_crm_spam', 
        'foo2 title', 'foo2 content', 'foo2 comment')

    self.assertEquals(event2, None)

  @simulate('RegularisationRequest_checkToSendUniqEvent', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_checkToTriggerNextEscalationStep_not_suspended(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_acknowledgement')
    ticket.validate()
    event = self.portal.event_module.newContent(
      portal_type="Mail Message",
      follow_up=ticket.getRelativeUrl(),
      resource='service_module/slapos_crm_acknowledgement',
      start_date=DateTime() - 2,
      )
    self.portal.portal_workflow._jumpToStateFor(event, 'delivered')
    self.tic()

    event2 = ticket.RegularisationRequest_checkToTriggerNextEscalationStep(
        1, 'service_module/slapos_crm_acknowledgement',
        'service_module/slapos_crm_spam', 
        'foo2 title', 'foo2 content', 'foo2 comment')

    self.assertEquals(event2, None)

  def test_checkToTriggerNextEscalationStep_REQUEST_disallowed(self):
    ticket = self.createRegularisationRequest()
    self.assertRaises(
      Unauthorized,
      ticket.RegularisationRequest_checkToTriggerNextEscalationStep,
      '', '', '', '', '', '',
      REQUEST={})

class TestSlapOSRegularisationRequest_triggerAcknowledgmentEscalation(
                                                          testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      resource='foo/bar',
      )

  def test_triggerAcknowledgmentEscalation_REQUEST_disallowed(self):
    ticket = self.createRegularisationRequest()
    self.assertRaises(
      Unauthorized,
      ticket.RegularisationRequest_triggerAcknowledgmentEscalation,
      REQUEST={})

  @simulate('RegularisationRequest_checkToTriggerNextEscalationStep', 
            'day, current, next, title, text_content, comment, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
  '%s %s %s %s %s %s" % (day, current, next, title, text_content, comment))')
  def test_checkToTriggerNextEscalationStep_matching_event(self):
    ticket = self.createRegularisationRequest()
    ticket.RegularisationRequest_triggerAcknowledgmentEscalation()
    self.assertEqual(
      'Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
      '%s %s %s %s %s %s' % \
      (38,
       'service_module/slapos_crm_acknowledgement',
       'service_module/slapos_crm_stop_reminder',
       'Reminder: invoice payment requested',
"""Dear user,

We would like to remind you the unpaid invoice you have on %s.
If no payment is done during the coming days, we will stop all your current instances to free some hardware resources.

Do not hesitate to visit the web forum (http://community.slapos.org/forum) in case of question.

Regards,
The slapos team
""" % self.portal.portal_preferences.getPreferredSlaposWebSiteUrl(),
       'Stopping reminder.'),
      ticket.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSRegularisationRequest_triggerStopReminderEscalation(
                                                          testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      resource='foo/bar',
      )

  def test_triggerStopReminderEscalation_REQUEST_disallowed(self):
    ticket = self.createRegularisationRequest()
    self.assertRaises(
      Unauthorized,
      ticket.RegularisationRequest_triggerStopReminderEscalation,
      REQUEST={})

  @simulate('RegularisationRequest_checkToTriggerNextEscalationStep', 
            'day, current, next, title, text_content, comment, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
  '%s %s %s %s %s %s" % (day, current, next, title, text_content, comment))')
  def test_checkToTriggerNextEscalationStep_matching_event(self):
    ticket = self.createRegularisationRequest()
    ticket.RegularisationRequest_triggerStopReminderEscalation()
    self.assertEqual(
      'Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
      '%s %s %s %s %s %s' % \
      (7,
       'service_module/slapos_crm_stop_reminder',
       'service_module/slapos_crm_stop_acknowledgement',
       'Acknowledgment: instances stopped',
"""Dear user,

Despite our last reminder, you still have an unpaid invoice on %s.
We will now stop all your current instances to free some hardware resources.

Do not hesitate to visit the web forum (http://community.slapos.org/forum) in case of question.

Regards,
The slapos team
""" % self.portal.portal_preferences.getPreferredSlaposWebSiteUrl(),
       'Stopping acknowledgment.'),
      ticket.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSRegularisationRequest_triggerStopAcknowledgmentEscalation(
                                                          testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      resource='foo/bar',
      )

  def test_triggerStopAcknowledgmentEscalation_REQUEST_disallowed(self):
    ticket = self.createRegularisationRequest()
    self.assertRaises(
      Unauthorized,
      ticket.RegularisationRequest_triggerStopAcknowledgmentEscalation,
      REQUEST={})

  @simulate('RegularisationRequest_checkToTriggerNextEscalationStep', 
            'day, current, next, title, text_content, comment, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
  '%s %s %s %s %s %s" % (day, current, next, title, text_content, comment))')
  def test_checkToTriggerNextEscalationStep_matching_event(self):
    ticket = self.createRegularisationRequest()
    ticket.RegularisationRequest_triggerStopAcknowledgmentEscalation()
    self.assertEqual(
      'Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
      '%s %s %s %s %s %s' % \
      (13,
       'service_module/slapos_crm_stop_acknowledgement',
       'service_module/slapos_crm_delete_reminder',
       'Last reminder: invoice payment requested',
"""Dear user,

We would like to remind you the unpaid invoice you have on %s.
If no payment is done during the coming days, we will delete all your instances.

Do not hesitate to visit the web forum (http://community.slapos.org/forum) in case of question.

Regards,
The slapos team
""" % self.portal.portal_preferences.getPreferredSlaposWebSiteUrl(),
       'Deleting reminder.'),
      ticket.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSRegularisationRequest_triggerDeleteReminderEscalation(
                                                          testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      resource='foo/bar',
      )

  def test_triggerDeleteReminderEscalation_REQUEST_disallowed(self):
    ticket = self.createRegularisationRequest()
    self.assertRaises(
      Unauthorized,
      ticket.RegularisationRequest_triggerDeleteReminderEscalation,
      REQUEST={})

  @simulate('RegularisationRequest_checkToTriggerNextEscalationStep', 
            'day, current, next, title, text_content, comment, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
  '%s %s %s %s %s %s" % (day, current, next, title, text_content, comment))')
  def test_checkToTriggerNextEscalationStep_matching_event(self):
    ticket = self.createRegularisationRequest()
    ticket.RegularisationRequest_triggerDeleteReminderEscalation()
    self.assertEqual(
      'Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
      '%s %s %s %s %s %s' % \
      (2,
       'service_module/slapos_crm_delete_reminder',
       'service_module/slapos_crm_delete_acknowledgement',
       'Acknowledgment: instances deleted',
"""Dear user,

Despite our last reminder, you still have an unpaid invoice on %s.
We will now delete all your instances.

Do not hesitate to visit the web forum (http://community.slapos.org/forum) in case of question.

Regards,
The slapos team
""" % self.portal.portal_preferences.getPreferredSlaposWebSiteUrl(),
       'Deleting acknowledgment.'),
      ticket.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSRegularisationRequest_stopHostingSubscriptionList(
                                                          testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      resource='foo/bar',
      )

  def createPerson(self):
    new_id = self.generateNewId()
    person = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person.edit(
      title="Person %s" % new_id,
      reference="TESTPERS-%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
      )
    person.manage_delObjects(
      [x.getId() for x in person.contentValues(portal_type="Assignment")]
    )
    return person

  def createHostingSubscription(self):
    new_id = self.generateNewId()
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.edit(
      reference="TESTHS-%s" % new_id,
    )
    hosting_subscription.validate()
    self.portal.portal_workflow._jumpToStateFor(
        hosting_subscription, 'start_requested')
    return hosting_subscription

  def test_stopHostingSubscriptionList_REQUEST_disallowed(self):
    ticket = self.createRegularisationRequest()
    self.assertRaises(
      Unauthorized,
      ticket.RegularisationRequest_stopHostingSubscriptionList,
      'footag',
      REQUEST={})

  @simulate('HostingSubscription_stopFromRegularisationRequest', 
            'person, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by HostingSubscription_stopFromRegularisationRequest ' \
  '%s" % (person))')
  def test_stopHostingSubscriptionList_matching_subscription(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    hosting_subscription = self.createHostingSubscription()

    ticket.edit(
      source_project_value=person,
      resource='service_module/slapos_crm_stop_acknowledgement',
    )
    ticket.validate()
    ticket.suspend()
    hosting_subscription.edit(
      destination_section=person.getRelativeUrl(),
    )
    self.tic()

    result = ticket.\
        RegularisationRequest_stopHostingSubscriptionList('footag')
    self.assertTrue(result)

    self.tic()
    self.assertEqual(
      'Visited by HostingSubscription_stopFromRegularisationRequest ' \
      '%s' % person.getRelativeUrl(),
      hosting_subscription.workflow_history['edit_workflow'][-1]['comment'])

  @simulate('HostingSubscription_stopFromRegularisationRequest', 
            'person, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by HostingSubscription_stopFromRegularisationRequest ' \
  '%s" % (person))')
  def test_stopHostingSubscriptionList_matching_subscription_2(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    hosting_subscription = self.createHostingSubscription()

    ticket.edit(
      source_project_value=person,
      resource='service_module/slapos_crm_delete_reminder',
    )
    ticket.validate()
    ticket.suspend()
    hosting_subscription.edit(
      destination_section=person.getRelativeUrl(),
    )
    self.tic()

    result = ticket.\
        RegularisationRequest_stopHostingSubscriptionList('footag')
    self.assertTrue(result)

    self.tic()
    self.assertEqual(
      'Visited by HostingSubscription_stopFromRegularisationRequest ' \
      '%s' % person.getRelativeUrl(),
      hosting_subscription.workflow_history['edit_workflow'][-1]['comment'])

  @simulate('HostingSubscription_stopFromRegularisationRequest', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_stopHostingSubscriptionList_other_subscription(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    hosting_subscription = self.createHostingSubscription()

    ticket.edit(
      source_project_value=person,
      resource='service_module/slapos_crm_stop_acknowledgement',
    )
    ticket.validate()
    ticket.suspend()

    self.tic()

    result = ticket.\
        RegularisationRequest_stopHostingSubscriptionList('footag')
    self.assertTrue(result)

    self.tic()

  @simulate('HostingSubscription_stopFromRegularisationRequest', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_stopHostingSubscriptionList_no_person(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()

    ticket.edit(
      resource='service_module/slapos_crm_stop_acknowledgement',
    )
    ticket.validate()
    ticket.suspend()

    self.tic()

    result = ticket.\
        RegularisationRequest_stopHostingSubscriptionList('footag')
    self.assertFalse(result)

    self.tic()

  @simulate('HostingSubscription_stopFromRegularisationRequest', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_stopHostingSubscriptionList_not_suspended(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    hosting_subscription = self.createHostingSubscription()

    ticket.edit(
      source_project_value=person,
      resource='service_module/slapos_crm_stop_acknowledgement',
    )
    ticket.validate()

    self.tic()

    result = ticket.\
        RegularisationRequest_stopHostingSubscriptionList('footag')
    self.assertFalse(result)

    self.tic()

  @simulate('HostingSubscription_stopFromRegularisationRequest', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_stopHostingSubscriptionList_other_resource(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    hosting_subscription = self.createHostingSubscription()

    ticket.edit(
      source_project_value=person,
      resource='service_module/slapos_crm_acknowledgement',
    )
    ticket.validate()
    ticket.suspend()

    self.tic()

    result = ticket.\
        RegularisationRequest_stopHostingSubscriptionList('footag')
    self.assertFalse(result)

    self.tic()

class TestSlapOSHostingSubscription_stopFromRegularisationRequest(
                                                          testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPerson(self):
    new_id = self.generateNewId()
    person = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person.edit(
      title="Person %s" % new_id,
      reference="TESTPERS-%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
      )
    person.manage_delObjects(
      [x.getId() for x in person.contentValues(portal_type="Assignment")]
    )
    return person

  def createHostingSubscription(self):
    new_id = self.generateNewId()
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.edit(
      reference="TESTHS-%s" % new_id,
    )
    hosting_subscription.validate()
    self.portal.portal_workflow._jumpToStateFor(
        hosting_subscription, 'start_requested')
    return hosting_subscription

  def test_stopFromRegularisationRequest_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.HostingSubscription_stopFromRegularisationRequest,
      '',
      REQUEST={})

  def test_stopFromRegularisationRequest_matching_subscription(self):
    person = self.createPerson()
    hosting_subscription = self.createHostingSubscription()
    hosting_subscription.edit(
      destination_section=person.getRelativeUrl(),
    )
    self.tic()

    software_release = hosting_subscription.getUrlString()
    software_title = hosting_subscription.getTitle()
    software_type = hosting_subscription.getSourceReference()
    instance_xml = hosting_subscription.getTextContent()
    sla_xml = hosting_subscription.getSlaXml()
    shared = hosting_subscription.isRootSlave()
    self.assertEquals(hosting_subscription.getSlapState(), "start_requested")

    result = hosting_subscription.\
        HostingSubscription_stopFromRegularisationRequest(person.getRelativeUrl())

    self.assertEquals(result, True)
    self.assertEquals(hosting_subscription.getUrlString(), software_release)
    self.assertEquals(hosting_subscription.getTitle(), software_title)
    self.assertEquals(hosting_subscription.getSourceReference(), software_type)
    self.assertEquals(hosting_subscription.getTextContent(), instance_xml)
    self.assertEquals(hosting_subscription.getSlaXml(), sla_xml)
    self.assertEquals(hosting_subscription.isRootSlave(), shared)
    self.assertEquals(hosting_subscription.getSlapState(), "stop_requested")
    
  def test_stopFromRegularisationRequest_stopped_subscription(self):
    person = self.createPerson()
    hosting_subscription = self.createHostingSubscription()
    hosting_subscription.edit(
      destination_section=person.getRelativeUrl(),
    )
    self.portal.portal_workflow._jumpToStateFor(
        hosting_subscription, 'stop_requested')

    result = hosting_subscription.\
        HostingSubscription_stopFromRegularisationRequest(person.getRelativeUrl())

    self.assertEquals(result, False)

  def test_stopFromRegularisationRequest_non_matching_person(self):
    hosting_subscription = self.createHostingSubscription()
    self.assertRaises(
      AssertionError,
      hosting_subscription.HostingSubscription_stopFromRegularisationRequest,
      'foobar')

class TestSlapOSHostingSubscription_deleteFromRegularisationRequest(
                                                          testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPerson(self):
    new_id = self.generateNewId()
    person = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person.edit(
      title="Person %s" % new_id,
      reference="TESTPERS-%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
      )
    person.manage_delObjects(
      [x.getId() for x in person.contentValues(portal_type="Assignment")]
    )
    return person

  def createHostingSubscription(self):
    new_id = self.generateNewId()
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.edit(
      reference="TESTHS-%s" % new_id,
    )
    hosting_subscription.validate()
    self.portal.portal_workflow._jumpToStateFor(
        hosting_subscription, 'start_requested')
    return hosting_subscription

  def test_deleteFromRegularisationRequest_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.HostingSubscription_deleteFromRegularisationRequest,
      '',
      REQUEST={})

  def test_deleteFromRegularisationRequest_started_subscription(self):
    person = self.createPerson()
    hosting_subscription = self.createHostingSubscription()
    hosting_subscription.edit(
      destination_section=person.getRelativeUrl(),
    )
    self.tic()

    software_release = hosting_subscription.getUrlString()
    software_title = hosting_subscription.getTitle()
    software_type = hosting_subscription.getSourceReference()
    instance_xml = hosting_subscription.getTextContent()
    sla_xml = hosting_subscription.getSlaXml()
    shared = hosting_subscription.isRootSlave()
    self.assertEquals(hosting_subscription.getSlapState(), "start_requested")

    result = hosting_subscription.\
        HostingSubscription_deleteFromRegularisationRequest(person.getRelativeUrl())

    self.assertEquals(result, True)
    self.assertEquals(hosting_subscription.getUrlString(), software_release)
    self.assertEquals(hosting_subscription.getTitle(), software_title)
    self.assertEquals(hosting_subscription.getSourceReference(), software_type)
    self.assertEquals(hosting_subscription.getTextContent(), instance_xml)
    self.assertEquals(hosting_subscription.getSlaXml(), sla_xml)
    self.assertEquals(hosting_subscription.isRootSlave(), shared)
    self.assertEquals(hosting_subscription.getSlapState(), "destroy_requested")

  def test_deleteFromRegularisationRequest_stopped_subscription(self):
    person = self.createPerson()
    hosting_subscription = self.createHostingSubscription()
    hosting_subscription.edit(
      destination_section=person.getRelativeUrl(),
    )
    self.portal.portal_workflow._jumpToStateFor(
        hosting_subscription, 'stop_requested')
    self.tic()

    software_release = hosting_subscription.getUrlString()
    software_title = hosting_subscription.getTitle()
    software_type = hosting_subscription.getSourceReference()
    instance_xml = hosting_subscription.getTextContent()
    sla_xml = hosting_subscription.getSlaXml()
    shared = hosting_subscription.isRootSlave()
    self.assertEquals(hosting_subscription.getSlapState(), "stop_requested")

    result = hosting_subscription.\
        HostingSubscription_deleteFromRegularisationRequest(person.getRelativeUrl())

    self.assertEquals(result, True)
    self.assertEquals(hosting_subscription.getUrlString(), software_release)
    self.assertEquals(hosting_subscription.getTitle(), software_title)
    self.assertEquals(hosting_subscription.getSourceReference(), software_type)
    self.assertEquals(hosting_subscription.getTextContent(), instance_xml)
    self.assertEquals(hosting_subscription.getSlaXml(), sla_xml)
    self.assertEquals(hosting_subscription.isRootSlave(), shared)
    self.assertEquals(hosting_subscription.getSlapState(), "destroy_requested")
    
  def test_deleteFromRegularisationRequest_destroyed_subscription(self):
    person = self.createPerson()
    hosting_subscription = self.createHostingSubscription()
    hosting_subscription.edit(
      destination_section=person.getRelativeUrl(),
    )
    self.portal.portal_workflow._jumpToStateFor(
        hosting_subscription, 'destroy_requested')

    result = hosting_subscription.\
        HostingSubscription_deleteFromRegularisationRequest(person.getRelativeUrl())

    self.assertEquals(result, False)

  def test_deleteFromRegularisationRequest_non_matching_person(self):
    hosting_subscription = self.createHostingSubscription()
    self.assertRaises(
      AssertionError,
      hosting_subscription.HostingSubscription_deleteFromRegularisationRequest,
      'foobar')

class TestSlapOSRegularisationRequest_deleteHostingSubscriptionList(
                                                          testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      resource='foo/bar',
      )

  def createPerson(self):
    new_id = self.generateNewId()
    person = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person.edit(
      title="Person %s" % new_id,
      reference="TESTPERS-%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
      )
    person.manage_delObjects(
      [x.getId() for x in person.contentValues(portal_type="Assignment")]
    )
    return person

  def createHostingSubscription(self):
    new_id = self.generateNewId()
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.edit(
      reference="TESTHS-%s" % new_id,
    )
    hosting_subscription.validate()
    self.portal.portal_workflow._jumpToStateFor(
        hosting_subscription, 'start_requested')
    return hosting_subscription

  def test_deleteHostingSubscriptionList_REQUEST_disallowed(self):
    ticket = self.createRegularisationRequest()
    self.assertRaises(
      Unauthorized,
      ticket.RegularisationRequest_deleteHostingSubscriptionList,
      'footag',
      REQUEST={})

  @simulate('HostingSubscription_deleteFromRegularisationRequest', 
            'person, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by HostingSubscription_deleteFromRegularisationRequest ' \
  '%s" % (person))')
  def test_deleteHostingSubscriptionList_matching_subscription(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    hosting_subscription = self.createHostingSubscription()

    ticket.edit(
      source_project_value=person,
      resource='service_module/slapos_crm_delete_acknowledgement',
    )
    ticket.validate()
    ticket.suspend()
    hosting_subscription.edit(
      destination_section=person.getRelativeUrl(),
    )
    self.tic()

    result = ticket.\
        RegularisationRequest_deleteHostingSubscriptionList('footag')
    self.assertTrue(result)

    self.tic()
    self.assertEqual(
      'Visited by HostingSubscription_deleteFromRegularisationRequest ' \
      '%s' % person.getRelativeUrl(),
      hosting_subscription.workflow_history['edit_workflow'][-1]['comment'])

  @simulate('HostingSubscription_deleteFromRegularisationRequest', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_deleteHostingSubscriptionList_other_subscription(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    hosting_subscription = self.createHostingSubscription()

    ticket.edit(
      source_project_value=person,
      resource='service_module/slapos_crm_delete_acknowledgement',
    )
    ticket.validate()
    ticket.suspend()

    self.tic()

    result = ticket.\
        RegularisationRequest_deleteHostingSubscriptionList('footag')
    self.assertTrue(result)

    self.tic()

  @simulate('HostingSubscription_deleteFromRegularisationRequest', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_deleteHostingSubscriptionList_no_person(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()

    ticket.edit(
      resource='service_module/slapos_crm_delete_acknowledgement',
    )
    ticket.validate()
    ticket.suspend()

    self.tic()

    result = ticket.\
        RegularisationRequest_deleteHostingSubscriptionList('footag')
    self.assertFalse(result)

    self.tic()

  @simulate('HostingSubscription_deleteFromRegularisationRequest', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_deleteHostingSubscriptionList_not_suspended(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    hosting_subscription = self.createHostingSubscription()

    ticket.edit(
      source_project_value=person,
      resource='service_module/slapos_crm_delete_acknowledgement',
    )
    ticket.validate()

    self.tic()

    result = ticket.\
        RegularisationRequest_deleteHostingSubscriptionList('footag')
    self.assertFalse(result)

    self.tic()

  @simulate('HostingSubscription_deleteFromRegularisationRequest', 
            '*args, **kwargs',
            'raise NotImplementedError, "Should not have been called"')
  def test_deleteHostingSubscriptionList_other_resource(self):
    person = self.createPerson()
    ticket = self.createRegularisationRequest()
    hosting_subscription = self.createHostingSubscription()

    ticket.edit(
      source_project_value=person,
      resource='service_module/slapos_crm_delete_reminder',
    )
    ticket.validate()
    ticket.suspend()

    self.tic()

    result = ticket.\
        RegularisationRequest_deleteHostingSubscriptionList('footag')
    self.assertFalse(result)

    self.tic()
