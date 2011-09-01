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

class TestVifibSlapComputerGetSoftwareReleaseList(TestVifibSlapWebServiceMixin):
  ########################################
  # Computer.getSoftwareReleaseList
  ########################################

  # ERP5/Zope does not follow REST API beacuse it is not possible to configure
  # Cookie Crumbler to ignore portal_slap
  @expectedFailure
  def test_Computer_getSoftwareReleaseList_unknowComputerUid(self):
    sequence_list = SequenceList()
    sequence_string = '\
      SlapLoginRandomComputer \
      CheckUnauthorizedComputerGetSoftwareReleaseListCall \
      Tic \
      SlapLogout \
      CheckUnexistingComputer \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  # ERP5/Zope does not follow REST API beacuse it is not possible to configure
  # Cookie Crumbler to ignore portal_slap
  @expectedFailure
  def test_Computer_getSoftwareReleaseList_draftComputer(self):
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      CreateDraftComputer \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckUnauthorizedComputerGetSoftwareReleaseListCall \
      Tic \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_validatedComputer(self):
    """
    Check that getSoftwareReleaseList returns an empty result if the
    validated computer is not related to any packing list.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_validatedAndDraftComputer(self):
    """
    Check that getSoftwareReleaseList returns an empty result if there are
    one draft and one validated computer.
    """
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      CreateDraftComputer \
      Tic \
      Logout '\
      + self.prepare_computer + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  # ERP5/Zope does not follow REST API beacuse it is not possible to configure
  # Cookie Crumbler to ignore portal_slap
  @expectedFailure
  def test_Computer_getSoftwareReleaseList_TwoValidatedComputer(self):
    # XXX: It shall be part of VifibMachineAuthentication test suite
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      LoginDefaultUser \
      DuplicateAndValidateCurrentComputer \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckUnauthorizedComputerGetSoftwareReleaseListCall \
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

  def test_Computer_getSoftwareReleaseList_SetupResource_ConfirmedState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    confirmed state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_SetupResource_CancelledState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    cancelled state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      CancelPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_SetupResource_StartedState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    started state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_SetupResource_StoppedState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    stopped state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      StopPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_SetupResource_DeliveredState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    delivered state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      StopPurchasePackingList \
      Tic \
      DeliverPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_AccountingResource_ConfirmedState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    confirmed state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_software_release_purchase_packing_list_accounting_resource + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_AccountingResource_CancelledState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    cancelled state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_software_release_purchase_packing_list_accounting_resource + '\
      LoginDefaultUser \
      CancelPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_AccountingResource_StartedState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    started state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_software_release_purchase_packing_list_accounting_resource + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_AccountingResource_StoppedState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    stopped state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_software_release_purchase_packing_list_accounting_resource + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      StopPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_AccountingResource_DeliveredState(self):
    """
    Check that calling Computer.getSoftwareReleaseList works in 
    delivered state with the accounting resource
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_software_release_purchase_packing_list_accounting_resource + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      StopPurchasePackingList \
      Tic \
      DeliverPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepSetCurrentPurchasePackingListAsA(self, sequence):
    sequence.edit(purchase_packing_list_a_uid=sequence[
      'purchase_packing_list_uid'])

  def stepSetCurrentPurchasePackingListAsB(self, sequence):
    sequence.edit(purchase_packing_list_b_uid=sequence[
      'purchase_packing_list_uid'])

  def stepStepPurchasePackingListBStartDateAfterPurchasePackingListA(self,
      sequence):
    a = self.portal.portal_catalog.getResultValue(uid=sequence[
      'purchase_packing_list_a_uid'])
    b = self.portal.portal_catalog.getResultValue(uid=sequence[
      'purchase_packing_list_b_uid'])
    b.setStartDate(a.getStartDate() + 2)

  def stepStepPurchasePackingListBStartDateBeforePurchasePackingListA(self,
      sequence):
    a = self.portal.portal_catalog.getResultValue(uid=sequence[
      'purchase_packing_list_a_uid'])
    b = self.portal.portal_catalog.getResultValue(uid=sequence[
      'purchase_packing_list_b_uid'])
    b.setStartDate(a.getStartDate() - 2)

  def stepCheckStoppedPurchasePackingListA(self, sequence):
    self.assertEqual('stopped',
        self.portal.portal_catalog.getResultValue(uid=sequence[
          'purchase_packing_list_a_uid']).getSimulationState())

  def stepCheckConfirmedPurchasePackingListB(self, sequence):
    self.assertEqual('confirmed',
        self.portal.portal_catalog.getResultValue(uid=sequence[
          'purchase_packing_list_b_uid']).getSimulationState())

  def stepCheckStartedPurchasePackingListB(self, sequence):
    self.assertEqual('started',
        self.portal.portal_catalog.getResultValue(uid=sequence[
          'purchase_packing_list_b_uid']).getSimulationState())

  def stepCheckStoppedPurchasePackingListB(self, sequence):
    self.assertEqual('stopped',
        self.portal.portal_catalog.getResultValue(uid=sequence[
          'purchase_packing_list_b_uid']).getSimulationState())

  def stepCheckSlaveInstanceSecurityWithDifferentCustomer(self, sequence):
    software_instance_uid = sequence["software_instance_uid"]
    portal_membership = self.portal.portal_membership
    username = portal_membership.getAuthenticatedMember().getUserName()
    self.login()
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)
    self.failIfUserCanViewDocument(username, software_instance)
    self.failIfUserCanAccessDocument(username, software_instance)
    self.login(username)

  def stepCheckTwoSlaveInstanceRequest(self, sequence):
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=sequence["computer_partition_uid"])
    sale_packing_list_line_list = computer_partition.getAggregateRelatedValueList(
        portal_type=self.sale_packing_list_line_portal_type)
    portal_type_list = [self.software_instance_portal_type,
        self.slave_instance_portal_type]
    instance_list = filter(None, [obj.getAggregateValue(portal_type=portal_type_list) \
        for obj in sale_packing_list_line_list])
    portal_type_list = [instance.getPortalType() for instance in instance_list]
    expected_portal_type_list = [self.slave_instance_portal_type,
        self.slave_instance_portal_type,
        self.software_instance_portal_type]
    self.assertEquals(expected_portal_type_list, sorted(portal_type_list))
    computer_partition_list = [obj.getAggregateValue(
      portal_type=self.computer_partition_portal_type) \
          for obj in sale_packing_list_line_list]
    uid_list = [computer_partition.getUid() \
        for computer_partition in computer_partition_list]
    self.assertEquals(1, len(set(uid_list)))

  def stepCheckSlaveInstanceReady(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    self.assertEquals(self.slave_instance_portal_type,
        slave_instance.getPortalType())
    sale_order_line = slave_instance.getAggregateRelatedValue(
        portal_type=self.sale_order_line_portal_type)
    self.assertEquals("confirmed", sale_order_line.getSimulationState())
    sale_packing_list_line = slave_instance.getAggregateRelatedValue(
        portal_type=self.sale_packing_list_line_portal_type)
    self.assertNotEquals(sale_packing_list_line.getAggregateValue(
      portal_type=self.computer_partition_portal_type), None)

  def stepCheckSlaveInstanceAssociationWithSoftwareInstance(self, sequence):
    portal_catalog = self.portal.portal_catalog
    computer_partition_reference_list = \
        sequence['computer_partition_reference_list']
    for reference in computer_partition_reference_list:
      computer_partition = portal_catalog.getResultValue(
          portal_type="Computer Partition", reference=reference)
      sale_packing_list_line_list = portal_catalog(
          portal_type="Sale Packing List Line",
          aggregate_relative_url=computer_partition.getRelativeUrl())
      software_release_uri_list = []
      for sale_packing_list_line in sale_packing_list_line_list:
        software_release_uri = sale_packing_list_line.getResultValue(
            portal_type="Software Release")
        software_release_uri_list.append(software_release_uri.getUrlString())
      self.assertEquals(1, len(set(software_release_uri_list)))

  def stepCheckSlaveInstanceAllocationWithTwoDifferentSoftwareInstance(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    self.assertEquals(self.slave_instance_portal_type,
        slave_instance.getPortalType())
    sale_packing_list_line = slave_instance.getAggregateRelatedValue(
        portal_type=self.sale_packing_list_line_portal_type)
    software_release = sale_packing_list_line.getAggregateValue(
        portal_type=self.software_release_portal_type)
    sale_packing_list_line_list = software_release.aggregateRelatedValues(
        portal_type=self.sale_packing_list_line_portal_type)
    computer_partition_list = [obj.getAggregateValue(
      portal_type=self.computer_partition_portal_type)\
          for obj in sale_packing_list_line_list]
    self.assertEquals(computer_partition_list[0],
        computer_partition_list[1])
    self.assertEquals(computer_partition_list[0].getReference(),
        computer_partition_list[1].getReference())
    self.assertEquals(2, len(computer_partition_list))

  def stepCheckSlaveInstanceNotReady(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    self.assertEquals(self.slave_instance_portal_type,
        slave_instance.getPortalType())
    sale_order_line = slave_instance.getAggregateRelatedValue(
        portal_type=self.sale_order_line_portal_type)
    self.assertEquals("ordered", sale_order_line.getSimulationState())
    self.assertRaises(ValueError, sale_order_line.confirm)
    sale_packing_list_line = slave_instance.getAggregateRelatedValue(
        portal_type=self.sale_packing_list_line_portal_type)
    self.assertEquals(sale_packing_list_line, None)

  def stepSelectSlaveInstanceFromOneComputerPartition(self, sequence):
    slave_instance = self._getSlaveInstanceFromCurrentComputerPartition(sequence)
    sequence.edit(software_instance_uid=slave_instance.getUid())

  def stepCheckEmptySlaveInstanceListFromOneComputerPartition(self, sequence):
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        partition_id)
    parameter_dict = computer_partition.getInstanceParameterDict()
    slave_instance_list = parameter_dict["slave_instance_list"]
    self.assertEquals([], slave_instance_list)

  def stepCheckSlaveInstanceListFromOneComputerPartition(self, sequence,
          expected_amount=1):
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        partition_id)
    parameter_dict = computer_partition.getInstanceParameterDict()
    self.assertEquals("RootSoftwareInstance",
        parameter_dict["slap_software_type"])
    slave_instance_list = parameter_dict["slave_instance_list"]
    self.assertEquals(expected_amount, len(slave_instance_list))
    for slave_instance in slave_instance_list:
      self.assertEquals("SlaveInstance", slave_instance["slap_software_type"])

  def stepCheckTwoSlaveInstanceListFromOneComputerPartition(self, sequence):
    self.stepCheckSlaveInstanceListFromOneComputerPartition(sequence, 
        expected_amount=2)

  def stepCheckSlaveInstanceAccessUsingCurrentSoftwareInstanceUser(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    portal_membership = self.portal.portal_membership
    username = portal_membership.getAuthenticatedMember().getUserName()
    self.assertUserCanViewDocument(username, slave_instance)
    self.assertUserCanAccessDocument(username, slave_instance)

  def stepSlapLoginSoftwareInstanceFromCurrentSoftwareInstance(self, sequence):
    software_instance = self._getSoftwareInstanceFromCurrentComputerPartition(
        sequence)
    self.assertNotEquals(None, software_instance)
    self.stepSlapLogout()
    global REMOTE_USER
    REMOTE_USER = software_instance.getReference()
    self.login(software_instance.getReference())

  def _getSoftwareInstanceFromCurrentComputerPartition(self, sequence):
    query = ComplexQuery(
        Query(aggregate_uid=sequence['computer_partition_uid']),
        Query(aggregate_portal_type=self.software_instance_portal_type),
        operator="AND")
    software_instance = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Packing List Line",
        sort_on=(('movement.start_date', 'DESC'),),
        query=query).getAggregateValue(portal_type="Software Instance")
    return software_instance

  def _getSlaveInstanceFromCurrentComputerPartition(self, sequence):
    query = ComplexQuery(
        Query(aggregate_uid=sequence['computer_partition_uid']),
        Query(aggregate_portal_type=self.slave_instance_portal_type),
        operator="AND")
    slave_instance = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Packing List Line",
        query=query).getAggregateValue(portal_type=self.slave_instance_portal_type)
    return slave_instance

  def stepRequestDestroySoftwareInstanceFromCurrentComputerPartition(self, sequence):
    software_instance = self._getSoftwareInstanceFromCurrentComputerPartition(
        sequence)
    software_instance.requestDestroyComputerPartition()

  def stepStartSoftwareInstanceFromCurrentComputerPartition(self, sequence):
    software_instance = self._getSoftwareInstanceFromCurrentComputerPartition(
        sequence)
    software_instance.requestStartComputerPartition()

  def stepRequestStopSoftwareInstanceFromCurrentComputerPartition(self,
      sequence):
    software_instance = self._getSoftwareInstanceFromCurrentComputerPartition(
        sequence)
    software_instance.requestStopComputerPartition()

  def stepCheckSalePackingListFromSlaveInstanceAccessUsingSoftwareInstanceUser(self,
      sequence):
    portal_membership = self.portal.portal_membership
    sale_packing_list_line = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Packing List Line",
        uid=sequence["sale_packing_list_line_uid"])
    username = portal_membership.getAuthenticatedMember().getUserName()
    self.assertUserCanViewDocument(username, sale_packing_list_line)
    self.failIfUserCanModifyDocument(username, sale_packing_list_line)

  def stepCheckSaleOrderFromSlaveInstanceAccessUsingSoftwareInstanceUser(self,
      sequence):
    portal_membership = self.portal.portal_membership
    sale_order = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Order",
        uid=sequence["sale_order_uid"])
    username = portal_membership.getAuthenticatedMember().getUserName()
    self.assertUserCanViewDocument(username, sale_order)
    self.failIfUserCanModifyDocument(username, sale_order)

  def stepCheckHostingSubscriptionFromSlaveInstanceAccessUsingSoftwareInstanceUser(self,
      sequence):
    portal_membership = self.portal.portal_membership
    sale_packing_list_line = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Packing List Line",
        uid=sequence["sale_packing_list_line_uid"])
    hosting_subscription = sale_packing_list_line.getAggregateValue(
        portal_type="Hosting Subscription")
    username = portal_membership.getAuthenticatedMember().getUserName()
    self.assertUserCanViewDocument(username, hosting_subscription)
    self.failIfUserCanModifyDocument(username, hosting_subscription)

  def stepStoreSaleOrderFromSlaveInstance(self, sequence):
    sale_order_line = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Order Line",
        aggregate_reference=sequence["software_instance_reference"])
    sequence.edit(sale_order_line_uid=sale_order_line.getUid(),
        sale_order_uid=sale_order_line.getParent().getUid())

  def stepStoreSalePackingListLineFromSlaveInstance(self, sequence):
    sale_packing_list_line = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Packing List Line",
        aggregate_uid=sequence["software_instance_uid"])
    sequence.edit(sale_packing_list_line_uid=sale_packing_list_line.getUid(),
        sale_packing_list_uid=sale_packing_list_line.getParent().getUid())

  def stepSetConnectionXmlToSlaveInstance(self, sequence):
    computer_reference = sequence["computer_reference"]
    computer_partition_reference = sequence["computer_partition_reference"]
    site_url = "https://www.example.com:8080/"
    connection_dict = dict(site_url=site_url)
    slave_reference = sequence["software_instance_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_reference, computer_partition_reference)
    computer_partition.setConnectionDict(connection_dict)
    sequence.edit(site_url=site_url)
    connection_dict["site_url"] += "DeF45uef"
    computer_partition.setConnectionDict(connection_dict,
        slave_reference)
    sequence.edit(slave_instance_site_url=site_url)

  def stepCheckConnectionXmlFromSlaveInstance(self, sequence):
    portal_catalog = self.portal.portal_catalog
    slave_instance = portal_catalog.getResultValue(
        reference=sequence["software_instance_reference"])
    self.assertTrue(sequence["slave_instance_site_url"] in \
        slave_instance.getConnectionXml())

  def stepCheckConnectionXmlFromSoftwareInstance(self, sequence):
    software_instance = self.portal.portal_catalog.getResultValue(
      portal_type="Software Instance")
    self.assertTrue("%s</parameter>" % sequence["site_url"] in \
        software_instance.getConnectionXml())

  def stepSlaveInstanceStarted(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence["software_instance_uid"])
    slave_instance.startComputerPartition()

  def stepRequestSlaveInstanceStart(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence["software_instance_uid"])
    slave_instance.requestStartComputerPartition()

  def stepRequestSlaveInstanceStop(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence["software_instance_uid"])
    slave_instance.requestStopComputerPartition()

  def stepSlaveInstanceStopped(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence["software_instance_uid"])
    slave_instance.stopComputerPartition()

  def stepSlaveInstanceStopComputerPartitionInstallation(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence["software_instance_uid"])
    slave_instance.stopComputerPartitionInstallation()

  def stepSetDeliveryLineAmountEqualZero(self, sequence):
    sequence.edit(delivery_line_amount=0)

  def stepSetDeliveryLineAmountEqualTwo(self, sequence):
    sequence.edit(delivery_line_amount=2)

  def stepSetDeliveryLineAmountEqualThree(self, sequence):
    sequence.edit(delivery_line_amount=3)

  def stepSetDeliveryLineAmountEqualOne(self, sequence):
    sequence.edit(delivery_line_amount=1)

  def test_Computer_getSoftwareReleaseList_twoPurchasePackingList(self):
    """
    Check that calling Computer.getSoftwareReleaseList uses the
    Purchase Packing List in proper state, regardless its date
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_two_purchase_packing_list + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout \
      LoginDefaultUser \
      StepPurchasePackingListBStartDateAfterPurchasePackingListA \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout \
      LoginDefaultUser \
      StepPurchasePackingListBStartDateBeforePurchasePackingListA \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      Tic \
      SlapLogout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_twoActivePurchasePackingList(self):
    """
    Check that getSoftwareReleaseList only returns 1 software release if it is
    associated to 2 purchase packing list.
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      Tic \
      CreatePurchasePackingList \
      Tic \
      CreatePurchasePackingListLine \
      Tic \
      SetPurchasePackingListLineSetupResource \
      SetPurchasePackingListLineAggregate \
      ConfirmPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerGetSoftwareReleaseList))
  return suite
