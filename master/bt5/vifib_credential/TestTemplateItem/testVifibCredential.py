##############################################################################
#
# Copyright (c) 2002-2011 Nexedi SA and Contributors. All Rights Reserved.
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

import re
from Products.ERP5Type.tests.utils import DummyMailHost
from VifibMixin import testVifibMixin

class TestVifibCredential(testVifibMixin):
  """ Tests to validate all features of vifib_credential """

  def getTitle(self):
    return "VifibCredentialTest"

  def getBusinessTemplateList(self):
    """ It extends the bt5 list to add the erp5_credential in list """
    result_list = super(TestVifibCredential, self).getBusinessTemplateList()
    result_list.append("vifib_credential")
    return result_list

  def stepSetCredentialRequestAutomaticApprovalPreferences(self):
    self.setSystemPreference()
    default_system_preference = self.portal.portal_preferences.restrictedTraverse(self.getDefaultSitePreferenceId())
    self.login("ERP5TypeTestCase")
    default_system_preference.edit(preferred_credential_request_automatic_approval=True)
    self.logout()

  def stepValidateNotificationMessage(self):
    module = self.portal.notification_message_module
    reference = "crendential_request-confirmation-without-password"
    search_result = module.searchFolder(reference=reference)
    [notification.getObject().validate() for notification in search_result]

  def testBase_getDefaultAssignmentArgumentDict(self):
    self.stepValidateNotificationMessage()
    self.stepSetCredentialRequestAutomaticApprovalPreferences()
    self.logout()
    portal_catalog = self.portal.portal_catalog
    self.portal.ERP5Site_registerCredentialRequest(first_name="Vifib",
                                                   last_name="Test",
                                                   reference="vifib_test",
                                                   password="vifib",
                                                   career_subordination_title="",
                                                   default_email_text="vifib@vifib.com",
                                                   default_telephone_text="223344",
                                                   default_address_street_address="Test Street",
                                                   default_address_city="My Street",
                                                   default_address_zip_code="28024030")
    self.login("ERP5TypeTestCase")
    self.stepTic()
    credential_request = portal_catalog.getResultValue(portal_type="Credential Request",
                                                       reference="vifib_test")
    mail_message = portal_catalog.getResultValue(portal_type="Mail Message",
                                                 follow_up=credential_request)
    self.logout()
    self.portal.ERP5Site_activeLogin(mail_message.getReference())
    self.login("ERP5TypeTestCase")
    self.stepTic()
    person = portal_catalog.getResultValue(reference="vifib_test", portal_type="Person")
    assignment_list = person.objectValues(portal_type="Assignment")
    assignment = assignment_list[0]
    self.assertEquals(assignment.getFunction(), "customer")
    self.assertEquals(assignment.getRole(), "client")
