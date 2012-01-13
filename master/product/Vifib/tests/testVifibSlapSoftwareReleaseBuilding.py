from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapSoftwareReleaseBuilding(TestVifibSlapWebServiceMixin):
  ########################################
  # SoftwareRelease.building
  ########################################

  def test_SoftwareRelease_building_afterRegister(self):
    """
    Check that calling SoftwareRelease.building after just registration raises a
    NotFoundError
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SelectNewSoftwareReleaseUri \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingAfterRegisterCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_building_SetupResource_ConfirmedState(self):
    """
    Check that calling SoftwareRelease.building works in 
    confirmed state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckStartedPurchasePackingList \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_building_SetupResource_CancelledState(self):
    """
    Check that calling SoftwareRelease.building works in 
    cancelled state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      CancelPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingCall \
      SlapLogout \
      LoginDefaultUser \
      CheckCancelledPurchasePackingList \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_building_SetupResource_StartedState(self):
    """
    Check that calling SoftwareRelease.building works in 
    started state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckStartedPurchasePackingList \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_building_SetupResource_StoppedState(self):
    """
    Check that calling SoftwareRelease.building works in 
    stopped state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      StopPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckStoppedPurchasePackingList \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_building_SetupResource_DeliveredState(self):
    """
    Check that calling SoftwareRelease.building works in 
    delivered state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      StopPurchasePackingList \
      DeliverPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckDeliveredPurchasePackingList \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_building_twoPurchasePackingList(self):
    """
    Check that calling SoftwareRelease.building uses the Purchase Packing List
    in proper state, regardless its date
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_two_purchase_packing_list + '\
      LoginDefaultUser \
      StepPurchasePackingListBStartDateAfterPurchasePackingListA \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckStartedPurchasePackingListB \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_string = self.prepare_two_purchase_packing_list + '\
      LoginDefaultUser \
      StepPurchasePackingListBStartDateBeforePurchasePackingListA \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckStartedPurchasePackingListB \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapSoftwareReleaseBuilding))
  return suite
