from Products.ERP5Type.tests.backportUnittest import skip
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
    self.stepConfirmOrderedSaleOrderActiveSense()
    self.stepTic()

    S1_instance = self.portal.portal_catalog.getResultValue(
      portal_type='Software Instance', title=S1)
    S1_instance.requestSoftwareInstance(partition_reference=S2, **common_kw)
    self.stepTic()
    S1_instance.requestSoftwareInstance(partition_reference=S3, **common_kw)
    self.stepConfirmOrderedSaleOrderActiveSense()
    self.stepTic()

    root_software_instance.requestSoftwareInstance(partition_reference=S4,
      **common_kw)
    self.stepTic()
    self.stepConfirmOrderedSaleOrderActiveSense()
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

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
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

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bang_computer_simple_tree(self):
    """Checks that bangs works on simple tree"""
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + \
      """
      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      ComputerBang
      Tic
      SlapLogout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      SlapLogout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
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

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepStoreComputerCoordinatesAsC1(self, sequence, **kw):
    sequence.edit(
      computer_uid_c1=sequence['computer_uid'],
      computer_reference_c1=sequence['computer_reference'],
    )

  def stepRestoreComputerC1Coordinates(self, sequence, **kw):
    sequence.edit(
      computer_uid=sequence['computer_uid_c1'],
      computer_reference=sequence['computer_reference_c1'],
    )

  def stepStoreComputerCoordinatesAsC0(self, sequence, **kw):
    sequence.edit(
      computer_uid_c0=sequence['computer_uid'],
      computer_reference_c0=sequence['computer_reference'],
    )

  def stepFinishSoftwareInstanceSpannedTree(self, sequence, **kw):
    self.stepLoginDefaultUser()
    rand = str(random())
    S1 = 'S1' + rand
    S2 = 'S2' + rand
    S3 = 'S3' + rand
    root_software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])
    common_kw = dict(
      software_release=sequence['software_release_uri'],
      software_type='any', instance_xml=self.minimal_correct_xml,
      state='stopped')
    self.logout()
    self.login(sequence['software_instance_reference'])
    root_software_instance.requestSoftwareInstance(
      partition_reference=S1,
      sla_xml="""<?xml version='1.0' encoding='utf-8'?>
      <instance>
        <parameter id="computer_guid">%s</parameter>
        </instance>""" % sequence['computer_reference_c1'],
      **common_kw)
    self.stepTic()
    self.stepConfirmOrderedSaleOrderActiveSense()
    self.stepTic()
    self.logout()

    self.stepLoginDefaultUser()
    S1_instance = self.portal.portal_catalog.getResultValue(
      portal_type='Software Instance', title=S1)
    S1_reference = S1_instance.getReference()
    self.logout()
    self.login(S1_reference)
    S1_instance.requestSoftwareInstance(
      partition_reference=S2,
      sla_xml="""<?xml version='1.0' encoding='utf-8'?>
      <instance>
        <parameter id="computer_guid">%s</parameter>
        </instance>""" % sequence['computer_reference_c0'],
      **common_kw)
    self.stepTic()
    self.stepConfirmOrderedSaleOrderActiveSense()
    self.stepTic()
    self.logout()

    self.stepLoginDefaultUser()
    S2_instance = self.portal.portal_catalog.getResultValue(
      portal_type='Software Instance', title=S2)
    S2_reference = S2_instance.getReference()
    self.logout()

    self.login(S2_reference)
    S2_instance.requestSoftwareInstance(
      partition_reference=S3,
      sla_xml="""<?xml version='1.0' encoding='utf-8'?>
      <instance>
        <parameter id="computer_guid">%s</parameter>
        </instance>""" % sequence['computer_reference_c1'],
      **common_kw)
    self.stepTic()
    self.logout()

    self.stepLoginDefaultUser()
    self.stepConfirmOrderedSaleOrderActiveSense()
    self.stepTic()
    S3_instance = self.portal.portal_catalog.getResultValue(
      portal_type='Software Instance', title=S3)
    S3_reference = S3_instance.getReference()
    self.logout()

    self.login(S1_reference)
    S1_instance.stopComputerPartitionInstallation()
    self.stepTic()
    self.logout()

    self.login(S2_reference)
    S2_instance.stopComputerPartitionInstallation()
    self.stepTic()
    self.logout()

    self.login(S3_reference)
    S3_instance.stopComputerPartitionInstallation()
    self.stepTic()
    self.logout()

    self.stepLoginDefaultUser()
    sequence.edit(
      S0_uid = sequence['software_instance_uid'],
      S1_uid = S1_instance.getUid(),
      S2_uid = S2_instance.getUid(),
      S3_uid = S3_instance.getUid(),
    )
    self.logout()

  def test_computer_bang_tree_with_other_computer(self):
    """Check that bang works on complex tree spanned on many computers

    For tree like this:

    S0
      \
       S1
         \
          S2

    Where S0 and S2 are on C0 and S1 is on C1 and both are non public it shall
    work.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_published_software_release + \
      """
      # prepare first computer
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      SetComputerCoordinatesFromComputerTitle
      StoreComputerCoordinatesAsC1
      ComputerSetAllocationScopeOpenPersonal
      Tic
      CheckComputerTradeConditionDestinationSectionTestVifibCustomer
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      LoginTestVifibCustomer
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      # prepare second computer
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      SetComputerCoordinatesFromComputerTitle
      StoreComputerCoordinatesAsC0
      ComputerSetAllocationScopeOpenPersonal
      Tic
      CheckComputerTradeConditionDestinationSectionTestVifibCustomer
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      LoginTestVifibCustomer
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      # Request S0
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceBuilding
      Tic
      SlapLogout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListStarted
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout
      LoginDefaultUser
      SetSelectedComputerPartition
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout
      LoginTestVifibCustomer
      RequestSoftwareInstanceStart
      Tic
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SlapLogout
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout

      FinishSoftwareInstanceSpannedTree

      Tic
      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      ComputerBang
      Tic
      SlapLogout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      SlapLogout

      RestoreComputerC1Coordinates
      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      SlapLogout
      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckComputerPartitionNoInstanceUpdateSalePackingList(self,
      sequence, **kw):
    self._checkComputerPartitionNoSalePackingList(
        self.portal.portal_preferences.getPreferredInstanceUpdateResource(),
        sequence)

  def test_computer_bang_not_called_on_destroying_destroyed(self):
    """Check that bang is ignoring destruction in progress and
       destroyed computer partitions"""
    self.computer_partition_amount = 1
    sequence_list = SequenceList()
    sequence_string = self.prepare_destroy_requested_computer_partition + \
      """
      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      ComputerBang
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionNoInstanceUpdateSalePackingList
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionIsFree
      Logout

      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      ComputerBang
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionNoInstanceUpdateSalePackingList
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepFinishSoftwareInstancePartlyDestroyedTree(self, sequence, **kw):
    self.stepLoginDefaultUser()
    rand = str(random())
    S1 = 'S1' + rand
    root_software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])
    common_kw = dict(
      software_release=sequence['software_release_uri'],
      software_type='any', instance_xml=self.minimal_correct_xml,
      sla_xml=self.minimal_correct_xml, state='stopped')
    self.logout()

    self.login(sequence['software_instance_reference'])
    root_software_instance.requestSoftwareInstance(
      partition_reference=S1,
      **common_kw)
    self.stepTic()
    self.stepConfirmOrderedSaleOrderActiveSense()
    self.stepTic()
    self.logout()

    self.stepLoginDefaultUser()
    S1_instance = self.portal.portal_catalog.getResultValue(
      portal_type='Software Instance', title=S1)
    S1_reference = S1_instance.getReference()
    self.logout()

    self.login(S1_reference)
    S1_instance.stopComputerPartitionInstallation()
    self.logout()

    self.login(sequence['software_instance_reference'])
    root_software_instance.requestDestroyComputerPartition()
    self.stepTic()
    self.logout()
    
    self.login(sequence['computer_reference'])
    root_software_instance.destroyComputerPartition()
    self.stepTic()
    self.logout()

    self.stepLoginDefaultUser()
    sequence.edit(
      S0_uid = sequence['software_instance_uid'],
      S1_uid = S1_instance.getUid(),
    )
    self.logout()

  def test_computer_bang_not_called_on_partly_destroyed_tree(self):
    """Check that bang is ignoring partitions on partly destroyed tree"""
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + \
      """
      FinishSoftwareInstancePartlyDestroyedTree

      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      ComputerBang
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionNoInstanceUpdateSalePackingList
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)
    self.login()
    self.portal.portal_alarms.vifib_check_consistency.activeSense()
    self.stepTic()
    self.assertTrue(self.portal.portal_alarms.vifib_check_consistency.sense())
    consistency_list = self.portal.portal_alarms.vifib_check_consistency\
      .Alarm_getConsistencyCheckReportLineList()
    self.assertEqual(2, len(consistency_list))
    self.assertEqual(sorted([q.message for q in consistency_list]),
      ['SSL Certificate must be set', 'SSL Key must be set'])

  def stepCheckTreeLooksLikeRenameComplexTree(self, sequence, **kw):
    hosting_subscription_uid = sequence['hosting_subscription_uid']

    hosting_subscription = self.portal.portal_catalog.getResultValue(
      uid=hosting_subscription_uid
    )

    root_software_instance = hosting_subscription.portal_catalog.getResultValue(
      title=hosting_subscription.getTitle(), portal_type="Software Instance",
      root_uid=hosting_subscription_uid)
    self.failIfEqual(root_software_instance, None)

    children_titles = set([si.getTitle()
                           for si in root_software_instance.getPredecessorValueList()])
    self.failUnless(set(['children_a', 'children_b']) <= children_titles)

    children_b_child = hosting_subscription.portal_catalog.getResultValue(
      title='children_b_child',
      root_uid=hosting_subscription.getUid(),
    )
    self.failIfEqual(children_b_child, None)

  @skip('Ignored for now')
  def test_ComputerPartition_rename_root_and_bang(self):
    r"""
    Request Master:                     __________
                                       /          \
                                      | HS: Master |
                                       \__________/
                                        _____|____
                                       /          \
                                      | SI: Master |
                                       \__________/

    Rename Software Instance Master into MasterDead:
           __________
          /          \
         | HS: Master |
          \__________/
         _______|______
        /              \
       | SI: MasterDead |
        \______________/

    Banging the tree should result:
                          _____________________________
                         /                              \
                        |            HS: Master          |
                         \______________________________/
                          ____/_____      _______\______
                         /          \    /              \
                        | SI: Master |  | SI: MasterDead |
                         \__________/    \______________/
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      SetRootSoftwareInstanceCurrentInstance
      Tic
      LoginDefaultUser
      RenameCurrentSoftwareInstanceDead
      Tic
      Logout
      SlapLoginCurrentSoftwareInstance
      Bang
      ConfirmOrderedSaleOrderActiveSense
      SlapLogout
      Tic
      LoginTestVifibCustomer
      CheckTreeHasARootSoftwareInstance
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Ignored for now')
  def test_ComputerPartition_rename_root_complex_tree(self):
    r"""
    Request Master which is a software realease having a complex tree :
              ___________________________
             /                            \
            |           HS: Master         |
             \____________________________/
              _____________|_____________
             /                            \
            |           SI: Master         |
             \____________________________/
              _____/_____     _____\_____
             /           \   /           \
            | SI: Child A | | SI: Child B |
             \___________/   \___________/
                             ______|______
                            /              \
                           | SI: GrandChild |
                            \______________/

    Rename Software Instance Master :
              ___________________________
             /                            \
            |           SI: Master         |
             \____________________________/
              _____________|_____________
             /                            \
            |        SI: MasterDead        |
             \____________________________/
              _____/_____     _____\_____
             /           \   /           \
            | SI: Child A | | SI: Child B |
             \___________/   \___________/
                             ______|______
                            /              \
                           | SI: GrandChild |
                            \______________/

    Run bang() on the tree. We expect to have a new root as :
              _______________________________________________
             /                                               \
            |                     HS: Master                  |
             \_______________________________________________/
              _____________|______________     _______|______
             /                            \   /              \
            |           SI: Master         | | SI: MasterDead |
             \____________________________/   \______________/
              _____/_____     _____\_____
             /           \   /           \
            | SI: Child A | | SI: Child B |
             \___________/   \___________/
                             ______|______
                            /              \
                           | SI: GrandChild |
                            \______________/

    """
    self.computer_partition_amount = 5
    sequence_list = SequenceList()
    sequence_string = self.prepare_children_a_children_b_sequence_string + """
      LoginDefaultUser
      SetSoftwareInstanceChildrenB
      SelectRequestedReferenceChildrenBChild
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      Tic
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SlapLoginTestVifibCustomer
      SetSoftwareInstanceRoot
      RenameCurrentSoftwareInstanceDead
      Tic
      Bang
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      SlapLogout

      LoginDefaultUser
      SetSoftwareInstanceGetRootOfTheTree
      SetRootSoftwareInstanceCurrentInstance
      SelectRequestedReferenceChildrenA
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SelectRequestedReferenceChildrenB
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLogout

      LoginDefaultUser
      SetSoftwareInstanceChildrenB
      SelectRequestedReferenceChildrenBChild
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLogout

      LoginDefaultUser
      SlapLoginCurrentComputer
      CheckTreeHasARootSoftwareInstance
      CheckTreeLooksLikeRenameComplexTree
      SlapLogout
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_rename_child_complex_tree(self):
    r"""
    Request A which is a software realease having a complex tree :
              ___________________________
             /                            \
            |           HS: Master         |
             \____________________________/
              _____________|_____________
             /                            \
            |           SI: Master         |
             \____________________________/
              _____/_____     _____\_____
             /           \   /           \
            | SI: Child A | | SI: Child B |
             \___________/   \___________/
                             ______|______
                            /              \
                           | SI: GrandChild |
                            \______________/

    Rename child C into E :
    (Rename reattach to root as Luke wanted it)
              ________________________________
             /                                \
            |             HS: Master           |
             \________________________________/
              ________________|_______________
             /                                \
            |            SI: Master            |
             \________________________________/
              _____/_____     _________\______
             /           \   /                \
            | SI: Child A | | SI: Child B Dead |
             \___________/   \________________/
                               ______|______
                              /              \
                             | SI: GrandChild |
                              \______________/

    Bang the tree. We espect to have a new C replacing it,
    as :      _________________________________________________
             /                                                 \
            |                      HS: Master                   |
             \_________________________________________________/
              _____________|___________________________________
             /                                                 \
            |                     SI: Master                    |
             \_________________________________________________/
              _____/_____     _____\_____      _______|________
             /           \   /           \    /                \
            | SI: Child A | | SI: Child B |  | SI: Child B Dead |
             \___________/   \___________/    \________________/
                             ______|______
                            /              \
                           | SI: GrandChild |
                            \______________/
    """
    self.computer_partition_amount = 5
    sequence_list = SequenceList()
    sequence_string = self.prepare_children_a_children_b_sequence_string + """
      LoginDefaultUser
      SetSoftwareInstanceChildrenB
      SelectRequestedReferenceChildrenBChild
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      Tic
      RequestComputerPartition
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLogout

      LoginDefaultUser
      SlapLoginTestVifibCustomer
      SetSoftwareInstanceChildrenB
      RenameCurrentSoftwareInstanceDead
      Tic
      Bang
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      SlapLogout

      LoginDefaultUser
      SetSoftwareInstanceGetRootOfTheTree
      SetRootSoftwareInstanceCurrentInstance
      SelectRequestedReferenceChildrenA
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLogout

      LoginDefaultUser
      SelectRequestedReferenceChildrenB
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLogout

      LoginDefaultUser
      SetSoftwareInstanceChildrenB
      SelectRequestedReferenceChildrenBChild
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLogout

      LoginDefaultUser
      SlapLoginCurrentComputer
      CheckTreeHasARootSoftwareInstance
      CheckTreeLooksLikeRenameComplexTree
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)


def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapBang))
  return suite
