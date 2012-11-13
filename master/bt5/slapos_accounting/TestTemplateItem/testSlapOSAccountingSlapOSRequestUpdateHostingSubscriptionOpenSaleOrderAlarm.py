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
from Products.ERP5Type.DateUtils import addToDate

def simulateHostingSubscription_requestUpdateOpenSaleOrder(func):
  @functools.wraps(func)
  def wrapped(self, *args, **kwargs):
    script_name = 'HostingSubscription_requestUpdateOpenSaleOrder'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by HostingSubscription_requestUpdateOpenSaleOrder') """ )
    transaction.commit()
    try:
      func(self, *args, **kwargs)
    finally:
      if script_name in self.portal.portal_skins.custom.objectIds():
        self.portal.portal_skins.custom.manage_delObjects(script_name)
      transaction.commit()
  return wrapped

class TestOpenSaleOrderAlarm(testSlapOSMixin):
  def test_noOSO_newPerson(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()

    self.assertEqual(None, self.portal.portal_catalog.getResultValue(
        portal_type='Open Sale Order',
        default_destination_section_uid=person.getUid()
    ))

  def test_noOSO_after_fixConsistency(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()
    person.fixConsistency()
    self.tic()

    self.assertEqual(None, self.portal.portal_catalog.getResultValue(
        portal_type='Open Sale Order',
        default_destination_section_uid=person.getUid()
    ))

  def test_OSO_after_Person_updateOpenSaleOrder(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()

    person.Person_updateOpenSaleOrder()
    self.tic()

    open_sale_order_list = self.portal.portal_catalog(
        validation_state='validated',
        portal_type='Open Sale Order',
        default_destination_section_uid=person.getUid()
    )
    self.assertEqual(1, len(open_sale_order_list))
    open_sale_order = open_sale_order_list[0]

    self.assertEqual('SlapOS Subscription Open Sale Order',
        open_sale_order.getTitle())
    self.assertEqual(0, len(open_sale_order.contentValues()))
    open_sale_order_template = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredOpenSaleOrderTemplate())
    self.assertTrue(all([q in open_sale_order.getCategoryList() \
        for q in open_sale_order_template.getCategoryList()]))

  @simulateHostingSubscription_requestUpdateOpenSaleOrder
  def test_alarm_HS_validated(self):
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(reference='TESTHS-%s' % self.generateNewId())
    self.portal.portal_workflow._jumpToStateFor(subscription, 'validated')
    self.tic()

    self.portal.portal_alarms\
        .slapos_request_update_hosting_subscription_open_sale_order\
        .activeSense()
    self.tic()
    self.assertEqual(
        'Visited by HostingSubscription_requestUpdateOpenSaleOrder',
        subscription.workflow_history['edit_workflow'][-1]['comment'])

  @simulateHostingSubscription_requestUpdateOpenSaleOrder
  def test_alarm_HS_validated_OSO_invalidated(self):
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(reference='TESTHS-%s' % self.generateNewId())
    self.portal.portal_workflow._jumpToStateFor(subscription, 'validated')

    open_sale_order = self.portal.open_sale_order_module\
        .template_open_sale_order.Base_createCloneDocument(batch_mode=1)
    open_sale_order.edit(reference='TESTOSO-%s' % self.generateNewId())
    open_sale_order.newContent(portal_type='Open Sale Order Line',
        aggregate=subscription.getRelativeUrl())
    self.portal.portal_workflow._jumpToStateFor(open_sale_order, 'invalidated')
    self.tic()

    self.portal.portal_alarms\
        .slapos_request_update_hosting_subscription_open_sale_order\
        .activeSense()
    self.tic()
    self.assertEqual(
        'Visited by HostingSubscription_requestUpdateOpenSaleOrder',
        subscription.workflow_history['edit_workflow'][-1]['comment'])

  @simulateHostingSubscription_requestUpdateOpenSaleOrder
  def test_alarm_HS_archived(self):
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(reference='TESTHS-%s' % self.generateNewId())
    self.portal.portal_workflow._jumpToStateFor(subscription, 'archived')
    self.tic()

    self.portal.portal_alarms\
        .slapos_request_update_hosting_subscription_open_sale_order\
        .activeSense()
    self.tic()
    self.assertEqual(
        'Visited by HostingSubscription_requestUpdateOpenSaleOrder',
        subscription.workflow_history['edit_workflow'][-1]['comment'])

  @simulateHostingSubscription_requestUpdateOpenSaleOrder
  def test_alarm_HS_archived_OSO_validated(self):
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(reference='TESTHS-%s' % self.generateNewId())
    self.portal.portal_workflow._jumpToStateFor(subscription, 'archived')

    open_sale_order = self.portal.open_sale_order_module\
        .template_open_sale_order.Base_createCloneDocument(batch_mode=1)
    open_sale_order.edit(reference='TESTOSO-%s' % self.generateNewId())
    open_sale_order.newContent(portal_type='Open Sale Order Line',
        aggregate=subscription.getRelativeUrl())
    self.portal.portal_workflow._jumpToStateFor(open_sale_order, 'validated')
    self.tic()

    self.portal.portal_alarms\
        .slapos_request_update_hosting_subscription_open_sale_order\
        .activeSense()
    self.tic()
    self.assertEqual(
        'Visited by HostingSubscription_requestUpdateOpenSaleOrder',
        subscription.workflow_history['edit_workflow'][-1]['comment'])

  @simulateHostingSubscription_requestUpdateOpenSaleOrder
  def test_alarm_HS_validated_OSO_validated(self):
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(reference='TESTHS-%s' % self.generateNewId())
    self.portal.portal_workflow._jumpToStateFor(subscription, 'validated')

    open_sale_order = self.portal.open_sale_order_module\
        .template_open_sale_order.Base_createCloneDocument(batch_mode=1)
    open_sale_order.edit(reference='TESTOSO-%s' % self.generateNewId())
    open_sale_order.newContent(portal_type='Open Sale Order Line',
        aggregate=subscription.getRelativeUrl())
    self.portal.portal_workflow._jumpToStateFor(open_sale_order, 'validated')
    self.tic()

    self.portal.portal_alarms\
        .slapos_request_update_hosting_subscription_open_sale_order\
        .activeSense()
    self.tic()
    self.assertNotEqual(
        'Visited by HostingSubscription_requestUpdateOpenSaleOrder',
        subscription.workflow_history['edit_workflow'][-1]['comment'])

  @simulateHostingSubscription_requestUpdateOpenSaleOrder
  def test_alarm_HS_archived_OSO_invalidated(self):
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(reference='TESTHS-%s' % self.generateNewId())
    self.portal.portal_workflow._jumpToStateFor(subscription, 'archived')

    open_sale_order = self.portal.open_sale_order_module\
        .template_open_sale_order.Base_createCloneDocument(batch_mode=1)
    open_sale_order.edit(reference='TESTOSO-%s' % self.generateNewId())
    open_sale_order.newContent(portal_type='Open Sale Order Line',
        aggregate=subscription.getRelativeUrl())
    self.portal.portal_workflow._jumpToStateFor(open_sale_order, 'invalidated')
    self.tic()

    self.portal.portal_alarms\
        .slapos_request_update_hosting_subscription_open_sale_order\
        .activeSense()
    self.tic()
    self.assertNotEqual(
        'Visited by HostingSubscription_requestUpdateOpenSaleOrder',
        subscription.workflow_history['edit_workflow'][-1]['comment'])

class TestHostingSubscription_requestUpdateOpenSaleOrder(testSlapOSMixin):
  def test_empty_HostingSubscription(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(reference='TESTHS-%s' % self.generateNewId(),
        destination_section=person.getRelativeUrl())
    self.portal.portal_workflow._jumpToStateFor(subscription, 'validated')
    self.tic()

    subscription.HostingSubscription_requestUpdateOpenSaleOrder()
    self.tic()

    open_sale_order_list = self.portal.portal_catalog(
        portal_type='Open Sale Order',
        default_destination_section_uid=person.getUid()
    )

    self.assertEqual(1,len(open_sale_order_list))
    open_sale_order = open_sale_order_list[0].getObject()
    self.assertEqual('validated', open_sale_order.getValidationState())

    open_sale_order_line_list = open_sale_order.contentValues(
        portal_type='Open Sale Order Line')

    self.assertEqual(1, len(open_sale_order_line_list))
    line = open_sale_order_line_list[0].getObject()

    self.assertEqual(subscription.getRelativeUrl(), line.getAggregate())
    open_sale_order_line_template = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredOpenSaleOrderLineTemplate())
    self.assertEqual(open_sale_order_line_template.getResource(),
        line.getResource())
    self.assertTrue(all([q in line.getCategoryList() \
        for q in open_sale_order_line_template.getCategoryList()]))
    self.assertEqual(None, line.getStartDate())

  def test_usualLifetime_HostingSubscription(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(reference='TESTHS-%s' % self.generateNewId(),
        title='Test Title %s' % self.generateNewId(),
        destination_section=person.getRelativeUrl())
    self.portal.portal_workflow._jumpToStateFor(subscription, 'validated')

    request_time = DateTime('2012/01/01')
    subscription.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Simulated request instance',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'start_requested',
        'time': request_time,
        'action': 'request_instance'
    })
    self.tic()

    subscription.HostingSubscription_requestUpdateOpenSaleOrder()
    self.tic()

    open_sale_order_list = self.portal.portal_catalog(
        portal_type='Open Sale Order',
        default_destination_section_uid=person.getUid()
    )

    self.assertEqual(1, len(open_sale_order_list))
    open_sale_order = open_sale_order_list[0].getObject()
    self.assertEqual('validated', open_sale_order.getValidationState())

    open_sale_order_line_list = open_sale_order.contentValues(
        portal_type='Open Sale Order Line')

    self.assertEqual(1, len(open_sale_order_line_list))
    line = open_sale_order_line_list[0].getObject()

    self.assertEqual(subscription.getRelativeUrl(), line.getAggregate())
    open_sale_order_line_template = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredOpenSaleOrderLineTemplate())
    self.assertTrue(all([q in line.getCategoryList() \
        for q in open_sale_order_line_template.getCategoryList()]))
    self.assertEqual(open_sale_order_line_template.getResource(),
        line.getResource())
    self.assertEqual(request_time, line.getStartDate())

    destroy_time = DateTime('2012/02/01')
    subscription.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Simulated request instance',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'destroy_requested',
        'time': destroy_time,
        'action': 'request_destroy'
    })
    self.tic()

    subscription.HostingSubscription_requestUpdateOpenSaleOrder()
    self.tic()

    open_sale_order_list = self.portal.portal_catalog(
        portal_type='Open Sale Order',
        default_destination_section_uid=person.getUid()
    )

    self.assertEqual(2, len(open_sale_order_list))
    validated_open_sale_order_list = [q for q in open_sale_order_list
        if q.getValidationState() == 'validated']
    archived_open_sale_order_list = [q for q in open_sale_order_list
        if q.getValidationState() == 'archived']
    self.assertEqual(1, len(validated_open_sale_order_list))
    self.assertEqual(1, len(archived_open_sale_order_list))
    validated_open_sale_order = validated_open_sale_order_list[0].getObject()
    archived_open_sale_order = archived_open_sale_order_list[0]\
        .getObject()
    self.assertEqual(open_sale_order.getRelativeUrl(),
        archived_open_sale_order.getRelativeUrl())

    validated_line_list = validated_open_sale_order.contentValues(
        portal_type='Open Sale Order Line')
    archived_line_list = archived_open_sale_order.contentValues(
        portal_type='Open Sale Order Line')
    self.assertEqual(0, len(validated_line_list))
    self.assertEqual(1, len(archived_line_list))

    archived_line = archived_line_list[0].getObject()

    self.assertEqual(line.getRelativeUrl(), archived_line.getRelativeUrl())

    self.assertEqual(subscription.getRelativeUrl(),
        archived_line.getAggregate())
    self.assertTrue(all([q in archived_line.getCategoryList() \
        for q in open_sale_order_line_template.getCategoryList()]))
    self.assertEqual(open_sale_order_line_template.getResource(),
        archived_line.getResource())
    self.assertEqual(request_time, archived_line.getStartDate())

    # calculate stop date to be after now, begin with start date with precision
    # of month
    stop_date = request_time
    now = DateTime()
    while stop_date < now:
      stop_date = addToDate(stop_date, to_add={'month': 1})
    self.assertEqual(stop_date, archived_line.getStopDate())
