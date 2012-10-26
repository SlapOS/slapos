# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Nexedi SA and Contributors. All Rights Reserved.
#                    Nicolas Godbert <ngodbert@tiolive.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#############################################################################
import unittest

from lxml import etree
from slapos import slap
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import skip

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibUsageReport))
  return suite

class TestVifibUsageReportMixin(TestVifibSlapWebServiceMixin):

  prepare_confirmed_cleanup_resource_packing_list2 = """ \
    LoginTestVifibAdmin \
    RequestSoftwareInstallation \
    Tic \
    Logout \
    \
    SlapLoginCurrentComputer \
    ComputerSoftwareReleaseAvailable \
    Tic \
    SlapLogout \
    \
    LoginTestVifibCustomer \
    PersonRequestSoftwareInstance \
    Tic \
    Logout \
    \
    LoginDefaultUser \
    CallSlaposAllocateInstanceAlarm \
    Tic \
    SetSelectedComputerPartition \
    SelectCurrentlyUsedSalePackingListUid \
    Logout \
    \
    LoginDefaultUser \
    CheckComputerPartitionInstanceSetupSalePackingListDelivered \
    Logout \
    \
    SlapLoginCurrentComputer \
    SoftwareInstanceBuilding \
    Tic \
    SlapLogout \
    \
    LoginDefaultUser \
    CheckComputerPartitionInstanceSetupSalePackingListDelivered \
    Logout \
    \
    SlapLoginCurrentComputer \
    SoftwareInstanceAvailable \
    Tic \
    SlapLogout \
    \
    LoginDefaultUser \
    SetSelectedComputerPartition \
    CheckComputerPartitionInstanceSetupSalePackingListDelivered \
    CheckComputerPartitionInstanceHostingSalePackingListConfirmed \
    Logout \
    \
    LoginDefaultUser \
    CreateSalePackingList \
    Tic \
    CreateSalePackingListLine \
    Tic \
    SetSalePackingListLineCleanupResource \
    SetSalePackingListLineAggregate \
    ConfirmSalePackingList \
    StartBuildingSalePackingList \
    Tic \
    Logout \
    """

  prepare_configured_instance = """ \
    InitializeTime""" + \
    TestVifibSlapWebServiceMixin.prepare_destroy_requested_computer_partition

  prepare_reported_usage_call = """ \
    SlapLoginCurrentComputer \
    SlapReportUsageCall \
    Tic \
    SlapLogout"""

  def stepInitializeTime(self, sequence=None):
    sequence['start'] = self.portal.portal_catalog(
        sort_on=('uid', 'DESC'), limit=1)[0].uid
    sequence['first_call'] = False
    sequence['second_call'] = False

  def stepSlapReportUsageCall(self, sequence, **kw):
    """
    Checks that slap.reportUsage is successfully called.
    """
    # We check if this is the first time that a node send a usage report
    if sequence['first_call'] == True:
      sequence['second_call'] = True
    else:
      sequence['first_call'] = True

    # We retrieve an example of XML report sent by a node
    vifib_test_folder = self.getPortalObject().portal_skins.vifib_test
    usage_string = \
      vifib_test_folder.ERP5Site_getUsageReportTestSample(
        self.purchase_packing_list_quantity)
    sequence['initial_xml'] = usage_string

    #We send the XML report to the Master
    slap_object = slap.slap()
    slap_object.initializeConnection(self.server_url)
    slap_object._connection_helper.POST(
      '/useComputer',
      {'computer_id': sequence['computer_reference'],
      'use_string': usage_string})

  def stepBuildSalePackingList(self, sequence, **kw):
    """
    Builds Sale Packing List
    """
    portal = self.getPortalObject()

    # We retrieve vifib_sale_invoice_builder object
    portal_deliveries_object = \
      portal['portal_deliveries']

    vifib_sale_invoice_builder = \
      portal_deliveries_object['vifib_sale_invoice_builder']

    # Then, we build existing Sale Packing List
    vifib_sale_invoice_builder.build()

  def stepCheckCreatedSalePackingList(self, sequence, **kw):
    """
    Checks that it is present in the system.
    """
    #We retrieve the sale packing list module
    sale_packing_list_portal_type = 'Sale Packing List'
    portal = self.getPortalObject()
    sale_packing_list_module = \
      portal.getDefaultModule(sale_packing_list_portal_type)

    #We retrieve the Sale Packing List
    sale_packing_list_list = sale_packing_list_module.searchFolder(
      title='Resource consumptions',
      uid={
        'query' : sequence['start'],
        'range' : 'min'})

    self.assertEquals(len(sale_packing_list_list), 1)
    sale_packing_list = sale_packing_list_list[0]
    sequence['sale_packing_list'] = sale_packing_list

  def stepCheckCompleteSalePackingList(self, sequence, **kw):
    """
    Checks if the Sale Packing List is properly completed
    """
    #We retrieve the Sale Packing List Lines
    sale_packing_list = sequence['sale_packing_list']
    xml = sale_packing_list.PackingList_generateUsageReport()
    initial_xml = sequence['initial_xml']

    #We parse XML reports to check if they are the same
    parser = etree.XMLParser(remove_blank_text=True)
    initial_xml = etree.tostring(etree.XML(initial_xml, parser))
    xml = etree.tostring(etree.XML(xml, parser))

    sequence.edit(check_quantity='first')
    self.assertEquals(xml, initial_xml)

  def stepCheckSaleInvoiceExists(self, sequence, **kw):
    """
    Checks if a sale invoice exists.
    """
    #We retrieve the Accounting module
    accounting_portal_type = 'Accounting'
    portal = self.getPortalObject()
    accounting_module = \
      portal.getDefaultModule(accounting_portal_type)

    #We retrieve the Sale Invoice
    sale_invoice_list = accounting_module.searchFolder(
      title='Resource consumptions',
      uid={
        'query' : sequence['start'],
        'range' : 'min'})

    self.assertEquals(len(sale_invoice_list), self.sale_invoice_list_quantity)

    for sale_invoice in sale_invoice_list:
      self.assertEquals(sale_invoice.getTitle(), 'Resource consumptions')
      self.assertEquals(sale_invoice.getSimulationState(), 'planned')

    sequence.edit(sale_invoice_list=sale_invoice_list)

  def stepCheckSaleInvoiceQuantitySinglePartition(self, sequence, **kw):
    """
    Checks quantities in the new sale invoice
    """
    # We retrieve the sale invoice
    sale_invoice = sequence['sale_invoice_list']
    self.assertEquals(len(sale_invoice), self.sale_invoice_list_quantity)

    sale_invoice_line_list = sale_invoice[0].getObject().contentValues(
        portal_type='Invoice Line')

    self.assertEquals(
      len(sale_invoice_line_list), 
      self.sale_invoice_line_list_quantity)

    # Then, we check quantities in sale invoice's lines
    for sale_invoice_line in sale_invoice_line_list:
      self.assertEquals(
        sale_invoice_line.getQuantity(), 
        self.sale_invoice_line_quantity)

  def stepClearModules(self, sequence, **kw):
    """
    Clear the Sale Packing List and Accounting Modules before to begin the other test
    """
    portal = self.getPortalObject()
    module_portal_type_list = [
      'Accounting',
      'Sale Packing List']

    for module_portal_type in module_portal_type_list:
      module_object = \
        portal.getDefaultModule(module_portal_type)

      result_tuple = module_object.searchFolder(
        title='Resource consumptions',
        uid={
          'query' : sequence['start'],
          'range' : 'min'})

      for result in result_tuple:
        document = result.getObject()
        module_object.manage_delObjects(document.getId())

  def stepCheckSaleInvoiceQuantityTwoPartitions(self, sequence, **kw):
    """
    Checks quantities in new sale invoices
    """
    # If this is the second call, we check if quantities have been doubled
    if sequence['second_call'] == True:
      quantity1 = self.sale_invoice1_line_quantity * 2
      quantity2 = self.sale_invoice2_line_quantity * 2
    else:
      quantity1 = self.sale_invoice1_line_quantity
      quantity2 = self.sale_invoice2_line_quantity

    # We retrieve sale invoice list
    sale_invoice_list = sequence['sale_invoice_list']
    self.assertEquals(len(sale_invoice_list), self.sale_invoice_list_quantity)

    # We retrieve computer
    computer_id = sequence['computer_reference']
    computer = self.getPortal().computer_module.searchFolder(
      reference = computer_id)[0].getObject()

    for sale_invoice in sale_invoice_list:
      sale_invoice_line_list = \
        sale_invoice.contentValues(portal_type='Invoice Line')

      # We check the number of line in sale invoices
      self.assertEquals(
        len(sale_invoice_line_list),
        self.sale_invoice_line_list_quantity)

      # Then, we check quantities in these lines
      for sale_invoice_line in sale_invoice_line_list:

        partition_id  = \
          sale_invoice_line.getItemIdList()[0]

        partition_title = computer.searchFolder(
          id = partition_id)[0].getObject().getTitle()

        if partition_title == 'slappart0':
          self.assertEquals(sale_invoice_line.getQuantity(), quantity1)
        else:
          self.assertEquals(sale_invoice_line.getQuantity(), quantity2)

class TestVifibUsageReport(TestVifibUsageReportMixin):

  def getTitle(self):
    return "testVifibUsageReport"

  @skip('Ignored for now.')
  def test_usageReportWithSinglePartition(self):
    """
    Checks if useComputer method of SlapTool is properly called one time.
    """
    self.computer_partition_amount = 1
    self.purchase_packing_list_quantity = 1
    self.sale_invoice_list_quantity = 1
    self.sale_invoice_line_list_quantity = 2
    self.sale_invoice_line_quantity = 42.42

    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_configured_instance + \
      self.prepare_reported_usage_call + """ \
      LoginERP5TypeTestCase \
      BuildSalePackingList \
      Tic \
      CheckCreatedSalePackingList \
      CheckCompleteSalePackingList \
      CheckSaleInvoiceExists \
      CheckSaleInvoiceQuantitySinglePartition \
      ClearModules \
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Ignored for now.')
  def test_usageReportWithTwoPartitions(self):
    """
    Checks if useComputer method of SlapTool is properly called two times.
    """
    self.computer_partition_amount = 2
    self.purchase_packing_list_quantity = 2
    self.sale_invoice_list_quantity = 2
    self.sale_invoice_line_list_quantity = 2
    self.sale_invoice1_line_quantity = 42.42
    self.sale_invoice2_line_quantity = 46.46

    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_configured_instance + \
      self.prepare_confirmed_cleanup_resource_packing_list2 + \
      self.prepare_reported_usage_call + """ \
      LoginERP5TypeTestCase \
      BuildSalePackingList \
      Tic \
      CheckCreatedSalePackingList \
      CheckCompleteSalePackingList \
      CheckSaleInvoiceExists \
      CheckSaleInvoiceQuantityTwoPartitions \
      Logout """ + self.prepare_reported_usage_call + """ \
      LoginERP5TypeTestCase \
      BuildSalePackingList \
      Tic \
      CheckSaleInvoiceExists \
      CheckSaleInvoiceQuantityTwoPartitions \
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)
