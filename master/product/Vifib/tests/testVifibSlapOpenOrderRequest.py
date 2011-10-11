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
    self.slap.initializeConnection(self.server_url)
    open_order = self.slap.registerOpenOrder()
    open_order.request(
       software_release=software_release,
       software_type=sequence.get('software_type', 'software_type'),
       partition_reference=sequence.get('requested_reference',
          'requested_reference'),
       partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
       filter_kw=sequence.get('requested_filter_dict', {})
       )

  def stepPersonRequestSlapSoftwareInstance(self, sequence, **kw):
    software_release = sequence['software_release_uri']
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    open_order = self.slap.registerOpenOrder()
    requested_slap_computer_partition = open_order.request(
       software_release=software_release,
       software_type=sequence.get('software_type', 'software_type'),
       partition_reference=sequence['requested_reference'],
       partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
       filter_kw=sequence.get('requested_filter_dict', {}))
    sequence.edit(
        requested_slap_computer_partition=requested_slap_computer_partition,
        requested_computer_partition_reference=\
            requested_slap_computer_partition.getId())

  def stepSetCurrentPersonSlapRequestedSoftwareInstance(self, sequence, **kw):
    software_instance_list = self.portal.portal_catalog(
        portal_type=self.software_instance_portal_type,
        title=sequence['requested_reference'])
    self.assertEqual(1, len(software_instance_list))
    software_instance = software_instance_list[0]
    sequence.edit(
        software_instance_uid=software_instance.getUid(),
        software_instance_reference=software_instance.getReference(),
        hosting_subscription_uid=software_instance.getAggregateRelatedValue(
          portal_type='Sale Order Line').getAggregateValue(
            portal_type='Hosting Subscription').getUid())

  def stepSoftwareInstanceSaleOrderConfirmRaisesValueError(self, sequence,
    **kw):
    """Checks that current software instance is realted only with sale order
    
    and that this sale order cannot be confirmed
    
    In Vifib implementation sale order which cannot find free computer partition
    raises ValueError"""
    software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])

    aggregate_value_list = software_instance.getAggregateRelatedValueList(portal_type=[self.sale_packing_list_line_portal_type, self.sale_order_line_portal_type])

    self.assertEqual(1, len(aggregate_value_list))
    self.assertTrue(self.sale_order_line_portal_type in [q.getPortalType() for\
        q in aggregate_value_list])
    sale_order_line = aggregate_value_list[0]
    sale_order = sale_order_line.getParentValue()

    self.assertRaises(ValueError, sale_order.confirm)

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

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapOpenOrderRequest))
  return suite
