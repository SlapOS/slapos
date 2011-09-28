from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapComputerPartitionGetSoftwareRelease(TestVifibSlapWebServiceMixin):
  ########################################
  # ComputerPartition.getSoftwareRelease
  ########################################

  def test_ComputerPartition_getSoftwareRelease_afterRegister(self):
    """
    Check that calling ComputerPartition.getSoftwareRelease after just 
    registration raises a NotFoundError
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      CheckNotFoundComputerPartitionGetSoftwareReleaseAfterRegisterCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getSoftwareRelease_confirmedState(self):
    """
    Check that calling ComputerPartition.getSoftwareRelease works in 
    confirmed state
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionGetSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getSoftwareRelease_cancelledState(self):
    """
    Check that calling ComputerPartition.getSoftwareRelease works in 
    cancelled state
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      LoginDefaultUser \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionGetSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getSoftwareRelease_startedState(self):
    """
    Check that calling ComputerPartition.getSoftwareRelease works in 
    started state
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_building_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionGetSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getSoftwareRelease_stoppedState(self):
    """
    Check that calling ComputerPartition.getSoftwareRelease works in 
    stopped state
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_installed_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionGetSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getSoftwareRelease_twoSalePackingList(self):
    """
    Check that calling ComputerPartition.getSoftwareRelease    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + '\
      LoginDefaultUser \
      CheckPackingListAmountTwoComputerPartition \
      SetHostingAfterSetupStartDate \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionGetSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionGetSoftwareRelease))
  return suite
