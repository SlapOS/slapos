from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
import transaction
import httplib
import urlparse
from ZODB.POSException import ConflictError

class TestVifibSlaposRestAPIV1(ERP5TypeTestCase):
  def getWorkflowTransitionAmount(self, document, transition_id):
    amount = 0
    workflow_id_list = [workflow_id for workflow_id, workflow_state in \
      document.getWorkflowStateItemList()]
    for wf_id in workflow_id_list:
      list_history_item = None
      try:
        list_history_item = self.portal.portal_workflow.getInfoFor(
          ob=document, name='history', wf_id=wf_id)
      except ConflictError:
        raise
      except Exception:
        pass
      if list_history_item in (None, ()):
        continue
      for wf_dict in list_history_item:
        if wf_dict.get('action', '') == transition_id:
          amount += 1
    return amount

  def generateNewId(self):
    return str(self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_rest_api_v1_test')))

  def reindexAndUpdateLocalRoles(self):
    # reindex and update roles for all, and reindex again to update catalog
    transaction.commit()
    for o in self.document_list:
      o.recursiveImmediateReindexObject()
      transaction.commit()
    for o in self.document_list:
      o.updateLocalRolesOnSecurityGroups()
      transaction.commit()
    for o in self.document_list:
      o.recursiveImmediateReindexObject()
      transaction.commit()

  def afterSetUp(self):
    self.customer = self.cloneByPath('person_module/template_member')
    self.customer_reference = 'P' + self.test_random_id
    self.customer.edit(
      reference=self.customer_reference,
      default_email_url_string=self.customer_reference+'@example.com')
    self.customer.validate()
    for assignment in self.customer.contentValues(portal_type='Assignment'):
      assignment.open()

    self.test_random_id = self.generateNewId()
    self.document_list = []
    self.portal = self.getPortalObject()
    self.api_url = self.portal.portal_vifib_rest_api_v1.absolute_url()
    self.api_scheme, self.api_netloc, self.api_path, self.api_query, \
      self.api_fragment = urlparse.urlsplit(self.api_url)

    self.reindexAndUpdateLocalRoles()

  def cloneByPath(self, path):
    o = self.portal.restrictedTraverse(path).Base_createCloneDocument(
      batch_mode=1)
    self.document_list.append(o)
    return o

  def createStartedInstance(self):
    self.computer = self.cloneByPath(
      'computer_module/test_vifib_slapos_rest_api_v1_computer')
    self.computer.edit(
      reference='C' + self.test_random_id,
      source_administration=self.customer.getRelativeUrl()
    )
    self.computer.validate()
    for p in self.computer.contentValues(portal_type='Computer Partition'):
      self.computer_partition = p
      p.validate()
      p.markFree()

    self.supply = self.cloneByPath(
      'sale_trade_condition_module/test_vifib_slapos_rest_api_v1_sale_trade_condition')
    self.supply.edit(
      destination_section=self.customer.getRelativeUrl(),
      source_section=self.customer.getRelativeUrl()
    )
    self.supply.validate()
    supply_line = self.supply.contentValues()[0]
    supply_line.edit(aggregate=self.computer.getRelativeUrl())

    self.internal_delivery = self.cloneByPath(
      'internal_packing_list_module/test_vifib_slapos_rest_api_v1_internal_packing_list')
    self.internal_delivery.edit(
        destination_section=self.customer.getRelativeUrl(),
        source_administration=self.customer.getRelativeUrl(),
        destination=self.customer.getRelativeUrl(),
    )
    internal_line = self.internal_delivery.contentValues()[0]
    internal_line.edit(aggregate=self.computer.getRelativeUrl())
    self.internal_delivery.confirm()
    self.internal_delivery.stop()
    self.internal_delivery.deliver()

    self.software_release = self.cloneByPath(
      'software_release_module/test_software_release')
    self.software_release.edit(url_string=self.test_random_id,
      reference=self.test_random_id)
    self.software_release.publish()

    self.instance_title = 'T' + self.test_random_id
    self.instance_reference = 'SI' + self.test_random_id
    self.hosting_subscription = self.cloneByPath(
      'hosting_subscription_module/test_vifib_slapos_rest_api_v1_hosting_subscription')
    self.hosting_subscription.setReference('HS' + self.test_random_id)
    self.hosting_subscription.setTitle(self.instance_title)
    self.hosting_subscription.validate()
    self.software_instance = self.cloneByPath(
      'software_instance_module/test_vifib_slapos_rest_api_v1_software_instance')
    self.software_instance.edit(
      reference=self.instance_reference,
      title=self.instance_title
    )
    self.software_instance.validate()
    self.software_instance.requestStartComputerPartition()
    self.hosting_subscription.setPredecessor(
      self.software_instance.getRelativeUrl())

    self.order = self.cloneByPath(
      'sale_order_module/test_vifib_slapos_rest_api_v1_sale_order')
    self.order.edit(
      destination_section=self.customer.getRelativeUrl(),
      destination_decision=self.customer.getRelativeUrl(),
      destination=self.customer.getRelativeUrl()
    )
    aggregate_list = [
        self.software_instance.getRelativeUrl(),
        self.hosting_subscription.getRelativeUrl(),
        self.software_release.getRelativeUrl(),
        self.computer_partition.getRelativeUrl()
      ]
    order_line = self.order.contentValues()[0]
    order_line.edit(aggregate_list=aggregate_list)
    self.order.order()
    self.order.confirm()

    self.packing_list = self.cloneByPath(
      'sale_packing_list_module/test_vifib_slapos_rest_api_v1_instance_setup_sale_packing_list')
    self.packing_list.edit(
      causality=self.order.getRelativeUrl(),
      destination=self.customer.getRelativeUrl(),
      destination_section=self.customer.getRelativeUrl(),
      destination_decision=self.customer.getRelativeUrl(),
    )
    packing_list_line = self.packing_list.contentValues()[0]
    packing_list_line.edit(aggregate_list=aggregate_list,
      causality=order_line.getRelativeUrl())
    self.packing_list.confirm()
    self.packing_list.start()
    self.packing_list.stop()

    self.open_order = self.cloneByPath(
      'open_sale_order_module/test_vifib_customer_open_sale_order')
    self.open_order.edit(
      reference='OO' + self.test_random_id,
      destination_section=self.customer.getRelativeUrl(),
      destination_decision=self.customer.getRelativeUrl(),
      destination=self.customer.getRelativeUrl()
    )
    self.open_order.deleteContent(list(self.open_order.objectIds()))
    self.open_order.newContent(portal_type='Open Sale Order Line',
        resource='service_module/vifib_instance_subscription',
        base_contribution=['base_amount/invoicing/discounted',
          'base_amount/invoicing/taxable'],
        use='trade/sale',
        quantity_unit='unit/piece',
        aggregate=self.hosting_subscription.getRelativeUrl()
    )
    self.open_order.order()
    self.open_order.validate()

    self.reindexAndUpdateLocalRoles()

  def test_instance_destruction_started(self):
    transition_id = 'request_software_instance'
    self.createStartedInstance()
    amount = self.getWorkflowTransitionAmount(self.customer,
      transition_id)
    connection = httplib.HTTPConnection(self.api_netloc)
    connection.request(method='DELETE',
      url='/'.join([self.api_path, 'instance', self.instance_reference]),
      body='', headers={'REMOTE_USER': self.customer_reference})
    response = connection.getresponse()
    self.assertEqual(response.status, httplib.ACCEPTED,
      '%s was expected, but got %s with response:\n%s' %
        (httplib.ACCEPTED, response.status, response.read()))
    self.assertEqual(amount+1, self.getWorkflowTransitionAmount(self.customer,
      transition_id), 'Transition %s was not called' % transition_id)
    raise NotImplementedError(
      'Check that passed reference was used in wf transition')
