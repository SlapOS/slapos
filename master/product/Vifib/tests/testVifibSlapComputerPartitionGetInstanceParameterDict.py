from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapComputerPartitionGetInstanceParameterDict(TestVifibSlapWebServiceMixin):
  ########################################
  # ComputerPartition.getInstanceParameterDict
  ########################################

  def test_ComputerPartition_getInstanceParameterDict_afterRegister(self):
    """
    Check that calling ComputerPartition.getInstanceParameterDict after just 
    registration works
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionGetInstanceParameterDictCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getInstanceParameterDict_confirmedState(self):
    """
    Check that calling ComputerPartition.getInstanceParameterDict works in 
    confirmed state
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      CheckSuccessComputerPartitionGetInstanceParameterDictCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getInstanceParameterDict_cancelledState(self):
    """
    Check that calling ComputerPartition.getInstanceParameterDict works in 
    cancelled state
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      LoginDefaultUser \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      Logout \
      SlapLoginCurrentSoftwareInstance \
      CheckSuccessComputerPartitionGetInstanceParameterDictCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getInstanceParameterDict_startedState(self):
    """
    Check that calling ComputerPartition.getInstanceParameterDict works in 
    started state
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_building_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      CheckSuccessComputerPartitionGetInstanceParameterDictCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getInstanceParameterDict_stoppedState(self):
    """
    Check that calling ComputerPartition.getInstanceParameterDict works in 
    stopped state
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_installed_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      CheckSuccessComputerPartitionGetInstanceParameterDictCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getInstanceParameterDict_emptyParameter(self):
    """
    Check that calling ComputerPartition.getInstanceParameterDict does 
    return minimal information in case no parameters are set
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      CheckMinimalParametersTransmitted \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getInstanceParameterDict_validXML(self):
    """
    Check that calling ComputerPartition.getInstanceParameterDict works
    if the XML doesn't respect the XSD
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      LoginDefaultUser \
      SetSoftwareInstanceValidXML \
      Tic \
      Logout \
      SlapLoginCurrentSoftwareInstance \
      CheckComputerPartitionGetInstanceParameterDictResult \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionGetInstanceParameterDict))
  return suite
