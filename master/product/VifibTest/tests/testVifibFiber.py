# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import unittest
from DateTime import DateTime
from VifibSecurityMixin import testVifibSecurityMixin
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import skip

class TestVifibFiberSubscription(testVifibSecurityMixin):
  """Class for test global registration processus"""

  def createVifibDocumentList(self):
    """Create vifib document"""
    
    #Add a valid vifib support
    self.logMessage("Create Support")
    module = self.portal.getDefaultModule("Organisation")
    organisation = module.newContent(portal_type="Organisation",
                                     reference="vifib-support")
    organisation.validate()

    #Install website
    self.logMessage("Install Websites")
    self.portal.portal_skins.vifib_web.WebSite_install()

    #Add Proxy Role
    workflow = self.portal.portal_workflow.document_conversion_interaction_workflow
    sc_wf = getattr(workflow,"scripts")
    python_script = sc_wf.get("updateContentMd5")
    python_script.manage_proxy(roles=["Manager"])  

  def modifyFiberRequestState(self,transition_name,sequence,fiber_request=None):
    """
      Calls the workflow for the fiber request
    """ 
    if fiber_request is None:
      fiber_request_url = sequence.get("fiber_request_url")
      fiber_request = self.getPortal().restrictedTraverse(fiber_request_url)

    #Do the workflow action
    fiber_request.portal_workflow.doActionFor(fiber_request, transition_name) 

  def stepSetFiberSkin(self, sequence=None, sequence_list=None, **kw):
    """
      Change current Skin
    """
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin("Fiber")
    request.set('portal_skin', "Fiber")

  def stepCallNewFiberRequestDialog(self, sequence=None, sequence_list=None, **kw):
    """Check access to the new free fiber request dialog"""
    self.portal.WebSection_viewNewFreeFiberRequestDialog()

  def stepCreateFiberRequest(self, sequence=None, sequence_list=None, **kw):
    """Create a free fiber request"""

    #Create new request
    self.portal.WebSection_newFreeFiberRequest(
                          dialog_id="WebSection_viewNewFreeFiberRequestDialog",
                          first_name="Test", 
                          last_name="Vifib", 
                          address_city="Cloud", 
                          address_street_address="First", 
                          address_zip_code=0000, 
                          default_birthplace_address_city="Nexedi", 
                          default_email_text="test.toto@vifib.test", 
                          internet_service_provider="Free", 
                          start_date=DateTime(), 
                          telephone_text="0320707288")
  
  def stepFindPendingFiberRequest(self, sequence=None, sequence_list=None, **kw):
    """Find pending request in sequence like in the workflow list"""

    pending_request_list = self.portal.portal_catalog(
                          validation_state="pending",
                          portal_type="Free Fiber Request",
                          title="Test Vifib",
                          sort_on=[('creation_date','descending')])

    #Set the last fiber request in the sequence
    self.assertTrue(len(pending_request_list) > 0)
    fiber_request = pending_request_list[0]
    sequence.edit(fiber_request_url=fiber_request.getRelativeUrl())

  def stepStartFiberRequest(self,sequence=None,sequence_list=None, **kw):
    """Start the fiber request present in sequence"""

    fiber_request_url = sequence.get("fiber_request_url")
    fiber_request = self.getPortal().restrictedTraverse(fiber_request_url)

    self.modifyFiberRequestState("start_action",sequence,fiber_request)
    self.assertEquals(fiber_request.getValidationState(), 'started') 

  def stepConfirmFiberRequest(self,sequence=None,sequence_list=None, **kw):
    """Confirm the fiber request present in sequence"""
    fiber_request_url = sequence.get("fiber_request_url")
    fiber_request = self.getPortal().restrictedTraverse(fiber_request_url)
    fiber_request.setGender("mister")
    self.modifyFiberRequestState("confirm_action",sequence,fiber_request)
    self.assertEquals(fiber_request.getValidationState(), 'confirmed') 

  def stepRefuseFiberRequest(self,sequence=None,sequence_list=None, **kw):
    """Refuse the fiber request present in sequence"""
    fiber_request_url = sequence.get("fiber_request_url")
    fiber_request = self.getPortal().restrictedTraverse(fiber_request_url)

    self.modifyFiberRequestState("refuse_action",sequence,fiber_request)
    self.assertEquals(fiber_request.getValidationState(), 'refused') 

  def stepRetractFiberRequest(self,sequence=None,sequence_list=None, **kw):
    """Retract the fiber request present in sequence"""
    fiber_request_url = sequence.get("fiber_request_url")
    fiber_request = self.getPortal().restrictedTraverse(fiber_request_url)

    self.modifyFiberRequestState("retract_action",sequence,fiber_request)
    self.assertEquals(fiber_request.getValidationState(), 'retracted') 

  def stepContactFiberRequest(self,sequence=None,sequence_list=None, **kw):
    """Contact the fiber request present in sequence"""
    fiber_request_url = sequence.get("fiber_request_url")
    fiber_request = self.getPortal().restrictedTraverse(fiber_request_url)

    self.modifyFiberRequestState("contact_action",sequence,fiber_request)
    self.assertEquals(fiber_request.getValidationState(), 'contacted') 

  def stepAcceptFiberRequest(self,sequence=None,sequence_list=None, **kw):
    """Accept the fiber request present in sequence"""
    fiber_request_url = sequence.get("fiber_request_url")
    fiber_request = self.getPortal().restrictedTraverse(fiber_request_url)

    self.modifyFiberRequestState("accept_action",sequence,fiber_request)
    self.assertEquals(fiber_request.getValidationState(), 'accepted') 

  def test_01_AnonymousCanCreateFiberRequest(self):
    """Anonymous Fiber Request creation"""
    sequence_list = SequenceList()
    sequence_string =  'stepSetFiberSkin \
                        stepLogout  \
                        stepCallNewFiberRequestDialog \
                        stepCreateFiberRequest \
                        stepTic \
                       '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_02_ManagerFindPendingFiberRequest(self):
    """Search request in pending list"""
    sequence_list = SequenceList()
    sequence_string =  'stepSetFiberSkin \
                        stepLogout  \
                        stepCreateFiberRequest \
                        stepTic \
                        stepLoginAsManager \
                        stepFindPendingFiberRequest \
                       '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_03_StaffCanConfirmPendingRequest(self):
    """Check confirmation of pending request"""   
    sequence_list = SequenceList()
    sequence_string =  'stepSetFiberSkin \
                        stepLogout \
                        stepCreateFiberRequest \
                        stepTic \
                        stepLoginAsManager \
                        stepFindPendingFiberRequest \
                        stepConfirmFiberRequest \
                       '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)


  def test_04_StaffCanRefusePendingRequest(self):
    """Check we can refuse instead of confirm a request"""   
    sequence_list = SequenceList()
    sequence_string =  'stepSetFiberSkin \
                        stepLogout \
                        stepCreateFiberRequest \
                        stepTic \
                        stepLoginAsManager \
                        stepFindPendingFiberRequest \
                        stepRefuseFiberRequest \
                       '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_05_StaffCanContactConfirmedRequest(self):
    """Next the confirmation, we cantact the person"""
    sequence_list = SequenceList()
    sequence_string =  'stepSetFiberSkin \
                        stepLogout \
                        stepCreateFiberRequest \
                        stepTic \
                        stepLoginAsManager \
                        stepFindPendingFiberRequest \
                        stepConfirmFiberRequest \
                        stepContactFiberRequest \
                       '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)


  def test_06_StaffCanRetractConfirmedRequest(self):
    """Instead of contact a person, we can retract the request"""
    sequence_list = SequenceList()
    sequence_string =  'stepSetFiberSkin \
                        stepLogout \
                        stepCreateFiberRequest \
                        stepTic \
                        stepLoginAsManager \
                        stepFindPendingFiberRequest \
                        stepConfirmFiberRequest \
                        stepRetractFiberRequest \
                        stepTic \
                       '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_07_StaffCanAcceptContactedRequest(self):
    """Contact was successfull, we accept the request"""
    sequence_list = SequenceList()
    sequence_string =  'stepSetFiberSkin \
                        stepLogout \
                        stepCreateFiberRequest \
                        stepTic \
                        stepLoginAsManager \
                        stepFindPendingFiberRequest \
                        stepConfirmFiberRequest \
                        stepContactFiberRequest \
                        stepAcceptFiberRequest \
                        stepTic \
                       '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_08_StaffCanRetractContactedRequest(self):
    """Cantact was unsuccessfull, we retract the request"""
    sequence_list = SequenceList()
    sequence_string =  'stepSetFiberSkin \
                        stepLogout \
                        stepCreateFiberRequest \
                        stepTic \
                        stepLoginAsManager \
                        stepFindPendingFiberRequest \
                        stepConfirmFiberRequest \
                        stepContactFiberRequest \
                        stepRetractFiberRequest \
                        stepTic \
                       '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_09_StaffCanRetractAcceptedRequest(self):
    """After accept a request, we are able to retract us."""
    sequence_list = SequenceList()
    sequence_string =  'stepSetFiberSkin \
                        stepLogout \
                        stepCreateFiberRequest \
                        stepTic \
                        stepLoginAsManager \
                        stepFindPendingFiberRequest \
                        stepConfirmFiberRequest \
                        stepContactFiberRequest \
                        stepAcceptFiberRequest \
                        stepRetractFiberRequest \
                        stepTic \
                       '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)


class TestVifibFiberSecurityRules(testVifibSecurityMixin):
  """Test if security rules are correctly set"""

  @skip('Test must be written')
  def test_01_AnonymousCanAccessPublishedWebPage(self):
    pass

def test_suite():
  """Define tests may be run"""
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibFiberSubscription))
  suite.addTest(unittest.makeSuite(TestVifibFiberSecurityRules))

  return suite
