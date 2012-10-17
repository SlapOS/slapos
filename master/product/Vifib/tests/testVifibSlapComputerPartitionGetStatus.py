from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from slapos import slap

class TestVifibSlapComputerPartitionGetStatus(TestVifibSlapWebServiceMixin):
  ########################################
  # ComputerPartition.getStatus
  ########################################

  def stepCheckNoDataComputerPartitionGetStatusCall(self, sequence, **kw):
    """
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence.get("computer_partition_reference",
        sequence['computer_partition_reference_list'][0])
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    status = computer_partition.getStatus()
    self.assertEquals('SlapOS Master', status['user'])
    self.assertEquals('#error no data found', status['text'])

  def test_ComputerPartition_getStatus_emptyPartition(self):
    """
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      CheckNoDataComputerPartitionGetStatusCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckOKComputerPartitionGetStatusCall(self, sequence, **kw):
    """
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence.get("computer_partition_reference",
        sequence['computer_partition_reference_list'][0])
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    status = computer_partition.getStatus()
    self.assertEquals(sequence['software_instance_reference'], status['user'])
    self.assertEquals('#access %s %s' % (
      sequence['computer_reference'], 
      sequence['software_instance_reference']), 
                      status['text'])

  def test_ComputerPartition_OK_getStatus(self):
    """
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_building_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      CheckSuccessSlapRegisterComputerPartitionCall \
      SlapLogout \
      SlapLoginCurrentComputer \
      CheckOKComputerPartitionGetStatusCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckErrorComputerPartitionGetStatusCall(self, sequence, **kw):
    """
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence.get("computer_partition_reference",
        sequence['computer_partition_reference_list'][0])
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    status = computer_partition.getStatus()
    self.assertEquals(sequence['computer_reference'], status['user'])
    self.assertEquals('#error while instanciating', status['text'])

  def test_ComputerPartition_Error_getStatus(self):
    """
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_building_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionErrorCall \
      CheckErrorComputerPartitionGetStatusCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionGetStatus))
  return suite
