import unittest
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.DateUtils import getClosestDate, addToDate
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

from DateTime.DateTime import DateTime

class TestVifibInstanceHostingRelatedDocument(TestVifibSlapWebServiceMixin):

  def stepBuildOneMoreSalePackingList(self, sequence, **kw):
    sequence.edit(
      number_of_sale_packing_list=\
      len(self.portal.sale_packing_list_module.contentValues()))
    build_before = sequence.get('build_before')
    if build_before is None:
      build_before = getClosestDate(
        target_date=DateTime(), precision='month', before=0)
      self.portal.portal_alarms.build_deliver_path.activeSense()
    else:
      build_before = addToDate(build_before, month=1)
      self.portal.portal_alarms.build_deliver_path.activeSense(
        params={'build_before':build_before})
    sequence.edit(build_before=build_before)

  def stepCheckSalePackingList(self, sequence, **kw):
    # check one more sale packing list is generated
    # and only one sale packing list line is inside
    self.assertEquals(
      len(self.portal.sale_packing_list_module.contentValues()),
      sequence.get('number_of_sale_packing_list') + 1)
    build_before = sequence.get('build_before')
    sale_packing_list = \
      self.portal.sale_packing_list_module.contentValues(
        portal_type="Sale Packing List",
        sort_on=(("creation_date", "DESC"),))[0]
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
    hosting_subscription = \
      open_order_line.getAggregateValue(portal_type="Hosting Subscription")

    # check related property
    self.assertEquals(open_order_line.getSpecialise(),
      sale_packing_list.getSpecialise())

  def stepBuildOneMoreInvoice(self, sequence, **kw):
    sequence.edit(number_of_invoice=\
      len(self.portal.accounting_module.contentValues(
        portal_type="Sale Invoice Transaction")))
    self.portal.portal_alarms.build_invoice_path.activeSense()

  def stepBuildOneMoreInvoiceTransaction(self, sequence, **kw):
    self.portal.portal_alarms.build_account_path.activeSense()

  def stepCheckInvoiceAndInvoiceTransaction(self, sequence, **kw):
    self.assertEquals(
      len(self.portal.accounting_module.contentValues(
        portal_type="Sale Invoice Transaction")),
      sequence.get('number_of_invoice') + 1)
    invoice = self.portal.accounting_module.contentValues(
      portal_type="Sale Invoice Transaction",
      sort_on=(("creation_date", "DESC"),))[0]

  def stepBuildOneMorePayment(self, sequence, **kw):
    sequence.edit(number_of_payment=\
      len(self.portal.accounting_module.contentValues(
        portal_type="Payment Transaction")))
    self.portal.portal_alarms.build_pay_path.activeSense()

  def stepCheckPayment(self, sequence, **kw):
    self.assertEquals(
      len(self.portal.accounting_module.contentValues(
        portal_type="Payment Transaction")),
      sequence.get('number_of_payment') + 1)
    payment = self.portal.accounting_module.contentValues(
      portal_type="Payment Transaction",
      sort_on=(("creation_date", "DESC"),))[0]

  def stepRefresh(self, sequence, **kw):
    self.stepBuildOneMoreInvoice(sequence, **kw)
    self.stepBuildOneMoreInvoiceTransaction(sequence, **kw)
    self.stepBuildOneMorePayment(sequence, **kw)

  def test_OpenOrder_sale_packing_list(self):
    """
    Check that sale_packing_list is generated properly from simulation
    """
    check_one_month = """
      LoginDefaultUser
      BuildOneMoreSalePackingList
      Tic
      SlapLogout
      LoginDefaultUser
      CheckSalePackingList
      Tic
      Logout
      LoginDefaultUser
      BuildOneMoreInvoice
      Tic
      BuildOneMoreInvoiceTransaction
      Tic
      SlapLogout
      LoginDefaultUser
      CheckInvoiceAndInvoiceTransaction
      Tic
      Logout
      LoginDefaultUser
      BuildOneMorePayment
      Tic
      SlapLogout
      LoginDefaultUser
      CheckPayment
      Tic
      Logout
    """
    self.computer_partition_amount = 1
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_installed_computer_partition_sequence_string \
          + """
        LoginDefaultUser
        Refresh
        Tic
        SlapLogout
        """ + (check_one_month * 12)
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibInstanceHostingRelatedDocument))
  return suite
