# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin, withAbort
from zExceptions import Unauthorized
from DateTime import DateTime
import time

class TestSlapOSAccounting(testSlapOSMixin):

  def createHostingSubscription(self):
    new_id = self.generateNewId()
    return self.portal.hosting_subscription_module.newContent(
      portal_type='Hosting Subscription',
      title="Subscription %s" % new_id,
      reference="TESTHS-%s" % new_id,
      )

  def createOpenSaleOrder(self):
    new_id = self.generateNewId()
    return self.portal.open_sale_order_module.newContent(
      portal_type='Open Sale Order',
      title="OpenSaleOrder %s" % new_id,
      reference="TESTOSO-%s" % new_id,
      )

  @withAbort
  def test_Service_getPriceCalculationOperandDict(self):
    service = self.portal.service_module.newContent(portal_type='Service')
    self.assertEqual({'price': 0.0},
        service.Service_getPriceCalculationOperandDict())

  @withAbort
  def test_HS_calculateSubscriptionStartDate_REQUEST_disallowed(self):
    item = self.createHostingSubscription()
    self.assertRaises(
      Unauthorized,
      item.HostingSubscription_calculateSubscriptionStartDate,
      REQUEST={})

  @withAbort
  def test_HS_calculateSubscriptionStartDate_noWorkflow(self):
    item = self.createHostingSubscription()
    item.workflow_history['instance_slap_interface_workflow'] = []
    date = item.HostingSubscription_calculateSubscriptionStartDate()
    self.assertEqual(date, item.getCreationDate().earliestTime())

  @withAbort
  def test_HS_calculateSubscriptionStartDate_withRequest(self):
    item = self.createHostingSubscription()
    item.workflow_history['instance_slap_interface_workflow'] = [{
        'comment':'Directly request the instance',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'draft',
        'time': DateTime('2012/11/15 11:11'),
        'action': 'request_instance'
        }]
    date = item.HostingSubscription_calculateSubscriptionStartDate()
    self.assertEqual(date, DateTime('2012/11/15'))

  @withAbort
  def test_HS_calculateSubscriptionStartDate_withRequestEndOfMonth(self):
    item = self.createHostingSubscription()
    item.workflow_history['instance_slap_interface_workflow'] = [{
        'comment':'Directly request the instance',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'draft',
        'time': DateTime('2012/11/30 11:11'),
        'action': 'request_instance'
    }]
    date = item.HostingSubscription_calculateSubscriptionStartDate()
    self.assertEqual(date, DateTime('2012/11/30'))

  @withAbort
  def test_HS_calculateSubscriptionStartDate_withRequestAfterDestroy(self):
    item = self.createHostingSubscription()
    destroy_date = DateTime('2012/10/30 11:11')
    request_date = DateTime('2012/11/30 11:11')
    item.workflow_history['instance_slap_interface_workflow'] = []
    item.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Directly destroy',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'destroy_requested',
        'time': destroy_date,
        'action': 'request_destroy'
    })
    item.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Directly request the instance',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'draft',
        'time': request_date,
        'action': 'request_instance'
    })
    date = item.HostingSubscription_calculateSubscriptionStartDate()
    self.assertEqual(date, DateTime('2012/10/30'))

  @withAbort
  def test_HS_calculateSubscriptionStopDate_REQUEST_disallowed(self):
    item = self.createHostingSubscription()
    self.assertRaises(
      Unauthorized,
      item.HostingSubscription_calculateSubscriptionStopDate,
      REQUEST={})

  @withAbort
  def test_HS_calculateSubscriptionStopDate_withDestroy(self):
    item = self.createHostingSubscription()
    destroy_date = DateTime('2012/10/30')
    item.workflow_history['instance_slap_interface_workflow'].append({
        'comment':'Directly destroy',
        'error_message': '',
        'actor': 'ERP5TypeTestCase',
        'slap_state': 'destroy_requested',
        'time': destroy_date,
        'action': 'request_destroy'
    })
    date = item.HostingSubscription_calculateSubscriptionStopDate()
    self.assertEqual(date, DateTime('2012/10/31'))

  @withAbort
  def test_HS_calculateSubscriptionStopDate_noDestroy(self):
    item = self.createHostingSubscription()
    item.workflow_history['instance_slap_interface_workflow'] = []
    date = item.HostingSubscription_calculateSubscriptionStopDate()
    self.assertEqual(date, None)

  def test_OpenSaleOrder_reindexIfIndexedBeforeLine_no_line(self):
    portal = self.portal
    order = self.createOpenSaleOrder()
    self.tic()
    indexation_timestamp = portal.portal_catalog(
      uid=order.getUid(),
      select_dict={'indexation_timestamp': None})[0].indexation_timestamp
    order.OpenSaleOrder_reindexIfIndexedBeforeLine()
    self.tic()
    new_indexation_timestamp = portal.portal_catalog(
      uid=order.getUid(),
      select_dict={'indexation_timestamp': None})[0].indexation_timestamp
    self.assertEquals(new_indexation_timestamp,
                      indexation_timestamp)

  def test_OpenSaleOrder_reindexIfIndexedBeforeLine_line_indexed_after(self):
    portal = self.portal
    order = self.createOpenSaleOrder()
    line = order.newContent(portal_type="Open Sale Order Line")
    self.tic()
    line.activate().immediateReindexObject()
    # XXX One more kitten killed
    time.sleep(1)
    self.tic()
    indexation_timestamp = portal.portal_catalog(
      uid=order.getUid(),
      select_dict={'indexation_timestamp': None})[0].indexation_timestamp
    order.OpenSaleOrder_reindexIfIndexedBeforeLine()
    self.tic()
    new_indexation_timestamp = portal.portal_catalog(
      uid=order.getUid(),
      select_dict={'indexation_timestamp': None})[0].indexation_timestamp
    self.assertNotEquals(new_indexation_timestamp,
                         indexation_timestamp)

  def test_OpenSaleOrder_reindexIfIndexedBeforeLine_line_indexed_before(self):
    portal = self.portal
    order = self.createOpenSaleOrder()
    line = order.newContent(portal_type="Open Sale Order Line")
    self.tic()
    order.activate().immediateReindexObject()
    # XXX One more kitten killed
    time.sleep(1)
    self.tic()
    indexation_timestamp = portal.portal_catalog(
      uid=order.getUid(),
      select_dict={'indexation_timestamp': None})[0].indexation_timestamp
    order.OpenSaleOrder_reindexIfIndexedBeforeLine()
    self.tic()
    new_indexation_timestamp = portal.portal_catalog(
      uid=order.getUid(),
      select_dict={'indexation_timestamp': None})[0].indexation_timestamp
    self.assertEquals(new_indexation_timestamp,
                      indexation_timestamp)

  def test_OpenSaleOrder_reindexIfIndexedBeforeLine_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.OpenSaleOrder_reindexIfIndexedBeforeLine,
      REQUEST={})
