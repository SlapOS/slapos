# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2013 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin, withAbort
from zExceptions import Unauthorized
from functools import wraps
from Products.ERP5Type.tests.utils import createZODBPythonScript

def simulate(script_id, params_string, code_string):
  def upperWrap(f):
    @wraps(f)
    def decorated(self, *args, **kw):
      if script_id in self.portal.portal_skins.custom.objectIds():
        raise ValueError('Precondition failed: %s exists in custom' % script_id)
      createZODBPythonScript(self.portal.portal_skins.custom,
                          script_id, params_string, code_string)
      try:
        result = f(self, *args, **kw)
      finally:
        if script_id in self.portal.portal_skins.custom.objectIds():
          self.portal.portal_skins.custom.manage_delObjects(script_id)
        transaction.commit()
      return result
    return decorated
  return upperWrap

class TestSlapOSComputer_reportComputerConsumption(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createComputer(self):
    new_id = self.generateNewId()
    return self.portal.computer_module.newContent(
      portal_type='Computer',
      title="Computer %s" % new_id,
      reference="TESTCOMP-%s" % new_id,
      )

  def test_reportComputerConsumption_REQUEST_disallowed(self):
    computer = self.createComputer()
    self.assertRaises(
      Unauthorized,
      computer.Computer_reportComputerConsumption,
      "foo", "bar",
      REQUEST={})

  def test_reportComputerConsumption_expected_xml(self):
    new_id = self.generateNewId()
    consumption_xml = """<?xml version='1.0' encoding='utf-8'?>
<journal>
<transaction type="Sale Packing List">
<title>Resource consumptions</title>
<start_date></start_date>
<stop_date></stop_date>
<reference>foo</reference>
<currency></currency>
<payment_mode></payment_mode>
<category></category>
<arrow type="Administration">
<source></source>
<destination></destination>
</arrow>
<movement>
<resource>CPU Consumption</resource>
<title>Title Sale Packing List Line 1</title>
<reference>slappart0</reference>
<quantity>42.42</quantity>
<price>0.00</price>
<VAT>None</VAT>
<category>None</category>
</movement>
</transaction>
</journal>"""

    computer = self.createComputer()
    document_relative_url = computer.Computer_reportComputerConsumption(
                                                 new_id, consumption_xml)
    document = self.portal.restrictedTraverse(document_relative_url)
    self.assertEquals(document.getPortalType(),
                      "Computer Consumption TioXML File")
    self.assertEquals(document.getSourceReference(), new_id)
    self.assertEquals(document.getTitle(),
                      "%s consumption (%s)" % (computer.getReference(), new_id))
    self.assertNotEquals(document.getReference(), "")
    self.assertEquals(document.getVersion(), "1")
    self.assertEquals(document.getData(), consumption_xml)
    self.assertEquals(document.getClassification(), "personal")
    self.assertEquals(document.getPublicationSection(), "other")
    self.assertEquals(document.getValidationState(), "submitted")
    self.assertEquals(document.getContributor(), computer.getRelativeUrl())

  def test_reportComputerConsumption_reported_twice(self):
    new_id = self.generateNewId()
    consumption_xml = """<?xml version='1.0' encoding='utf-8'?>
<journal>
<transaction type="Sale Packing List">
<title>Resource consumptions</title>
<start_date></start_date>
<stop_date></stop_date>
<reference>foo</reference>
<currency></currency>
<payment_mode></payment_mode>
<category></category>
<arrow type="Administration">
<source></source>
<destination></destination>
</arrow>
<movement>
<resource>CPU Consumption</resource>
<title>Title Sale Packing List Line 1</title>
<reference>slappart0</reference>
<quantity>42.42</quantity>
<price>0.00</price>
<VAT>None</VAT>
<category>None</category>
</movement>
</transaction>
</journal>"""

    computer = self.createComputer()
    document1_relative_url = computer.Computer_reportComputerConsumption(
                                                 new_id, consumption_xml)
    document1 = self.portal.restrictedTraverse(document1_relative_url)

    document2_relative_url = computer.Computer_reportComputerConsumption(
                                                 new_id, consumption_xml)
    document2 = self.portal.restrictedTraverse(document2_relative_url)

    self.assertEquals(document2.getPortalType(),
                      "Computer Consumption TioXML File")
    self.assertEquals(document2.getSourceReference(),
                      document1.getSourceReference())
    self.assertEquals(document2.getTitle(), document1.getTitle())
    self.assertEquals(document2.getReference(), document1.getReference())
    self.assertEquals(document1.getVersion(), "1")
    self.assertEquals(document2.getVersion(), "2")
    self.assertEquals(document2.getData(), consumption_xml)
    self.assertEquals(document2.getClassification(), "personal")
    self.assertEquals(document2.getPublicationSection(), "other")
    self.assertEquals(document1.getValidationState(), "submitted")
    self.assertEquals(document2.getValidationState(), "submitted")
    self.assertEquals(document2.getContributor(), computer.getRelativeUrl())

class TestSlapOSComputerConsumptionTioXMLFile_parseXml(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createTioXMLFile(self):
    document = self.portal.consumption_document_module.newContent(
      title=self.generateNewId(),
      reference="TESTTIOCONS-%s" % self.generateNewId(),
    )
    document.submit()
    return document

  def test_parseXml_REQUEST_disallowed(self):
    document = self.createTioXMLFile()
    self.assertRaises(
      Unauthorized,
      document.ComputerConsumptionTioXMLFile_parseXml,
      REQUEST={})

  def test_parseXml_no_data(self):
    document = self.createTioXMLFile()
    result = document.ComputerConsumptionTioXMLFile_parseXml()
    self.assertEqual(result, None)

  def test_parseXml_no_xml(self):
    document = self.createTioXMLFile()
    document.edit(data="<?xml version='1.0' encoding='utf-8'?><foo></foo>")
    result = document.ComputerConsumptionTioXMLFile_parseXml()
    self.assertEqual(result, None)

  def test_parseXml_invalid_xml(self):
    document = self.createTioXMLFile()
    document.edit(data="<xml></foo>")
    result = document.ComputerConsumptionTioXMLFile_parseXml()
    self.assertEqual(result, None)

  def test_parseXml_valid_xml_one_movement(self):
    document = self.createTioXMLFile()
    consumption_xml = """<?xml version='1.0' encoding='utf-8'?>
<journal>
<transaction type="Sale Packing List">
<title>Resource consumptionsé</title>
<start_date>Sun, 06 Nov 1994 08:49:37 GMT</start_date>
<stop_date>Sun, 07 Nov 1994 08:49:37 GMT</stop_date>
<reference>fooé</reference>
<currency></currency>
<payment_mode></payment_mode>
<category></category>
<arrow type="Administration">
<source></source>
<destination></destination>
</arrow>
<movement>
<resource>CPU Consumptioné</resource>
<title>Title Sale Packing List Line 1</title>
<reference>slappart0é</reference>
<quantity>42.42</quantity>
<price>0.00</price>
<VAT>None</VAT>
<category>caté</category>
</movement>
</transaction>
</journal>"""
    document.edit(data=consumption_xml)
    result = document.ComputerConsumptionTioXMLFile_parseXml()
    self.assertEqual(result, {
      'title': 'Resource consumptionsé',
      'movement': [{
        'resource': 'CPU Consumptioné',
        'reference': 'slappart0é',
        'quantity': 42.42,
        'category': "caté",
        'title': "Title Sale Packing List Line 1",
      }],
    })

  def test_parseXml_valid_xml_two_movements(self):
    document = self.createTioXMLFile()
    consumption_xml = """<?xml version='1.0' encoding='utf-8'?>
<journal>
<transaction type="Sale Packing List">
<title>Resource consumptionsé</title>
<start_date>Sun, 06 Nov 1994 08:49:37 GMT</start_date>
<stop_date>Sun, 07 Nov 1994 08:49:37 GMT</stop_date>
<reference>fooé</reference>
<currency></currency>
<payment_mode></payment_mode>
<category></category>
<arrow type="Administration">
<source></source>
<destination></destination>
</arrow>
<movement>
<resource>CPU Consumptioné</resource>
<title>Title Sale Packing List Line 1</title>
<reference>slappart0é</reference>
<quantity>42.42</quantity>
<price>0.00</price>
<VAT>None</VAT>
<category>caté</category>
</movement>
<movement>
<resource>CPU Consumptioné</resource>
<title>Title Sale Packing List Line 1</title>
<reference>slappart0é</reference>
<quantity>42.42</quantity>
<price>0.00</price>
<VAT>None</VAT>
<category>caté</category>
</movement>
</transaction>
</journal>"""
    document.edit(data=consumption_xml)
    result = document.ComputerConsumptionTioXMLFile_parseXml()
    self.assertEqual(result, {
      'title': 'Resource consumptionsé',
      'movement': [{
        'resource': 'CPU Consumptioné',
        'reference': 'slappart0é',
        'quantity': 42.42,
        'category': "caté",
        'title': "Title Sale Packing List Line 1",
        },{
        'resource': 'CPU Consumptioné',
        'reference': 'slappart0é',
        'quantity': 42.42,
        'category': "caté",
        'title': "Title Sale Packing List Line 1",
      }],
    })

class TestSlapOSComputerConsumptionTioXMLFile_solveInvoicingGeneration(
                                                           testSlapOSMixin):

  def createTioXMLFile(self):
    document = self.portal.consumption_document_module.newContent(
      title=self.generateNewId(),
      reference="TESTTIOCONS-%s" % self.generateNewId(),
    )
    document.submit()
    return document

  def createAllocatedComputer(self):
    # Create person
    password = self.generateNewId()
    reference = 'test_%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
      title=reference,
      reference=reference, password=password)
    person.newContent(portal_type='Assignment', role='member').open()

    transaction.commit()
    person.recursiveImmediateReindexObject()
    self.person = person
    self.person_reference = person.getReference()

    new_id = self.generateNewId()

    # Prepare computer
    self.computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    self.computer.edit(
      title="Computer %s" % new_id,
      reference="TESTCOMP-%s" % new_id
    )

    self.computer.validate()

    self.tic()

    self._makeComplexComputer()
    self.tic()

    self.start_requested_software_instance.getSpecialiseValue().edit(
      destination_section_value=person
    )

    self.stop_requested_software_instance.getSpecialiseValue().edit(
      destination_section_value=person
    )
    
    return self.computer

  def test_solveInvoicingGeneration_REQUEST_disallowed(self):
    document = self.createTioXMLFile()
    self.assertRaises(
      Unauthorized,
      document.ComputerConsumptionTioXMLFile_solveInvoicingGeneration,
      REQUEST={})

  @simulate('ComputerConsumptionTioXMLFile_parseXml', 
            '*args, **kwargs',
            'return None')
  def test_solveInvoicingGeneration_no_data(self):
    document = self.createTioXMLFile()
    self.assertEqual(document.getValidationState(), "submitted")
    result = document.ComputerConsumptionTioXMLFile_solveInvoicingGeneration()
    self.assertEqual(document.getValidationState(), "draft")
    self.assertEqual("Not usable TioXML data",
        document.workflow_history['document_publication_workflow'][-1]['comment'])
    self.assertEqual(result, [])

  tio_dict = {
    'title': 'Resource consumptionsé',
    'movement': [{
      'title': 'fooà',
      'resource': 'service_module/slapos_netdrive_consumption',
      'reference': 'partition1',
      'quantity': 42.42,
      'category': "caté",
    }],
  }
  @simulate('ComputerConsumptionTioXMLFile_parseXml', 
            '*args, **kwargs',
            "return %s" % tio_dict)
  def test_solveInvoicingGeneration_valid_xml_one_movement(self):
    document = self.createTioXMLFile()
    computer = self.createAllocatedComputer()
    document.edit(
      contributor_value=computer,
    )
    self.tic()
    self.assertEqual(document.getValidationState(), "submitted")
    result = document.ComputerConsumptionTioXMLFile_solveInvoicingGeneration()
    self.assertEqual(document.getValidationState(), "shared")
    self.assertEqual("Created packing list: %s" % result,
        document.workflow_history['document_publication_workflow'][-1]['comment'])
    self.assertEqual(len(result), 1)
    delivery = self.portal.restrictedTraverse(result[0])

    self.assertEqual(delivery.getPortalType(), "Sale Packing List")
    self.assertEqual(delivery.getDestination(), self.person.getRelativeUrl())
    self.assertEqual(delivery.getDestinationDecision(),
                     self.person.getRelativeUrl())
    self.assertEqual(delivery.getStartDate(),
                     document.getCreationDate())
    self.assertEqual(delivery.getTitle(),
      "%s Consumption Usage" % \
        self.start_requested_software_instance.getReference())
    self.assertEqual(delivery.getSimulationState(), "delivered")
    self.assertEqual(delivery.getCausalityState(), "building")
    self.assertEqual(delivery.getSpecialise(),
      "sale_trade_condition_module/slapos_consumption_trade_condition")

    self.assertEqual(
      len(delivery.contentValues(portal_type="Sale Packing List Line")), 1)
    line = delivery.contentValues(portal_type="Sale Packing List Line")[0]
    
    self.assertEqual(line.getTitle(), "fooà")
    self.assertEqual(line.getQuantity(), 42.42)
    self.assertEqual(line.getAggregateList(), [
      self.computer.partition1.getRelativeUrl(),
      self.start_requested_software_instance.getRelativeUrl(),
      self.start_requested_software_instance.getSpecialise()
    ])
    self.assertEqual(line.getResource(),
                     "service_module/slapos_netdrive_consumption")
    self.assertEqual(line.getQuantityUnit(),
                     "unit/piece")

  tio_dict = {
    'title': 'Resource consumptionsé',
    'movement': [{
      'title': 'fooà',
      'resource': 'service_module/slapos_netdrive_consumption',
      'reference': 'partition1',
      'quantity': 42.42,
      'category': "caté",
      },{
      'title': 'foob',
      'resource': 'service_module/slapos_netdrive_consumption',
      'reference': 'partition1',
      'quantity': 24.24,
      'category': "caté",
    }],
  }
  @simulate('ComputerConsumptionTioXMLFile_parseXml', 
            '*args, **kwargs',
            "return %s" % tio_dict)
  def test_solveInvoicingGeneration_valid_xml_two_movement(self):
    document = self.createTioXMLFile()
    computer = self.createAllocatedComputer()
    document.edit(
      contributor_value=computer,
    )
    self.tic()
    self.assertEqual(document.getValidationState(), "submitted")
    result = document.ComputerConsumptionTioXMLFile_solveInvoicingGeneration()
    self.assertEqual(document.getValidationState(), "shared")
    self.assertEqual("Created packing list: %s" % result,
        document.workflow_history['document_publication_workflow'][-1]['comment'])
    self.assertEqual(len(result), 1)
    delivery = self.portal.restrictedTraverse(result[0])

    self.assertEqual(delivery.getPortalType(), "Sale Packing List")
    self.assertEqual(delivery.getDestination(), self.person.getRelativeUrl())
    self.assertEqual(delivery.getDestinationDecision(),
                     self.person.getRelativeUrl())
    self.assertEqual(delivery.getStartDate(),
                     document.getCreationDate())
    self.assertEqual(delivery.getTitle(),
      "%s Consumption Usage" % \
        self.start_requested_software_instance.getReference())
    self.assertEqual(delivery.getSimulationState(), "delivered")
    self.assertEqual(delivery.getCausalityState(), "building")
    self.assertEqual(delivery.getSpecialise(),
      "sale_trade_condition_module/slapos_consumption_trade_condition")

    self.assertEqual(
      len(delivery.contentValues(portal_type="Sale Packing List Line")), 2)

    line = delivery.contentValues(portal_type="Sale Packing List Line")[0]
    self.assertEqual(line.getTitle(), "fooà")
    self.assertEqual(line.getQuantity(), 42.42)
    self.assertEqual(line.getAggregateList(), [
      self.computer.partition1.getRelativeUrl(),
      self.start_requested_software_instance.getRelativeUrl(),
      self.start_requested_software_instance.getSpecialise()
    ])
    self.assertEqual(line.getResource(),
                     "service_module/slapos_netdrive_consumption")
    self.assertEqual(line.getQuantityUnit(),
                     "unit/piece")

    line = delivery.contentValues(portal_type="Sale Packing List Line")[1]
    self.assertEqual(line.getTitle(), "foob")
    self.assertEqual(line.getQuantity(), 24.24)
    self.assertEqual(line.getAggregateList(), [
      self.computer.partition1.getRelativeUrl(),
      self.start_requested_software_instance.getRelativeUrl(),
      self.start_requested_software_instance.getSpecialise()
    ])
    self.assertEqual(line.getResource(),
                     "service_module/slapos_netdrive_consumption")
    self.assertEqual(line.getQuantityUnit(),
                     "unit/piece")

  tio_dict = {
    'title': 'Resource consumptionsé',
    'movement': [{
      'title': 'fooà',
      'resource': 'service_module/slapos_netdrive_consumption',
      'reference': 'partition1',
      'quantity': 42.42,
      'category': "caté",
      },{
      'title': 'foob',
      'resource': 'service_module/slapos_netdrive_consumption',
      'reference': 'partition2',
      'quantity': 24.24,
      'category': "caté",
    }],
  }
  @simulate('ComputerConsumptionTioXMLFile_parseXml', 
            '*args, **kwargs',
            "return %s" % tio_dict)
  def test_solveInvoicingGeneration_valid_xml_two_partitions(self):
    document = self.createTioXMLFile()
    computer = self.createAllocatedComputer()
    document.edit(
      contributor_value=computer,
    )
    self.tic()
    self.assertEqual(document.getValidationState(), "submitted")
    result = document.ComputerConsumptionTioXMLFile_solveInvoicingGeneration()
    self.assertEqual(document.getValidationState(), "shared")
    self.assertEqual("Created packing list: %s" % result,
        document.workflow_history['document_publication_workflow'][-1]['comment'])
    self.assertEqual(len(result), 2)

    # Delivery 1
    delivery = self.portal.restrictedTraverse(result[0])

    self.assertEqual(delivery.getPortalType(), "Sale Packing List")
    self.assertEqual(delivery.getDestination(), self.person.getRelativeUrl())
    self.assertEqual(delivery.getDestinationDecision(),
                     self.person.getRelativeUrl())
    self.assertEqual(delivery.getStartDate(),
                     document.getCreationDate())
    self.assertEqual(delivery.getTitle(),
      "%s Consumption Usage" % \
        self.start_requested_software_instance.getReference())
    self.assertEqual(delivery.getSimulationState(), "delivered")
    self.assertEqual(delivery.getCausalityState(), "building")
    self.assertEqual(delivery.getSpecialise(),
      "sale_trade_condition_module/slapos_consumption_trade_condition")

    self.assertEqual(
      len(delivery.contentValues(portal_type="Sale Packing List Line")), 1)

    line = delivery.contentValues(portal_type="Sale Packing List Line")[0]
    self.assertEqual(line.getTitle(), "fooà")
    self.assertEqual(line.getQuantity(), 42.42)
    self.assertEqual(line.getAggregateList(), [
      self.computer.partition1.getRelativeUrl(),
      self.start_requested_software_instance.getRelativeUrl(),
      self.start_requested_software_instance.getSpecialise()
    ])
    self.assertEqual(line.getResource(),
                     "service_module/slapos_netdrive_consumption")
    self.assertEqual(line.getQuantityUnit(),
                     "unit/piece")

    # Delivery 2
    delivery = self.portal.restrictedTraverse(result[1])

    self.assertEqual(delivery.getPortalType(), "Sale Packing List")
    self.assertEqual(delivery.getDestination(), self.person.getRelativeUrl())
    self.assertEqual(delivery.getDestinationDecision(),
                     self.person.getRelativeUrl())
    self.assertEqual(delivery.getStartDate(),
                     document.getCreationDate())
    self.assertEqual(delivery.getTitle(),
      "%s Consumption Usage" % \
        self.stop_requested_software_instance.getReference())
    self.assertEqual(delivery.getSimulationState(), "delivered")
    self.assertEqual(delivery.getCausalityState(), "building")
    self.assertEqual(delivery.getSpecialise(),
      "sale_trade_condition_module/slapos_consumption_trade_condition")

    self.assertEqual(
      len(delivery.contentValues(portal_type="Sale Packing List Line")), 1)

    line = delivery.contentValues(portal_type="Sale Packing List Line")[0]
    self.assertEqual(line.getTitle(), "foob")
    self.assertEqual(line.getQuantity(), 24.24)
    self.assertEqual(line.getAggregateList(), [
      self.computer.partition2.getRelativeUrl(),
      self.stop_requested_software_instance.getRelativeUrl(),
      self.stop_requested_software_instance.getSpecialise()
    ])
    self.assertEqual(line.getResource(),
                     "service_module/slapos_netdrive_consumption")
    self.assertEqual(line.getQuantityUnit(),
                     "unit/piece")
