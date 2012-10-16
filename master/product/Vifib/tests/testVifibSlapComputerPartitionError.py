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
      SlapLoginTestVifibAdmin \
      CustomerRegisterNewComputer \
      Tic \
      SlapLogout \
      LoginTestVifibAdmin \
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
      CleanTic \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionError))
  return suite
