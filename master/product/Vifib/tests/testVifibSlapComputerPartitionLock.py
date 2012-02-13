from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from zExceptions import Unauthorized

class TestVifibSlapComputerPartitionLock(TestVifibSlapWebServiceMixin):

  lock_user_sequence_string = '\
      LoginERP5TypeTestCase \
      TriggerBuild \
      Tic \
      TriggerStopConfirmedInvoiceAlarm \
      Tic \
      TriggerBuild \
      Tic \
      Logout'

  def stepSoftwareInstanceSaleOrderConfirmRaisesUnauthorized(self, sequence,
    **kw):
    """Checks that current software instance is realted only with sale order
    
    and that this sale order cannot be confirmed because of Unauthorized
    
    It means that user has bad balance."""
    software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])

    aggregate_value_list = software_instance.getAggregateRelatedValueList(
        portal_type=[self.sale_packing_list_line_portal_type,
        self.sale_order_line_portal_type])

    self.assertEqual(1, len(aggregate_value_list))
    self.assertTrue(self.sale_order_line_portal_type in [q.getPortalType() for\
        q in aggregate_value_list])
    sale_order_line = aggregate_value_list[0]
    sale_order = sale_order_line.getParentValue()

    self.assertRaises(Unauthorized, sale_order.confirm)

  def stepAssertNoComputerPartition(self, sequence, **kw):
    """Sets in sequence computer partition parameters related to current
    software instance"""
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    delivery_line_list = [q for q in software_instance
        .getAggregateRelatedValueList(
          portal_type=self.sale_packing_list_line_portal_type)]
    self.assertEqual(0, len(delivery_line_list))

  def test_negative_person_balance_request(self):
    """Locked person can not request
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_installed_software_release_sequence_string + \
      self.register_new_user_sequence_string  + \
      self.lock_user_sequence_string + '\
      LoginWebUser \
      PersonRequestSoftwareInstance \
      Tic \
      Logout \
      \
      LoginDefaultUser \
      SoftwareInstanceSaleOrderConfirmRaisesUnauthorized \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      AssertNoComputerPartition \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_negative_person_balance_request_slave(self):
    """Locked person can not request
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_install_requested_computer_partition_sequence_string + \
      self.register_new_user_sequence_string + \
      self.lock_user_sequence_string + '\
      LoginWebUser \
      PersonRequestSlaveInstance \
      Tic \
      Logout \
      \
      LoginDefaultUser \
      SoftwareInstanceSaleOrderConfirmRaisesUnauthorized \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      AssertNoComputerPartition \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionLock))
  return suite
