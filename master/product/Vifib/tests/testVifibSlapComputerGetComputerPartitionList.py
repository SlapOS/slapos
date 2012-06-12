from Products.ZSQLCatalog.SQLCatalog import Query, ComplexQuery
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import skip
import transaction
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from Products.DCWorkflow.DCWorkflow import ValidationFailed

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
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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

  @skip('ERP5/Zope does not follow REST API beacuse it is not possible to '
    'configure  Cookie Crumbler to ignore portal_slap')
  def test_Computer_getComputerPartitionList_unknowComputerUid(self):
    sequence_list = SequenceList()
    sequence_string = '\
      SlapLoginRandomComputer \
      CheckUnauthorizedSlapGetComputerPartitionListCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('ERP5/Zope does not follow REST API beacuse it is not possible to '
    'configure  Cookie Crumbler to ignore portal_slap')
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('ERP5/Zope does not follow REST API beacuse it is not possible to '
    'configure  Cookie Crumbler to ignore portal_slap')
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      CheckComputerPartitionInstanceHostingSalePackingListCancelled \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      CheckComputerPartitionInstanceSetupSalePackingListDelivered \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      CheckComputerPartitionInstanceHostingSalePackingListCancelled \
      CheckComputerPartitionInstanceCleanupSalePackingListDoesNotExists \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepDeliverInstanceSetupSalePackingList(self, sequence, **kw):
    delivery = self.portal.portal_catalog.getResultValue(
      default_aggregate_uid=ComplexQuery(
         Query(default_aggregate_uid=sequence['computer_partition_uid']),
         Query(default_aggregate_uid=sequence['software_instance_uid']),
         operator="AND"),
      portal_type=self.sale_packing_list_line_portal_type,
      simulation_state='stopped',
      resource_relative_url=self.portal.portal_preferences\
        .getPreferredInstanceSetupResource()
    ).getParentValue()
    self.portal.portal_workflow.doActionFor(delivery, 'deliver_action')

  def test_Computer_getComputerPartitionList_SetupResource_DeliveredState(self):
    """
    Check that calling Computer.getComputerPartitionList works in
    delivered state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_installed_computer_partition_sequence_string + '\
      CallVifibUpdateDeliveryCausalityStateAlarm \
      CleanTic \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceSetupSalePackingListDelivered \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      CheckComputerPartitionInstanceHostingSalePackingListCancelled \
      CheckComputerPartitionInstanceCleanupSalePackingListDoesNotExists \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      \
      LoginTestVifibCustomer \
      SetSoftwareTitleRandom \
      PersonRequestSlaveInstance \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CallConfirmOrderedSaleOrderAlarm \
      Tic \
      CheckComputerPartitionInstanceSetupSalePackingListDelivered \
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
      SetDeliveryLineAmountEqualOne \
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      \
      LoginTestVifibCustomer \
      SetSoftwareTitleRandom \
      PersonRequestSlaveInstance \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CallConfirmOrderedSaleOrderAlarm \
      Tic \
      SetDeliveryLineAmountEqualOne \
      CheckComputerPartitionInstanceSetupSalePackingListDelivered \
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
      SetDeliveryLineAmountEqualOne \
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      \
      LoginTestVifibCustomer \
      RequestSoftwareInstanceStop \
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
      SetDeliveryLineAmountEqualOne \
      CheckComputerPartitionInstanceHostingSalePackingListStopped \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      LoginTestVifibCustomer \
      SetSequenceSoftwareInstanceStateDestroyed \
      PersonRequestSoftwareInstance \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      SoftwareInstanceDestroyed \
      Tic \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered \
      CheckComputerPartitionIsFree \
      CheckOpenOrderLineRemoved \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      CheckDestroyedComputerPartitionGetStateCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      CheckSuccessComputerGetComputerPartitionCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
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
      CheckStartedComputerPartitionGetStateCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepSetSoftwareInstanceValidConnectionXML(self, sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    software_instance.edit(connection_xml="")

  def stepDamageSoftwareInstanceSlaXml(self, sequence, **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    self.assertRaises(ValidationFailed, instance.requestStart,
        software_release=instance.getRootSoftwareReleaseUrl(),
        instance_xml=instance.getTextContent(),
        software_type=instance.getSourceReference(),
        sla_xml="""DAMAGED<BAD?xml XMLversion="1.0" encoding="utf-8"?>""",
        shared=shared,
        )

  def stepDamageSoftwareInstanceConnectionXml(self, sequence, **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    instance.edit(connection_xml="""
    DAMAGED<BAD?xml XMLversion="1.0" encoding="utf-8"?>""")

  def stepDamageSoftwareInstanceXml(self, sequence, **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    self.assertRaises(ValidationFailed, instance.requestStart,
        software_release=instance.getRootSoftwareReleaseUrl(),
        instance_xml="""DAMAGED<BAD?xml XMLversion="1.0" encoding="utf-8"?>""",
        software_type=instance.getSourceReference(),
        sla_xml=instance.getSlaXml(),
        shared=shared,
        )

  def stepCheckDamageSoftwareInstanceSiteConsistency(self, sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])
    self.portal.portal_alarms.vifib_check_consistency.activeSense()
    transaction.commit()
    self.tic()
    consistency_error_list = self.portal.portal_alarms.vifib_check_consistency\
        .Alarm_getConsistencyCheckReportLineList()
    self.assertEqual(1, len(consistency_error_list))
    consistency_error = consistency_error_list[0]
    self.assertEqual(consistency_error.getObject().getPath(),
      software_instance.getPath())
    self.assertTrue('Sla XML is invalid' in str(consistency_error.getMessage()))
    self.assertTrue(self.portal.portal_alarms.vifib_check_consistency.sense())
    self.checkDivergency()

  def test_Computer_getComputerPartitionList_damaged_xml(self):
    """Check that getComputerPartitionList works in case of trying to damag XML,
    which is refused."""
    sequence_list = SequenceList()
    sequence_string = self\
      .prepare_install_requested_computer_partition_sequence_string + """
      LoginDefaultUser
      DamageSoftwareInstanceXml
      Logout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      Tic
      SlapLogout

      LoginDefaultUser
      SetSoftwareInstanceValidXML
      DamageSoftwareInstanceConnectionXml
      Logout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      Tic
      SlapLogout

      LoginDefaultUser
      SetSoftwareInstanceValidConnectionXML
      DamageSoftwareInstanceSlaXml
      Logout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      Tic
      SlapLogout

      LoginERP5TypeTestCase
      CheckDamageSoftwareInstanceSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)


def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerGetComputerPartitionList))
  return suite
