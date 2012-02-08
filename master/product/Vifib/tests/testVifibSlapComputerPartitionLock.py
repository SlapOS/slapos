from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from Products.DCWorkflow.DCWorkflow import ValidationFailed
from random import random
from slapos import slap
from zExceptions import Unauthorized
from DateTime import DateTime
from Products.ERP5Type.tests.backportUnittest import skip

class TestVifibSlapComputerPartitionLock(TestVifibSlapWebServiceMixin):

  register_new_user_sequence_string = '\
      Logout \
      RequestCredentialFromWebSite \
      Tic \
      LoginDefaultUser \
      SubmitCredentialRequest \
      Tic \
      AcceptSubmittedCredentialsActiveSense \
      Tic \
      Logout \
      '

  create_new_user_instance_sequence_string = '\
      LoginWebUser \
      PersonRequestSoftwareInstance \
      Tic \
      Logout \
      \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      SetSelectedComputerPartition \
      SelectCurrentlyUsedSalePackingListUid \
      Logout \
      '

  create_new_user_slave_instance_sequence_string = '\
      LoginWebUser \
      PersonRequestSlaveInstance \
      Tic \
      Logout \
      \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      SetSelectedComputerPartition \
      SelectCurrentlyUsedSalePackingListUid \
      Logout \
      '

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
      self.register_new_user_sequence_string \
      + self.lock_user_string() + '\
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
      self.lock_user_string() + '\
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

  def stepCreateSmallInvoiceWebUser(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    invoice = self.portal.accounting_module.newContent(
      portal_type='Sale Invoice Transaction',
      start_date=DateTime(),
      resource='currency_module/EUR',
      source_section='organisation_module/vifib_internet',
      source='organisation_module/vifib_internet',
      destination_section=person.getRelativeUrl(),
      destination=person.getRelativeUrl(),
      specialise='sale_trade_condition_module/vifib_trade_condition'
    )
    invoice.newContent(
      portal_type='Invoice Line',
      resource=self.portal.portal_preferences.getPreferredRegistrationResource(),
      quantity=1,
      price=1
    )
    sequence['invoice'] = invoice

  def stepPlanInvoice(self, sequence, **kw):
    sequence['invoice'].plan()

  def stepConfirmInvoice(self, sequence, **kw):
    sequence['invoice'].confirm()

  def stepStartInvoice(self, sequence, **kw):
    sequence['invoice'].start()

  def stepCheckWebUserBalanceHighAmount(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    self.assertEqual(-10000.0,
      self.portal.portal_simulation.getInventoryAssetPrice(
      node_category='account_type/asset/receivable',
      simulation_state=['started', 'stopped', 'delivered'],
      section_uid=self.portal.restrictedTraverse(
        'organisation_module/vifib_internet').getUid(),
      mirror_section_uid=person.getUid())
    )

  def stepCheckWebUserBalanceSmallAmount(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    self.assertEqual(-1.0,
      self.portal.portal_simulation.getInventoryAssetPrice(
      node_category='account_type/asset/receivable',
      simulation_state=['started', 'stopped', 'delivered'],
      section_uid=self.portal.restrictedTraverse(
        'organisation_module/vifib_internet').getUid(),
      mirror_section_uid=person.getUid())
    )

  def stepCreatePastSmallPayment(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    payment_transaction = self.portal.accounting_module.newContent(
        destination_section='organisation_module/vifib_internet',
        source_section=person.getRelativeUrl(),
        resource='currency_module/EUR',
        portal_type="Payment Transaction",
        start_date=DateTime()-90,
        )
    payment_transaction.newContent(
        portal_type="Accounting Transaction Line",
        quantity=1,
        destination='account_module/receivable',
        )
    payment_transaction.newContent(
        portal_type="Accounting Transaction Line",
        quantity=-1,
        destination='account_module/sales',
        )
    payment_transaction.confirm()
    payment_transaction.checkConsistency()

    sequence['payment_transaction'] = payment_transaction

  def stepCancelPayment(self, sequence, **kw):
    sequence['payment_transaction'].cancel()

  def stepStartPayment(self, sequence, **kw):
    sequence['payment_transaction'].start()

  def stepStopPayment(self, sequence, **kw):
    sequence['payment_transaction'].stop()

  def stepDeliverPayment(self, sequence, **kw):
    sequence['payment_transaction'].deliver()

  def stepCreateHighBalanceInvoiceWebUser(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    invoice = self.portal.accounting_module.newContent(
      portal_type='Sale Invoice Transaction',
      start_date=DateTime(),
      resource='currency_module/EUR',
      source_section='organisation_module/vifib_internet',
      source='organisation_module/vifib_internet',
      destination_section=person.getRelativeUrl(),
      destination=person.getRelativeUrl(),
      specialise='sale_trade_condition_module/vifib_trade_condition'
    )
    invoice.newContent(
      portal_type='Invoice Line',
      resource=self.portal.portal_preferences.getPreferredRegistrationResource(),
      quantity=1,
      price=10000
    )
    sequence['invoice'] = invoice

  def new_software_instance_string(self):
    return \
      self.prepare_installed_software_release_sequence_string + \
      self.register_new_user_sequence_string + '\
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      ' + \
      self.create_new_user_instance_sequence_string

  def new_slave_instance_string(self):
    return \
      self.prepare_installed_computer_partition_sequence_string + \
      self.register_new_user_sequence_string + '\
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      ' + \
      self.create_new_user_slave_instance_sequence_string

  def lock_user_string(self):
    return '\
      LoginERP5TypeTestCase \
      TriggerBuild \
      Tic \
      TriggerStopConfirmedInvoiceAlarm \
      Tic \
      TriggerBuild \
      Tic \
      Logout'

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionLock))
  return suite
