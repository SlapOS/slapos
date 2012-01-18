from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapComputerPartitionAvailable(TestVifibSlapWebServiceMixin):
  ########################################
  # ComputerPartition.available
  ########################################

  def test_ComputerPartition_available_afterRegister(self):
    """
    Check that calling ComputerPartition.available after just registration raises a
    NotFoundError
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + """
      SlapLoginCurrentComputer
      CheckNotFoundComputerPartitionAvailableAfterRegisterCall
      SlapLogout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_available_successConfirmed(self):
    """
    Check that calling ComputerPartition.available change the sale packing
    list state to stopped.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_installed_computer_partition_sequence_string + """
      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_available_alreadyStartedSalePackingList(self):
    """
    Check that calling ComputerPartition.available more then once can be called
    without error and changes nothing
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_installed_computer_partition_sequence_string + """
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionAvailable))
  return suite
