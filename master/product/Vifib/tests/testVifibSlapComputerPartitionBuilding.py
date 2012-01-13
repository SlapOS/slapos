from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapComputerPartitionBuilding(TestVifibSlapWebServiceMixin):
  ########################################
  # ComputerPartition.building
  ########################################

  def test_ComputerPartition_building_afterRegister(self):
    """
    Check that calling ComputerPartition.building after just registration raises a
    NotFoundError
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      CheckNotFoundComputerPartitionBuildingAfterRegisterCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_building_success(self):
    """
    Check that calling ComputerPartition.building change the sale packing
    list state to started.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_building_computer_partition_sequence_string + """
      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_building_alreadyConfirmedSalePackingList(self):
    """
    Check that calling ComputerPartition.building failed if there is already
    confirmed sale packing list
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_building_computer_partition_sequence_string + """
      SlapLoginCurrentComputer
      SoftwareInstanceBuilding
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListStarted
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionBuilding))
  return suite
