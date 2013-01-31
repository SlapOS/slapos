# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction

class TestSlapOSPaymentTransactionOrderBuilder(testSlapOSMixin):
  def sumReceivable(self, transaction):
    quantity = .0
    default_source_uid = self.portal.restrictedTraverse(
        'account_module/receivable').getUid()
    for line in transaction.searchFolder(
        portal_type=self.portal.getPortalAccountingMovementTypeList(),
        default_source_uid=default_source_uid):
      quantity += line.getQuantity()
    return quantity

  def assertPayment(self, payment, invoice):
    self.assertEqual(self.sumReceivable(invoice), payment\
        .PaymentTransaction_getTotalPayablePrice())
    self.assertEqual('confirmed', payment.getSimulationState())
    self.assertSameSet([], payment.checkConsistency())
    self.assertSameSet([invoice], payment.getCausalityValueList())
    self.assertSameSet([], payment.getCausalityRelatedValueList(
        portal_type='Applied Rule'))
    expected_set = [
      'causality/%s' % invoice.getRelativeUrl(),
      'destination_section/%s' % invoice.getDestinationSection(),
      'price_currency/%s' % invoice.getPriceCurrency(),
      'resource/%s' % invoice.getResource(),
      'source_payment/organisation_module/slapos/bank_account',
      'payment_mode/payzen',
      'source_section/%s' % invoice.getSourceSection(),
    ]
    self.assertSameSet(expected_set, payment.getCategoryList())
    self.assertEqual(invoice.getStartDate(), payment.getStartDate())
    self.assertEqual(invoice.getStopDate(), payment.getStopDate())

    movement_list = payment.getMovementList()
    self.assertEqual(2, len(movement_list))
    bank_list = [q for q in movement_list
        if q.getSource() == 'account_module/bank']
    rec_list = [q for q in movement_list
        if q.getSource() == 'account_module/receivable']
    self.assertEqual(1, len(bank_list))
    self.assertEqual(1, len(rec_list))

    def assertLine(line, quantity, category_list):
      self.assertFalse(line.hasStartDate())
      self.assertFalse(line.hasStopDate())
      self.assertEqual(quantity, line.getQuantity())
      self.assertSameSet(category_list, line.getCategoryList())

    invoice_amount = self.sumReceivable(invoice)
    assertLine(bank_list[0], invoice_amount, [
        'destination/account_module/bank',
        'source/account_module/bank'])
    assertLine(rec_list[0], -1 * invoice_amount, [
        'destination/account_module/payable',
        'source/account_module/receivable'])

  def emptyBuild(self, **kw):
    delivery_list = self._build(**kw)
    self.assertSameSet([], delivery_list)
    return delivery_list

  def fullBuild(self, **kw):
    delivery_list = self._build(**kw)
    self.assertNotEqual([], delivery_list)
    return delivery_list

  def _build(self, **kw):
    return self.portal.portal_orders.slapos_payment_transaction_builder.build(
        **kw)

  def test(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice.edit(destination_section=person.getRelativeUrl())
    invoice.confirm()
    invoice.stop()
    self.tic()
    payment_list = self.fullBuild(uid=invoice.getUid())
    self.tic()

    self.assertEqual(1, len(payment_list))

    payment = payment_list[0].getObject()
    self.assertPayment(payment, invoice)

  def test_twice(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice.edit(destination_section=person.getRelativeUrl())
    invoice.confirm()
    invoice.stop()
    self.tic()
    payment_list = self.fullBuild(uid=invoice.getUid())
    self.tic()
    self.emptyBuild(uid=invoice.getUid())

    self.assertEqual(1, len(payment_list))

    payment = payment_list[0].getObject()
    self.assertPayment(payment, invoice)

  def test_twice_transaction(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice.edit(destination_section=person.getRelativeUrl())
    invoice.confirm()
    invoice.stop()
    self.tic()
    payment_list = self.fullBuild(uid=invoice.getUid())
    self.emptyBuild(uid=invoice.getUid())
    self.tic()

    self.assertEqual(1, len(payment_list))

    payment = payment_list[0].getObject()
    self.assertPayment(payment, invoice)

  def test_twice_indexation(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice.edit(destination_section=person.getRelativeUrl())
    invoice.confirm()
    invoice.stop()
    self.tic()
    payment_list = self.fullBuild(uid=invoice.getUid())
    transaction.commit()
    # the payment transaction is immediately indexed
    self.assertEqual(1, len(payment_list))

    self.emptyBuild(uid=invoice.getUid())
    self.tic()


    payment = payment_list[0].getObject()
    self.assertPayment(payment, invoice)

  def test_cancelled_payment(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice.edit(destination_section=person.getRelativeUrl())
    invoice.confirm()
    invoice.stop()
    self.tic()
    payment_list = self.fullBuild(uid=invoice.getUid())
    payment_list[0].cancel()
    self.tic()
    payment_list = self.fullBuild(uid=invoice.getUid())
    self.tic()
    self.emptyBuild(uid=invoice.getUid())

    self.assertEqual(1, len(payment_list))

    payment = payment_list[0].getObject()
    self.assertPayment(payment, invoice)

  def test_two_invoices(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice_1 = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice_1.edit(destination_section=person.getRelativeUrl())
    invoice_1.confirm()
    invoice_1.stop()
    invoice_2 = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice_2.edit(destination_section=person.getRelativeUrl())
    invoice_2.confirm()
    invoice_2.stop()
    self.tic()
    payment_list = self.fullBuild(uid=[invoice_1.getUid(), invoice_2.getUid()])
    self.tic()

    self.assertEqual(2, len(payment_list))

    payment_1_list = [q for q in payment_list
        if q.getCausalityValue() == invoice_1]
    payment_2_list = [q for q in payment_list
        if q.getCausalityValue() == invoice_2]
    self.assertEqual(1, len(payment_1_list))
    self.assertEqual(1, len(payment_2_list))
    payment_1 = payment_1_list[0]
    payment_2 = payment_2_list[0]
    self.assertPayment(payment_1, invoice_1)
    self.assertPayment(payment_2, invoice_2)

  def test_two_lines(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    invoice = self.portal.accounting_module.template_sale_invoice_transaction\
        .Base_createCloneDocument(batch_mode=1)
    invoice.edit(destination_section=person.getRelativeUrl())
    self.tic()
    default_source_uid = self.portal.restrictedTraverse(
        'account_module/receivable').getUid()
    modified = False
    for line in invoice.searchFolder(
        portal_type=self.portal.getPortalAccountingMovementTypeList(),
        default_source_uid=default_source_uid):
      quantity = line.getQuantity() / 2
      line.edit(quantity=quantity)
      line.getObject().Base_createCloneDocument(batch_mode=1).edit(
          quantity=quantity)
      modified = True
      break
    self.assertTrue(modified)

    invoice.confirm()
    invoice.stop()
    self.tic()
    payment_list = self.fullBuild(uid=[invoice.getUid()])
    self.tic()

    self.assertEqual(1, len(payment_list))

    payment = payment_list[0].getObject()
    self.assertPayment(payment, invoice)

