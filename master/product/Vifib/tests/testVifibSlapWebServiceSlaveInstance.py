from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from Products.ERP5Type.tests.backportUnittest import skip

class TestVifibSlapWebServiceSlaveInstance(TestVifibSlapWebServiceMixin):
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
    Logout
    LoginDefaultUser
    ConfirmOrderedSaleOrderActiveSense
    Tic
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
        PersonRequestSlaveInstance
        Tic
        Logout
        LoginDefaultUser
        ConfirmOrderedSaleOrderActiveSense
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
    PersonRequestSlaveInstance
    Tic
    Logout

    LoginDefaultUser
    ConfirmOrderedSaleOrderActiveSense
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
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLogout
      LoginTestVifibCustomer
      SlaveInstanceStopComputerPartitionInstallation
      Tic
      SlaveInstanceStarted
      Tic
      SlaveInstanceStopped
      Tic
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
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
      PersonRequestSlaveInstance
      ConfirmOrderedSaleOrderActiveSense
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
      PersonRequestSoftwareInstance
      ConfirmOrderedSaleOrderActiveSense
      Tic
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      ConfirmOrderedSaleOrderActiveSense
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
      PersonRequestSlaveInstance
      Tic
      ConfirmOrderedSaleOrderActiveSense
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
    PersonRequestSlaveInstance
    Tic
    ConfirmOrderedSaleOrderActiveSense
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
      PersonRequestSlaveInstance
      ConfirmOrderedSaleOrderActiveSense
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
      PersonRequestSoftwareInstance
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SelectDifferentSoftwareReleaseUri
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      ConfirmOrderedSaleOrderActiveSense
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
      PersonRequestSlaveInstance
      SlapLogout

      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
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

  def test_SlaveInstance_request_start_when_SoftwareInstance_is_started(self):
    """
      Check that the Slave Instance will be started correctly
      XXX - Review the sequence of steps to verify that the scenario is
      validating the feature of  start a Instance Slave
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SoftwareInstanceStarted
      Tic
      SetDeliveryLineAmountEqualTwo
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_request_stop_from_SoftwareInstance(self):
    """
      Check that the Slave Instance will be stopped correctly when
      a Software Instance is stopped
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      LoginTestVifibCustomer
      StartSoftwareInstanceFromCurrentComputerPartition
      Tic
      SoftwareInstanceStarted
      Tic
      SoftwareInstanceStopped
      Tic
      SetDeliveryLineAmountEqualTwo
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
      CheckComputerPartitionInstanceSetupSalePackingListStopped

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_request_start_from_SoftwareInstance(self):
    """
      Check that the Slave Instance will be started correctly when
      a Software Instance is started
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
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
      SetDeliveryLineAmountEqualTwo
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      LoginTestVifibCustomer
      RequestStopSoftwareInstanceFromCurrentComputerPartition
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
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
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      SetDeliveryLineAmountEqualZero
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
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
      SetDeliveryLineAmountEqualThree
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStarted
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
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_call_destroy_from_SoftwareInstance(self):
    """
      Check that the Slave Instance will be stopped correctly when
      a Software Instance is destroyed
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_slave_instance_sequence_string + """
      LoginTestVifibCustomer
      RequestDestroySoftwareInstanceFromCurrentComputerPartition
      Tic
      SetDeliveryLineAmountEqualTwo
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_destroy_SoftwareInstance_after_request_SlaveInstance(self):
    """
      Check that destroying the Software Instance after request Slave
      Instance with the same user, the Slave Instance must be destroyed
      correctly
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      LoginTestVifibCustomer
      RequestDestroySoftwareInstanceFromCurrentComputerPartition
      Tic
      SetDeliveryLineAmountEqualTwo
      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_destroy_SoftwareInstance_after_request_SlaveInstance_with_another_user(self):
    """
      Check that destroying the Software Instance after request Slave
      Instance with the different user, the Slave Instance must be destroyed
      correctly
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      LoginTestVifibCustomerA
      PersonRequestSlaveInstance
      SlapLogout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      LoginTestVifibCustomer
      RequestDestroySoftwareInstanceFromCurrentComputerPartition
      Tic
      SetDeliveryLineAmountEqualTwo
      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_destroy_SoftwareInstance_after_destroy_SlaveInstance(self):
    """
      Check that destroying the Software Instance after request destroy Slave
      Instance, the request to destroy the Software Instance will not raise
      exception
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      LoginTestVifibCustomer
      RequestSoftwareInstanceDestroy
      Tic
      RequestDestroySoftwareInstanceFromCurrentComputerPartition
      Tic
      SetDeliveryLineAmountEqualTwo
      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_request_stop(self):
    """
      Check that the Slave Instance will be stopped correctly
      XXX - Review the sequence of steps to verify that the scenario is
      validating the feature of stop a Instance Slave
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + """
      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      SlapLogout
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
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
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
      Logout
      LoginTestVifibCustomer
      RequestStopSoftwareInstanceFromCurrentComputerPartition
      Tic
      Logout
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
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
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
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLogout
      LoginAsCustomerA
      CheckSlaveInstanceSecurityWithDifferentCustomer
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      SlapLogout
      LoginTestVifibCustomer
      CheckSlaveInstanceSecurityWithDifferentCustomer
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
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
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
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
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
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
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
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      SlapLoginCurrentSoftwareInstance
      RequestSlaveInstanceFromComputerPartition
      SlapLogout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      LoginDefaultUser
      StartSoftwareInstanceFromCurrentComputerPartition
      Logout
      Tic
      SoftwareInstanceStarted
      Tic
      CheckEmptyComputerGetComputerPartitionCall
      SlapLogout
      SlapLoginCurrentSoftwareInstance
      SelectRequestedParameterDictRequestedParameter
      RequestSlaveInstanceFromComputerPartition
      SlapLogout
      LoginDefaultUser
      CheckComputerPartitionInstanceUpdateSalePackingListConfirmed
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

  def test_SlaveInstance_destroy_slave_with_SlaveInstance_stopped(self):
    """
      Check that request destroy from Software Instance when exists one Slave
      Instance stopped, both instances will be destroyed correctly

      Scenario:
        1. request master instance
        2. request Slave Instance
        3. stop Slave Instance
        4. request destroy the master instance
      Both instances must be destroyed
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
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      SlapLoginCurrentSoftwareInstance
      RequestSlaveInstanceFromComputerPartition
      SlapLogout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      LoginDefaultUser
      StartSoftwareInstanceFromCurrentComputerPartition
      Logout
      Tic
      SoftwareInstanceStarted
      Tic
      SlapLogout
      LoginDefaultUser
      SelectSlaveInstanceFromOneComputerPartition
      SlapLoginCurrentSoftwareInstance
      RequestSoftwareInstanceStop
      Tic
      SlaveInstanceStopped
      Tic
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
      SetDeliveryLineAmountEqualTwo
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      RequestDestroySoftwareInstanceFromCurrentComputerPartition
      Tic
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      LoginDefaultUser
      CheckComputerPartitionIsFree
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionInstanceSetupSalePackingListDelivered

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
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      SlapLoginCurrentSoftwareInstance
      RequestSlaveInstanceFromComputerPartition
      SlapLogout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic 
      LoginDefaultUser
      SetDeliveryLineAmountEqualTwo
      CheckComputerPartitionInstanceSetupSalePackingListStopped
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
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
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
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
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
      SetDeliveryLineAmountEqualTwo
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout
      LoginAsCustomerA
      RequestDestroySoftwareInstanceFromCurrentComputerPartition
      Tic
      Logout
      LoginDefaultUser
      SetDeliveryLineAmountEqualTwo
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
