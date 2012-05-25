# -*- coding: utf-8 -*-

from zLOG import LOG, INFO
from OFS.Traversable import NotFound
from lxml import etree
from DateTime import DateTime
from Products.ERP5Type.UnrestrictedMethod import UnrestrictedMethod
parser = etree.XMLParser(remove_blank_text=True)

class ReportParser:
  """
  This parser is used to extract all informations 
  from the XML report given by SlapTool
  """

  def __init__(self, xml):
    self.transaction_dict = {}
    tags_text_transaction = {}
    arrow_list = []
    movement_list = []
    tags_text_movement = {}
    tags_text_arrow = {}

    xmltree = self.convertToXml(xml)

    #We fill up a list of movement extracted from xml with (tag - text) pairs
    for transaction in xmltree.findall('transaction'):
      for children in transaction.getchildren():
        if children.tag == "movement":
          for toddler in children.getchildren():
            tags_text_movement[toddler.tag] = toddler.text
          movement_list.append(tags_text_movement)
          tags_text_movement = {}
        elif children.tag == "arrow":
          for toddler in children.getchildren():
            tags_text_arrow[toddler.tag] = toddler.text
          arrow_list.append(tags_text_arrow)
          tags_text_arrow = {}
        else:
          tags_text_transaction[children.tag] = children.text
      self.transaction_dict['element_dict'] = tags_text_transaction
      self.transaction_dict['arrow_list'] = arrow_list
      self.transaction_dict['movement_list'] = movement_list
      tags_text_transaction = {}
      arrow_list = []
      movement_list = []

  def convertToXml(self, xml):
    """
    Converts xml in a node if it is a string
    """
    if xml is None: return None
    if isinstance(xml, (str, unicode)):
      if isinstance(xml, unicode):
        xml = xml.encode('utf-8')
      #LOG('VifibCounduit', INFO, '%s' % xml, error=True)
      xml = etree.XML(xml, parser=parser)
    #if we have the xml from the node erp5 we just take the subnode
    if xml.xpath('local-name()') == 'erp5':
      xml = xml[0]
    return xml

  def getTransactionDict(self):
    return self.transaction_dict

  def getTransactionElementDict(self):
    return self.transaction_dict['element_dict']

  def getArrowList(self):
    return self.transaction_dict['arrow_list']

  def getMovementList(self):
    return self.transaction_dict['movement_list']

  def checkComplete(self):
    """
    Checks if a report is complete
    """
    #We check that the XML report sent by the node got a title
    if None in [self.transaction_dict['element_dict'].get('title')]:
        return False

    #We check that this title is not empty
    if None in [self.transaction_dict['element_dict']['title']]:
        return False

    for movement in self.transaction_dict['movement_list']:
      #First, we check that following tags exist in the XML report
      if None in [movement.get('title'), movement.get('reference'), 
                  movement.get('resource')]:
        return False

      #Then, if they exist, we check that they are not empty
      if None in [movement['title'], movement['reference'], 
                  movement['resource']]:
        return False

    return True

class VifibConduit:
  """Synchronizes tiosafe packing list and erp5"""  

  def __init__(self):
    pass

  @UnrestrictedMethod
  def _applyTradeCondition(self, delivery_line):
    delivery_line.SaleOrder_applySaleTradeCondition(batch_mode=1)

  def addNode(self, object=None, xml=None, computer_id=None):
    """
    Creates a Sale Packing List from a XML report sent by a node
    """

    xml = ReportParser(xml)

    #We retrieve the sale packing list module
    sale_packing_list_portal_type = 'Sale Packing List'
    portal = object.getPortalObject()
    sale_packing_list_module = \
      portal.getDefaultModule(sale_packing_list_portal_type)

    #We retrieve the computer
    computer_module = portal.getDefaultModule('Computer')
    computer = \
      computer_module.searchFolder(reference=computer_id)[0].getObject()

    if xml.checkComplete():
      #We create a SPL 
      usage_report_sale_packing_list_document = \
        sale_packing_list_module.newContent(
          portal_type = 'Sale Packing List',
          title = xml.getTransactionElementDict()['title'],
          start_date = DateTime())

      #We create SPLLs for each movements
      for movement in xml.getMovementList():
        usage_report_sale_packing_list_document_line = \
          usage_report_sale_packing_list_document.newContent(
            portal_type='Sale Packing List Line')

        service_list = portal.portal_catalog(
          portal_type='Service',
          title=movement['resource'])

        if len(service_list) == 1:
          service = service_list[0].getObject()
        else:
          LOG('VifibConduit', INFO, 
            'Error, nonexistent service : %s' % movement['resource'])
          raise NotFound, "Error, nonexistent service : %s" % movement['resource']

        #We retrieve the partition
        partition = \
          computer.searchFolder(reference=movement['reference'])[0].getObject()

        # We retrieve the latest SPL (Instance Setup) related to the partition
        instance = portal.portal_catalog.getResultValue(
            portal_type="Software Instance",
            default_aggregate_uid=partition.getUid(),
            )
        instance_setup_packing_list = \
          instance.getCausalityValue()
        instance_setup_packing_list_line = \
          instance_setup_packing_list.contentValues(
              portal_type=["Sale Order Line", "Sale Packing List Line"],
            )[0]

        # We edit the SPLL
        usage_report_sale_packing_list_document_line.edit(
          resource = service.getRelativeUrl(),
          source = instance_setup_packing_list.getSource(),
          source_section = instance_setup_packing_list.getSourceSection(),
          destination = instance_setup_packing_list.getDestination(),
          destination_section = \
            instance_setup_packing_list.getDestinationSection(),
          specialise = instance_setup_packing_list.getSpecialise(),
          start_date = DateTime(),
          title = movement['title'],
          reference = movement['reference'],
          quantity = movement['quantity'],
          aggregate_list = instance_setup_packing_list_line.getAggregateList())

        self._applyTradeCondition(usage_report_sale_packing_list_document_line)

      usage_report_sale_packing_list_document.confirm()
      usage_report_sale_packing_list_document.start()
    else:
      LOG('VifibConduit', INFO, 
        'The XML report sent by the node is not complete')
      raise NotImplementedError("The XML report sent by the node is not complete")
