from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import expectedFailure
import transaction
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapComputerGetSoftwareReleaseList(TestVifibSlapWebServiceMixin):
  ########################################
  # Computer.getSoftwareReleaseList
  ########################################

  # ERP5/Zope does not follow REST API beacuse it is not possible to configure
  # Cookie Crumbler to ignore portal_slap
  @expectedFailure
  def test_Computer_getSoftwareReleaseList_unknowComputerUid(self):
    sequence_list = SequenceList()
    sequence_string = '\
      SlapLoginRandomComputer \
      CheckUnauthorizedComputerGetSoftwareReleaseListCall \
      Tic \
      SlapLogout \
      CheckUnexistingComputer \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  # ERP5/Zope does not follow REST API beacuse it is not possible to configure
  # Cookie Crumbler to ignore portal_slap
  @expectedFailure
  def test_Computer_getSoftwareReleaseList_draftComputer(self):
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      CreateDraftComputer \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckUnauthorizedComputerGetSoftwareReleaseListCall \
      Tic \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_validatedComputer(self):
    """
    Check that getSoftwareReleaseList returns an empty result if the
    validated computer is not related to any packing list.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_validatedAndDraftComputer(self):
    """
    Check that getSoftwareReleaseList returns an empty result if there are
    one draft and one validated computer.
    """
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      CreateDraftComputer \
      Tic \
      Logout '\
      + self.prepare_computer + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  # ERP5/Zope does not follow REST API beacuse it is not possible to configure
  # Cookie Crumbler to ignore portal_slap
  @expectedFailure
  def test_Computer_getSoftwareReleaseList_TwoValidatedComputer(self):
    # XXX: It shall be part of VifibMachineAuthentication test suite
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      LoginDefaultUser \
      DuplicateAndValidateCurrentComputer \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckUnauthorizedComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    try:
      sequence_list.play(self)
    finally:
      self.login('ERP5TypeTestCase')
      for c in self.portal.computer_module.contentValues():
        if c.getValidationState() == 'validated':
          c.invalidate()
          transaction.commit()

  def test_Computer_getSoftwareReleaseList_SetupResource_ConfirmedState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    confirmed state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_SetupResource_CancelledState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    cancelled state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      CancelPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_SetupResource_StartedState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    started state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_SetupResource_StoppedState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    stopped state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      StopPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_SetupResource_DeliveredState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    delivered state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      StopPurchasePackingList \
      Tic \
      DeliverPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_AccountingResource_ConfirmedState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    confirmed state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_software_release_purchase_packing_list_accounting_resource + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_AccountingResource_CancelledState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    cancelled state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_software_release_purchase_packing_list_accounting_resource + '\
      LoginDefaultUser \
      CancelPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_AccountingResource_StartedState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    started state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_software_release_purchase_packing_list_accounting_resource + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_AccountingResource_StoppedState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    stopped state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_software_release_purchase_packing_list_accounting_resource + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      StopPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_AccountingResource_DeliveredState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    delivered state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_software_release_purchase_packing_list_accounting_resource + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      StopPurchasePackingList \
      Tic \
      DeliverPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_twoPurchasePackingList(self):
    """
    Check that calling Computer.getSoftwareReleaseList uses the
    Purchase Packing List in proper state, regardless its date
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_two_purchase_packing_list + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout \
      LoginDefaultUser \
      StepPurchasePackingListBStartDateAfterPurchasePackingListA \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout \
      LoginDefaultUser \
      StepPurchasePackingListBStartDateBeforePurchasePackingListA \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      Tic \
      SlapLogout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_twoActivePurchasePackingList(self):
    """
    Check that getSoftwareReleaseList only returns 1 software release if it is
    associated to 2 purchase packing list.
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      Tic \
      CreatePurchasePackingList \
      Tic \
      CreatePurchasePackingListLine \
      Tic \
      SetPurchasePackingListLineSetupResource \
      SetPurchasePackingListLineAggregate \
      ConfirmPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerGetSoftwareReleaseList))
  return suite
