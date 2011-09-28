from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import expectedFailure
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapRegisterComputerPartition(TestVifibSlapWebServiceMixin):
  ########################################
  # slap.registerComputerPartition
  ########################################

  # ERP5/Zope does not follow REST API beacuse it is not possible to configure
  # Cookie Crumbler to ignore portal_slap
  @expectedFailure
  def test_slap_registerComputerPartition_unknowComputerUid(self):
    """
    Check the slap.registerComputerPartition without any Computer document
    fails.
    """
    sequence_list = SequenceList()
    sequence_string = '\
      SlapLoginRandomComputer \
      CheckUnauthorizedSlapRegisterComputerPartitionCall \
      SlapLogout \
      Tic \
      CheckUnexistingComputer \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  # ERP5/Zope does not follow REST API beacuse it is not possible to configure
  # Cookie Crumbler to ignore portal_slap
  @expectedFailure
  def test_slap_registerComputerPartition_draftComputer(self):
    """
    Check the slap.registerComputerPartition fails
    """
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      CreateDraftComputer \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckUnauthorizedSlapRegisterComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_slap_registerComputerPartition_ComputerWithoutPartition(self):
    """
    Check the slap.registerComputerPartition fails
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      SlapLoginCurrentComputer\
      CheckNotFoundSlapRegisterComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_slap_registerComputerPartition_ComputerWithPartition(self):
    """
    Check the slap.registerComputerPartition works
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      CheckSuccessSlapRegisterComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_slap_registerComputerPartition_TwoValidatedComputer(self):
    """
    Check the slap.registerComputerPartition works
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      CheckSuccessSlapRegisterComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_slap_registerComputerPartition_ComputerWithTwoPartition(self):
    """
    Check the slap.registerComputerPartition fails if there are 2 partition
    with the same reference.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      CheckSuccessSlapRegisterComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapRegisterComputerPartition))
  return suite
