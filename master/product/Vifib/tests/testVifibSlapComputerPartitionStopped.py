from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapComputerPartitionStopped(TestVifibSlapWebServiceMixin):
  def test_ComputerPartition_stopped(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_stopped_computer_partition_sequence_string + """

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
        """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_stopped_destroy_requested(self):
    """Checks that stopped does not raise in case if destroy was requested"""
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_stopped_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_stopped_destroy_requested_started(self):
    """Checks that stopped does not raise in case if destroy was requested
    on started one"""
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_started_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionStopped))
  return suite
