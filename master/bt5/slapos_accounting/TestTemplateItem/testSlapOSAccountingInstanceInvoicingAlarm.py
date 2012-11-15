# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

import transaction
import functools
from Products.ERP5Type.tests.utils import createZODBPythonScript
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from DateTime import DateTime

def simulateInstance_solveInvoicingGeneration(func):
  @functools.wraps(func)
  def wrapped(self, *args, **kwargs):
    script_name = 'Instance_solveInvoicingGeneration'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Instance_solveInvoicingGeneration') """ )
    transaction.commit()
    try:
      func(self, *args, **kwargs)
    finally:
      if script_name in self.portal.portal_skins.custom.objectIds():
        self.portal.portal_skins.custom.manage_delObjects(script_name)
      transaction.commit()
  return wrapped

class TestInstanceInvoicingAlarm(testSlapOSMixin):
  def afterSetUp(self):
    super(TestInstanceInvoicingAlarm, self).afterSetUp()

    self.software_instance_request_kw = dict(
      software_release=self.generateNewSoftwareReleaseUrl(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
    )

    self.slave_instance_request_kw = dict(
      software_release=self.generateNewSoftwareReleaseUrl(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=True,
    )

  def beforeTearDown(self):
    transaction.abort()

  def test_noSaleOrderPackingList_newSoftwareInstance(self):
    """
    Be sure no delivery is created synchronously (break old code behaviour)
    """
    instance = self.portal.software_instance_module.template_software_instance\
        .Base_createCloneDocument(batch_mode=1)
    instance.edit(title="TESTSI-%s" % self.generateNewId())
    instance.requestStart(**self.software_instance_request_kw)

    self.assertEqual(None, instance.getCausalityValue())

  def test_noSaleOrderPackingList_newSlaveInstance(self):
    """
    Be sure no delivery is created synchronously (break old code behaviour)
    """
    instance = self.portal.software_instance_module.template_slave_instance\
        .Base_createCloneDocument(batch_mode=1)
    instance.edit(title="TESTSI-%s" % self.generateNewId())
    instance.requestStart(**self.slave_instance_request_kw)
    self.tic()

    self.assertEqual(None, instance.getCausalityValue())

  @simulateInstance_solveInvoicingGeneration
  def test_alarm_findSoftwareInstance(self):
    new_id = self.generateNewId()
    instance = self.portal.software_instance_module.newContent(
      portal_type='Software Instance',
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      ssl_certificate="foo",
      ssl_key="bar",
      )

    self.tic()

    self.portal.portal_alarms\
        .slapos_instance_invoicing\
        .activeSense()
    self.tic()
    self.assertEqual(
        'Visited by Instance_solveInvoicingGeneration',
        instance.workflow_history['edit_workflow'][-1]['comment'])

  @simulateInstance_solveInvoicingGeneration
  def test_alarm_findSlaveInstance(self):
    new_id = self.generateNewId()
    instance = self.portal.software_instance_module.newContent(
      portal_type='Slave Instance',
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      )

    self.tic()

    self.portal.portal_alarms\
        .slapos_instance_invoicing\
        .activeSense()
    self.tic()
    self.assertEqual(
        'Visited by Instance_solveInvoicingGeneration',
        instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_solved_instance(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    instance = self.portal.software_instance_module\
        .template_slave_instance.Base_createCloneDocument(batch_mode=1)
    new_id = self.generateNewId()
    instance.edit(
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
    )

    request_time = DateTime('2012/01/01')
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Simulated request instance',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'destroyed',
        'time': request_time,
        'action': 'request_instance'
    })
    self.portal.portal_workflow._jumpToStateFor(instance, 'solved')

    instance.Instance_solveInvoicingGeneration()
    self.assertEqual(instance.getCausalityState(), 'solved')
    self.assertEqual(None, instance.getCausalityValue())

  def test_instance_in_draft_state(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    instance = self.portal.software_instance_module\
        .template_slave_instance.Base_createCloneDocument(batch_mode=1)
    new_id = self.generateNewId()
    instance.edit(
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
    )
    self.portal.portal_workflow._jumpToStateFor(instance, 'diverged')
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Stay in draft',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'draft',
        'time': DateTime(),
        'action': 'foo_transition'
    })

    instance.Instance_solveInvoicingGeneration()
    self.assertEqual(instance.getCausalityState(), 'solved')
    self.assertEqual(None, instance.getCausalityValue())

  def test_instance_in_unknown_state(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    instance = self.portal.software_instance_module\
        .template_slave_instance.Base_createCloneDocument(batch_mode=1)
    new_id = self.generateNewId()
    instance.edit(
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
    )
    self.portal.portal_workflow._jumpToStateFor(instance, 'diverged')
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Stay in unknown state',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'unknown_state',
        'time': DateTime(),
        'action': 'foo_transition'
    })

    self.assertRaises(AssertionError, instance.Instance_solveInvoicingGeneration) 

  def test_instance_in_early_destroyed_state(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(
      reference='TESTHS-%s' % self.generateNewId(),
      destination_section_value=person)
    instance = self.portal.software_instance_module\
        .template_slave_instance.Base_createCloneDocument(batch_mode=1)
    new_id = self.generateNewId()
    instance.edit(
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      specialise_value=subscription,
    )
    self.portal.portal_workflow._jumpToStateFor(instance, 'diverged')
    start_date = instance.workflow_history\
      ['instance_slap_interface_workflow'][0]['time']
    stop_date = DateTime('2222/11/15')
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Directly in destroyed state',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'destroy_requested',
        'time': stop_date,
        'action': 'foo_transition'
    })

    instance.Instance_solveInvoicingGeneration()
    self.assertEqual(instance.getCausalityState(), 'solved')
    self.assertNotEqual(None, instance.getCausalityValue())
    self.assertEqual(2, instance.getInvoicingSynchronizationPointer())
    delivery = instance.getCausalityValue()

    setup_line, update_line, destroy_line =\
      self.check_instance_delivery(delivery, start_date, stop_date, person, 2)
    self.check_instance_movement(setup_line, instance, subscription, 1)
    self.check_instance_movement(destroy_line, instance, subscription, 1)

  def check_instance_delivery(self, delivery, start_date, stop_date, 
                              person, line_count):
    packing_list_line = delivery.contentValues(
      portal_type='Sale Packing List Line')
    self.assertEqual(len(packing_list_line), line_count)
    self.assertEqual(delivery.getDestinationValue(), person)
    self.assertEqual(delivery.getDestinationSectionValue(), person)
    self.assertEqual(delivery.getDestinationDecisionValue(), person)
    self.assertEqual(delivery.getStopDate(), stop_date)
    self.assertEqual(delivery.getStartDate(), start_date)
    self.assertEqual(delivery.getSimulationState(), 'delivered')
    self.assertEqual(delivery.getCausalityState(), 'building')

    # Hardcoded, but, no idea how to not make it...
    setup_line = ([None]+[x for x in packing_list_line \
      if x.getResource() == 'service_module/slapos_instance_setup'])[-1]
    destroy_line = ([None]+[x for x in packing_list_line \
      if x.getResource() == 'service_module/slapos_instance_cleanup'])[-1]
    update_line = ([None]+[x for x in packing_list_line \
      if x.getResource() == 'service_module/slapos_instance_update'])[-1]
    return setup_line, update_line, destroy_line

  def check_instance_movement(self, movement, instance, 
                              subscription, quantity):
    self.assertEqual(movement.getQuantity(), quantity)
    self.assertSameSet(movement.getAggregateValueList(),
                       [instance, subscription])
    self.assertEqual(len(movement.contentValues()), 0)

  def test_instance_create_non_destroyed_state(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(
      reference='TESTHS-%s' % self.generateNewId(),
      destination_section_value=person)
    instance = self.portal.software_instance_module\
        .template_slave_instance.Base_createCloneDocument(batch_mode=1)
    new_id = self.generateNewId()
    instance.edit(
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      specialise_value=subscription,
    )
    self.portal.portal_workflow._jumpToStateFor(instance, 'diverged')
    start_date = instance.workflow_history\
      ['instance_slap_interface_workflow'][0]['time']
    stop_date = DateTime('2222/11/15')
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Directly in start state',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'start_requested',
        'time': stop_date,
        'action': 'foo_transition'
    })

    instance.Instance_solveInvoicingGeneration()
    self.assertEqual(instance.getCausalityState(), 'solved')
    self.assertNotEqual(None, instance.getCausalityValue())
    self.assertEqual(2, instance.getInvoicingSynchronizationPointer())
    delivery = instance.getCausalityValue()

    setup_line, update_line, destroy_line =\
      self.check_instance_delivery(delivery, start_date, stop_date, person, 1)
    self.check_instance_movement(setup_line, instance, subscription, 1)

  def test_instance_create_non_destroyed_with_update_state(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(
      reference='TESTHS-%s' % self.generateNewId(),
      destination_section_value=person)
    instance = self.portal.software_instance_module\
        .template_slave_instance.Base_createCloneDocument(batch_mode=1)
    new_id = self.generateNewId()
    instance.edit(
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      specialise_value=subscription,
    )
    self.portal.portal_workflow._jumpToStateFor(instance, 'diverged')
    start_date = instance.workflow_history\
      ['instance_slap_interface_workflow'][0]['time']
    stop_date = DateTime('2222/11/15')
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Update',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'foo_state',
        'time': stop_date-1,
        'action': 'foo_transition'
    })
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Update',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'foo_state',
        'time': stop_date-2,
        'action': 'foo_transition'
    })
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Directly in start state',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'start_requested',
        'time': stop_date,
        'action': 'foo_transition'
    })

    instance.Instance_solveInvoicingGeneration()
    self.assertEqual(instance.getCausalityState(), 'solved')
    self.assertNotEqual(None, instance.getCausalityValue())
    self.assertEqual(4, instance.getInvoicingSynchronizationPointer())
    delivery = instance.getCausalityValue()

    setup_line, update_line, destroy_line =\
      self.check_instance_delivery(delivery, start_date, stop_date, person, 2)
    self.check_instance_movement(setup_line, instance, subscription, 1)
    self.check_instance_movement(update_line, instance, subscription, 2)

  def test_instance_create_destroyed_with_update_state(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(
      reference='TESTHS-%s' % self.generateNewId(),
      destination_section_value=person)
    instance = self.portal.software_instance_module\
        .template_slave_instance.Base_createCloneDocument(batch_mode=1)
    new_id = self.generateNewId()
    instance.edit(
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      specialise_value=subscription,
    )
    self.portal.portal_workflow._jumpToStateFor(instance, 'diverged')
    start_date = instance.workflow_history\
      ['instance_slap_interface_workflow'][0]['time']
    stop_date = DateTime('2222/11/15')
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Update',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'foo_state',
        'time': stop_date-1,
        'action': 'foo_transition'
    })
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Update',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'foo_state',
        'time': stop_date-2,
        'action': 'foo_transition'
    })
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Directly in destroy state',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'destroy_requested',
        'time': stop_date,
        'action': 'foo_transition'
    })

    instance.Instance_solveInvoicingGeneration()
    self.assertEqual(instance.getCausalityState(), 'solved')
    self.assertNotEqual(None, instance.getCausalityValue())
    self.assertEqual(4, instance.getInvoicingSynchronizationPointer())
    delivery = instance.getCausalityValue()

    setup_line, update_line, destroy_line =\
      self.check_instance_delivery(delivery, start_date, stop_date, person, 3)
    self.check_instance_movement(setup_line, instance, subscription, 1)
    self.check_instance_movement(update_line, instance, subscription, 1)
    self.check_instance_movement(destroy_line, instance, subscription, 1)

  def test_instance_update_non_destroyed_state(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(
      reference='TESTHS-%s' % self.generateNewId(),
      destination_section_value=person)
    instance = self.portal.software_instance_module\
        .template_slave_instance.Base_createCloneDocument(batch_mode=1)
    previous_delivery = self.portal.sale_packing_list_module.newContent(
      portal_type='Sale Packing List')
    new_id = self.generateNewId()
    instance.edit(
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      specialise_value=subscription,
      invoicing_synchronization_pointer=2,
      causality_value=previous_delivery,
    )
    self.portal.portal_workflow._jumpToStateFor(instance, 'diverged')
    stop_date = DateTime('2222/11/15')
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Update',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'foo_state',
        'time': stop_date-1,
        'action': 'foo_transition'
    })
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Update',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'foo_state',
        'time': stop_date-2,
        'action': 'foo_transition'
    })
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Directly in start state',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'start_requested',
        'time': stop_date,
        'action': 'foo_transition'
    })
    start_date = stop_date-1

    instance.Instance_solveInvoicingGeneration()
    self.assertEqual(instance.getCausalityState(), 'solved')
    self.assertNotEqual(None, instance.getCausalityValue())
    self.assertEqual(4, instance.getInvoicingSynchronizationPointer())
    delivery = instance.getCausalityValue()

    setup_line, update_line, destroy_line =\
      self.check_instance_delivery(delivery, start_date, stop_date, person, 1)
    self.check_instance_movement(update_line, instance, subscription, 2)

  def test_instance_update_destroyed_state(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(
      reference='TESTHS-%s' % self.generateNewId(),
      destination_section_value=person)
    instance = self.portal.software_instance_module\
        .template_slave_instance.Base_createCloneDocument(batch_mode=1)
    previous_delivery = self.portal.sale_packing_list_module.newContent(
      portal_type='Sale Packing List')
    new_id = self.generateNewId()
    instance.edit(
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      specialise_value=subscription,
      invoicing_synchronization_pointer=2,
      causality_value=previous_delivery,
    )
    self.portal.portal_workflow._jumpToStateFor(instance, 'diverged')
    stop_date = DateTime('2222/11/15')
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Update',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'foo_state',
        'time': stop_date-1,
        'action': 'foo_transition'
    })
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Update',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'foo_state',
        'time': stop_date-2,
        'action': 'foo_transition'
    })
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Directly in start state',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'destroy_requested',
        'time': stop_date,
        'action': 'foo_transition'
    })
    start_date = stop_date-1

    instance.Instance_solveInvoicingGeneration()
    self.assertEqual(instance.getCausalityState(), 'solved')
    self.assertNotEqual(None, instance.getCausalityValue())
    self.assertEqual(4, instance.getInvoicingSynchronizationPointer())
    delivery = instance.getCausalityValue()

    setup_line, update_line, destroy_line =\
      self.check_instance_delivery(delivery, start_date, stop_date, person, 2)
    self.check_instance_movement(update_line, instance, subscription, 1)
    self.check_instance_movement(destroy_line, instance, subscription, 1)

  def test_instance_update_already_destroyed(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(
      reference='TESTHS-%s' % self.generateNewId(),
      destination_section_value=person)
    instance = self.portal.software_instance_module\
        .template_slave_instance.Base_createCloneDocument(batch_mode=1)
    previous_delivery = self.portal.sale_packing_list_module.newContent(
      portal_type='Sale Packing List')
    new_id = self.generateNewId()
    instance.edit(
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      specialise_value=subscription,
      invoicing_synchronization_pointer=2,
      causality_value=previous_delivery,
    )
    self.portal.portal_workflow._jumpToStateFor(instance, 'diverged')
    stop_date = DateTime('2222/11/15')
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Update',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'destroy_requested',
        'time': stop_date-1,
        'action': 'foo_transition'
    })
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Update',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'destroy_requested',
        'time': stop_date-2,
        'action': 'foo_transition'
    })
    instance.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Directly in start state',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'destroy_requested',
        'time': stop_date,
        'action': 'foo_transition'
    })
    start_date = stop_date-1

    instance.Instance_solveInvoicingGeneration()
    self.assertEqual(instance.getCausalityState(), 'solved')
    self.assertNotEqual(None, instance.getCausalityValue())
    self.assertEqual(4, instance.getInvoicingSynchronizationPointer())
    delivery = instance.getCausalityValue()

    setup_line, update_line, destroy_line =\
      self.check_instance_delivery(delivery, start_date, stop_date, person, 1)
    self.check_instance_movement(update_line, instance, subscription, 2)
