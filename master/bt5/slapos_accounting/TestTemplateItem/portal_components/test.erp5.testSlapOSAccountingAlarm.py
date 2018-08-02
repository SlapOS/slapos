# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

import transaction
from functools import wraps
from Products.ERP5Type.tests.utils import createZODBPythonScript
from erp5.component.test.SlapOSTestCaseMixin import SlapOSTestCaseMixin, withAbort

import os
import tempfile
from DateTime import DateTime
from Products.ERP5Type.DateUtils import addToDate, getClosestDate
from zExceptions import Unauthorized

class Simulator:
  def __init__(self, outfile, method, to_return=None):
    self.outfile = outfile
    open(self.outfile, 'w').write(repr([]))
    self.method = method
    self.to_return = to_return

  def __call__(self, *args, **kwargs):
    """Simulation Method"""
    old = open(self.outfile, 'r').read()
    if old:
      l = eval(old)
    else:
      l = []
    l.append({'recmethod': self.method,
      'recargs': args,
      'reckwargs': kwargs})
    open(self.outfile, 'w').write(repr(l))
    return self.to_return

def simulateByEditWorkflowMark(script_name):
  def wrapper(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
      if script_name in self.portal.portal_skins.custom.objectIds():
        raise ValueError('Precondition failed: %s exists in custom' % script_name)
      createZODBPythonScript(self.portal.portal_skins.custom,
                          script_name,
                          '*args, **kwargs',
                          '# Script body\n'
  """context.portal_workflow.doActionFor(context, action='edit_action', comment='Visited by %s') """ % script_name )
      transaction.commit()
      try:
        result = func(self, *args, **kwargs)
      finally:
        if script_name in self.portal.portal_skins.custom.objectIds():
          self.portal.portal_skins.custom.manage_delObjects(script_name)
        transaction.commit()
      return result
    return wrapped
  return wrapper

def simulateByTitlewMark(script_name):
  def wrapper(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
      if script_name in self.portal.portal_skins.custom.objectIds():
        raise ValueError('Precondition failed: %s exists in custom' % script_name)
      createZODBPythonScript(self.portal.portal_skins.custom,
                          script_name,
                          '*args, **kwargs',
                          '# Script body\n'
"""
if context.getTitle() == 'Not visited by %s':
  context.setTitle('Visited by %s')
""" %(script_name, script_name))
      transaction.commit()
      try:
        result = func(self, *args, **kwargs)
      finally:
        if script_name in self.portal.portal_skins.custom.objectIds():
          self.portal.portal_skins.custom.manage_delObjects(script_name)
        transaction.commit()
      return result
    return wrapped
  return wrapper

class TestOpenSaleOrderAlarm(SlapOSTestCaseMixin):
  def test_noOSO_newPerson(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()

    self.assertEqual(None, self.portal.portal_catalog.getResultValue(
        portal_type='Open Sale Order',
        default_destination_uid=person.getUid()
    ))

  def test_noOSO_after_fixConsistency(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()
    person.fixConsistency()
    self.tic()

    self.assertEqual(None, self.portal.portal_catalog.getResultValue(
        portal_type='Open Sale Order',
        default_destination_uid=person.getUid()
    ))

  def test_OSO_after_Person_updateOpenSaleOrder(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()

    person.Person_storeOpenSaleOrderJournal()
    self.tic()

    open_sale_order_list = self.portal.portal_catalog(
        validation_state='validated',
        portal_type='Open Sale Order',
        default_destination_uid=person.getUid()
    )
    # No need to create any open order without hosting subscription
    self.assertEqual(0, len(open_sale_order_list))

  @simulateByEditWorkflowMark('HostingSubscription_requestUpdateOpenSaleOrder')
  def test_alarm_HS_diverged(self):
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(reference='TESTHS-%s' % self.generateNewId())
    self.tic()

    self.portal.portal_alarms\
        .slapos_request_update_hosting_subscription_open_sale_order\
        .activeSense()
    self.tic()
    self.assertEqual(
        'Visited by HostingSubscription_requestUpdateOpenSaleOrder',
        subscription.workflow_history['edit_workflow'][-1]['comment'])

class TestHostingSubscription_requestUpdateOpenSaleOrder(SlapOSTestCaseMixin):
  def test_REQUEST_disallowed(self):
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    self.assertRaises(
      Unauthorized,
      subscription.HostingSubscription_requestUpdateOpenSaleOrder,
      REQUEST={})

  def test_solved_HostingSubscription(self):
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    self.portal.portal_workflow._jumpToStateFor(subscription, 'solved')
    subscription.HostingSubscription_requestUpdateOpenSaleOrder()
    self.assertEqual(subscription.getCausalityState(), 'solved')

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
    self.assertEqual(subscription.getCausalityState(), 'solved')

    open_sale_order_list = self.portal.portal_catalog(
        portal_type='Open Sale Order',
        default_destination_uid=person.getUid()
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
    self.assertEqual(open_sale_order_line_template.getQuantity(),
        line.getQuantity())
    self.assertEqual(open_sale_order_line_template.getPrice(),
        line.getPrice())
    self.assertEqual(DateTime().earliestTime(), line.getStartDate())
    self.assertEqual(min(DateTime().day(), 28),
                     subscription.getPeriodicityMonthDay())
    start_date = addToDate(line.getStartDate(), to_add={'month': 1})
    start_date = addToDate(start_date, to_add={'second': -1})
    while start_date.day() >= 28:
      start_date = addToDate(start_date, to_add={'day': -1})
    self.assertEqual(start_date, line.getStopDate())

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
    subscription.workflow_history['instance_slap_interface_workflow'] = [{
        'comment':'Simulated request instance',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'start_requested',
        'time': request_time,
        'action': 'request_instance'
    }]
    subscription.edit(periodicity_month_day_list=[])
    subscription.fixConsistency()
    self.assertEqual(subscription.getPeriodicityMonthDay(), 1)
    self.tic()

    subscription.HostingSubscription_requestUpdateOpenSaleOrder()
    self.tic()
    self.assertEqual(subscription.getCausalityState(), 'solved')

    open_sale_order_list = self.portal.portal_catalog(
        portal_type='Open Sale Order',
        default_destination_uid=person.getUid()
    )

    self.assertEqual(1, len(open_sale_order_list))
    open_sale_order = open_sale_order_list[0].getObject()
    self.assertEqual('validated', open_sale_order.getValidationState())

    open_sale_order_line_list = open_sale_order.contentValues(
        portal_type='Open Sale Order Line')

    self.assertEqual(1, len(open_sale_order_line_list))
    line = open_sale_order_line_list[0].getObject()

    # calculate stop date to be after now, begin with start date with precision
    # of month
    now = DateTime()
    now = now.toZone(request_time.timezone())
    stop_date = getClosestDate(target_date=now, precision='month')
    stop_date = addToDate(stop_date, to_add={'second': -1})
    self.assertEqual(stop_date, line.getStopDate())

    self.assertEqual(subscription.getRelativeUrl(), line.getAggregate())
    open_sale_order_line_template = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredOpenSaleOrderLineTemplate())
    self.assertTrue(all([q in line.getCategoryList() \
        for q in open_sale_order_line_template.getCategoryList()]))
    self.assertEqual(open_sale_order_line_template.getResource(),
        line.getResource())
    self.assertEqual(open_sale_order_line_template.getQuantity(),
        line.getQuantity())
    self.assertEqual(open_sale_order_line_template.getPrice(),
        line.getPrice())
    self.assertEqual(request_time, line.getStartDate())
    self.assertEqual(stop_date, line.getStopDate())

    destroy_time = DateTime('2112/02/01')
    subscription.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Simulated request instance',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'destroy_requested',
        'time': destroy_time,
        'action': 'request_destroy'
    })
    subscription.diverge()
    self.tic()

    subscription.HostingSubscription_requestUpdateOpenSaleOrder()
    self.tic()
    self.assertEqual(subscription.getCausalityState(), 'solved')

    open_sale_order_list = self.portal.portal_catalog(
        portal_type='Open Sale Order',
        default_destination_uid=person.getUid()
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
    self.assertEqual(open_sale_order_line_template.getQuantity(),
        line.getQuantity())
    self.assertEqual(open_sale_order_line_template.getPrice(),
        line.getPrice())
    self.assertEqual(request_time, archived_line.getStartDate())
    self.assertEqual(DateTime('2112/02/02'), line.getStopDate())

  def test_lateAnalysed_HostingSubscription(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(reference='TESTHS-%s' % self.generateNewId(),
        title='Test Title %s' % self.generateNewId(),
        destination_section=person.getRelativeUrl())
    self.portal.portal_workflow._jumpToStateFor(subscription, 'validated')

    subscription.workflow_history['instance_slap_interface_workflow'] = []
    request_time = DateTime('2012/01/01')
    subscription.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Simulated request instance',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'start_requested',
        'time': request_time,
        'action': 'request_instance'
    })

    destroy_time = DateTime('2012/02/01')
    subscription.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Simulated request instance',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'destroy_requested',
        'time': destroy_time,
        'action': 'request_destroy'
    })
    subscription.edit(periodicity_month_day_list=[])
    subscription.fixConsistency()
    self.tic()

    subscription.HostingSubscription_requestUpdateOpenSaleOrder()
    self.tic()
    self.assertEqual(subscription.getCausalityState(), 'solved')

    open_sale_order_list = self.portal.portal_catalog(
        portal_type='Open Sale Order',
        default_destination_uid=person.getUid()
    )

    self.assertEqual(2, len(open_sale_order_list))
    open_sale_order = [x for x in open_sale_order_list \
                       if x.getValidationState() != 'validated'][0].getObject()
    self.assertEqual('archived', open_sale_order.getValidationState())

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
    self.assertEqual(open_sale_order_line_template.getQuantity(),
        line.getQuantity())
    self.assertEqual(open_sale_order_line_template.getPrice(),
        line.getPrice())
    self.assertEqual(request_time, line.getStartDate())

    self.assertEqual(DateTime('2012/02/02'), line.getStopDate())

    new_open_sale_order = [x for x in open_sale_order_list \
                           if x.getValidationState() == 'validated'][0].getObject()
    self.assertEqual('validated', new_open_sale_order.getValidationState())
    open_sale_order_line_list = new_open_sale_order.contentValues(
        portal_type='Open Sale Order Line')
    self.assertEqual(0, len(open_sale_order_line_list))

  def test_two_HostingSubscription(self):
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
    subscription.workflow_history['instance_slap_interface_workflow'] = [{
        'comment':'Simulated request instance',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'start_requested',
        'time': request_time,
        'action': 'request_instance'
    }]
    subscription.edit(periodicity_month_day_list=[])
    subscription.fixConsistency()
    self.tic()

    subscription.HostingSubscription_requestUpdateOpenSaleOrder()
    self.tic()

    open_sale_order_list = self.portal.portal_catalog(
        portal_type='Open Sale Order',
        default_destination_uid=person.getUid()
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
    self.assertEqual(open_sale_order_line_template.getQuantity(),
        line.getQuantity())
    self.assertEqual(open_sale_order_line_template.getPrice(),
        line.getPrice())
    self.assertEqual(request_time, line.getStartDate())

    # calculate stop date to be after now, begin with start date with precision
    # of month
    stop_date = request_time
    next_stop_date = stop_date
    now = DateTime()
    while next_stop_date < now:
      stop_date = next_stop_date
      next_stop_date = addToDate(stop_date, to_add={'month': 1})
    stop_date = addToDate(stop_date, to_add={'second': -1})
    self.assertEqual(stop_date, line.getStopDate())

    subscription2 = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription2.edit(reference='TESTHS-%s' % self.generateNewId(),
        title='Test Title %s' % self.generateNewId(),
        destination_section=person.getRelativeUrl())
    self.portal.portal_workflow._jumpToStateFor(subscription2, 'validated')

    request_time_2 = DateTime('2012/08/01')
    subscription2.workflow_history['instance_slap_interface_workflow'] = [{
        'comment':'Simulated request instance',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'start_requested',
        'time': request_time_2,
        'action': 'request_instance'
    }]
    subscription2.edit(periodicity_month_day_list=[])
    subscription2.fixConsistency()
    self.tic()

    subscription2.HostingSubscription_requestUpdateOpenSaleOrder()
    self.tic()

    open_sale_order_list = self.portal.portal_catalog(
        portal_type='Open Sale Order',
        default_destination_uid=person.getUid()
    )

    self.assertEqual(1, len(open_sale_order_list))
    validated_open_sale_order_list = [q for q in open_sale_order_list
        if q.getValidationState() == 'validated']
    archived_open_sale_order_list = [q for q in open_sale_order_list
        if q.getValidationState() == 'archived']
    self.assertEqual(1, len(validated_open_sale_order_list))
    self.assertEqual(0, len(archived_open_sale_order_list))
    validated_open_sale_order = validated_open_sale_order_list[0].getObject()

    validated_line_list = validated_open_sale_order.contentValues(
        portal_type='Open Sale Order Line')
    self.assertEqual(2, len(validated_line_list))

    self.assertEqual(open_sale_order_line_template.getQuantity(),
        line.getQuantity())
    self.assertEqual(open_sale_order_line_template.getPrice(),
        line.getPrice())

    stop_date_2 = request_time_2
    next_stop_date_2 = stop_date_2
    now = DateTime()
    while next_stop_date_2 < now:
      stop_date_2 = next_stop_date_2
      next_stop_date_2 = addToDate(stop_date_2, to_add={'month': 1})
    stop_date_2 = addToDate(stop_date_2, to_add={'second': -1})

    validated_line_1 = [q for q in validated_line_list if q.getAggregate() == \
        subscription.getRelativeUrl()][0]
    validated_line_2 = [q for q in validated_line_list if q.getAggregate() == \
        subscription2.getRelativeUrl()][0]

    self.assertTrue(all([q in validated_line_1.getCategoryList() \
        for q in open_sale_order_line_template.getCategoryList()]))
    self.assertEqual(open_sale_order_line_template.getResource(),
        validated_line_1.getResource())
    self.assertEqual(open_sale_order_line_template.getQuantity(),
        line.getQuantity())
    self.assertEqual(open_sale_order_line_template.getPrice(),
        line.getPrice())
    self.assertEqual(request_time, validated_line_1.getStartDate())
    self.assertEqual(stop_date, validated_line_1.getStopDate())

    self.assertTrue(all([q in validated_line_2.getCategoryList() \
        for q in open_sale_order_line_template.getCategoryList()]))
    self.assertEqual(open_sale_order_line_template.getResource(),
        validated_line_2.getResource())
    self.assertEqual(open_sale_order_line_template.getQuantity(),
        line.getQuantity())
    self.assertEqual(open_sale_order_line_template.getPrice(),
        line.getPrice())
    self.assertEqual(request_time_2, validated_line_2.getStartDate())
    self.assertEqual(stop_date_2, validated_line_2.getStopDate())

  def test_hosting_subscription_start_date_not_changed(self):
    # if there was no request_instance the getCreationDate has been used
    # but if request_instance appeared start_date is not changed
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

    request_time = DateTime('2112/01/01')
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
    self.assertEqual(subscription.getCausalityState(), 'solved')

    open_sale_order_list = self.portal.portal_catalog(
        portal_type='Open Sale Order',
        default_destination_uid=person.getUid()
    )

    self.assertEqual(1, len(open_sale_order_list))
    open_sale_order = open_sale_order_list[0].getObject()
    self.assertEqual('validated', open_sale_order.getValidationState())

    open_sale_order_line_list = open_sale_order.contentValues(
        portal_type='Open Sale Order Line')

    self.assertEqual(1, len(open_sale_order_line_list))
    line = open_sale_order_line_list[0].getObject()
    self.assertEqual(subscription.getCreationDate().earliestTime(),
                     line.getStartDate())

  def test_hosting_subscription_diverged_to_solve(self):
    # check that HS becomes solved even if not modification is needed on open
    # order
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(reference='TESTHS-%s' % self.generateNewId(),
        destination_section=person.getRelativeUrl())
    self.portal.portal_workflow._jumpToStateFor(subscription, 'validated')
    self.assertEqual(subscription.getCausalityState(), 'diverged')
    self.tic()

    subscription.HostingSubscription_requestUpdateOpenSaleOrder()
    self.tic()
    self.assertEqual(subscription.getCausalityState(), 'solved')

    self.portal.portal_workflow._jumpToStateFor(subscription, 'diverged')
    subscription.reindexObject()
    self.assertEqual(subscription.getCausalityState(), 'diverged')
    self.assertEqual(subscription.getSlapState(), 'draft')
    self.tic()

    subscription.HostingSubscription_requestUpdateOpenSaleOrder()
    self.tic()
    self.assertEqual(subscription.getCausalityState(), 'solved')

  def test_empty_destroyed_HostingSubscription(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()
    subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    subscription.edit(reference='TESTHS-%s' % self.generateNewId(),
        destination_section=person.getRelativeUrl())
    self.portal.portal_workflow._jumpToStateFor(subscription, 'validated')
    self.portal.portal_workflow._jumpToStateFor(subscription, 'destroy_requested')
    self.tic()

    subscription.HostingSubscription_requestUpdateOpenSaleOrder()
    self.tic()
    self.assertEqual(subscription.getCausalityState(), 'solved')

    open_sale_order_list = self.portal.portal_catalog(
        portal_type='Open Sale Order',
        default_destination_uid=person.getUid()
    )

    self.assertEqual(2,len(open_sale_order_list))
    open_sale_order = [x for x in open_sale_order_list \
                       if x.getValidationState() != 'validated'][0].getObject()
    self.assertEqual('archived', open_sale_order.getValidationState())

    open_sale_order_line_list = open_sale_order.contentValues(
        portal_type='Open Sale Order Line')

    self.assertEqual(1, len(open_sale_order_line_list))
    effective_date = open_sale_order.getEffectiveDate()
    line = open_sale_order_line_list[0].getObject()

    self.assertEqual(subscription.getRelativeUrl(), line.getAggregate())
    open_sale_order_line_template = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredOpenSaleOrderLineTemplate())
    self.assertEqual(open_sale_order_line_template.getResource(),
        line.getResource())
    self.assertTrue(all([q in line.getCategoryList() \
        for q in open_sale_order_line_template.getCategoryList()]))
    self.assertEqual(open_sale_order_line_template.getQuantity(),
        line.getQuantity())
    self.assertEqual(open_sale_order_line_template.getPrice(),
        line.getPrice())
    self.assertEqual(DateTime().earliestTime(), line.getStartDate())
    self.assertEqual(addToDate(line.getStartDate(), to_add={'day': 1}),
                     line.getStopDate())

    new_open_sale_order = [x for x in open_sale_order_list \
                           if x.getValidationState() == 'validated'][0].getObject()
    self.assertEqual('validated', new_open_sale_order.getValidationState())
    new_effective_date = new_open_sale_order.getEffectiveDate()
    open_sale_order_line_list = new_open_sale_order.contentValues(
        portal_type='Open Sale Order Line')
    self.assertEqual(0, len(open_sale_order_line_list))
    self.assertTrue(new_effective_date > effective_date,
                    "%s <= %s" % (new_effective_date, effective_date))

class TestSlapOSTriggerBuildAlarm(SlapOSTestCaseMixin):
  @simulateByTitlewMark('SimulationMovement_buildSlapOS')
  def test_SimulationMovement_withoutDelivery(self):
    applied_rule = self.portal.portal_simulation.newContent(
        portal_type='Applied Rule')
    simulation_movement = applied_rule.newContent(
        portal_type='Simulation Movement',
        title='Not visited by SimulationMovement_buildSlapOS')
    self.tic()

    self.portal.portal_alarms.slapos_trigger_build.activeSense()
    self.tic()

    self.assertEqual(
        'Visited by SimulationMovement_buildSlapOS',
        simulation_movement.getTitle())

  @simulateByTitlewMark('SimulationMovement_buildSlapOS')
  def test_SimulationMovement_withDelivery(self):
    delivery = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List')
    delivery_line = delivery.newContent(portal_type='Sale Packing List Line')
    applied_rule = self.portal.portal_simulation.newContent(
        portal_type='Applied Rule')
    simulation_movement = applied_rule.newContent(
        portal_type='Simulation Movement',
        delivery=delivery_line.getRelativeUrl(),
        title='Shall be visited by SimulationMovement_buildSlapOS')
    self.tic()

    self.portal.portal_alarms.slapos_trigger_build.activeSense()
    self.tic()

    self.assertNotEqual(
        'Not visited by SimulationMovement_buildSlapOS',
        simulation_movement.getTitle())

  @withAbort
  def test_SimulationMovement_buildSlapOS(self):
    build_simulator = tempfile.mkstemp()[1]
    activate_simulator = tempfile.mkstemp()[1]

    business_process = self.portal.business_process_module.newContent(
        portal_type='Business Process')
    root_business_link = business_process.newContent(
        portal_type='Business Link')
    business_link = business_process.newContent(portal_type='Business Link')

    root_applied_rule = self.portal.portal_simulation.newContent(
        portal_type='Applied Rule')
    simulation_movement = root_applied_rule.newContent(
        causality=root_business_link.getRelativeUrl(),
        portal_type='Simulation Movement')

    applied_rule = simulation_movement.newContent(portal_type='Applied Rule')
    lower_simulation_movement = applied_rule.newContent(
        causality=business_link.getRelativeUrl(),
        portal_type='Simulation Movement')

    try:
      from Products.CMFActivity.ActiveObject import ActiveObject
      ActiveObject.original_activate = ActiveObject.activate
      ActiveObject.activate = Simulator(activate_simulator, 'activate',
          root_applied_rule)
      from Products.ERP5.Document.BusinessLink import BusinessLink
      BusinessLink.original_build = BusinessLink.build
      BusinessLink.build = Simulator(build_simulator, 'build')

      simulation_movement.SimulationMovement_buildSlapOS(tag='root_tag')

      build_value = eval(open(build_simulator).read())
      activate_value = eval(open(activate_simulator).read())

      self.assertEqual([{
        'recmethod': 'build',
        'recargs': (),
        'reckwargs': {'path': '%s/%%' % root_applied_rule.getPath(),
        'activate_kw': {'tag': 'root_tag'}}}],
        build_value
      )
      self.assertEqual([{
        'recmethod': 'activate',
        'recargs': (),
        'reckwargs': {'tag': 'build_in_progress_%s_%s' % (
            root_business_link.getUid(), root_applied_rule.getUid()),
          'after_tag': 'root_tag', 'activity': 'SQLQueue'}}],
        activate_value)

      open(build_simulator, 'w').truncate()
      open(activate_simulator, 'w').truncate()

      lower_simulation_movement.SimulationMovement_buildSlapOS(tag='lower_tag')
      build_value = eval(open(build_simulator).read())
      activate_value = eval(open(activate_simulator).read())

      self.assertEqual([{
        'recmethod': 'build',
        'recargs': (),
        'reckwargs': {'path': '%s/%%' % root_applied_rule.getPath(),
        'activate_kw': {'tag': 'lower_tag'}}}],
        build_value
      )
      self.assertEqual([{
        'recmethod': 'activate',
        'recargs': (),
        'reckwargs': {'tag': 'build_in_progress_%s_%s' % (
            business_link.getUid(), root_applied_rule.getUid()),
          'after_tag': 'lower_tag', 'activity': 'SQLQueue'}}],
        activate_value)

    finally:
      ActiveObject.activate = ActiveObject.original_activate
      delattr(ActiveObject, 'original_activate')
      BusinessLink.build = BusinessLink.original_build
      delattr(BusinessLink, 'original_build')
      if os.path.exists(build_simulator):
        os.unlink(build_simulator)
      if os.path.exists(activate_simulator):
        os.unlink(activate_simulator)

  @withAbort
  def test_SimulationMovement_buildSlapOS_withDelivery(self):
    build_simulator = tempfile.mkstemp()[1]
    activate_simulator = tempfile.mkstemp()[1]

    delivery = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List')
    delivery_line = delivery.newContent(portal_type='Sale Packing List Line')
    business_process = self.portal.business_process_module.newContent(
        portal_type='Business Process')
    root_business_link = business_process.newContent(
        portal_type='Business Link')
    business_link = business_process.newContent(portal_type='Business Link')

    root_applied_rule = self.portal.portal_simulation.newContent(
        portal_type='Applied Rule')
    simulation_movement = root_applied_rule.newContent(
        causality=root_business_link.getRelativeUrl(),
        delivery=delivery_line.getRelativeUrl(),
        portal_type='Simulation Movement')

    applied_rule = simulation_movement.newContent(portal_type='Applied Rule')
    lower_simulation_movement = applied_rule.newContent(
        causality=business_link.getRelativeUrl(),
        delivery=delivery_line.getRelativeUrl(),
        portal_type='Simulation Movement')

    try:
      from Products.CMFActivity.ActiveObject import ActiveObject
      ActiveObject.original_activate = ActiveObject.activate
      ActiveObject.activate = Simulator(activate_simulator, 'activate',
          root_applied_rule)
      from Products.ERP5.Document.BusinessLink import BusinessLink
      BusinessLink.original_build = BusinessLink.build
      BusinessLink.build = Simulator(build_simulator, 'build')

      simulation_movement.SimulationMovement_buildSlapOS(tag='root_tag')

      build_value = eval(open(build_simulator).read())
      activate_value = eval(open(activate_simulator).read())

      self.assertEqual([], build_value)
      self.assertEqual([], activate_value)

      open(build_simulator, 'w').write(repr([]))
      open(activate_simulator, 'w').write(repr([]))

      lower_simulation_movement.SimulationMovement_buildSlapOS(tag='lower_tag')
      build_value = eval(open(build_simulator).read())
      activate_value = eval(open(activate_simulator).read())

      self.assertEqual([], build_value)
      self.assertEqual([], activate_value)

    finally:
      ActiveObject.activate = ActiveObject.original_activate
      delattr(ActiveObject, 'original_activate')
      BusinessLink.build = BusinessLink.original_build
      delattr(BusinessLink, 'original_build')
      if os.path.exists(build_simulator):
        os.unlink(build_simulator)
      if os.path.exists(activate_simulator):
        os.unlink(activate_simulator)

class TestSlapOSManageBuildingCalculatingDeliveryAlarm(SlapOSTestCaseMixin):
  @simulateByTitlewMark('Delivery_manageBuildingCalculatingDelivery')
  def _test(self, state, message):
    delivery = self.portal.sale_packing_list_module.newContent(
        title='Not visited by Delivery_manageBuildingCalculatingDelivery',
        portal_type='Sale Packing List')
    self.portal.portal_workflow._jumpToStateFor(delivery, state)
    self.tic()

    self.portal.portal_alarms.slapos_manage_building_calculating_delivery\
        .activeSense()
    self.tic()

    self.assertEqual(message, delivery.getTitle())

  def test_building(self):
    self._test('building', 'Visited by Delivery_manageBuildingCalculatingDelivery')

  def test_calculating(self):
    self._test('calculating', 'Visited by Delivery_manageBuildingCalculatingDelivery')

  def test_diverged(self):
    self._test('diverged', 'Not visited by Delivery_manageBuildingCalculatingDelivery')

  def test_solved(self):
    self._test('solved', 'Not visited by Delivery_manageBuildingCalculatingDelivery')

  @withAbort
  def _test_Delivery_manageBuildingCalculatingDelivery(self, state, empty=False):
    updateCausalityState_simulator = tempfile.mkstemp()[1]
    updateSimulation_simulator = tempfile.mkstemp()[1]

    delivery = self.portal.sale_packing_list_module.newContent(
        title='Not visited by Delivery_manageBuildingCalculatingDelivery',
        portal_type='Sale Packing List')
    self.portal.portal_workflow._jumpToStateFor(delivery, state)

    try:
      from Products.ERP5.Document.Delivery import Delivery
      Delivery.original_updateCausalityState = Delivery.updateCausalityState
      Delivery.original_updateSimulation = Delivery.updateSimulation
      Delivery.updateCausalityState = Simulator(
          updateCausalityState_simulator, 'updateCausalityState')
      Delivery.updateSimulation = Simulator(
          updateSimulation_simulator, 'updateSimulation')

      delivery.Delivery_manageBuildingCalculatingDelivery()

      updateCausalityState_value = eval(open(updateCausalityState_simulator).read())
      updateSimulation_value = eval(open(updateSimulation_simulator).read())

      if empty:
        self.assertEqual([], updateCausalityState_value)
        self.assertEqual([], updateSimulation_value)
      else:
        self.assertEqual([{
          'recmethod': 'updateCausalityState',
          'recargs': (),
          'reckwargs': {'solve_automatically': True}}],
          updateCausalityState_value
        )
        self.assertEqual([{
          'recmethod': 'updateSimulation',
          'recargs': (),
          'reckwargs': {'expand_root': 1, 'expand_related': 1}}],
          updateSimulation_value
        )
    finally:
      Delivery.updateCausalityState = Delivery.original_updateCausalityState
      Delivery.updateSimulation = Delivery.original_updateSimulation
      delattr(Delivery, 'original_updateCausalityState')
      delattr(Delivery, 'original_updateSimulation')
      if os.path.exists(updateCausalityState_simulator):
        os.unlink(updateCausalityState_simulator)
      if os.path.exists(updateSimulation_simulator):
        os.unlink(updateSimulation_simulator)

  def test_Delivery_manageBuildingCalculatingDelivery_calculating(self):
    self._test_Delivery_manageBuildingCalculatingDelivery('calculating')

  def test_Delivery_manageBuildingCalculatingDelivery_building(self):
    self._test_Delivery_manageBuildingCalculatingDelivery('building')

  def test_Delivery_manageBuildingCalculatingDelivery_solved(self):
    self._test_Delivery_manageBuildingCalculatingDelivery('solved', True)

  def test_Delivery_manageBuildingCalculatingDelivery_diverged(self):
    self._test_Delivery_manageBuildingCalculatingDelivery('diverged', True)

class TestSlapOSConfirmedDeliveryMixin:
  def _test(self, simulation_state, causality_state, specialise, positive,
      delivery_date=DateTime('2012/04/22'),
      accounting_date=DateTime('2012/04/28')):
    @simulateByTitlewMark(self.script)
    def _real(self, simulation_state, causality_state, specialise, positive,
          delivery_date,
          accounting_date):
      not_visited = 'Not visited by %s' % self.script
      visited = 'Visited by %s' % self.script
      module = self.portal.getDefaultModule(portal_type=self.portal_type)
      delivery = module.newContent(title=not_visited, start_date=delivery_date,
          portal_type=self.portal_type, specialise=specialise)
      _jumpToStateFor = self.portal.portal_workflow._jumpToStateFor
      _jumpToStateFor(delivery, simulation_state)
      _jumpToStateFor(delivery, causality_state)
      self.tic()

      alarm = getattr(self.portal.portal_alarms, self.alarm)
      alarm.activeSense(params=dict(accounting_date=accounting_date))
      self.tic()

      if positive:
        self.assertEqual(visited, delivery.getTitle())
      else:
        self.assertEqual(not_visited, delivery.getTitle())
    _real(self, simulation_state, causality_state, specialise, positive,
        delivery_date, accounting_date)

  def test_typical(self):
    self._test('confirmed', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition', True)

  def test_bad_specialise(self):
    self._test('confirmed', 'solved', None, False)

  def test_bad_simulation_state(self):
    self._test('started', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition', False)

  def test_bad_causality_state(self):
    self._test('confirmed', 'calculating',
        'sale_trade_condition_module/slapos_aggregated_trade_condition', False)

  @withAbort
  def _test_script(self, simulation_state, causality_state, specialise,
        destination_state, consistency_failure=False):
    module = self.portal.getDefaultModule(portal_type=self.portal_type)
    delivery = module.newContent(portal_type=self.portal_type,
        specialise=specialise, start_date=DateTime())
    _jumpToStateFor = self.portal.portal_workflow._jumpToStateFor
    _jumpToStateFor(delivery, simulation_state)
    _jumpToStateFor(delivery, causality_state)
    def checkConsistency(*args, **kwargs):
      if consistency_failure:
        return ['bad']
      else:
        return []
    try:
      from Products.ERP5Type.Core.Folder import Folder
      Folder.original_checkConsistency = Folder.checkConsistency
      Folder.checkConsistency = checkConsistency
      getattr(delivery, self.script)()
    finally:
      Folder.checkConsistency = Folder.original_checkConsistency
      delattr(Folder, 'original_checkConsistency')
    self.assertEqual(destination_state, delivery.getSimulationState())

  def test_script_typical(self):
    self._test_script('confirmed', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition',
        self.destination_state)

  def test_script_bad_specialise(self):
    self._test_script('confirmed', 'solved', None, 'confirmed')

  def test_script_bad_simulation_state(self):
    self._test_script('started', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition',
        'started')

  def test_script_bad_causality_state(self):
    self._test_script('confirmed', 'building',
        'sale_trade_condition_module/slapos_aggregated_trade_condition',
        'confirmed')

  def test_script_bad_consistency(self):
    self._test_script('confirmed', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition',
        'confirmed', True)

class TestSlapOSStartConfirmedAggregatedSalePackingListAlarm(
      SlapOSTestCaseMixin, TestSlapOSConfirmedDeliveryMixin):
  destination_state = 'started'
  script = 'Delivery_startConfirmedAggregatedSalePackingList'
  portal_type = 'Sale Packing List'
  alarm = 'slapos_start_confirmed_aggregated_sale_packing_list'

  def test_previous_month(self):
    self._test('confirmed', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition',
        True, delivery_date=DateTime("2012/03/22"),
        accounting_date=DateTime('2012/04/28'))

  def test_next_month(self):
    self._test('confirmed', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition',
        False, delivery_date=DateTime("2012/05/22"),
        accounting_date=DateTime('2012/04/28'))

  def test_same_month_early(self):
    self._test('confirmed', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition',
        False, delivery_date=DateTime("2012/04/22"),
        accounting_date=DateTime('2012/04/23'))

  def test_start_date_is_resetted(self):
    delivery = self.portal.sale_packing_list_module.newContent(
      portal_type="Sale Packing List",
      start_date=DateTime("2012/04/22"),
      specialise='sale_trade_condition_module/slapos_aggregated_trade_condition',
      source='organisation_module/slapos',
      source_section='organisation_module/slapos',
      destination='organisation_module/slapos',
      destination_section='organisation_module/slapos',
      destination_decision='organisation_module/slapos',
      price_currency='currency_module/EUR',
      )
    delivery.newContent(
      portal_type="Sale Packing List Line",
      resource='service_module/slapos_instance_setup',
      quantity=0,
      price=0,
      )
    self.portal.portal_workflow._jumpToStateFor(delivery, 'solved')
    self.portal.portal_workflow._jumpToStateFor(delivery, 'confirmed')
    delivery.Delivery_startConfirmedAggregatedSalePackingList()
    self.assertEquals(delivery.getStartDate(),
                      DateTime().earliestTime())
    self.assertEquals(delivery.getStopDate(),
                      DateTime().earliestTime())
    self.assertEquals(delivery.getSimulationState(), 'started')

class TestSlapOSDeliverStartedAggregatedSalePackingListAlarm(
      SlapOSTestCaseMixin):
  destination_state = 'delivered'
  script = 'Delivery_deliverStartedAggregatedSalePackingList'
  portal_type = 'Sale Packing List'
  alarm = 'slapos_deliver_started_aggregated_sale_packing_list'

  def _test(self, simulation_state, causality_state, specialise, positive,
      delivery_date=DateTime('2012/04/22'),
      accounting_date=DateTime('2012/04/28')):
    @simulateByTitlewMark(self.script)
    def _real(self, simulation_state, causality_state, specialise, positive,
          delivery_date,
          accounting_date):
      not_visited = 'Not visited by %s' % self.script
      visited = 'Visited by %s' % self.script
      module = self.portal.getDefaultModule(portal_type=self.portal_type)
      delivery = module.newContent(title=not_visited, start_date=delivery_date,
          portal_type=self.portal_type, specialise=specialise)
      _jumpToStateFor = self.portal.portal_workflow._jumpToStateFor
      _jumpToStateFor(delivery, simulation_state)
      _jumpToStateFor(delivery, causality_state)
      self.tic()

      alarm = getattr(self.portal.portal_alarms, self.alarm)
      alarm.activeSense(params=dict(accounting_date=accounting_date))
      self.tic()

      if positive:
        self.assertEqual(visited, delivery.getTitle())
      else:
        self.assertEqual(not_visited, delivery.getTitle())
    _real(self, simulation_state, causality_state, specialise, positive,
        delivery_date, accounting_date)

  def test_typical(self):
    self._test('started', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition', True)

  def test_bad_specialise(self):
    self._test('started', 'solved', None, False)

  def test_bad_simulation_state(self):
    self._test('confirmed', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition', False)

  def test_bad_causality_state(self):
    self._test('started', 'calculating',
        'sale_trade_condition_module/slapos_aggregated_trade_condition', False)

  @withAbort
  def _test_script(self, simulation_state, causality_state, specialise,
        destination_state, consistency_failure=False):
    module = self.portal.getDefaultModule(portal_type=self.portal_type)
    delivery = module.newContent(portal_type=self.portal_type,
        specialise=specialise, start_date=DateTime())
    _jumpToStateFor = self.portal.portal_workflow._jumpToStateFor
    _jumpToStateFor(delivery, simulation_state)
    _jumpToStateFor(delivery, causality_state)
    def checkConsistency(*args, **kwargs):
      if consistency_failure:
        return ['bad']
      else:
        return []
    try:
      from Products.ERP5Type.Core.Folder import Folder
      Folder.original_checkConsistency = Folder.checkConsistency
      Folder.checkConsistency = checkConsistency
      getattr(delivery, self.script)()
    finally:
      Folder.checkConsistency = Folder.original_checkConsistency
      delattr(Folder, 'original_checkConsistency')
    self.assertEqual(destination_state, delivery.getSimulationState())

  def test_script_typical(self):
    self._test_script('started', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition',
        self.destination_state)

  def test_script_bad_specialise(self):
    self._test_script('started', 'solved', None, 'started')

  def test_script_bad_simulation_state(self):
    self._test_script('confirmed', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition',
        'confirmed')

  def test_script_bad_causality_state(self):
    self._test_script('started', 'building',
        'sale_trade_condition_module/slapos_aggregated_trade_condition',
        'started')

  def test_script_bad_consistency(self):
    self._test_script('started', 'solved',
        'sale_trade_condition_module/slapos_aggregated_trade_condition',
        'started', True)

class TestSlapOSStopConfirmedAggregatedSaleInvoiceTransactionAlarm(
      SlapOSTestCaseMixin, TestSlapOSConfirmedDeliveryMixin):
  destination_state = 'stopped'
  script = 'Delivery_stopConfirmedAggregatedSaleInvoiceTransaction'
  portal_type = 'Sale Invoice Transaction'
  alarm = 'slapos_stop_confirmed_aggregated_sale_invoice_transaction'

class TestSlapOSUpdateOpenSaleOrderPeriod(SlapOSTestCaseMixin):

  def createOpenOrder(self):
    open_order = self.portal.open_sale_order_module\
        .slapos_accounting_open_sale_order_template.Base_createCloneDocument(batch_mode=1)
    open_order.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTHS-%s" % self.generateNewId(),
    )
    open_order.order()
    open_order.validate()
    return open_order

  def test_updatePeriod_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.OpenSaleOrder_updatePeriod,
      REQUEST={})

  def _simulatePerson_storeOpenSaleOrderJournal(self):
    script_name = 'Person_storeOpenSaleOrderJournal'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Person_storeOpenSaleOrderJournal') """ )
    transaction.commit()

  def _dropPerson_storeOpenSaleOrderJournal(self):
    script_name = 'Person_storeOpenSaleOrderJournal'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_updatePeriod_no_person(self):
    open_order = self.createOpenOrder()
    open_order.OpenSaleOrder_updatePeriod()

  def test_updatePeriod_validated(self):
    open_order = self.createOpenOrder()
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    open_order.edit(
      destination_decision_value=person,
    )

    self._simulatePerson_storeOpenSaleOrderJournal()
    try:
      open_order.OpenSaleOrder_updatePeriod()
    finally:
      self._dropPerson_storeOpenSaleOrderJournal()
    self.assertEqual(
        'Visited by Person_storeOpenSaleOrderJournal',
        person.workflow_history['edit_workflow'][-1]['comment'])

  def test_updatePeriod_invalidated(self):
    open_order = self.createOpenOrder()
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    open_order.edit(
      destination_decision_value=person,
    )
    open_order.invalidate()

    self._simulatePerson_storeOpenSaleOrderJournal()
    try:
      open_order.OpenSaleOrder_updatePeriod()
    finally:
      self._dropPerson_storeOpenSaleOrderJournal()
    self.assertNotEqual(
        'Visited by Person_storeOpenSaleOrderJournal',
        person.workflow_history['edit_workflow'][-1]['comment'])

  def _simulateOpenSaleOrder_updatePeriod(self):
    script_name = 'OpenSaleOrder_updatePeriod'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by OpenSaleOrder_updatePeriod') """ )
    transaction.commit()

  def _dropOpenSaleOrder_updatePeriod(self):
    script_name = 'OpenSaleOrder_updatePeriod'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm(self):
    open_order = self.createOpenOrder()
    open_order.newContent(portal_type="Open Sale Order Line")
    self.tic()
    self._simulateOpenSaleOrder_updatePeriod()
    try:
      self.portal.portal_alarms.slapos_update_open_sale_order_period.activeSense()
      self.tic()
    finally:
      self._dropOpenSaleOrder_updatePeriod()
    self.assertEqual(
        'Visited by OpenSaleOrder_updatePeriod',
        open_order.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_invalidated(self):
    open_order = self.createOpenOrder()
    open_order.newContent(portal_type="Open Sale Order Line")
    open_order.invalidate()
    self.tic()
    self._simulateOpenSaleOrder_updatePeriod()
    try:
      self.portal.portal_alarms.slapos_update_open_sale_order_period.activeSense()
      self.tic()
    finally:
      self._dropOpenSaleOrder_updatePeriod()
    self.assertNotEqual(
        'Visited by OpenSaleOrder_updatePeriod',
        open_order.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_no_line(self):
    open_order = self.createOpenOrder()
    self.tic()
    self._simulateOpenSaleOrder_updatePeriod()
    try:
      self.portal.portal_alarms.slapos_update_open_sale_order_period.activeSense()
      self.tic()
    finally:
      self._dropOpenSaleOrder_updatePeriod()
    self.assertNotEqual(
        'Visited by OpenSaleOrder_updatePeriod',
        open_order.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSReindexOpenSaleOrder(SlapOSTestCaseMixin):

  def createOpenOrder(self):
    open_order = self.portal.open_sale_order_module\
        .slapos_accounting_open_sale_order_template.\
          Base_createCloneDocument(batch_mode=1)
    open_order.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTHS-%s" % self.generateNewId(),
    )
    return open_order

  def _simulateOpenSaleOrder_reindexIfIndexedBeforeLine(self):
    script_name = 'OpenSaleOrder_reindexIfIndexedBeforeLine'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by OpenSaleOrder_reindexIfIndexedBeforeLine') """ )
    transaction.commit()

  def _dropOpenSaleOrder_reindexIfIndexedBeforeLine(self):
    script_name = 'OpenSaleOrder_reindexIfIndexedBeforeLine'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm(self):
    open_order = self.createOpenOrder()
    open_order.newContent(portal_type="Open Sale Order Line")
    self.tic()
    self._simulateOpenSaleOrder_reindexIfIndexedBeforeLine()
    try:
      self.portal.portal_alarms.slapos_reindex_open_sale_order.activeSense()
      self.tic()
    finally:
      self._dropOpenSaleOrder_reindexIfIndexedBeforeLine()
    self.assertEqual(
        'Visited by OpenSaleOrder_reindexIfIndexedBeforeLine',
        open_order.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_no_line(self):
    open_order = self.createOpenOrder()
    self.tic()
    self._simulateOpenSaleOrder_reindexIfIndexedBeforeLine()
    try:
      self.portal.portal_alarms.slapos_reindex_open_sale_order.activeSense()
      self.tic()
    finally:
      self._dropOpenSaleOrder_reindexIfIndexedBeforeLine()
    self.assertNotEqual(
        'Visited by OpenSaleOrder_reindexIfIndexedBeforeLine',
        open_order.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSGeneratePackingListFromTioXML(SlapOSTestCaseMixin):

  def createTioXMLFile(self):
    document = self.portal.consumption_document_module.newContent(
      title=self.generateNewId(),
      reference="TESTTIOCONS-%s" % self.generateNewId(),
    )
    return document

  def _simulateComputerConsumptionTioXMLFile_solveInvoicingGeneration(self):
    script_name = 'ComputerConsumptionTioXMLFile_solveInvoicingGeneration'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by ComputerConsumptionTioXMLFile_solveInvoicingGeneration') """ )
    transaction.commit()

  def _dropComputerConsumptionTioXMLFile_solveInvoicingGeneration(self):
    script_name = 'ComputerConsumptionTioXMLFile_solveInvoicingGeneration'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm(self):
    document = self.createTioXMLFile()
    document.submit()
    self.tic()
    self._simulateComputerConsumptionTioXMLFile_solveInvoicingGeneration()
    try:
      self.portal.portal_alarms.\
        slapos_accounting_generate_packing_list_from_tioxml.activeSense()
      self.tic()
    finally:
      self._dropComputerConsumptionTioXMLFile_solveInvoicingGeneration()
    self.assertEqual(
        'Visited by ComputerConsumptionTioXMLFile_solveInvoicingGeneration',
        document.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_submitted(self):
    document = self.createTioXMLFile()
    self.tic()
    self._simulateComputerConsumptionTioXMLFile_solveInvoicingGeneration()
    try:
      self.portal.portal_alarms.\
        slapos_accounting_generate_packing_list_from_tioxml.activeSense()
      self.tic()
    finally:
      self._dropComputerConsumptionTioXMLFile_solveInvoicingGeneration()
    self.assertNotEqual(
        'Visited by ComputerConsumptionTioXMLFile_solveInvoicingGeneration',
        document.workflow_history['edit_workflow'][-1]['comment'])
