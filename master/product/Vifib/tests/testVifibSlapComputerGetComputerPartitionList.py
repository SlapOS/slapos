from DateTime import DateTime
from AccessControl.SecurityManagement import newSecurityManager
from Products.ERP5Type.Errors import UnsupportedWorkflowMethod
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import expectedFailure
from Products.ERP5Type.tests.backportUnittest import skip
from Products.ERP5Type.tests.SecurityTestCase import AssertNoPermissionMethod, \
    AssertPermissionMethod
from Products.ERP5Type import Permissions
from Products.ZSQLCatalog.SQLCatalog import Query, ComplexQuery
from VifibMixin import testVifibMixin
from random import random
from slapos import slap
import urllib
import urlparse
import httplib
from xml_marshaller import xml_marshaller
import transaction
import unittest

class TestVifibSlapComputerGetComputerPartitionList(TestVifibSlapWebServiceMixin):
  ########################################
  # Computer.getComputerPartitionList
  ########################################
  def test_Computer_getComputerPartitionList_validatedComputer(self):
    """
    Check that getComputerPartitionList returns an empty result if the
    validated computer is not related to any packing list.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_emptyPartition(self):
    """
    Check that getComputerPartitionList returns nothing if Computer Partition
    is not related with proper Sale Packing List Line
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_twoEmptyPartition(self):
    """
    Check that getComputerPartitionList returns nothing if Computer Partitions
    are not related with proper Sale Packing List Lines
    """
    self.computer_partition_amount = 2
    self.test_Computer_getComputerPartitionList_emptyPartition()

  # ERP5/Zope does not follow REST API beacuse it is not possible to configure
  # Cookie Crumbler to ignore portal_slap
  @expectedFailure
  def test_Computer_getComputerPartitionList_unknowComputerUid(self):
    sequence_list = SequenceList()
    sequence_string = '\
      SlapLoginRandomComputer \
      CheckUnauthorizedSlapGetComputerPartitionListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  # ERP5/Zope does not follow REST API beacuse it is not possible to configure
  # Cookie Crumbler to ignore portal_slap
  @expectedFailure
  def test_Computer_getComputerPartitionList_draftComputer(self):
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      CreateDraftComputer \
      Tic \
      Logout \
      \
      SlapLoginRandomComputer \
      CheckUnauthorizedSlapGetComputerPartitionListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_validatedAndDraftComputer(self):
    """
    Check that getComputerPartitionList returns an empty result if there are
    one draft and one validated computer.
    """
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      CreateDraftComputer \
      Tic \
      Logout \
      ' + self.prepare_computer + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  # ERP5/Zope does not follow REST API beacuse it is not possible to configure
  # Cookie Crumbler to ignore portal_slap
  @expectedFailure
  def test_Computer_getComputerPartitionList_TwoValidatedComputer(self):
    # XXX: It shall be part of VifibMachineAuthentication test suite
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      \
      LoginDefaultUser \
      DuplicateAndValidateCurrentComputer \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckUnauthorizedSlapGetComputerPartitionListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    try:
      sequence_list.play(self)
    finally:
      self.login('ERP5TypeTestCase')
      for c in self.portal.computer_module.contentValues():
        if c.getValidationState() == 'validated':
          c.invalidate()
          transaction.commit()

  def test_Computer_getComputerPartitionList_SetupResource_CancelledState(self):
    """
    Check that calling Computer.getComputerPartitionList works in
    cancelled state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      LoginDefaultUser \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      CheckComputerPartitionInstanceSetupSalePackingListCancelled \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      CheckComputerPartitionInstanceCleanupSalePackingListCancelled \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_SetupResource_ConfirmedState(self):
    """
    Check that calling Computer.getComputerPartitionList works in
    confirmed state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      Tic \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_SetupResource_StartedState(self):
    """
    Check that calling Computer.getComputerPartitionList works in
    started state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_building_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_SetupResource_StoppedState(self):
    """
    Check that calling Computer.getComputerPartitionList works in
    stopped state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_installed_computer_partition_sequence_string + '\
      LoginDefaultUser \
      Tic \
      CheckComputerPartitionInstanceSetupSalePackingListStopped \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      CheckComputerPartitionInstanceHostingSalePackingListCancelled \
      CheckComputerPartitionInstanceCleanupSalePackingListDoesNotExists \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_SetupResource_DeliveredState(self):
    """
    Check that calling Computer.getComputerPartitionList works in
    delivered state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_installed_computer_partition_sequence_string + '\
      LoginDefaultUser \
      DeliverSalePackingList \
      Tic \
      CheckComputerPartitionInstanceSetupSalePackingListDelivered \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      CheckComputerPartitionInstanceHostingSalePackingListCancelled \
      CheckComputerPartitionInstanceCleanupSalePackingListDoesNotExists \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_HostingResource_CancelledState(self):
    """
    Check that calling Computer.getComputerPartitionList works in
    cancelled state with the hosting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_start_requested_computer_partition_sequence_string + '\
      LoginDefaultUser \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_HostingResource_ConfirmedState(self):
    """
    Check that calling Computer.getComputerPartitionList works in
    confirmed state with the hosting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_start_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_HostingResource_StartedState(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    started state with the hosting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_HostingResource_StartedState_with_slave(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    started state with the hosting resource when a Slave Partition is present.

    We validate checking more them one Slave Instance allocation.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
      \
      LoginTestVifibCustomer \
      PersonRequestSlaveInstance \
      SlapLogout \
      \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SoftwareInstanceAvailable \
      Tic \
      CheckSuccessComputerGetComputerPartitionCall \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      SetDeliveryLineAmountEqualTwo \
      CheckComputerPartitionInstanceHostingSalePackingListStarted \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
      \
      LoginTestVifibCustomer \
      PersonRequestSlaveInstance \
      SlapLogout \
      \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceAvailable \
      Tic \
      CheckSuccessComputerGetComputerPartitionCall \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      SetDeliveryLineAmountEqualThree \
      CheckComputerPartitionInstanceHostingSalePackingListStarted \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
      \
      LoginTestVifibCustomer \
      RequestSlaveInstanceStop \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      SetDeliveryLineAmountEqualTwo \
      CheckComputerPartitionInstanceHostingSalePackingListStarted \
      SetDeliveryLineAmountEqualOne \
      CheckComputerPartitionInstanceHostingSalePackingListDelivered \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_HostingResource_StoppedState(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    stopped state with the hosting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_stop_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_HostingResource_DeliveredState(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    delivered state with the hosting resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_stopped_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_CleanupResource_CancelledState(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    cancelled state with the cleanup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_destroy_requested_computer_partition + '\
      LoginDefaultUser \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckStartedComputerPartitionGetStateCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_CleanupResource_ConfirmedState(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    confirmed state with the cleanup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_destroy_requested_computer_partition + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_CleanupResource_StartedState(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    started state with the cleanup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_destroy_requested_computer_partition + '\
      LoginDefaultUser \
      SelectCurrentlyUsedSalePackingListUid \
      StartSalePackingList \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_CleanupResource_StoppedState(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    stopped state with the cleanup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_destroy_requested_computer_partition + '\
      LoginDefaultUser \
      SelectCurrentlyUsedSalePackingListUid \
      StartSalePackingList \
      Tic \
      StopSalePackingList \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_CleanupResource_DeliveredState(self):
    """
    Check that calling Computer.getComputerPartitionList works in
    delivered state with the cleanup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_destroyed_computer_partition + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetComputerPartitionCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_AccountingResource_CancelledState(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    cancelled state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_computer_partition_accounting_resource_sequence_string + '\
      LoginDefaultUser \
      CancelSalePackingList \
      Tic \
      CheckComputerPartitionAccoutingResourceSalePackingListCancelled \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckStartedComputerPartitionGetStateCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_AccountingResource_ConfirmedState(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    confirmed state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_computer_partition_accounting_resource_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckStartedComputerPartitionGetStateCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_AccountingResource_StartedState(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    started state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string =  \
        self.prepare_computer_partition_accounting_resource_started_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckStartedComputerPartitionGetStateCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_AccountingResource_StoppedState(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    stopped state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string =  \
        self.prepare_computer_partition_accounting_resource_stopped_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckStartedComputerPartitionGetStateCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_AccountingResource_DeliveredState(self):
    """
    Check that calling Computer.getComputerPartitionList works in 
    delivered state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string =  \
        self.prepare_computer_partition_accounting_resource_delivered_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckStartedComputerPartitionGetStateCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getComputerPartitionList_twoSalePackingList(self):
    """
    Check that calling Computer.getComputerPartitionList uses the latest sale packing
    list for calculation
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_start_requested_computer_partition_sequence_string + '\
      LoginDefaultUser \
      SetHostingAfterSetupStartDate \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckStartedComputerPartitionGetStateCall \
      SlapLogout \
      Tic \
      LoginDefaultUser \
      CheckSalePackingListNoErrorText \
      SetHostingBeforeSetupStartDate \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckStoppedComputerPartitionGetStateCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerGetComputerPartitionList))
  return suite
