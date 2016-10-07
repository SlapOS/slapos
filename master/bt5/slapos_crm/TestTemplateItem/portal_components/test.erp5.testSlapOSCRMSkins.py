# Copyright (c) 2013 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from zExceptions import Unauthorized
from DateTime import DateTime
from functools import wraps
from Products.ERP5Type.tests.utils import createZODBPythonScript
import difflib
import json

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

class TestSlapOSFolder_getOpenTicketList(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def afterSetUp(self):
    super(TestSlapOSFolder_getOpenTicketList, self).afterSetUp()
    self.new_id = self.generateNewId()
    self.person = self.portal.person_module.newContent(
      portal_type='Person',
      title="Person %s" % self.new_id,
      reference="TESTPERS-%s" % self.new_id,
      default_email_text="live_test_%s@example.org" % self.new_id,
      )
  
  def _test_ticket(self, ticket, expected_amount):
    module = ticket.getParentValue()
    open_ticket_list = module.Folder_getOpenTicketList(title=ticket.getTitle())
    
    self.assertEquals(len(open_ticket_list), expected_amount-1)
    
    ticket.submit()
    ticket.immediateReindexObject()
    open_ticket_list = module.Folder_getOpenTicketList(title=ticket.getTitle())
    self.assertEquals(len(open_ticket_list), expected_amount)
    self.assertEquals(open_ticket_list[0].getUid(), ticket.getUid())
    
    
    ticket.validate()
    ticket.immediateReindexObject()
    open_ticket_list = module.Folder_getOpenTicketList(title=ticket.getTitle())
    self.assertEquals(len(open_ticket_list), expected_amount)
    self.assertEquals(open_ticket_list[0].getUid(), ticket.getUid())
    
    ticket.suspend()
    ticket.immediateReindexObject()
    open_ticket_list = module.Folder_getOpenTicketList(title=ticket.getTitle())
    self.assertEquals(len(open_ticket_list), expected_amount)
    self.assertEquals(open_ticket_list[0].getUid(), ticket.getUid())
    
    ticket.invalidate()
    ticket.immediateReindexObject()
    open_ticket_list = module.Folder_getOpenTicketList(title=ticket.getTitle())
    self.assertEquals(len(open_ticket_list), expected_amount)
    self.assertEquals(open_ticket_list[0].getUid(), ticket.getUid())
  
  
  def _test_upgrade_decision(self, ticket, expected_amount):
    module = ticket.getParentValue()
    open_ticket_list = module.Folder_getOpenTicketList(title=ticket.getTitle())
    
    self.assertEquals(len(open_ticket_list), expected_amount-1)
    
    ticket.plan()
    ticket.immediateReindexObject()
    open_ticket_list = module.Folder_getOpenTicketList(title=ticket.getTitle())
    self.assertEquals(len(open_ticket_list), expected_amount-1)

    ticket.confirm()
    ticket.immediateReindexObject()
    open_ticket_list = module.Folder_getOpenTicketList(title=ticket.getTitle())
    self.assertEquals(len(open_ticket_list), expected_amount)
    self.assertEquals(open_ticket_list[0].getUid(), ticket.getUid())
    
    ticket.start()
    ticket.immediateReindexObject()
    open_ticket_list = module.Folder_getOpenTicketList(title=ticket.getTitle())
    self.assertEquals(len(open_ticket_list), expected_amount-1)


    ticket.stop()
    ticket.immediateReindexObject()
    open_ticket_list = module.Folder_getOpenTicketList(title=ticket.getTitle())
    self.assertEquals(len(open_ticket_list), expected_amount-1)
    
    ticket.deliver()
    ticket.immediateReindexObject()
    open_ticket_list = module.Folder_getOpenTicketList(title=ticket.getTitle())
    self.assertEquals(len(open_ticket_list), expected_amount)
    self.assertEquals(open_ticket_list[0].getUid(), ticket.getUid())
  
  
  def test_support_request(self):
    def newSupportRequest():
      sr = self.portal.support_request_module.newContent(\
                        title="Test Support Request %s" % self.new_id)
      
      sr.immediateReindexObject()
      return sr
    
    ticket = newSupportRequest()
    self._test_ticket(ticket, 1)

    ticket = newSupportRequest()
    self._test_ticket(ticket, 2)

  def test_regularisation_request(self):
    def newRegularisationRequest():
      ticket = self.portal.regularisation_request_module.newContent(
        portal_type='Regularisation Request',
        title="Test Reg. Req.%s" % self.new_id,
        reference="TESTREGREQ-%s" % self.new_id
        )
      
      ticket.immediateReindexObject()
      return ticket
    
    ticket = newRegularisationRequest()
    self._test_ticket(ticket, 1)

    ticket = newRegularisationRequest()
    self._test_ticket(ticket, 2)

  def test_upgrade_decision(self):
    def newUpgradeDecision():
      ticket = self.portal.upgrade_decision_module.newContent(
        portal_type='Upgrade Decision',
        title="Upgrade Decision Test %s" % self.new_id,
        reference="TESTUD-%s" % self.new_id
        )
      
      ticket.immediateReindexObject()
      return ticket
    
    ticket = newUpgradeDecision()
    self._test_upgrade_decision(ticket, 1)

    ticket = newUpgradeDecision()
    self._test_upgrade_decision(ticket, 2)

class TestSlapOSTicketEvent(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def afterSetUp(self):
    super(TestSlapOSTicketEvent, self).afterSetUp()
      
  def _test_event(self, ticket):
    
    def newEvent(ticket):
      event = self.portal.event_module.newContent(
        title="Test Event %s" % self.new_id,
        portal_type="Web Message",
        follow_up_value=ticket)
      
      event.immediateReindexObject()
      return event
      
    last_event = ticket.Ticket_getLatestEvent()
    
    self.assertEquals(last_event, None)
    
    event = newEvent(ticket)
    last_event = ticket.Ticket_getLatestEvent()
    
    self.assertEquals(last_event, None)
    
    event.plan()
    event.immediateReindexObject()
    self.assertEquals(last_event, None)

    event.confirm()
    event.immediateReindexObject()
    last_event = ticket.Ticket_getLatestEvent()
    self.assertEquals(last_event, event)

    event.start()
    event.immediateReindexObject()
    last_event = ticket.Ticket_getLatestEvent()
    self.assertEquals(last_event, event)

    event.stop()
    event.immediateReindexObject()
    last_event = ticket.Ticket_getLatestEvent()
    self.assertEquals(last_event, event)

    event.deliver()
    event.immediateReindexObject()
    last_event = ticket.Ticket_getLatestEvent()
    self.assertEquals(last_event, event)
  

    # Now we test unwanted cases (deleted and cancelled)
    another_event = newEvent(ticket)
    last_event = ticket.Ticket_getLatestEvent()
    
    self.assertEquals(last_event, event)
    
    another_event.cancel()
    event.immediateReindexObject()
    last_event = ticket.Ticket_getLatestEvent()
    self.assertEquals(last_event, event) 

    another_event = newEvent(ticket)
    last_event = ticket.Ticket_getLatestEvent()
    
    self.assertEquals(last_event, event)
    
    another_event.delete()
    event.immediateReindexObject()
    last_event = ticket.Ticket_getLatestEvent()
    self.assertEquals(last_event, event)

class TestSlapOSEvent_getRSSTextContent(TestSlapOSTicketEvent):

  def afterSetUp(self):
    super(TestSlapOSEvent_getRSSTextContent, self).afterSetUp()
    self.new_id = self.generateNewId()
    self.person = self.portal.person_module.newContent(
      portal_type='Person',
      title="Person %s" % self.new_id,
      reference="TESTPERS-%s" % self.new_id,
      default_email_text="live_test_%s@example.org" % self.new_id,
      )

  def beforeTearDown(self):
    transaction.abort()

  def test_Event_getRSSTextContent(self):
    source = self.person

    destination = self.portal.person_module.newContent(
      portal_type='Person',
      title="Person Destination %s" % self.new_id,
      reference="TESTPERSD-%s" % self.new_id,
      default_email_text="live_test_%s@example.org" % self.new_id,
      )

    destination_2 = self.portal.person_module.newContent(
      portal_type='Person',
      title="Person Destination 2 %s" % self.new_id,
      reference="TESTPERSD2-%s" % self.new_id,
      default_email_text="live_test_%s@example.org" % self.new_id,
      )

    event = self.portal.event_module.newContent(
        title="Test Event %s" % self.new_id,
        portal_type="Web Message",
        text_content="Test Event %s" % self.new_id)


    text_content = event.Event_getRSSTextContent()
    
    self.assertTrue(event.getTextContent() in text_content)
    self.assertTrue("Sender: " in text_content, "Sender: not in %s" % text_content)
    self.assertTrue("Recipient: " in text_content, "Recipient: not in %s" % text_content)
    self.assertTrue("Content:" in text_content, "Content: not in %s" % text_content)

    event.setSourceValue(source)
    text_content = event.Event_getRSSTextContent()
    self.assertTrue("Sender: %s" % source.getTitle() in text_content, 
      "Sender: %s not in %s" % (source.getTitle(), text_content))
    
    event.setDestinationValue(destination)
    text_content = event.Event_getRSSTextContent()
    self.assertTrue("Recipient: %s" % destination.getTitle() in text_content, 
      "Recipient: %s not in %s" % (destination.getTitle(), text_content))

    event.setDestinationValue(destination_2)
    text_content = event.Event_getRSSTextContent()
    self.assertTrue("Recipient: %s" % destination_2.getTitle() in text_content, 
      "Recipient: %s not in %s" % (destination.getTitle(), text_content))
    
    event.setDestinationValueList([destination, destination_2])
    text_content = event.Event_getRSSTextContent()
    self.assertTrue(
      "Recipient: %s,%s" % (destination.getTitle(), 
                            destination_2.getTitle()) in text_content, 
      "Recipient: %s,%s not in %s" % (destination.getTitle(), 
                                      destination_2.getTitle(), 
                                      text_content)
      )

  def test_support_request(self):
    ticket = self.portal.support_request_module.newContent(\
                        title="Test Support Request %s" % self.new_id,
                        resource="service_module/slapos_crm_monitoring",
                        destination_decision_value=self.person)
      
    ticket.immediateReindexObject()
    self._test_event(ticket)


class TestSlapOSTicket_getLatestEvent(TestSlapOSTicketEvent):

  def beforeTearDown(self):
    transaction.abort()

  def afterSetUp(self):
    super(TestSlapOSTicket_getLatestEvent, self).afterSetUp()
    self.new_id = self.generateNewId()
    self.person = self.portal.person_module.newContent(
      portal_type='Person',
      title="Person %s" % self.new_id,
      reference="TESTPERS-%s" % self.new_id,
      default_email_text="live_test_%s@example.org" % self.new_id,
      )
      
  def test_support_request(self):
    ticket = self.portal.support_request_module.newContent(\
                        title="Test Support Request %s" % self.new_id,
                        resource="service_module/slapos_crm_monitoring",
                        destination_decision_value=self.person)
      
    ticket.immediateReindexObject()
    self._test_event(ticket)


  def test_regularisation_request(self):
    ticket = self.portal.regularisation_request_module.newContent(
        portal_type='Regularisation Request',
        title="Test Reg. Req.%s" % self.new_id,
        reference="TESTREGREQ-%s" % self.new_id
        )
      
    ticket.immediateReindexObject()
    self._test_event(ticket)

  def test_upgrade_decision(self):
    ticket = self.portal.upgrade_decision_module.newContent(
        portal_type='Upgrade Decision',
        title="Upgrade Decision Test %s" % self.new_id,
        reference="TESTUD-%s" % self.new_id
        )
      
    ticket.immediateReindexObject()
    self._test_event(ticket)


class TestSlapOSPerson_checkToCreateRegularisationRequest(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPerson(self):
    new_id = self.generateNewId()
    return self.portal.person_module.newContent(
      portal_type='Person',
      title="Person %s" % new_id,
      reference="TESTPERS-%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
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

  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "slapos-crm.create.regularisation.request"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["test_addRegularisationRequest_notification_message"])')
  @simulate('Entity_statBalance', '*args, **kwargs', 'return "1"')
  def test_addRegularisationRequest_notification_message(self):
    for preference in \
      self.portal.portal_catalog(portal_type="System Preference"):
      preference = preference.getObject()
      if preference.getPreferenceState() == 'global':
        preference.setPreferredSlaposWebSiteUrl('http://foobar.org/')

    person = self.createPerson()
    new_id = self.generateNewId()
    notification_message = self.portal.notification_message_module.newContent(
      portal_type="Notification Message",
      title='Test NM title %s' % new_id,
      text_content='Test NM content<br/>%s<br/>' % new_id,
      content_type='text/html',
      )
    self.portal.REQUEST\
        ['test_addRegularisationRequest_notification_message'] = \
        notification_message.getRelativeUrl()

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
    self.assertEquals(event.getTitle(),
           'Test NM title %s' % new_id)
    self.assertEquals(event.getDestination(),
                      person.getRelativeUrl())
    self.assertEquals(event.getSource(),
                      ticket.getSource())
    expected_text_content = 'Test NM content\n%s\n' % new_id
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
    ticket = person.Person_checkToCreateRegularisationRequest()[0]
    ticket.invalidate()
    transaction.commit()
    self.tic()
    ticket2, event2 = person.Person_checkToCreateRegularisationRequest()
    self.assertNotEquals(ticket2.getRelativeUrl(), ticket.getRelativeUrl())
    self.assertNotEquals(event2, None)

  def test_addRegularisationRequest_REQUEST_disallowed(self):
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
      default_email_text="live_test_%s@example.org" % new_id,
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
      default_email_text="live_test_%s@example.org" % new_id,
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

  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "slapos-crm.acknowledgment.escalation"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["test_checkToTriggerNextEscalationStep_notification_message"])')
  @simulate('RegularisationRequest_checkToTriggerNextEscalationStep',
            'day, current, next, title, text_content, comment, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
  '%s %s %s %s %s %s" % (day, current, next, title, text_content, comment))')
  def test_checkToTriggerNextEscalationStep_notification_message(self):
    ticket = self.createRegularisationRequest()
    new_id = self.generateNewId()
    notification_message = self.portal.notification_message_module.newContent(
      portal_type="Notification Message",
      title='Test NM title %s' % new_id,
      text_content='Test NM content<br/>%s<br/>' % new_id,
      content_type='text/html',
      )
    self.portal.REQUEST\
        ['test_checkToTriggerNextEscalationStep_notification_message'] = \
        notification_message.getRelativeUrl()
    ticket.RegularisationRequest_triggerAcknowledgmentEscalation()
    self.assertEqual(
      'Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
      '%s %s %s %s %s %s' % \
      (38,
       'service_module/slapos_crm_acknowledgement',
       'service_module/slapos_crm_stop_reminder',
       'Test NM title %s' % new_id,
       'Test NM content\n%s\n' % new_id,
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

  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "slapos-crm.stop.reminder.escalation"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["test_checkToTriggerNextEscalationStep_notification_message"])')
  @simulate('RegularisationRequest_checkToTriggerNextEscalationStep',
            'day, current, next, title, text_content, comment, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
  '%s %s %s %s %s %s" % (day, current, next, title, text_content, comment))')
  def test_checkToTriggerNextEscalationStep_notification_message(self):
    ticket = self.createRegularisationRequest()
    new_id = self.generateNewId()
    notification_message = self.portal.notification_message_module.newContent(
      portal_type="Notification Message",
      title='Test NM title %s' % new_id,
      text_content='Test NM content<br/>%s<br/>' % new_id,
      content_type='text/html',
      )
    self.portal.REQUEST\
        ['test_checkToTriggerNextEscalationStep_notification_message'] = \
        notification_message.getRelativeUrl()
    ticket.RegularisationRequest_triggerStopReminderEscalation()
    self.assertEqual(
      'Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
      '%s %s %s %s %s %s' % \
      (7,
       'service_module/slapos_crm_stop_reminder',
       'service_module/slapos_crm_stop_acknowledgement',
       'Test NM title %s' % new_id,
       'Test NM content\n%s\n' % new_id,
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

  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "slapos-crm.stop.acknowledgment.escalation"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["test_checkToTriggerNextEscalationStep_notification_message"])')
  @simulate('RegularisationRequest_checkToTriggerNextEscalationStep',
            'day, current, next, title, text_content, comment, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
  '%s %s %s %s %s %s" % (day, current, next, title, text_content, comment))')
  def test_checkToTriggerNextEscalationStep_notification_message(self):
    ticket = self.createRegularisationRequest()
    new_id = self.generateNewId()
    notification_message = self.portal.notification_message_module.newContent(
      portal_type="Notification Message",
      title='Test NM title %s' % new_id,
      text_content='Test NM content<br/>%s<br/>' % new_id,
      content_type='text/html',
      )
    self.portal.REQUEST\
        ['test_checkToTriggerNextEscalationStep_notification_message'] = \
        notification_message.getRelativeUrl()
    ticket.RegularisationRequest_triggerStopAcknowledgmentEscalation()
    self.assertEqual(
      'Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
      '%s %s %s %s %s %s' % \
      (13,
       'service_module/slapos_crm_stop_acknowledgement',
       'service_module/slapos_crm_delete_reminder',
       'Test NM title %s' % new_id,
       'Test NM content\n%s\n' % new_id,
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

  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "slapos-crm.delete.reminder.escalation"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["test_checkToTriggerNextEscalationStep_notification_message"])')
  @simulate('RegularisationRequest_checkToTriggerNextEscalationStep',
            'day, current, next, title, text_content, comment, REQUEST=None',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
  '%s %s %s %s %s %s" % (day, current, next, title, text_content, comment))')
  def test_checkToTriggerNextEscalationStep_notification_message(self):
    ticket = self.createRegularisationRequest()
    new_id = self.generateNewId()
    notification_message = self.portal.notification_message_module.newContent(
      portal_type="Notification Message",
      title='Test NM title %s' % new_id,
      text_content='Test NM content<br/>%s<br/>' % new_id,
      content_type='text/html',
      )
    self.portal.REQUEST\
        ['test_checkToTriggerNextEscalationStep_notification_message'] = \
        notification_message.getRelativeUrl()
    ticket.RegularisationRequest_triggerDeleteReminderEscalation()
    self.assertEqual(
      'Visited by RegularisationRequest_checkToTriggerNextEscalationStep ' \
      '%s %s %s %s %s %s' % \
      (2,
       'service_module/slapos_crm_delete_reminder',
       'service_module/slapos_crm_delete_acknowledgement',
       'Test NM title %s' % new_id,
       'Test NM content\n%s\n' % new_id,
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
    self.createHostingSubscription()

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
    self.createPerson()
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
    self.createHostingSubscription()

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
    self.createHostingSubscription()

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
    self.createHostingSubscription()

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
    self.createPerson()
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
    self.createHostingSubscription()

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
    self.createHostingSubscription()

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
  
  
  
class TestSlapOSComputer_notifyWrongAllocationScope(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()
  
  def afterSetUp(self):
    super(TestSlapOSComputer_notifyWrongAllocationScope, self).afterSetUp()
    self.new_id = self.generateNewId()
    self._cancelTestSupportRequestList()
  
  def _cancelTestSupportRequestList(self):
    for support_request in self.portal.portal_catalog(
                        portal_type="Support Request",
                        title="%%TESTCOMPT-%",
                        simulation_state=["validated", "suspended"]):
      support_request.invalidate()
    self.tic()
  
  def _makeComputer(self):
    super(TestSlapOSComputer_notifyWrongAllocationScope, self)._makeComputer()
    
    # Clone computer document
    self.computer.edit(
      source_administration_value=self._makePerson()
    )
    return self.computer
  
  def _makePerson(self):
    # Clone computer document
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    person.edit(reference='TESTPERSON-%s' % (self.generateNewId(), ))
    person.immediateReindexObject()
    return person
  
  def _updatePersonAssignment(self, person, role='role/member'):
    for assignment in person.contentValues(portal_type="Assignment"):
      assignment.cancel()
    assignment = person.newContent(portal_type='Assignment')
    assignment.setRole(role)
    assignment.setStartDate(DateTime())
    assignment.open()
    return assignment
    
  def _getGeneratedSupportRequest(self, computer):
    request_title = '%%We have changed allocation scope for %s' % \
                        computer.getReference()
    support_request = self.portal.portal_catalog.getResultValue(
          portal_type = 'Support Request',
          title = request_title,
          simulation_state = 'suspended',
          default_aggregate_uid = computer.getUid()
    )
    return support_request
  
  def _makeNotificationMessage(self, reference):
    notification_message = self.portal.notification_message_module.newContent(
      portal_type="Notification Message",
      title='We have changed allocation scope for %s' % reference,
      text_content='Test NM content<br/>%s<br/>' % reference,
      content_type='text/html',
      )
    
    return notification_message.getRelativeUrl()
  

  @simulate('ERP5Site_isSupportRequestCreationClosed', '*args, **kwargs','return 0')
  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "slapos-crm-computer_allocation_scope.notification"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["test_computerNotAllowedAllocationScope_OpenPublic"])')
  @simulate('SupportRequest_trySendNotificationMessage',
            'message_title, message, destination_relative_url',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by SupportRequest_trySendNotificationMessage ' \
  '%s %s %s" % (message_title, message, destination_relative_url))\n' \
  'return 1')
  def test_computerNotAllowedAllocationScope_OpenPublic(self):
    computer = self._makeComputer()
    person = computer.getSourceAdministrationValue()
    self._updatePersonAssignment(person, 'role/member')
    
    self.portal.REQUEST['test_computerNotAllowedAllocationScope_OpenPublic'] = \
        self._makeNotificationMessage(computer.getReference())
    
    computer.edit(allocation_scope='open/public')
    ticket = computer.Computer_checkAndUpdateAllocationScope()
    self.tic()
    self.assertEquals(computer.getAllocationScope(), 'open/personal')
    #ticket = self._getGeneratedSupportRequest(computer)
    self.assertNotEquals(None, ticket)
    self.assertEquals(ticket.getSimulationState(), 'suspended')

    self.assertEqual('Visited by SupportRequest_trySendNotificationMessage ' \
      '%s %s %s' % \
      ('Allocation scope of %s changed to %s' % (computer.getReference(),
                                                  'open/personal'),
       'Test NM content\n%s\n' % computer.getReference(), person.getRelativeUrl()),
      ticket.workflow_history['edit_workflow'][-1]['comment'])
    

  @simulate('ERP5Site_isSupportRequestCreationClosed', '*args, **kwargs','return 0')
  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "slapos-crm-computer_allocation_scope.notification"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["test_computerNotAllowedAllocationScope_OpenFriend"])')
  @simulate('SupportRequest_trySendNotificationMessage',
            'message_title, message, destination_relative_url',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by SupportRequest_trySendNotificationMessage ' \
  '%s %s %s" % (message_title, message, destination_relative_url))\n' \
  'return 1')
  def test_computerNotAllowedAllocationScope_OpenFriend(self):
    computer = self._makeComputer()
    person = computer.getSourceAdministrationValue()
    self._updatePersonAssignment(person, 'role/member')
    
    self.portal.REQUEST['test_computerNotAllowedAllocationScope_OpenFriend'] = \
        self._makeNotificationMessage(computer.getReference())
    
    friend_person = self._makePerson()
    computer.edit(allocation_scope='open/friend',
        destination_section=friend_person.getRelativeUrl())
    ticket = computer.Computer_checkAndUpdateAllocationScope()
    self.tic()
    self.assertEquals(computer.getAllocationScope(), 'open/personal')
    self.assertEquals(ticket.getSimulationState(), 'suspended')
    self.assertEqual('Visited by SupportRequest_trySendNotificationMessage ' \
      '%s %s %s' % \
      ('Allocation scope of %s changed to %s' % (computer.getReference(),
                                                  'open/personal'),
       'Test NM content\n%s\n' % computer.getReference(), person.getRelativeUrl()),
      ticket.workflow_history['edit_workflow'][-1]['comment'])

  @simulate('ERP5Site_isSupportRequestCreationClosed', '*args, **kwargs','return 0')
  @simulate('Computer_hasContactedRecently', '*args, **kwargs','return False')
  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "slapos-crm-computer-allocation-scope-closed.notification"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["test_computerToCloseAllocationScope_OpenPersonal"])')
  @simulate('SupportRequest_trySendNotificationMessage',
            'message_title, message, destination_relative_url',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by SupportRequest_trySendNotificationMessage ' \
  '%s %s %s" % (message_title, message, destination_relative_url))\n' \
  'return 1')
  def test_computerToCloseAllocationScope_OpenPersonal(self):
    computer = self._makeComputer()
    person = computer.getSourceAdministrationValue()
    target_allocation_scope = 'close/outdated'
    
    self.portal.REQUEST['test_computerToCloseAllocationScope_OpenPersonal'] = \
        self._makeNotificationMessage(computer.getReference())
    
    computer.edit(allocation_scope='open/personal')
    support_request = computer.Computer_checkAndUpdatePersonalAllocationScope()
    self.tic()
    
    self.assertEquals('suspended', support_request.getSimulationState())
    self.assertEquals(computer.getAllocationScope(), target_allocation_scope)
    self.assertEqual('Visited by SupportRequest_trySendNotificationMessage ' \
      '%s %s %s' % \
      ('Allocation scope of %s changed to %s' % (computer.getReference(),
                                                  target_allocation_scope),
       'Test NM content\n%s\n' % computer.getReference(), person.getRelativeUrl()),
      support_request.workflow_history['edit_workflow'][-1]['comment'])

  def test_computerNormalAllocationScope_OpenPersonal(self):
    computer = self._makeComputer()
    person = computer.getSourceAdministrationValue()
    self._updatePersonAssignment(person, 'role/member')
    
    computer.edit(allocation_scope='open/personal')
    computer.Computer_checkAndUpdateAllocationScope()
    self.tic()
    self.assertEquals(computer.getAllocationScope(), 'open/personal')
  

  def test_computerAllowedAllocationScope_OpenPublic(self):
    computer = self._makeComputer()
    person = computer.getSourceAdministrationValue()
    self._updatePersonAssignment(person, 'role/service_provider')
    
    computer.edit(allocation_scope='open/public')
    computer.Computer_checkAndUpdateAllocationScope()
    self.tic()
    self.assertEquals(computer.getAllocationScope(), 'open/public')
    
  
  def test_computerAllowedAllocationScope_OpenFriend(self):
    computer = self._makeComputer()
    person = computer.getSourceAdministrationValue()
    self._updatePersonAssignment(person, 'role/service_provider')
    
    friend_person = self._makePerson()
    computer.edit(allocation_scope='open/friend',
        destination_section=friend_person.getRelativeUrl())
    computer.Computer_checkAndUpdateAllocationScope()
    self.tic()
    self.assertEquals(computer.getAllocationScope(), 'open/friend')


class TestComputer_hasContactedRecently(testSlapOSMixin):
  
  def beforeTearDown(self):
    transaction.abort()
  
  def afterSetUp(self):
    super(TestComputer_hasContactedRecently, self).afterSetUp()

  def _makeComputer(self):
    super(TestComputer_hasContactedRecently, self)._makeComputer()
    return self.computer

  def createSPL(self, computer):
    delivery_template = self.portal.restrictedTraverse(
      self.portal.portal_preferences.getPreferredInstanceDeliveryTemplate())
    delivery = delivery_template.Base_createCloneDocument(batch_mode=1)

    delivery.edit(
      title="TEST SPL COMP %s" % computer.getReference(),
      start_date=computer.getCreationDate(),
    )

    delivery.newContent(
      portal_type="Sale Packing List Line",
      title="SPL Line for %s" % computer.getReference(),
      quantity=1,
      aggregate_value_list=computer,
    )
    delivery.confirm(comment="Created from %s" % computer.getRelativeUrl())
    delivery.start()
    delivery.stop()
    delivery.deliver()
    return delivery

  def test_Computer_hasContactedRecently_newly_created(self):
    computer = self._makeComputer()
    self.tic()
    has_contacted = computer.Computer_hasContactedRecently()
    self.assertTrue(has_contacted)

  @simulate('Computer_getCreationDate', '*args, **kwargs','return DateTime() - 32')
  def test_Computer_hasContactedRecently_no_data(self):
    computer = self._makeComputer()
    self.tic()

    computer.getCreationDate = self.portal.Computer_getCreationDate
    has_contacted = computer.Computer_hasContactedRecently()
    self.assertFalse(has_contacted)

  @simulate('Computer_getCreationDate', '*args, **kwargs','return DateTime() - 32')
  def test_Computer_hasContactedRecently_memcached(self):
    computer = self._makeComputer()
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
        key_prefix='slap_tool',
        plugin_path='portal_memcached/default_memcached_plugin')

    memcached_dict[computer.getReference()] = json.dumps({
      "created_at": DateTime().strftime("%Y/%m/%d %H:%M")
    })
    self.tic()

    computer.getCreationDate = self.portal.Computer_getCreationDate

    has_contacted = computer.Computer_hasContactedRecently()
    self.assertTrue(has_contacted)

  @simulate('Computer_getCreationDate', '*args, **kwargs','return DateTime() - 32')
  def test_Computer_hasContactedRecently_memcached_oudated_no_spl(self):
    computer = self._makeComputer()
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
        key_prefix='slap_tool',
        plugin_path='portal_memcached/default_memcached_plugin')

    memcached_dict[computer.getReference()] = json.dumps({
      "created_at": (DateTime() - 32).strftime("%Y/%m/%d %H:%M")
    })
    self.tic()

    computer.getCreationDate = self.portal.Computer_getCreationDate

    has_contacted = computer.Computer_hasContactedRecently()
    self.assertFalse(has_contacted)

  @simulate('Computer_getCreationDate', '*args, **kwargs','return DateTime() - 32')
  def test_Computer_hasContactedRecently_memcached_oudated_with_spl(self):
    computer = self._makeComputer()
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
        key_prefix='slap_tool',
        plugin_path='portal_memcached/default_memcached_plugin')

    memcached_dict[computer.getReference()] = json.dumps({
      "created_at": (DateTime() - 32).strftime("%Y/%m/%d %H:%M")
    })
    self.createSPL(computer)
    self.tic()

    computer.getCreationDate = self.portal.Computer_getCreationDate

    has_contacted = computer.Computer_hasContactedRecently()
    self.assertFalse(has_contacted)

class TestSlapOSPerson_isServiceProvider(testSlapOSMixin):
  
  def beforeTearDown(self):
    transaction.abort()
  
  def afterSetUp(self):
    super(TestSlapOSPerson_isServiceProvider, self).afterSetUp()
    
    
  def test_Person_isServiceProvider(self):
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    person.edit(reference='TESTPERSON-%s' % (self.generateNewId(), ))
    
    self.assertFalse(person.Person_isServiceProvider())
    person.setRole("service_provider")
    self.assertTrue(person.Person_isServiceProvider())

  def test_Person_isServiceProvider_assignment(self):
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    person.edit(reference='TESTPERSON-%s' % (self.generateNewId(), ))
    
    self.assertFalse(person.Person_isServiceProvider())
    assignment = person.newContent(portal_type="Assignment",
                                   role="service_provider")
    self.assertFalse(person.Person_isServiceProvider())
    assignment.open()
    self.assertTrue(person.Person_isServiceProvider())
  

class TestSlapOSisSupportRequestCreationClosed(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()
  
  def afterSetUp(self):
    super(TestSlapOSisSupportRequestCreationClosed, self).afterSetUp()
    self.new_id = self.generateNewId()
    self._cancelTestSupportRequestList()
  
  def _cancelTestSupportRequestList(self):
    for support_request in self.portal.portal_catalog(
                        portal_type="Support Request",
                        simulation_state=["validated", "suspended"]):
      support_request.invalidate()
    self.tic()
  
  def _makePerson(self):
    # Clone computer document
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    person.edit(reference='TESTPERSON-%s' % (self.generateNewId(), ))
    person.immediateReindexObject()
    return person

  def test_ERP5Site_isSupportRequestCreationClosed(self):
    
    person = self._makePerson()
    other_person = self._makePerson()
    url = person.getRelativeUrl()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed())

    def newSupportRequest():
      sr = self.portal.support_request_module.newContent(\
                        title="Test Support Request POIUY",
                        resource="service_module/slapos_crm_monitoring",
                        destination_decision=url)
      sr.validate()
      sr.immediateReindexObject()

    newSupportRequest()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    newSupportRequest()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    newSupportRequest()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    newSupportRequest()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    newSupportRequest()
    self.assertTrue(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    
    self.assertTrue(self.portal.ERP5Site_isSupportRequestCreationClosed())
    
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(
                     other_person.getRelativeUrl()))
  
  def test_ERP5Site_isSupportRequestCreationClosed_suspended_state(self):
    person = self._makePerson()
    url = person.getRelativeUrl()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed())
    
    def newSupportRequest():
      sr = self.portal.support_request_module.newContent(\
                        title="Test Support Request POIUY",
                        resource="service_module/slapos_crm_monitoring",
                        destination_decision=url)
      sr.validate()
      sr.suspend()
      sr.immediateReindexObject()
    # Create five tickets, the limit of ticket creation
    newSupportRequest()
    newSupportRequest()
    newSupportRequest()
    newSupportRequest()
    newSupportRequest()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed())


  def test_ERP5Site_isSupportRequestCreationClosed_nonmonitoring(self):
    person = self._makePerson()
    url = person.getRelativeUrl()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed())
    
    def newSupportRequest():
      sr = self.portal.support_request_module.newContent(\
                        title="Test Support Request POIUY",
                        destination_decision=url)
      sr.validate()
      sr.immediateReindexObject()

    # Create five tickets, the limit of ticket creation
    newSupportRequest()
    newSupportRequest()
    newSupportRequest()
    newSupportRequest()
    newSupportRequest()

    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed())
    

class TestSlapOSGenerateSupportRequestForSlapOS(testSlapOSMixin):
  
  
  def afterSetUp(self):
    super(TestSlapOSGenerateSupportRequestForSlapOS, self).afterSetUp()
    self.tic()
    self._cancelTestSupportRequestList()
  
  def _cancelTestSupportRequestList(self):
    for support_request in self.portal.portal_catalog(
                        portal_type="Support Request",
                        simulation_state=["validated", "suspended"]):
      support_request.invalidate()
    self.tic()

  def _makeHostingSubscription(self):
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    hosting_subscription = self.portal\
      .hosting_subscription_module.template_hosting_subscription\
      .Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    new_id = self.generateNewId()
    hosting_subscription.edit(
        title= "Test hosting sub ticket %s" % new_id,
        reference="TESTHST-%s" % new_id,
        destination_section_value=person
    )

    return hosting_subscription

  def _makeSoftwareInstance(self, hosting_subscription, software_url):

    kw = dict(
      software_release=software_url,
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='started'
    )
    hosting_subscription.requestStart(**kw)
    hosting_subscription.requestInstance(**kw)
    
  def _makeComputer(self):
    super(TestSlapOSGenerateSupportRequestForSlapOS, self)._makeComputer()
    
    # Clone computer document
    self.computer.edit(
      source_administration_value=self._makePerson()
    )
    return self.computer
  
  def _makePerson(self):
    # Clone computer document
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    person.edit(reference='TESTPERSON-%s' % (self.generateNewId(), ))
    person.immediateReindexObject()
    return person
    
  def _makeSoftwareInstallation(self):
    self._makeComputer()
    software_installation = self.portal\
       .software_installation_module.template_software_installation\
       .Base_createCloneDocument(batch_mode=1)
    software_installation.edit(
       url_string=self.generateNewSoftwareReleaseUrl(),
       aggregate=self.computer.getRelativeUrl(),
       reference='TESTSOFTINSTS-%s' % self.generateNewId(),
       title='Start requested for %s' % self.computer.getUid()
     )
    software_installation.validate()
    software_installation.requestStart()

    return software_installation
  
  def test_computer_Base_generateSupportRequestForSlapOS(self):
    self._makeComputer()
    title = "Test Support Request %s" % self.computer.getReference()
    support_request = self.computer.Base_generateSupportRequestForSlapOS(
      title, title, self.computer.getRelativeUrl()
    )
    self.tic()

    self.assertNotEqual(support_request, None)

    self.assertEqual(support_request.getSimulationState(), "validated")
    self.assertEqual(support_request.getRelativeUrl(), 
      self.portal.REQUEST.get("support_request_in_progress", None))

    # The support request is added to computer owner.
    self.assertEquals(support_request.getDestinationDecision(),
                      self.computer.getSourceAdministration())
    self.assertEquals(support_request.getTitle(), title)
    self.assertEquals(support_request.getDescription(), title)
    self.assertEquals(support_request.getAggregateValue(),
                      self.computer)

  def test_software_instance_Base_generateSupportRequestForSlapOS(self):
    hosting_subscription = self._makeHostingSubscription()
    self._makeSoftwareInstance(hosting_subscription, 
                               self.generateNewSoftwareReleaseUrl())
                               
    instance = hosting_subscription.getPredecessorValue()
    title = "Test Support Request %s" % instance.getReference()
    support_request = instance.Base_generateSupportRequestForSlapOS(
      title, title, instance.getRelativeUrl()
    )
    self.tic()

    self.assertNotEqual(support_request, None)
    
    self.assertEqual(support_request.getSimulationState(), "validated")
    self.assertEqual(support_request.getRelativeUrl(), 
      self.portal.REQUEST.get("support_request_in_progress", None))

    # The support request is added to computer owner.
    self.assertEquals(support_request.getDestinationDecision(),
                      hosting_subscription.getDestinationSection())
    self.assertEquals(support_request.getTitle(), title)
    self.assertEquals(support_request.getDescription(), title)
    self.assertEquals(support_request.getAggregateValue(),
                      instance)

  def test_hosting_subscription_Base_generateSupportRequestForSlapOS(self):
    hosting_subscription = self._makeHostingSubscription()

    title = "Test Support Request %s" % hosting_subscription.getReference()
    support_request = hosting_subscription.Base_generateSupportRequestForSlapOS(
      title, title, hosting_subscription.getRelativeUrl()
    )
    self.tic()

    self.assertNotEqual(support_request, None)

    self.assertEqual(support_request.getSimulationState(), "validated")
    self.assertEqual(support_request.getRelativeUrl(), 
      self.portal.REQUEST.get("support_request_in_progress", None))

    # The support request is added to computer owner.
    self.assertEquals(support_request.getDestinationDecision(),
                      hosting_subscription.getDestinationSection())

    self.assertEquals(support_request.getTitle(), title)
    self.assertEquals(support_request.getDescription(), title)
    self.assertEquals(support_request.getAggregateValue(),
                      hosting_subscription)

  def test_software_installation_Base_generateSupportRequestForSlapOS(self):
    software_installation = self._makeSoftwareInstallation()

    title = "Test Support Request %s" % software_installation.generateNewId()
    support_request = software_installation.Base_generateSupportRequestForSlapOS(
      title, title, software_installation.getRelativeUrl()
    )
    self.tic()

    self.assertNotEqual(support_request, None)

    self.assertEqual(support_request.getSimulationState(), "validated")
    self.assertEqual(support_request.getRelativeUrl(), 
      self.portal.REQUEST.get("support_request_in_progress", None))

    # The support request is added to computer owner.
    self.assertEquals(support_request.getDestinationDecision(),
                      software_installation.getDestinationSection())

    self.assertEquals(support_request.getTitle(), title)
    self.assertEquals(support_request.getDescription(), title)
    self.assertEquals(support_request.getAggregateValue(),
                      software_installation)


  def test_Base_generateSupportRequestForSlapOS_do_not_recreate_if_open(self):
    self._makeComputer()
    title = "Test Support Request %s" % self.computer.getReference()
    support_request = self.computer.Base_generateSupportRequestForSlapOS(
      title, title, self.computer.getRelativeUrl()
    )
    self.tic()
    self.portal.REQUEST.set("support_request_in_progress", None)

    same_support_request = self.computer.Base_generateSupportRequestForSlapOS(
      title, title, self.computer.getRelativeUrl()
    )
    
    self.assertEqual(support_request, same_support_request)


  def test_Base_generateSupportRequestForSlapOS_do_not_recreate_if_suspended(self):
    self._makeComputer()
    title = "Test Support Request %s" % self.computer.getReference()
    support_request = self.computer.Base_generateSupportRequestForSlapOS(
      title, title, self.computer.getRelativeUrl()
    )
    
    support_request.suspend()
    self.tic()
    self.portal.REQUEST.set("support_request_in_progress", None)

    same_support_request = self.computer.Base_generateSupportRequestForSlapOS(
      title, title, self.computer.getRelativeUrl()
    )
    
    self.assertEqual(support_request, same_support_request)

  def test_Base_generateSupportRequestForSlapOS_recreate_if_closed(self):
    self._makeComputer()
    title = "Test Support Request %s" % self.computer.getReference()
    support_request = self.computer.Base_generateSupportRequestForSlapOS(
      title, title, self.computer.getRelativeUrl())
    self.tic()

    support_request.invalidate()
    self.tic()
    
    self.portal.REQUEST.set("support_request_in_progress", None)

    support_request = self.computer.Base_generateSupportRequestForSlapOS(
      title, title, self.computer.getRelativeUrl()
    )
    self.tic()

    self.assertNotEqual(support_request, None)

  def test_Base_generateSupportRequestForSlapOS_recreate(self):
    self._makeComputer()
    title = "Test Support Request %s" % self.computer.getRelativeUrl()
    support_request = self.computer.Base_generateSupportRequestForSlapOS(
      title, title, self.computer.getRelativeUrl())

    same_support_request = self.computer.Base_generateSupportRequestForSlapOS(
      title, title, self.computer.getRelativeUrl()
    )
    
    self.assertEqual(support_request, same_support_request)
    
  def test_Base_generateSupportRequestForSlapOS_inprogress(self):
    self._makeComputer()
    title = "Test Support Request %s" % self.computer.getRelativeUrl()
    support_request = self.computer.Base_generateSupportRequestForSlapOS(
      title, title, self.computer.getRelativeUrl())

    in_progress = support_request.getRelativeUrl()
    self.portal.REQUEST.set("support_request_in_progress", in_progress)

    title = "Test Support Request %s" % self.computer.getRelativeUrl()
    support_request = self.computer.Base_generateSupportRequestForSlapOS(
      title, title, self.computer.getRelativeUrl())

    self.assertEqual(support_request.getRelativeUrl(), in_progress)
    

class TestSlapOSComputer_CheckState(testSlapOSMixin):

  def beforeTearDown(self):
    self._cancelTestSupportRequestList()
    transaction.abort()
  
  def afterSetUp(self):
    super(TestSlapOSComputer_CheckState, self).afterSetUp()
    self.new_id = self.generateNewId()
    self._cancelTestSupportRequestList()
    
  def _makeSupportRequest(self):
    support_request = self.portal.\
      support_request_module.\
      slapos_crm_support_request_template_for_monitoring.\
       Base_createCloneDocument(batch_mode=1)
    return support_request

  def _cancelTestSupportRequestList(self):
    for support_request in self.portal.portal_catalog(
                        portal_type="Support Request",
                        title="% TESTCOMPT-%",
                        simulation_state=["validated", "suspended"]):
      support_request.invalidate()
    self.tic()
  
  def _makeNotificationMessage(self, reference):
    notification_message = self.portal.notification_message_module.newContent(
      portal_type="Notification Message",
      title='The Computer %s has not contacted the server for more than 24 hours' % reference,
      text_content='Test NM content<br/>%s<br/>' % reference,
      content_type='text/html',
      )
    
    return notification_message.getRelativeUrl()
  
  def _getGeneratedSupportRequest(self, computer_uid, request_title):
    support_request = self.portal.portal_catalog.getResultValue(
          portal_type = 'Support Request',
          title = request_title,
          simulation_state = 'validated',
          default_aggregate_uid = computer_uid
    )
    return support_request
  
  def _makeComputer(self):
    super(TestSlapOSComputer_CheckState, self)._makeComputer()
    
    # Clone computer document
    self.computer.edit(
      source_administration_value=self._makePerson()
    )
    return self.computer
  
  def _makePerson(self):
    # Clone computer document
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    person.edit(reference='TESTPERSON-%s' % (self.generateNewId(), ))
    person.immediateReindexObject()
    return person

  def _simulateBase_generateSupportRequestForSlapOS(self):
    script_name = 'Base_generateSupportRequestForSlapOS'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""return context.getPortalObject().REQUEST['_simulateBase_generateSupportRequestForSlapOS']""")
    transaction.commit()

  def _dropBase_generateSupportRequestForSlapOS(self):
    script_name = 'Base_generateSupportRequestForSlapOS'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()
    self.assertFalse(script_name in self.portal.portal_skins.custom.objectIds())

  @simulate('ERP5Site_isSupportRequestCreationClosed', '*args, **kwargs','return 0')
  def test_Computer_checkState_call_support_request(self):
    computer = self._makeComputer()
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

    memcached_dict[computer.getReference()] = json.dumps(
        {"created_at":"%s" % (DateTime() - 1.1)}
    )

    self._simulateBase_generateSupportRequestForSlapOS()
    support_request = self._makeSupportRequest()
    self.portal.REQUEST.set('_simulateBase_generateSupportRequestForSlapOS', 
                               support_request)

    try:
      computer_support_request = computer.Computer_checkState()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()

    self.assertEqual(support_request,
      computer_support_request)


  @simulate('ERP5Site_isSupportRequestCreationClosed', '*args, **kwargs','return 0')
  def test_Computer_checkState_empty_cache(self):
    computer = self._makeComputer()

    self._simulateBase_generateSupportRequestForSlapOS()
    support_request = self._makeSupportRequest()
    self.portal.REQUEST.set('_simulateBase_generateSupportRequestForSlapOS', 
                               support_request)

    try:
      computer_support_request = computer.Computer_checkState()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertEqual(support_request,
      computer_support_request)
  
  @simulate('ERP5Site_isSupportRequestCreationClosed', '*args, **kwargs','return 0')
  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "slapos-crm-computer_check_state.notification"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["test_Computer_checkState_notify"])')
  @simulate('SupportRequest_trySendNotificationMessage',
            'message_title, message, destination_relative_url',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by SupportRequest_trySendNotificationMessage ' \
  '%s %s %s" % (message_title, message, destination_relative_url))')
  def test_Computer_checkState_notify(self):
    computer = self._makeComputer()
    person = computer.getSourceAdministrationValue()


    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

    memcached_dict[computer.getReference()] = json.dumps(
        {"created_at":"%s" % (DateTime() - 0.1)}
    )
    
    self.portal.REQUEST['test_Computer_checkState_notify'] = \
        self._makeNotificationMessage(computer.getReference())
    
    computer.Computer_checkState()
    self.tic()
    
    ticket_title = "[MONITORING] Lost contact with computer %s" % computer.getReference()
    ticket = self._getGeneratedSupportRequest(computer.getUid(), ticket_title)
    self.assertNotEqual(ticket, None)
    self.assertEqual('Visited by SupportRequest_trySendNotificationMessage ' \
      '%s %s %s' % ( \
      ticket_title,
      'Test NM content\n%s\n' % computer.getReference(),
      person.getRelativeUrl()),
      ticket.workflow_history['edit_workflow'][-1]['comment'])
  
  
  @simulate('ERP5Site_isSupportRequestCreationClosed', '*args, **kwargs','return 0')
  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "slapos-crm-computer_check_state.notification"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["test_Computer_checkState_empty_cache_notify"])')
  @simulate('SupportRequest_trySendNotificationMessage',
            'message_title, message, destination_relative_url',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by SupportRequest_trySendNotificationMessage ' \
  '%s %s %s" % (message_title, message, destination_relative_url))')
  def test_Computer_checkState_empty_cache_notify(self):
    computer = self._makeComputer()
    person = computer.getSourceAdministrationValue()
    
    self.portal.REQUEST['test_Computer_checkState_empty_cache_notify'] = \
        self._makeNotificationMessage(computer.getReference())
    
    computer.Computer_checkState()
    self.tic()
    
    ticket_title = "[MONITORING] No information about %s" % computer.getReference()
    ticket = self._getGeneratedSupportRequest(computer.getUid(), ticket_title)
    self.assertNotEqual(ticket, None)
    self.assertEqual('Visited by SupportRequest_trySendNotificationMessage ' \
      '%s %s %s' % ( \
      ticket_title,
      'Test NM content\n%s\n' % computer.getReference(),
      person.getRelativeUrl()),
      ticket.workflow_history['edit_workflow'][-1]['comment'])


class TestSlapOSHostingSubscription_createSupportRequestEvent(testSlapOSMixin):

  def _makeNotificationMessage(self, reference):
    notification_message = self.portal.notification_message_module.newContent(
      portal_type="Notification Message",
      title='%s created an event' % reference,
      text_content='Test NM content<br/>%s<br/>' % reference,
      content_type='text/html',
      )
    
    return notification_message.getRelativeUrl()
  
  def _makeHostingSubscription(self):
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    hosting_subscription = self.portal\
      .hosting_subscription_module.template_hosting_subscription\
      .Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    new_id = self.generateNewId()
    hosting_subscription.edit(
        title= "Test hosting sub ticket %s" % new_id,
        reference="TESTHST-%s" % new_id,
        destination_section_value=person
    )

    return hosting_subscription
    
  def _getGeneratedSupportRequest(self, hosting_suscription_uid):
    support_request = self.portal.portal_catalog.getResultValue(
          portal_type = 'Support Request',
          simulation_state = "validated",
          default_aggregate_uid = hosting_suscription_uid
    )
    return support_request

  @simulate('ERP5Site_isSupportRequestCreationClosed', '*args, **kwargs','return 0')
  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "test-slapos-crm-check.notification"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["testHostingSubscription_createSupportRequestEvent"])')
  @simulate('SupportRequest_trySendNotificationMessage',
            'message_title, message, destination_relative_url',
  'context.portal_workflow.doActionFor(' \
  'context, action="edit_action", ' \
  'comment="Visited by SupportRequest_trySendNotificationMessage ' \
  '%s %s %s" % (message_title, message, destination_relative_url))')
  def testHostingSubscription_createSupportRequestEvent(self):
    hosting_subscription = self._makeHostingSubscription()
    person =  hosting_subscription.getDestinationSectionValue()
    self.portal.REQUEST['testHostingSubscription_createSupportRequestEvent'] = \
        self._makeNotificationMessage(hosting_subscription.getReference())

    hosting_subscription.HostingSubscription_createSupportRequestEvent(
      hosting_subscription, "test-slapos-crm-check.notification")
    
    self.tic()
    ticket_title = "Hosting Subscription %s is failing." % hosting_subscription.getTitle()
    ticket = self._getGeneratedSupportRequest(
      hosting_subscription.getUid())
    self.assertNotEqual(ticket, None)
    self.assertEqual(ticket.getSimulationState(), "validated")
    self.assertEqual('Visited by SupportRequest_trySendNotificationMessage ' \
      '%s %s %s' % ( \
      ticket_title,
      'Test NM content\n%s\n' % hosting_subscription.getReference(),
      person.getRelativeUrl()),
      ticket.workflow_history['edit_workflow'][-1]['comment'])

    ticket.suspend()
    self.tic()
    self.assertEquals(None, self._getGeneratedSupportRequest(
      hosting_subscription.getUid()))
    
    hosting_subscription.HostingSubscription_createSupportRequestEvent(
      hosting_subscription, "test-slapos-crm-check.notification")
    self.tic()
    
    previous_ticket = ticket
    ticket = self._getGeneratedSupportRequest(
      hosting_subscription.getUid())
    self.assertEqual(ticket, previous_ticket)
    self.assertEqual(ticket.getSimulationState(), "validated")
    self.assertEqual('Visited by SupportRequest_trySendNotificationMessage ' \
      '%s %s %s' % ( \
      ticket_title.replace('', ''),
      'Test NM content\n%s\n' % hosting_subscription.getReference(),
      person.getRelativeUrl()),
      ticket.workflow_history['edit_workflow'][-1]['comment'])
      
  @simulate('ERP5Site_isSupportRequestCreationClosed', '*args, **kwargs','return 1')
  def testHostingSubscription_createSupportRequestEvent_closed(self):
    hosting_subscription = self._makeHostingSubscription()
    self.assertEquals(None, 
      hosting_subscription.HostingSubscription_createSupportRequestEvent(
         hosting_subscription, "test-slapos-crm-check.notification"))

  @simulate('ERP5Site_isSupportRequestCreationClosed', '*args, **kwargs','return 0')
  def testHostingSubscription_createSupportRequestEvent_no_person(self):
    hosting_subscription = self._makeHostingSubscription()
    hosting_subscription.setDestinationSectionValue(None)
    self.assertEquals(None,
      hosting_subscription.HostingSubscription_createSupportRequestEvent(
         hosting_subscription, "test-slapos-crm-check.notification"))

class TestSlapOSHasError(testSlapOSMixin):
  
  def _makeSoftwareRelease(self, software_release_url=None):
    software_release = self.portal.software_release_module\
      .template_software_release.Base_createCloneDocument(batch_mode=1)
      
    new_id = self.generateNewId()
    software_release.edit(
      url_string=software_release_url or self.generateNewSoftwareReleaseUrl(),
      reference='TESTSOFTRELS-%s' % new_id,
      title='Start requested for %s' % new_id
    )
    software_release.release()

    return software_release
    
  def _makeSoftwareInstallation(self, software_release_url):
    software_installation = self.portal\
       .software_installation_module.template_software_installation\
       .Base_createCloneDocument(batch_mode=1)

    new_id = self.generateNewId()
    software_installation.edit(
       url_string=software_release_url,
       aggregate=self.computer.getRelativeUrl(),
       reference='TESTSOFTINSTS-%s' % new_id,
       title='Start requested for %s' % self.computer.getUid()
     )
    software_installation.validate()
    software_installation.requestStart()

    return software_installation

  def _makeSoftwareInstance(self, hosting_subscription, software_url):

    kw = dict(
      software_release=software_url,
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='started'
    )
    hosting_subscription.requestStart(**kw)
    hosting_subscription.requestInstance(**kw)

  def _makeHostingSubscription(self):
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    hosting_subscription = self.portal\
      .hosting_subscription_module.template_hosting_subscription\
      .Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    new_id = self.generateNewId()
    hosting_subscription.edit(
        title= "Test hosting sub ticket %s" % new_id,
        reference="TESTHST-%s" % new_id,
        destination_section_value=person
    )

    return hosting_subscription

  def _makeComputerPartitionList(self):
    for i in range(1, 5):
      id_ = 'partition%s' % (i, )
      p = self.computer.newContent(portal_type='Computer Partition',
        id=id_,
        title=id_,
        reference=id_,
        default_network_address_ip_address='ip_address_%s' % i,
        default_network_address_netmask='netmask_%s' % i)
      p.markFree()
      p.validate()

  def test_SoftwareInstance_hasReportedError(self):
    hosting_subscription = self._makeHostingSubscription()
    self._makeSoftwareInstance(hosting_subscription, 
        self.generateNewSoftwareReleaseUrl())
    instance = hosting_subscription.getPredecessorValue()

    self._makeComputer()
    self._makeComputerPartitionList()
    
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

    error_date = DateTime()
    memcached_dict[instance.getReference()] = json.dumps(
        {"created_at":"%s" % error_date, "text": "#error "}
    )
    
    self.assertEquals(instance.SoftwareInstance_hasReportedError(), None)

    instance.setAggregateValue(self.computer.partition1)
    
    self.assertEquals(instance.SoftwareInstance_hasReportedError(), error_date)

    memcached_dict[instance.getReference()] = json.dumps(
        {"created_at":"%s" % error_date, "text": "#access "}
    )
    
    self.assertEquals(instance.SoftwareInstance_hasReportedError(), None)

  def test_SoftwareInstallation_hasReportedError(self):
    software_release = self._makeSoftwareRelease()
    self._makeComputer()
    installation = self._makeSoftwareInstallation(
      software_release.getUrlString()
    )

    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

    self.assertEquals(installation.SoftwareInstallation_hasReportedError(), None)

    error_date = DateTime()
    memcached_dict[installation.getReference()] = json.dumps(
        {"created_at":"%s" % error_date, "text": "#error "}
    )

    self.assertEquals(installation.SoftwareInstallation_hasReportedError(), error_date)
    
    memcached_dict[installation.getReference()] = json.dumps(
        {"created_at":"%s" % error_date, "text": "#building "}
     )
    
    self.assertEquals(installation.SoftwareInstallation_hasReportedError(), None)

  @simulate('ERP5Site_isSupportRequestCreationClosed', '','return 0')
  @simulate('HostingSubscription_createSupportRequestEvent',
            'instance, notification_message_reference',
  'return "Visited by HostingSubscription_createSupportRequestEvent ' \
  '%s %s" % (instance.getUid(), notification_message_reference)')
  def testHostingSubscription_checkSoftwareInstanceState(self):
    date = DateTime()
    def getCreationDate(*args, **kwargs):
      return date - 2

    from Products.ERP5Type.Base import Base

    original_get_creation = Base.getCreationDate
    Base.getCreationDate = getCreationDate
    try:
      hosting_subscription = self._makeHostingSubscription()
      
      self.assertEquals(hosting_subscription.getCreationDate(), date - 2)

      self._makeSoftwareInstance(hosting_subscription, 
          self.generateNewSoftwareReleaseUrl())
      instance = hosting_subscription.getPredecessorValue()

      self.assertEquals(instance.getCreationDate(), date - 2)

      self._makeComputer()
      self._makeComputerPartitionList()
      instance.setAggregateValue(self.computer.partition1)

      memcached_dict = self.portal.portal_memcached.getMemcachedDict(
        key_prefix='slap_tool',
        plugin_path='portal_memcached/default_memcached_plugin')

      error_date = DateTime()
      memcached_dict[instance.getReference()] = json.dumps(
        {"created_at":"%s" % error_date, "text": "#error "}
      )

      self.assertEquals(
        'Visited by HostingSubscription_createSupportRequestEvent %s %s' % \
        (instance.getUid(), 
         "slapos-crm-hosting-subscription-instance-state.notification"),
        hosting_subscription.HostingSubscription_checkSoftwareInstanceState())
     
      memcached_dict[instance.getReference()] = json.dumps(
          {"created_at":"%s" % error_date, "text": "#access "}
      )

      self.assertEquals(None,
        hosting_subscription.HostingSubscription_checkSoftwareInstanceState())
     

    finally:
      Base.getCreationDate = original_get_creation

      self.portal.portal_types.resetDynamicDocumentsOnceAtTransactionBoundary()
      transaction.commit()


  @simulate('ERP5Site_isSupportRequestCreationClosed', '','return 0')
  @simulate('HostingSubscription_createSupportRequestEvent',
            'instance, notification_message_reference',
  'return "Visited by HostingSubscription_createSupportRequestEvent ' \
  '%s %s" % (instance.getRelativeUrl(), notification_message_reference)')
  def testHostingSubscription_checkSoftwareInstanceState_partially_allocation(self):
    date = DateTime()
    def getCreationDate(*args, **kwargs):
      return date - 2

    from Products.ERP5Type.Base import Base

    original_get_creation = Base.getCreationDate
    Base.getCreationDate = getCreationDate
    try:
      hosting_subscription = self._makeHostingSubscription()
      
      self.assertEquals(hosting_subscription.getCreationDate(), date - 2)

      self._makeSoftwareInstance(hosting_subscription, 
          self.generateNewSoftwareReleaseUrl())
      instance = hosting_subscription.getPredecessorValue()

      self.assertEquals(instance.getCreationDate(), date - 2)

      self._makeComputer()
      self._makeComputerPartitionList()
      instance.setAggregateValue(self.computer.partition1)
      
      kw = dict(
        software_release=hosting_subscription.getUrlString(),
        software_type=self.generateNewSoftwareType(),
        instance_xml=self.generateSafeXml(),
        sla_xml=self.generateSafeXml(),
        shared=False,
        software_title="Another INstance %s" % self.generateNewId(),
        state='started'
      )
      instance.requestInstance(**kw)
      self.tic()
      
      memcached_dict = self.portal.portal_memcached.getMemcachedDict(
        key_prefix='slap_tool',
        plugin_path='portal_memcached/default_memcached_plugin')
      error_date = DateTime()
      memcached_dict[instance.getReference()] = json.dumps(
        {"created_at":"%s" % error_date, "text": "#access "}
      )

      self.assertEquals(
        'Visited by HostingSubscription_createSupportRequestEvent %s %s' % \
        (instance.getPredecessor(portal_type="Software Instance"), 
         "slapos-crm-hosting-subscription-instance-allocation.notification"),
        hosting_subscription.HostingSubscription_checkSoftwareInstanceState())

      kw["state"] = "destroyed"
      instance.requestInstance(**kw)
      self.tic()

      self.assertEquals(
        None,
        hosting_subscription.HostingSubscription_checkSoftwareInstanceState())

    finally:
      Base.getCreationDate = original_get_creation

      self.portal.portal_types.resetDynamicDocumentsOnceAtTransactionBoundary()
      transaction.commit()

  @simulate('ERP5Site_isSupportRequestCreationClosed', '','return 0')
  def testHostingSubscription_checkSoftwareInstanceState_too_early(self):
    hosting_subscription = self._makeHostingSubscription()
      
    self._makeSoftwareInstance(hosting_subscription, 
        self.generateNewSoftwareReleaseUrl())
    instance = hosting_subscription.getPredecessorValue()

    
    self._makeComputer()
    self._makeComputerPartitionList()
    instance.setAggregateValue(self.computer.partition1)

    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

    error_date = DateTime()
    memcached_dict[instance.getReference()] = json.dumps(
      {"created_at":"%s" % error_date, "text": "#error "}
    )

    self.assertEquals(
        None,
        hosting_subscription.HostingSubscription_checkSoftwareInstanceState())

class TestSupportRequestTrySendNotificationMessage(testSlapOSMixin):

  def _makeComputer(self):
    super(TestSupportRequestTrySendNotificationMessage, self)._makeComputer()
    
    # Clone computer document
    self.computer.edit(
      source_administration_value=self._makePerson()
    )
    return self.computer
  
  def _makePerson(self):
    # Clone computer document
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    person.edit(reference='TESTPERSON-%s' % (self.generateNewId(), ))
    person.immediateReindexObject()
    return person

  def test_SupportRequest_trySendNotificationMessage(self):
    self._makeComputer()
    person = self.computer.getSourceAdministrationValue()
    title = "Test Support Request %s" % self.computer.getReference()
    text_content='Test NM content<br/>%s<br/>' % self.computer.getReference()
    
    support_request = self.portal.support_request_module.newContent(\
            title=title, description=title,
            destination_decision=self.computer.getSourceAdministration(),
            aggregate_value=self.computer.getRelativeUrl())
    support_request.validate()
    self.tic()
    
    first_event = support_request.SupportRequest_trySendNotificationMessage(
      message_title=title, message=text_content,
      destination_relative_url=person.getRelativeUrl()
    )
    self.assertNotEqual(first_event, None)
    
    self.assertEquals(
      support_request.getFollowUpRelatedList(), 
      [first_event.getRelativeUrl()])
    
    self.assertEquals(title, first_event.getTitle())
    self.assertEquals(text_content, first_event.getTextContent())
    self.assertNotEquals(None, first_event.getStartDate())
    self.assertEquals("service_module/slapos_crm_information", 
                      first_event.getResource())
    self.assertEquals(first_event.getDestination(), person.getRelativeUrl())
    self.assertEquals(first_event.getFollowUp(), support_request.getRelativeUrl())

    event = support_request.SupportRequest_trySendNotificationMessage(
      message_title=title, message=text_content,
      destination_relative_url=person.getRelativeUrl()
    )
    self.assertEqual(event, first_event)

    self.assertEquals(title, event.getTitle())
    self.assertEquals(text_content, event.getTextContent())
    self.assertNotEquals(None, event.getStartDate())
    self.assertEquals("service_module/slapos_crm_information", 
                      event.getResource())
    self.assertEquals(event.getDestination(), person.getRelativeUrl())
    
    title += "__zz"
    event = support_request.SupportRequest_trySendNotificationMessage(
      message_title=title, message=text_content,
      destination_relative_url=person.getRelativeUrl(),
    )
    
    self.assertEqual(event.getTitle(), title)
    self.assertEquals(text_content, event.getTextContent())
    self.assertNotEquals(None, event.getStartDate())
    self.assertEquals("service_module/slapos_crm_information", 
                      event.getResource())
    self.assertEquals(event.getDestination(), person.getRelativeUrl())
    
    another_support_request = self.portal.support_request_module.newContent(\
            title=title, description=title,
            destination_decision=self.computer.getSourceAdministration(),
            aggregate_value=self.computer.getRelativeUrl())
    another_support_request.validate()
    self.tic()
    
    another_first_event = \
      another_support_request.SupportRequest_trySendNotificationMessage(
        message_title=title, message=text_content,
        destination_relative_url=person.getRelativeUrl())
        
    self.assertNotEqual(another_first_event, None)
    
    self.assertEquals(
      another_support_request.getFollowUpRelatedList(), 
      [another_first_event.getRelativeUrl()])
    
    self.assertEquals(title, another_first_event.getTitle())
    self.assertEquals(text_content, another_first_event.getTextContent())
    self.assertNotEquals(None, another_first_event.getStartDate())
    self.assertEquals("service_module/slapos_crm_information", 
                      another_first_event.getResource())
    self.assertEquals(another_first_event.getDestination(), person.getRelativeUrl())
    self.assertEquals(another_first_event.getFollowUp(),
     another_support_request.getRelativeUrl())



    