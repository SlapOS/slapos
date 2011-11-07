from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import expectedFailure
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from slapos import slap

class TestVifibSlapOpenOrderRequest(TestVifibSlapWebServiceMixin):
  ########################################
  # OpenOrder.request
  ########################################

  def stepPersonRequestSlapSoftwareInstancePrepare(self, sequence,
      **kw):
    software_release = sequence['software_release_uri']
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    open_order = self.slap.registerOpenOrder()
    open_order.request(
       software_release=software_release,
       software_type=sequence.get('software_type', 'software_type'),
       partition_reference=sequence.get('requested_reference',
          'requested_reference'),
       partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
       filter_kw=sequence.get('requested_filter_dict', {}),
       state=sequence.get('requested_state')
       )

  def test_person_request_ComputerPartition_filter_computer_guid(self):
    """Check that requesting with computer_guid in filter_kw works as
       expected in case of person request"""
    self.computer_partition_amount = 1
    sequence_list = SequenceList()
    # There is only one partition on each computer, which has installed
    # software release. But as request has sla parameter, the partition
    # on another computer is not selected, as not following SLA.
    sequence_string = self.prepare_published_software_release + \
      self.prepare_formated_computer + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout
      """ + \
      self.prepare_another_computer_sequence_string + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SetRandomRequestedReference
      SlapLoginTestVifibCustomer
      PersonRequestSlapSoftwareInstancePrepare
      Tic
      SlapLogout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout

      SlapLoginTestVifibCustomer
      PersonRequestSlapSoftwareInstance
      Tic
      SlapLogout

      LoginDefaultUser
      SetCurrentPersonSlapRequestedSoftwareInstance
      CheckPersonRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      SelectYetAnotherRequestedReference
      SlapLoginTestVifibCustomer
      PersonRequestSlapSoftwareInstancePrepare
      Tic
      SlapLogout

      LoginDefaultUser
      SetCurrentPersonSlapRequestedSoftwareInstance
      SoftwareInstanceSaleOrderConfirmRaisesValueError
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_person_request_ComputerPartition(self):
    """Checks that Person using Slap interface is able to request Computer
       Partition"""
    self.computer_partition_amount = 1
    sequence_list = SequenceList()
    sequence_string = self.prepare_published_software_release + \
      self.prepare_formated_computer + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      SetRandomRequestedReference
      SlapLoginTestVifibCustomer
      PersonRequestSlapSoftwareInstancePrepare
      Tic
      SlapLogout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout

      SlapLoginTestVifibCustomer
      PersonRequestSlapSoftwareInstance
      Tic
      SlapLogout

      LoginDefaultUser
      SetCurrentPersonSlapRequestedSoftwareInstance
      CheckPersonRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      SlapLogout

      LoginTestVifibCustomer
      CheckViewCurrentSoftwareInstance
      CheckWriteCurrentSoftwareInstance
      Tic
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepSetFirstSoftwareType(self, sequence,
      **kw):
    sequence.edit(software_type="FirstSoftwareType")

  def stepPersonRequestSlapSoftwareInstanceWithAnotherSoftwareType(
                                                    self, sequence, **kw):
    software_release = sequence['software_release_uri']
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    open_order = self.slap.registerOpenOrder()
    requested_slap_computer_partition = open_order.request(
       software_release=software_release,
       software_type="SecondSoftwareType",
       partition_reference=sequence['requested_reference'],
       partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
       filter_kw=sequence.get('requested_filter_dict', {}))

  def stepCheckPersonRequestSlapSoftwareInstanceWithAnotherSoftwareType(
                                                    self, sequence, **kw):
    software_release = sequence['software_release_uri']
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    open_order = self.slap.registerOpenOrder()
    requested_slap_computer_partition = open_order.request(
       software_release=software_release,
       software_type="SecondSoftwareType",
       partition_reference=sequence['requested_reference'],
       partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
       filter_kw=sequence.get('requested_filter_dict', {}))

    self.assertEquals(sequence.get('requested_computer_partition_reference'),
                      requested_slap_computer_partition.getId())
    self.assertEquals("SecondSoftwareType",
                      requested_slap_computer_partition.getInstanceParameterDict()['slap_software_type'])
    self.assertEquals(1,
                      requested_slap_computer_partition._need_modification)

  def test_OpenOrder_request_changeSoftwareType(self):
    """
    Check that requesting the same instance with a different software type
    does not create a new instance
    """
    self.computer_partition_amount = 1
    sequence_list = SequenceList()
    sequence_string = self.prepare_published_software_release + \
      self.prepare_formated_computer + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      SetRandomRequestedReference
      SlapLoginTestVifibCustomer
      SetFirstSoftwareType
      PersonRequestSlapSoftwareInstancePrepare
      Tic
      SlapLogout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout

      SlapLoginTestVifibCustomer
      PersonRequestSlapSoftwareInstance
      Tic
      PersonRequestSlapSoftwareInstanceWithAnotherSoftwareType
      Tic
      CheckPersonRequestSlapSoftwareInstanceWithAnotherSoftwareType
      Tic
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapOpenOrderRequest))
  return suite
