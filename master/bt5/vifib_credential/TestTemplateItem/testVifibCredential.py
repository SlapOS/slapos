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

  def createCredentialRequest(self,
                              first_name="Gabriel",
                              last_name="Monnerat",
                              reference="gabriel",
                              password="123",
                              default_email_text="gabriel@test.com"):
    self.logout()
    self.portal.ERP5Site_registerCredentialRequest(first_name=first_name,
                                                   last_name=last_name,
                                                   reference=reference,
                                                   password=password,
                                                   career_subordination_title="",
                                                   default_email_text=default_email_text,
                                                   default_telephone_text="223344",
                                                   default_address_street_address="Test Street",
                                                   default_address_city="Campos",
                                                   default_address_zip_code="28024030")
    self.login("ERP5TypeTestCase")
    self.stepTic()

  def createSystemPreference(self):
    """ """
    portal_preferences = self.getPreferenceTool()
    preference = portal_preferences.newContent(portal_type='System Preference',
                                               title='Default Site Preference',
                                               id='test_site_preference')
    self.stepTic()
    return preference
    
  def afterSetUp(self):
    """ """
    portal_preferences = self.getPreferenceTool()
    preference = getattr(portal_preferences, 'test_site_preference', None)
    if preference is None:
      preference = self.createSystemPreference()
    if preference.getPreferenceState() == 'disabled':
       preference.enable()
    preference.edit(preferred_credential_request_automatic_approval=True,
                    preferred_credential_recovery_automatic_approval=True,
                    preferred_organisation_credential_update_automatic_approval=True,
                    preferred_person_credential_update_automatic_approval=True)
    self.portal.email_from_address = 'site@example.invalid'
    oldMailHost = getattr(self.portal, 'MailHost', None)		 
    if oldMailHost is not None:		 
      self.portal.manage_delObjects(['MailHost'])		 
      self.portal._setObject('MailHost', DummyMailHost('MailHost'))

    self.stepTic()

  def testMailMessagePosted(self):
    """ Test if the Mail Message was posted correctly """
    self.createCredentialRequest(reference="vifibtest")
    portal_catalog = self.portal.portal_catalog
    credential_request = portal_catalog.getResultValue(portal_type="Credential Request", 
                                                       reference="vifibtest")    
    mail_message = portal_catalog.getResultValue(portal_type="Mail Message",
                                                 follow_up=credential_request)
    self.assertEquals(mail_message.getSimulationState(), "started")
    self.assertTrue("key=%s" % mail_message.getReference() in mail_message.getTextContent())   

  def test_MailFromMailMessageEvent(self):
    """ """
    self.createCredentialRequest(first_name="Vifib", 
                                 last_name="Test",
                                 reference="vifibtest")
    portal_catalog = self.portal.portal_catalog
    credential_request = portal_catalog.getResultValue(portal_type="Credential Request", 
                                                       reference="vifibtest",
                                                       first_name="Vifib",
                                                       last_name="Test")
    mail_message = portal_catalog.getResultValue(portal_type="Mail Message",
                                                 follow_up=credential_request)
    last_message = self.portal.MailHost._last_message
    self.assertNotEquals((), last_message)
    mfrom, mto, message_text = last_message
    self.assertEquals(mfrom, 'Portal Administrator <site@example.invalid>')
    self.assertEquals(['Vifib Test <gabriel@test.com>'], mto)
    self.assertNotEquals(re.search("Subject\:.*Welcome_to_Vifib", message_text), None)
    self.assertNotEquals(re.search("Hello\ Vifib\ Test\,", message_text), None)
    self.assertNotEquals(re.search("key\=..%s" % mail_message.getReference(), message_text), None)

  def testERP5Site_activeLogin(self):
    """ Test if the script WebSection_activeLogin will create one user
    correctly """
    self.createCredentialRequest()
    portal_catalog = self.portal.portal_catalog
    credential_request = portal_catalog.getResultValue(portal_type="Credential Request", 
                                                       reference="gabriel")
    mail_message = portal_catalog.getResultValue(portal_type="Mail Message",
                                                 follow_up=credential_request)
    self.logout()
    self.portal.ERP5Site_activeLogin(mail_message.getReference())
    self.login("ERP5TypeTestCase")
    self.stepTic()
    person = portal_catalog.getResultValue(reference="gabriel", portal_type="Person")
    self.assertEquals(person.getValidationState(), "validated")

  def testERP5Site_registerCredentialRequest(self):
    """ Test if the script ERP5Site_registerCredentialRequest will create one
    Credential Request correctly """
    self.createCredentialRequest()
    portal_catalog = self.portal.portal_catalog
    credential_request = portal_catalog.getResultValue(portal_type="Credential Request", 
                                                       reference="gabriel")
    self.assertEquals(credential_request.getFirstName(), "Gabriel")
    self.assertEquals(credential_request.getDefaultEmailText(), "gabriel@test.com")
