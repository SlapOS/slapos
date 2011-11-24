from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapAllocationScope(TestVifibSlapWebServiceMixin):

  def stepCheckComputerAllocationScopeEmpty(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    self.assertEqual(computer.getAllocationScope(), None)

  def stepCheckComputerAllocationScopeOpenFriend(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    self.assertEqual(computer.getAllocationScope(), 'open/friend')

  def stepCheckComputerAllocationScopeClose(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    self.assertEqual(computer.getAllocationScope(), 'close')

  def stepCheckComputerAllocationScopeOpenPersonal(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    self.assertEqual(computer.getAllocationScope(), 'open/personal')

  def stepCheckComputerAllocationScopeOpenPublic(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    self.assertEqual(computer.getAllocationScope(), 'open/public')

  def stepCheckComputerTradeConditionDestinationSectionVifibAdminTestVifibCustomer(
      self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    trade_condition = computer.getAggregateRelatedValue(
      portal_type='Sale Supply Line').getParentValue()
    person_url_list = sorted([q.getRelativeUrl() for q in \
      self.portal.portal_catalog(portal_type='Person',
      default_email_text=['test_customer@example.org',
      'test_computer_vifib_admin@example.org'])])
    self.assertEqual(sorted(trade_condition.getDestinationSectionList()),
      person_url_list)

  request_and_install_software = """
      LoginTestVifibCustomer
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout
  """

  def stepCheckNoRelatedSalePackingListLineForSoftwareInstance(self, sequence,
    **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    self.assertEqual(0, len(software_instance.getAggregateRelatedValueList(
          portal_type=self.sale_packing_list_line_portal_type)))

  def stepSetSequenceSlaXmlCurrentComputer(self, sequence, **kw):
    sequence['sla_xml'] = """<?xml version='1.0' encoding='utf-8'?>
<instance>
<parameter id="computer_guid">%s</parameter>
</instance>""" % sequence['computer_reference']
    sequence['requested_filter_dict'] = dict(
      computer_guid=sequence['computer_reference'])

  def test_allocation_scope_open_personal(self):
    """Check that computer is open/personal it is only available
    to owner"""
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      SetSequenceSlaXmlCurrentComputer

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenPersonal
      CheckComputerTradeConditionDestinationSectionTestVifibCustomer
      Logout
    """ + self.prepare_published_software_release + \
      self.request_and_install_software + """
      # request as owner
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for owner
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # request as someone else
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # fail to instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckNoRelatedSalePackingListLineForSoftwareInstance
      Logout

      # request as owner
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for owner
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepComputerSetAllocationScopeOpenFriendTestVifibAdmin(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin("Hosting")
    request.set('portal_skin', "Hosting")

    computer.Computer_updateAllocationScope(allocation_scope='open/friend',
      subject_list=['test_computer_vifib_admin@example.org'])

    self.getPortal().portal_skins.changeSkin("View")
    request.set('portal_skin', "View")
    
  def test_allocation_scope_open_friend(self):
    """Check that computer is open/friend it is only available
    to owner and its friends"""
    self.computer_partition_amount = 3
    sequence_list = SequenceList()
    sequence_string = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenFriendTestVifibAdmin
      Tic
      Logout
      SetSequenceSlaXmlCurrentComputer

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenFriend
      CheckComputerTradeConditionDestinationSectionVifibAdminTestVifibCustomer
      Logout
    """ + self.prepare_published_software_release + \
      self.request_and_install_software + """
      # request as owner
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for owner
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # request as friend
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for friend
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # request as someone else
      LoginTestVifibCustomerA
      PersonRequestSoftwareInstance
      Tic
      Logout

      # fail to instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckNoRelatedSalePackingListLineForSoftwareInstance
      Logout

      # request as friend
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for friend
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_allocation_scope_open_public(self):
    """Check that computer is open/public it is only available
    to anybody"""
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenPublic
      Tic
      Logout
      SetSequenceSlaXmlCurrentComputer

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenPublic
      CheckComputerTradeConditionDestinationSectionListEmpty
      Logout
    """ + self.prepare_published_software_release + \
      self.request_and_install_software + """
      # request as owner
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for owner
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # request as someone else
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_allocation_scope_close(self):
    """Check that computer is close it is not only available
    to anybody"""
    sequence_list = SequenceList()
    sequence_string = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      LoginTestVifibCustomer
      ComputerSetAllocationScopeClose
      Tic
      Logout
      SetSequenceSlaXmlCurrentComputer

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeClose
      CheckComputerTradeConditionDestinationSectionTestVifibCustomer
      Logout
    """ + self.prepare_published_software_release + \
      self.request_and_install_software + """
      # request as owner
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout

      # fail to instantiate for owner
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckNoRelatedSalePackingListLineForSoftwareInstance
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_allocation_scope_empty(self):
    """Check that computer's allocation scope is not set it is unavailable"""
    sequence_list = SequenceList()
    sequence_string = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      LoginTestVifibCustomer
      ComputerSetAllocationScopeEmpty
      Tic
      Logout
      SetSequenceSlaXmlCurrentComputer

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeEmpty
      CheckComputerTradeConditionDestinationSectionTestVifibCustomer
      Logout
    """ + self.prepare_published_software_release + \
      self.request_and_install_software + """
      # request as owner
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout

      # fail to instantiate for owner
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckNoRelatedSalePackingListLineForSoftwareInstance
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  prepare_open_public_computer = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenPublic
      Tic
      Logout
      SetSequenceSlaXmlCurrentComputer

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenPublic
      CheckComputerTradeConditionDestinationSectionListEmpty
      Logout
    """ + TestVifibSlapWebServiceMixin.prepare_published_software_release \
      + request_and_install_software

  def test_allocation_scope_public_software_instance_request(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string =  self.prepare_open_public_computer + """
      # request as someone else
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # now this computer patrition request new one
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartition
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRequestedComputerPartitionCleanParameterList
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_allocation_scope_personal_software_instance_request(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string =  self.prepare_open_public_computer + """
      # request as someone else
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # change allocation to personal
      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenPersonal
      Tic
      Logout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenPersonal
      CheckComputerTradeConditionDestinationSectionTestVifibCustomer
      Logout

      # now this computer patrition request new one
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotFoundResponse
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepStoreTestVifibAdminComputerPartitionCoordinate(self, sequence, **kw):
    sequence.edit(
      test_vifib_admin_computer_reference=sequence['computer_reference'],
      test_vifib_admin_computer_partition_reference=sequence[
        'computer_partition_reference'],
      test_vifib_admin_software_instance_reference=sequence[
        'software_instance_reference'],
      test_vifib_admin_software_instance_uid=sequence[
        'software_instance_uid'],
    )

  def stepRestoreTestVifibAdminComputerPartitionCoordinate(self,
    sequence, **kw):
    sequence.edit(
      computer_reference=sequence['test_vifib_admin_computer_reference'],
      computer_partition_reference=sequence[
        'test_vifib_admin_computer_partition_reference'],
        software_instance_reference=sequence[
          'test_vifib_admin_software_instance_reference'],
        software_instance_uid=sequence[
          'test_vifib_admin_software_instance_uid'],
    )

  def test_allocation_scope_friend_software_instance_request(self):
    self.computer_partition_amount = 3
    sequence_list = SequenceList()
    sequence_string =  self.prepare_open_public_computer + """
      # request as friend
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for friend
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      StoreTestVifibAdminComputerPartitionCoordinate

      # request as someone else
      LoginTestVifibCustomerA
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # change allocation to friend
      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenFriendTestVifibAdmin
      Tic
      Logout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenFriend
      CheckComputerTradeConditionDestinationSectionVifibAdminTestVifibCustomer
      Logout

      # now this computer patrition request new one
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotFoundResponse
      SlapLogout

      # now vifib_admin computer partition request new one and suceeds
      RestoreTestVifibAdminComputerPartitionCoordinate

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartition
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRequestedComputerPartitionCleanParameterList
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_allocation_scope_close_software_instance_request(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string =  self.prepare_open_public_computer + """
      # request as someone else
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # change allocation to close
      LoginTestVifibCustomer
      ComputerSetAllocationScopeClose
      Tic
      Logout

      LoginDefaultUser
      CheckComputerAllocationScopeClose
      CheckComputerTradeConditionDestinationSectionTestVifibCustomer
      Logout

      # now this computer patrition request new one
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotFoundResponse
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_allocation_scope_empty_software_instance_request(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string =  self.prepare_open_public_computer + """
      # request as someone else
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # change allocation to empty
      LoginTestVifibCustomer
      ComputerSetAllocationScopeEmpty
      Tic
      Logout

      LoginDefaultUser
      CheckComputerAllocationScopeEmpty
      CheckComputerTradeConditionDestinationSectionTestVifibCustomer
      Logout

      # now this computer patrition request new one
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotFoundResponse
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepSetSequenceSoftwareInstanceStateStopped(self, sequence, **kw):
    sequence['software_instance_state'] = 'stopped'

  def test_start_computer_partition_allocation_scope_close(self):
    """Check that it is possible to request stop of computer partition even
    if computer is close"""
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenPublic
      Tic
      Logout

      SetSequenceSlaXmlCurrentComputer
      SetSequenceSoftwareInstanceStateStopped

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenPublic
      CheckComputerTradeConditionDestinationSectionListEmpty
      Logout
    """ + self.prepare_published_software_release + \
      self.request_and_install_software + """
      # request as owner
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for owner
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # request as someone else
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # confirm instantiation
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout

      LoginDefaultUser
      SetSelectedComputerPartition
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      CheckComputerPartitionNoInstanceHostingSalePackingList
      Logout

      # close allocation scope of computer
      LoginTestVifibCustomer
      ComputerSetAllocationScopeClose
      Tic
      Logout

      LoginDefaultUser
      CheckComputerAllocationScopeClose
      CheckComputerTradeConditionDestinationSectionTestVifibCustomer
      Logout

      # request start and check that it worked
      LoginTestVifibAdmin
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
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapAllocationScope))
  return suite
