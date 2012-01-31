from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import skip
import urllib
import urlparse
import httplib
from xml_marshaller import xml_marshaller
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from slapos import slap

class TestVifibSlapComputerPartitionRequest(TestVifibSlapWebServiceMixin):
  ########################################
  # ComputerPartition.request
  ########################################

  def test_ComputerPartition_request_noFreePartition(self):
    """
    Check that first call to request raises NotFound response
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_request_noParameterInRequest(self):
    """
    Check that it is possible to request another Computer Partition
    from existing one, without passing any parameters and that in such case
    original's Sofware Instance parameters will be passed.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      CheckRaisesNotFoundComputerPartitionParameterDict \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      CheckSoftwareInstanceAndRelatedComputerPartition \
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition \
      Logout \
      \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      CheckRequestedComputerPartitionCleanParameterList \
      SlapLogout \
      \
      LoginTestVifibCustomer \
      CheckViewCurrentSoftwareInstance \
      CheckWriteCurrentSoftwareInstance \
      Tic \
      CheckViewRequestedSoftwareInstance \
      CheckWriteRequestedSoftwareInstance \
      Tic \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_request_instantiate(self):
    """
    Check that after computer partition is requested it is possible to
    instantiate it and it is started correctly.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      CheckRaisesNotFoundComputerPartitionParameterDict \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      CheckSoftwareInstanceAndRelatedComputerPartition \
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition \
      Logout \
      \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      CheckRequestedComputerPartitionCleanParameterList \
      SlapLogout \
      \
      LoginDefaultUser \
      SetCurrentSoftwareInstanceRequested \
      SetSelectedComputerPartition \
      SelectCurrentlyUsedSalePackingListUid \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceSetupSalePackingListStarted \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceSetupSalePackingListStopped \
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceHostingSalePackingListStarted \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepSetInstanceStateStopped(self, sequence=None, **kw):
    sequence['instance_state'] = 'stopped'

  def test_ComputerPartition_request_instantiate_state_stopped(self):
    """
    Check that after computer partition is requested it is possible to
    instantiate it and it is stopped correctly, as requested initally.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SetInstanceStateStopped \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      CheckRaisesNotFoundComputerPartitionParameterDict \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      CheckSoftwareInstanceAndRelatedComputerPartition \
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition \
      Logout \
      \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      CheckRequestedComputerPartitionCleanParameterList \
      SlapLogout \
      \
      LoginDefaultUser \
      SetCurrentSoftwareInstanceRequested \
      SetSelectedComputerPartition \
      SelectCurrentlyUsedSalePackingListUid \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceSetupSalePackingListStarted \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceSetupSalePackingListStopped \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStopped \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      stepCheckComputerPartitionNoInstanceHostingSalePackingList \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_request_instantiate_stop_later(self):
    """
    Check that after computer partition is requested it is possible to
    instantiate it and it is started correctly, and later it is stopped
    correctly as requested.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      CheckRaisesNotFoundComputerPartitionParameterDict \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      CheckSoftwareInstanceAndRelatedComputerPartition \
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition \
      Logout \
      \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      CheckRequestedComputerPartitionCleanParameterList \
      SlapLogout \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      LoginDefaultUser \
      SetCurrentSoftwareInstanceRequested \
      SetSelectedComputerPartition \
      SelectCurrentlyUsedSalePackingListUid \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceSetupSalePackingListStarted \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceSetupSalePackingListStopped \
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceHostingSalePackingListStarted \
      Logout \
      \
      SetInstanceStateStopped \
      \
      LoginDefaultUser \
      SetCurrentSoftwareInstanceRequester \
      SetSelectedComputerPartition \
      SelectCurrentlyUsedSalePackingListUid \
      Logout \
      \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      SetCurrentSoftwareInstanceRequested \
      SetSelectedComputerPartition \
      SelectCurrentlyUsedSalePackingListUid \
      CheckComputerPartitionInstanceHostingSalePackingListStopped \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStopped \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceHostingSalePackingListDelivered \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepDirectRequestComputerPartitionHttpRequestTimeoutResponseWithoutState(self,
    sequence, **kw):
    request_dict = { 'computer_id': sequence['computer_reference'] ,
        'computer_partition_id': sequence['computer_partition_reference'],
        'software_release': sequence['software_release_uri'],
        'software_type': sequence.get('requested_software_type',
          'requested_software_type'),
        'partition_reference': sequence.get('requested_reference',
          'requested_reference'),
        'shared_xml': xml_marshaller.dumps(kw.get("shared", False)),
        'partition_parameter_xml': xml_marshaller.dumps({}),
        'filter_xml': xml_marshaller.dumps({}),
        #'state': Note: State is omitted
      }
    scheme, netloc, path, query, fragment = urlparse.urlsplit(self.server_url)
    connection = httplib.HTTPConnection(host=netloc)
    connection.request("POST", path + '/requestComputerPartition',
        urllib.urlencode(request_dict),
        {'Content-type': "application/x-www-form-urlencoded"})
    response = connection.getresponse()
    self.assertEqual(httplib.REQUEST_TIMEOUT, response.status)

  def test_ComputerPartition_request_state_is_optional(self):
    """Checks that state is optional parameter on Slap Tool
    
    This ensures backward compatibility with old libraries."""
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      DirectRequestComputerPartitionHttpRequestTimeoutResponseWithoutState \
      Tic \
      SlapLogout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('This test fails because test_vifib_customer security is cached '
    'and this user is not in SOFTINST-x group. We do not want to clear '
    'cache in tests.')
  def test_ComputerPartition_request_instantiateStop(self):
    """
    Check that after computer partition is requested it is possible to
    instantiate it and stop.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckSoftwareInstanceAndRelatedComputerPartition \
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition \
      Logout \
      \
      SlapLoginCurrentSoftwareInstance \
      CheckRequestedComputerPartitionCleanParameterList \
      Logout \
      \
      LoginDefaultUser \
      SetCurrentSoftwareInstanceRequested \
      SetSelectedComputerPartition \
      SelectCurrentlyUsedSalePackingListUid \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceSetupSalePackingListStarted \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceSetupSalePackingListStopped \
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceHostingSalePackingListStarted \
      Logout \
      \
      LoginTestVifibCustomer \
      RequestSoftwareInstanceStop \
      Tic \
      Logout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceHostingSalePackingListStopped \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStopped \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceHostingSalePackingListDelivered \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_request_parameterInRequest(self):
    """
    Check that it is possible to request another Computer Partition
    from existing one, with passing parameters and that in such case all
    passed parameters are available on new Computer Partition and no
    parameters are copied.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SelectRequestedReference \
      SelectRequestedParameterDictRequestedParameter \
      \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      CheckRaisesNotFoundComputerPartitionParameterDict \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      CheckSoftwareInstanceAndRelatedComputerPartition \
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition \
      Logout \
      \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      CheckRequestedComputerPartitionRequestedParameter \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_request_twiceSameSourceSameResult(self):
    """
    Checks that requesting twice with same arguments from same Computer Partition
    will return same object."""
    self.computer_partition_amount = 3
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SelectRequestedReference \
      SelectEmptyRequestedParameterDict \
      \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      CheckRaisesNotFoundComputerPartitionParameterDict \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      CheckSoftwareInstanceAndRelatedComputerPartition \
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition \
      Logout \
      \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      CheckRequestedComputerPartitionCleanParameterList \
      SlapLogout \
      \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckSoftwareInstanceAndRelatedComputerPartition \
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition \
      Logout \
      \
      SlapLoginCurrentSoftwareInstance \
      CheckRequestedComputerPartitionCleanParameterList \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_request_twiceDifferentParent(self):
    """
    Checks that requesting twice with same arguments from different Computer
    Partition will return same object.

    This test is reproducing scenario:

            Master
          /       \
    ChildrenA   ChildrenB
          \
      ChildrenRequestedTwice

    Then ChildrenB requests ChildrenRequestedTwice, so graph changes to:

            Master
          /       \
    ChildrenA   ChildrenB
                  /
      ChildrenRequestedTwice
    """
    self.computer_partition_amount = 4
    sequence_list = SequenceList()
    sequence_string = self.prepare_children_a_children_b_sequence_string + """
      # Generate first part of graph
      #            Master
      #          /       \
      #    ChildrenA   ChildrenB
      #          \
      #      ChildrenRequestedTwice

      LoginDefaultUser
      SetSoftwareInstanceChildrenA
      SelectRequestedReference
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SetRequestedComputerPartition
      CheckComputerPartitionChildrenA
      CheckComputerPartitionChildrenBNoChild
      CheckComputerPartitionRequestedDoubleScenarioChildrenA
      Logout

      # Generate second part of graph
      #            Master
      #          /       \
      #    ChildrenA   ChildrenB
      #                  /
      #      ChildrenRequestedTwice

      LoginDefaultUser
      SetRequestedComputerPartition
      SetSoftwareInstanceChildrenB
      SelectRequestedReference
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SetRequestedComputerPartition
      CheckComputerPartitionChildrenANoChild
      CheckComputerPartitionChildrenB
      CheckComputerPartitionRequestedDoubleScenarioChildrenB
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_request_SlaveInstance_twiceDifferentParent(self):
    """
    Checks that requesting a Slave Instance twice with same arguments from
    different Computer Partition will return same object.

    This test is reproducing scenario:

            Master
          /       \
    ChildrenA   ChildrenB
          \
      SlaveInstanceRequestTwice

    Then ChildrenB requests SlaveInstanceRequestedTwice, so graph changes to:

            Master
          /       \
    ChildrenA   ChildrenB
                  /
      SlaveInstanceRequestedTwice
    """
    self.computer_partition_amount = 3
    sequence_list = SequenceList()
    sequence_string = self.prepare_children_a_children_b_sequence_string + """
      # Generate first part of graph
      #            Master
      #          /       \
      #    ChildrenA   ChildrenB
      #          \
      #      SlaveInstanceRequestedTwice

      LoginDefaultUser
      SetSoftwareInstanceChildrenA
      SelectRequestedReference
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestSlaveInstanceFromComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      RequestSlaveInstanceFromComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SetRequestedComputerPartition
      CheckComputerPartitionChildrenA
      CheckComputerPartitionChildrenBNoChild
      Logout

      # Generate second part of graph
      #            Master
      #          /       \
      #    ChildrenA   ChildrenB
      #                  /
      #      SlaveInstanceRequestedTwice

      LoginDefaultUser
      SetRequestedComputerPartition
      SetSoftwareInstanceChildrenB
      SelectRequestedReference
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestSlaveInstanceFromComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      RequestSlaveInstanceFromComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SetRequestedComputerPartition
      CheckComputerPartitionChildrenANoChild
      CheckComputerPartitionChildrenB
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Implementation is not ready yet')
  def test_ComputerPartition_request_twiceDifferentParentWithoutTic(self):
    """
    Checks that requesting twice with same arguments from different Computer
    Partition will return same object.

    This test is reproducing scenario:

            Master
          /       \
    ChildrenA   ChildrenB
          \
      ChildrenRequestedTwice

    Then ChildrenB requests ChildrenRequestedTwice, so graph changes to:

            Master
          /       \
    ChildrenA   ChildrenB
                  /
      ChildrenRequestedTwice

    Case without tic between requests.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_children_a_children_b_sequence_string + """
      SelectRequestedReference
      SelectEmptyRequestedParameterDict

      SetSoftwareInstanceChildrenA
      RequestComputerPartition
      Tic

      SetSoftwareInstanceChildrenB
      RequestComputerPartition
      Tic
      SetRequestedComputerPartition
      CheckComputerPartitionChildrenA
      CheckComputerPartitionChildrenB
      CheckComputerPartitionRequestedDoubleScenario

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_request_differentSourceDifferentResultWithTic(self):
    """
    Check that requesting different Computer Partitions from different sources
    gives different result, because they are requesting different
    partition_reference.

    This test is reproducing scenario:
            Master
          /       \
    ChildrenA   ChildrenB
        |           |
    ChildChildA  ChildChildB
    """
    self.computer_partition_amount = 5
    sequence_list = SequenceList()
    sequence_string = self.prepare_children_a_children_b_sequence_string + """
      # Request ChildChildrenA
      LoginDefaultUser
      SetSoftwareInstanceChildrenA
      SelectRequestedReferenceChildrenAChild
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout

      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SetChildrenAChildComputerPartition

      # Request ChilChildrenB
      SetSoftwareInstanceChildrenB
      SelectRequestedReferenceChildrenBChild
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SetChildrenBChildComputerPartition
      # Do assertions
      CheckComputerPartitionChildrenAWithOwnChildren
      CheckComputerPartitionChildrenBWithOwnChildren
      CheckComputerPartitionChildrenAChild
      CheckComputerPartitionChildrenBChild
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Implementation is not ready yet.')
  def test_ComputerPartition_request_differentSourceDifferentResultWithoutTic(
      self):
    """
    Check that requesting different Computer Partitions from different sources
    gives different result, because they are requesting different
    partition_reference.

    This test is reproducing scenario:
            Master
          /       \
    ChildrenA   ChildrenB
        |           |
    ChilChildA  ChildChildB

    Case without tic between requests.
    """
    self.computer_partition_amount = 5
    sequence_list = SequenceList()
    sequence_string = self.prepare_children_a_children_b_sequence_string + """
      LoginDefaultUser
      SetSoftwareInstanceChildrenA
      SelectRequestedReferenceChildrenAChild
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SetChildrenAChildComputerPartition

      SetSoftwareInstanceChildrenB
      SelectRequestedReferenceChildrenBChild
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SetChildrenBChildComputerPartition

      CheckComputerPartitionChildrenAWithOwnChildren
      CheckComputerPartitionChildrenBWithOwnChildren
      CheckComputerPartitionChildrenAChild
      CheckComputerPartitionChildrenBChild
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_request_serialiseIsCalled(self):
    """
    Check that during ComputerPartition.request serialise is being called
    on being choosen Computer Partition.

    Serialize call is used to protect Computer Partition from being selected
    as free in case of concurrency connections.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      SelectRequestedReferenceChildrenA \
      SelectEmptyRequestedParameterDict \
      RequestComputerPartition \
      SlapLogout \
      LoginDefaultUser \
      ConfirmSaleOrderOrderedToCheckSerializeCalledOnSelected \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '

    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  ########################################
  # ComputerPartition.request - filter - computer_guid
  ########################################
  def test_ComputerPartition_request_filter_computer_guid(self):
    """
    Check that requesting with filter computer_guid key works as expected
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    # There are two partitions on another computer
    # so request shall be processed twice correctly, 3rd time it shall
    # fail
    sequence_string = \
    self.prepare_install_requested_computer_partition_sequence_string + \
      self.prepare_another_computer_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      SlapLogout \
      \
      SelectAnotherRequestedReference \
      \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      SlapLogout \
      \
      SelectYetAnotherRequestedReference \
      SlapLoginCurrentSoftwareInstance \
      RequestComputerPartition \
      Tic \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
      '

    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  ########################################
  # ComputerPartition.request - slave
  ########################################
  def test_ComputerPartition_request_slave_simpleCase(self):
    """
    Check the most simple case of request. The behaviour should
    keep the same as Software Instance.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_install_requested_computer_partition_sequence_string +\
      """
       SlapLoginCurrentSoftwareInstance
       SelectEmptyRequestedParameterDict \
       SetRandomRequestedReference \
       RequestSlaveInstanceFromComputerPartition \
       Tic \
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

  def test_ComputerPartition_request_slave_instantiate(self):
    """
      Check that one Slave Instance is instantiate correctly and the validate
      the Sale Packing List states
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_install_requested_computer_partition_sequence_string +\
      """
       SlapLoginCurrentSoftwareInstance
       SelectEmptyRequestedParameterDict
       SetRandomRequestedReference
       RequestSlaveInstanceFromComputerPartition
       Tic
       CheckRaisesNotFoundComputerPartitionParameterDict
       Tic
       RequestSlaveInstanceFromComputerPartition
       Tic
       SlapLogout
       LoginDefaultUser
       ConfirmOrderedSaleOrderActiveSense

       Tic
       SlapLoginCurrentSoftwareInstance
       CheckSlaveInstanceListFromOneComputerPartition
       SelectSlaveInstanceFromOneComputerPartition
       SlapLogout

       LoginDefaultUser
       SetDeliveryLineAmountEqualTwo
       CheckComputerPartitionInstanceSetupSalePackingListConfirmed
       SlapLogout

       SlapLoginCurrentComputer
       SoftwareInstanceAvailable
       Tic
       SlapLogout

       LoginDefaultUser \
       CheckComputerPartitionInstanceSetupSalePackingListStopped
       CheckComputerPartitionInstanceHostingSalePackingListConfirmed
       Logout

       SlapLoginCurrentComputer \
       SoftwareInstanceStarted \
       Tic \
       SlapLogout \
       \
       LoginDefaultUser \
       CheckComputerPartitionInstanceHostingSalePackingListStarted \
       Logout \
       LoginERP5TypeTestCase \
       CheckSiteConsistency \
       Logout \
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_request_slave_same_twice_SR(self):
    """
      Check that requesting the same slave instance twice, only one is created
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_install_requested_computer_partition_sequence_string +\
        """
         SlapLoginCurrentSoftwareInstance
         SelectEmptyRequestedParameterDict
         SelectRequestedReference
         RequestSlaveInstanceFromComputerPartition \
         Tic
         SlapLogout
         LoginDefaultUser
         ConfirmOrderedSaleOrderActiveSense
         Tic
         SlapLoginCurrentComputer
         CheckSlaveInstanceListFromOneComputerPartition
         SlapLogout

         SlapLoginCurrentSoftwareInstance \
         RequestSlaveInstanceFromComputerPartition \
         Tic
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

  def test_ComputerPartition_request_slave_after_destroy_SlaveInstance(self):
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
        SlapLoginCurrentSoftwareInstance
        SelectEmptyRequestedParameterDict
        SelectRequestedReference
        RequestSlaveInstanceFromComputerPartition
        Tic
        LoginDefaultUser
        SelectSlaveInstanceFromSaleOrderOrdered
        SoftwareInstanceSaleOrderConfirmRaisesValueError
        ConfirmOrderedSaleOrderActiveSense
        Tic
        CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
        CheckComputerPartitionInstanceSetupSalePackingListStopped
        CheckComputerPartitionInstanceHostingSalePackingListConfirmed
        SetDeliveryLineAmountEqualZero
        CheckComputerPartitionInstanceSetupSalePackingListConfirmed

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_request_slave_twice_different(self):
    """
     Check request 2 different slave instances on same Software 
     Instance.
    """
    simple_request_with_random = """
         SlapLoginCurrentSoftwareInstance
         SelectEmptyRequestedParameterDict \
         SetRandomRequestedReference \
         RequestSlaveInstanceFromComputerPartition \
         Tic \
         SlapLogout
         LoginDefaultUser
         ConfirmOrderedSaleOrderActiveSense
         Tic
         """

    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_install_requested_computer_partition_sequence_string +\
        simple_request_with_random + """
          SlapLoginCurrentComputer
          CheckSlaveInstanceListFromOneComputerPartition
          SlapLogout
        """ + \
        simple_request_with_random + \
        """
        SlapLoginCurrentComputer
        CheckTwoSlaveInstanceListFromOneComputerPartition
        SlapLogout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
        """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_request_slave_NotFound(self):
    """
    Check that requesting a Slave Instance works in system capable to fulfill
    such request, when Software Instance is not installed yet.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + """
        LoginDefaultUser
        SetRandomComputerPartition
        SlapLoginCurrentComputer
        SelectEmptyRequestedParameterDict
        SetRandomRequestedReference
        SelectNewSoftwareReleaseUri
        RequestSlaveInstanceFromComputerPartitionNotFoundError
        SlapLogout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepDirectRequestComputerPartitionHttpRequestTimeoutResponseWithoutStateAndSharedTrue(
      self, sequence, **kw):
    kw["shared"] = True
    self.stepDirectRequestComputerPartitionHttpRequestTimeoutResponseWithoutState(
       sequence, **kw)

  def test_ComputerPartition_request_slave_state_is_optional(self):
    """Checks that state is optional parameter on Slap Tool This ensures
    backward compatibility with old libraries."""
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      DirectRequestComputerPartitionHttpRequestTimeoutResponseWithoutStateAndSharedTrue \
      Tic \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepSetRequestedWrongFilterParameterDict(self, sequence):
        sequence['requested_filter_dict'] = dict(
          computer_guid="COMP-99999999999999999999999")

  def test_ComputerPartition_request_filter_slave_computer_guid(self):
    """Check that requesting with filter computer_guid key works as expected.

    This include tests for slave instance case."""
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    # There are two partitions on another computer
    # so request shall be processed twice correctly, 3rd time it shall
    # fail
    sequence_string = \
    self.prepare_install_requested_computer_partition_sequence_string + \
      self.prepare_another_computer_sequence_string + '\
      SelectAnotherRequestedReference \
      SelectEmptyRequestedParameterDict \
      SlapLoginCurrentSoftwareInstance \
      RequestSlaveInstanceFromComputerPartition \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      SelectSlaveInstanceFromSaleOrderOrdered \
      SoftwareInstanceSaleOrderConfirmRaisesValueError \
      Tic \
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed \
      Logout \
      SlapLoginCurrentSoftwareInstance \
      SetRequestedFilterParameterDict \
      RequestSlaveInstanceFromComputerPartition \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      SetDeliveryLineAmountEqualTwo \
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed \
      Logout \
      \
      SetRequestedWrongFilterParameterDict \
      SelectYetAnotherRequestedReference \
      SlapLoginCurrentSoftwareInstance \
      RequestSlaveInstanceFromComputerPartition \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckConnectionXmlOfSlaveInstanceFromComputerPartition(self, sequence):
    computer_reference = sequence["computer_reference"]
    computer_partition_reference = sequence["computer_partition_reference"]
    slave_reference = sequence["requested_reference"]
    slave_software_release = sequence["software_release_uri"]
    slave_software_type = sequence["requested_software_type"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    # Get Computer Partition
    computer_partition = self.slap.registerComputerPartition(
        computer_reference, computer_partition_reference)
    # Get slave
    slave_instance = computer_partition.request(
        software_release=slave_software_release,
        software_type=slave_software_type,
        partition_reference=slave_reference,
        shared=True,
    )
    self.assertEquals(sequence["slave_instance_site_url"],
                      slave_instance.getConnectionParameter("site_url"))

  def test_SlaveInstance_request_SlaveInstance_From_SoftwareInstance(self):
    """
      Check that existing Software Instance can request new Slave Instance
      and access to its parameters.
      
      Scenario :
      All Software Instances use the same SoftwareRelease.
      SoftwareType requested_software_type can act as master instance, slave
        instance.
      SoftwareType another_requested_software_type can act as Software Instance
        requesting a Slave Instance of SoftwareType requested_software_type.
      1/ Request instance "Master Instance" with SoftwareType
         requested_software_type.
      2/ Simulate succesful deployment of instance
      3/ Request instance "Normal instance" with SoftwareType
         another_requested_software_type.
      4/ From "Normal Instance", request a Slave Instance with SoftwareType
         requested_software_type.
      5/ From "Master Instance", try to set connection XML of Slave Instance
      5/ Check that "Normal Instance" can access connection XML of Slave
         Instance.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_install_requested_computer_partition_sequence_string + '\
      Tic \
      SlapLoginCurrentComputer \
      SoftwareInstanceAvailable \
      Tic \
      CheckEmptySlaveInstanceListFromOneComputerPartition \
      \
      SelectAnotherRequestedSoftwareType \
      SelectAnotherRequestedReference \
      SlapLoginTestVifibCustomer \
      PersonRequestSlapSoftwareInstancePrepare \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      Logout \
      SlapLoginTestVifibCustomer \
      PersonRequestSlapSoftwareInstance \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      SetRequestedComputerPartition \
      SetRequestedComputerPartitionAsCurrentComputerPartition \
      SlapLogout \
      Tic \
      SlapLoginCurrentComputer \
      SoftwareInstanceAvailable \
      Tic \
      \
      LoginDefaultUser \
      SetCurrentComputerPartitionFromRequestedComputerPartition \
      SelectSoftwareInstanceFromCurrentComputerPartition \
      Logout \
      SlapLoginCurrentSoftwareInstance \
      SelectRequestedParameterDictRequestedParameter \
      SelectYetAnotherRequestedReference \
      SelectRequestedSoftwaretype \
      RequestSlaveInstanceFromComputerPartition \
      Tic \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      Logout \
      RequestSlaveInstanceFromComputerPartition \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      SetComputerPartitionFromRootSoftwareInstance \
      SelectSlaveInstanceFromOneComputerPartition \
      SlapLoginSoftwareInstanceFromCurrentSoftwareInstance \
      SetConnectionXmlToSlaveInstance \
      SlapLogout \
      LoginDefaultUser \
      SetRequestedComputerPartitionAsCurrentComputerPartition \
      SelectSoftwareInstanceFromCurrentComputerPartition \
      Logout \
      SlapLoginCurrentSoftwareInstance \
      CheckConnectionXmlOfSlaveInstanceFromComputerPartition \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_request_SlaveInstance_From_SoftwareInstance_Fetch_Correct_Slave(self):
    """
      Check that existing Software Instance requesting new Slave Instance
      fetches the correct Slave Instance when doing request() to get
      parameters.
      
      Scenario :
      All Software Instances use the same SoftwareRelease.
      SoftwareType requested_software_type can act as master instance, slave
        instance.
      SoftwareType another_requested_software_type can act as Software Instance
        requesting a Slave Instance of SoftwareType requested_software_type.
      1/ Request instance "Master Instance" with SoftwareType
         requested_software_type.
      2/ "Master Instance" requests a new Slave Instance
      3/ Simulate succesful deployment of Master Instance
      4/ Request instance "Normal instance" with SoftwareType
         another_requested_software_type.
      5/ From "Normal Instance", request a Slave Instance with SoftwareType
         requested_software_type.
      6/ From "Master Instance", try to set connection XML of Slave Instance
      7/ Check that "Normal Instance" can access connection XML of Slave
         Instance.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      SelectEmptyRequestedParameterDict \
      SetRandomRequestedReference \
      RequestSlaveInstanceFromComputerPartition \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      SlapLoginCurrentComputer \
      CheckSlaveInstanceListFromOneComputerPartition \
      SlapLogout \
      \
      Tic \
      SlapLoginCurrentComputer \
      SoftwareInstanceAvailable \
      Tic \
      \
      SelectAnotherRequestedSoftwareType \
      SelectAnotherRequestedReference \
      SlapLoginTestVifibCustomer \
      PersonRequestSlapSoftwareInstancePrepare \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      Logout \
      SlapLoginTestVifibCustomer \
      PersonRequestSlapSoftwareInstance \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      SetRequestedComputerPartition \
      SetRequestedComputerPartitionAsCurrentComputerPartition \
      SlapLogout \
      Tic \
      SlapLoginCurrentComputer \
      SoftwareInstanceAvailable \
      Tic \
      \
      LoginDefaultUser \
      SetCurrentComputerPartitionFromRequestedComputerPartition \
      SelectSoftwareInstanceFromCurrentComputerPartition \
      Logout \
      SlapLoginCurrentSoftwareInstance \
      SelectRequestedParameterDictRequestedParameter \
      SelectYetAnotherRequestedReference \
      SelectRequestedSoftwaretype \
      RequestSlaveInstanceFromComputerPartition \
      Tic \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      Logout \
      RequestSlaveInstanceFromComputerPartition \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      SetComputerPartitionFromRootSoftwareInstance \
      SelectSlaveInstanceFromOneComputerPartition \
      SlapLoginSoftwareInstanceFromCurrentSoftwareInstance \
      SetConnectionXmlToSlaveInstance \
      SlapLogout \
      LoginDefaultUser \
      SetRequestedComputerPartitionAsCurrentComputerPartition \
      SelectSoftwareInstanceFromCurrentComputerPartition \
      Logout \
      SlapLoginCurrentSoftwareInstance \
      CheckConnectionXmlOfSlaveInstanceFromComputerPartition \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  ##################################################
  # ComputerPartition.request - change software type
  ##################################################

  def stepSetFirstSoftwareType(self, sequence,
      **kw):
    sequence.edit(requested_software_type="FirstSoftwareType")

  def stepSelectSlaveInstanceFromSaleOrderOrdered(self, sequence):
    order_line = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Order Line", simulation_state="ordered")
    slave_instance_uid = order_line.getAggregateValue(
        portal_type="Slave Instance").getUid()
    sequence.edit(software_instance_uid=slave_instance_uid)

  def stepRequestComputerPartitionWithAnotherSoftwareType(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])
    kw = dict(software_release=sequence['software_release_uri'],
      software_type="SecondSoftwareType",
      partition_reference=sequence.get('requested_reference',
        'requested_reference'),
      partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
      filter_kw=sequence.get('requested_filter_dict', {}),
      state=sequence.get('instance_state'))

    slap_computer_partition.request(**kw)

  def stepCheckRequestComputerPartitionWithAnotherSoftwareType(
                                     self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])
    kw = dict(software_release=sequence['software_release_uri'],
      software_type="SecondSoftwareType",
      partition_reference=sequence.get('requested_reference',
        'requested_reference'),
      partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
      filter_kw=sequence.get('requested_filter_dict', {}),
      state=sequence.get('instance_state'))

    requested_slap_computer_partition = slap_computer_partition.request(**kw)

    self.assertEquals(sequence.get('requested_computer_partition_reference'),
                      requested_slap_computer_partition.getId())
    self.assertEquals("SecondSoftwareType",
                      requested_slap_computer_partition.getInstanceParameterDict()['slap_software_type'])
    self.assertEquals(1,
                      requested_slap_computer_partition._need_modification)

  def test_ComputerPartition_request_changeSoftwareType(self):
    """
    Check that requesting the same instance with a different software type
    does not create a new instance
    """
    self.computer_partition_amount = 3
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SelectRequestedReference \
      SelectEmptyRequestedParameterDict \
      \
      SlapLoginCurrentSoftwareInstance \
      SetFirstSoftwareType \
      RequestComputerPartition \
      Tic \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      Logout \
      RequestComputerPartition \
      Tic \
      RequestComputerPartitionWithAnotherSoftwareType \
      Tic \
      RequestComputerPartitionWithAnotherSoftwareType \
      Tic \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      Logout \
      CheckRequestComputerPartitionWithAnotherSoftwareType \
      Tic \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionRequest))
  return suite
