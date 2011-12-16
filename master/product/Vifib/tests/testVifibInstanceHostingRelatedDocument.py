import unittest
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.DateUtils import getClosestDate, addToDate
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

from DateTime.DateTime import DateTime

class TestVifibInstanceHostingRelatedDocument(TestVifibSlapWebServiceMixin):

  def stepBuildOneMoreSalePackingList(self, sequence, **kw):
    build_before = sequence.get('build_before')
    self.portal.portal_alarms.vifib_trigger_build.activeSense()
    if build_before is None:
      build_before = getClosestDate(
        target_date=DateTime(), precision='month', before=0)
      self.portal.portal_alarms.build_deliver_path.activeSense()
    else:
      build_before = addToDate(build_before, month=1)
      self.portal.portal_alarms.build_deliver_path.activeSense(
        params={'build_before':build_before})
    sequence.edit(build_before=build_before)

  def stepTriggerNextBuild(self, sequence, **kw):
    sequence.edit(
      number_of_sale_packing_list=sequence.get(
        'number_of_sale_packing_list', 0) + 1,
      number_of_invoice=sequence.get('number_of_invoice', 0) + 1,
      number_of_payment=sequence.get('number_of_payment', 0) + 1
    )
    self.portal.portal_alarms.vifib_trigger_build.activeSense()

  def stepCheckOneMoreDocumentList(self, sequence, **kw):
    hosting_subscription = self.portal.portal_catalog\
      .getResultValue(uid=sequence['hosting_subscription_uid'])
    sale_packing_list_list = self.portal.portal_catalog(
      portal_type='Sale Packing List',
      causality_relative_url=hosting_subscription.getRelativeUrl(),
      sort_on=(('delivery.start_date', "DESC")))

    self.assertEqual(sequence['number_of_sale_packing_list'],
      len(sale_packing_list_list))

    sale_packing_list = sale_packing_list_list[0].getObject()
    sale_invoice_transaction_list = sale_packing_list\
      .getCausalityRelatedValueList(portal_type='Sale Invoice Transaction')
    self.assertEqual(1, len(sale_invoice_transaction_list))
    sale_invoice_transaction = sale_invoice_transaction_list[0]

    payment_transaction_list = sale_invoice_transaction\
      .getCausalityRelatedValueList(portal_type='Payment Transaction')
    self.assertEqual(1, len(payment_transaction_list))
    payment_transaction = payment_transaction_list[0]

    sequence.edit(
      current_sale_packing_list=sale_packing_list,
      current_sale_invoice_transaction=sale_invoice_transaction,
      current_payment_transaction=payment_transaction
    )

  def stepCheckSalePackingList(self, sequence, **kw):
    # check one more sale packing list is generated
    # and only one sale packing list line is inside
    sale_packing_list = sequence['current_sale_packing_list']
    sale_packing_list_line_list = \
      sale_packing_list.contentValues(portal_type="Sale Packing List Line")
    self.assertEquals(1, len(sale_packing_list_line_list))
    sale_packing_list_line = sale_packing_list_line_list[0]

    # check sale packing list related property
    self.assertEquals("organisation_module/vifib_internet",
      sale_packing_list.getSource())
    self.assertEquals("organisation_module/vifib_internet",
      sale_packing_list.getSourceSection())
    self.assertEquals("person_module/test_vifib_customer",
      sale_packing_list.getDestination())
    self.assertEquals("person_module/test_vifib_customer",
      sale_packing_list.getDestinationSection())
    self.assertEquals("currency_module/EUR",
      sale_packing_list.getPriceCurrency())

    # check sale packing list line related property
    self.assertEquals("service_module/vifib_instance_subscription",
      sale_packing_list_line.getResource())
    self.assertEquals(1,
      sale_packing_list_line.getQuantity())
    self.assertEquals("unit/piece",
      sale_packing_list_line.getQuantityUnit())
    self.assertEquals(1,
      sale_packing_list_line.getPrice())

    # fetch open order, open order line and subscription
    person = self.portal.person_module['test_vifib_customer']
    open_order = \
      person.getDestinationDecisionRelatedValue(portal_type="Open Sale Order")
    open_order_line = \
      open_order.contentValues(portal_type="Open Sale Order Line")[0]

    # check related property
    self.assertEquals(open_order_line.getSpecialise(),
      sale_packing_list.getSpecialise())

  def stepCheckInvoiceAndInvoiceTransaction(self, sequence, **kw):
    sale_invoice_transaction = sequence['current_sale_invoice_transaction']
    self.assertEqual(sale_invoice_transaction.getSimulationState(),
      'confirmed')
    self.assertEqual(sale_invoice_transaction.getCausalityList(),
      [sequence['current_sale_packing_list'].getRelativeUrl()])
    self.portal.portal_workflow.doActionFor(sale_invoice_transaction,
      'start_action')
    self.assertEqual(sale_invoice_transaction.getSimulationState(),
      'started')

  def stepCheckPayment(self, sequence, **kw):
    payment_transaction = sequence['current_payment_transaction']
    self.assertEqual(payment_transaction.getSimulationState(), 'planned')
    self.assertEqual(payment_transaction.getCausalityList(),
      [sequence['current_sale_invoice_transaction'].getRelativeUrl()])
    self.portal.portal_workflow.doActionFor(payment_transaction,
      'confirm_action')
    self.assertEqual(payment_transaction.getSimulationState(),
      'confirmed')

  def test_OpenOrder_sale_packing_list(self):
    """
    Check that sale_packing_list is generated properly from simulation
    """
    check_one_month = """
      LoginDefaultUser
      TriggerNextBuild
      Tic
      Logout

      LoginDefaultUser
      CheckOneMoreDocumentList
      CheckSalePackingList
      CheckInvoiceAndInvoiceTransaction
      CheckPayment
      Logout
    """
    self.computer_partition_amount = 1
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_installed_computer_partition_sequence_string \
          + (check_one_month * 12)
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibInstanceHostingRelatedDocument))
  return suite
