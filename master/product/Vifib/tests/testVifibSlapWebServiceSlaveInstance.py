from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from Products.ERP5Type.tests.backportUnittest import skip
from Products.ZSQLCatalog.SQLCatalog import Query, ComplexQuery

class TestVifibSlapWebServiceSlaveInstance(TestVifibSlapWebServiceMixin):
  def stepCheckComputerPartitionSaleOrderAggregatedList(self, sequence):
    portal_catalog = self.portal.portal_catalog
    sale_packing_list = portal_catalog.getResultValue(
        uid=sequence['sale_packing_list_uid'])
    sale_packing_list_line = sale_packing_list.objectValues()[0]
    computer_partition = sale_packing_list_line.getAggregateValue(
        portal_type=self.computer_partition_portal_type)
    sale_order_line_list = computer_partition.getAggregateRelatedValueList(
        portal_type="Sale Order Line")
    sale_order_line_1, sale_order_line_2 = sale_order_line_list
    self.assertEquals(sale_order_line_1.getAggregateValue(
                        portal_type=self.computer_partition_portal_type),
                      sale_order_line_2.getAggregateValue(
                        portal_type=self.computer_partition_portal_type))
    self.assertEquals(2, len(sale_order_line_list))
    query = ComplexQuery(
        Query(default_aggregate_uid=computer_partition.getUid()),
        Query(default_resource_uid=self.portal.restrictedTraverse(
          self.portal.portal_preferences.getPreferredInstanceSetupResource()
            ).getUid()),
        operator="AND"
    )
    sale_packing_line_list = portal_catalog(
        portal_type="Sale Packing List Line",
        query=query
        )
    self.assertEquals(2, len(sale_packing_line_list))
    sale_packing_list_line_1, sale_packing_list_line_2 = sale_packing_line_list
    self.assertEquals(sale_packing_list_line_1.getAggregateValue(
                        portal_type=self.software_release_portal_type),
                      sale_packing_list_line_2.getAggregateValue(
                        portal_type=self.software_release_portal_type))
    self.assertEquals(sale_packing_list_line_1.getAggregateValue(
                        portal_type=self.computer_partition_portal_type),
                      sale_packing_list_line_2.getAggregateValue(
                        portal_type=self.computer_partition_portal_type))
    hosting_1, hosting_2 = [hosting.getAggregateValue(
      portal_type=self.hosting_subscription_portal_type) \
          for hosting in sale_packing_line_list]
    self.assertNotEquals(hosting_1, hosting_2)

  def test_SlaveInstance_Person_request_with_Different_User(self):
    """
      Check that user B can declare a slot of slave instance in computer
      partition used by user A
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
    SlapLogout
    LoginAsCustomerA
    PersonRequestSlaveInstance
    Tic
    Logout
    LoginDefaultUser
    CallConfirmOrderedSaleOrderAlarm
    Tic
    Tic # in order to call real build
    CheckComputerPartitionSaleOrderAggregatedList
    Logout
    LoginERP5TypeTestCase
    CheckSiteConsistency
    Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_request_after_destroy_SlaveInstance(self):
    """
      Check that a Slave Instance will not be allocated when a Software
      Instance is destroyed 
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_installed_computer_partition_sequence_string + """
        LoginTestVifibCustomer
        RequestSoftwareInstanceDestroy
        Tic
        SlapLogout
        LoginDefaultUser
        CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
        SlapLogout
        LoginTestVifibCustomer
        SetSoftwareTitleRandom
        PersonRequestSlaveInstance
        Tic
        Logout
        LoginDefaultUser
        CallConfirmOrderedSaleOrderAlarm
        Tic
        CheckSlaveInstanceNotReady
        Logout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_Person_request_SlaveInstance(self):
    """
      Check that one Slave Instance is created correctly
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
    Tic
    LoginTestVifibCustomer
    SetSoftwareTitleRandom
    PersonRequestSlaveInstance
    Tic
    Logout

    LoginDefaultUser
    CallConfirmOrderedSaleOrderAlarm
    Tic
    
    SetSelectedComputerPartition
    SelectCurrentlyUsedSalePackingListUid
    Logout

    LoginDefaultUser
    CheckComputerPartitionSaleOrderAggregatedList
    Logout

    LoginERP5TypeTestCase
    CheckSiteConsistency
    Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_getInstanceParameterDict_with_SlaveInstance_stopped(self):
    """
      Check that the Slave Instance is ignored when the state of Sale Packing
      List in stopped.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      SlapLogout
      LoginTestVifibCustomer
      SlaveInstanceStarted
      Tic
      SlaveInstanceStopped
      Tic
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStopped
      SlapLoginCurrentComputer
      CheckEmptySlaveInstanceListFromOneComputerPartition
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_getInstanceParameterDict_with_two_SlaveInstance(self):
    """
      Check that with two Slave Instance installed in different computers, the
      method getInstanceParameterDict returns correctly the slave instance list
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """ 
      Tic
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      CallConfirmOrderedSaleOrderAlarm
      Tic 
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic """ + self.prepare_formated_computer + """
      Tic
      LoginTestVifibDeveloper \
      SelectNewSoftwareReleaseUri \
      CreateSoftwareRelease \
      Tic \
      SubmitSoftwareRelease \
      Tic \
      CreateSoftwareProduct \
      Tic \
      ValidateSoftwareProduct \
      Tic \
      SetSoftwareProductToSoftwareRelease \
      PublishByActionSoftwareRelease \
      Tic
      Logout \
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout
      Tic
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSoftwareInstance
      CleanTic
      CallConfirmOrderedSaleOrderAlarm
      Tic
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      CallConfirmOrderedSaleOrderAlarm
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      CheckSlaveInstanceListFromOneComputerPartition

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """

    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_Person_request_without_SoftwareInstance(self):
    """
      Check that one Slave Instance will wait allocation correctly when no
      exists Software Instance installed
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + \
      self.prepare_published_software_release + """
      Tic
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      CallConfirmOrderedSaleOrderAlarm
      Tic
      CheckSlaveInstanceNotReady
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_Person_request_with_Two_Different_ComputerPartition(self):
    """
      Check that one Slave Instance is allocated correctly when exists two different
      Software Instances and Computer Partition. The slave instance must be
      allocated in Computer Partition that exists one Software Instance with
      the same Software Release.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
    Tic
    StoreSoftwareReleaseUri
    SetRandomComputerReference
    """ + self.prepare_install_requested_computer_partition_sequence_string + """
    Tic
    LoginTestVifibCustomer
    SetSoftwareTitleRandom
    PersonRequestSlaveInstance
    Tic
    CallConfirmOrderedSaleOrderAlarm
    Tic
    CheckSlaveInstanceReady
    CheckSlaveInstanceAllocationWithTwoDifferentSoftwareInstance

    LoginERP5TypeTestCase
    CheckSiteConsistency
    Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_Person_request_with_Two_Different_SoftwareInstance(self):
    """
      Check that one Slave Instance is allocated correctly when exists two different
      Software Instances. The slave instance must be allocated in the same
      Computer Partition that exists one Software Instance installed.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      StoreSoftwareReleaseUri
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      CallConfirmOrderedSaleOrderAlarm
      Tic
      """ + self.prepare_published_software_release + """
      Tic
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSoftwareInstance
      CleanTic
      CallConfirmOrderedSaleOrderAlarm
      Tic
      SelectDifferentSoftwareReleaseUri
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      CallConfirmOrderedSaleOrderAlarm
      Tic
      CheckSlaveInstanceAssociationWithSoftwareInstance
      SlapLogout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_Person_request_twice(self):
    """
      Check that request a Slave Instance twice, the instances are created
      correctly
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      LoginAsCustomerA
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      SlapLogout

      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      Tic
      SlapLogout

      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      CheckTwoSlaveInstanceRequest
      SlapLogout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip("Not Implemented yet")
  def test_request_SlaveInstance_without_enough_slots(self):
    """
     Check the behaviour when one Slave Instance is requested and not exist one
     available slot
    """
    raise NotImplementedError

  def test_SlaveInstance_request_start_from_SoftwareInstance(self):
    """
      Check that the Slave Instance will be started correctly when
      a Software Instance is started
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      SlapLogout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      LoginTestVifibCustomer
      StartSoftwareInstanceFromCurrentComputerPartition
      Tic
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SlapLogout
      LoginDefaultUser
      SetDeliveryLineAmountEqualOne
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      LoginTestVifibCustomer
      RequestStopSoftwareInstanceFromCurrentComputerPartition
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      StartSoftwareInstanceFromCurrentComputerPartition
      Tic
      SoftwareInstanceStarted
      Tic
      RequestStopSoftwareInstanceFromCurrentComputerPartition
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      StartSoftwareInstanceFromCurrentComputerPartition
      Tic
      SoftwareInstanceStarted
      Tic
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      SlapLogout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      LoginTestVifibCustomer
      RequestSoftwareInstanceStart
      Tic
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SetDeliveryLineAmountEqualOne
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      RequestStopSoftwareInstanceFromCurrentComputerPartition
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      LoginTestVifibCustomer
      StartSoftwareInstanceFromCurrentComputerPartition
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepStoreCurrentSoftwareInstanceBufferA(self, sequence, **kw):
    sequence.edit(
      software_instance_uid_buffer_a=sequence['software_instance_uid'],
      software_instance_reference_buffer_a=sequence[
        'software_instance_reference'])

  def stepStoreCurrentSoftwareInstanceBufferB(self, sequence, **kw):
    sequence.edit(
      software_instance_uid_buffer_b=sequence['software_instance_uid'],
      software_instance_reference_buffer_b=sequence[
        'software_instance_reference'])

  def stepRestoreCurrentSoftwareInstanceBufferA(self, sequence, **kw):
    sequence.edit(
      software_instance_uid=sequence['software_instance_uid_buffer_a'],
      software_instance_reference=sequence[
        'software_instance_reference_buffer_a'])

  def stepRestoreCurrentSoftwareInstanceBufferB(self, sequence, **kw):
    sequence.edit(
      software_instance_uid=sequence['software_instance_uid_buffer_b'],
      software_instance_reference=sequence[
        'software_instance_reference_buffer_b'])

  def test_SlaveInstance_request_stop(self):
    """
      Check that the Slave Instance will be stopped correctly
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + """
      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      SlapLogout
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      CheckSuccessComputerGetComputerPartitionCall
      SoftwareInstanceStarted
      Tic
      SlapLogout
      LoginTestVifibCustomer
      RequestSoftwareInstanceStop
      Tic
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStopped
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SoftwareInstanceStarted
      Tic
      SlapLogout
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStopped
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
     """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckComputerPartitionIsBusy(self, sequence, **kw):
    computer_partition_uid = sequence["computer_partition_uid"]
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=computer_partition_uid)
    self.assertEqual('busy', computer_partition.getSlapState())

  def test_SlaveInstance_request_destroy(self):
    """
      Check that the Slave Instance will be destroyed correctly
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      LoginTestVifibCustomer
      RequestSoftwareInstanceDestroy
      Tic
      SlapLogout
      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      CheckComputerPartitionIsBusy
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_check_permission_with_different_customer(self):
    """
      Check that one Customer A can not view the Slave Instance of a Customer B
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      SlapLogout
      LoginAsCustomerA
      CheckSlaveInstanceSecurityWithDifferentCustomer
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      SlapLogout
      LoginTestVifibCustomer
      CheckSlaveInstanceSecurityWithDifferentCustomer
      Tic
      SlapLogout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_Information_with_getInstanceParameterDict(self):
    """
      Check that Computer Partition of user A is reinstanciated with new
      parameters provided by user B. User B and Aget the right connection
      parameter
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      SlapLoginCurrentComputer
      CheckEmptySlaveInstanceListFromOneComputerPartition
      LoginAsCustomerA
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      SlapLoginCurrentComputer
      CheckSlaveInstanceListFromOneComputerPartition
      SlapLogout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_security_with_SoftwareInstance_user(self):
    """
      Check that the software instance user can access a Slave Instance
      installed in the same computer partition than your software instance
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      SlapLoginCurrentComputer
      CheckEmptySlaveInstanceListFromOneComputerPartition
      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      StoreSalePackingListLineFromSlaveInstance
      StoreSaleOrderFromSlaveInstance
      SlapLoginCurrentComputer
      CheckSlaveInstanceListFromOneComputerPartition
      SlapLoginSoftwareInstanceFromCurrentSoftwareInstance
      CheckSlaveInstanceAccessUsingCurrentSoftwareInstanceUser
      CheckSalePackingListFromSlaveInstanceAccessUsingSoftwareInstanceUser
      CheckSaleOrderFromSlaveInstanceAccessUsingSoftwareInstanceUser
      CheckHostingSubscriptionFromSlaveInstanceAccessUsingSoftwareInstanceUser
      SlapLogout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_update_connection_xml(self):
    """
      Check that the connection_xml will be update correctly using portal_slap
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      SlapLoginCurrentComputer
      CheckEmptySlaveInstanceListFromOneComputerPartition
      LoginAsCustomerA
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      SlapLoginSoftwareInstanceFromCurrentSoftwareInstance
      SetConnectionXmlToSlaveInstance
      CheckConnectionXmlFromSlaveInstance
      CheckConnectionXmlFromSoftwareInstance

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepSetSoftwareInstanceAsCurrentRequestedSlave(self, sequence, **kw):
    slave_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid']).getPredecessorValue(
        portal_type='Slave Instance')
    sequence['software_instance_uid'] = slave_instance.getUid()

  def stepCheckComputerPartitionInstanceUpdateSalePackingListDelivered(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('delivered',
        self.portal.portal_preferences.getPreferredInstanceUpdateResource(),
        sequence)

  def test_SlaveInstance_change_parameter_dict_after_request(self):
    """
      Check that request to change the parameter dict from a Slave Instance
      will create update packing list correctly
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      CheckEmptySlaveInstanceListFromOneComputerPartition
      SlapLoginCurrentSoftwareInstance
      SelectEmptyRequestedParameterDict
      SetRandomRequestedReference
      RequestSlaveInstanceFromComputerPartition
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      Logout
      SlapLoginCurrentSoftwareInstance
      RequestSlaveInstanceFromComputerPartition
      SlapLogout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout
      SlapLoginCurrentComputer
      LoginDefaultUser
      StartSoftwareInstanceFromCurrentComputerPartition
      Tic
      Logout
      SlapLoginCurrentSoftwareInstance
      SoftwareInstanceStarted
      Tic
      CheckSuccessComputerGetComputerPartitionCall
      SlapLogout

      SlapLoginCurrentSoftwareInstance
      SelectRequestedParameterDictRequestedParameter
      RequestSlaveInstanceFromComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SetSoftwareInstanceAsCurrentRequestedSlave
      CheckComputerPartitionInstanceUpdateSalePackingListDelivered
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

  def test_Security_after_destroy_SoftwareInstance_with_different_user(self):
    """
      Check that destroying one Software Instance it will not destroy Slave
      Instances that is not related to your Software Instance.
      Scenario:

        VifibCustomer         CustomerA
           |                     | 
        SoftwareInstance     SoftwareInstanceA (requestDestroy)
           |                     | 
        SlaveInstance        SlaveInstanceA

     The Slave Instance related to Customer should not be destroyed
    """
    self.computer_partition_amount = 4
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      CheckEmptySlaveInstanceListFromOneComputerPartition
      SlapLoginCurrentSoftwareInstance
      SelectEmptyRequestedParameterDict
      SetRandomRequestedReference
      RequestSlaveInstanceFromComputerPartition
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      Logout
      SlapLoginCurrentSoftwareInstance
      RequestSlaveInstanceFromComputerPartition
      SlapLogout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic 
      LoginDefaultUser
      SetDeliveryLineAmountEqualOne
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed """ + \
      self.prepare_published_software_release + """
      Tic
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      LoginAsCustomerA
      PersonRequestSoftwareInstance
      Logout
      Tic
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLoginCurrentSoftwareInstance
      SelectEmptyRequestedParameterDict
      SetRandomRequestedReference
      RequestSlaveInstanceFromComputerPartition
      Tic
      SlapLogout
      LoginDefaultUser
      CallConfirmOrderedSaleOrderAlarm
      Tic
      Logout
      SlapLoginCurrentSoftwareInstance
      RequestSlaveInstanceFromComputerPartition
      Tic
      SlapLogout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout
      LoginDefaultUser
      SetDeliveryLineAmountEqualOne
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout
      LoginAsCustomerA
      RequestDestroySoftwareInstanceFromCurrentComputerPartition
      Tic
      Logout
      LoginDefaultUser
      SetDeliveryLineAmountEqualOne
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)


def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapWebServiceSlaveInstance))
  return suite
