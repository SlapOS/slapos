# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Nexedi SA and Contributors. All Rights Reserved.
#                    Łukasz Nowak <luke@nexedi.com>
#                    Romain Courteaud <romain@nexedi.com>
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
##############################################################################
from DateTime import DateTime
from AccessControl.SecurityManagement import newSecurityManager, \
  getSecurityManager
from Products.ERP5Type.Errors import UnsupportedWorkflowMethod
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import skip
from Products.ERP5Type.tests.SecurityTestCase import AssertNoPermissionMethod, \
    AssertPermissionMethod
from Products.ERP5Type import Permissions
from Products.ZSQLCatalog.SQLCatalog import Query, ComplexQuery
from VifibMixin import testVifibMixin
from random import random
from slapos import slap
from xml_marshaller import xml_marshaller
import transaction
import unittest

# global variable used to simulate Slap based logins
REMOTE_USER = None

# typical parameters sent by slap, always present in instance dict
DEFAULT_INSTANCE_DICT_PARAMETER_LIST = [
    'ip_list',
    'slap_computer_id',
    'slap_computer_partition_id',
    'slap_partition_reference',
    'slap_software_release_url',
    'slap_software_type',
    "slave_instance_list",
    'timestamp',
]


def fakeSlapAuth():
  """Dynamic patch of HTTPConnection which allow to login as different machines"""
  from httplib import HTTPConnection
  if getattr(HTTPConnection, '_original_request', None) is None:
    HTTPConnection._original_request = HTTPConnection.request

  def patched_request(self, method, url, body=None, headers={}):
    headers = headers.copy()
    assert REMOTE_USER is not None
    headers['REMOTE_USER'] = REMOTE_USER
    return self._original_request(method, url, body=body, headers=headers)
  HTTPConnection.request = patched_request


def unfakeSlapAuth():
  from httplib import HTTPConnection
  if getattr(HTTPConnection, '_original_request', None) is not None:
    HTTPConnection.request = HTTPConnection._original_request
    delattr(HTTPConnection, '_original_request')


class TestVifibSlapWebServiceMixin(testVifibMixin):
  """
  Check the slap behaviour on ERP5 documents
  """
  computer_partition_portal_type = "Computer Partition"
  computer_portal_type = "Computer"
  hosting_subscription_portal_type = "Hosting Subscription"
  sale_packing_list_line_portal_type = "Sale Packing List Line"
  sale_order_line_portal_type = "Sale Order Line"
  sale_packing_list_portal_type = "Sale Packing List"
  service_portal_type = "Service"
  slave_instance_portal_type = "Slave Instance"
  software_instance_portal_type = "Software Instance"
  software_release_portal_type = "Software Release"
  software_product_portal_type = "Software Product"

  minimal_correct_xml = '<?xml version="1.0" encoding="utf-8"?><instance/>'

  computer_partition_amount = 1
  failIfUserCanViewDocument = AssertNoPermissionMethod(Permissions.View)
  failIfUserCanAccessDocument = AssertNoPermissionMethod(
      Permissions.AccessContentsInformation)
  failIfUserCanModifyDocument = AssertNoPermissionMethod(
                                     Permissions.ModifyPortalContent)
  assertUserCanViewDocument = AssertPermissionMethod(Permissions.View)
  assertUserCanAccessDocument =\
      AssertPermissionMethod(Permissions.AccessContentsInformation)

  def stepTic(self, **kw):
    def activateAlarm():
      sm = getSecurityManager()
      self.login()
      try:
        for alarm in self.portal.portal_alarms.contentValues():
          if alarm.isEnabled() and (alarm.getId() not in \
              ('vifib_check_consistency',)):
            alarm.activeSense()
      finally:
        setSecurityManager(sm)

    if kw.get('sequence', None) is None:
      # in case of using not in sequence commit transaction
      transaction.commit()
    # trigger activateAlarm before tic
    activateAlarm()
    transaction.commit()

    self.tic()

    # retrigger activateAlarm after tic
    activateAlarm()
    transaction.commit()

    # tic after activateAlarm
    self.tic()

    try:
      self.checkDivergency()
    except AssertionError:
      # try last time to solve deliveries
      sm = getSecurityManager()
      self.login()
      try:
        self.portal.portal_alarms.vifib_update_delivery_causality_state\
          .activeSense()
        transaction.commit()
        self.tic()
        self.portal.portal_alarms.vifib_solve_automatically.activeSense()
        transaction.commit()
        self.tic()
      finally:
        setSecurityManager(sm)
      self.checkDivergency()

  def stepCleanTic(self, **kw):
    self.tic()

  def stepLogout(self, **kw):
    self.logout()

  # access related steps
  def stepLoginDefaultUser(self, **kw):
    self.login('default_user')

  def stepLoginTestHrAdmin(self, **kw):
    self.login('test_hr_admin')

  def stepLoginTestUpdatedVifibUser(self, **kw):
    self.login('test_updated_vifib_user')

  def stepLoginTestVifibAdmin(self, **kw):
    self.login('test_vifib_admin')

  def stepLoginTestVifibCustomer(self, **kw):
    self.login('test_vifib_customer')

  def stepLoginTestVifibCustomerA(self, **kw):
    self.login('test_vifib_customer_a')

  def stepLoginTestVifibDeveloper(self, **kw):
    self.login('test_vifib_developer')

  def stepLoginTestVifibMember(self, **kw):
    self.login('test_vifib_member')

  def stepLoginTestVifibUserAdmin(self, **kw):
    self.login('test_vifib_user_admin')

  def stepLoginTestVifibUserDeveloper(self, **kw):
    self.login('test_vifib_user_developer')

  def stepLoginERP5TypeTestCase(self, **kw):
    self.login('ERP5TypeTestCase')

  def clearCache(self):
    self.portal.portal_caches.clearAllCache()
    self.portal.portal_workflow.refreshWorklistCache()

  def checkDivergency(self):
    # there shall be no divergency
    current_skin = self.app.REQUEST.get('portal_skin', 'View')
    try:
      # Note: Worklists are cached, so in order to have next correct result
      # clear cache
      self.clearCache()
      self.changeSkin('RSS')
      diverged_document_list = self.portal.portal_catalog(
        portal_type=self.portal.getPortalDeliveryTypeList(),
        causality_state='!= solved'
      )
      self.assertFalse('to Solve' in self.portal.ERP5Site_viewWorklist(),
        'There are unsolved deliveries: %s' % ','.join([
          ' '.join((q.getTitle(), q.getPath(), q.getCausalityState())) \
          for q in diverged_document_list]))
    finally:
      self.changeSkin(current_skin)

  def stepCheckSiteConsistency(self, **kw):
    self.portal.portal_alarms.vifib_check_consistency.activeSense()
    transaction.commit()
    self.tic()
    self.assertEqual([], self.portal.portal_alarms.vifib_check_consistency\
        .Alarm_getConsistencyCheckReportLineList())
    self.assertFalse(self.portal.portal_alarms.vifib_check_consistency.sense())
    self.checkDivergency()

  def markManualCreation(self, document):
    self.portal.portal_workflow.doActionFor(document, 'edit_action',
      comment='Manually created by test.')

  def fakeSlapAuth(self):
    fakeSlapAuth()

  def unfakeSlapAuth(self):
    unfakeSlapAuth()

  def afterSetUp(self):
    self.fakeSlapAuth()
    testVifibMixin.afterSetUp(self)
    self.server_url = self.portal.portal_slap.absolute_url()

  def beforeTearDown(self):
    self.unfakeSlapAuth()
    super(testVifibMixin, self).beforeTearDown()

  def _loginAsUser(self, username):
    """Login as a given username. The user must exist."""
    uf = self.getPortal().acl_users
    user = uf.getUserById(username)
    self.assertNotEquals(user, None, 'No user %s' % username)
    newSecurityManager(None, user.__of__(uf))

  ########################################
  # Assertions
  ########################################
  def assertSameDict(self, expected, got):
    got = got.copy()
    issue_list = []
    for k, v in expected.items():
      if k not in got:
        issue_list.append('key %r not found' % k)
      else:
        got_v = got.pop(k)
        if got_v != v:
          issue_list.append('key %r, expected %r got %r' % (k, v, got_v))
    self.assertEqual([], issue_list, '\n'.join(issue_list))
    self.assertEqual(got, {})

  ########################################
  # Helpers
  ########################################
  def _softwareInstance_getComputerPartition(self, software_instance):
    sale_packing_list_line = software_instance\
        .getAggregateRelatedValue(
            portal_type=self.sale_packing_list_line_portal_type)
    computer_partition = sale_packing_list_line.getAggregateValue(
        portal_type=self.computer_partition_portal_type)
    self.assertNotEqual(None, computer_partition)
    return computer_partition

  def _computerPartition_getSoftwareInstance(self, computer_partition):
    sale_packing_list_line = computer_partition\
        .getAggregateRelatedValue(
            portal_type=self.sale_packing_list_line_portal_type)
    software_instance = sale_packing_list_line.getAggregateValue(
        portal_type=self.software_instance_portal_type)
    self.assertNotEqual(None, software_instance)
    return software_instance

  def _generateRandomUniqueReference(self, portal_type):
    reference = None
    while reference is None:
      random_reference = "test_%s" % random()
      result_list = self.portal.portal_catalog(
          portal_type=portal_type,
          reference=random_reference,
          )
      if not len(result_list):
        reference = random_reference
    return reference

  ########################################
  # Steps -- scenarios
  ########################################
  def stepCheckSoftwareInstanceNoDeliveryRelated(self, sequence, **kw):
    self.assertEqual(None, self.portal.portal_catalog.getResultValue(
      default_aggregate_uid=sequence['software_instance_uid'],
      portal_type=self.sale_packing_list_line_portal_type
    ))

  def stepCheckSoftwareInstanceCancelledSaleOrderLine(self, sequence, **kw):
    self.assertEqual('cancelled', self.portal.portal_catalog.getResultValue(
      default_aggregate_uid=sequence['software_instance_uid'],
      portal_type=self.sale_order_line_portal_type
    ).getSimulationState())

  def stepCheckSoftwareInstanceOrderedSaleOrderLine(self, sequence, **kw):
    self.assertEqual('ordered', self.portal.portal_catalog.getResultValue(
      default_aggregate_uid=sequence['software_instance_uid'],
      portal_type=self.sale_order_line_portal_type
    ).getSimulationState())

  def stepCheckOpenOrderLineRemoved(self, sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])
    hosting_subscription = software_instance.getAggregateRelatedValue(
      portal_type='Sale Order Line').getAggregateValue(
        portal_type='Hosting Subscription')
    # shall be not present on any validted open order
    validated_open_order_line = self.portal.portal_catalog.getResultValue(
      portal_type='Open Sale Order Line', validation_state='validated',
      default_aggregate_uid=hosting_subscription.getUid())
    self.assertEqual(None, validated_open_order_line)
    # shall be present on the latest archived open order
    reference = self.portal.portal_catalog.getResultValue(
      portal_type='Open Sale Order Line',
      default_aggregate_uid=hosting_subscription.getUid())\
        .getParentValue().getReference()
    open_sale_order = self.portal.portal_catalog.getResultValue(
        portal_type='Open Sale Order',
        reference=reference,
        validation_state='archived',
        sort_on=(('effective_date', 'descending'),)
      )
    self.assertTrue(hosting_subscription.getRelativeUrl() in \
      [q.getAggregate(portal_type='Hosting Subscription') for q in \
        open_sale_order.contentValues(portal_type='Open Sale Order Line')])

  def stepRequestComputerPartitionNoTic(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])
    kw = dict(software_release=sequence['software_release_uri'],
      software_type=sequence.get('requested_software_type',
                                 'requested_software_type'),
      partition_reference=sequence.get('requested_reference',
        'requested_reference'),
      partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
      filter_kw=sequence.get('requested_filter_dict', {}),
      state=sequence.get('instance_state'))

    slap_computer_partition.request(**kw)

  def _getRequestBasedComputerPartitionCount(self, sequence):
    return self.portal.portal_catalog.countResults(
      portal_type='Computer Partition',
      parent_uid=sequence['computer_uid'],
      software_release_url=sequence['software_release_uri'],
      free_for_request=1)[0][0]

  def stepCheckSoftwareReleaseAvailableForRequest(self, sequence, **kw):
    self.assertNotEqual(0, self._getRequestBasedComputerPartitionCount(sequence))

  def stepCheckSoftwareReleaseUnavailableForRequest(self, sequence, **kw):
    self.assertEqual(0, self._getRequestBasedComputerPartitionCount(sequence))

  def stepCheckSoftwareReleaseNotInSoftwareCatalog(self, sequence, **kw):
    software_release = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_release_uid'])
    software_product = software_release.getAggregateValue(
      portal_type='Software Product')
    # if software release is back referenced from product, it is preferred
    self.assertFalse(software_product.getRelativeUrl() \
      in software_product.getAggregateList())

  def stepCheckComputerTradeConditionDestinationSectionTestVifibCustomer(
      self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    trade_condition = computer.getAggregateRelatedValue(
      portal_type='Sale Supply Line').getParentValue()
    person_url = self.portal.portal_catalog.getResultValue(portal_type='Person',
      default_email_text='test_customer@example.org').getRelativeUrl()
    self.assertEqual(trade_condition.getDestinationSectionList(), [person_url])

  def stepPersonRequestSlapSoftwareInstancePrepare(self, sequence,
      **kw):
    software_release = sequence['software_release_uri']
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    open_order = self.slap.registerOpenOrder()
    open_order.request(
       software_release=software_release,
       software_type=sequence.get('requested_software_type', 'software_type'),
       partition_reference=sequence.get('requested_reference',
          'requested_reference'),
       partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
       filter_kw=sequence.get('requested_filter_dict', {}),
       state=sequence.get('requested_state')
       )

  def stepPersonRequestSlapSoftwareInstance(self, sequence, **kw):
    software_release = sequence['software_release_uri']
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    open_order = self.slap.registerOpenOrder()
    requested_slap_computer_partition = open_order.request(
       software_release=software_release,
       software_type=sequence.get('requested_software_type', 'software_type'),
       partition_reference=sequence.get('requested_reference',
         'requested_reference'),
       partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
       filter_kw=sequence.get('requested_filter_dict', {}),
       state=sequence.get('requested_state'))
    sequence.edit(
        requested_slap_computer_partition=requested_slap_computer_partition)
    try:
      requested_slap_computer_partition.getId()
    except slap.ResourceNotReady:
      sequence.edit(
          requested_computer_partition_reference=None)
    else:
      sequence.edit(
          requested_computer_partition_reference=\
              requested_slap_computer_partition.getId())

  def stepSetCurrentComputerPartitionFromRequestedComputerPartition(self, sequence):
    sequence['computer_partition_reference'] = \
        sequence["requested_computer_partition_reference"]

  def stepSelectSoftwareInstanceFromCurrentComputerPartition(self, sequence):
    computer_partition_reference = sequence["computer_partition_reference"]
    computer_partition = self.portal.portal_catalog.getResultValue(
        portal_type="Computer Partition",
        reference=computer_partition_reference)
    software_instance = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Packing List Line",
        aggregate_uid=computer_partition.getUid()).getAggregateValue(
            portal_type="Software Instance")
    sequence.edit(
        software_instance_uid=software_instance.getUid(),
        software_instance_reference=software_instance.getReference(),
        hosting_subscription_uid=software_instance.getAggregateRelatedValue(
          portal_type='Sale Order Line').getAggregateValue(
            portal_type='Hosting Subscription').getUid())

  def stepSetCurrentPersonSlapRequestedSoftwareInstance(self, sequence, **kw):
    software_instance_list = []
    for software_instance in self.portal.portal_catalog(
        portal_type=self.software_instance_portal_type,
        title=sequence['requested_reference']):
      # only not yet destroyed ones
      if software_instance.SoftwareInstance_getStatus() != 'Destroyed':
        software_instance_list.append(software_instance)

    self.assertEqual(1, len(software_instance_list))
    software_instance = software_instance_list[0]
    sequence.edit(
        software_instance_uid=software_instance.getUid(),
        software_instance_reference=software_instance.getReference(),
        hosting_subscription_uid=software_instance.getAggregateRelatedValue(
          portal_type='Sale Order Line').getAggregateValue(
            portal_type='Hosting Subscription').getUid())

  def stepSoftwareInstanceFailedAllocation(self, sequence,
    **kw):
    """Checks that current software instance is realted only with sale order
    and that no partition is found
    """
    software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])

    self.assertEqual(None, software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None, software_instance.getAggregateValue(
        portal_type='Computer Partition'))

  def stepCheckViewCurrentSoftwareInstance(self, sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    self.assertTrue(sequence['software_instance_reference'] in \
        software_instance.view())

  def stepCheckWriteCurrentSoftwareInstance(self, sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    software_instance.setTitle('new_title')
    self.assertEqual('new_title', software_instance.getTitle())

  def stepCheckViewRequestedSoftwareInstance(self, sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['requested_software_instance_uid'])
    self.assertTrue(sequence['requested_software_instance_reference'] in \
        software_instance.view())

  def stepCheckWriteRequestedSoftwareInstance(self, sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['requested_software_instance_uid'])
    software_instance.setTitle('new_title')
    self.assertEqual('new_title', software_instance.getTitle())

  def _checkComputerPartitionSalePackingListDoesNotExists(self, resource,
      sequence):
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=sequence['computer_partition_uid'])
    delivery_line_list = [q.getObject() for q in self.portal.portal_catalog(
      aggregate_relative_url=computer_partition.getRelativeUrl(),
      portal_type=self.sale_packing_list_line_portal_type,
      resource_relative_url=resource)]
    self.assertEqual(0, len(delivery_line_list))

  def _checkComputerPartitionSalePackingListState(self, state,
      resource, sequence):
    delivery_line_amount = sequence.get("delivery_line_amount", 1)
    self.assertEqual(delivery_line_amount, self.portal.portal_catalog\
      .countResults(
      default_aggregate_uid=ComplexQuery(
         Query(default_aggregate_uid=sequence['computer_partition_uid']),
         Query(default_aggregate_uid=sequence['software_instance_uid']),
         operator="AND"),
      portal_type=self.sale_packing_list_line_portal_type,
      simulation_state=state,
      resource_relative_url=resource)[0][0])

  def _checkComputerPartitionNoSalePackingList(self, resource, sequence):
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=sequence['computer_partition_uid'])
    delivery_line_list = [q.getObject() for q in self.portal.portal_catalog(
      aggregate_relative_url=computer_partition.getRelativeUrl(),
      portal_type=self.sale_packing_list_line_portal_type,
      resource_relative_url=resource)]
    self.assertEqual(0, len(delivery_line_list))

  def stepLoginAsCustomerA(self, sequence):
    global REMOTE_USER
    REMOTE_USER = "test_vifib_customer_a"
    self.login("test_vifib_customer_a")

  def stepSetSoftwareTitleRandom(self, sequence, **kw):
    sequence['software_title'] = str(random())

  def stepCheckComputerPartitionInstanceCleanupSalePackingListConfirmed(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('confirmed',
        self.portal.portal_preferences.getPreferredInstanceCleanupResource(),
        sequence)

  def stepCheckComputerPartitionInstanceCleanupSalePackingListDelivered(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('delivered',
        self.portal.portal_preferences.getPreferredInstanceCleanupResource(),
        sequence)

  def stepCheckComputerPartitionInstanceSetupSalePackingListDelivered(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('delivered',
        self.portal.portal_preferences.getPreferredInstanceSetupResource(),
        sequence)

  def stepCheckComputerPartitionInstanceHostingSalePackingListConfirmed(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('confirmed',
        self.portal.portal_preferences.getPreferredInstanceHostingResource(),
        sequence)

  def stepCheckComputerPartitionInstanceHostingSalePackingListStarted(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('started',
        self.portal.portal_preferences.getPreferredInstanceHostingResource(),
        sequence)

  def stepCheckComputerPartitionInstanceHostingSalePackingListStopped(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('stopped',
        self.portal.portal_preferences.getPreferredInstanceHostingResource(),
        sequence)

  def stepCheckComputerPartitionInstanceHostingSalePackingListDelivered(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('delivered',
        self.portal.portal_preferences.getPreferredInstanceHostingResource(),
        sequence)

  def stepCheckComputerPartitionNoInstanceHostingSalePackingList(self,
      sequence, **kw):
    self._checkComputerPartitionNoSalePackingList(
        self.portal.portal_preferences.getPreferredInstanceHostingResource(),
        sequence)

  def stepPersonRequestSlaveInstance(self, sequence, **kw):
    kw = dict(instance_portal_type=self.slave_instance_portal_type,
              shared=True,
              software_type=sequence.get('requested_software_type',
                                         'requested_software_type'))
    self.stepPersonRequestSoftwareInstance(sequence, **kw)

  def stepPersonRequestSoftwareInstance(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    software_release = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_release_uid'])
    software_title = sequence.get('software_title',
      self.id() + str(random()))

    if 'software_type' not in kw:
      kw['software_type'] = sequence.get('requested_software_type',
                                         'requested_software_type')
    default_state = 'started'
    if 'state' not in kw:
      kw['state'] = sequence.get('software_instance_state', default_state) \
        or default_state

    person.requestSoftwareInstance(
      software_release=software_release.getUrlString(),
      software_title=software_title,
      software_type=kw['software_type'],
      instance_xml=self.minimal_correct_xml,
      sla_xml=sequence.get('sla_xml'),
      shared=kw.get('shared', False),
      state=kw['state'])

    software_instance = self.portal.REQUEST.get('request_instance')
    hosting_subscription = self.portal.REQUEST.get('request_hosting_subscription')
    if (software_instance is not None):
      sequence.edit(
          root_software_instance_title=software_title,
          software_instance_uid=software_instance.getUid(),
          software_instance_reference=software_instance.getReference(),
          hosting_subscription_uid=hosting_subscription.getUid(),
          )

  def stepSetComputerPartitionFromRootSoftwareInstance(self, sequence):
    computer_partition = self.portal.portal_catalog.getResultValue(
        title=sequence['root_software_instance_title'], 
        portal_type="Software Instance").getAggregateRelatedValue(
            portal_type="Sale Packing List Line").getAggregateValue(
                portal_type="Computer Partition")
    sequence.edit(
      computer_partition_uid=computer_partition.getUid(),
      computer_partition_reference=computer_partition.getReference()
    )

  def stepSetSelectedComputerPartition(self, sequence, **kw):
    """Sets in sequence computer partition parameters related to current
    software instance"""
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    computer_partition = software_instance.getAggregateValue(
        portal_type=self.computer_partition_portal_type)
    sequence.edit(
      computer_partition_uid=computer_partition.getUid(),
      computer_partition_reference=computer_partition.getReference()
    )

  def stepRequestSoftwareInstanceDestroy(self, sequence, **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    instance.requestDestroy(
        software_release=instance.getUrlString(),
        instance_xml=instance.getTextContent(),
        software_type=instance.getSourceReference(),
        sla_xml=instance.getSlaXml(),
        shared=shared,
        )

  def stepRequestSoftwareInstanceDestroyRaisesUnsupportedWorkflowMethod(self,
    sequence, **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    self.assertRaises(UnsupportedWorkflowMethod, instance.requestDestroy, 
        software_release=instance.getUrlString(),
        instance_xml=instance.getTextContent(),
        software_type=instance.getSourceReference(),
        sla_xml=instance.getSlaXml(),
        shared=shared,
        )

  def stepRequestSoftwareInstanceStart(self, sequence, **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    instance.requestStart(
        software_release=instance.getUrlString(),
        instance_xml=instance.getTextContent(),
        software_type=instance.getSourceReference(),
        sla_xml=instance.getSlaXml(),
        shared=shared,
        )

  def stepRequestSoftwareInstanceStop(self, sequence, **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    instance.requestStop(
        software_release=instance.getUrlString(),
        instance_xml=instance.getTextContent(),
        software_type=instance.getSourceReference(),
        sla_xml=instance.getSlaXml(),
        shared=shared,
        )

  def stepRequestSoftwareInstallation(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
        uid=sequence['computer_uid'])

    software_release = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_release_uid'])

    computer.requestSoftwareRelease(
        software_release_url=software_release.getUrlString(), state='available')

  def _createComputer(self):
    # Mimics WebSection_registerNewComputer
    computer_reference = "COMP-%s" % self.portal.portal_ids.generateNewId(
            id_group='slap_computer_reference', id_generator='uid')
    module = self.portal.getDefaultModule(
        portal_type=self.computer_portal_type)
    computer = module.newContent(
      portal_type=self.computer_portal_type,
      title=computer_reference,
      reference=computer_reference,
      destination_reference=computer_reference,
    )
    self.markManualCreation(computer)
    return computer, computer_reference

  def stepCreateDraftComputer(self, sequence, **kw):
    computer, computer_reference = self._createComputer()
    sequence.edit(
        computer_uid=computer.getUid(),
        computer_reference=computer_reference,
    )

  def stepCreateComputer(self, sequence, **kw):
    """
    Create a computer document.
    """
    computer, computer_reference = self._createComputer()
    computer.requestComputerRegistration()
    computer.approveComputerRegistration()
    sequence.edit(
        computer_uid=computer.getUid(),
        computer_reference=computer_reference,
    )

  def stepCustomerRegisterNewComputer(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    sequence['computer_title'] = str(random())
    open_order = self.slap.registerOpenOrder()
    sequence['requested_computer'] = open_order.requestComputer(
        sequence['computer_title'])

  def stepSetComputerTitle(self, sequence, **kw):
    sequence['computer_title'] = str(random())

  def stepRequestComputer(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    open_order = self.slap.registerOpenOrder()
    sequence['requested_computer'] = open_order.requestComputer(
        sequence['computer_title'])

  def stepRevokeComputerCertificate(self, sequence, **kw):
    sequence['requested_computer'].revokeCertificate()

  def stepSetComputerCoordinatesFromComputerTitle(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      title=sequence['computer_title'], portal_type='Computer')

    sequence.edit(
      computer_uid=computer.getUid(),
      computer_reference=computer.getReference(),
    )

  def stepComputerSetAllocationScopeEmpty(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin("Hosting")
    request.set('portal_skin', "Hosting")

    computer.Computer_updateAllocationScope(allocation_scope='',
      subject_list=[])

    self.getPortal().portal_skins.changeSkin("View")
    request.set('portal_skin', "View")

  def stepComputerSetAllocationScopeOpenPersonal(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin("Hosting")
    request.set('portal_skin', "Hosting")

    computer.Computer_updateAllocationScope(allocation_scope='open/personal',
      subject_list=[])

    self.getPortal().portal_skins.changeSkin("View")
    request.set('portal_skin', "View")

  def stepComputerSetAllocationScopeClose(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin("Hosting")
    request.set('portal_skin', "Hosting")

    computer.Computer_updateAllocationScope(allocation_scope='close',
      subject_list=[])

    self.getPortal().portal_skins.changeSkin("View")
    request.set('portal_skin', "View")

  def stepComputerSetAllocationScopeOpenPublic(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin("Hosting")
    request.set('portal_skin', "Hosting")

    computer.Computer_updateAllocationScope(allocation_scope='open/public',
      subject_list=[])

    self.getPortal().portal_skins.changeSkin("View")
    request.set('portal_skin', "View")

  def stepDuplicateAndValidateCurrentComputer(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
        uid=sequence['computer_uid'])
    new_computer = computer.Base_createCloneDocument(batch_mode=1)
    new_computer.validate()

  def stepSetRandomComputerReference(self, sequence, **kw):
    sequence['computer_reference'] = str(random())

  def stepSetRandomComputerPartition(self, sequence, **kw):
    sequence.edit(computer_partition_reference=\
        sequence["computer_partition_reference_list"][0])

  def stepFormatComputer(self, sequence, **kw):
    computer_partition_reference_list = []
    computer_guid = sequence["computer_reference"]
    computer_dict = {
        'address': '127.0.0.1',
        'netmask': '255.255.255.0',
        'reference': computer_guid,
        'partition_list': []}

    for index in range(self.computer_partition_amount):
      reference = 'slappart%s' % index
      computer_partition_reference_list.append(reference)
      partition_dict = {
          'reference': reference,
          'tap': dict(name='tap'),
          'address_list': [],
          }
      computer_dict['partition_list'].append(partition_dict)
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    self.slap.registerComputer(computer_guid).updateConfiguration(
        xml_marshaller.dumps(computer_dict))
    sequence.edit(
        computer_partition_reference_list=computer_partition_reference_list)

  def stepComputerSoftwareReleaseAvailable(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    software_release_url = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_release_uid']).getUrlString()
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    # XXX: it is impossible to do:
    #  sr = self.slap.registerSoftwareRelease(
    #       software_release=software_release_url)
    #  sr.available(computer_guid)
    computer = self.slap.registerComputer(computer_guid)
    software_release = [q for q in computer.getSoftwareReleaseList()
        if q.getURI() == software_release_url][0]
    software_release.available()

  def stepSoftwareInstanceStopped(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        sequence['computer_partition_reference'])
    computer_partition.stopped()

  def stepSoftwareInstanceStarted(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        sequence['computer_partition_reference'])
    computer_partition.started()

  def stepSoftwareInstanceAvailable(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        sequence['computer_partition_reference'])
    computer_partition.available()

  def stepSoftwareInstanceDestroyed(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        sequence['computer_partition_reference'])
    computer_partition.destroyed()

  def stepSoftwareInstanceBuilding(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        sequence['computer_partition_reference'])
    computer_partition.building()

  def stepPayPayment(self, sequence, **kw):
    """
    """
    payment = self.portal.portal_catalog.getResultValue(
        portal_type="Payment Transaction",
        simulation_state="started")
    payment.stop()

  ########################################
  # Steps -- REMOTE_USER logins
  ########################################

  def stepSlapLogout(self, **kw):
    global REMOTE_USER
    REMOTE_USER = None
    self.logout()

  def stepSlapLoginRandomComputer(self, sequence, **kw):
    global REMOTE_USER
    REMOTE_USER = str(random())
    self.login('ERP5TypeTestCase')

  def stepSlapLoginTestVifibAdmin(self, sequence, **kw):
    global REMOTE_USER
    REMOTE_USER = 'test_vifib_admin'

  def stepSlapLoginCurrentComputer(self, sequence, **kw):
    global REMOTE_USER
    REMOTE_USER = sequence['computer_reference']

  def stepSlapLoginCurrentSoftwareInstance(self, sequence, **kw):
    global REMOTE_USER
    REMOTE_USER = sequence['software_instance_reference']

  def stepSlapLoginTestVifibCustomer(self, sequence, **kw):
    global REMOTE_USER
    REMOTE_USER = 'test_vifib_customer'

  def stepSlapLoginWebUser(self, sequence, **kw):
    global REMOTE_USER
    REMOTE_USER = sequence['web_user']

  ########################################
  # Typical sequences for scenarios
  ########################################

  prepare_published_software_release = """
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      CleanTic
      SubmitSoftwareRelease
      CleanTic
      CreateSoftwareProduct
      CleanTic
      ValidateSoftwareProduct
      CleanTic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      CleanTic
      Logout
  """

  # stabilise accounting until payment is reached
  stabilise_accounting = """
      CallSlaposUpdateDeliveryCausalityStateAlarm
      CleanTic
      CallVifibSolveAutomaticallyAlarm
      CleanTic
      CallVifibExpandDeliveryLineAlarm
      CleanTic
      CallSlaposTriggerBuildAlarm
      CleanTic
      CallSlaposUpdateDeliveryCausalityStateAlarm
      CleanTic
      CallVifibSolveAutomaticallyAlarm
      CleanTic
      CallVifibExpandDeliveryLineAlarm
      CleanTic
      CallSlaposTriggerBuildAlarm
      CleanTic
      CallSlaposUpdateDeliveryCausalityStateAlarm
      CleanTic
      CallVifibSolveAutomaticallyAlarm
      CleanTic
      CallStopConfirmedSaleInvoiceTransactionAlarm
      CleanTic
      CallVifibExpandDeliveryLineAlarm
      CleanTic
      CallSlaposTriggerBuildAlarm
      CleanTic
      CallSlaposUpdateDeliveryCausalityStateAlarm
      CleanTic
      CallVifibSolveAutomaticallyAlarm
      CleanTic
  """

  prepare_computer = stabilise_accounting + """
      SlapLoginTestVifibAdmin
      CustomerRegisterNewComputer
      CleanTic
      SlapLogout
      LoginTestVifibAdmin
      SetComputerCoordinatesFromComputerTitle
      ComputerSetAllocationScopeOpenPublic
      CleanTic
      CheckComputerTradeConditionDestinationSectionListEmpty
      Logout
  """

  prepare_formated_computer = prepare_computer + """
      SlapLoginCurrentComputer
      FormatComputer
      CleanTic
      SlapLogout
  """

  prepare_supply_software_release = """
      SlapLoginTestVifibAdmin
      SupplyComputerSoftwareReleaseAvailable
      Tic
      SlapLogout
  """

  prepare_software_release_purchase_packing_list = \
      prepare_published_software_release + prepare_formated_computer + \
      prepare_supply_software_release + '\
        LoginDefaultUser \
        CheckSoftwareReleaseAvailableForRequest \
        Logout'

  prepare_installed_software_release_sequence_string = \
      prepare_published_software_release + \
      prepare_formated_computer + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout
    """

  prepare_person_requested_software_instance = \
      prepare_published_software_release + \
      prepare_formated_computer + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      LoginTestVifibCustomer
      SetSoftwareTitleRandom
      PersonRequestSoftwareInstance
      Tic
      Logout
  """
  prepare_install_requested_computer_partition_sequence_string = \
      prepare_person_requested_software_instance + """
      LoginDefaultUser
      CallSlaposAllocateInstanceAlarm
      Tic
      CallSlaposTriggerBuildAlarm
      CleanTic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      Logout
  """

  prepare_building_computer_partition_sequence_string = \
      prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckComputerPartitionInstanceSetupSalePackingListDelivered \
      Logout \
    '

  prepare_installed_computer_partition_sequence_string = \
      prepare_install_requested_computer_partition_sequence_string + """
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout
      LoginDefaultUser
      SetSelectedComputerPartition
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout
  """

  prepare_destroy_requested_computer_partition = \
      prepare_installed_computer_partition_sequence_string + '\
      LoginTestVifibCustomer \
      SetSequenceSoftwareInstanceStateDestroyed \
      PersonRequestSoftwareInstance \
      Tic \
      Logout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed \
      Logout \
      '

  prepare_destroyed_computer_partition = \
      prepare_destroy_requested_computer_partition + '\
      SlapLoginCurrentComputer \
      SoftwareInstanceDestroyed \
      Tic \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered \
      CheckComputerPartitionIsFree \
      CheckOpenOrderLineRemoved \
      Logout \
      '

  prepare_start_requested_computer_partition_sequence_string = \
      prepare_installed_computer_partition_sequence_string + '\
      LoginTestVifibCustomer \
      SetSequenceSoftwareInstanceStateStarted \
      PersonRequestSoftwareInstance \
      Tic \
      Logout \
      LoginDefaultUser \
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed \
      Logout \
  '

  prepare_started_computer_partition_sequence_string = \
      prepare_start_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceHostingSalePackingListStarted \
      Logout \
  '
  prepare_stop_requested_computer_partition_sequence_string = \
      prepare_installed_computer_partition_sequence_string + '\
      LoginTestVifibCustomer \
      SetSequenceSoftwareInstanceStateStopped \
      PersonRequestSoftwareInstance \
      Tic \
      Logout \
  '
  prepare_stopped_computer_partition_sequence_string = \
      prepare_stop_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      SoftwareInstanceStopped \
      Tic \
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceHostingSalePackingListStopped \
      Logout \
  '

  prepare_children_a_children_b_sequence_string = \
      prepare_install_requested_computer_partition_sequence_string + \
      """
      LoginDefaultUser
      SetRootSoftwareInstanceCurrentInstance
      SelectRequestedReferenceChildrenA
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict \
      LoginDefaultUser
      CallSlaposAllocateInstanceAlarm
      Tic
      Logout
      RequestComputerPartition \
      Tic \
      SlapLogout

      LoginDefaultUser
      SetChildrenAComputerPartition
      SelectRequestedReferenceChildrenB
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      CheckRaisesNotFoundComputerPartitionParameterDict
      LoginDefaultUser
      CallSlaposAllocateInstanceAlarm
      Tic
      Logout
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SetChildrenBComputerPartition
      Logout
      """

  prepare_another_computer_sequence_string = """
    StoreComputerReference
    SlapLoginTestVifibAdmin
    CustomerRegisterNewComputer
    Tic
    SlapLogout
    LoginTestVifibAdmin
    SetComputerCoordinatesFromComputerTitle
    ComputerSetAllocationScopeOpenPublic
    Tic
    Logout

    SlapLoginCurrentComputer
    FormatComputer
    Tic
    SlapLogout

    LoginTestVifibAdmin
    RequestSoftwareInstallation
    Tic
    Logout

    SlapLoginCurrentComputer
    ComputerSoftwareReleaseAvailable
    Tic
    SlapLogout

    SetRequestedFilterParameterDict
    RestoreComputerReference
  """

  register_new_user_sequence_string = '\
      Logout \
      RequestCredentialFromWebSite \
      Tic \
      LoginDefaultUser \
      SubmitCredentialRequest \
      Tic \
      CallAcceptSubmittedCredentialsAlarm \
      Tic \
      Logout \
      LoginERP5TypeTestCase \
      CallVifibExpandDeliveryLineAlarm \
      CleanTic \
      CallSlaposUpdateDeliveryCausalityStateAlarm \
      CleanTic \
      CallVifibSolveAutomaticallyAlarm \
      CleanTic \
      CallSlaposTriggerBuildAlarm \
      CleanTic \
      CallVifibExpandDeliveryLineAlarm \
      CleanTic \
      CallSlaposTriggerBuildAlarm \
      CleanTic \
      CallSlaposUpdateDeliveryCausalityStateAlarm \
      CleanTic \
      CallVifibSolveAutomaticallyAlarm \
      CleanTic \
      CallStopConfirmedSaleInvoiceTransactionAlarm \
      CleanTic \
      CallVifibExpandDeliveryLineAlarm \
      CleanTic \
      CallSlaposTriggerBuildAlarm \
      CleanTic \
      CallVifibExpandDeliveryLineAlarm \
      CleanTic \
      CallSlaposUpdateDeliveryCausalityStateAlarm \
      CleanTic \
      CallVifibSolveAutomaticallyAlarm \
      CleanTic \
      CallVifibPayzenUpdateConfirmedPaymentAlarm \
      CleanTic \
      Logout'

  create_new_user_instance_sequence_string = '\
      LoginWebUser \
      ResetSequenceSoftwareInstanceState \
      SetSoftwareTitleRandom \
      PersonRequestSoftwareInstance \
      Tic \
      Logout \
      \
      LoginDefaultUser \
      CallSlaposAllocateInstanceAlarm \
      CleanTic \
      CallVifibExpandConfirmedSaleOrderAlarm \
      CleanTic \
      CallSlaposTriggerBuildAlarm \
      CleanTic \
      CallSlaposUpdateDeliveryCausalityStateAlarm \
      CleanTic \
      CallVifibSolveAutomaticallyAlarm \
      CleanTic \
      SetSelectedComputerPartition \
      SelectCurrentlyUsedSalePackingListUid \
      Logout \
      '

  ########################################
  # Steps
  ########################################

  def stepSupplyComputerSoftwareReleaseAvailable(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    supply = self.slap.registerSupply()
    supply.supply(sequence['software_release_uri'],
      sequence['computer_reference'], 'available')

  def stepSupplyComputerSoftwareReleaseDestroyed(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    supply = self.slap.registerSupply()
    supply.supply(sequence['software_release_uri'],
      sequence['computer_reference'], 'destroyed')

  def stepResetSequenceSoftwareInstanceState(self, sequence, **kw):
    sequence['software_instance_state'] = ''

  def stepSetSequenceSoftwareInstanceStateStopped(self, sequence, **kw):
    sequence['software_instance_state'] = 'stopped'

  def stepSetSequenceSoftwareInstanceStateStarted(self, sequence, **kw):
    sequence['software_instance_state'] = 'started'

  def stepSetSequenceSoftwareInstanceStateDestroyed(self, sequence, **kw):
    sequence['software_instance_state'] = 'destroyed'

  def stepCheckComputerTradeConditionDestinationSectionListEmpty(self,
      sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    trade_condition = computer.getAggregateRelatedValue(
      portal_type='Sale Supply Line').getParentValue()
    self.assertEqual(trade_condition.getDestinationSectionList(), [])

  def stepCheckSuccessSlapRegisterComputerCall(self, sequence, **kw):
    """
    Check that slap.registerComputer is successfully called.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer = self.slap.registerComputer(computer_guid)
    self.assertTrue(isinstance(computer, slap.Computer))

  def stepCheckUnexistingComputer(self, sequence, **kw):
    """
    Generate a new computer reference.
    Check that it is not present in the system.
    """
    computer_reference = sequence["computer_reference"]
    result_list = self.portal.portal_catalog(
          portal_type=self.computer_portal_type,
          reference=computer_reference,
          )
    self.assertEquals(0, len(result_list))

  def stepCheckUnauthorizedSlapGetComputerPartitionListCall(self, sequence,
      **kw):
    computer_guid = sequence.get("computer_reference", str(random()))
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer = self.slap.registerComputer(computer_guid)
    self.assertRaises(slap.Unauthorized, computer.getComputerPartitionList)

  def stepCheckUnauthorizedSlapRegisterComputerPartitionCall(self, sequence,
      **kw):
    computer_guid = sequence.get("computer_reference", str(random()))
    partition_id = str(random())
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    self.slap.registerComputerPartition(computer_guid, partition_id)
    self.assertRaises(slap.Unauthorized,
        self.slap.registerComputerPartition, computer_guid, partition_id)

  def stepCheckNotFoundSlapRegisterComputerPartitionCall(self, sequence, **kw):
    """
    Check that slap.registerComputerPartition fails with slap.NotFoundError
    exception
    """
    computer_guid = sequence["computer_reference"]
    partition_id = str(random())
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    self.assertRaises(slap.NotFoundError,
        self.slap.registerComputerPartition, computer_guid, partition_id)

  def stepCheckSuccessSlapRegisterComputerPartitionCall(self, sequence, **kw):
    """
    Check that slap.registerComputerPartition is successfully called.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference_list"][0]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer = self.slap.registerComputerPartition(computer_guid, partition_id)
    self.assertTrue(isinstance(computer, slap.ComputerPartition))

  def stepSelectNewSoftwareReleaseUri(self, sequence, **kw):
    """
    Generate a new software release uri
    Check that it is not present in the system.
    """
    url = None
    while url is None:
      random_url = "http://example.org/test_%s" % random()
      result_list = self.portal.portal_catalog(
          portal_type=self.software_release_portal_type,
          url_string=random_url,
          )
      if not len(result_list):
        url = random_url
    sequence.edit(software_release_uri=url)

  def stepSelectDifferentSoftwareReleaseUri(self, sequence, **kw):
    """
      Change the software release uri
    """
    software_release_uri_list = sequence.get("software_release_uri_list", [])
    software_release_uri = sequence.get("software_release_uri")
    old_software_release_uri = software_release_uri
    for uri in software_release_uri_list:
      if uri != software_release_uri:
        sequence.edit(software_release_uri=uri)
        break
    self.assertNotEquals(sequence["software_release_uri"],
        old_software_release_uri)

  def stepStoreSoftwareReleaseUri(self, sequence, **kw):
    """
      Store the current software release uri in one list
    """
    software_release_uri = sequence["software_release_uri"]
    software_release_uri_list = sequence.get("software_release_uri_list", [])
    if software_release_uri not in software_release_uri_list:
      software_release_uri_list.append(software_release_uri)
    sequence.edit(software_release_uri_list=software_release_uri_list)

  def stepCheckSuccessSlapRegisterSoftwareReleaseCall(self, sequence, **kw):
    """
    Check that slap.registerSoftwareRelease is successfully called.
    """
    url = sequence["software_release_uri"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer = self.slap.registerSoftwareRelease(url)
    self.assertTrue(isinstance(computer, slap.SoftwareRelease))

  def stepCreateSoftwareProduct(self, sequence, **kw):
    """
    Create a software product
    """
    module = self.portal.getDefaultModule(
        portal_type=self.software_product_portal_type)
    title = None
    while title is None:
      random_title = "Test Software Product %s" % random()
      result_list = self.portal.portal_catalog(
          portal_type=self.software_product_portal_type,
          title=random_title,
          )
      if not len(result_list):
        title = random_title
    software_product = module.newContent(
        portal_type=self.software_product_portal_type,
        title=title,
        )
    self.markManualCreation(software_product)
    sequence.edit(software_product_uid=software_product.getUid())

  def stepValidateSoftwareProduct(self, sequence, **kw):
    """
    Validate the software product
    """
    software_product_uid = sequence["software_product_uid"]
    software_product = self.portal.portal_catalog.getResultValue(
        uid=software_product_uid)
    software_product.portal_workflow.doActionFor(software_product,
                                                 'validate_action')

  def stepCreateSoftwareRelease(self, sequence, **kw):
    """
    Create a software release document.
    """
    url = sequence["software_release_uri"]
    module = self.portal.getDefaultModule(
        portal_type=self.software_release_portal_type)
    software_release = module.newContent(
        portal_type=self.software_release_portal_type,
        version=1,
        language='en',
        reference=url,
        contributor_value=self.portal.person_module.test_vifib_user_developer,
        url_string=url)
    self.markManualCreation(software_release)
    sequence.edit(software_release_uid=software_release.getUid())

  def stepSetSoftwareProductToSoftwareRelease(self, sequence, **kw):
    """
    Associate software product to software release
    """
    software_release_uid = sequence["software_release_uid"]
    software_product_uid = sequence["software_product_uid"]
    software_release = self.portal.portal_catalog.getResultValue(
        uid=software_release_uid)
    software_product = self.portal.portal_catalog.getResultValue(
        uid=software_product_uid)
    software_release.edit(
        aggregate_value=software_product,
        )

  def stepSubmitSoftwareRelease(self, sequence, **kw):
    """
    Submit the software release document.
    """
    software_release_uid = sequence["software_release_uid"]
    software_release = self.portal.portal_catalog.getResultValue(
        uid=software_release_uid)
    software_release.portal_workflow.doActionFor(software_release,
                                                 'submit_action')

  def stepPublishByActionSoftwareRelease(self, sequence, **kw):
    """
    Validate the software release document.
    """
    software_release_uid = sequence["software_release_uid"]
    software_release = self.portal.portal_catalog.getResultValue(
        uid=software_release_uid)
    software_release.portal_workflow.doActionFor(software_release,
                                                 'publish_action')

  def stepSelectYetAnotherRequestedReference(self, sequence, **kw):
    sequence.edit(requested_reference='yet_another_requested_reference' + str(random()))

  def stepSelectAnotherRequestedReference(self, sequence, **kw):
    sequence.edit(requested_reference='another_requested_reference' + str(random()))

  def stepSelectAnotherRequestedSoftwareType(self, sequence, **kw):
    sequence.edit(requested_software_type='another_requested_software_type' + str(random()))

  def stepSelectRequestedReference(self, sequence, **kw):
    sequence.edit(requested_reference='requested_reference')
    sequence.edit(requested_software_type='requested_software_type')

  def stepSelectRequestedSoftwaretype(self, sequence, **kw):
    sequence.edit(requested_software_type='requested_software_type')

  def stepSelectRequestedReferenceChildrenA(self, sequence, **kw):
    sequence.edit(requested_reference='children_a')
    sequence.edit(requested_software_type='children_a')

  def stepSelectRequestedReferenceChildrenB(self, sequence, **kw):
    sequence.edit(requested_reference='children_b')
    sequence.edit(requested_software_type='children_b')

  def stepSelectRequestedReferenceChildrenAChild(self, sequence, **kw):
    sequence.edit(requested_reference='children_a_child')
    sequence.edit(requested_software_type='children_a_child')

  def stepSelectRequestedReferenceChildrenBChild(self, sequence, **kw):
    sequence.edit(requested_reference='children_b_child')
    sequence.edit(requested_software_type='children_b_child')

  def stepSelectRequestedReferenceRootSoftwareInstanceTitle(self, sequence,
      **kw):
    sequence.edit(requested_reference=sequence['root_software_instance_title'])
    sequence.edit(requested_software_type=sequence['root_software_instance_title'])

  def stepSelectRequestedReferenceB(self, sequence, **kw):
    sequence.edit(requested_reference='b')
    sequence.edit(requested_software_type='b')

  def stepSelectRequestedReferenceC(self, sequence, **kw):
    sequence.edit(requested_reference='c')
    sequence.edit(requested_software_type='c')

  def stepSelectEmptyRequestedParameterDict(self, sequence, **kw):
    sequence.edit(requested_parameter_dict=None)

  def stepSelectRequestedParameterDictRequestedParameter(self, sequence, **kw):
    sequence.edit(requested_parameter_dict={
      'requested_parameter_id': 'requested_parameter_value'})

  def stepCheckGetSetConnectionDict(self, sequence, **kw):
    # Note: To be splited to ERP5 checking part (with using logged user)
    #       and slap based part (with slap call)
    global REMOTE_USER
    software_instance_uid = sequence['software_instance_uid']
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)

    computer_partition = software_instance.getAggregateRelatedValue(
        portal_type=self.sale_packing_list_line_portal_type).getAggregateValue(
            portal_type=self.computer_partition_portal_type)
    computer = computer_partition
    while computer.getPortalType() != self.computer_portal_type:
      computer = computer.getParentValue()

    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    REMOTE_USER = computer.getReference()
    slap_computer_partition = self.slap.registerComputerPartition(
        computer.getReference(), computer_partition.getReference())

    self.assertEqual(None, software_instance.getConnectionXml())

    stored_dict = dict(parameter='value')
    REMOTE_USER = computer.getReference()
    slap_computer_partition.setConnectionDict(stored_dict)
    transaction.commit()

    server_xml = software_instance.getConnectionXml()
    # check that values on server are ok
    self.assertTrue('parameter' in server_xml)
    self.assertTrue('value' in server_xml)
    # check that returned dict has no change
    REMOTE_USER = software_instance.getReference()
    # re-register the partition, in order to re-read data from server
    # as registerComputerPartition sends immediately synchronised computer
    # partition, it is required to re-fetch it
    slap_computer_partition = self.slap.registerComputerPartition(
        computer.getReference(), computer_partition.getReference())
    self.assertEqual('value',
        slap_computer_partition.getConnectionParameter('parameter'))

  def stepRequestSlaveInstanceFromComputerPartition(self, sequence, **kw):
    software_release_uri = sequence['software_release_uri']
    requested_reference = sequence['requested_reference']
    requested_parameter_dict = sequence['requested_parameter_dict']

    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])

    requested_slap_computer_partition = slap_computer_partition.request(
        software_release=software_release_uri,
        software_type=sequence.get('requested_software_type',
                                   'requested_software_type'),
        partition_reference=requested_reference,
        partition_parameter_kw=requested_parameter_dict,
        # XXX The follow API should be slave, but shared was kept for
        # Backward compatibility with older versions of slap
        shared=True,
        filter_kw=sequence.get('requested_filter_dict', {}),
        state=sequence.get('instance_state'))

    # tic as request is done on slap level library
    self.stepTic()

    sequence.edit(
        requested_slap_computer_partition=requested_slap_computer_partition)
    try:
      requested_slap_computer_partition.getId()
    except slap.ResourceNotReady:
      sequence.edit(
          requested_computer_partition_reference=None)
    else:
      sequence.edit(
          requested_computer_partition_reference=\
              requested_slap_computer_partition.getId())

  def stepRequestSlaveInstanceFromComputerPartitionNotFoundError(self, sequence, **kw):
    software_release_uri = sequence['software_release_uri']
    requested_reference = sequence['requested_reference']
    requested_parameter_dict = sequence['requested_parameter_dict']

    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])

    self.assertRaises(slap.NotFoundError,
      slap_computer_partition.request,
      software_release=software_release_uri,
      software_type=sequence.get('requested_software_type',
                                 'requested_software_type'),
      partition_reference=requested_reference,
      partition_parameter_kw=requested_parameter_dict,
      shared=True,
      filter_kw=sequence.get('requested_filter_dict', {}),
      state=sequence.get('instance_state'))

  def stepRequestTwoAndCheckDifferentResult(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])
    software_release = sequence['software_release_uri']
    software_type = sequence.get('requested_reference', 'requested_reference')
    first = slap_computer_partition.request(software_release,
        software_type, software_type + str(1))
    second = slap_computer_partition.request(software_release,
        software_type, software_type + str(2))
    self.stepLoginDefaultUser()
    self.stepTic()
    self.stepCallSlaposAllocateInstanceAlarm()
    self.stepTic()
    self.stepLogout()
    first = slap_computer_partition.request(software_release,
        software_type, software_type + str(1))
    second = slap_computer_partition.request(software_release,
        software_type, software_type + str(2))
    self.stepTic()
    self.assertNotEqual(first.getId(), second.getId())

  def stepRequestComputerPartition(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])
    kw = dict(software_release=sequence['software_release_uri'],
      software_type=sequence.get('requested_software_type',
                                 'requested_software_type'),
      partition_reference=sequence.get('requested_reference',
        'requested_reference'),
      partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
      filter_kw=sequence.get('requested_filter_dict', {}),
      state=sequence.get('instance_state'))

    requested_slap_computer_partition = slap_computer_partition.request(**kw)
    self.stepTic()

    sequence.edit(
        requested_slap_computer_partition=requested_slap_computer_partition)
    try:
      requested_slap_computer_partition.getId()
    except slap.ResourceNotReady:
      sequence.edit(
          requested_computer_partition_reference=None)
    else:
      sequence.edit(
          requested_computer_partition_reference=\
              requested_slap_computer_partition.getId())

  def _stepSetSoftwareInstanceChildren(self, sequence, source_reference):
    software_instance_uid = sequence['root_software_instance_uid']
    hosting_subscription_uid = sequence['hosting_subscription_uid']
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)
    children_software_instance = \
      software_instance.portal_catalog.getResultValue(
          portal_type="Software Instance", source_reference=source_reference,
          root_uid=hosting_subscription_uid)
    self.assertNotEqual(None, children_software_instance)
    self.assertNotEqual(software_instance.getRelativeUrl(),
        children_software_instance.getRelativeUrl())
    sequence.edit(
        software_instance_uid=children_software_instance.getUid(),
        software_instance_reference=children_software_instance.getReference(),
        computer_partition_reference=self.\
            _softwareInstance_getComputerPartition(children_software_instance
              ).getReference()
        )
  def stepSetSoftwareInstanceChildrenA(self, sequence, **kw):
    self._stepSetSoftwareInstanceChildren(sequence, 'children_a')

  def stepSetSoftwareInstanceChildrenB(self, sequence, **kw):
    self._stepSetSoftwareInstanceChildren(sequence, 'children_b')

  def stepSetRootSoftwareInstanceCurrentInstance(self, sequence, **kw):
    software_instance_uid = sequence['software_instance_uid']
    self.assertNotEqual(None, software_instance_uid)
    sequence.edit(root_software_instance_uid=software_instance_uid)

  def stepSetSoftwareInstanceRoot(self, sequence, **kw):
    root_software_instance_uid = sequence['root_software_instance_uid']
    self.failIfEqual(None, root_software_instance_uid)
    root_software_instance = self.portal.portal_catalog.getResultValue(
      uid=root_software_instance_uid,
    )
    self.failIfEqual(None, root_software_instance)
    computer_partition_reference = self._softwareInstance_getComputerPartition(
      root_software_instance).getReference()
    sequence.edit(software_instance_uid=root_software_instance_uid,
                  computer_partition_reference=computer_partition_reference)

  def stepConfirmSaleOrderOrderedToCheckSerializeCalledOnSelected(
      self, sequence, **kw):

    # check that on being_requested serialise is being called
    # code stolen from testERP5Security:test_MultiplePersonReferenceConcurrentTransaction
    class DummyTestException(Exception):
      pass

    def verify_serialize_call(self):
      # it is checking that anything below computer_module raises exception
      # thanks to this this test do not have to be destructive
      if self.getPortalType() == "Computer Partition":
        raise DummyTestException
      else:
        return self.serialize_call()

    from Products.ERP5Type.Base import Base
    Base.serialize_call = Base.serialize
    Base.serialize = verify_serialize_call

    try:
      sale_order_line_ordered = self.portal.portal_catalog.getResultValue(
          portal_type="Sale Order Line", simulation_state="ordered")
      self.assertRaises(DummyTestException,
        sale_order_line_ordered.SaleOrderLine_tryToAllocatePartition)
    finally:
      Base.serialize = Base.serialize_call

    transaction.abort()

  def _getComputerPartitionByReference(self, sequence):
    computer_partition_list = self.portal.portal_catalog(
        portal_type=self.computer_partition_portal_type,
        reference=sequence['requested_computer_partition_reference'],
        parent_uid=sequence['computer_uid'])
    self.assertEqual(1, len(computer_partition_list))
    return computer_partition_list[0]

  def stepSetChildrenAComputerPartition(self, sequence, **kw):
    sequence.edit(children_a_computer_partition=self\
        ._getComputerPartitionByReference(sequence))

  def stepSetChildrenBComputerPartition(self, sequence, **kw):
    sequence.edit(children_b_computer_partition=self\
        ._getComputerPartitionByReference(sequence))

  def stepSetChildrenAChildComputerPartition(self, sequence, **kw):
    sequence.edit(children_a_child_computer_partition=self\
        ._getComputerPartitionByReference(sequence))

  def stepSetChildrenBChildComputerPartition(self, sequence, **kw):
    sequence.edit(children_b_child_computer_partition=self\
        ._getComputerPartitionByReference(sequence))

  def stepSetRequestedComputerPartition(self, sequence, **kw):
    sequence.edit(requested_computer_partition=self\
        ._getComputerPartitionByReference(sequence))

  def stepSetRequestedComputerPartitionAsCurrentComputerPartition(self, 
      sequence):
    sequence.edit(computer_partition_reference=\
        sequence["requested_computer_partition"].getReference())

  def stepCheckComputerPartitionChildrenANoChild(self, sequence, **kw):
    computer_partition = sequence['children_a_computer_partition']
    self._checkComputerPartitionAndRelatedSoftwareInstance(computer_partition)
    software_instance = self._computerPartition_getSoftwareInstance(
        computer_partition)
    predecessor_list = software_instance.getPredecessorValueList()
    self.assertEqual(0, len(predecessor_list))

  def stepCheckComputerPartitionChildrenA(self, sequence, **kw):
    computer_partition = sequence['children_a_computer_partition']
    self._checkComputerPartitionAndRelatedSoftwareInstance(computer_partition)
    software_instance = self._computerPartition_getSoftwareInstance(
        computer_partition)
    predecessor_list = software_instance.getPredecessorValueList()
    self.assertEqual(1, len(predecessor_list))
    predecessor = predecessor_list[0]
    self.assertEqual('requested_software_type', predecessor.getSourceReference())
    self.assertEqual(1, len(software_instance.getPredecessorRelatedValueList()))

  def stepCheckComputerPartitionChildrenAWithOwnChildren(self, sequence, **kw):
    computer_partition = sequence['children_a_computer_partition']
    self._checkComputerPartitionAndRelatedSoftwareInstance(computer_partition)
    software_instance = self._computerPartition_getSoftwareInstance(
        computer_partition)
    predecessor_list = software_instance.getPredecessorValueList()
    self.assertEqual(1, len(predecessor_list))
    predecessor = predecessor_list[0]
    self.assertEqual('children_a_child', predecessor.getSourceReference())
    self.assertEqual(1, len(software_instance.getPredecessorRelatedValueList()))

  def stepCheckComputerPartitionChildrenBNoChild(self, sequence, **kw):
    computer_partition = sequence['children_b_computer_partition']
    self._checkComputerPartitionAndRelatedSoftwareInstance(computer_partition)
    software_instance = self._computerPartition_getSoftwareInstance(
        computer_partition)
    predecessor_list = software_instance.getPredecessorValueList()
    self.assertEqual(0, len(predecessor_list))

  def stepCheckComputerPartitionChildrenB(self, sequence, **kw):
    computer_partition = sequence['children_b_computer_partition']
    self._checkComputerPartitionAndRelatedSoftwareInstance(computer_partition)
    software_instance = self._computerPartition_getSoftwareInstance(
        computer_partition)
    predecessor_list = software_instance.getPredecessorValueList()
    self.assertEqual(1, len(predecessor_list))
    predecessor = predecessor_list[0]
    self.assertEqual('requested_software_type', predecessor.getSourceReference())
    self.assertEqual(1, len(software_instance.getPredecessorRelatedValueList()))

  def stepCheckComputerPartitionChildrenBWithOwnChildren(self, sequence, **kw):
    computer_partition = sequence['children_b_computer_partition']
    self._checkComputerPartitionAndRelatedSoftwareInstance(computer_partition)
    software_instance = self._computerPartition_getSoftwareInstance(
        computer_partition)
    predecessor_list = software_instance.getPredecessorValueList()
    self.assertEqual(1, len(predecessor_list))
    predecessor = predecessor_list[0]
    self.assertEqual('children_b_child', predecessor.getSourceReference())
    self.assertEqual(1, len(software_instance.getPredecessorRelatedValueList()))

  def stepCheckComputerPartitionRequestedDoubleScenarioChildrenA(self,
      sequence, **kw):
    computer_partition = sequence['requested_computer_partition']
    self._checkComputerPartitionAndRelatedSoftwareInstance(computer_partition)
    software_instance = self._computerPartition_getSoftwareInstance(
        computer_partition)
    self.assertEqual(0, len(software_instance.getPredecessorValueList()))
    predecessor_related_list = software_instance.getPredecessorRelatedValueList()
    self.assertEqual(1, len(predecessor_related_list))
    self.assertSameSet(['children_a'],
        [q.getSourceReference() for q in predecessor_related_list])

  def stepCheckComputerPartitionRequestedDoubleScenarioChildrenB(self,
      sequence, **kw):
    computer_partition = sequence['requested_computer_partition']
    self._checkComputerPartitionAndRelatedSoftwareInstance(computer_partition)
    software_instance = self._computerPartition_getSoftwareInstance(
        computer_partition)
    self.assertEqual(0, len(software_instance.getPredecessorValueList()))
    predecessor_related_list = software_instance.getPredecessorRelatedValueList()
    self.assertEqual(1, len(predecessor_related_list))
    self.assertSameSet(['children_b'],
        [q.getSourceReference() for q in predecessor_related_list])

  def stepCheckComputerPartitionChildrenAChild(self, sequence, **kw):
    computer_partition = sequence['children_a_child_computer_partition']
    self._checkComputerPartitionAndRelatedSoftwareInstance(computer_partition)
    software_instance = self._computerPartition_getSoftwareInstance(
        computer_partition)
    self.assertEqual(0, len(software_instance.getPredecessorValueList()))
    predecessor_related_list = software_instance.getPredecessorRelatedValueList()
    self.assertEqual(1, len(predecessor_related_list))
    predecessor = predecessor_related_list[0]
    self.assertEqual('children_a', predecessor.getSourceReference())

  def stepCheckComputerPartitionChildrenBChild(self, sequence, **kw):
    computer_partition = sequence['children_b_child_computer_partition']
    self._checkComputerPartitionAndRelatedSoftwareInstance(computer_partition)
    software_instance = self._computerPartition_getSoftwareInstance(
        computer_partition)
    self.assertEqual(0, len(software_instance.getPredecessorValueList()))
    predecessor_related_list = software_instance.getPredecessorRelatedValueList()
    self.assertEqual(1, len(predecessor_related_list))
    predecessor = predecessor_related_list[0]
    self.assertEqual('children_b', predecessor.getSourceReference())

  def stepCheckSuccessComputerGetComputerPartitionCall(self, sequence, **kw):
    """
    Check that Computer.getComputerPartitionList is successfully called.
    """
    computer_guid = sequence["computer_reference"]
    computer_uid = sequence["computer_uid"]
    erp5_computer = self.portal.portal_catalog.unrestrictedSearchResults(
        uid=computer_uid)[0].getObject()
    computer_partition_amount = len([x for x in \
      erp5_computer.contentValues(portal_type="Computer Partition") \
      ])

    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer = self.slap.registerComputer(computer_guid)
    computer_partition_list = computer.getComputerPartitionList()
    self.assertEquals(computer_partition_amount,
                      len(computer_partition_list))

  def stepCheckSuccessComputerPartitionGetIdCall(self, sequence, **kw):
    """
    Check that slap.registerComputerPartition is successfully called.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference_list"][0]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)
    self.assertEquals(partition_id, computer_partition.getId())

  def stepCheckSuccessSoftwareReleaseGetURICall(self, sequence, **kw):
    """
    Check that SoftwareRelease.getURI is successfully called.
    """
    url = sequence["software_release_uri"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    software_release = self.slap.registerSoftwareRelease(url)
    self.assertEquals(url, software_release.getURI())

  def stepCheckUnauthorizedComputerGetSoftwareReleaseListCall(self, sequence,
      **kw):
    """
    Check that Computer.getSoftwareReleaseList raise NotFoundError is the
    computer doesn't exist.
    """
    computer_guid = sequence.get("computer_reference", str(random()))
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer = self.slap.registerComputer(computer_guid)
    self.assertRaises(slap.Unauthorized, computer.getSoftwareReleaseList)

  def stepCheckEmptyComputerGetSoftwareReleaseListCall(self, sequence, **kw):
    """
    Check that Computer.getSoftwareReleaseList returns an empty list.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer = self.slap.registerComputer(computer_guid)
    self.assertEquals([], [q for q in computer.getSoftwareReleaseList() \
      if q.getState() != 'destroyed'])

  def stepCheckDestroyedStateGetSoftwareReleaseListCall(self, sequence, **kw):
    """
    Check that Computer.getSoftwareReleaseList returns software release
    associated to the computer.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer = self.slap.registerComputer(computer_guid)
    self.assertEquals(1, len(computer.getSoftwareReleaseList()))
    software_release = computer.getSoftwareReleaseList()[0]
    self.assertEqual('destroyed', software_release.getState())

  def stepCheckSuccessComputerGetSoftwareReleaseListCall(self, sequence, **kw):
    """
    Check that Computer.getSoftwareReleaseList returns software release
    associated to the computer.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer = self.slap.registerComputer(computer_guid)
    self.assertEquals(1, len(computer.getSoftwareReleaseList()))
    self.assertTrue(isinstance(computer.getSoftwareReleaseList()[0],
                               slap.SoftwareRelease))

  def stepCheckNameErrorSoftwareReleaseBuildingAfterRegisterCall(self,
      sequence, **kw):
    """
    Check that calling SoftwareRelease.building after just registration raises a
    NotFoundError
    """
    url = sequence["software_release_uri"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    software_release = self.slap.registerSoftwareRelease(url)

    self.assertRaises(NameError, software_release.building)

  def stepCheckNotFoundSoftwareReleaseDestroyedCall(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    software_release = self.slap.registerSoftwareRelease(
        sequence['software_release_uri'])
    # Note: Hackish
    software_release._computer_guid = computer_guid
    self.assertRaises(slap.NotFoundError, software_release.destroyed)

  def stepCheckNameErrorSoftwareReleaseDestroyedAfterRegisterCall(self, sequence,
      **kw):
    url = sequence["software_release_uri"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    software_release = self.slap.registerSoftwareRelease(url)

    self.assertRaises(NameError, software_release.destroyed)

  def stepCheckNameErrorSoftwareReleaseAvailableAfterRegisterCall(self, sequence,
      **kw):
    """
    Check that calling SoftwareRelease.available after just registration raises a
    NotFoundError
    """
    url = sequence["software_release_uri"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    software_release = self.slap.registerSoftwareRelease(url)

    self.assertRaises(NameError, software_release.available)

  def stepCheckNameErrorSoftwareReleaseErrorAfterRegisterCall(self, sequence,
      **kw):
    """
    Check that calling SoftwareRelease.error after just registration raises a
    NotFoundError
    """
    url = sequence["software_release_uri"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    software_release = self.slap.registerSoftwareRelease(url)

    self.assertRaises(NameError, software_release.error, "ErrorLog")

  def stepCheckNotFoundComputerPartitionBuildingAfterRegisterCall(self, sequence,
      **kw):
    """
    Check that calling ComputerPartition.building after just registrationraises a
    NotFoundError
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference_list"][0]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertRaises(slap.NotFoundError, computer_partition.building)

  def stepCheckNotFoundComputerPartitionAvailableAfterRegisterCall(self,
      sequence, **kw):
    """
    Check that calling ComputerPartition.available after just registration
    raises a NotFoundError
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference_list"][0]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertRaises(slap.NotFoundError, computer_partition.available)

  def stepCheckSuccessComputerPartitionDestroyedCall(self, sequence, **kw):
    """
    Check that calling ComputerPartition.available raises an Unauthorized error
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)
    computer_partition.destroyed()

  def stepCheckRaisesNotFoundComputerPartitionDestroyedCall(self, sequence,
      **kw):
    """
    Check that calling ComputerPartition.available raises an Unauthorized error
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)
    self.assertRaises(slap.NotFoundError, computer_partition.destroyed)

  def stepCheckNotFoundComputerPartitionErrorAfterRegisterCall(self, sequence,
      **kw):
    """
    Check that calling ComputerPartition.error after just registration raises a
    NotFoundError
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference_list"][0]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    self.slap.registerComputerPartition(
        computer_guid, partition_id)

  def stepCheckSuccessComputerPartitionErrorCall(self, sequence, **kw):
    """
    Check that calling ComputerPartition.error works.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)
    computer_partition.error("ErrorLog")

  def stepSelectCurrentlyUsedSalePackingListUid(self, sequence, **kw):
    """Sets sale_packing_list_uid to currently used to mach Computer Partition
    and Software Instance"""
    software_instance = self.portal.portal_catalog.getResultValue(
        portal_type="Software Instance",
        default_aggregate_uid=sequence['computer_partition_uid'])
    delivery = software_instance.getCausalityValue(
        portal_type="Sale Packing List")
    if delivery is None:
      order = software_instance.getCausalityValue(
          portal_type="Sale Order")
      delivery = order.getCausalityRelatedValue(
          portal_type="Sale Packing List")
    sequence.edit(sale_packing_list_uid=delivery.getUid())

  def stepCheckSalePackingListErrorText(self, sequence, **kw):
    """
    Check that the sale packing list has an error log
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    self.assertFalse(packing_list.getComment('').endswith("ErrorLog"))

  def stepCheckSalePackingListNoErrorText(self, sequence, **kw):
    """
    Check that the sale packing list has no error log
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    self.assertFalse(packing_list.getComment('').endswith("ErrorLog"))

  def stepCheckNotFoundComputerPartitionGetSoftwareReleaseAfterRegisterCall(
      self, sequence, **kw):
    """
    Check that calling ComputerPartition.getSoftwareRelease after just
    registration raises a NotFoundError
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference_list"][0]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertRaises(slap.NotFoundError, computer_partition.getSoftwareRelease)

  def stepCheckSuccessComputerPartitionGetSoftwareReleaseCall(self, sequence,
      **kw):
    """
    Check that calling ComputerPartition.getSoftwareRelease works.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    url = sequence["software_release_uri"]
    software_release = computer_partition.getSoftwareRelease()
    self.assertTrue(isinstance(software_release, slap.SoftwareRelease))
    self.assertEquals(url, software_release.getURI())

  def stepCheckSuccessComputerPartitionGetInstanceParameterDictCall(self,
      sequence, **kw):
    """
    Check that slap.registerComputerPartition is successfully called.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    computer_partition.getInstanceParameterDict()

  def stepFillTimestamp(self, sequence, **kw):
    get = self.portal.portal_catalog.getResultValue
    timestamp = int(get(uid=sequence['computer_partition_uid']\
      ).getModificationDate())
    instance = get(uid=sequence['software_instance_uid'])
    newtimestamp = int(instance.getBangTimestamp(int(
      instance.getModificationDate())))
    if (newtimestamp > timestamp):
      timestamp = newtimestamp
    sequence['partition_timestamp'] = str(timestamp)

  def stepCheckMinimalParametersTransmitted(self, sequence, **kw):
    """
    Check that slap.registerComputerPartition raises a NotFound error
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    result = computer_partition.getInstanceParameterDict()
    self.assertTrue(isinstance(result, dict))
    software_release_uri = sequence['software_release_uri']
    expected = {
        'slap_computer_id': computer_guid,
        'slap_computer_partition_id': partition_id,
        'slap_software_release_url': software_release_uri,
        'slap_software_type':
          sequence.get('requested_software_type',
                       'requested_software_type'),
        'slave_instance_list': [],
        'ip_list': [],
        'timestamp': sequence['partition_timestamp']
    }
    self.assertSameDict(expected, result)

  def stepSetSoftwareInstanceValidXML(self, sequence, **kw):
    """
    Set valid XML on the software instance
    """
    software_instance_uid = sequence["software_instance_uid"]
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)
    software_instance.edit(text_content="""<?xml version="1.0" encoding="utf-8"?>
<instance>

<parameter id="test_parameter">lala</parameter>
<parameter id="new_test_parameter">lala2</parameter>

</instance>""")

  def stepCheckRequestedComputerPartitionCleanParameterList(self, sequence, **kw):
    """Checks that only basic parameters are available in parameter dict"""
    requested_slap_computer_partition = sequence['requested_slap_computer_partition']
    instance_parameter_dict = requested_slap_computer_partition\
        .getInstanceParameterDict()
    self.assertEqual([],
        [q for q in instance_parameter_dict.keys() \
            if q not in DEFAULT_INSTANCE_DICT_PARAMETER_LIST])

  def stepCheckRaisesNotFoundComputerPartitionParameterDict(self, sequence, **kw):
    requested_slap_computer_partition = sequence['requested_slap_computer_partition']
    self.assertRaises(slap.NotFoundError,
      requested_slap_computer_partition.getInstanceParameterDict)

  def stepCheckRequestedComputerPartitionRequestedParameter(self, sequence,
      **kw):
    requested_slap_computer_partition = sequence['requested_slap_computer_partition']
    instance_parameter_dict = requested_slap_computer_partition\
        .getInstanceParameterDict()
    # check that all request parameters are available on new Computer Partition
    requested_parameter_dict = sequence['requested_parameter_dict']
    for k, v in requested_parameter_dict.iteritems():
      self.assertEqual(v, instance_parameter_dict.pop(k))
    self.assertEqual([],
        [q for q in instance_parameter_dict.keys() \
            if q not in DEFAULT_INSTANCE_DICT_PARAMETER_LIST])

  def stepCheckComputerPartitionGetInstanceParameterDictResult(self, sequence,
      **kw):
    """
    Check that slap.registerComputerPartition raises a NotFound error
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    result = computer_partition.getInstanceParameterDict()
    self.assertTrue(isinstance(result, dict))
    software_release_uri = sequence['software_release_uri']
    expected = {
        'new_test_parameter': 'lala2',
        'slap_computer_id': computer_guid,
        'slap_computer_partition_id': partition_id,
        'slap_software_release_url': software_release_uri,
        'slap_software_type':
          sequence.get('requested_software_type',
                       'requested_software_type'),
        'test_parameter': 'lala',
        'slave_instance_list': [],
        'ip_list': [],
        'timestamp': sequence['partition_timestamp']
    }
    self.assertSameDict(expected, result)

  def stepCheckStoppedComputerPartitionGetStateCall(self, sequence, **kw):
    """
    Check that ComputerPartition.getState return 'stopped'
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertEquals('stopped', computer_partition.getState())

  def stepCheckStartedComputerPartitionGetStateCall(self, sequence, **kw):
    """
    Check that ComputerPartition.getState return 'started'
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertEquals('started', computer_partition.getState())

  def stepCheckDestroyedComputerPartitionGetStateCall(self, sequence, **kw):
    """
    Check that ComputerPartition.getState return 'destroyed'
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence.get("computer_partition_reference",
        sequence['computer_partition_reference_list'][0])
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertEquals('destroyed', computer_partition.getState())

  def stepCheckComputerPartitionIsFree(self, sequence, **kw):
    computer_partition_uid = sequence["computer_partition_uid"]
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=computer_partition_uid)
    self.assertEqual('free', computer_partition.getSlapState())

  def stepSetHostingBeforeSetupStartDate(self, sequence, **kw):
    """
    Set date on Sale Packing List Line
    """
    computer_partition_uid = sequence["computer_partition_uid"]
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=computer_partition_uid)
    hosting_date = DateTime() - 1
    for movement in computer_partition.getAggregateRelatedValueList(
        portal_type=self.sale_packing_list_line_portal_type):
      if movement.getResource() == \
          movement.portal_preferences.getPreferredInstanceHostingResource():
        movement.edit(start_date=hosting_date)

  def stepCheckPackingListAmountTwoComputerPartition(self, sequence, **kw):
    computer_partition_uid = sequence["computer_partition_uid"]
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=computer_partition_uid)
    self.assertEqual(2, len(computer_partition.getAggregateRelatedList(
        portal_type=self.sale_packing_list_line_portal_type)))

  def stepSetHostingAfterSetupStartDate(self, sequence, **kw):
    """
    Set date on Sale Packing List Line
    """
    computer_partition_uid = sequence["computer_partition_uid"]
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=computer_partition_uid)
    hosting_date = DateTime() + 1
    for movement in computer_partition.getAggregateRelatedValueList(
        portal_type=self.sale_packing_list_line_portal_type):
      if movement.getResource() == \
          movement.portal_preferences.getPreferredInstanceHostingResource():
        movement.edit(start_date=hosting_date)

  def _checkComputerPartitionAndRelatedSoftwareInstance(self,
      computer_partition):
    sale_packing_list_line_list = computer_partition\
        .getAggregateRelatedValueList(
            portal_type=self.sale_packing_list_line_portal_type)
    self.assertEqual(2, len(sale_packing_list_line_list))
    sale_packing_list_line = sale_packing_list_line_list[0]
    software_instance = sale_packing_list_line.getAggregateValue(
        portal_type=self.software_instance_portal_type)

    software_instance_sale_packing_list_line_list = software_instance\
        .getAggregateRelatedList(
            portal_type=self.sale_packing_list_line_portal_type)
    self.assertEqual(2, len(software_instance_sale_packing_list_line_list))

  def _checkSoftwareInstanceAndRelatedPartition(self, software_instance,
      partition_portal_type=computer_partition_portal_type):
    # There should be two Sale Packing List Line
    sale_packing_list_line_list = software_instance\
        .getAggregateRelatedValueList(
            portal_type=self.sale_packing_list_line_portal_type)
    if (software_instance.getSlapState() == "start_requested"):
      expected_count = 2
    else:
      expected_count = 1

    self.assertEqual(expected_count, len(sale_packing_list_line_list))
    sale_packing_list_line = sale_packing_list_line_list[0]

    # This Sale Packing List Line shall have only one Computer Partition
    computer_partition_list = sale_packing_list_line.getAggregateValueList(
        portal_type=partition_portal_type)
    self.assertEqual(1, len(computer_partition_list))

    computer_partition = computer_partition_list[0]

    # This Computer Partition shall have two Sale Packing List Line related
    computer_partition_sale_packing_list_line_list = computer_partition\
        .getAggregateRelatedValueList(
            portal_type=self.sale_packing_list_line_portal_type)
    self.assertEqual(expected_count, len(computer_partition_sale_packing_list_line_list))

  def stepCheckPersonRequestedSoftwareInstanceAndRelatedComputerPartition(self,
    sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])
    # in this test it is required to assume that requested_reference
    computer_partition = self._softwareInstance_getComputerPartition(
      software_instance)
    # There should be only one Sale Packing List Line
    sale_packing_list_line_list = self.portal.portal_catalog(
      portal_type=self.sale_packing_list_line_portal_type,
      default_aggregate_uid=software_instance.getUid(),
      default_resource_uid=self.portal.restrictedTraverse(self.portal\
        .portal_preferences.getPreferredInstanceSetupResource()).getUid()
    )
    self.assertEqual(1, len(sale_packing_list_line_list))
    sale_packing_list_line = sale_packing_list_line_list[0]
    # This Sale Packing List Line shall have only one Computer Partition
    computer_partition_list = sale_packing_list_line.getAggregateValueList(
        portal_type='Computer Partition')
    self.assertEqual(1, len(computer_partition_list))

    computer_partition = computer_partition_list[0]

    # This Computer Partition shall have only Sale Packing List Line related
    computer_partition_sale_packing_list_line_list = []
    for delivery_line in computer_partition\
        .getAggregateRelatedValueList(
            portal_type=self.sale_packing_list_line_portal_type):
      if sequence['software_instance_uid'] in delivery_line\
          .getAggregateUidList() and delivery_line\
          .getResource() == self.portal.portal_preferences\
            .getPreferredInstanceSetupResource():
        computer_partition_sale_packing_list_line_list.append(delivery_line)
    self.assertEqual(1, len(computer_partition_sale_packing_list_line_list))

    # There should be only one Sale Order Line
    sale_order_line_list = software_instance\
        .getAggregateRelatedValueList(
            portal_type=self.sale_order_line_portal_type)
    self.assertEqual(1, len(sale_order_line_list))
    sale_order_line = sale_order_line_list[0]
    # This Sale Order Line shall have only one Computer Partition
    computer_partition_list = sale_order_line.getAggregateValueList(
        portal_type='Computer Partition')
    self.assertEqual(1, len(computer_partition_list))

    computer_partition = computer_partition_list[0]

    # This Computer Partition shall have only Sale Order Line related
    computer_partition_sale_order_line_list = []
    for order_line in computer_partition\
        .getAggregateRelatedValueList(
            portal_type=self.sale_order_line_portal_type):
      if sequence['software_instance_uid'] in order_line.getAggregateUidList():
        computer_partition_sale_order_line_list.append(order_line)
    self.assertEqual(1, len(computer_partition_sale_order_line_list))

  def stepCheckSoftwareInstanceAndRelatedComputerPartition(self,
      sequence, **kw):
    self.stepCheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck(sequence, **kw)
    software_instance_uid = sequence['software_instance_uid']
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)
    self._checkSoftwareInstanceAndRelatedPartition(software_instance)

  def stepCheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck(self,
      sequence, **kw):
    software_instance_uid = sequence['software_instance_uid']
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)
    # There should be only one predecessor
    predecessor_value_list = software_instance.getPredecessorValueList()
    self.assertEqual(1, len(predecessor_value_list))

    sequence.edit(
      requested_software_instance_uid=predecessor_value_list[0].getUid(),
      requested_software_instance_reference=predecessor_value_list[0].getReference())

  def stepCheckRequestedSoftwareInstanceAndRelatedComputerPartition(self,
      sequence, **kw):
    software_instance_uid = sequence['software_instance_uid']
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)
    # There should be only one predecessor
    predecessor_list = software_instance.getPredecessorValueList()
    self.assertEqual(1, len(predecessor_list))
    predecessor = predecessor_list[0]

    # This predecessor shall have only one related predecessor
    self.assertEqual(1, len(predecessor.getPredecessorRelatedList()))

    self._checkSoftwareInstanceAndRelatedPartition(predecessor)

  def stepStoreComputerReference(self, sequence):
    sequence['original_computer_reference'] = sequence['computer_reference']

  def stepRestoreComputerReference(self, sequence):
    sequence['computer_reference'] = sequence['original_computer_reference']

  def stepSetRequestedFilterParameterDict(self, sequence):
    sequence['requested_filter_dict'] = dict(
      computer_guid=sequence['computer_reference'])

  def stepSetCurrentSoftwareInstanceRequested(self, sequence):
    sequence.edit(
      requester_software_instance_uid=sequence['software_instance_uid'],
      requester_software_instance_reference=sequence[
        'software_instance_reference'],
      software_instance_uid=sequence['requested_software_instance_uid'],
      software_instance_reference=sequence[
        'requested_software_instance_reference']
    )

  def stepSetCurrentSoftwareInstanceRequester(self, sequence):
    sequence.edit(
      software_instance_uid=sequence['requester_software_instance_uid']
    )

  def stepCheckSlaveInstanceSecurityWithDifferentCustomer(self, sequence):
    software_instance_uid = sequence["software_instance_uid"]
    portal_membership = self.portal.portal_membership
    username = portal_membership.getAuthenticatedMember().getUserName()
    self.login()
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)
    self.failIfUserCanViewDocument(username, software_instance)
    self.failIfUserCanAccessDocument(username, software_instance)
    self.login(username)

  def stepCheckTwoSlaveInstanceRequest(self, sequence):
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=sequence["computer_partition_uid"])
    sale_packing_list_line_list = computer_partition.getAggregateRelatedValueList(
        portal_type=self.sale_packing_list_line_portal_type)
    portal_type_list = [self.software_instance_portal_type,
        self.slave_instance_portal_type]
    instance_list = filter(None, [obj.getAggregateValue(portal_type=portal_type_list) \
        for obj in sale_packing_list_line_list])
    portal_type_list = [instance.getPortalType() for instance in instance_list]
    expected_portal_type_list = [self.slave_instance_portal_type,
        self.slave_instance_portal_type,
        self.slave_instance_portal_type,
        self.slave_instance_portal_type,
        self.software_instance_portal_type,
        self.software_instance_portal_type]
    self.assertEquals(expected_portal_type_list, sorted(portal_type_list))
    computer_partition_list = [obj.getAggregateValue(
      portal_type=self.computer_partition_portal_type) \
          for obj in sale_packing_list_line_list]
    uid_list = [computer_partition.getUid() \
        for computer_partition in computer_partition_list]
    self.assertEquals(1, len(set(uid_list)))

  def stepCheckSlaveInstanceReady(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    self.assertEquals(self.slave_instance_portal_type,
        slave_instance.getPortalType())
    sale_order_line = slave_instance.getAggregateRelatedValue(
        portal_type=self.sale_order_line_portal_type)
    self.assertEquals("confirmed", sale_order_line.getSimulationState())
    sale_packing_list_line = slave_instance.getAggregateRelatedValue(
        portal_type=self.sale_packing_list_line_portal_type)
    self.assertNotEquals(sale_packing_list_line.getAggregate(
      portal_type=self.computer_partition_portal_type), None)

  def stepCheckSlaveInstanceAssociationWithSoftwareInstance(self, sequence):
    portal_catalog = self.portal.portal_catalog
    computer_partition_reference_list = \
        sequence['computer_partition_reference_list']
    for reference in computer_partition_reference_list:
      computer_partition = portal_catalog.getResultValue(
          portal_type="Computer Partition", reference=reference)
      sale_packing_list_line_list = portal_catalog(
          portal_type="Sale Packing List Line",
          aggregate_relative_url=computer_partition.getRelativeUrl())
      software_release_uri_list = []
      for sale_packing_list_line in sale_packing_list_line_list:
        software_release_uri = sale_packing_list_line.getResultValue(
            portal_type="Software Release")
        software_release_uri_list.append(software_release_uri.getUrlString())
      self.assertEquals(1, len(set(software_release_uri_list)))

  def stepCheckSlaveInstanceAllocationWithTwoDifferentSoftwareInstance(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    self.assertEquals(self.slave_instance_portal_type,
        slave_instance.getPortalType())
    sale_packing_list_line = slave_instance.getAggregateRelatedValue(
        portal_type=self.sale_packing_list_line_portal_type)
    software_release = sale_packing_list_line.getAggregateValue(
        portal_type=self.software_release_portal_type)
    sale_packing_list_line_list = software_release.aggregateRelatedValues(
        portal_type=self.sale_packing_list_line_portal_type)
    computer_partition_list = [obj.getAggregate(
      portal_type=self.computer_partition_portal_type)\
          for obj in sale_packing_list_line_list]
    self.assertEquals(computer_partition_list[0],
        computer_partition_list[1])
    self.assertEquals(4, len(computer_partition_list))

  def stepCheckSlaveInstanceNotReady(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    self.assertEqual(slave_instance.getAggregateValue(
        portal_type='Computer Partition'))
    slave_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(slave_instance.getAggregateValue(
        portal_type='Computer Partition'))

  def stepSelectSlaveInstanceFromOneComputerPartition(self, sequence):
    slave_instance = self._getSlaveInstanceFromCurrentComputerPartition(sequence)
    sequence.edit(software_instance_uid=slave_instance.getUid(),
        software_instance_reference=slave_instance.getReference())

  def stepCheckEmptySlaveInstanceListFromOneComputerPartition(self, sequence):
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        partition_id)
    parameter_dict = computer_partition.getInstanceParameterDict()
    slave_instance_list = parameter_dict["slave_instance_list"]
    self.assertEquals([], slave_instance_list)

  def stepCheckSlaveInstanceListFromOneComputerPartition(self, sequence,
          expected_amount=1):
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        partition_id)
    parameter_dict = computer_partition.getInstanceParameterDict()
    self.assertEquals(
        sequence.get('requested_software_type',
                     'requested_software_type'),
        parameter_dict["slap_software_type"])
    slave_instance_list = parameter_dict["slave_instance_list"]
    self.assertEquals(expected_amount, len(slave_instance_list))
    for slave_instance in slave_instance_list:
      self.assertEquals(
          sequence.get('requested_software_type',
                       'requested_software_type'),
          slave_instance["slap_software_type"])

  def stepCheckTwoSlaveInstanceListFromOneComputerPartition(self, sequence):
    self.stepCheckSlaveInstanceListFromOneComputerPartition(sequence,
        expected_amount=2)

  def stepCheckSlaveInstanceAccessUsingCurrentSoftwareInstanceUser(self, sequence):
    slave_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    portal_membership = self.portal.portal_membership
    username = portal_membership.getAuthenticatedMember().getUserName()
    self.assertUserCanViewDocument(username, slave_instance)
    self.assertUserCanAccessDocument(username, slave_instance)

  def stepSlapLoginSoftwareInstanceFromCurrentSoftwareInstance(self, sequence):
    software_instance = self._getSoftwareInstanceFromCurrentComputerPartition(
        sequence)
    self.assertNotEquals(None, software_instance)
    self.stepSlapLogout()
    global REMOTE_USER
    REMOTE_USER = software_instance.getReference()
    self.login(software_instance.getReference())

  def _getSoftwareInstanceFromCurrentComputerPartition(self, sequence):
    query = ComplexQuery(
        Query(aggregate_uid=sequence['computer_partition_uid']),
        Query(aggregate_portal_type=self.software_instance_portal_type),
        operator="AND")
    software_instance = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Packing List Line",
        sort_on=(('movement.start_date', 'DESC'),),
        query=query).getAggregateValue(portal_type="Software Instance")
    return software_instance

  def _getSlaveInstanceFromCurrentComputerPartition(self, sequence):
    query = ComplexQuery(
        Query(aggregate_uid=sequence['computer_partition_uid']),
        Query(aggregate_portal_type=self.slave_instance_portal_type),
        operator="AND")
    slave_instance = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Packing List Line",
        query=query).getAggregateValue(portal_type=self.slave_instance_portal_type)
    return slave_instance

  def stepRequestDestroySoftwareInstanceFromCurrentComputerPartition(self, sequence):
    instance = self._getSoftwareInstanceFromCurrentComputerPartition(
        sequence)
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    instance.requestDestroy(
        software_release=instance.getUrlString(),
        instance_xml=instance.getTextContent(),
        software_type=instance.getSourceReference(),
        sla_xml=instance.getSlaXml(),
        shared=shared,
        )

  def stepStartSoftwareInstanceFromCurrentComputerPartition(self, sequence):
    instance = self._getSoftwareInstanceFromCurrentComputerPartition(
        sequence)
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    instance.requestStart(
        software_release=instance.getUrlString(),
        instance_xml=instance.getTextContent(),
        software_type=instance.getSourceReference(),
        sla_xml=instance.getSlaXml(),
        shared=shared,
        )

  def stepRequestStopSoftwareInstanceFromCurrentComputerPartition(self,
      sequence):
    instance = self._getSoftwareInstanceFromCurrentComputerPartition(
        sequence)
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    instance.requestStop(
        software_release=instance.getUrlString(),
        instance_xml=instance.getTextContent(),
        software_type=instance.getSourceReference(),
        sla_xml=instance.getSlaXml(),
        shared=shared,
        )

  def stepCheckSalePackingListFromSlaveInstanceAccessUsingSoftwareInstanceUser(self,
      sequence):
    portal_membership = self.portal.portal_membership
    sale_packing_list_line = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Packing List Line",
        uid=sequence["sale_packing_list_line_uid"])
    username = portal_membership.getAuthenticatedMember().getUserName()
    self.assertUserCanViewDocument(username, sale_packing_list_line)
    self.failIfUserCanModifyDocument(username, sale_packing_list_line)

  def stepCheckSaleOrderFromSlaveInstanceAccessUsingSoftwareInstanceUser(self,
      sequence):
    portal_membership = self.portal.portal_membership
    sale_order = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Order",
        uid=sequence["sale_order_uid"])
    username = portal_membership.getAuthenticatedMember().getUserName()
    self.assertUserCanViewDocument(username, sale_order)
    self.failIfUserCanModifyDocument(username, sale_order)

  def stepCheckHostingSubscriptionFromSlaveInstanceAccessUsingSoftwareInstanceUser(self,
      sequence):
    portal_membership = self.portal.portal_membership
    sale_packing_list_line = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Packing List Line",
        uid=sequence["sale_packing_list_line_uid"])
    hosting_subscription = sale_packing_list_line.getAggregateValue(
        portal_type="Hosting Subscription")
    username = portal_membership.getAuthenticatedMember().getUserName()
    self.assertUserCanViewDocument(username, hosting_subscription)
    self.failIfUserCanModifyDocument(username, hosting_subscription)

  def stepStoreSaleOrderFromSlaveInstance(self, sequence):
    sale_order_line = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Order Line",
        aggregate_reference=sequence["software_instance_reference"])
    sequence.edit(sale_order_line_uid=sale_order_line.getUid(),
        sale_order_uid=sale_order_line.getParent().getUid())

  def stepStoreSalePackingListLineFromSlaveInstance(self, sequence):
    sale_packing_list_line = self.portal.portal_catalog.getResultValue(
        portal_type="Sale Packing List Line",
        aggregate_uid=sequence["software_instance_uid"])
    sequence.edit(sale_packing_list_line_uid=sale_packing_list_line.getUid(),
        sale_packing_list_uid=sale_packing_list_line.getParent().getUid())

  def stepSetConnectionXmlToSlaveInstance(self, sequence):
    computer_reference = sequence["computer_reference"]
    computer_partition_reference = sequence["computer_partition_reference"]
    site_url = "https://www.example.com:8080/"
    connection_dict = dict(site_url=site_url)
    slave_reference = sequence["software_instance_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer_partition = self.slap.registerComputerPartition(
        computer_reference, computer_partition_reference)
    computer_partition.setConnectionDict(connection_dict)
    sequence.edit(site_url=site_url)
    connection_dict["site_url"] += "DeF45uef"
    computer_partition.setConnectionDict(connection_dict,
        slave_reference)
    sequence.edit(slave_instance_site_url=connection_dict["site_url"])

  def stepCheckConnectionXmlFromSlaveInstance(self, sequence):
    portal_catalog = self.portal.portal_catalog
    slave_instance = portal_catalog.getResultValue(
        reference=sequence["software_instance_reference"])
    self.assertTrue(sequence["slave_instance_site_url"] in \
        slave_instance.getConnectionXml())

  def stepCheckConnectionXmlFromSoftwareInstance(self, sequence):
    software_instance = self.portal.portal_catalog.getResultValue(
      portal_type="Software Instance")
    self.assertTrue("%s</parameter>" % sequence["site_url"] in \
        software_instance.getConnectionXml())

  def stepSlaveInstanceStarted(self, sequence):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence["software_instance_uid"])
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    instance.requestStart(
        software_release=instance.getUrlString(),
        instance_xml=instance.getTextContent(),
        software_type=instance.getSourceReference(),
        sla_xml=instance.getSlaXml(),
        shared=shared,
        )

  def stepSlaveInstanceStopped(self, sequence):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence["software_instance_uid"])
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    instance.requestStop(
        software_release=instance.getUrlString(),
        instance_xml=instance.getTextContent(),
        software_type=instance.getSourceReference(),
        sla_xml=instance.getSlaXml(),
        shared=shared,
        )

  def stepSetDeliveryLineAmountEqualZero(self, sequence):
    sequence.edit(delivery_line_amount=0)

  def stepSetDeliveryLineAmountEqualTwo(self, sequence):
    sequence.edit(delivery_line_amount=2)

  def stepSetDeliveryLineAmountEqualOne(self, sequence):
    sequence.edit(delivery_line_amount=1)

  def stepSetRandomRequestedReference(self, sequence, **kw):
    sequence['requested_reference'] = self.id() + str(random())

  def stepSetRandomRequestedReferenceAndTitle(self, sequence, **kw):
    sequence['requested_reference'] = self.id() + str(random())
    sequence['software_title'] = sequence['requested_reference']

  def stepRenameCurrentSoftwareInstanceDead(self, sequence, **kw):
    """Renames software instance using external API"""

    # Note: In order to keep step list as it is it hackishly access
    # needed details required to login through SlapTool
    software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid']
    )

    # login into slap
    global REMOTE_USER
    REMOTE_USER = software_instance.getReference()

    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)

    slap_computer_partition = self.slap.registerComputerPartition(
        software_instance.getAggregateValue(
          portal_type='Computer Partition').getParentValue().getReference(),
        software_instance.getAggregateValue(
          portal_type='Computer Partition').getReference()
    )

    slap_computer_partition.rename('%sDead' % software_instance.getTitle())

  def stepCheckTreeHasARootSoftwareInstance(self, sequence, **kw):
    hosting_subscription_uid = sequence['hosting_subscription_uid']

    hosting_subscription = self.portal.portal_catalog.getResultValue(
      uid=hosting_subscription_uid,
    )
    root_software_instance = self.portal.portal_catalog.getResultValue(
      root_uid=hosting_subscription_uid,
      title=hosting_subscription.getTitle(),
    )

    self.failIfEqual(root_software_instance, None,
                     "No root software instance")

  def stepSetSoftwareInstanceGetRootOfTheTree(self, sequence, **kw):
    hosting_subscription_uid = sequence['hosting_subscription_uid']

    hosting_subscription = self.portal.portal_catalog.getResultValue(
      uid=hosting_subscription_uid,
    )
    root_software_instance = self.portal.portal_catalog.getResultValue(
      root_uid=hosting_subscription_uid,
      title=hosting_subscription.getTitle(),
    )
    self.failIfEqual(root_software_instance, None,
                     "No root software instance")
    computer_partition_reference = self._softwareInstance_getComputerPartition(
      root_software_instance).getReference()
    sequence.edit(software_instance_uid=root_software_instance.getUid(),
                  computer_partition_reference=computer_partition_reference)

  def stepRequestCredentialFromWebSite(self, sequence, **kw):
    sequence['web_user_email'] = '%s@example.com' % random()
    sequence['web_user'] = '%s.%s' % (self.id(), random())
    self.portal.ERP5Site_newCredentialRequest(\
        first_name='Homer',
        last_name='Simpson',
        reference=sequence['web_user'],
        password='secret',
        default_email_text=sequence['web_user_email'],
        )

  def stepSubmitCredentialRequest(self, sequence, **kw):
    """Simulates click of user in email confirmation about account"""
    credential_request = self.portal.portal_catalog.getResultValue(
      portal_type='Credential Request',
      reference=sequence['web_user']
      )
    credential_request.submit()

  def stepLoginWebUser(self, sequence, **kw):
    self.login(sequence['web_user'])


class TestVifibSlapWebService(TestVifibSlapWebServiceMixin):
  ########################################
  # slap.initializeConnection
  ########################################

  @skip('Not implemented')
  def test_slap_initializeConnection(self):
    """
    Check authentification with the initializeConnection method
    """
    raise NotImplementedError

  ########################################
  # slap.registerOpenOrder
  ########################################

  @skip('Not implemented')
  def test_slap_registerOpenOrder(self):
    """
    """
    raise NotImplementedError

  ########################################
  # ComputerPartition.getId
  ########################################

  def test_ComputerPartition_getId(self):
    """
    Check the ComputerPartition.getId works
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionGetIdCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  ########################################
  # SoftwareRelease.getURI
  ########################################

  def test_SoftwareRelease_getURI(self):
    """
    Check that SoftwareRelease.getURI works.
    """
    sequence_list = SequenceList()
    sequence_string = '\
      SelectNewSoftwareReleaseUri \
      CheckSuccessSoftwareReleaseGetURICall \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  ########################################
  # ComputerPartition.started
  ########################################
  def test_ComputerPartition_started(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_started_computer_partition_sequence_string + """

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
        """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  ########################################
  # ComputerPartition.destroy
  ########################################

  def test_ComputerPartition_destroyed_raisesNoCleanupPackingList(self):
    """Checks that calling cp.destroy when there was no destroy request raises"""
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_installed_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionDestroyedCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_destroyed_worksOnInstalled(self):
    """Checks default destroy scenario on installed computer partition"""
    sequence_list = SequenceList()
    sequence_string = self.prepare_destroyed_computer_partition + """
      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_destroyed_multiplecalls(self):
    """Checks that destroyed action on free computer partition raises"""
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_installed_computer_partition_sequence_string + '\
      LoginTestVifibCustomer \
      SetSequenceSoftwareInstanceStateDestroyed \
      PersonRequestSoftwareInstance \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      SoftwareInstanceDestroyed \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckComputerPartitionIsFree \
      Logout \
      SlapLoginCurrentComputer \
      CheckRaisesNotFoundComputerPartitionDestroyedCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  ########################################
  # Person using PKI/Slap interface
  ########################################

  def _safe_revoke_certificate(self, person):
    user = getSecurityManager().getUser().getId()
    try:
      self.login('ERP5TypeTestCase')
      person.revokeCertificate()
    except ValueError, err:
      if 'No certificate for' in err.message:
        pass
      else:
        raise
    finally:
      self.login(user)

  def test_person_request_new_certificate(self):
    """Checks that Person is capable to ask for new certificate"""
    # XXX: Will be obsoleted by Products.ERP5.tests.testCertificateAuthority
    self.login()
    self.portal.portal_certificate_authority._checkCertificateAuthority()
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(
      'test_vifib_user_admin')
    self._safe_revoke_certificate(person)
    self.login('test_vifib_user_admin')
    certificate = person.getCertificate()
    self.assertTrue('CN=test_vifib_user_admin' in certificate['certificate'])

  def test_person_request_revoke_certificate(self):
    """Chekcs that Person is capable to ask for revocation of certificate"""
    # XXX: Will be obsoleted by Products.ERP5.tests.testCertificateAuthority
    self.login()
    self.portal.portal_certificate_authority._checkCertificateAuthority()
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(
      'test_vifib_user_admin')
    self._safe_revoke_certificate(person)
    self.login('test_vifib_user_admin')
    certificate = person.getCertificate()
    self.assertTrue('CN=test_vifib_user_admin' in certificate['certificate'])
    person.revokeCertificate()

  def test_person_request_new_certificate_twice(self):
    """Checks that if Person asks twice for a certificate the next call
       fails"""
    # XXX: Will be obsoleted by Products.ERP5.tests.testCertificateAuthority
    self.login()
    self.portal.portal_certificate_authority._checkCertificateAuthority()
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(
      'test_vifib_user_admin')
    self._safe_revoke_certificate(person)
    self.login('test_vifib_user_admin')
    certificate = person.getCertificate()
    self.assertTrue('CN=test_vifib_user_admin' in certificate['certificate'])
    self.assertRaises(ValueError, person.getCertificate)

  def test_person_request_certificate_for_another_person(self):
    """Checks that if Person tries to request ceritifcate for someone else it
    will fail"""
    # XXX: Will be obsoleted by Products.ERP5.tests.testCertificateAuthority
    from AccessControl import Unauthorized
    self.login()
    self.portal.portal_certificate_authority._checkCertificateAuthority()
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(
      'test_vifib_user_admin')
    self._safe_revoke_certificate(person)
    self.login('test_hr_admin')
    self.assertRaises(Unauthorized, person.getCertificate)

  def test_person_request_revoke_certificate_for_another_person(self):
    """Checks that if Person tries to request ceritifcate for someone else it
    will fail"""
    # XXX: Will be obsoleted by Products.ERP5.tests.testCertificateAuthority
    from AccessControl import Unauthorized
    self.login()
    self.portal.portal_certificate_authority._checkCertificateAuthority()
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(
      'test_vifib_user_admin')
    self._safe_revoke_certificate(person)
    self.login('test_vifib_user_admin')
    certificate = person.getCertificate()
    self.assertTrue('CN=test_vifib_user_admin' in certificate['certificate'])
    self.login('test_hr_admin')
    self.assertRaises(Unauthorized, person.revokeCertificate)

  ########################################
  # Other tests
  ########################################

  def test_person_from_credential_request_software_instance(self):
    """Checks that person created from web can use the system"""
    sequence_list = SequenceList()
    sequence_string = self.stabilise_accounting + \
        self.prepare_published_software_release + \
        self.prepare_formated_computer + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      Logout
      RequestCredentialFromWebSite
      Tic

      LoginDefaultUser
      SubmitCredentialRequest
      Tic
      CallAcceptSubmittedCredentialsAlarm
      Tic
      PayPayment
      Tic
      Logout

      """ + self.stabilise_accounting + """

      LoginWebUser
      PersonRequestSoftwareInstance
      Tic
      Logout

      LoginDefaultUser
      CallSlaposAllocateInstanceAlarm
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepPersonRequestCredentialUpdate(self, sequence, **kw):
    sequence['updated_last_name'] = 'Another'
    self.portal.ERP5Site_newPersonCredentialUpdate(
        first_name='Homer',
        last_name=sequence['updated_last_name'],
        reference=sequence['web_user'],
        password='secret',
        default_email_text=sequence['web_user_email'],
    )

  def stepCheckPersonUpdatedCredential(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    self.assertEqual(sequence['updated_last_name'], person.getLastName())

  def test_person_credential_update(self):
    """Checks that Credential Update works in vifib environment."""
    sequence_list = SequenceList()
    sequence_string = """
      Logout
      RequestCredentialFromWebSite
      Tic

      LoginDefaultUser
      SubmitCredentialRequest
      Tic
      CallAcceptSubmittedCredentialsAlarm
      Tic
      Logout

      LoginWebUser
      PersonRequestCredentialUpdate
      Tic
      Logout

      LoginDefaultUser
      CallAcceptSubmittedCredentialsAlarm
      Tic

      LoginWebUser
      CheckPersonUpdatedCredential
      Logout

      CallSlaposUpdateDeliveryCausalityStateAlarm
      CleanTic

      CallVifibSolveAutomaticallyAlarm
      CleanTic

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

# class IComputerPartition
#   def started():
#   def stopped():
#   def request(software_release, partition_reference):
#   def setUsage(usage_log):
# class IComputer(Interface):
#   def reportUsage(computer_partition_list):

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapWebService))
  return suite
