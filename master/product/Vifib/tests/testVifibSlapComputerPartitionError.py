from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapComputerPartitionError(TestVifibSlapWebServiceMixin):
  ########################################
  # ComputerPartition.error
  ########################################

  def test_ComputerPartition_error_afterRegister(self):
    """
    Check that calling ComputerPartition.error after just registration raises a
    NotFoundError
    """
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      CustomerRegisterNewComputer \
      Tic \
      SetComputerCoordinatesFromComputerTitle \
      ComputerSetAllocationScopeOpenPublic \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      FormatComputer \
      Tic \
      SlapLogout \
      Tic \
      SlapLoginCurrentComputer \
      CheckNotFoundComputerPartitionErrorAfterRegisterCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_SetupResource_CancelledState(self):
    """
    Check that calling ComputerPartition.error works in
    cancelled state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      LoginDefaultUser \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_SetupResource_ConfirmedState(self):
    """
    Check that calling ComputerPartition.error works in 
    confirmed state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_installed_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_SetupResource_StartedState(self):
    """
    Check that calling ComputerPartition.error works in 
    started state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_building_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_SetupResource_StoppedState(self):
    """
    Check that calling ComputerPartition.error works in 
    stopped state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_installed_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_SetupResource_DeliveredState(self):
    """
    Check that calling ComputerPartition.error works in 
    delivered state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_installed_computer_partition_sequence_string + '\
      LoginDefaultUser \
      DeliverSalePackingList \
      Tic \
      CheckComputerPartitionInstanceSetupSalePackingListDelivered \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_HostingResource_ConfirmedState(self):
    """
    Check that calling ComputerPartition.error works in 
    confirmed state with the hosting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_start_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_HostingResource_StartedState(self):
    """
    Check that calling ComputerPartition.error works in 
    started state with the hosting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_HostingResource_StoppedState(self):
    """
    Check that calling ComputerPartition.error works in 
    stopped state with the hosting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_stop_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_HostingResource_DeliveredState(self):
    """
    Check that calling ComputerPartition.error works in 
    delivered state with the hosting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_stopped_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_HostingResource_CancelledState(self):
    """
    Check that calling ComputerPartition.error works in 
    cancelled state with the hosting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_start_requested_computer_partition_sequence_string + '\
      LoginDefaultUser \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_CleanupResource_ConfirmedState(self):
    """
    Check that calling ComputerPartition.error works in 
    confirmed state with the cleanup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_confirmed_cleanup_resource_packing_list + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      CheckConfirmedSalePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_CleanupResource_CancelledState(self):
    """
    Check that calling ComputerPartition.error works in 
    cancelled state with the cleanup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_confirmed_cleanup_resource_packing_list + '\
      LoginDefaultUser \
      CancelSalePackingList \
      Tic \
      CheckComputerPartitionInstanceCleanupSalePackingListCancelled \
      Logout \
      SlapLoginCurrentComputer \
      CheckSoftwareReleaseErrorCall \
      SlapLogout \
      LoginDefaultUser \
      SelectCurrentlyUsedSalePackingListUid \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_CleanupResource_StartedState(self):
    """
    Check that calling ComputerPartition.error works in 
    started state with the cleanup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_confirmed_cleanup_resource_packing_list + '\
      LoginDefaultUser \
      StartSalePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      SlapLogout \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      CheckStartedSalePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_CleanupResource_StoppedState(self):
    """
    Check that calling ComputerPartition.error works in 
    stopped state with the cleanup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_confirmed_cleanup_resource_packing_list + '\
      LoginDefaultUser \
      StartSalePackingList \
      StopSalePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      SlapLogout \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      CheckStoppedSalePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_CleanupResource_DeliveredState(self):
    """
    Check that calling ComputerPartition.error works in
    delivered state with the cleanup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_confirmed_cleanup_resource_packing_list + '\
      LoginDefaultUser \
      StartSalePackingList \
      StopSalePackingList \
      DeliverSalePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckNotFoundComputerPartitionErrorCall \
      SlapLogout \
      LoginDefaultUser \
      CheckSalePackingListNoErrorText \
      CheckDeliveredSalePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_AccountingResource_ConfirmedState(self):
    """
    Check that calling ComputerPartition.error works in 
    confirmed state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer_partition_accounting_resource_sequence_string + '\
      LoginDefaultUser \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSoftwareReleaseErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckSalePackingListNoErrorText \
      SelectCurrentlyUsedSalePackingListUid \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_AccountingResource_CancelledState(self):
    """
    Check that calling ComputerPartition.error works in 
    cancelled state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer_partition_accounting_resource_sequence_string + '\
      LoginDefaultUser \
      CancelSalePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSoftwareReleaseErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckSalePackingListNoErrorText \
      CheckCancelledSalePackingList \
      SelectCurrentlyUsedSalePackingListUid \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_AccountingResource_StartedState(self):
    """
    Check that calling ComputerPartition.error works in 
    started state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer_partition_accounting_resource_sequence_string + '\
      LoginDefaultUser \
      StartSalePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSoftwareReleaseErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckSalePackingListNoErrorText \
      CheckStartedSalePackingList \
      SelectCurrentlyUsedSalePackingListUid \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_AccountingResource_StoppedState(self):
    """
    Check that calling ComputerPartition.error works in 
    stopped state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer_partition_accounting_resource_sequence_string + '\
      LoginDefaultUser \
      StartSalePackingList \
      StopSalePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSoftwareReleaseErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckSalePackingListNoErrorText \
      CheckStoppedSalePackingList \
      SelectCurrentlyUsedSalePackingListUid \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_AccountingResource_DeliveredState(self):
    """
    Check that calling ComputerPartition.error works in 
    delivered state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer_partition_accounting_resource_sequence_string + '\
      LoginDefaultUser \
      StartSalePackingList \
      StopSalePackingList \
      DeliverSalePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSoftwareReleaseErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckSalePackingListNoErrorText \
      CheckDeliveredSalePackingList \
      SelectCurrentlyUsedSalePackingListUid \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_error_twoSalePackingList(self):
    """
    Check that calling ComputerPartition.error uses the latest sale packing
    list for calculation
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_start_requested_computer_partition_sequence_string + '\
      LoginDefaultUser \
      SetHostingAfterSetupStartDate \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      LoginDefaultUser \
      CheckSalePackingListNoErrorText \
      SetHostingBeforeSetupStartDate \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckSalePackingListErrorText \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionError))
  return suite
