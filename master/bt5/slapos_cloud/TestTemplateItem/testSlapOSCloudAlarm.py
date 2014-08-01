# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from Products.ERP5Type.tests.utils import createZODBPythonScript
from Products.ERP5Type.tests.backportUnittest import skip
import json
from zExceptions import Unauthorized
from DateTime import DateTime
from Products.ERP5Type.DateUtils import addToDate
from App.Common import rfc1123_date
from functools import wraps

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

class TestSlapOSCorePromiseSlapOSModuleIdGeneratorAlarm(testSlapOSMixin):

  def generateNewId(self):
    return self.portal.portal_ids.generateNewId(
        id_group=('slapos_core_test'))

  def test_Module_assertIdGenerator(self):
    module = self.portal.newContent(portal_type='Person Module',
        id=str(self.generateNewId()),
        id_generator='bad_id_generator')

    self.assertEqual('bad_id_generator', module.getIdGenerator())

    # check positive response
    self.assertTrue(module.Module_assertIdGenerator('bad_id_generator', False))
    self.assertEqual('bad_id_generator', module.getIdGenerator())
    self.assertTrue(module.Module_assertIdGenerator('bad_id_generator', True))
    self.assertEqual('bad_id_generator', module.getIdGenerator())

    # check negative response and that no-op run does not modify
    self.assertFalse(module.Module_assertIdGenerator('good_id_generator', False))
    self.assertEqual('bad_id_generator', module.getIdGenerator())

    # check negative response with fixit request
    self.assertFalse(module.Module_assertIdGenerator('good_id_generator', True))
    self.assertEqual('good_id_generator', module.getIdGenerator())
    self.assertTrue(module.Module_assertIdGenerator('good_id_generator', False))
    self.assertEqual('good_id_generator', module.getIdGenerator())

    transaction.abort()

  def _simulateModule_assertIdGenerator(self):
    script_name = 'Module_assertIdGenerator'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        'id_generator, fixit, active_process=None',
                        '# Script body\n'
"""from Products.CMFActivity.ActiveResult import ActiveResult
active_result = ActiveResult()
active_result.edit(
  summary='Module_assertIdGenerator simulation',
  severity=0,
  detail=context.getRelativeUrl())
active_process.postResult(active_result)
""" )
    transaction.commit()

  def _dropModule_assertIdGenerator(self):
    script_name = 'Module_assertIdGenerator'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm(self):
    alarm = self.portal.portal_alarms.promise_slapos_module_id_generator
    previous_active_process = self.portal.portal_catalog.getResultValue(
      portal_type='Active Process',
      causality_uid=alarm.getUid(),
      sort_on=(('creation_date', 'DESC'),)
    )
    self._simulateModule_assertIdGenerator()
    try:
      alarm.activeSense()
      self.tic()
    finally:
      self._dropModule_assertIdGenerator()
    active_process = self.portal.portal_catalog.getResultValue(
      portal_type='Active Process',
      causality_uid=alarm.getUid(),
      sort_on=(('creation_date', 'DESC'),)
    )

    self.assertNotEqual(previous_active_process.getPath(),
        active_process.getPath())

    visited_list = sorted([q.detail for q in active_process.getResultList() \
        if q.summary == 'Module_assertIdGenerator simulation'])

    expected_list = sorted([
      'access_token_module',
      'account_module',
      'accounting_module',
      'bug_module',
      'business_configuration_module',
      'business_process_module',
      'campaign_module',
      'component_module',
      'computer_model_module',
      'computer_module',
      'computer_network_module',
      'consumption_document_module',
      'credential_recovery_module',
      'credential_request_module',
      'credential_update_module',
      'currency_module',
      'cloud_contract_module',
      'data_set_module',
      'document_ingestion_module',
      'document_module',
      'event_module',
      'external_source_module',
      'glossary_module',
      'hosting_subscription_module',
      'image_module',
      'internal_order_module',
      'internal_packing_list_module',
      'internal_supply_module',
      'internal_trade_condition_module',
      'inventory_module',
      'item_module',
      'knowledge_pad_module',
      'meeting_module',
      'notification_message_module',
      'open_internal_order_module',
      'open_purchase_order_module',
      'open_sale_order_module',
      'organisation_module',
      'person_module',
      'portal_activities',
      'portal_simulation',
      'product_module',
      'project_module',
      'purchase_order_module',
      'purchase_packing_list_module',
      'purchase_supply_module',
      'purchase_trade_condition_module',
      'quantity_unit_conversion_module',
      'query_module',
      'regularisation_request_module',
      'requirement_module',
      'returned_purchase_packing_list_module',
      'returned_sale_packing_list_module',
      'sale_opportunity_module',
      'sale_order_module',
      'sale_packing_list_module',
      'sale_supply_module',
      'sale_trade_condition_module',
      'service_module',
      'service_report_module',
      'software_installation_module',
      'software_instance_module',
      'software_licence_module',
      'software_product_module',
      'software_publication_module',
      'software_release_module',
      'support_request_module',
      'system_event_module',
      'task_module',
      'task_report_module',
      'transformation_module',
      'upgrade_decision_module',
      'web_page_module',
      'web_site_module',
      'workflow_module',
    ])

    diff = lambda l1,l2: [x for x in l1 if x not in l2]
    result = ""
    for x in diff(expected_list, visited_list):
      result += "- %s\n" % x
    for x in diff(visited_list, expected_list):
      result += "+ %s\n" % x
    self.assertSameSet(expected_list, visited_list, result)

class TestSlapOSAllocation(testSlapOSMixin):

  def _makeSlaveTree(self, requested_template_id='template_slave_instance'):
    super(TestSlapOSAllocation, self).\
        _makeTree(requested_template_id=requested_template_id)

  def _simulatePerson_isAllowedToAllocate(self):
    script_name = 'Person_isAllowedToAllocate'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Person_isAllowedToAllocate')
return True""" )
    transaction.commit()

  def _simulatePerson_isNotAllowedToAllocate(self):
    script_name = 'Person_isAllowedToAllocate'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""return False""")
    transaction.commit()

  def _dropPerson_isAllowedToAllocate(self):
    script_name = 'Person_isAllowedToAllocate'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_person_allocation_checked(self):
    self._makeTree()
    self._simulatePerson_isAllowedToAllocate()
    try:
      self.software_instance.SoftwareInstance_tryToAllocatePartition()
    finally:
      self._dropPerson_isAllowedToAllocate()
    self.assertEqual(
        'Visited by Person_isAllowedToAllocate',
        self.person_user.workflow_history['edit_workflow'][-1]['comment'])

  def test_no_allocation_if_person_is_not_allowed(self):
    self._makeTree()

    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self._simulatePerson_isNotAllowedToAllocate()
    try:
      self.software_instance.SoftwareInstance_tryToAllocatePartition()
    finally:
      self._dropPerson_isAllowedToAllocate()
    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.assertEqual(
        'Allocation failed: Allocation disallowed',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_no_free_partition(self):
    self._makeTree()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_no_host_instance(self):
    self._makeSlaveTree()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))

  def _installSoftware(self, computer, url):
    software_installation = self.portal.software_installation_module\
        .template_software_installation.Base_createCloneDocument(batch_mode=1)
    software_installation.edit(url_string=url,
        reference='TESTSOFTINST-%s' % self.generateNewId(),
        aggregate=computer.getRelativeUrl())
    software_installation.validate()
    software_installation.requestStart()
    self.tic()

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_free_partition(self):
    self._makeTree()

    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  def _allocateHost(self, software_instance, computer_partition):
    software_instance.edit(
        aggregate_value=computer_partition
        )
    computer_partition.markBusy()
    self.tic()

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_host_instance(self):
    self._makeSlaveTree()

    self._makeComputer()
    self._allocateHost(self.requested_software_instance,
        self.partition)

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_capacity_scope_close(self):
    self._makeTree()

    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())
    self.computer.edit(capacity_scope='close')
    self.tic()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None,
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_host_capacity_scope_close(self):
    self._makeSlaveTree()

    self._makeComputer()
    self._allocateHost(self.requested_software_instance,
        self.partition)
    self.computer.edit(capacity_scope='close')
    self.tic()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None,
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_allocation_scope_close(self):
    self._makeTree()

    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())
    self.computer.edit(allocation_scope='close')
    self.tic()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None,
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_host_allocation_scope_close(self):
    self._makeSlaveTree()

    self._makeComputer()
    self._allocateHost(self.requested_software_instance,
        self.partition)
    self.computer.edit(allocation_scope='close')
    self.tic()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None,
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_allocation_scope_open_personal(self):
    self._makeTree()

    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())
    self.computer.edit(allocation_scope='open/personal',
      source_administration=self.person_user.getRelativeUrl())
    self.tic()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_host_allocation_scope_open_personal(self):
    self._makeSlaveTree()

    self._makeComputer()
    self._allocateHost(self.requested_software_instance,
        self.partition)
    self.computer.edit(allocation_scope='open/personal',
      source_administration=self.person_user.getRelativeUrl())
    self.tic()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_allocation_scope_open_friend(self):
    self._makeTree()

    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())
    # change computer owner
    new_id = self.generateNewId()
    person_user = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    person_user.validate()
    for assignment in person_user.contentValues(portal_type="Assignment"):
      assignment.open()

    self.computer.edit(
      source_administration=person_user.getRelativeUrl(),
      destination_section=self.person_user.getRelativeUrl(),
      allocation_scope='open/friend')
    self.tic()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_host_allocation_scope_open_friend(self):
    self._makeSlaveTree()

    self._makeComputer()
    self._allocateHost(self.requested_software_instance,
        self.partition)
    # change computer owner
    new_id = self.generateNewId()
    person_user = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    person_user.validate()
    for assignment in person_user.contentValues(portal_type="Assignment"):
      assignment.open()

    self.computer.edit(
      source_administration=person_user.getRelativeUrl(),
      destination_section=self.person_user.getRelativeUrl(),
      allocation_scope='open/friend')
    self.tic()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_does_not_fail_on_instance_with_damaged_sla_xml(self):
    self._makeTree()

    self.software_instance.setSlaXml('this is not xml')
    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    transaction.abort()

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_does_not_fail_on_slave_with_damaged_sla_xml(self):
    self._makeSlaveTree()

    self.software_instance.setSlaXml('this is not xml')
    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    transaction.abort()

  def _simulateSoftwareInstance_tryToAllocatePartition(self):
    script_name = 'SoftwareInstance_tryToAllocatePartition'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by SoftwareInstance_tryToAllocatePartition') """ )
    transaction.commit()

  def _dropSoftwareInstance_tryToAllocatePartition(self):
    script_name = 'SoftwareInstance_tryToAllocatePartition'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_alarm_software_instance_unallocated(self):
    self._makeTree()

    self._simulateSoftwareInstance_tryToAllocatePartition()
    try:
      self.portal.portal_alarms.slapos_allocate_instance.activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_tryToAllocatePartition()
    self.assertEqual(
        'Visited by SoftwareInstance_tryToAllocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_alarm_slave_instance_unallocated(self):
    self._makeSlaveTree()

    self._simulateSoftwareInstance_tryToAllocatePartition()
    try:
      self.portal.portal_alarms.slapos_allocate_instance.activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_tryToAllocatePartition()
    self.assertEqual(
        'Visited by SoftwareInstance_tryToAllocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_alarm_software_instance_allocated(self):
    self._makeTree()

    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.tic()
    self._simulateSoftwareInstance_tryToAllocatePartition()
    try:
      self.portal.portal_alarms.slapos_allocate_instance.activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_tryToAllocatePartition()
    self.assertNotEqual(
        'Visited by SoftwareInstance_tryToAllocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_alarm_slave_instance_allocated(self):
    self._makeSlaveTree()

    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.tic()
    self._simulateSoftwareInstance_tryToAllocatePartition()
    try:
      self.portal.portal_alarms.slapos_allocate_instance.activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_tryToAllocatePartition()
    self.assertNotEqual(
        'Visited by SoftwareInstance_tryToAllocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_computer_guid(self):
    self._makeTree()

    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))

    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='computer_guid'>%s</parameter>
        </instance>""" % '%s_foo' % self.partition.getParentValue().getReference())
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None,
        self.software_instance.getAggregate(portal_type='Computer Partition'))

    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='computer_guid'>%s</parameter>
        </instance>""" % '%s' % self.partition.getParentValue().getReference())
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_instance_guid(self):
    self._makeSlaveTree()

    self._makeComputer()
    self._allocateHost(self.requested_software_instance,
        self.partition)

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))

    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='instance_guid'>%s</parameter>
        </instance>""" % '%s_foo' % \
        self.requested_software_instance.getReference())
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None,
        self.software_instance.getAggregate(portal_type='Computer Partition'))

    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='instance_guid'>%s</parameter>
        </instance>""" % '%s' % \
        self.requested_software_instance.getReference())
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_network_guid(self):
    self._makeTree()

    self._makeComputer()
    new_id = self.generateNewId()
    computer_network = self.portal.computer_network_module.newContent(
        portal_type='Computer Network',
        title="live_test_%s" % new_id,
        reference="live_test_%s" % new_id)
    computer_network.validate()
    self.computer.edit(
        subordination_value=computer_network)
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))

    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='network_guid'>%s</parameter>
        </instance>""" % '%s_foo' % \
          self.partition.getParentValue().getSubordinationReference())
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None,
        self.software_instance.getAggregate(portal_type='Computer Partition'))

    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='network_guid'>%s</parameter>
        </instance>""" % '%s' % \
          self.partition.getParentValue().getSubordinationReference())
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_mode_unique_by_network_one_network(self):
    """
    Test that when mode is "unique_by_network", we deploy new instance on
    computer network not already used by any software instance of the
    hosting subscription.
    Then test that we do NOT deploy new instance on
    computer network already used by any software instance of the
    hosting subscription.
    """
    sla_xml = """<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='mode'>unique_by_network</parameter>
        </instance>"""
    self._makeTree()
    computer1, partition1 = self._makeComputer()
    computer2, partition2 = self._makeComputer()
    self._installSoftware(computer1, self.software_instance.getUrlString())
    self._installSoftware(computer2, self.software_instance.getUrlString())

    new_id = self.generateNewId()
    computer_network = self.portal.computer_network_module.newContent(
        portal_type='Computer Network',
        title="live_test_%s" % new_id,
        reference="live_test_%s" % new_id)
    computer_network.validate()
    computer1.edit(subordination_value=computer_network)
    computer2.edit(subordination_value=computer_network)

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))

    software_instance2 = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    software_instance2.edit(
      title=self.generateNewSoftwareTitle(),
      reference="TESTSI-%s" % self.generateNewId(),
      url_string=self.software_instance.getUrlString(),
      source_reference=self.generateNewSoftwareType(),
      text_content=self.generateSafeXml(),
      sla_xml=sla_xml,
      specialise=self.hosting_subscription.getRelativeUrl(),
    )
    self.portal.portal_workflow._jumpToStateFor(software_instance2, 'start_requested')
    software_instance2.validate()
    self.tic()

    self.software_instance.setSlaXml(sla_xml)
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(
        computer_network.getReference(),
        self.software_instance.getAggregateValue(portal_type='Computer Partition')\
            .getParentValue().getSubordinationReference(),
    )

    self.tic()
    software_instance2.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(
        None,
        software_instance2.getAggregate(portal_type='Computer Partition')
    )

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_mode_unique_by_network_several_network(self):
    """
    Test that when mode is "unique_by_network", we deploy new instance on
    computer network not already used by any software instance of the
    hosting subscription.
    Then test that we do NOT deploy new instance on
    computer network already used by any software instance of the
    hosting subscription.
    Test with 3 instances and 3 existing computers on 2 different networks.
    """
    sla_xml = """<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='mode'>unique_by_network</parameter>
        </instance>"""
    self._makeTree()
    computer1, partition1 = self._makeComputer()
    computer2, partition2 = self._makeComputer()
    computer3, partition3 = self._makeComputer()
    computer_network1 = self._makeComputerNetwork()
    computer_network2 = self._makeComputerNetwork()

    computer1.edit(subordination_value=computer_network1)
    computer2.edit(subordination_value=computer_network1)
    computer3.edit(subordination_value=computer_network2)

    self._installSoftware(computer1, self.software_instance.getUrlString())
    self._installSoftware(computer2, self.software_instance.getUrlString())
    self._installSoftware(computer3, self.software_instance.getUrlString())

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))

    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='mode'>unique_by_network</parameter>
        <parameter id='computer_guid'>%s</parameter>
        </instance>""" % computer1.getReference())
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(
        self.software_instance.getAggregate(portal_type='Computer Partition'),
        partition1.getRelativeUrl(),
    )

    software_instance2 = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    software_instance2.edit(
      title=self.generateNewSoftwareTitle(),
      reference="TESTSI-%s" % self.generateNewId(),
      url_string=self.software_instance.getUrlString(),
      source_reference=self.generateNewSoftwareType(),
      text_content=self.generateSafeXml(),
      sla_xml=sla_xml,
      specialise=self.hosting_subscription.getRelativeUrl(),
    )
    self.portal.portal_workflow._jumpToStateFor(software_instance2, 'start_requested')
    software_instance2.validate()
    self.tic()
    software_instance2.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(
        software_instance2.getAggregate(portal_type='Computer Partition'),
        partition3.getRelativeUrl(),
    )

    software_instance3 = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    software_instance3.edit(
      title=self.generateNewSoftwareTitle(),
      reference="TESTSI-%s" % self.generateNewId(),
      url_string=self.software_instance.getUrlString(),
      source_reference=self.generateNewSoftwareType(),
      text_content=self.generateSafeXml(),
      sla_xml=sla_xml,
      specialise=self.hosting_subscription.getRelativeUrl(),
    )
    self.portal.portal_workflow._jumpToStateFor(software_instance3, 'start_requested')
    software_instance3.validate()
    self.tic()

    software_instance3.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(
        None,
        software_instance3.getAggregate(portal_type='Computer Partition')
    )

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_mode_unique_by_network_no_network(self):
    """
    Test that when we request instance with mode as 'unique_by_network',
    instance is not deployed on computer with no network.
    """
    self._makeTree()
    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))

    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='mode'>unique_by_network</parameter>
        </instance>""")
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(
        None,
        self.software_instance.getAggregate(portal_type='Computer Partition')
    )

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_mode_unique_by_network_check_serialize_called(self):
    """
    Test that on being_requested serialise is being called
    code stolen from testERP5Security:test_MultiplePersonReferenceConcurrentTransaction
    """
    class DummyTestException(Exception):
      pass

    def verify_serialize_call(self):
      # it is checking that anything below computer_module raises exception
      # thanks to this this test do not have to be destructive
      if self.getPortalType() == "Hosting Subscription":
        raise DummyTestException
      else:
        return self.serialize_call()

    self._makeTree()
    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='mode'>unique_by_network</parameter>
        </instance>""")

    from Products.ERP5Type.Base import Base
    Base.serialize_call = Base.serialize
    try:
      Base.serialize = verify_serialize_call
      self.assertRaises(DummyTestException,
        self.software_instance.SoftwareInstance_tryToAllocatePartition)
    finally:
      Base.serialize = Base.serialize_call

    transaction.abort()

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_mode_unique_by_network_no_parallel(self):
    """
    Test that when we request two instances of the same Hosting Subscription
    with mode as 'unique_by_network' at the same time, they don't get
    allocated to the same network.
    """
    sla_xml = """<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='mode'>unique_by_network</parameter>
        </instance>"""
    self._makeTree()
    computer1, partition1 = self._makeComputer()
    computer2, partition2 = self._makeComputer()
    self._installSoftware(computer1, self.software_instance.getUrlString())
    self._installSoftware(computer2, self.software_instance.getUrlString())

    new_id = self.generateNewId()
    computer_network = self.portal.computer_network_module.newContent(
        portal_type='Computer Network',
        title="live_test_%s" % new_id,
        reference="live_test_%s" % new_id)
    computer_network.validate()
    computer1.edit(subordination_value=computer_network)
    computer2.edit(subordination_value=computer_network)

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))

    software_instance2 = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    software_instance2.edit(
      title=self.generateNewSoftwareTitle(),
      reference="TESTSI-%s" % self.generateNewId(),
      url_string=self.software_instance.getUrlString(),
      source_reference=self.generateNewSoftwareType(),
      text_content=self.generateSafeXml(),
      sla_xml=sla_xml,
      specialise=self.hosting_subscription.getRelativeUrl(),
    )
    self.portal.portal_workflow._jumpToStateFor(software_instance2, 'start_requested')
    software_instance2.validate()
    self.tic()

    self.software_instance.setSlaXml(sla_xml)
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    software_instance2.SoftwareInstance_tryToAllocatePartition()
    # First is deployed
    self.assertEqual(
        computer_network.getReference(),
        self.software_instance.getAggregateValue(portal_type='Computer Partition')\
            .getParentValue().getSubordinationReference(),
    )
    # But second is not yet deployed because of pending activities containing tag
    self.assertEqual(
        None,
        software_instance2.getAggregate(portal_type='Computer Partition')
    )

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_unexpected_sla_parameter(self):
    self._makeTree()

    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))

    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='foo'>bar</parameter>
        </instance>""")
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None,
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  def check_allocation_category_sla(self, base_category, computer_category,
                                    other_category):
    self._makeTree()

    self._makeComputer()
    self.computer.edit(**{base_category: computer_category})
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))

    # Another category
    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='%s'>%s</parameter>
        </instance>""" % (base_category, other_category))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None,
        self.software_instance.getAggregate(portal_type='Computer Partition'))

    # No existing category
    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='%s'>foo</parameter>
        </instance>""" % (base_category))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None,
        self.software_instance.getAggregate(portal_type='Computer Partition'))

    # Computer category
    self.software_instance.setSlaXml("""<?xml version='1.0' encoding='utf-8'?>
        <instance>
        <parameter id='%s'>%s</parameter>
        </instance>""" % (base_category, computer_category))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_group_sla(self):
    return self.check_allocation_category_sla('group', 'vifib', 'ovh')

  @skip('No category available')
  def test_allocation_cpu_core_sla(self):
    return self.check_allocation_category_sla('cpu_core', 'vifib', 'ovh')

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_cpu_frequency_sla(self):
    return self.check_allocation_category_sla('cpu_frequency', '1000', '2000')

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_cpu_type_sla(self):
    return self.check_allocation_category_sla('cpu_type', 'x86', 'x86/x86_32')

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_local_area_network_type_sla(self):
    return self.check_allocation_category_sla('local_area_network_type', 
                                              'ethernet', 'wifi')

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_memory_size_sla(self):
    return self.check_allocation_category_sla('memory_size', '128', '256')

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_memory_type_sla(self):
    return self.check_allocation_category_sla('memory_type', 'ddr2', 'ddr3')

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_region_sla(self):
    return self.check_allocation_category_sla('region', 'africa', 
                                              'america')

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_storage_capacity_sla(self):
    return self.check_allocation_category_sla('storage_capacity', 'finite', 
                                              'infinite')

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_storage_interface_sla(self):
    return self.check_allocation_category_sla('storage_interface', 'nas', 'san')

  @simulate('Person_isAllowedToAllocate', '*args, **kwargs', 'return True')
  def test_allocation_storage_redundancy_sla(self):
    return self.check_allocation_category_sla('storage_redundancy', 'dht', 'raid')

class TestSlapOSCoreSlapOSAssertHostingSubscriptionPredecessorAlarm(
    testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSCoreSlapOSAssertHostingSubscriptionPredecessorAlarm,
        self).afterSetUp()
    self._makeTree()

  def test_HostingSubscription_assertPredecessor(self):
    self.software_instance.rename(new_name=self.generateNewSoftwareTitle())
    self.tic()

    # check that no interaction has recreated the instance
    self.assertFalse(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

    self.hosting_subscription.HostingSubscription_assertPredecessor()
    self.assertTrue(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

  def test_HostingSubscription_assertPredecessor_stop_requested(self):
    self.software_instance.rename(new_name=self.generateNewSoftwareTitle())
    self.portal.portal_workflow._jumpToStateFor(self.hosting_subscription,
        'stop_requested')
    self.tic()

    # check that no interaction has recreated the instance
    self.assertFalse(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

    self.hosting_subscription.HostingSubscription_assertPredecessor()
    self.assertTrue(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

  def test_HostingSubscription_assertPredecessor_destroy_requested(self):
    self.software_instance.rename(new_name=self.generateNewSoftwareTitle())
    self.portal.portal_workflow._jumpToStateFor(self.hosting_subscription,
        'destroy_requested')
    self.tic()

    # check that no interaction has recreated the instance
    self.assertFalse(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

    self.hosting_subscription.HostingSubscription_assertPredecessor()
    self.assertFalse(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

  def test_HostingSubscription_assertPredecessor_archived(self):
    self.software_instance.rename(new_name=self.generateNewSoftwareTitle())
    self.hosting_subscription.archive()
    self.tic()

    # check that no interaction has recreated the instance
    self.assertFalse(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

    self.hosting_subscription.HostingSubscription_assertPredecessor()
    self.assertFalse(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

  def _simulateHostingSubscription_assertPredecessor(self):
    script_name = 'HostingSubscription_assertPredecessor'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by HostingSubscription_assertPredecessor') """ )
    transaction.commit()

  def _dropHostingSubscription_assertPredecessor(self):
    script_name = 'HostingSubscription_assertPredecessor'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_renamed(self):
    self.software_instance.edit(title=self.generateNewSoftwareTitle())
    self.tic()
    self._simulateHostingSubscription_assertPredecessor()
    try:
      self.portal.portal_alarms.slapos_assert_hosting_subscription_predecessor.activeSense()
      self.tic()
    finally:
      self._dropHostingSubscription_assertPredecessor()
    self.assertEqual(
        'Visited by HostingSubscription_assertPredecessor',
        self.hosting_subscription.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_renamed(self):
    self._simulateHostingSubscription_assertPredecessor()
    try:
      self.portal.portal_alarms.slapos_assert_hosting_subscription_predecessor.activeSense()
      self.tic()
    finally:
      self._dropHostingSubscription_assertPredecessor()
    self.assertNotEqual(
        'Visited by HostingSubscription_assertPredecessor',
        self.hosting_subscription.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSFreeComputerPartitionAlarm(testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSFreeComputerPartitionAlarm, self).afterSetUp()
    self._makeTree()

  def test_Instance_tryToUnallocatePartition(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.software_instance.Instance_tryToUnallocatePartition()
    self.tic()
    self.assertEqual(None, self.software_instance.getAggregate())
    self.assertEqual('free', self.partition.getSlapState())

  def test_Instance_tryToUnallocatePartition_concurrency(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.partition.activate(tag="allocate_%s" % self.partition.getRelativeUrl()\
        ).getId()
    transaction.commit()
    self.software_instance.Instance_tryToUnallocatePartition()
    self.tic()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate())
    self.assertEqual('busy', self.partition.getSlapState())

  def test_Instance_tryToUnallocatePartition_twoInstances(self):
    software_instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)

    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.software_instance.Instance_tryToUnallocatePartition()
    self.tic()
    self.assertEqual(None, self.software_instance.getAggregate())
    self.assertEqual('busy', self.partition.getSlapState())
    self.assertEqual(self.partition.getRelativeUrl(), software_instance.getAggregate())

  def _simulateInstance_tryToUnallocatePartition(self):
    script_name = 'Instance_tryToUnallocatePartition'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Instance_tryToUnallocatePartition') """ )
    transaction.commit()

  def _dropInstance_tryToUnallocatePartition(self):
    script_name = 'Instance_tryToUnallocatePartition'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_allocated(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.software_instance.invalidate()
    self.tic()
    self._simulateInstance_tryToUnallocatePartition()
    try:
      self.portal.portal_alarms.slapos_free_computer_partition.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToUnallocatePartition()
    self.assertEqual(
        'Visited by Instance_tryToUnallocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_unallocated(self):
    self._makeComputer()
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.software_instance.invalidate()
    self.tic()
    self._simulateInstance_tryToUnallocatePartition()
    try:
      self.portal.portal_alarms.slapos_free_computer_partition.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToUnallocatePartition()
    self.assertNotEqual(
        'Visited by Instance_tryToUnallocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_validated(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()
    self._simulateInstance_tryToUnallocatePartition()
    try:
      self.portal.portal_alarms.slapos_free_computer_partition.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToUnallocatePartition()
    self.assertNotEqual(
        'Visited by Instance_tryToUnallocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_start_requested(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.tic()
    self._simulateInstance_tryToUnallocatePartition()
    try:
      self.portal.portal_alarms.slapos_free_computer_partition.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToUnallocatePartition()
    self.assertNotEqual(
        'Visited by Instance_tryToUnallocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSFreeComputerPartitionAlarmWithSlave(testSlapOSMixin):
  def afterSetUp(self):
    super(TestSlapOSFreeComputerPartitionAlarmWithSlave, self).afterSetUp()
    self._makeTree(requested_template_id='template_slave_instance')

  def test_Instance_tryToUnallocatePartition(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.software_instance.Instance_tryToUnallocatePartition()
    self.tic()
    self.assertEqual(None, self.software_instance.getAggregate())
    self.assertEqual('free', self.partition.getSlapState())

  def test_Instance_tryToUnallocatePartition_nonDestroyed(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.tic()

    self.software_instance.Instance_tryToUnallocatePartition()
    self.tic()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate())
    self.assertEqual('busy', self.partition.getSlapState())


class TestSlapOSGarbageCollectDestroyedRootTreeAlarm(testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSGarbageCollectDestroyedRootTreeAlarm, self).afterSetUp()
    self._makeTree()

  def test_Instance_tryToGarbageCollect(self):
    self.hosting_subscription.archive()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.requested_software_instance.Instance_tryToGarbageCollect()
    self.tic()
    self.assertEqual('destroy_requested',
        self.requested_software_instance.getSlapState())
    self.assertEqual('validated',
        self.requested_software_instance.getValidationState())

  def test_Instance_tryToGarbageCollect_not_destroy_requested(self):
    self.requested_software_instance.Instance_tryToGarbageCollect()
    self.tic()
    self.assertEqual('start_requested',
        self.requested_software_instance.getSlapState())
    self.assertEqual('validated',
        self.requested_software_instance.getValidationState())

  def test_Instance_tryToGarbageCollect_not_archived(self):
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.requested_software_instance.Instance_tryToGarbageCollect()
    self.tic()
    self.assertEqual('start_requested',
        self.requested_software_instance.getSlapState())
    self.assertEqual('validated',
        self.requested_software_instance.getValidationState())

  def test_Instance_tryToGarbageCollect_only_instance_destroy_requested(self):
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.requested_software_instance.Instance_tryToGarbageCollect()
    self.tic()
    self.assertEqual('start_requested',
        self.requested_software_instance.getSlapState())
    self.assertEqual('validated',
        self.requested_software_instance.getValidationState())

  def _simulateInstance_tryToGarbageCollect(self):
    script_name = 'Instance_tryToGarbageCollect'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Instance_tryToGarbageCollect') """ )
    transaction.commit()

  def _dropInstance_tryToGarbageCollect(self):
    script_name = 'Instance_tryToGarbageCollect'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm(self):
    self.hosting_subscription.archive()
    self.tic()
    self._simulateInstance_tryToGarbageCollect()
    try:
      self.portal.portal_alarms.slapos_garbage_collect_destroyed_root_tree.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToGarbageCollect()
    self.assertEqual(
        'Visited by Instance_tryToGarbageCollect',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_invalidated(self):
    self.hosting_subscription.archive()
    self.software_instance.invalidate()
    self.tic()
    self._simulateInstance_tryToGarbageCollect()
    try:
      self.portal.portal_alarms.slapos_garbage_collect_destroyed_root_tree.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToGarbageCollect()
    self.assertNotEqual(
        'Visited by Instance_tryToGarbageCollect',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_archived(self):
    self.tic()
    self._simulateInstance_tryToGarbageCollect()
    try:
      self.portal.portal_alarms.slapos_garbage_collect_destroyed_root_tree.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToGarbageCollect()
    self.assertNotEqual(
        'Visited by Instance_tryToGarbageCollect',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSUpdateComputerCapacityScopeAlarm(testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSUpdateComputerCapacityScopeAlarm, self).afterSetUp()
    self.computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    self.computer.edit(
        allocation_scope='open/public',
        capacity_scope='open',
        reference='TESTC-%s' % self.generateNewId(),
    )
    self.computer.validate()
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
        key_prefix='slap_tool',
        plugin_path='portal_memcached/default_memcached_plugin')
    memcached_dict[self.computer.getReference()] = json.dumps({
        'text': '#access ok',
        'created_at': rfc1123_date(DateTime())
    })
    transaction.commit()

  def test_Computer_checkAndUpdateCapacityScope(self):
    self.computer.Computer_checkAndUpdateCapacityScope()
    self.assertEqual('open', self.computer.getCapacityScope())

  def _newComputerModel(self, quantity=None):
    computer_model = self.portal.computer_model_module.\
        template_computer_model.Base_createCloneDocument(batch_mode=1)
    computer_model.edit(capacity_quantity=quantity,
        reference='TESTCM-%s' % self.generateNewId(),
    )
    return computer_model

  def _addPartitionToComputer(self):
    partition = self.computer.newContent(portal_type='Computer Partition',
        reference='part1')
    partition.markFree()
    partition.markBusy()
    partition.validate()
    self.software_instance.setAggregate(partition.getRelativeUrl())
    self.tic()

  def test_Computer_checkAndUpdateCapacityScope_model(self):
    computer_model = self._newComputerModel(9999)

    self.computer.edit(specialise_value=computer_model, 
                       capacity_quantity=None)
    transaction.commit()

    self.computer.Computer_checkAndUpdateCapacityScope()
    self.assertEqual('open', self.computer.getCapacityScope())
    self.assertEqual(computer_model.getCapacityQuantity(),
                     self.computer.getCapacityQuantity())

  def test_Computer_checkAndUpdateCapacityScope_model_no_capacity(self):
    self._makeTree()

    computer_model = self._newComputerModel(1)
    self.computer.edit(specialise_value=computer_model, 
                       capacity_quantity=None)

    self._addPartitionToComputer() 
    self.computer.Computer_checkAndUpdateCapacityScope()
    self.assertEqual('close', self.computer.getCapacityScope())
    self.assertEqual('Computer capacity limit exceeded',
        self.computer.workflow_history['edit_workflow'][-1]['comment'])

    self.assertEqual(computer_model.getCapacityQuantity(),
                     self.computer.getCapacityQuantity())

  def test_Computer_checkAndUpdateCapacityScope_model_has_capacity(self):
    # If capacity is set on computer, model value is ignored.
    self._makeTree()

    computer_model = self._newComputerModel(1)
    self.computer.edit(specialise_value=computer_model, 
                       capacity_quantity=2)

    self._addPartitionToComputer()
    self.computer.Computer_checkAndUpdateCapacityScope()
    self.assertEqual('open', self.computer.getCapacityScope())

    self.assertNotEqual(computer_model.getCapacityQuantity(),
                     self.computer.getCapacityQuantity())

  def test_Computer_checkAndUpdateCapacityScope_with_old_access(self):
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
        key_prefix='slap_tool',
        plugin_path='portal_memcached/default_memcached_plugin')
    memcached_dict[self.computer.getReference()] = json.dumps({
        'text': '#access ok',
        'created_at': rfc1123_date(addToDate(DateTime(), 
                                             to_add={'minute': -11}))
    })
    self.computer.Computer_checkAndUpdateCapacityScope()
    self.assertEqual('close', self.computer.getCapacityScope())
    self.assertEqual("Computer didn't contact for more than 10 minutes",
        self.computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_Computer_checkAndUpdateCapacityScope_no_capacity_quantity(self):
    self._makeTree()
    self.computer.edit(capacity_quantity=1)
    self._addPartitionToComputer()
    self.computer.Computer_checkAndUpdateCapacityScope()
    self.assertEqual('close', self.computer.getCapacityScope())
    self.assertEqual('Computer capacity limit exceeded',
        self.computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_Computer_checkAndUpdateCapacityScope_no_access(self):
    self.computer.edit(reference='TESTC-%s' % self.generateNewId())
    self.computer.Computer_checkAndUpdateCapacityScope()
    self.assertEqual('close', self.computer.getCapacityScope())
    self.assertEqual("Computer didn't contact the server",
        self.computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_Computer_checkAndUpdateCapacityScope_close(self):
    self.computer.edit(capacity_scope='close')
    self.computer.Computer_checkAndUpdateCapacityScope()
    self.assertEqual('open', self.computer.getCapacityScope())

  def test_Computer_checkAndUpdateCapacityScope_with_error(self):
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
        key_prefix='slap_tool',
        plugin_path='portal_memcached/default_memcached_plugin')
    memcached_dict[self.computer.getReference()] = json.dumps({
        'text': '#error not ok'
    })
    self.computer.Computer_checkAndUpdateCapacityScope()
    self.assertEqual('close', self.computer.getCapacityScope())
    self.assertEqual("Computer reported an error",
        self.computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_Computer_checkAndUpdateCapacityScope_with_error_non_public(self):
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
        key_prefix='slap_tool',
        plugin_path='portal_memcached/default_memcached_plugin')
    memcached_dict[self.computer.getReference()] = json.dumps({
        'text': '#error not ok'
    })
    self.computer.edit(allocation_scope='open/personal')
    self.computer.Computer_checkAndUpdateCapacityScope()
    self.assertEqual('open', self.computer.getCapacityScope())

  def _simulateComputer_checkAndUpdateCapacityScope(self):
    script_name = 'Computer_checkAndUpdateCapacityScope'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Computer_checkAndUpdateCapacityScope') """ )
    transaction.commit()

  def _dropComputer_checkAndUpdateCapacityScope(self):
    script_name = 'Computer_checkAndUpdateCapacityScope'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm(self):
    self._simulateComputer_checkAndUpdateCapacityScope()
    try:
      self.portal.portal_alarms.slapos_update_computer_capacity_scope.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkAndUpdateCapacityScope()
    self.assertEqual(
        'Visited by Computer_checkAndUpdateCapacityScope',
        self.computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_non_public(self):
    self.computer.edit(allocation_scope='open/personal')
    self.tic()
    self._simulateComputer_checkAndUpdateCapacityScope()
    try:
      self.portal.portal_alarms.slapos_update_computer_capacity_scope.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkAndUpdateCapacityScope()
    self.assertNotEqual(
        'Visited by Computer_checkAndUpdateCapacityScope',
        self.computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_invalidated(self):
    self.computer.invalidate()
    self.tic()
    self._simulateComputer_checkAndUpdateCapacityScope()
    try:
      self.portal.portal_alarms.slapos_update_computer_capacity_scope.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkAndUpdateCapacityScope()
    self.assertNotEqual(
        'Visited by Computer_checkAndUpdateCapacityScope',
        self.computer.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSGarbageCollectStoppedRootTreeAlarm(testSlapOSMixin):

  def createInstance(self):
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.edit(
    )
    hosting_subscription.validate()
    hosting_subscription.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTHS-%s" % self.generateNewId(),
    )
    request_kw = dict(
      software_release=\
          self.generateNewSoftwareReleaseUrl(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='started'
    )
    hosting_subscription.requestStart(**request_kw)
    hosting_subscription.requestInstance(**request_kw)

    instance = hosting_subscription.getPredecessorValue()
    self.tic()
    return instance

  def test_Instance_tryToStopCollect_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Instance_tryToStopCollect,
      REQUEST={})

  def test_Instance_tryToStopCollect_started_instance(self):
    instance = self.createInstance()
    hosting_subscription = instance.getSpecialiseValue()

    self.portal.portal_workflow._jumpToStateFor(hosting_subscription,
        'stop_requested')
    self.assertEqual('start_requested', instance.getSlapState())

    instance.Instance_tryToStopCollect()
    self.assertEqual('stop_requested', instance.getSlapState())

  def test_Instance_tryToStopCollect_started_instance(self):
    instance = self.createInstance()
    hosting_subscription = instance.getSpecialiseValue()

    self.portal.portal_workflow._jumpToStateFor(hosting_subscription,
        'stop_requested')
    self.assertEqual('start_requested', instance.getSlapState())

    instance.Instance_tryToStopCollect()
    self.assertEqual('stop_requested', instance.getSlapState())

  def test_Instance_tryToStopCollect_destroyed_instance(self):
    instance = self.createInstance()
    hosting_subscription = instance.getSpecialiseValue()

    self.portal.portal_workflow._jumpToStateFor(hosting_subscription,
        'stop_requested')
    self.portal.portal_workflow._jumpToStateFor(instance,
        'destroy_requested')

    instance.Instance_tryToStopCollect()
    self.assertEqual('destroy_requested', instance.getSlapState())

  def test_Instance_tryToStopCollect_started_subscription(self):
    instance = self.createInstance()
    hosting_subscription = instance.getSpecialiseValue()

    self.assertEqual('start_requested', hosting_subscription.getSlapState())
    self.assertEqual('start_requested', instance.getSlapState())

    instance.Instance_tryToStopCollect()
    self.assertEqual('start_requested', instance.getSlapState())

  def _simulateInstance_tryToStopCollect(self):
    script_name = 'Instance_tryToStopCollect'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Instance_tryToStopCollect') """ )
    transaction.commit()

  def _dropInstance_tryToStopCollect(self):
    script_name = 'Instance_tryToStopCollect'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm(self):
    instance = self.createInstance()
    self._simulateInstance_tryToStopCollect()
    try:
      self.portal.portal_alarms.slapos_stop_collect_instance.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToStopCollect()
    self.assertEqual(
        'Visited by Instance_tryToStopCollect',
        instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_invalidated(self):
    instance = self.createInstance()
    instance.invalidate()
    self.tic()
    self._simulateInstance_tryToStopCollect()
    try:
      self.portal.portal_alarms.slapos_stop_collect_instance.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToStopCollect()
    self.assertNotEqual(
        'Visited by Instance_tryToStopCollect',
        instance.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSGarbageCollectNonAllocatedRootTreeAlarm(testSlapOSMixin):

  def createInstance(self):
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    hosting_subscription.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTHS-%s" % self.generateNewId(),
    )
    request_kw = dict(
      software_release=\
          self.generateNewSoftwareReleaseUrl(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='started'
    )
    hosting_subscription.requestStart(**request_kw)
    hosting_subscription.requestInstance(**request_kw)

    instance = hosting_subscription.getPredecessorValue()
    return instance

  def createComputerPartition(self):
    computer = self.portal.computer_module\
        .template_computer.Base_createCloneDocument(batch_mode=1)
    computer.validate()
    computer.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTCOMP-%s" % self.generateNewId(),
    )
    partition = computer.newContent(portal_type="Computer Partition")
    return partition

  def test_tryToGarbageCollect_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Instance_tryToGarbageCollectNonAllocatedRootTree,
      REQUEST={})

  def test_tryToGarbageCollect_invalidated_instance(self):
    instance = self.createInstance()
    instance.invalidate()
    self.tic()

    instance.Instance_tryToGarbageCollectNonAllocatedRootTree()
    self.assertEqual('start_requested', instance.getSlapState())
    hosting_subscription = instance.getSpecialiseValue()
    self.assertEqual('start_requested', hosting_subscription.getSlapState())

  def test_tryToGarbageCollect_destroyed_instance(self):
    instance = self.createInstance()
    self.portal.portal_workflow._jumpToStateFor(instance, 'destroy_requested')
    self.tic()

    instance.Instance_tryToGarbageCollectNonAllocatedRootTree()
    self.assertEqual('destroy_requested', instance.getSlapState())
    hosting_subscription = instance.getSpecialiseValue()
    self.assertEqual('start_requested', hosting_subscription.getSlapState())

  def test_tryToGarbageCollect_allocated_instance(self):
    instance = self.createInstance()
    partition = self.createComputerPartition()
    instance.edit(aggregate_value=partition)
    self.tic()

    instance.Instance_tryToGarbageCollectNonAllocatedRootTree()
    self.assertEqual('start_requested', instance.getSlapState())
    hosting_subscription = instance.getSpecialiseValue()
    self.assertEqual('start_requested', hosting_subscription.getSlapState())

  def test_tryToGarbageCollect_no_allocation_try_found(self):
    instance = self.createInstance()
    self.tic()

    instance.Instance_tryToGarbageCollectNonAllocatedRootTree()
    self.assertEqual('start_requested', instance.getSlapState())
    hosting_subscription = instance.getSpecialiseValue()
    self.assertEqual('start_requested', hosting_subscription.getSlapState())

  def test_tryToGarbageCollect_recent_allocation_try_found(self):
    instance = self.createInstance()
    self.tic()
    instance.workflow_history['edit_workflow'].append({
        'comment':'Allocation failed: no free Computer Partition',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': '',
        'time': addToDate(DateTime(), to_add={'day': -6}),
        'action': 'edit'
    })

    instance.Instance_tryToGarbageCollectNonAllocatedRootTree()
    self.assertEqual('start_requested', instance.getSlapState())
    hosting_subscription = instance.getSpecialiseValue()
    self.assertEqual('start_requested', hosting_subscription.getSlapState())

  def test_tryToGarbageCollect_complex_tree(self):
    instance = self.createInstance()
    hosting_subscription = instance.getSpecialiseValue()
    request_kw = dict(
      software_release=\
          self.generateNewSoftwareReleaseUrl(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title="another %s" % hosting_subscription.getTitle(),
      state='started'
    )
    instance.requestInstance(**request_kw)
    sub_instance = instance.getPredecessorValue()
    self.tic()
    sub_instance.workflow_history['edit_workflow'].append({
        'comment':'Allocation failed: no free Computer Partition',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': '',
        'time': addToDate(DateTime(), to_add={'day': -8}),
        'action': 'edit'
    })

    sub_instance.Instance_tryToGarbageCollectNonAllocatedRootTree()
    self.assertEqual('start_requested', hosting_subscription.getSlapState())

  def test_tryToGarbageCollect_old_allocation_try_found(self):
    instance = self.createInstance()
    hosting_subscription = instance.getSpecialiseValue()
    self.tic()
    instance.workflow_history['edit_workflow'].append({
        'comment':'Allocation failed: no free Computer Partition',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': '',
        'time': addToDate(DateTime(), to_add={'day': -8}),
        'action': 'edit'
    })

    instance.Instance_tryToGarbageCollectNonAllocatedRootTree()
    self.assertEqual('destroy_requested', hosting_subscription.getSlapState())
    self.assertEqual('archived', hosting_subscription.getValidationState())

  def _simulateInstance_tryToGarbageCollectNonAllocatedRootTree(self):
    script_name = 'Instance_tryToGarbageCollectNonAllocatedRootTree'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Instance_tryToGarbageCollectNonAllocatedRootTree') """ )
    transaction.commit()

  def _dropInstance_tryToGarbageCollectNonAllocatedRootTree(self):
    script_name = 'Instance_tryToGarbageCollectNonAllocatedRootTree'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm(self):
    instance = self.createInstance()
    self.tic()
    self._simulateInstance_tryToGarbageCollectNonAllocatedRootTree()
    try:
      self.portal.portal_alarms.slapos_garbage_collect_non_allocated_root_tree.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToGarbageCollectNonAllocatedRootTree()
    self.assertEqual(
        'Visited by Instance_tryToGarbageCollectNonAllocatedRootTree',
        instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_invalidated(self):
    instance = self.createInstance()
    instance.invalidate()
    self.tic()
    self._simulateInstance_tryToGarbageCollectNonAllocatedRootTree()
    try:
      self.portal.portal_alarms.slapos_garbage_collect_non_allocated_root_tree.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToGarbageCollectNonAllocatedRootTree()
    self.assertNotEqual(
        'Visited by Instance_tryToGarbageCollectNonAllocatedRootTree',
        instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_allocated(self):
    instance = self.createInstance()
    partition = self.createComputerPartition()
    instance.edit(aggregate_value=partition)
    self.tic()
    self._simulateInstance_tryToGarbageCollectNonAllocatedRootTree()
    try:
      self.portal.portal_alarms.slapos_garbage_collect_non_allocated_root_tree.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToGarbageCollectNonAllocatedRootTree()
    self.assertNotEqual(
        'Visited by Instance_tryToGarbageCollectNonAllocatedRootTree',
        instance.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSInvalidateDestroyedInstance(testSlapOSMixin):

  def createSoftwareInstance(self):
    new_id = self.generateNewId()
    return self.portal.software_instance_module.newContent(
      portal_type='Software Instance',
      title="Test instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      )

  def createComputerPartition(self):
    new_id = self.generateNewId()
    computer = self.portal.computer_module.newContent(
      portal_type='Computer',
      title="Test computer %s" % new_id,
      reference="TESTCOMP-%s" % new_id,
      )
    computer_partition = computer.newContent(
      portal_type='Computer Partition',
      )
    return computer_partition

  def test_tryToInvalidateIfDestroyed_REQUEST_disallowed(self):
    instance = self.createSoftwareInstance()
    self.assertRaises(
      Unauthorized,
      instance.SoftwareInstance_tryToInvalidateIfDestroyed,
      REQUEST={})

  def test_tryToInvalidateIfDestroyed_unexpected_context(self):
    self.assertRaises(
      TypeError,
      self.portal.SoftwareInstance_tryToInvalidateIfDestroyed,
      )

  def test_tryToInvalidateIfDestroyed_expected_instance(self):
    instance = self.createSoftwareInstance()
    self.portal.portal_workflow._jumpToStateFor(instance, 'validated')
    self.portal.portal_workflow._jumpToStateFor(instance, 'destroy_requested')
    instance.SoftwareInstance_tryToInvalidateIfDestroyed()
    self.assertEqual(instance.getValidationState(), "invalidated")
    self.assertEqual(instance.getSlapState(), "destroy_requested")

  def test_tryToInvalidateIfDestroyed_invalidated_instance(self):
    instance = self.createSoftwareInstance()
    self.portal.portal_workflow._jumpToStateFor(instance, 'invalidated')
    self.portal.portal_workflow._jumpToStateFor(instance, 'destroy_requested')
    instance.SoftwareInstance_tryToInvalidateIfDestroyed()
    self.assertEqual(instance.getValidationState(), "invalidated")
    self.assertEqual(instance.getSlapState(), "destroy_requested")

  def test_tryToInvalidateIfDestroyed_not_destroyed_instance(self):
    instance = self.createSoftwareInstance()
    self.portal.portal_workflow._jumpToStateFor(instance, 'validated')
    self.portal.portal_workflow._jumpToStateFor(instance, 'stop_requested')
    instance.SoftwareInstance_tryToInvalidateIfDestroyed()
    self.assertEqual(instance.getValidationState(), "validated")
    self.assertEqual(instance.getSlapState(), "stop_requested")

  def test_tryToInvalidateIfDestroyed_allocated_instance(self):
    instance = self.createSoftwareInstance()
    partition = self.createComputerPartition()
    instance.edit(aggregate_value=partition)
    self.portal.portal_workflow._jumpToStateFor(instance, 'validated')
    self.portal.portal_workflow._jumpToStateFor(instance, 'destroy_requested')
    instance.SoftwareInstance_tryToInvalidateIfDestroyed()
    self.assertEqual(instance.getValidationState(), "validated")
    self.assertEqual(instance.getSlapState(), "destroy_requested")

  def _simulateSoftwareInstance_tryToInvalidateIfDestroyed(self):
    script_name = 'SoftwareInstance_tryToInvalidateIfDestroyed'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by SoftwareInstance_tryToInvalidateIfDestroyed') """ )
    transaction.commit()

  def _dropSoftwareInstance_tryToInvalidateIfDestroyed(self):
    script_name = 'SoftwareInstance_tryToInvalidateIfDestroyed'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_software_instance_allocated(self):
    instance = self.createSoftwareInstance()
    partition = self.createComputerPartition()
    instance.edit(aggregate_value=partition)
    self.portal.portal_workflow._jumpToStateFor(instance, 'validated')
    self.portal.portal_workflow._jumpToStateFor(instance, 'destroy_requested')
    self.tic()

    self._simulateSoftwareInstance_tryToInvalidateIfDestroyed()
    try:
      self.portal.portal_alarms.slapos_cloud_invalidate_destroyed_instance.\
          activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_tryToInvalidateIfDestroyed()
    self.assertNotEqual(
        'Visited by SoftwareInstance_tryToInvalidateIfDestroyed',
        instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_software_instance_invalidated(self):
    instance = self.createSoftwareInstance()
    partition = self.createComputerPartition()
    self.portal.portal_workflow._jumpToStateFor(instance, 'invalidated')
    self.portal.portal_workflow._jumpToStateFor(instance, 'destroy_requested')
    self.tic()

    self._simulateSoftwareInstance_tryToInvalidateIfDestroyed()
    try:
      self.portal.portal_alarms.slapos_cloud_invalidate_destroyed_instance.\
          activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_tryToInvalidateIfDestroyed()
    self.assertNotEqual(
        'Visited by SoftwareInstance_tryToInvalidateIfDestroyed',
        instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_software_instance_matching(self):
    instance = self.createSoftwareInstance()
    partition = self.createComputerPartition()
    self.portal.portal_workflow._jumpToStateFor(instance, 'validated')
    self.portal.portal_workflow._jumpToStateFor(instance, 'destroy_requested')
    self.tic()

    self._simulateSoftwareInstance_tryToInvalidateIfDestroyed()
    try:
      self.portal.portal_alarms.slapos_cloud_invalidate_destroyed_instance.\
          activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_tryToInvalidateIfDestroyed()
    self.assertEqual(
        'Visited by SoftwareInstance_tryToInvalidateIfDestroyed',
        instance.workflow_history['edit_workflow'][-1]['comment'])
