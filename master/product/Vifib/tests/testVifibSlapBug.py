from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapBug(TestVifibSlapWebServiceMixin):
  def test_bug_Person_request_more_then_one_instance(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_person_requested_software_instance + '\
      LoginTestVifibCustomer \
      PersonRequestSoftwareInstance \
      Tic \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_ComputerPartition_request_two_similar(self):
    """
    Checks that requesting twice with different arguments from same Computer
    Partition will return different objects."""
    self.computer_partition_amount = 3
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      RequestTwoAndCheckDifferentResult \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_doubleClickOnStart(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_stopped_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      RequestSoftwareInstanceStart
      RequestSoftwareInstanceStartRaisesValueError
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_doubleClickOnStart_serializeIsCalled(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_stopped_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      RequestSoftwareInstanceStartCheckSerializeIsCalled
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_doubleClickOnDestroy(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_installed_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      RequestSoftwareInstanceDestroy
      RequestSoftwareInstanceDestroyRaisesValueError
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_doubleClickOnDestroy_serializeIsCalled(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_installed_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      RequestSoftwareInstanceDestroyCheckSerializeIsCalled
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepArchiveSoftwareRelease(self, sequence, **kw):
    """
    Submit the software release document.
    """
    software_release_uid = sequence["software_release_uid"]
    software_release = self.portal.portal_catalog.getResultValue(
        uid=software_release_uid)
    software_release.portal_workflow.doActionFor(software_release,
                                                 'archive_action')

  def test_bug_archived_software_release_access(self):
    """Checks that Computer has access to archived Software Release"""
    sequence_string = self.\
      prepare_start_requested_computer_partition_sequence_string + \
      """
      LoginTestVifibDeveloper
      ArchiveSoftwareRelease
      Tic
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout
    """
    sequence_list = SequenceList()
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepStoreCurrentSoftwareInstanceUidBufferA(self, sequence, **kw):
    sequence['buffer_a_software_instance_uid'] = sequence['software_instance_uid']

  def stepStoreCurrentSoftwareInstanceUidBufferB(self, sequence, **kw):
    sequence['buffer_b_software_instance_uid'] = sequence['software_instance_uid']

  def stepStoreCurrentComputerUidBufferA(self, sequence, **kw):
    sequence['buffer_a_computer_uid'] = sequence['computer_uid']

  def stepStoreCurrentComputerUidBufferB(self, sequence, **kw):
    sequence['buffer_b_computer_uid'] = sequence['computer_uid']

  def stepRestoreSoftwareInstanceUidFromBufferA(self, sequence, **kw):
    sequence['software_instance_uid'] = sequence['buffer_a_software_instance_uid']

  def stepRestoreSoftwareInstanceUidFromBufferB(self, sequence, **kw):
    sequence['software_instance_uid'] = sequence['buffer_b_software_instance_uid']

  def stepRestoreComputerUidFromBufferA(self, sequence, **kw):
    sequence['computer_uid'] = sequence['buffer_a_computer_uid']

  def stepRestoreComputerUidFromBufferB(self, sequence, **kw):
    sequence['computer_uid'] = sequence['buffer_b_computer_uid']

  def stepStoreCurrentComputerReferenceBufferA(self, sequence, **kw):
    sequence['buffer_a_computer_reference'] = sequence['computer_reference']

  def stepStoreCurrentComputerReferenceBufferB(self, sequence, **kw):
    sequence['buffer_b_computer_reference'] = sequence['computer_reference']

  def stepStoreCurrentComputerPartitionUidBufferA(self, sequence, **kw):
    sequence['buffer_a_computer_partition_uid'] = sequence['computer_partition_uid']

  def stepStoreCurrentComputerPartitionUidBufferB(self, sequence, **kw):
    sequence['buffer_b_computer_partition_uid'] = sequence['computer_partition_uid']

  def stepStoreCurrentComputerPartitionReferenceBufferA(self, sequence, **kw):
    sequence['buffer_a_computer_partition_reference'] = sequence['computer_partition_reference']

  def stepStoreCurrentComputerPartitionReferenceBufferB(self, sequence, **kw):
    sequence['buffer_b_computer_partition_reference'] = sequence['computer_partition_reference']

  def stepRestoreComputerReferenceFromBufferA(self, sequence, **kw):
    sequence['computer_reference'] = sequence['buffer_a_computer_reference']

  def stepRestoreComputerReferenceFromBufferB(self, sequence, **kw):
    sequence['computer_reference'] = sequence['buffer_b_computer_reference']

  def stepRestoreComputerPartitionUidFromBufferA(self, sequence, **kw):
    sequence['computer_partition_uid'] = sequence['buffer_a_computer_partition_uid']

  def stepRestoreComputerPartitionUidFromBufferB(self, sequence, **kw):
    sequence['computer_partition_uid'] = sequence['buffer_b_computer_partition_uid']

  def stepRestoreComputerPartitionReferenceFromBufferA(self, sequence, **kw):
    sequence['computer_partition_reference'] = sequence['buffer_a_computer_partition_reference']

  def stepRestoreComputerPartitionReferenceFromBufferB(self, sequence, **kw):
    sequence['computer_partition_reference'] = sequence['buffer_b_computer_partition_reference']

  def stepCheckHostingSubscriptionMultipleComputerAuditor(self, sequence, **kw):
    hosting_subscription = self.portal.portal_catalog.getResultValue(
      uid=sequence['hosting_subscription_uid'])
    role_list = hosting_subscription.get_local_roles()
    setup_packing_list_line_list = [q for q in
      hosting_subscription.getAggregateRelatedValueList(
        portal_type='Sale Packing List Line') if q.getResource() ==
          self.portal.portal_preferences.getPreferredInstanceSetupResource()]
    computer_list = [q.getAggregateValue(
      portal_type='Computer Partition').getParentValue() for q in
        setup_packing_list_line_list]
    for computer in computer_list:
      self.assertTrue((computer.getReference(), ('Auditor',))) in role_list

  def test_bug_destruction_of_partition_originated_from_another_computer(self):
    """Checks that computer is capable to destroy own Software Instance

    If software instance originated on computer comes from another computer it
    shall be possible to sucesfully destroy it.

    Test is done in a way to trigger unstable Assignor role calculation
    on Hosting Subscription which leads to unavailability of Software Instances
    from one computer to another.
    """
    sequence_list = SequenceList()
    sequence_string = """
      # Prepare software release shared by both Computers
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic
      SubmitSoftwareRelease
      Tic
      CreateSoftwareProduct
      Tic
      ValidateSoftwareProduct
      Tic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      Logout

      # Create first computer
      LoginTestVifibAdmin
      CustomerRegisterNewComputer
      Tic
      SetComputerCoordinatesFromComputerTitle
      ComputerSetAllocationScopeOpenPublic
      Tic
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferA
      StoreCurrentComputerUidBufferA

      # Install software on first computer
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      # Now request and instantiate this software release on first computer
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

      StoreCurrentComputerPartitionReferenceBufferA
      StoreCurrentComputerPartitionUidBufferA
      StoreCurrentSoftwareInstanceUidBufferA

      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # Start it..
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout

      LoginDefaultUser
      SetSelectedComputerPartition
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout

      # ...stop it...

      LoginDefaultUser
      RequestSoftwareInstanceStop
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStopped
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
      Logout

      # ...and request destruction
      LoginDefaultUser
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      # Now prepare second computer

      LoginTestVifibAdmin
      CustomerRegisterNewComputer
      Tic
      SetComputerCoordinatesFromComputerTitle
      ComputerSetAllocationScopeOpenPublic
      Tic
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferB
      StoreCurrentComputerUidBufferB

      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferB
      StoreCurrentComputerUidBufferB

      # Now request self software release from one computer to another
      RestoreComputerReferenceFromBufferA
      RestoreComputerUidFromBufferA
      RestoreSoftwareInstanceUidFromBufferA
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      Tic
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      LoginDefaultUser
      SetCurrentSoftwareInstanceRequested
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      Logout

      StoreCurrentComputerPartitionReferenceBufferB
      StoreCurrentComputerPartitionUidBufferB
      StoreCurrentSoftwareInstanceUidBufferB

      RestoreComputerReferenceFromBufferB
      RestoreComputerUidFromBufferB

      # Start the requested software instance...

      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout

      LoginDefaultUser
      SetSelectedComputerPartition
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout

      # ...and stop it

      LoginDefaultUser
      RequestSoftwareInstanceStop
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStopped
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
      Logout

      # Now request destruction of second software instance...

      LoginDefaultUser
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      # ...and destroy it

      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionIsFree
      Logout

      # Time to switch back to first software instance and destroy it
      RestoreComputerPartitionReferenceFromBufferA
      RestoreComputerPartitionUidFromBufferA
      RestoreSoftwareInstanceUidFromBufferA
      RestoreComputerReferenceFromBufferA
      RestoreComputerUidFromBufferA

      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionIsFree
      Logout

      LoginDefaultUser
      CheckHostingSubscriptionMultipleComputerAuditor
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_destruction_confirmed_instance_setup(self):
    """Proves that all is correctly handled in case of confirmed instance
    setup packing list existence"""
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + \
      """
      LoginTestVifibCustomer
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      # Now there are two packing lists in confirmed state:
      #  * one for instance setup
      #  * one for instance destruction
      # Simulate typical scenario:
      #  * stopped
      #  * commit
      #  * destroyed
      #  * commit
      #  * tic

      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      SoftwareInstanceDestroyed
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionIsFree
      CheckComputerPartitionNoInstanceHostingSalePackingList
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_destruction_with_cancelled_packing_list(self):
    """Proves that even if some packing lists are in cancelled state
    it is possible to destroy software instance"""
    sequence_list = SequenceList()
    sequence_string = self.prepare_stopped_computer_partition_sequence_string + """
      # Request destruction...
      LoginDefaultUser
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      # and cancel current destruction.
      LoginDefaultUser
      SelectCurrentlyUsedSalePackingListUid
      CancelSalePackingList
      Tic
      CheckComputerPartitionInstanceCleanupSalePackingListCancelled
      Logout

      # So all packing lists are finished, but one is cancelled,
      # time to request destruction...

      LoginDefaultUser
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      # ...and destroy it

      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionIsFree
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_destruction_with_unfinished_packing_list(self):
    """Proves that even if some packing lists are not fully delivered
    it is possible to destroy software instance"""
    sequence_list = SequenceList()
    sequence_string = """
      # Prepare software release
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic
      SubmitSoftwareRelease
      Tic
      CreateSoftwareProduct
      Tic
      ValidateSoftwareProduct
      Tic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      Logout

      # Create first computer
      LoginTestVifibAdmin
      CustomerRegisterNewComputer
      Tic
      SetComputerCoordinatesFromComputerTitle
      ComputerSetAllocationScopeOpenPublic
      Tic
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferA
      StoreCurrentComputerUidBufferA

      # Install software on first computer
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      # Now request and instantiate this software release on first computer
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

      # Request destruction...
      LoginDefaultUser
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      # ...and destroy it

      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionIsFree
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepDirectRequestComputerPartitionRaisesDisconnectedSoftwareTree(self,
    sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
      uid = sequence['software_instance_uid'])
    from erp5.document.SoftwareInstance import DisconnectedSoftwareTree
    self.assertRaises(DisconnectedSoftwareTree,
      software_instance.requestSoftwareInstance,
      software_release=sequence['software_release_uri'],
      software_type=sequence['requested_reference'],
      partition_reference=sequence['requested_reference'],
      shared=False,
      instance_xml=self.minimal_correct_xml,
      sla_xml=self.minimal_correct_xml,
      state='started'
    )

  def test_bug_orhpaned_software_instance(self):
    """Check that no orphaned Software Instances would be created

    In below scenario system shall behave like mentioned:

      OpenOrder.request(SR, A)  | SR(A)
      A.request(SR, B)          | SR(A) <- SR(B)
      B.request(SR, C)          | SR(A) <- SR(B) <- SR(C)
      C.request(SR, B) raises immediately, because the result would be:
        SR(A)
        SR(B) <- SR(C)
      do B would become root of orphaned tree.
    """
    # Setup sufficient amount of CP
    self.computer_partition_amount = 3
    sequence_list = SequenceList()
    sequence_string = """
      # Prepare software release
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic
      SubmitSoftwareRelease
      Tic
      CreateSoftwareProduct
      Tic
      ValidateSoftwareProduct
      Tic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      Logout

      # Create the computer
      LoginTestVifibAdmin
      CustomerRegisterNewComputer
      Tic
      SetComputerCoordinatesFromComputerTitle
      ComputerSetAllocationScopeOpenPublic
      Tic
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferA
      StoreCurrentComputerUidBufferA

      # Install the software release
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      # Create Software Instance A (originates from Open Order)
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

      # From root request B
      SelectRequestedReferenceB

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      Tic
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      LoginDefaultUser
      SetCurrentSoftwareInstanceRequested
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      Logout

      # From B request C
      SelectRequestedReferenceC
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      Tic
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      LoginDefaultUser
      SetCurrentSoftwareInstanceRequested
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      Logout

      # Try to: from C request B and prove that it raises
      SelectRequestedReferenceB

      LoginDefaultUser # login as superuser in order to work in erp5
      DirectRequestComputerPartitionRaisesDisconnectedSoftwareTree
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepDirectRequestComputerPartitionRaisesCyclicSoftwareTree(self,
    sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
      uid = sequence['software_instance_uid'])
    from erp5.document.SoftwareInstance import CyclicSoftwareTree
    self.assertRaises(CyclicSoftwareTree,
      software_instance.requestSoftwareInstance,
      software_release=sequence['software_release_uri'],
      software_type=sequence['requested_reference'],
      partition_reference=sequence['requested_reference'],
      shared=False,
      instance_xml=self.minimal_correct_xml,
      sla_xml=self.minimal_correct_xml,
      state='started'
    )

  def test_bug_cyclic_software_instance(self):
    """Check that no cyclic Software Instance trees would be created

    In below scenario system shall behave like mentioned:

      OpenOrder.request(SR, A)  | SR(A)
      A.request(SR, B)          | SR(A) <- SR(B)
      B.request(SR, A)          | SR(A) <- SR(B) <- SR(C)
      C.request(SR, B) raises immediately, because the result would be:
        SR(A)
        SR(B) <-> SR(C)
      so B and C would be cyclic
    """
    # Setup sufficient amount of CP
    self.computer_partition_amount = 3
    sequence_list = SequenceList()
    sequence_string = """
      # Prepare software release
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic
      SubmitSoftwareRelease
      Tic
      CreateSoftwareProduct
      Tic
      ValidateSoftwareProduct
      Tic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      Logout

      # Create the computer
      LoginTestVifibAdmin
      CustomerRegisterNewComputer
      Tic
      SetComputerCoordinatesFromComputerTitle
      ComputerSetAllocationScopeOpenPublic
      Tic
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferA
      StoreCurrentComputerUidBufferA

      # Install the software release
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      # Create Software Instance A (originates from Open Order)
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

      # From root request B
      SelectRequestedReferenceB
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      Tic
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      LoginDefaultUser
      SetCurrentSoftwareInstanceRequested
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      Logout

      # From B request C
      SelectRequestedReferenceC
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      Tic
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      LoginDefaultUser
      SetCurrentSoftwareInstanceRequested
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      Logout

      # Try to: from C request B and prove that it raises
      SelectRequestedReferenceB

      LoginDefaultUser # login as superuser in order to work in erp5
      DirectRequestComputerPartitionRaisesCyclicSoftwareTree
      """
    sequence_list.addSequenceString(sequence_string)
    import erp5.document.SoftwareInstance
    def makeTrue(*args, **kwargs):
      return True
    # Disable temporialy checkConnected in order to have only
    # checkCyclic called
    erp5.document.SoftwareInstance.original_checkConnected = \
      erp5.document.SoftwareInstance.checkConnected
    erp5.document.SoftwareInstance.checkConnected = makeTrue
    try:
      sequence_list.play(self)
    finally:
      erp5.document.SoftwareInstance.checkConnected = \
        erp5.document.SoftwareInstance.original_checkConnected
      del(erp5.document.SoftwareInstance.original_checkConnected)

  def stepDirectRequestComputerPartitionRaisesValueError(self,
    sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
      uid = sequence['software_instance_uid'])
    self.assertRaises(ValueError,
      software_instance.requestSoftwareInstance,
      software_release=sequence['software_release_uri'],
      software_type=sequence['requested_reference'],
      partition_reference=sequence['requested_reference'],
      shared=False,
      instance_xml=self.minimal_correct_xml,
      sla_xml=self.minimal_correct_xml,
      state='started'
    )

  def test_bug_cyclic_software_instance_small_tree(self):
    """Check that no cyclic Software Instance trees would be created

    In below scenario system shall behave like mentioned:

      OpenOrder.request(SR, A)  | SR(A)
      A.request(SR, B)          | SR(A) <- SR(B)
      B.request(SR, A) raises immediately, because the result would be:
        SR(A) <-> SR(B)
      so B and A would be cyclic
    """
    # Setup sufficient amount of CP
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = """
      # Prepare software release
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic
      SubmitSoftwareRelease
      Tic
      CreateSoftwareProduct
      Tic
      ValidateSoftwareProduct
      Tic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      Logout

      # Create the computer
      LoginTestVifibAdmin
      CustomerRegisterNewComputer
      Tic
      SetComputerCoordinatesFromComputerTitle
      ComputerSetAllocationScopeOpenPublic
      Tic
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferA
      StoreCurrentComputerUidBufferA

      # Install the software release
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      # Create Software Instance A (originates from Open Order)
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

      # From root request B
      SelectRequestedReferenceB
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      Tic
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      LoginDefaultUser
      SetCurrentSoftwareInstanceRequested
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      Logout

      # Try to: From B request root
      SelectRequestedReferenceRootSoftwareInstanceTitle

      LoginDefaultUser # login as superuser in order to work in erp5
      DirectRequestComputerPartitionRaisesValueError
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapBug))
  return suite
