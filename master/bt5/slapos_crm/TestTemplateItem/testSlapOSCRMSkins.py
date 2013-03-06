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
    self.assertEquals(ticket.getTitle(),
           'Account regularisation expected for "%s"' % person.getTitle())
    self.assertEquals(event.getPortalType(), 'Mail Message')
    self.assertTrue(event.getStartDate() >= before_date)
    self.assertTrue(event.getStopDate() <= after_date)
    self.assertEquals(event.getTitle(), "Invoice payment requested")
    self.assertEquals(event.getDestination(),
                      person.getRelativeUrl())
    self.assertEquals(event.getSource(),
                      ticket.getSource())
    expected_text_content = """
Dear user,

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

