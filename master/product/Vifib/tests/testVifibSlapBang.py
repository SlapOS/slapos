from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from Products.ERP5Type.tests.backportUnittest import expectedFailure
from slapos import slap
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from random import random

class TestVifibSlapBang(TestVifibSlapWebServiceMixin):

  bang_message = 'Bang message'

  # expected scenarios
  def stepFinishSoftwareInstanceTree(self, sequence, **kw):
    rand = str(random())
    S1 = 'S1' + rand
    S2 = 'S2' + rand
    S3 = 'S3' + rand
    S4 = 'S4' + rand
    root_software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])
    common_kw = dict(
      software_release=sequence['software_release_uri'],
      software_type='any', instance_xml=self.minimal_correct_xml,
      sla_xml=self.minimal_correct_xml, state='stopped')
    root_software_instance.requestSoftwareInstance(partition_reference=S1,
      **common_kw)
    self.stepTic()

    S1_instance = self.portal.portal_catalog.getResultValue(
      portal_type='Software Instance', title=S1)

    S1_instance.requestSoftwareInstance(partition_reference=S2, **common_kw)
    self.stepTic()
    S1_instance.requestSoftwareInstance(partition_reference=S3, **common_kw)
    self.stepTic()

    root_software_instance.requestSoftwareInstance(partition_reference=S4,
      **common_kw)
    self.stepTic()

    S2_instance = self.portal.portal_catalog.getResultValue(
      portal_type='Software Instance', title=S2)
    S3_instance = self.portal.portal_catalog.getResultValue(
      portal_type='Software Instance', title=S3)
    S4_instance = self.portal.portal_catalog.getResultValue(
      portal_type='Software Instance', title=S4)

    S1_instance.stopComputerPartitionInstallation()
    S2_instance.stopComputerPartitionInstallation()
    S3_instance.stopComputerPartitionInstallation()
    S4_instance.stopComputerPartitionInstallation()
    self.stepTic()
    sequence.edit(
      S0_uid = sequence['software_instance_uid'],
      S1_uid = S1_instance.getUid(),
      S2_uid = S2_instance.getUid(),
      S3_uid = S3_instance.getUid(),
      S4_uid = S4_instance.getUid()
    )

  def stepBang(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])
    slap_computer_partition.bang(self.bang_message)

  def stepProcessSoftwareInstanceList(self, sequence, **kw):
    S0 = self.portal.portal_catalog.getResultValue(uid=sequence['S0_uid'])
    S0.startComputerPartition()
    S1 = self.portal.portal_catalog.getResultValue(uid=sequence['S1_uid'])
    S1.stopComputerPartition()
    S2 = self.portal.portal_catalog.getResultValue(uid=sequence['S2_uid'])
    S2.stopComputerPartition()
    S3 = self.portal.portal_catalog.getResultValue(uid=sequence['S3_uid'])
    S3.stopComputerPartition()
    S4 = self.portal.portal_catalog.getResultValue(uid=sequence['S4_uid'])
    S4.stopComputerPartition()

  def stepSetCurrentSoftwareInstanceS1(self, sequence, **kw):
    S1 = self.portal.portal_catalog.getResultValue(uid=sequence['S1_uid'])
    sequence.edit(
      software_instance_reference=S1.getReference(),
      computer_partition_reference=S1.getAggregateRelatedValue()\
        .getAggregateValue(portal_type='Computer Partition').getReference()
    )

  def stepSetCurrentSoftwareInstanceS3(self, sequence, **kw):
    S3 = self.portal.portal_catalog.getResultValue(uid=sequence['S3_uid'])
    sequence.edit(
      software_instance_reference=S3.getReference(),
      computer_partition_reference=S3.getAggregateRelatedValue()\
        .getAggregateValue(portal_type='Computer Partition').getReference()
    )

  def checkSoftwareInstanceBangMessage(self, software_instance):
    bang_list = [q for q in software_instance.Base_getWorkflowHistoryItemList(
      'software_instance_slap_interface_workflow')
      if q.action == 'report_computer_partition_bang']
    self.assertEqual(1, len(bang_list))
    self.assertEqual(self.bang_message, bang_list[0].comment)

  def stepCheckS0BangMessage(self, sequence, **kw):
    self.checkSoftwareInstanceBangMessage(
      self.portal.portal_catalog.getResultValue(uid=sequence['S0_uid']))

  def stepCheckS1BangMessage(self, sequence, **kw):
    self.checkSoftwareInstanceBangMessage(
      self.portal.portal_catalog.getResultValue(uid=sequence['S1_uid']))

  def stepCheckS2BangMessage(self, sequence, **kw):
    self.checkSoftwareInstanceBangMessage(
      self.portal.portal_catalog.getResultValue(uid=sequence['S1_uid']))

  def stepCheckS3BangMessage(self, sequence, **kw):
    self.checkSoftwareInstanceBangMessage(
      self.portal.portal_catalog.getResultValue(uid=sequence['S3_uid']))

  def stepCheckS4BangMessage(self, sequence, **kw):
    self.checkSoftwareInstanceBangMessage(
      self.portal.portal_catalog.getResultValue(uid=sequence['S3_uid']))

  def test_bang_computer_partition_complex_tree(self):
    """Checks that bangs works on complex tree

    For tree like:

          S0
         /   \
       S4     S1
             /  \
            S2  S3

    Invoking bang on Root, S1 or S3 will made whole tree updatable.
    """
    self.computer_partition_amount = 5
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + \
      """
      LoginDefaultUser
      FinishSoftwareInstanceTree
      Logout

      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      SlapLogout

      SlapLoginCurrentSoftwareInstance
      Bang
      Tic
      SlapLogout

      LoginDefaultUser
      CheckS0BangMessage
      Logout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      SlapLogout

      LoginDefaultUser
      ProcessSoftwareInstanceList
      Tic
      SetCurrentSoftwareInstanceS1
      Logout

      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      SlapLogout

      SlapLoginCurrentSoftwareInstance
      Bang
      Tic
      SlapLogout

      LoginDefaultUser
      CheckS1BangMessage
      Logout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      SlapLogout

      LoginDefaultUser
      ProcessSoftwareInstanceList
      Tic
      SetCurrentSoftwareInstanceS3
      Logout

      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      SlapLogout

      SlapLoginCurrentSoftwareInstance
      Bang
      Tic
      SlapLogout

      LoginDefaultUser
      CheckS3BangMessage
      Logout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      SlapLogout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepComputerBang(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    slap_computer = self.slap.registerComputer(
      sequence['computer_reference'])
    slap_computer.bang(self.bang_message)

  def stepCheckComputerBangMessage(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    bang_list = [q for q in computer.Base_getWorkflowHistoryItemList(
      'computer_slap_interface_workflow') if q.action == 'report_computer_bang']
    self.assertEqual(1, len(bang_list))
    self.assertEqual(self.bang_message, bang_list[0].comment)

  def test_bang_computer_complex_tree(self):
    """Checks that bangs works on complex tree

    For tree like:

          S0
         /   \
       S4     S1
             /  \
            S2  S3

    Invoking bang on Computer will made whole tree updatable.
    """
    self.computer_partition_amount = 5
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + \
      """
      LoginDefaultUser
      FinishSoftwareInstanceTree
      Logout

      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      ComputerBang
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerBangMessage
      CheckS0BangMessage
      CheckS1BangMessage
      CheckS2BangMessage
      CheckS3BangMessage
      CheckS4BangMessage
      Logout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      SlapLogout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  # Computer owner cannot do bang yet
  @expectedFailure
  def test_admin_bang_computer_complex_tree(self):
    """Checks that bangs works on complex tree

    For tree like:

          S0
         /   \
       S4     S1
             /  \
            S2  S3

    Invoking bang on Computer will made whole tree updatable.
    """
    self.computer_partition_amount = 5
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + \
      """
      LoginDefaultUser
      FinishSoftwareInstanceTree
      Logout

      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      SlapLogout

      SlapLoginTestVifibCustomer
      ComputerBang
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerBangMessage
      CheckS0BangMessage
      CheckS1BangMessage
      CheckS2BangMessage
      CheckS3BangMessage
      CheckS4BangMessage
      Logout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      SlapLogout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapBang))
  return suite
