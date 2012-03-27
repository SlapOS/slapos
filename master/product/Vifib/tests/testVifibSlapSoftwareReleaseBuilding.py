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
      CheckSoftwareReleaseUnavailableForRequest \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_building_SetupResource_ConfirmedState_CleanupResource_ConfirmedState(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      CheckSoftwareReleaseUnavailableForRequest \
      SetCurrentPurchasePackingListAsA \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout ' + self.prepare_software_release_cleanup_confirmed_packing_list + '\
      LoginDefaultUser \
      SetCurrentPurchasePackingListAsB \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      CheckDestroyedStateGetSoftwareReleaseListCall \
      CheckSuccessSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckSoftwareReleaseUnavailableForRequest \
      CheckStartedPurchasePackingListA \
      CheckConfirmedPurchasePackingListB \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      CheckDestroyedStateGetSoftwareReleaseListCall \
      CheckSuccessSoftwareReleaseDestroyedCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckSoftwareReleaseUnavailableForRequest \
      CheckDeliveredPurchasePackingListA \
      CheckDeliveredPurchasePackingListB \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_building_CleanupResource_ConfirmedState(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_cleanup_purchase_packing_list + '\
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
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
      CheckSoftwareReleaseUnavailableForRequest \
      Logout \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingCall \
      SlapLogout \
      LoginDefaultUser \
      CheckCancelledPurchasePackingList \
      CheckSoftwareReleaseUnavailableForRequest \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_building_CleanupResource_CancelledState(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_cleanup_purchase_packing_list + '\
      LoginDefaultUser \
      CancelPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
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
      CheckSoftwareReleaseUnavailableForRequest \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckStartedPurchasePackingList \
      CheckSoftwareReleaseUnavailableForRequest \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_building_CleanupResource_StartedState(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_cleanup_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
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
      CheckSoftwareReleaseAvailableForRequest \
      Logout \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckStoppedPurchasePackingList \
      CheckSoftwareReleaseAvailableForRequest \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_building_CleanupResource_StoppedState(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_cleanup_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      StopPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
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
      CheckSoftwareReleaseUnvailableForRequest \
      Logout \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckDeliveredPurchasePackingList \
      CheckSoftwareReleaseUnvailableForRequest \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_building_CleanupResource_DeliveredState(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_cleanup_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      StopPurchasePackingList \
      Tic \
      DeliverPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingCall \
      Tic \
      SlapLogout \
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
