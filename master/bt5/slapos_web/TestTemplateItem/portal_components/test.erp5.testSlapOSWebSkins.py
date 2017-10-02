##############################################################################
#
# Copyright (c) 2002-2016 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################


# Copyright (c) 2013 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from Products.ERP5Type.tests.SecurityTestCase import SecurityTestCase
import time

from DateTime import DateTime

class SlapOSWebMixin(testSlapOSMixin, SecurityTestCase):

  def createComputer(self, person=None):
    computer = self.portal.computer_module.newContent(
        portal_type="Computer",
        title="%s Test RSS Computer" % self.new_id)
    computer.edit(source_administration_value=person)
    computer.validate()
    computer.immediateReindexObject()
    computer.updateLocalRolesOnSecurityGroups()
    return computer

  def createHostingSubscription(self, person=None):
    hs = self.portal.hosting_subscription_module.newContent(
        portal_type="Hosting Subscription",
        title="%s Test RSS Hosting Subscription" % self.new_id)
    if person is not None:
      hs.edit(destination_section=person.getRelativeUrl())
    hs.validate()
    hs.immediateReindexObject()
    hs.updateLocalRolesOnSecurityGroups()
    return hs

  def createSupportRequest(self, person, computer=None, validate=1):
    sr = self.portal.support_request_module.newContent(\
                        title="Test Support Request %s" % self.new_id,
                        resource="service_module/slapos_crm_monitoring",
                        destination_decision_value=person)
    if validate:
      sr.validate()

    if computer:
      sr.setAggregateValue(computer)

    sr.immediateReindexObject()
    sr.updateLocalRolesOnSecurityGroups()
    if validate:
      self.assertUserCanAccessDocument(person.getUserId(), sr)
      self.assertUserCanViewDocument(person.getUserId(), sr)

    return sr

  def createUpgradeDecision(self, person, computer=None, validate=1):
    ud = self.portal.upgrade_decision_module.newContent(\
                        title="Upgrade Decision %s" % self.new_id,
                        destination_decision_value=person)
    ud.immediateReindexObject()
    ud.updateLocalRolesOnSecurityGroups()
    # This seems odd, user can see draft SR even he is auditor
    self.assertUserCanAccessDocument(person.getUserId(), ud)
    self.assertUserCanViewDocument(person.getUserId(), ud)

    if computer is not None:
      line = ud.newContent(
         portal_type="Upgrade Decision Line",
         aggregate_value=computer)
      line.immediateReindexObject()
    return ud

  def createRegularisationRequest(self, person, validate=1):
    rr = self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % self.new_id,
      reference="TESTREGREQ-%s" % self.new_id,
      destination_decision_value=person)
    if validate:
      rr.validate()
    rr.immediateReindexObject()
    rr.updateLocalRolesOnSecurityGroups()
    if validate:
      self.assertUserCanAccessDocument(person.getUserId(), rr)
      self.assertUserCanViewDocument(person.getUserId(), rr)

    return rr

  def afterSetUp(self):
    """ bootstrap test """
    self.login()
    self.changeSkin("View")

    if getattr(self, "person", None) is None:
      self.new_id = self.generateNewId()
      self.person = self.makePerson(new_id=self.new_id)
      self.computer = self.createComputer(person=self.person)
      self.hosting_subscription = self.createHostingSubscription(
                                                           person=self.person)
      self.support_request = self.createSupportRequest(self.person,
                                                       computer=self.computer)
      self.upgrade_decision = self.createUpgradeDecision(self.person,
                                                       computer=self.computer)
      self.hs_support_request = self.createSupportRequest(self.person,
                                            computer=self.hosting_subscription)
      self.hs_upgrade_decision = self.createUpgradeDecision(self.person,
                                            computer=self.hosting_subscription)

      self.regularisation_request = self.createRegularisationRequest(
                                                self.person)
      self.cancelled_support_request = self.createSupportRequest(self.person,
                                                        computer=self.computer,
                                                        validate=0)
      self.cancelled_upgrade_decision = self.createUpgradeDecision(self.person,
                                                        computer=self.computer,
                                                        validate=0)
      self.cancelled_regularisation_request = self.createRegularisationRequest(
                          self.person, validate=0)

      self.cancelled_support_request.cancel()
      self.cancelled_upgrade_decision.cancel()
      self.cancelled_regularisation_request.cancel()

    self.tic()

  def _test_WebSection_getUserTicketList(self):
    ticket_list = self.portal.WebSection_getUserTicketList()
    self.assertEquals(len(ticket_list), 5)
    self.assertSameSet([i.getUid() for i in ticket_list],
                       [self.support_request.getUid(),
                        self.upgrade_decision.getUid(),
                        self.regularisation_request.getUid(),
                        self.hs_support_request.getUid(),
                        self.hs_upgrade_decision.getUid()])

  def _test_Base_getOpenRelatedTicketList_computer(self):
    """ Test get Computer RSS """
    self.login()
    ticket_list = self.computer.Base_getOpenRelatedTicketList()
    self.assertSameSet([i.getRelativeUrl() for i in ticket_list],
                       [self.support_request.getRelativeUrl(),
                        self.upgrade_decision.getRelativeUrl()])
    self.assertEquals(len(ticket_list), 2)


  def _test_Base_getOpenRelatedTicketList_hosting_subscription(self):
    """ Test get Hosting Subscription RSS """
    self.login()
    ticket_list = self.hosting_subscription.Base_getOpenRelatedTicketList()

    self.assertSameSet([i.getRelativeUrl() for i in ticket_list],
                       [self.hs_support_request.getRelativeUrl(),
                        self.hs_upgrade_decision.getRelativeUrl()])
    self.assertEquals(len(ticket_list), 2)

class TestSlapOSWebSkin(SlapOSWebMixin):

  def afterSetUp(self):
    super(TestSlapOSWebSkin, self).afterSetUp()
    self.login(self.person.getUserId())
    self.changeSkin("Hosting")

  def test_WebSection_getUserTicketList(self):
    """ Test get User Tickers at Hosting Skin"""
    self._test_WebSection_getUserTicketList()

  def test_WebSection_getUserTicketList_new_support_request(self):
    """ Test get User Tickers at Hosting Skin with new support request """
    self._test_WebSection_getUserTicketList()
    try:
      sr = self.portal.support_request_module.newContent(\
                          title="Test Support Request %s" % self.new_id,
                          resource="service_module/slapos_crm_monitoring",
                          destination_decision_value=self.person)
      self.portal.REQUEST.set("new_support_request", sr.getRelativeUrl())
      ticket_list = self.portal.WebSection_getUserTicketList()
      self.assertEquals(len(ticket_list), 6)
      self.assertSameSet([i.getUid() for i in ticket_list],
                         [self.support_request.getUid(),
                          self.upgrade_decision.getUid(),
                          self.regularisation_request.getUid(),
                          self.hs_support_request.getUid(),
                          self.hs_upgrade_decision.getUid(),
                          sr.getUid()])
      self.assertEquals(ticket_list[0].getUid(), sr.getUid())
    finally:
      transaction.abort()

  def test_Base_getOpenRelatedTicketList_computer(self):
    """ Test Base_getOpenRelatedTicketList with Hosting Subscriptions on Hosting
    """
    self._test_Base_getOpenRelatedTicketList_computer()

  def test_Base_getOpenRelatedTicketList_hosting_subscription(self):
    """ Test Base_getOpenRelatedTicketList with Computer on Hosting
    """
    self._test_Base_getOpenRelatedTicketList_hosting_subscription()

class TestSlapOSRSSSkin(SlapOSWebMixin):

  def afterSetUp(self):
    super(TestSlapOSRSSSkin, self).afterSetUp()
    self.login(self.person.getUserId())
    self.changeSkin("RSS")

  def test_WebSection_getUserTicketList(self):
    """ Test get User Tickers at RSS Skin"""
    self._test_WebSection_getUserTicketList()

  def _test_WebSection_getRSSContent(self, ticket):
    """ Test for get Date and Content for the RSS Feed
    """
    date_content = ticket.WebSection_getRSSDateContent()
    description = ticket.WebSection_getRSSDescriptionContent()

    self.assertEquals(ticket.getModificationDate(), date_content)
    self.assertEquals(ticket.getDescription(), description)

    event = self.portal.event_module.newContent(
      portal_type="Web Message",
      follow_up_value=ticket,
      title="%s Web Message" % ticket.getTitle(),
      text_content="%s Web Message Content" % ticket.getTitle(),
      start_date=DateTime()
      )
    event.immediateReindexObject()
    transaction.commit()

    # Now the event dates and content should be showed instead of the ticket
    self.assertEquals(event.getModificationDate(),
                      ticket.WebSection_getRSSDateContent())
    self.assertEquals(event.getTextContent(),
                      ticket.WebSection_getRSSDescriptionContent())

    # Create another event and check if it continues the same
    new_event = self.portal.event_module.newContent(
      portal_type="Web Message",
      follow_up_value=ticket,
      title="%s New Web Message" % ticket.getTitle(),
      text_content="%s New Web Message Content" % ticket.getTitle(),
      start_date=DateTime()
      )
    new_event.immediateReindexObject()
    transaction.commit()

    # Now the new event dates and content should be showed instead
    self.assertEquals(new_event.getModificationDate(),
                      ticket.WebSection_getRSSDateContent())
    self.assertEquals(new_event.getTextContent(),
                      ticket.WebSection_getRSSDescriptionContent())

    # Catalog table dont index microseconds, so it can cause problems when search
    # sleep 2 second to produce a good modification date.
    time.sleep(2)

    # Modify first event title and check if it takes the lead again.
    event.setTitle("%s Modified Web Message" % ticket.getTitle())
    event.edit(start_date=DateTime())

    event.immediateReindexObject()
    transaction.commit()

    self.assertTrue(event.getModificationDate() > new_event.getModificationDate(),
      "%s is not larger them %s" % (event.getModificationDate(), new_event.getModificationDate()))

    # Now the first event dates and content should be showed instead
    self.assertEquals(event.getTextContent(),
                      ticket.WebSection_getRSSDescriptionContent())

    self.assertEquals(event.getModificationDate(),
                      ticket.WebSection_getRSSDateContent())

  def test_WebSection_getRSSContents_support_request(self):
    """ Test for get Date and Content for the RSS Feed for Support Request
    """
    self._test_WebSection_getRSSContent(self.support_request)

  def test_WebSection_getRSSContents_upgrade_decision(self):
    """ Test for get Date and Content for the RSS Feed for Upgrade Decision
    """
    self._test_WebSection_getRSSContent(self.upgrade_decision)

  def test_WebSection_getRSSContents_regularisation_request(self):
    """ Test for get Date + Content for the RSS Feed for Regularisation Request
    """
    self._test_WebSection_getRSSContent(self.regularisation_request)

  def test_Base_getOpenRelatedTicketList_computer(self):
    """ Test Base_getOpenRelatedTicketList with Computer on RSS """
    self._test_Base_getOpenRelatedTicketList_computer()

  def test_Base_getOpenRelatedTicketList_hosting_subscription(self):
    """ Test Base_getOpenRelatedTicketList with Hosting Subscriptions on RSS """
    self._test_Base_getOpenRelatedTicketList_hosting_subscription()
