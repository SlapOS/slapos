from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from Products.DCWorkflow.DCWorkflow import ValidationFailed
from random import random
from slapos import slap
from zExceptions import Unauthorized
from DateTime import DateTime
from Products.ERP5Type.tests.backportUnittest import skip

class TestVifibDefaultUseCase(TestVifibSlapWebServiceMixin):

  def stepCheckRegistrationAccounting(self, sequence, **kw):
    """
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])

    # Check that one sale invoice has been generated for the user
    transaction_list = self.portal.portal_catalog(
      portal_type="Sale Invoice Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      )
    self.assertEquals(1, len(transaction_list))

    sale_invoice = transaction_list[0].getObject()

    # Check invoice creation
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSourceSection())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestinationSection())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getResource())
    self.assertEquals(
      'sale_trade_condition_module/vifib_trade_condition',
      sale_invoice.getSpecialise())
    self.assertEquals(
      'stopped',
      sale_invoice.getSimulationState())
    self.assertAlmostEquals(
      1, sale_invoice.getTotalPrice(), 3)

    # 2 invoice lines are expected
    invoice_line_list = sale_invoice.contentValues(
        portal_type="Invoice Line")
    self.assertEquals(2, len(invoice_line_list))

    service_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_registration'][0]
    vat_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_tax'][0]

    self.assertEquals(True, service_line.hasPrice())
    self.assertAlmostEquals(0.836, service_line.getPrice(), 3)
    self.assertEquals(1, service_line.getQuantity())

    self.assertEquals(True, vat_line.hasPrice())
    self.assertAlmostEquals(0.196, vat_line.getPrice(), 3)
    self.assertAlmostEquals(0.836, vat_line.getQuantity(), 3)

    # 3 transaction lines
    transaction_line_list = sale_invoice.contentValues(
        portal_type="Sale Invoice Transaction Line")
    self.assertEquals(3, len(transaction_line_list))

    sale_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/sales'][0]
    receivable_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/receivable'][0]
    vat_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/coll_vat'][0]

    self.assertAlmostEquals(1, receivable_line.getPrice(), 3)
    self.assertAlmostEquals(-1, receivable_line.getQuantity(), 3)
    self.assertEquals('account_module/receivable', receivable_line.getSource())
    self.assertEquals('account_module/payable', receivable_line.getDestination())
    self.assertEquals('sale_trade_condition_module/vifib_trade_condition', receivable_line.getSpecialise())

    self.assertAlmostEquals(1, sale_line.getPrice(), 3)
    self.assertAlmostEquals(0.836, sale_line.getQuantity(), 3)
    self.assertEquals('account_module/sales', sale_line.getSource())
    self.assertEquals('account_module/purchase', sale_line.getDestination())
    self.assertEquals('sale_trade_condition_module/vifib_trade_condition', sale_line.getSpecialise())

    self.assertAlmostEquals(1, vat_line.getPrice(), 3)
    self.assertAlmostEquals(0.164, vat_line.getQuantity(), 3)
    self.assertEquals('account_module/coll_vat', vat_line.getSource())
    self.assertEquals('account_module/refundable_vat', vat_line.getDestination())
    self.assertEquals('sale_trade_condition_module/vifib_trade_condition', vat_line.getSpecialise())

    # XXX Check user interface display
    self.assertEquals(
      'Waiting for payment',
      sale_invoice.portal_skins.vifib_hosting.AccountingTransaction_getPaymentState())
    self.assertEquals('solved', sale_invoice.getCausalityState())

    # Check the payment transaction
    payment_list = self.portal.portal_catalog(
      portal_type="Payment Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      )
    self.assertEquals(1, len(payment_list))

    payment = payment_list[0]
    sequence.edit(payment_transaction_uid=payment.getUid())

    # Payment should have a causality link
    self.assertEquals(sale_invoice.getRelativeUrl(), payment.getCausality())

    # Check invoice creation
    self.assertEquals(
      None,
      payment.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      payment.getSourceSection())
    self.assertEquals(
      None,
      payment.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      payment.getDestinationSection())
    self.assertEquals(
      None,
      payment.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      payment.getResource())
    self.assertEquals(
      None,
      payment.getSpecialise())
    self.assertEquals(
      'planned',
      payment.getSimulationState())
    self.assertAlmostEquals(
      0, payment.getTotalPrice(), 3)
    self.assertEquals('solved', payment.getCausalityState())

    transaction_line_list = payment.contentValues(
        portal_type="Accounting Transaction Line")
    self.assertEquals(2, len(transaction_line_list))

    sale_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/bank'][0]
    receivable_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/receivable'][0]

    self.assertEquals(True, receivable_line.hasPrice())
    self.assertAlmostEquals(1, receivable_line.getPrice(), 3)
    self.assertAlmostEquals(1, receivable_line.getQuantity(), 3)
    self.assertEquals('account_module/receivable', receivable_line.getSource())
    self.assertEquals('account_module/payable', receivable_line.getDestination())
    self.assertEquals('sale_trade_condition_module/vifib_trade_condition', receivable_line.getSpecialise())

    self.assertEquals(True, sale_line.hasPrice())
    self.assertAlmostEquals(1, sale_line.getPrice(), 3)
    self.assertAlmostEquals(-1, sale_line.getQuantity(), 3)
    self.assertEquals('account_module/bank', sale_line.getSource())
    self.assertEquals('account_module/bank', sale_line.getDestination())
    self.assertEquals('sale_trade_condition_module/vifib_trade_condition', sale_line.getSpecialise())

  def stepCheckPaidRegistrationAccounting(self, sequence, **kw):
    """
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])

    # Check that one sale invoice has been generated for the user
    transaction_list = self.portal.portal_catalog(
      portal_type="Sale Invoice Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      )
    self.assertEquals(1, len(transaction_list))

    sale_invoice = transaction_list[0].getObject()

    # Check invoice creation
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSourceSection())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestinationSection())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getResource())
    self.assertEquals(
      'sale_trade_condition_module/vifib_trade_condition',
      sale_invoice.getSpecialise())
    self.assertEquals(
      'stopped',
      sale_invoice.getSimulationState())
    self.assertAlmostEquals(
      1, sale_invoice.getTotalPrice(), 3)

    # 2 invoice lines are expected
    invoice_line_list = sale_invoice.contentValues(
        portal_type="Invoice Line")
    self.assertEquals(2, len(invoice_line_list))

    service_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_registration'][0]
    vat_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_tax'][0]

    self.assertEquals(True, service_line.hasPrice())
    self.assertAlmostEquals(0.836, service_line.getPrice(), 3)
    self.assertEquals(1, service_line.getQuantity())

    self.assertEquals(True, vat_line.hasPrice())
    self.assertAlmostEquals(0.196, vat_line.getPrice(), 3)
    self.assertAlmostEquals(0.836, vat_line.getQuantity(), 3)

    # 3 transaction lines
    transaction_line_list = sale_invoice.contentValues(
        portal_type="Sale Invoice Transaction Line")
    self.assertEquals(3, len(transaction_line_list))

    sale_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/sales'][0]
    receivable_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/receivable'][0]
    vat_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/coll_vat'][0]

    self.assertAlmostEquals(1, receivable_line.getPrice(), 3)
    self.assertAlmostEquals(-1, receivable_line.getQuantity(), 3)
    self.assertEquals('account_module/receivable', receivable_line.getSource())
    self.assertEquals('account_module/payable', receivable_line.getDestination())
    self.assertEquals('sale_trade_condition_module/vifib_trade_condition', receivable_line.getSpecialise())
    self.assertTrue(receivable_line.hasGroupingReference())
    invoice_grouping_reference = receivable_line.getGroupingReference()

    self.assertAlmostEquals(1, sale_line.getPrice(), 3)
    self.assertAlmostEquals(0.836, sale_line.getQuantity(), 3)
    self.assertEquals('account_module/sales', sale_line.getSource())
    self.assertEquals('account_module/purchase', sale_line.getDestination())
    self.assertEquals('sale_trade_condition_module/vifib_trade_condition', sale_line.getSpecialise())

    self.assertAlmostEquals(1, vat_line.getPrice(), 3)
    self.assertAlmostEquals(0.164, vat_line.getQuantity(), 3)
    self.assertEquals('account_module/coll_vat', vat_line.getSource())
    self.assertEquals('account_module/refundable_vat', vat_line.getDestination())
    self.assertEquals('sale_trade_condition_module/vifib_trade_condition', vat_line.getSpecialise())

    # XXX Check user interface display
    self.assertEquals(
      'Paid',
      sale_invoice.portal_skins.vifib_hosting.AccountingTransaction_getPaymentState())
    self.assertEquals('solved', sale_invoice.getCausalityState())

    # Check the payment transaction
    payment_list = self.portal.portal_catalog(
      portal_type="Payment Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      )
    self.assertEquals(1, len(payment_list))

    payment = payment_list[0]
    sequence.edit(payment_transaction_uid=payment.getUid())

    # Payment should have a causality link
    self.assertEquals(sale_invoice.getRelativeUrl(), payment.getCausality())

    # Check invoice creation
    self.assertEquals(
      None,
      payment.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      payment.getSourceSection())
    self.assertEquals(
      None,
      payment.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      payment.getDestinationSection())
    self.assertEquals(
      None,
      payment.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      payment.getResource())
    self.assertEquals(
      None,
      payment.getSpecialise())
    self.assertEquals(
      'stopped',
      payment.getSimulationState())
    self.assertAlmostEquals(
      0, payment.getTotalPrice(), 3)
    self.assertEquals('solved', payment.getCausalityState())

    transaction_line_list = payment.contentValues(
        portal_type="Accounting Transaction Line")
    self.assertEquals(2, len(transaction_line_list))

    sale_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/bank'][0]
    receivable_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/receivable'][0]

    self.assertAlmostEquals(1, receivable_line.getPrice(), 3)
    self.assertAlmostEquals(1, receivable_line.getQuantity(), 3)
    self.assertEquals('account_module/receivable', receivable_line.getSource())
    self.assertEquals('account_module/payable', receivable_line.getDestination())
    self.assertEquals('sale_trade_condition_module/vifib_trade_condition', receivable_line.getSpecialise())
    self.assertTrue(receivable_line.hasGroupingReference())
    self.assertEquals(invoice_grouping_reference,
                      receivable_line.getGroupingReference())

    self.assertAlmostEquals(1, sale_line.getPrice(), 3)
    self.assertAlmostEquals(-1, sale_line.getQuantity(), 3)
    self.assertEquals('account_module/bank', sale_line.getSource())
    self.assertEquals('account_module/bank', sale_line.getDestination())
    self.assertEquals('sale_trade_condition_module/vifib_trade_condition', sale_line.getSpecialise())

  def stepCheckSetupOngoingInvoice(self, sequence, **kw):
    """
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])

    # Check that 2 sale invoice has been generated for the user
    transaction_list = self.portal.portal_catalog(
      portal_type="Sale Invoice Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      )
    self.assertEquals(2, len(transaction_list))

    # Check that 1 ongoing sale invoice has been generated for the user
    transaction_list = self.portal.portal_catalog(
      portal_type="Sale Invoice Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      simulation_state='planned',
      )
    self.assertEquals(1, len(transaction_list))

    sale_invoice = transaction_list[0].getObject()

    # Check invoice creation
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSourceSection())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestinationSection())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getResource())
#     self.assertEquals(
#       'sale_trade_condition_module/vifib_trade_condition',
#       sale_invoice.getSpecialise())
    self.assertEquals(
      'planned',
      sale_invoice.getSimulationState())
    self.assertAlmostEquals(
      0.836, sale_invoice.getTotalPrice(), 3)

    # 1 invoice line is expected
    invoice_line_list = sale_invoice.contentValues(
        portal_type="Invoice Line")
    self.assertEquals(2, len(invoice_line_list))

    service_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_setup'][0]
    subscription_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_subscription'][0]

    self.assertEquals(True, service_line.hasPrice())
    self.assertAlmostEquals(0, service_line.getPrice(), 3)
    self.assertEquals(1, service_line.getQuantity())

    self.assertEquals(True, subscription_line.hasPrice())
    self.assertAlmostEquals(0.836, subscription_line.getPrice(), 3)
    self.assertEquals(1, subscription_line.getQuantity())

    # 0 transaction line
    transaction_line_list = sale_invoice.contentValues(
        portal_type="Sale Invoice Transaction Line")
    self.assertEquals(0, len(transaction_line_list))

    # XXX Check user interface display
    self.assertEquals(
      'Ongoing',
      sale_invoice.portal_skins.vifib_hosting.AccountingTransaction_getPaymentState())
    self.assertEquals('solved', sale_invoice.getCausalityState())

  def stepCheckHostingOngoingInvoice(self, sequence, **kw):
    """
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])

    # Check that 2 sale invoice has been generated for the user
    transaction_list = self.portal.portal_catalog(
      portal_type="Sale Invoice Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      )
    self.assertEquals(2, len(transaction_list))

    # Check that 1 ongoing sale invoice has been generated for the user
    transaction_list = self.portal.portal_catalog(
      portal_type="Sale Invoice Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      simulation_state='planned',
      )
    self.assertEquals(1, len(transaction_list))

    sale_invoice = transaction_list[0].getObject()

    # Check invoice creation
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSourceSection())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestinationSection())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getResource())
#     self.assertEquals(
#       'sale_trade_condition_module/vifib_trade_condition',
#       sale_invoice.getSpecialise())
    self.assertEquals(
      'planned',
      sale_invoice.getSimulationState())
    self.assertAlmostEquals(
      0.836, sale_invoice.getTotalPrice(), 3)

    # 1 invoice line is expected
    invoice_line_list = sale_invoice.contentValues(
        portal_type="Invoice Line")
    self.assertEquals(3, len(invoice_line_list))

    service_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_setup'][0]
    subscription_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_subscription'][0]
    hosting_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_hosting'][0]

    self.assertEquals(True, service_line.hasPrice())
    self.assertAlmostEquals(0, service_line.getPrice(), 3)
    self.assertEquals(1, service_line.getQuantity())

    self.assertEquals(True, subscription_line.hasPrice())
    self.assertAlmostEquals(0.836, subscription_line.getPrice(), 3)
    self.assertEquals(1, subscription_line.getQuantity())

    self.assertEquals(True, hosting_line.hasPrice())
    self.assertAlmostEquals(0, hosting_line.getPrice(), 3)
    self.assertEquals(1, hosting_line.getQuantity())

    # 0 transaction line
    transaction_line_list = sale_invoice.contentValues(
        portal_type="Sale Invoice Transaction Line")
    self.assertEquals(0, len(transaction_line_list))

    # XXX Check user interface display
    self.assertEquals(
      'Ongoing',
      sale_invoice.portal_skins.vifib_hosting.AccountingTransaction_getPaymentState())
    self.assertEquals('solved', sale_invoice.getCausalityState())

  def stepCheckDestroyOngoingInvoice(self, sequence, **kw):
    """
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])

    # Check that 2 sale invoice has been generated for the user
    transaction_list = self.portal.portal_catalog(
      portal_type="Sale Invoice Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      )
    self.assertEquals(2, len(transaction_list))

    # Check that 1 ongoing sale invoice has been generated for the user
    transaction_list = self.portal.portal_catalog(
      portal_type="Sale Invoice Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      simulation_state='planned',
      )
    self.assertEquals(1, len(transaction_list))

    sale_invoice = transaction_list[0].getObject()

    # Check invoice creation
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSourceSection())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestinationSection())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getResource())
#     self.assertEquals(
#       'sale_trade_condition_module/vifib_trade_condition',
#       sale_invoice.getSpecialise())
    self.assertEquals(
      'planned',
      sale_invoice.getSimulationState())
    self.assertAlmostEquals(
      0.836, sale_invoice.getTotalPrice(), 3)

    # 1 invoice line is expected
    invoice_line_list = sale_invoice.contentValues(
        portal_type="Invoice Line")
    self.assertEquals(4, len(invoice_line_list))

    service_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_setup'][0]
    subscription_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_subscription'][0]
    hosting_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_hosting'][0]
    destroy_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_cleanup'][0]

    self.assertEquals(True, service_line.hasPrice())
    self.assertAlmostEquals(0, service_line.getPrice(), 3)
    self.assertEquals(1, service_line.getQuantity())

    self.assertEquals(True, subscription_line.hasPrice())
    self.assertAlmostEquals(0.836, subscription_line.getPrice(), 3)
    self.assertEquals(1, subscription_line.getQuantity())

    self.assertEquals(True, hosting_line.hasPrice())
    self.assertAlmostEquals(0, hosting_line.getPrice(), 3)
    self.assertEquals(1, hosting_line.getQuantity())

    self.assertEquals(True, destroy_line.hasPrice())
    self.assertAlmostEquals(0, destroy_line.getPrice(), 3)
    self.assertEquals(1, destroy_line.getQuantity())

    # 0 transaction line
    transaction_line_list = sale_invoice.contentValues(
        portal_type="Sale Invoice Transaction Line")
    self.assertEquals(0, len(transaction_line_list))

    # XXX Check user interface display
    self.assertEquals(
      'Ongoing',
      sale_invoice.portal_skins.vifib_hosting.AccountingTransaction_getPaymentState())
    self.assertEquals('solved', sale_invoice.getCausalityState())

  def stepConfirmOngoingInvoice(self, sequence, **kw):
    """
    """
    for invoice in self.portal.portal_catalog(
        portal_type="Sale Invoice Transaction",
        simulation_state="planned"):
      invoice = invoice.getObject()
      invoice.confirm()

  def stepCheckWaitingInvoice(self, sequence, **kw):
    """
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])

    # Check that 2 sale invoice has been generated for the user
    transaction_list = self.portal.portal_catalog(
      portal_type="Sale Invoice Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      sort_on=(('uid', 'DESC')),
      )
    self.assertEquals(2, len(transaction_list))

    sale_invoice = transaction_list[0].getObject()

    # Check invoice creation
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSourceSection())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestinationSection())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getResource())
#     self.assertEquals(
#       'sale_trade_condition_module/vifib_trade_condition',
#       sale_invoice.getSpecialise())
    self.assertEquals(
      'stopped',
      sale_invoice.getSimulationState())
    self.assertAlmostEquals(
      1, sale_invoice.getTotalPrice(), 3)

    # 5 invoice lines are expected
    invoice_line_list = sale_invoice.contentValues(
        portal_type="Invoice Line")
    self.assertEquals(5, len(invoice_line_list))

    service_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_setup'][0]
    subscription_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_subscription'][0]
    hosting_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_hosting'][0]
    destroy_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_cleanup'][0]
    tax_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_tax'][0]

    self.assertEquals(True, service_line.hasPrice())
    self.assertAlmostEquals(0, service_line.getPrice(), 3)
    self.assertEquals(1, service_line.getQuantity())

    self.assertEquals(True, subscription_line.hasPrice())
    self.assertAlmostEquals(0.836, subscription_line.getPrice(), 3)
    self.assertEquals(1, subscription_line.getQuantity())

    self.assertEquals(True, hosting_line.hasPrice())
    self.assertAlmostEquals(0, hosting_line.getPrice(), 3)
    self.assertEquals(1, hosting_line.getQuantity())

    self.assertEquals(True, destroy_line.hasPrice())
    self.assertAlmostEquals(0, destroy_line.getPrice(), 3)
    self.assertEquals(1, destroy_line.getQuantity())

    self.assertEquals(True, tax_line.hasPrice())
    self.assertAlmostEquals(0.196, tax_line.getPrice(), 3)
    self.assertAlmostEquals(0.836, tax_line.getQuantity(), 3)

    # 0 transaction line
    transaction_line_list = sale_invoice.contentValues(
        portal_type="Sale Invoice Transaction Line")
    self.assertEquals(3, len(transaction_line_list))

    sale_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/sales'][0]
    receivable_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/receivable'][0]
    vat_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/coll_vat'][0]

    self.assertAlmostEquals(1, receivable_line.getPrice(), 3)
    self.assertAlmostEquals(-1, receivable_line.getQuantity(), 3)
    self.assertEquals('account_module/receivable', receivable_line.getSource())
    self.assertEquals('account_module/payable', receivable_line.getDestination())
    self.assertFalse(receivable_line.hasGroupingReference())

    self.assertAlmostEquals(1, sale_line.getPrice(), 3)
    self.assertAlmostEquals(0.836, sale_line.getQuantity(), 3)
    self.assertEquals('account_module/sales', sale_line.getSource())
    self.assertEquals('account_module/purchase', sale_line.getDestination())

    self.assertAlmostEquals(1, vat_line.getPrice(), 3)
    self.assertAlmostEquals(0.164, vat_line.getQuantity(), 3)
    self.assertEquals('account_module/coll_vat', vat_line.getSource())
    self.assertEquals('account_module/refundable_vat', vat_line.getDestination())

    # XXX Check user interface display
    self.assertEquals(
      'Waiting for payment',
      sale_invoice.portal_skins.vifib_hosting.AccountingTransaction_getPaymentState())
    self.assertEquals('solved', sale_invoice.getCausalityState())

    # Check the payment transaction
    payment_list = self.portal.portal_catalog(
      portal_type="Payment Transaction",
      causality_uid=sale_invoice.getUid(),
      )
    self.assertEquals(1, len(payment_list))

    payment = payment_list[0]
    sequence.edit(payment_transaction_uid=payment.getUid())

    # Payment should have a causality link
    self.assertEquals(sale_invoice.getRelativeUrl(), payment.getCausality())

    # Check invoice creation
    self.assertEquals(
      None,
      payment.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      payment.getSourceSection())
    self.assertEquals(
      None,
      payment.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      payment.getDestinationSection())
    self.assertEquals(
      None,
      payment.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      payment.getResource())
    self.assertEquals(
      None,
      payment.getSpecialise())
    self.assertEquals(
      'planned',
      payment.getSimulationState())
    self.assertAlmostEquals(
      0, payment.getTotalPrice(), 3)
    self.assertEquals('solved', payment.getCausalityState())

    transaction_line_list = payment.contentValues(
        portal_type="Accounting Transaction Line")
    self.assertEquals(2, len(transaction_line_list))

    sale_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/bank'][0]
    receivable_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/receivable'][0]

    self.assertEquals(True, receivable_line.hasPrice())
    self.assertAlmostEquals(1, receivable_line.getPrice(), 3)
    self.assertAlmostEquals(1, receivable_line.getQuantity(), 3)
    self.assertEquals('account_module/receivable', receivable_line.getSource())
    self.assertEquals('account_module/payable', receivable_line.getDestination())
    self.assertFalse(receivable_line.hasGroupingReference())

    self.assertEquals(True, sale_line.hasPrice())
    self.assertAlmostEquals(1, sale_line.getPrice(), 3)
    self.assertAlmostEquals(-1, sale_line.getQuantity(), 3)
    self.assertEquals('account_module/bank', sale_line.getSource())
    self.assertEquals('account_module/bank', sale_line.getDestination())

  def stepCheckPaidInvoice(self, sequence, **kw):
    """
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])

    # Check that 2 sale invoice has been generated for the user
    transaction_list = self.portal.portal_catalog(
      portal_type="Sale Invoice Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      sort_on=(('uid', 'DESC')),
      )
    self.assertEquals(2, len(transaction_list))

    sale_invoice = transaction_list[0].getObject()

    # Check invoice creation
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSourceSection())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestinationSection())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getResource())
#     self.assertEquals(
#       'sale_trade_condition_module/vifib_trade_condition',
#       sale_invoice.getSpecialise())
    self.assertEquals(
      'stopped',
      sale_invoice.getSimulationState())
    self.assertAlmostEquals(
      1, sale_invoice.getTotalPrice(), 3)

    # 5 invoice lines are expected
    invoice_line_list = sale_invoice.contentValues(
        portal_type="Invoice Line")
    self.assertEquals(5, len(invoice_line_list))

    service_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_setup'][0]
    subscription_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_subscription'][0]
    hosting_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_hosting'][0]
    destroy_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_cleanup'][0]
    tax_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_tax'][0]

    self.assertEquals(True, service_line.hasPrice())
    self.assertAlmostEquals(0, service_line.getPrice(), 3)
    self.assertEquals(1, service_line.getQuantity())

    self.assertEquals(True, subscription_line.hasPrice())
    self.assertAlmostEquals(0.836, subscription_line.getPrice(), 3)
    self.assertEquals(1, subscription_line.getQuantity())

    self.assertEquals(True, hosting_line.hasPrice())
    self.assertAlmostEquals(0, hosting_line.getPrice(), 3)
    self.assertEquals(1, hosting_line.getQuantity())

    self.assertEquals(True, destroy_line.hasPrice())
    self.assertAlmostEquals(0, destroy_line.getPrice(), 3)
    self.assertEquals(1, destroy_line.getQuantity())

    self.assertEquals(True, tax_line.hasPrice())
    self.assertAlmostEquals(0.196, tax_line.getPrice(), 3)
    self.assertAlmostEquals(0.836, tax_line.getQuantity(), 3)

    transaction_line_list = sale_invoice.contentValues(
        portal_type="Sale Invoice Transaction Line")
    self.assertEquals(3, len(transaction_line_list))

    sale_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/sales'][0]
    receivable_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/receivable'][0]
    vat_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/coll_vat'][0]

    self.assertAlmostEquals(1, receivable_line.getPrice(), 3)
    self.assertAlmostEquals(-1, receivable_line.getQuantity(), 3)
    self.assertEquals('account_module/receivable', receivable_line.getSource())
    self.assertEquals('account_module/payable', receivable_line.getDestination())
    self.assertTrue(receivable_line.hasGroupingReference())
    invoice_grouping_reference = receivable_line.getGroupingReference()

    self.assertAlmostEquals(1, sale_line.getPrice(), 3)
    self.assertAlmostEquals(0.836, sale_line.getQuantity(), 3)
    self.assertEquals('account_module/sales', sale_line.getSource())
    self.assertEquals('account_module/purchase', sale_line.getDestination())

    self.assertAlmostEquals(1, vat_line.getPrice(), 3)
    self.assertAlmostEquals(0.164, vat_line.getQuantity(), 3)
    self.assertEquals('account_module/coll_vat', vat_line.getSource())
    self.assertEquals('account_module/refundable_vat', vat_line.getDestination())

    # XXX Check user interface display
    self.assertEquals(
      'Paid',
      sale_invoice.portal_skins.vifib_hosting.AccountingTransaction_getPaymentState())
    self.assertEquals('solved', sale_invoice.getCausalityState())

    # Check the payment transaction
    payment_list = self.portal.portal_catalog(
      portal_type="Payment Transaction",
      causality_uid=sale_invoice.getUid(),
      )
    self.assertEquals(1, len(payment_list))

    payment = payment_list[0]
    sequence.edit(payment_transaction_uid=payment.getUid())

    # Payment should have a causality link
    self.assertEquals(sale_invoice.getRelativeUrl(), payment.getCausality())

    # Check invoice creation
    self.assertEquals(
      None,
      payment.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      payment.getSourceSection())
    self.assertEquals(
      None,
      payment.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      payment.getDestinationSection())
    self.assertEquals(
      None,
      payment.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      payment.getResource())
    self.assertEquals(
      None,
      payment.getSpecialise())
    self.assertEquals(
      'stopped',
      payment.getSimulationState())
    self.assertAlmostEquals(
      0, payment.getTotalPrice(), 3)
    self.assertEquals('solved', payment.getCausalityState())

    transaction_line_list = payment.contentValues(
        portal_type="Accounting Transaction Line")
    self.assertEquals(2, len(transaction_line_list))

    sale_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/bank'][0]
    receivable_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/receivable'][0]

    self.assertEquals(True, receivable_line.hasPrice())
    self.assertAlmostEquals(1, receivable_line.getPrice(), 3)
    self.assertAlmostEquals(1, receivable_line.getQuantity(), 3)
    self.assertEquals('account_module/receivable', receivable_line.getSource())
    self.assertEquals('account_module/payable', receivable_line.getDestination())
    self.assertTrue(receivable_line.hasGroupingReference())
    self.assertEquals(invoice_grouping_reference,
                      receivable_line.getGroupingReference())

    self.assertEquals(True, sale_line.hasPrice())
    self.assertAlmostEquals(1, sale_line.getPrice(), 3)
    self.assertAlmostEquals(-1, sale_line.getQuantity(), 3)
    self.assertEquals('account_module/bank', sale_line.getSource())
    self.assertEquals('account_module/bank', sale_line.getDestination())

  def test_default_use_case(self):
    """Test full default use case.

    User subscribes and pays 1 euro for registration.

    He orders a software release with a 1 euro subscription price (vat
    included) (everything else free).

    Stopping his payment should generate the grouping reference on the related
    invoice.
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_installed_software_release_sequence_string + \
      self.register_new_user_sequence_string + '\
        LoginWebUser \
        CheckRegistrationAccounting \
        Logout \
        LoginDefaultUser \
        PayRegistrationPayment \
        Tic \
        Logout \
        LoginWebUser \
        CheckPaidRegistrationAccounting \
      ' + \
      self.create_new_user_instance_sequence_string + '\
        SlapLoginCurrentComputer \
        SoftwareInstanceBuilding \
        SoftwareInstanceAvailable \
        Tic \
        SlapLogout \
        LoginERP5TypeTestCase \
        TriggerBuild \
        Tic \
        TriggerStopConfirmedInvoiceAlarm \
        Tic \
        TriggerBuild \
        Tic \
        Logout \
        LoginWebUser \
        CheckSetupOngoingInvoice \
        RequestSoftwareInstanceStart \
        Tic \
        Logout \
        SlapLoginCurrentComputer \
        SoftwareInstanceStarted \
        Tic \
        Logout \
        LoginWebUser \
        RequestSoftwareInstanceStop \
        Tic \
        Logout \
        SlapLoginCurrentComputer \
        SoftwareInstanceStopped \
        Tic \
        Logout \
        LoginERP5TypeTestCase \
        TriggerBuild \
        Tic \
        TriggerStopConfirmedInvoiceAlarm \
        Tic \
        TriggerBuild \
        Tic \
        Logout \
        LoginWebUser \
        CheckHostingOngoingInvoice \
        \
        RequestSoftwareInstanceDestroy \
        Tic \
        Logout \
        SlapLoginCurrentComputer \
        SoftwareInstanceDestroyed \
        Tic \
        SlapLogout \
        LoginWebUser \
        CheckDestroyOngoingInvoice \
        SlapLogout \
        \
        LoginERP5TypeTestCase \
        ConfirmOngoingInvoice \
        Tic \
        Tic \
        SlapLogout \
        Tic \
        LoginWebUser \
        CheckWaitingInvoice \
        Tic \
        PayRegistrationPayment \
        Tic \
        CheckPaidInvoice \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckComplexInvoice(self, sequence, **kw):
    """
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])

    # Check that 2 sale invoice has been generated for the user
    transaction_list = self.portal.portal_catalog(
      portal_type="Sale Invoice Transaction",
      destination_section_relative_url=person.getRelativeUrl(),
      sort_on=(('uid', 'DESC')),
      )
    self.assertEquals(2, len(transaction_list))

    sale_invoice = transaction_list[0].getObject()

    # Check invoice creation
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      sale_invoice.getSourceSection())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      sale_invoice.getDestinationSection())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      sale_invoice.getResource())
#     self.assertEquals(
#       'sale_trade_condition_module/vifib_trade_condition',
#       sale_invoice.getSpecialise())
    self.assertEquals(
      'stopped',
      sale_invoice.getSimulationState())
    self.assertAlmostEquals(
      2, sale_invoice.getTotalPrice(), 3)

    # 5 invoice lines are expected
    invoice_line_list = sale_invoice.contentValues(
        portal_type="Invoice Line")
    self.assertEquals(5, len(invoice_line_list))

    service_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_setup'][0]
    subscription_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_subscription'][0]
    hosting_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_hosting'][0]
    destroy_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_instance_cleanup'][0]
    tax_line = [x for x in invoice_line_list \
        if x.getResource() == 'service_module/vifib_tax'][0]

    self.assertEquals(True, service_line.hasPrice())
    self.assertAlmostEquals(0, service_line.getPrice(), 3)
    self.assertEquals(2, service_line.getQuantity())

    self.assertEquals(True, subscription_line.hasPrice())
    self.assertAlmostEquals(0.836, subscription_line.getPrice(), 3)
    self.assertEquals(2, subscription_line.getQuantity())

    self.assertEquals(True, hosting_line.hasPrice())
    self.assertAlmostEquals(0, hosting_line.getPrice(), 3)
    self.assertEquals(3, hosting_line.getQuantity())

    self.assertEquals(True, destroy_line.hasPrice())
    self.assertAlmostEquals(0, destroy_line.getPrice(), 3)
    self.assertEquals(2, destroy_line.getQuantity())

    self.assertEquals(True, tax_line.hasPrice())
    self.assertAlmostEquals(0.196, tax_line.getPrice(), 3)
    self.assertAlmostEquals(1.672, tax_line.getQuantity(), 3)

    # 3 transaction line
    transaction_line_list = sale_invoice.contentValues(
        portal_type="Sale Invoice Transaction Line")
    self.assertEquals(3, len(transaction_line_list))

    sale_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/sales'][0]
    receivable_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/receivable'][0]
    vat_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/coll_vat'][0]

    self.assertAlmostEquals(1, receivable_line.getPrice(), 3)
    self.assertAlmostEquals(-2, receivable_line.getQuantity(), 3)
    self.assertEquals('account_module/receivable', receivable_line.getSource())
    self.assertEquals('account_module/payable', receivable_line.getDestination())
    self.assertTrue(receivable_line.hasGroupingReference())
    invoice_grouping_reference = receivable_line.getGroupingReference()

    self.assertAlmostEquals(1, sale_line.getPrice(), 3)
    self.assertAlmostEquals(1.672, sale_line.getQuantity(), 3)
    self.assertEquals('account_module/sales', sale_line.getSource())
    self.assertEquals('account_module/purchase', sale_line.getDestination())

    self.assertAlmostEquals(1, vat_line.getPrice(), 3)
    self.assertAlmostEquals(0.328, vat_line.getQuantity(), 3)
    self.assertEquals('account_module/coll_vat', vat_line.getSource())
    self.assertEquals('account_module/refundable_vat', vat_line.getDestination())

    # XXX Check user interface display
    self.assertEquals(
      'Paid',
      sale_invoice.portal_skins.vifib_hosting.AccountingTransaction_getPaymentState())
    self.assertEquals('solved', sale_invoice.getCausalityState())

    # Check the payment transaction
    payment_list = self.portal.portal_catalog(
      portal_type="Payment Transaction",
      causality_uid=sale_invoice.getUid(),
      )
    self.assertEquals(1, len(payment_list))

    payment = payment_list[0]
    sequence.edit(payment_transaction_uid=payment.getUid())

    # Payment should have a causality link
    self.assertEquals(sale_invoice.getRelativeUrl(), payment.getCausality())

    # Check invoice creation
    self.assertEquals(
      None,
      payment.getSource())
    self.assertEquals(
      'organisation_module/vifib_internet',
      payment.getSourceSection())
    self.assertEquals(
      None,
      payment.getDestination())
    self.assertEquals(
      person.getRelativeUrl(),
      payment.getDestinationSection())
    self.assertEquals(
      None,
      payment.getPriceCurrency())
    self.assertEquals(
      'currency_module/EUR',
      payment.getResource())
    self.assertEquals(
      None,
      payment.getSpecialise())
    self.assertEquals(
      'stopped',
      payment.getSimulationState())
    self.assertAlmostEquals(
      0, payment.getTotalPrice(), 3)
    self.assertEquals('solved', payment.getCausalityState())

    transaction_line_list = payment.contentValues(
        portal_type="Accounting Transaction Line")
    self.assertEquals(2, len(transaction_line_list))

    sale_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/bank'][0]
    receivable_line = [x for x in transaction_line_list \
        if x.getSource() == 'account_module/receivable'][0]

    self.assertEquals(True, receivable_line.hasPrice())
    self.assertAlmostEquals(1, receivable_line.getPrice(), 3)
    self.assertAlmostEquals(2, receivable_line.getQuantity(), 3)
    self.assertEquals('account_module/receivable', receivable_line.getSource())
    self.assertEquals('account_module/payable', receivable_line.getDestination())
    self.assertTrue(receivable_line.hasGroupingReference())
    self.assertEquals(invoice_grouping_reference,
                      receivable_line.getGroupingReference())

    self.assertEquals(True, sale_line.hasPrice())
    self.assertAlmostEquals(1, sale_line.getPrice(), 3)
    self.assertAlmostEquals(-2, sale_line.getQuantity(), 3)
    self.assertEquals('account_module/bank', sale_line.getSource())
    self.assertEquals('account_module/bank', sale_line.getDestination())

  def test_aggregated_use_case(self):
    """Test a more complex use case with many packing list agregated
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_installed_software_release_sequence_string + \
      self.register_new_user_sequence_string + '\
        LoginWebUser \
        CheckRegistrationAccounting \
        Logout \
        LoginDefaultUser \
        PayRegistrationPayment \
        Tic \
        Logout \
        LoginWebUser \
      ' + \
      self.create_new_user_instance_sequence_string + '\
        SlapLoginCurrentComputer \
        SoftwareInstanceBuilding \
        SoftwareInstanceAvailable \
        Tic \
        SlapLogout \
        \
        LoginWebUser \
        RequestSoftwareInstanceStart \
        Tic \
        Logout \
        SlapLoginCurrentComputer \
        SoftwareInstanceStarted \
        Tic \
        Logout \
        LoginWebUser \
        RequestSoftwareInstanceStop \
        Tic \
        Logout \
        SlapLoginCurrentComputer \
        SoftwareInstanceStopped \
        Tic \
        Logout \
        \
        LoginWebUser \
        RequestSoftwareInstanceStart \
        Tic \
        Logout \
        SlapLoginCurrentComputer \
        SoftwareInstanceStarted \
        Tic \
        Logout \
        LoginWebUser \
        RequestSoftwareInstanceStop \
        Tic \
        Logout \
        SlapLoginCurrentComputer \
        SoftwareInstanceStopped \
        Tic \
        Logout \
        \
        LoginWebUser \
        RequestSoftwareInstanceDestroy \
        Tic \
        Logout \
        SlapLoginCurrentComputer \
        SoftwareInstanceDestroyed \
        Tic \
        SlapLogout \
        ' + \
      self.create_new_user_instance_sequence_string + '\
        SlapLoginCurrentComputer \
        SoftwareInstanceBuilding \
        SoftwareInstanceAvailable \
        Tic \
        SlapLogout \
        \
        LoginWebUser \
        RequestSoftwareInstanceStart \
        Tic \
        Logout \
        SlapLoginCurrentComputer \
        SoftwareInstanceStarted \
        Tic \
        Logout \
        LoginWebUser \
        RequestSoftwareInstanceStop \
        Tic \
        Logout \
        SlapLoginCurrentComputer \
        SoftwareInstanceStopped \
        Tic \
        Logout \
        \
        LoginWebUser \
        RequestSoftwareInstanceDestroy \
        Tic \
        Logout \
        SlapLoginCurrentComputer \
        SoftwareInstanceDestroyed \
        Tic \
        SlapLogout \
        \
        \
        LoginERP5TypeTestCase \
        ConfirmOngoingInvoice \
        Tic \
        Tic \
        SlapLogout \
        Tic \
        LoginWebUser \
        PayRegistrationPayment \
        Tic \
        CheckComplexInvoice \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibDefaultUseCase))
  return suite
