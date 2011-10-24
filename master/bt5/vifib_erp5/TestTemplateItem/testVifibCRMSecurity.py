##############################################################################
#
# Copyright (c) 2011 Nexedi SA and Contributors. All Rights Reserved.
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

from VifibMixin import testVifibMixin
from AccessControl import Unauthorized
from Products.ERP5Type.tests.SecurityTestCase import SecurityTestCase

sale_login_id = 'test_sale_agent'
member_login_id = 'test_vifib_customer'

class TestVifibCRMSecurity(testVifibMixin, SecurityTestCase):
  def getTitle(self):
    return "Vifib CRM Security"

  def test_CampaignSecurity(self):
    """
    Sale division should be able to manage campaign.
    Anonymous/member has no permission to any campaign.
    """
    # Sale division
    self.login(user_name=sale_login_id)
    # Try to acceed the campaign module through restrictedTraverse
    # This will test the security of the module
    campaign_module_id = self.portal.getDefaultModuleId(portal_type='Campaign')
    campaign_module = self.portal.restrictedTraverse(campaign_module_id)
    # Add campaign
    campaign = campaign_module.newContent(portal_type='Campaign')
    # Edit the campaign
    campaign.edit(
      title='Test Vifib Campaign',
    )
    campaign_relative_url = campaign.getRelativeUrl()
    self.stepTic()
    self.assertEquals(1, len(self.portal.portal_catalog(
      relative_url=campaign_relative_url)))
    # XXX TODO: test real CRM use case related to the security
    self.assertUserHaveRoleOnDocument(sale_login_id, "Assignor", campaign)
    self.logout()

    # Member
    self.login(user_name=member_login_id)
    self.assertRaises(Unauthorized,
                      self.portal.restrictedTraverse,
                      [campaign_module_id]
    )
    self.assertEquals(0, len(self.portal.portal_catalog(
      relative_url=campaign_relative_url)))
    self.logout()

    # Anonymous
    self.assertRaises(Unauthorized,
                      self.portal.restrictedTraverse,
                      [campaign_module_id]
    )
    self.assertEquals(0, len(self.portal.portal_catalog(
      relative_url=campaign_relative_url)))

  def test_SupportRequestSecurity(self):
    """
    Sale division should be able to manage support request.
    Anonymous/member has no permission to any support request.
    """
    # Sale division
    self.login(user_name=sale_login_id)
    # Try to acceed the support_request module through restrictedTraverse
    # This will test the security of the module
    support_request_module_id = self.portal.getDefaultModuleId(
      portal_type='Support Request')
    support_request_module = self.portal.restrictedTraverse(
        support_request_module_id)
    # Add support_request
    support_request = support_request_module.newContent(
      portal_type='Support Request')
    # Edit the support_request
    support_request.edit(
      title='Test Vifib Support Request',
    )
    support_request_relative_url = support_request.getRelativeUrl()
    self.stepTic()
    self.assertEquals(1, len(self.portal.portal_catalog(
      relative_url=support_request_relative_url)))
    # XXX TODO: test real CRM use case related to the security
    self.assertUserHaveRoleOnDocument(sale_login_id, "Assignor",
                                      support_request)
    self.logout()

    # Member
    self.login(user_name=member_login_id)
    self.assertRaises(Unauthorized,
                      self.portal.restrictedTraverse,
                      [support_request_module_id]
    )
    self.assertEquals(0, len(self.portal.portal_catalog(
      relative_url=support_request_relative_url)))
    self.logout()

    # Anonymous
    self.assertRaises(Unauthorized,
                      self.portal.restrictedTraverse,
                      [support_request_module_id]
    )
    self.assertEquals(0, len(self.portal.portal_catalog(
      relative_url=support_request_relative_url)))

  def test_NotificationMessageSecurity(self):
    """
    Sale division should be able to manage notification message.
    Anonymous/member has no permission to any notification message.
    """
    # Sale division
    self.login(user_name=sale_login_id)
    # Try to acceed the notification_message module through restrictedTraverse
    # This will test the security of the module
    notification_message_module_id = self.portal.getDefaultModuleId(
      portal_type='Notification Message')
    notification_message_module = self.portal.restrictedTraverse(
      notification_message_module_id)
    # Add notification_message
    notification_message = notification_message_module.newContent(
      portal_type='Notification Message')
    # Edit the notification_message
    notification_message.edit(
      title='Test Vifib Notification Message',
    )
    notification_message_relative_url = notification_message.getRelativeUrl()
    self.stepTic()
    self.assertEquals(1, len(self.portal.portal_catalog(
      relative_url=notification_message_relative_url)))
    # XXX TODO: test real CRM use case related to the security
    self.assertUserHaveRoleOnDocument(sale_login_id, "Assignor",
                                      notification_message)
    self.logout()

    # Member
    self.login(user_name=member_login_id)
    self.assertRaises(Unauthorized,
                      self.portal.restrictedTraverse,
                      [notification_message_module_id]
    )
    self.assertEquals(0, len(self.portal.portal_catalog(
      relative_url=notification_message_relative_url)))
    self.logout()

    # Anonymous
    self.assertRaises(Unauthorized,
                      self.portal.restrictedTraverse,
                      [notification_message_module_id]
    )
    self.assertEquals(0, len(self.portal.portal_catalog(
      relative_url=notification_message_relative_url)))

  def test_EventSecurity(self):
    """
    Sale division should be able to manage event.
    Anonymous/member has no permission to any event.
    """
    # Sale division
    self.login(user_name=sale_login_id)
    # Try to acceed the event module through restrictedTraverse
    # This will test the security of the module
    event_module_id = self.portal.getDefaultModuleId(
      portal_type='Fax Message')
    event_module = self.portal.restrictedTraverse(
      event_module_id)
    self.logout()

    for portal_type in self.portal.getPortalEventTypeList():
      # Sale division
      self.login(user_name=sale_login_id)

      # Add event
      event = event_module.newContent(
        portal_type=portal_type)
      # Edit the event
      event.edit(
        title='Test Vifib %s' % portal_type,
      )
      event_relative_url = event.getRelativeUrl()
      self.stepTic()
      self.assertEquals(1, len(self.portal.portal_catalog(
        relative_url=event_relative_url)))
      # XXX TODO: test real CRM use case related to the security
      self.assertUserHaveRoleOnDocument(sale_login_id, "Assignor", event)
      self.logout()

      # Member
      self.login(user_name=member_login_id)
      self.assertRaises(Unauthorized,
                        self.portal.restrictedTraverse,
                        [event_module_id]
      )
      self.assertEquals(0, len(self.portal.portal_catalog(
        relative_url=event_relative_url)))
      self.logout()

      # Anonymous
      self.assertRaises(Unauthorized,
                        self.portal.restrictedTraverse,
                        [event_module_id]
      )
      self.assertEquals(0, len(self.portal.portal_catalog(
        relative_url=event_relative_url)))

  def test_PersonSecurity(self):
    """
    Sale division should be able to manage person.
    """
    # Sale division
    self.login(user_name=sale_login_id)
    # Try to acceed the person module through restrictedTraverse
    # This will test the security of the module
    person_module_id = self.portal.getDefaultModuleId(
      portal_type='Person')
    person_module = self.portal.restrictedTraverse(
      person_module_id)

    # Add person
    person = person_module.newContent(
      portal_type="Person")
    # Edit the person
    person.edit(
      title='Test Vifib Person'
    )
    person_relative_url = person.getRelativeUrl()
    self.stepTic()
    self.assertEquals(1, len(self.portal.portal_catalog(
      relative_url=person_relative_url)))
    # XXX TODO: test real CRM use case related to the security
    self.assertUserHaveRoleOnDocument(sale_login_id, "Assignor", person)
    self.logout()

  def test_OrganisationSecurity(self):
    """
    Sale division should be able to manage organisation.
    """
    # Sale division
    self.login(user_name=sale_login_id)
    # Try to acceed the organisation module through restrictedTraverse
    # This will test the security of the module
    organisation_module_id = self.portal.getDefaultModuleId(
      portal_type='Organisation')
    organisation_module = self.portal.restrictedTraverse(
      organisation_module_id)

    # Add organisation
    organisation = organisation_module.newContent(
      portal_type="Organisation")
    # Edit the organisation
    organisation.edit(
      title='Test Vifib Organisation'
    )
    organisation_relative_url = organisation.getRelativeUrl()
    self.stepTic()
    self.assertEquals(1, len(self.portal.portal_catalog(
      relative_url=organisation_relative_url)))
    # XXX TODO: test real CRM use case related to the security
    self.assertUserHaveRoleOnDocument(sale_login_id, "Assignor", organisation)
    self.logout()

