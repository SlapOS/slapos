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
