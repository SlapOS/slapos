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
from AccessControl.SecurityManagement import newSecurityManager
from Products.ERP5Type.Errors import UnsupportedWorkflowMethod
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import expectedFailure
from Products.ERP5Type.tests.backportUnittest import skip
from Products.ERP5Type.tests.SecurityTestCase import AssertNoPermissionMethod, \
    AssertPermissionMethod
from Products.ERP5Type import Permissions
from Products.ZSQLCatalog.SQLCatalog import Query, ComplexQuery
from VifibMixin import testVifibMixin
from random import random
from slapos import slap
import urllib
import urlparse
import httplib
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
    'slap_server_url',
    'slap_software_release_url',
    'slap_software_type',
    "slave_instance_list"
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
  if getattr(HTTPConnection, '_original_request', None) is None:
    HTTPConnection.request = HTTPConnection._original_request
    delattr(HTTPConnection, '_original_request')


class TestVifibSlapWebServiceMixin(testVifibMixin):
  """
  Check the slap behaviour on ERP5 documents
  """
  computer_partition_portal_type = "Computer Partition"
  computer_portal_type = "Computer"
  hosting_subscription_portal_type = "Hosting Subscription"
  purchase_packing_list_line_portal_type = "Purchase Packing List Line"
  purchase_packing_list_portal_type = "Purchase Packing List"
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

  def afterSetUp(self):
    fakeSlapAuth()
    testVifibMixin.afterSetUp(self)
    self.server_url = self.portal.portal_slap.absolute_url()

  def beforeTearDown(self):
    unfakeSlapAuth()
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
    delivery_line_list = [q for q in computer_partition
        .getAggregateRelatedValueList(
          portal_type=self.sale_packing_list_line_portal_type)
        if q.getResource() == resource]
    self.assertEqual(0, len(delivery_line_list))

  def _checkComputerPartitionSalePackingListState(self, state,
      resource, sequence):
    delivery_line_amount = sequence.get("delivery_line_amount", 1)
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=sequence['computer_partition_uid'])
    delivery_line_list = [q for q in computer_partition
        .getAggregateRelatedValueList(
          portal_type=self.sale_packing_list_line_portal_type)
        if q.getResource() == resource
        and q.getSimulationState() == state]
    self.assertEqual(delivery_line_amount, len(delivery_line_list))

  def _checkComputerPartitionNoSalePackingList(self, resource, sequence):
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=sequence['computer_partition_uid'])
    delivery_line_list = [q for q in computer_partition
        .getAggregateRelatedValueList(
          portal_type=self.sale_packing_list_line_portal_type)
        if q.getResource() == resource]
    self.assertEqual(0, len(delivery_line_list))

  def stepCheckComputerPartitionInstanceCleanupSalePackingListDoesNotExists(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListDoesNotExists(
        self.portal.portal_preferences.getPreferredInstanceCleanupResource(),
        sequence)

  def stepCheckComputerPartitionInstanceCleanupSalePackingListCancelled(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('cancelled',
        self.portal.portal_preferences.getPreferredInstanceCleanupResource(),
        sequence)

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

  def stepCheckComputerPartitionInstanceSetupSalePackingListCancelled(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('cancelled',
        self.portal.portal_preferences.getPreferredInstanceSetupResource(),
        sequence)

  def stepCheckComputerPartitionInstanceSetupSalePackingListConfirmed(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('confirmed',
        self.portal.portal_preferences.getPreferredInstanceSetupResource(),
        sequence)

  def stepCheckComputerPartitionInstanceSetupSalePackingListStarted(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('started',
        self.portal.portal_preferences.getPreferredInstanceSetupResource(),
        sequence)

  def stepCheckComputerPartitionInstanceSetupSalePackingListStopped(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('stopped',
        self.portal.portal_preferences.getPreferredInstanceSetupResource(),
        sequence)

  def stepCheckComputerPartitionInstanceSetupSalePackingListDelivered(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('delivered',
        self.portal.portal_preferences.getPreferredInstanceSetupResource(),
        sequence)

  def stepCheckComputerPartitionInstanceHostingSalePackingListCancelled(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('cancelled',
        self.portal.portal_preferences.getPreferredInstanceHostingResource(),
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

  def stepCheckComputerPartitionNoInstanceHostingSalePackingList(self,
      sequence, **kw):
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=sequence['computer_partition_uid'])
    delivery_line_list = [q for q in computer_partition
        .getAggregateRelatedValueList(
          portal_type=self.sale_packing_list_line_portal_type)
        if q.getResource() == self.\
          portal.portal_preferences.getPreferredInstanceHostingResource()]
    self.assertEqual(0, len(delivery_line_list))

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

  def stepCheckComputerPartitionAccoutingResourceSalePackingListCancelled(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('cancelled',
        self.portal.portal_catalog.getResultValue(
          uid=sequence['service_uid']).getRelativeUrl(),
        sequence)

  def stepCheckComputerPartitionAccoutingResourceSalePackingListConfirmed(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('confirmed',
        self.portal.portal_catalog.getResultValue(
          uid=sequence['service_uid']).getRelativeUrl(),
        sequence)

  def stepCheckComputerPartitionAccoutingResourceSalePackingListStarted(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('started',
        self.portal.portal_catalog.getResultValue(
          uid=sequence['service_uid']).getRelativeUrl(),
        sequence)

  def stepCheckComputerPartitionAccoutingResourceSalePackingListStopped(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('stopped',
        self.portal.portal_catalog.getResultValue(
          uid=sequence['service_uid']).getRelativeUrl(),
        sequence)

  def stepCheckComputerPartitionAccoutingResourceSalePackingListDelivered(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('delivered',
        self.portal.portal_catalog.getResultValue(
          uid=sequence['service_uid']).getRelativeUrl(),
        sequence)

  def stepPersonRequestSlaveInstance(self, sequence, **kw):
    kw = dict(instance_portal_type=self.slave_instance_portal_type,
              shared=True,
              software_type="SlaveInstance")
    self.stepPersonRequestSoftwareInstance(sequence, **kw)

  def stepPersonRequestSoftwareInstance(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    software_release = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_release_uid'])
    software_title = self.id() + str(random())
    person.requestSoftwareInstance(
      software_release=software_release.getUrlString(),
      software_title=software_title,
      instance_xml=self.minimal_correct_xml,
      **kw)
    transaction.commit()
    self.tic()
    # Note: This is tricky part. Workflow methods does not return nothing
    # so the only way is to find again the computer partition.
    # But only title can be passed, that is why random is used to avoid
    # duplication
    software_instance_portal_type = kw.get("instance_portal_type",
                                  self.software_instance_portal_type)
    software_instance_list = self.portal.portal_catalog(
        portal_type=software_instance_portal_type,
        title=software_title)
    self.assertEqual(1, len(software_instance_list))
    software_instance = software_instance_list[0]
    sequence.edit(
        root_software_instance_title=software_title,
        software_instance_uid=software_instance.getUid(),
        software_instance_reference=software_instance.getReference(),
        hosting_subscription_uid=software_instance.getAggregateRelatedValue(
          portal_type='Sale Order Line').getAggregateValue(
            portal_type='Hosting Subscription').getUid())

  def stepSetSelectedComputerPartition(self, sequence, **kw):
    """Sets in sequence computer partition parameters related to current
    software instance"""
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    delivery_line = [q for q in software_instance
        .getAggregateRelatedValueList(
          portal_type=self.sale_packing_list_line_portal_type)
        if q.getSimulationState() in ['confirmed', 'started', 'stopped']][0]
    computer_partition = delivery_line.getAggregateValue(
        portal_type=self.computer_partition_portal_type)
    sequence.edit(
      computer_partition_uid=computer_partition.getUid(),
      computer_partition_reference=computer_partition.getReference()
    )

  def stepRequestSoftwareInstanceDestroy(self, sequence, **kw):
    self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid']).requestDestroyComputerPartition()

  def stepRequestSoftwareInstanceDestroyRaisesValueError(self, sequence, **kw):
    self.assertRaises(ValueError, self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid']).requestDestroyComputerPartition)

  def stepRequestSoftwareInstanceStart(self, sequence, **kw):
    self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid']).requestStartComputerPartition()

  def stepRequestSoftwareInstanceStartRaisesValueError(self, sequence, **kw):
    self.assertRaises(ValueError, self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid']).requestStartComputerPartition)

  def stepRequestSoftwareInstanceStop(self, sequence, **kw):
    self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid']).requestStopComputerPartition()

  def stepRequestSoftwareInstallation(self, sequence, **kw):
    # based on WebSection_triggerSelectedSoftwareReleaseInstallation
    # XXX: Hardcoded values
    seller = self.portal.restrictedTraverse(
        "organisation_module/vifib_internet")
    currency = self.portal.restrictedTraverse("currency_module/EUR")
    # select a person
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()

    service = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredSoftwareSetupResource())

    computer = self.portal.portal_catalog.getResultValue(
        uid=sequence['computer_uid'])

    software_release = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_release_uid'])

    module = self.portal.getDefaultModule(
        portal_type=self.purchase_packing_list_portal_type)
    packing_list = module.newContent(
        portal_type=self.purchase_packing_list_portal_type,
        start_date=DateTime(),
        destination_section_value=person,
        destination_decision_value=person,
        source_administration_value=person,
        source_value=seller,
        source_section_value=seller,
        price_currency_value=currency,
    )
    packing_list.newContent(
      portal_type=self.purchase_packing_list_line_portal_type,
      resource_value=service,
      aggregate_value_list=[software_release, computer],
      quantity=1
    )

    self.portal.portal_workflow.doActionFor(packing_list, "confirm_action")

  def stepCheckComputerPartitionSaleOrderAggregatedList(self, sequence):
    portal_catalog = self.portal.portal_catalog
    sale_packing_list = portal_catalog.getResultValue(
        uid=sequence['sale_packing_list_uid'])
    sale_packing_list_line = sale_packing_list.objectValues()[0]
    computer_partition = sale_packing_list_line.getAggregateValue(
        portal_type=self.computer_partition_portal_type)
    sale_order_line_list = computer_partition.getAggregateRelatedValueList(
        portal_type="Sale Order Line")
    sale_order_line_1, sale_order_line_2 = sale_order_line_list
    self.assertEquals(sale_order_line_1.getAggregateValue(
                        portal_type=self.computer_partition_portal_type),
                      sale_order_line_2.getAggregateValue(
                        portal_type=self.computer_partition_portal_type))
    self.assertEquals(2, len(sale_order_line_list))
    sale_packing_line_list = computer_partition.getAggregateRelatedValueList(
        portal_type="Sale Packing List Line")
    self.assertEquals(2, len(sale_packing_line_list))
    sale_packing_list_line_1, sale_packing_list_line_2 = sale_packing_line_list
    self.assertEquals(sale_packing_list_line_1.getAggregateValue(
                        portal_type=self.software_release_portal_type),
                      sale_packing_list_line_2.getAggregateValue(
                        portal_type=self.software_release_portal_type))
    self.assertEquals(sale_packing_list_line_1.getAggregateValue(
                        portal_type=self.computer_partition_portal_type),
                      sale_packing_list_line_2.getAggregateValue(
                        portal_type=self.computer_partition_portal_type))
    hosting_1, hosting_2 = [hosting.getAggregateValue(
      portal_type=self.hosting_subscription_portal_type) \
          for hosting in sale_packing_line_list]
    self.assertNotEquals(hosting_1, hosting_2)

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
    self.slap.initializeConnection(self.server_url)
    self.slap.registerComputer(computer_guid).updateConfiguration(
        xml_marshaller.dumps(computer_dict))
    sequence.edit(
        computer_partition_reference_list=computer_partition_reference_list)

  def stepComputerSoftwareReleaseAvailable(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    software_release_url = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_release_uid']).getUrlString()
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
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
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        sequence['computer_partition_reference'])
    computer_partition.stopped()

  def stepSoftwareInstanceStarted(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        sequence['computer_partition_reference'])
    computer_partition.started()

  def stepSoftwareInstanceAvailable(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        sequence['computer_partition_reference'])
    computer_partition.available()

  def stepSoftwareInstanceDestroyed(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        sequence['computer_partition_reference'])
    computer_partition.destroyed()

  def stepSoftwareInstanceBuilding(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(computer_guid,
        sequence['computer_partition_reference'])
    computer_partition.building()

  def stepConfirmOrderedSaleOrderActiveSense(self, **kw):
    self.portal.portal_alarms.confirm_ordered_sale_order.activeSense()

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

  def stepSlapLoginCurrentComputer(self, sequence, **kw):
    global REMOTE_USER
    REMOTE_USER = sequence['computer_reference']

  def stepSlapLoginCurrentSoftwareInstance(self, sequence, **kw):
    global REMOTE_USER
    REMOTE_USER = sequence['software_instance_reference']

  def stepSlapLoginTestVifibCustomer(self, sequence, **kw):
    global REMOTE_USER
    REMOTE_USER = 'test_vifib_customer'

  ########################################
  # Typical sequences for scenarios
  ########################################

  prepare_published_software_release = """
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic
      SubmitSoftwareRelease
      Tic
      CreateSoftwareProduct
      Tic
      ValidateSoftwareProduct
      Tic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      Logout
  """

  prepare_computer = """
      LoginTestVifibAdmin
      CreateComputer
      Tic
      Logout
  """

  prepare_formated_computer = prepare_computer + """
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
  """

  prepare_software_release_confirmed_packing_list = """
      LoginDefaultUser
      CreatePurchasePackingList
      Tic
      CreatePurchasePackingListLine
      Tic
      SetPurchasePackingListLineSetupResource
      SetPurchasePackingListLineAggregate
      ConfirmPurchasePackingList
      Tic
      CheckConfirmedPurchasePackingList
      Logout
  """

  prepare_software_release_purchase_packing_list = \
      prepare_published_software_release + prepare_formated_computer + \
      prepare_software_release_confirmed_packing_list

  prepare_software_release_purchase_packing_list_accounting_resource = \
      prepare_published_software_release + prepare_formated_computer + """
      LoginDefaultUser
      CreateAccountingService
      CreatePurchasePackingList
      Tic
      CreatePurchasePackingListLine
      Tic
      SetPurchasePackingListLineAccountingResource
      SetPurchasePackingListLineAggregate
      ConfirmPurchasePackingList
      Tic
      Logout
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
      PersonRequestSoftwareInstance
      Tic
      Logout
  """
  prepare_install_requested_computer_partition_sequence_string = \
      prepare_person_requested_software_instance + """
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout
  """

  prepare_building_computer_partition_sequence_string = \
      prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckComputerPartitionInstanceSetupSalePackingListStarted \
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
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout
  """

  prepare_confirmed_cleanup_resource_packing_list = \
      prepare_installed_computer_partition_sequence_string + """
      LoginDefaultUser
      CreateSalePackingList
      Tic
      CreateSalePackingListLine
      Tic
      SetSalePackingListLineCleanupResource
      SetSalePackingListLineAggregate
      ConfirmSalePackingList
      Tic
      """

  prepare_destroy_requested_computer_partition = \
      prepare_installed_computer_partition_sequence_string + '\
      LoginTestVifibCustomer \
      RequestSoftwareInstanceDestroy \
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
      SlapLogout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered \
      CheckComputerPartitionIsFree \
      Logout \
      '

  prepare_start_requested_computer_partition_sequence_string = \
      prepare_installed_computer_partition_sequence_string + '\
      LoginTestVifibCustomer \
      RequestSoftwareInstanceStart \
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
      prepare_started_computer_partition_sequence_string + '\
      LoginTestVifibCustomer \
      RequestSoftwareInstanceStop \
      Tic \
      Logout \
      \
      LoginDefaultUser \
      CheckComputerPartitionInstanceHostingSalePackingListStopped \
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
      CheckComputerPartitionInstanceHostingSalePackingListDelivered \
      Logout \
  '

  prepare_computer_partition_accounting_resource_sequence_string = \
      prepare_installed_computer_partition_sequence_string + '\
      LoginDefaultUser \
      CreateSalePackingList \
      CreateAccountingService \
      Tic \
      CreateSalePackingListLine \
      Tic \
      SetSalePackingListLineAccountingResource \
      SetSalePackingListLineAggregate \
      Tic \
      ConfirmSalePackingList \
      Tic \
      CheckComputerPartitionAccoutingResourceSalePackingListConfirmed \
      Logout \
      '

  prepare_computer_partition_accounting_resource_started_sequence_string = \
      prepare_computer_partition_accounting_resource_sequence_string + '\
      LoginDefaultUser \
      StartSalePackingList \
      Tic \
      CheckComputerPartitionAccoutingResourceSalePackingListStarted \
      Logout \
      '

  prepare_computer_partition_accounting_resource_stopped_sequence_string = \
      prepare_computer_partition_accounting_resource_started_sequence_string + '\
      LoginDefaultUser \
      StopSalePackingList \
      Tic \
      CheckComputerPartitionAccoutingResourceSalePackingListStopped \
      Logout \
      '

  prepare_computer_partition_accounting_resource_delivered_sequence_string = \
      prepare_computer_partition_accounting_resource_stopped_sequence_string + '\
      LoginDefaultUser \
      DeliverSalePackingList \
      Tic \
      CheckComputerPartitionAccoutingResourceSalePackingListDelivered \
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
      RequestComputerPartitionNotReadyResponse
      Tic
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SetChildrenAComputerPartition
      SelectRequestedReferenceChildrenB
      SelectEmptyRequestedParameterDict
      Logout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotReadyResponse
      Tic
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      SetChildrenBComputerPartition
      Logout
      """ 

  computer_with_software_release = """
      CreateComputer
      Tic
      CreatePurchasePackingList
      Tic
      CreatePurchasePackingListLine
      Tic
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic \
      SubmitSoftwareRelease \
      Tic \
      CreateSoftwareProduct \
      Tic \
      ValidateSoftwareProduct \
      Tic \
      SetSoftwareProductToSoftwareRelease \
      PublishByActionSoftwareRelease \
      Tic
      SetPurchasePackingListLineSetupResource
      SetPurchasePackingListLineAggregate
      ConfirmPurchasePackingList
      StopPurchasePackingList
      Tic
  """

  requesting_computer_partition_with_software_instance = """
      SelectNewComputerPartitionReference
      CreateComputerPartition
      CreateSalePackingList
      Tic
      CreateSalePackingListLine
      Tic
      SetSalePackingListLineSetupResource
      SetSalePackingListLineAggregate
      ConfirmSalePackingList
      Tic
  """

  slave_owner_computer_partition_with_software_instance = """
      SelectNewComputerPartitionReference
      CreateComputerPartition
      SetSoftwareInstanceTitle
      CreateSalePackingList
      Tic
      CreateSalePackingListLine
      Tic
      SetSalePackingListLineSetupResource
      SetSalePackingListLineAggregate
      ConfirmSalePackingList
      Tic
      SetComputerPartitionQuantity
      Tic
      SelectCurrentComputerPartitionAsSlaveOwner
  """

  check_positive_request_shared = """
      RequestSharedComputerPartitionNotReadyResponse
      Tic
      RequestSharedComputerPartition
      CheckSoftwareInstanceAndRelatedSlavePartition
      CheckRequestedSoftwareInstanceAndRelatedSlavePartition
  """

  prepare_two_purchase_packing_list = \
                  prepare_software_release_purchase_packing_list + '\
                  LoginDefaultUser \
                  SetCurrentPurchasePackingListAsA \
                  StartPurchasePackingList \
                  StopPurchasePackingList \
                  Tic \
                  Logout \
                  SlapLoginCurrentComputer \
                  CheckEmptyComputerGetSoftwareReleaseListCall \
                  SlapLogout ' + \
                  prepare_software_release_confirmed_packing_list + '\
                  LoginDefaultUser \
                  SetCurrentPurchasePackingListAsB \
                  CheckStoppedPurchasePackingListA \
                  CheckConfirmedPurchasePackingListB \
                  Logout'

  prepare_another_computer_sequence_string = """
    StoreComputerReference
    LoginTestVifibAdmin
    CreateComputer
    Tic
    Logout

    SlapLoginCurrentComputer
    FormatComputer
    Tic
    SlapLogout""" + prepare_software_release_confirmed_packing_list + """

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

  prepare_started_slave_instance_sequence_string = \
      prepare_started_computer_partition_sequence_string + """
        LoginTestVifibCustomer
        PersonRequestSlaveInstance
        SlapLogout
        LoginDefaultUser
        ConfirmOrderedSaleOrderActiveSense
        Tic
        SlapLogout
        SlapLoginCurrentComputer
        SoftwareInstanceAvailable
        Tic
        LoginTestVifibCustomer
        RequestStopSoftwareInstanceFromCurrentComputerPartition
        Tic
        SoftwareInstanceStopped
        Tic
        StartSoftwareInstanceFromCurrentComputerPartition
        Tic
        SoftwareInstanceStarted
        Tic
        Logout
        LoginDefaultUser
        SetDeliveryLineAmountEqualTwo
        CheckComputerPartitionInstanceHostingSalePackingListStarted
        CheckComputerPartitionInstanceSetupSalePackingListStopped
        Logout
      """

  ########################################
  # Steps
  ########################################

  def stepCheckSuccessSlapRegisterComputerCall(self, sequence, **kw):
    """
    Check that slap.registerComputer is successfully called.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
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

  def stepCreateAccountingService(self, sequence, **kw):
    """
    Create an accounting service
    """
    module = self.portal.getDefaultModule(
        portal_type=self.service_portal_type)
    service = module.newContent(
        portal_type=self.service_portal_type,
        title="A custom accounting service")
    service.validate()
    sequence.edit(service_uid=service.getUid())

  def stepCheckDraftComputerState(self, sequence, **kw):
    """
    Check that computer document is draft.
    """
    computer_uid = sequence["computer_uid"]
    computer = self.portal.portal_catalog.getResultValue(uid=computer_uid)
    self.assertEquals("draft", computer.getValidationState())

  def stepValidateComputer(self, sequence, **kw):
    """
    Validate the computer document.
    """
    computer_uid = sequence["computer_uid"]
    computer = self.portal.portal_catalog.getResultValue(uid=computer_uid)
    computer.validate()

  def stepCheckValidatedComputerState(self, sequence, **kw):
    """
    Check that computer document is validated.
    """
    computer_uid = sequence["computer_uid"]
    computer = self.portal.portal_catalog.getResultValue(uid=computer_uid)
    self.assertEquals("validated", computer.getValidationState())

  def stepCheckUnauthorizedSlapGetComputerPartitionListCall(self, sequence,
      **kw):
    computer_guid = sequence.get("computer_reference", str(random()))
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    self.assertRaises(slap.Unauthorized, computer.getComputerPartitionList)

  def stepCheckUnauthorizedSlapRegisterComputerPartitionCall(self, sequence,
      **kw):
    computer_guid = sequence.get("computer_reference", str(random()))
    partition_id = str(random())
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
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
    self.slap.initializeConnection(self.server_url)
    self.assertRaises(slap.NotFoundError,
        self.slap.registerComputerPartition, computer_guid, partition_id)

  def stepSelect0QuantityComputerPartition(self, sequence, **kw):
    sequence.edit(computer_partition_quantity=0)

  def stepSetComputerPartitionQuantity(self, sequence, **kw):
    """
    Set Computer Partition quantity, defaults to 1
    """
    computer_partition_uid = sequence["computer_partition_uid"]
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=computer_partition_uid)
    quantity = sequence.get('computer_partition_quantity',
        1)
    computer_partition.edit(quantity=quantity)

  def stepSelectCurrentComputerPartitionAsSlaveOwner(self, sequence, **kw):
    computer_partition_uid = sequence["computer_partition_uid"]
    self.assertNotEqual(None, computer_partition_uid)
    sequence.edit(slave_owner_uid=computer_partition_uid)

  def stepCreateComputerPartition(self, sequence, **kw):
    """
    Create a computer partition document.
    """
    computer_uid = sequence["computer_uid"]
    partition_reference = sequence["computer_partition_reference"]

    computer = self.portal.portal_catalog.getResultValue(uid=computer_uid)
    computer_partition = computer.newContent(
        portal_type=self.computer_partition_portal_type,
        reference=partition_reference)
    # Mark newly created computer partition as free by default
    computer_partition.markFree()
    sequence.edit(computer_partition_uid=computer_partition.getUid())

  def stepCheckSuccessSlapRegisterComputerPartitionCall(self, sequence, **kw):
    """
    Check that slap.registerComputerPartition is successfully called.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference_list"][0]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
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
    self.slap.initializeConnection(self.server_url)
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
    sequence.edit(software_release_uid=software_release.getUid())

  def stepCheckUnexistingSoftwareRelease(self, sequence, **kw):
    """
    Check that it is not present in the system.
    """
    url = sequence["software_release_uri"]
    result_list = self.portal.portal_catalog(
          portal_type=self.software_release_portal_type,
          url_string=url,
          )
    self.assertEquals(0, len(result_list))

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

  def stepPublishSoftwareRelease(self, sequence, **kw):
    """
    Validate the software release document.
    """
    software_release_uid = sequence["software_release_uid"]
    software_release = self.portal.portal_catalog.getResultValue(
        uid=software_release_uid)
    software_release.publish()

  def stepPublishByActionSoftwareRelease(self, sequence, **kw):
    """
    Validate the software release document.
    """
    software_release_uid = sequence["software_release_uid"]
    software_release = self.portal.portal_catalog.getResultValue(
        uid=software_release_uid)
    software_release.portal_workflow.doActionFor(software_release,
                                                 'publish_action')

  def stepCheckDraftSoftwareReleaseState(self, sequence, **kw):
    """
    Check that software release is draft.
    """
    software_release_uid = sequence["software_release_uid"]
    software_release = self.portal.portal_catalog.getResultValue(
        uid=software_release_uid)
    self.assertEquals("draft", software_release.getValidationState())

  def stepCheckPublishedSoftwareReleaseState(self, sequence, **kw):
    """
    Check that software release is validated.
    """
    software_release_uid = sequence["software_release_uid"]
    software_release = self.portal.portal_catalog.getResultValue(
        uid=software_release_uid)
    self.assertEquals("published", software_release.getValidationState())

  def stepCheckNotFoundComputerGetComputerPartitionCall(self, sequence, **kw):
    """
    Check that Computer.getComputerPartitionList is successfully called.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    self.assertRaises(slap.NotFoundError, computer.getComputerPartitionList)

  def stepCheckEmptyComputerGetComputerPartitionCall(self, sequence, **kw):
    """
    Check that Computer.getComputerPartitionList is successfully called.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    self.assertEquals([], computer.getComputerPartitionList())

  def stepSelectYetAnotherRequestedReference(self, sequence, **kw):
    sequence.edit(requested_reference='yet_another_requested_reference')

  def stepSelectAnotherRequestedReference(self, sequence, **kw):
    sequence.edit(requested_reference='another_requested_reference')

  def stepSelectRequestedReference(self, sequence, **kw):
    sequence.edit(requested_reference='requested_reference')

  def stepSelectRequestedReferenceChildrenA(self, sequence, **kw):
    sequence.edit(requested_reference='children_a')

  def stepSelectRequestedReferenceChildrenB(self, sequence, **kw):
    sequence.edit(requested_reference='children_b')

  def stepSelectRequestedReferenceChildrenAChild(self, sequence, **kw):
    sequence.edit(requested_reference='children_a_child')

  def stepSelectRequestedReferenceChildrenBChild(self, sequence, **kw):
    sequence.edit(requested_reference='children_b_child')

  def stepSelectRequestedReferenceRootSoftwareInstanceTitle(self, sequence,
      **kw):
    sequence.edit(requested_reference=sequence['root_software_instance_title'])

  def stepSelectRequestedReferenceB(self, sequence, **kw):
    sequence.edit(requested_reference='b')

  def stepSelectRequestedReferenceC(self, sequence, **kw):
    sequence.edit(requested_reference='c')

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
    self.slap.initializeConnection(self.server_url)
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
    self.assertEqual('value',
        slap_computer_partition.getConnectionParameter('parameter'))

  def stepRequestSlaveInstanceFromComputerPartition(self, sequence, **kw):
    software_release_uri = sequence['software_release_uri']
    requested_reference = sequence['requested_reference']
    requested_parameter_dict = sequence['requested_parameter_dict']

    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])

    requested_slap_computer_partition = slap_computer_partition.request(
        software_release=software_release_uri,
        software_type="SlaveInstance",
        partition_reference=requested_reference,
        partition_parameter_kw=requested_parameter_dict,
        # XXX The follow API should be slave, but shared was kept for
        # Backward compatibility with older versions of slap
        shared=True,
        filter_kw=sequence.get('requested_filter_dict', {}),
        state=sequence.get('instance_state'))

    sequence.edit(
        requested_slap_computer_partition=requested_slap_computer_partition,
        requested_computer_partition_reference=\
            requested_slap_computer_partition.getId())

  def stepRequestSlaveInstanceFromComputerPartitionNotReadyResponse(self, sequence, **kw):
    software_release_uri = sequence['software_release_uri']
    requested_reference = sequence['requested_reference']
    requested_parameter_dict = sequence['requested_parameter_dict']

    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])

    # first try will raise slap.ResourceNotReady
    self.assertRaises(slap.ResourceNotReady,
      slap_computer_partition.request,
      software_release=software_release_uri,
      software_type="SlaveInstance",
      partition_reference=requested_reference,
      partition_parameter_kw=requested_parameter_dict,
      shared=True,
      filter_kw=sequence.get('requested_filter_dict', {}),
      state=sequence.get('instance_state'))

  def stepRequestSlaveInstanceFromComputerPartitionNotFoundError(self, sequence, **kw):
    software_release_uri = sequence['software_release_uri']
    requested_reference = sequence['requested_reference']
    requested_parameter_dict = sequence['requested_parameter_dict']

    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])

    self.assertRaises(slap.NotFoundError, 
      slap_computer_partition.request,
      software_release=software_release_uri,
      software_type="SlaveInstance",
      partition_reference=requested_reference,
      partition_parameter_kw=requested_parameter_dict,
      shared=True, 
      filter_kw=sequence.get('requested_filter_dict', {}),
      state=sequence.get('instance_state'))

  def stepRequestTwoAndCheckDifferentResult(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])
    software_release = sequence['software_release_uri']
    software_type = sequence.get('requested_reference', 'requested_reference')
    self.assertRaises(slap.ResourceNotReady, slap_computer_partition.request,
        software_release, software_type, software_type + str(1))
    self.assertRaises(slap.ResourceNotReady, slap_computer_partition.request,
        software_release, software_type, software_type + str(2))
    transaction.commit()
    self.tic()
    first = slap_computer_partition.request(software_release,
        software_type, software_type + str(1))
    second = slap_computer_partition.request(software_release,
        software_type, software_type + str(2))
    self.assertNotEqual(first.getId(), second.getId())

  def stepRequestComputerPartition(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])
    requested_slap_computer_partition = slap_computer_partition.request(
      software_release=sequence['software_release_uri'],
      software_type=sequence.get('requested_reference', 'requested_reference'),
      partition_reference=sequence.get('requested_reference',
        'requested_reference'),
      partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
      filter_kw=sequence.get('requested_filter_dict', {}),
      state=sequence.get('instance_state'))

    sequence.edit(
        requested_slap_computer_partition=requested_slap_computer_partition,
        requested_computer_partition_reference=\
            requested_slap_computer_partition.getId())

  def stepDirectRequestComputerPartitionNotReadyResponseWithoutStateAndSharedTrue(
      self, sequence, **kw):
    kw["shared"] = True
    self.stepDirectRequestComputerPartitionNotReadyResponseWithoutState(
       sequence, **kw)

  def stepDirectRequestComputerPartitionNotReadyResponseWithoutState(self,
    sequence, **kw):
    request_dict = { 'computer_id': sequence['computer_reference'] ,
        'computer_partition_id': sequence['computer_partition_reference'],
        'software_release': sequence['software_release_uri'],
        'software_type': sequence.get('requested_reference', 'requested_reference'),
        'partition_reference': sequence.get('requested_reference', 'requested_reference'),
        'shared_xml': xml_marshaller.dumps(kw.get("shared", False)),
        'partition_parameter_xml': xml_marshaller.dumps({}),
        'filter_xml': xml_marshaller.dumps({}),
        #'state': Note: State is omitted
      }
    scheme, netloc, path, query, fragment = urlparse.urlsplit(self.server_url)
    connection = httplib.HTTPConnection(host=netloc)
    connection.request("POST", path + '/requestComputerPartition',
        urllib.urlencode(request_dict),
        {'Content-type': "application/x-www-form-urlencoded"})
    response = connection.getresponse()
    self.assertEqual(httplib.REQUEST_TIMEOUT, response.status)

  def stepRequestComputerPartitionNotReadyResponse(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])
    self.assertRaises(slap.ResourceNotReady, slap_computer_partition.request,
      software_release=sequence['software_release_uri'],
      software_type=sequence.get('requested_reference', 'requested_reference'),
      partition_reference=sequence.get('requested_reference',
        'requested_reference'),
      partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
      filter_kw=sequence.get('requested_filter_dict', {}),
      state=sequence.get('instance_state'))

  def stepRequestComputerPartitionNotFoundResponse(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])
    self.assertRaises(slap.NotFoundError, slap_computer_partition.request,
      software_release=sequence['software_release_uri'],
      software_type=sequence.get('requested_reference', 'requested_reference'),
      partition_reference=sequence.get('requested_reference',
        'requested_reference'),
      partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
      filter_kw=sequence.get('requested_filter_dict', {}),
      state=sequence.get('instance_state'))

  def stepSetSoftwareInstanceChildrenA(self, sequence, **kw):
    software_instance_uid = sequence['root_software_instance_uid']
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)
    children_software_instance = \
      software_instance.portal_catalog.getResultValue(
          portal_type="Software Instance", source_reference='children_a',
          root_uid=software_instance_uid)
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

  def stepSetRootSoftwareInstanceCurrentInstance(self, sequence, **kw):
    software_instance_uid = sequence['software_instance_uid']
    self.assertNotEqual(None, software_instance_uid)
    sequence.edit(root_software_instance_uid=software_instance_uid)

  def stepSetSoftwareInstanceChildrenB(self, sequence, **kw):
    software_instance_uid = sequence['root_software_instance_uid']
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)
    children_software_instance = \
      software_instance.portal_catalog.getResultValue(
          portal_type="Software Instance", source_reference='children_b',
          root_uid=software_instance_uid)
    self.assertNotEqual(None, children_software_instance)
    self.assertNotEqual(software_instance.getRelativeUrl(),
        children_software_instance.getRelativeUrl())
    sequence.edit(
        software_instance_uid=children_software_instance.getUid(),
        software_instance_refernece=children_software_instance.getReference(),
        computer_partition_reference=self.\
            _softwareInstance_getComputerPartition(children_software_instance
              ).getReference()
        )

  def stepRequestComputerPartitionDifferentReferenceSameTransaction(self,
      sequence, **kw):
    software_release_uri = sequence['software_release_uri']
    computer_guid = sequence["computer_reference"]
    requested_parameter_dict = sequence['requested_parameter_dict']
    software_instance_uid = sequence['software_instance_uid']
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)

    # Slap Tool have to be used directly to simulate same transaction

    raise NotImplementedError("Do not test slap tool but slap library")
    children_software_instance = software_instance\
        .SoftwareInstance_findAlreadyExisting('children_a')
    slap_tool_response = self.portal.portal_slap.requestComputerPartition(
        computer_guid, children_software_instance\
            .SoftwareInstance_getComputerPartition().getReference(),
            software_release_uri, 'children_a_child',
            requested_parameter_dict)
    self.assertEqual(408, slap_tool_response.getStatus())

    children_software_instance = software_instance\
        .SoftwareInstance_findAlreadyExisting('children_b')
    slap_tool_response = self.portal.portal_slap.requestComputerPartition(
        computer_guid, children_software_instance\
            .SoftwareInstance_getComputerPartition().getReference(),
            software_release_uri, 'children_b_child',
            requested_parameter_dict)
    self.assertEqual(408, slap_tool_response.getStatus())

  def stepRequestComputerPartitionSameReferenceSameTransaction(self, sequence,
      **kw):
    raise NotImplementedError('Wrong logic')
    software_release_uri = sequence['software_release_uri']
    requested_reference = sequence['requested_reference']
    computer_guid = sequence["computer_reference"]
    requested_parameter_dict = sequence['requested_parameter_dict']
    software_instance_uid = sequence['software_instance_uid']
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)
    self.slap = slap.slap()

    # Slap Tool have to be used directly to simulate same transaction
    children_software_instance = \
      software_instance.portal_catalog.getResultValue(
          portal_type="Software Instance", source_reference='children_a',
          root_uid=software_instance_uid)
    movement = children_software_instance.getAggregateRelatedValue(
                                    portal_type="Sale Packing List Line")
    children_partition = movement.getAggregateValue(
                                    portal_type="Computer Partition")
    slap_computer_partition = self.slap.registerComputerPartition(
                                            computer_guid,
                                            children_partition.getReference())
    self.assertRaises(slap.ResourceNotReady, slap_computer_partition.request,
        software_release=software_release_uri, software_type=requested_reference,
        partition_reference=requested_reference,
        partition_parameter_kw=requested_parameter_dict)

    children_software_instance = \
      software_instance.portal_catalog.getResultValue(
          portal_type="Software Instance", source_reference='children_b',
          root_uid=software_instance_uid)
    movement = children_software_instance.getAggregateRelatedValue(
                                    portal_type="Sale Packing List Line")
    children_partition = movement.getAggregateValue(
                                    portal_type="Computer Partition")
    slap_computer_partition = self.slap.registerComputerPartition(
                                            computer_guid,
                                            children_partition.getReference())
    self.assertRaises(slap.ResourceNotReady, slap_computer_partition.request,
        software_release=software_release_uri,
        software_type=requested_reference,
        partition_reference=requested_reference,
        partition_parameter_kw=requested_parameter_dict)

  def stepRequestSoftwareInstanceStartCheckSerializeIsCalled(self, sequence):
    # check that on being_requested serialise is being called
    # code stolen from testERP5Security:test_MultiplePersonReferenceConcurrentTransaction
    class DummyTestException(Exception):
      pass

    def verify_serialize_call(self):
      # it is checking that anything below computer_module raises exception
      # thanks to this this test do not have to be destructive
      if self.getPortalType() == "Software Instance":
        raise DummyTestException
      else:
        return self.serialize_call()

    from Products.ERP5Type.Base import Base
    Base.serialize_call = Base.serialize
    Base.serialize = verify_serialize_call

    try:
      self.assertRaises(DummyTestException,
        self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid']).requestStartComputerPartition)
    finally:
      Base.serialize = Base.serialize_call

  def stepRequestSoftwareInstanceDestroyCheckSerializeIsCalled(self, sequence):
    # check that on being_requested serialise is being called
    # code stolen from testERP5Security:test_MultiplePersonReferenceConcurrentTransaction
    class DummyTestException(Exception):
      pass

    def verify_serialize_call(self):
      # it is checking that anything below computer_module raises exception
      # thanks to this this test do not have to be destructive
      if self.getPortalType() == "Software Instance":
        raise DummyTestException
      else:
        return self.serialize_call()

    from Products.ERP5Type.Base import Base
    Base.serialize_call = Base.serialize
    Base.serialize = verify_serialize_call

    try:
      self.assertRaises(DummyTestException,
        self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid']).requestDestroyComputerPartition)
    finally:
      Base.serialize = Base.serialize_call

  def stepRequestComputerComputerPartitionCheckSerializeCalledOnSelected(
      self, sequence, **kw):
    software_release_uri = sequence['software_release_uri']
    requested_reference = sequence['requested_reference']
    software_instance_uid = sequence['software_instance_uid']

    # slap cannot be used to this test, as ERP5 itself shall raise
    requester = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)

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
      self.assertRaises(DummyTestException, requester.requestSoftwareInstance,
                        software_release=software_release_uri,
                        partition_reference=requested_reference,
                        software_type=requested_reference,
                        shared=False,
                        filter_kw={},
                        instance_xml=self.minimal_correct_xml,
                        sla_xml=self.minimal_correct_xml,
                        state=None)
    finally:
      Base.serialize = Base.serialize_call

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
    self.assertEqual('requested_reference', predecessor.getSourceReference())
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
    self.assertEqual('requested_reference', predecessor.getSourceReference())
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
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    computer_partition_list = computer.getComputerPartitionList()
    self.assertEquals(self.computer_partition_amount,
                      len(computer_partition_list))

  def stepCheckSuccessComputerPartitionGetIdCall(self, sequence, **kw):
    """
    Check that slap.registerComputerPartition is successfully called.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference_list"][0]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)
    self.assertEquals(partition_id, computer_partition.getId())

  def stepCheckSuccessSoftwareReleaseGetURICall(self, sequence, **kw):
    """
    Check that SoftwareRelease.getURI is successfully called.
    """
    url = sequence["software_release_uri"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
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
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    self.assertRaises(slap.Unauthorized, computer.getSoftwareReleaseList)

  def stepCheckNotFoundComputerGetSoftwareReleaseListCall(self, sequence, **kw):
    """
    Check that Computer.getSoftwareReleaseList raise NotFoundError is the
    computer doesn't exist.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    self.assertRaises(slap.NotFoundError, computer.getSoftwareReleaseList)

  def stepCheckEmptyComputerGetSoftwareReleaseListCall(self, sequence, **kw):
    """
    Check that Computer.getSoftwareReleaseList returns an empty list.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    self.assertEquals([], computer.getSoftwareReleaseList())

  def stepCheckSuccessComputerGetSoftwareReleaseListCall(self, sequence, **kw):
    """
    Check that Computer.getSoftwareReleaseList returns software release
    associated to the computer.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    self.assertEquals(1, len(computer.getSoftwareReleaseList()))
    self.assertTrue(isinstance(computer.getSoftwareReleaseList()[0],
                               slap.SoftwareRelease))

  def stepCreatePurchasePackingList(self, sequence, **kw):
    """
    Create an purchase packing list document.
    """
    module = self.portal.getDefaultModule(
        portal_type=self.purchase_packing_list_portal_type)
    order = module.newContent(
        portal_type=self.purchase_packing_list_portal_type,
        start_date=DateTime(),
        )
    sequence.edit(purchase_packing_list_uid=order.getUid())

  def stepCreatePurchasePackingListLine(self, sequence, **kw):
    """
    Create an purchase packing list line document.
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    line = order.newContent(
        portal_type=self.purchase_packing_list_line_portal_type)
    sequence.edit(purchase_packing_list_line_uid=line.getUid())

  def stepSetPurchasePackingListLineAggregate(self, sequence, **kw):
    """
    Associate a computer and a software release to the purchase packing list line.
    """
    line = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_line_uid"])
    line.edit(
        aggregate_uid_list=[sequence["computer_uid"],
                            sequence["software_release_uid"]]
        )

  def stepConfirmPurchasePackingList(self, sequence, **kw):
    """
    Confirm the purchase packing list
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    order.portal_workflow.doActionFor(order, 'confirm_action')

  def stepStartPurchasePackingList(self, sequence, **kw):
    """
    Start the purchase packing list
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    order.portal_workflow.doActionFor(order, 'start_action')

  def stepStopPurchasePackingList(self, sequence, **kw):
    """
    Stop the purchase packing list
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    order.portal_workflow.doActionFor(order, 'stop_action')

  def stepDeliverPurchasePackingList(self, sequence, **kw):
    """
    Deliver the purchase packing list
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    order.portal_workflow.doActionFor(order, 'deliver_action')

  def stepCancelPurchasePackingList(self, sequence, **kw):
    """
    Cancel the purchase packing list
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    order.portal_workflow.doActionFor(order, 'cancel_action')

  def stepCheckNotFoundSoftwareReleaseBuildingAfterRegisterCall(self,
      sequence, **kw):
    """
    Check that calling SoftwareRelease.building after just registration raises a
    NotFoundError
    """
    url = sequence["software_release_uri"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    software_release = self.slap.registerSoftwareRelease(url)

    self.assertRaises(slap.NotFoundError, software_release.building)

  def stepCheckSuccessSoftwareReleaseBuildingCall(self, sequence, **kw):
    """
    Check that calling SoftwareRelease.building works.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    software_release = computer.getSoftwareReleaseList()[0]

    software_release.building()

  def stepCheckConfirmedPurchasePackingList(self, sequence, **kw):
    """
    Check that the purchase packing list is confirmed.
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    self.assertEquals("confirmed", packing_list.getSimulationState())

  def stepCheckStartedPurchasePackingList(self, sequence, **kw):
    """
    Check that the purchase packing list is started.
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    self.assertEquals("started", packing_list.getSimulationState())

  def stepCheckNotFoundSoftwareReleaseBuildingCall(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    software_release = self.slap.registerSoftwareRelease(
        sequence['software_release_uri'])
    # Note: Hackish
    software_release._computer_guid = computer_guid
    self.assertRaises(slap.NotFoundError, software_release.building)

  def stepCheckTicAndNotFoundSoftwareReleaseBuildingCall(self, sequence, **kw):
    """
    Check that calling SoftwareRelease.building raises NotFoundError
    after using tic.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    software_release = computer.getSoftwareReleaseList()[0]

    self.tic()
    transaction.commit()

    self.assertRaises(slap.NotFoundError, software_release.building)

  def stepCheckNotFoundSoftwareReleaseAvailableCall(self, sequence, **kw):
    """
    Check that calling SoftwareRelease.available raises NotFound
    after using tic.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    software_release = self.slap.registerSoftwareRelease(
        sequence['software_release_uri'])
    # Note: Hackish
    software_release._computer_guid = computer_guid
    self.assertRaises(slap.NotFoundError, software_release.available)

  def stepCheckTicAndNotFoundSoftwareReleaseAvailableCall(self, sequence, **kw):
    """
    Check that calling SoftwareRelease.available raises NotFound
    after using tic.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    software_release = computer.getSoftwareReleaseList()[0]

    self.tic()
    transaction.commit()

    self.assertRaises(slap.NotFoundError, software_release.available)

  def stepCheckSoftwareReleaseErrorCall(self, sequence, **kw):
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    software_release = self.slap.registerSoftwareRelease(
        sequence['software_release_uri'])
    # Note: Hackish
    software_release._computer_guid = computer_guid
    software_release.error("ErrorLog")

  def stepCheckTicAndSoftwareReleaseErrorCall(self, sequence, **kw):
    """
    Check that calling SoftwareRelease.error raises NotFound
    after using tic.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    software_release = computer.getSoftwareReleaseList()[0]

    self.tic()
    transaction.commit()

    software_release.error("ErrorLog")

  def stepCheckTicAndNotFoundSoftwareReleaseErrorCall(self, sequence, **kw):
    """
    Check that calling SoftwareRelease.error raises NotFound
    after using tic.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    software_release = computer.getSoftwareReleaseList()[0]

    self.tic()
    transaction.commit()

    self.assertRaises(slap.NotFoundError, software_release.error, "ErrorLog")

  def stepCheckNotFoundSoftwareReleaseAvailableAfterRegisterCall(self, sequence,
      **kw):
    """
    Check that calling SoftwareRelease.available after just registration raises a
    NotFoundError
    """
    url = sequence["software_release_uri"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    software_release = self.slap.registerSoftwareRelease(url)

    self.assertRaises(slap.NotFoundError, software_release.available)

  def stepCheckSuccessSoftwareReleaseAvailableCall(self, sequence, **kw):
    """
    Check that calling SoftwareRelease.available works.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    software_release = computer.getSoftwareReleaseList()[0]

    software_release.available()

  def stepCheckUnauthorizedSoftwareReleaseAvailableCall(self, sequence, **kw):
    """
    Check that calling SoftwareRelease.available is Unauthorized
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    software_release = computer.getSoftwareReleaseList()[0]

    self.assertRaises(slap.Unauthorized, software_release.available)

  def stepCheckStoppedPurchasePackingList(self, sequence, **kw):
    """
    Check that the purchase packing list is started.
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    self.assertEquals("stopped", packing_list.getSimulationState())

  def stepCheckDeliveredPurchasePackingList(self, sequence, **kw):
    """
    Check that the purchase packing list is started.
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    self.assertEquals("delivered", packing_list.getSimulationState())

  def stepCheckNotFoundSoftwareReleaseErrorAfterRegisterCall(self, sequence,
      **kw):
    """
    Check that calling SoftwareRelease.error after just registration raises a
    NotFoundError
    """
    url = sequence["software_release_uri"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    software_release = self.slap.registerSoftwareRelease(url)

    self.assertRaises(slap.NotFoundError, software_release.error, "ErrorLog")

  def stepCheckSuccessSoftwareReleaseErrorCall(self, sequence, **kw):
    """
    Check that calling SoftwareRelease.error works.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    software_release = computer.getSoftwareReleaseList()[0]

    software_release.error("ErrorLog")

  def stepCheckCancelledPurchasePackingList(self, sequence, **kw):
    """
    Check that the purchase packing list is cancelled
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    self.assertEquals("cancelled", packing_list.getSimulationState())

  def stepCheckPurchasePackingListErrorText(self, sequence, **kw):
    """
    Check that the purchase packing list is cancelled
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    self.assertFalse(packing_list.getComment('').endswith("ErrorLog"))

  def stepCheckPurchasePackingListNoErrorText(self, sequence, **kw):
    """
    Check that the purchase packing list is cancelled
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_uid"])
    self.assertFalse(packing_list.getComment('').endswith("ErrorLog"))

  def stepCheckUnauthorizedSoftwareReleaseBuildingCall(self, sequence, **kw):
    """
    Check that calling SoftwareRelease.building raises an Unauthorized error
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    software_release = computer.getSoftwareReleaseList()[0]

    self.assertRaises(slap.Unauthorized, software_release.building)

  def stepCheckTicAndSuccessSoftwareReleaseErrorCall(self, sequence, **kw):
    """
    Check that calling SoftwareRelease.building is OK
    after using tic.
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    software_release = computer.getSoftwareReleaseList()[0]

    self.tic()
    transaction.commit()

    software_release.error("ErrorLog")

  def stepCheckSuccessComputerPartitionBuildingCall(self, sequence, **kw):
    """
    Check that calling ComputerPartition.building works
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    computer_partition.building()

  def stepCheckNotFoundComputerPartitionBuildingCall(self, sequence, **kw):
    """
    Check that calling ComputerPartition.building after just registration raises a
    NotFound
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertRaises(slap.NotFoundError, computer_partition.building)

  def stepCheckUnauthorizedComputerPartitionBuildingCall(self, sequence, **kw):
    """
    Check that calling ComputerPartition.building after just registration raises a
    Unauthorized
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertRaises(slap.Unauthorized, computer_partition.building)

  def stepCreateSalePackingList(self, sequence, **kw):
    """
    Create an sale packing list document.
    """
    module = self.portal.getDefaultModule(
        portal_type=self.sale_packing_list_portal_type)
    order = module.newContent(
        portal_type=self.sale_packing_list_portal_type)
    sequence.edit(sale_packing_list_uid=order.getUid())

  def stepCreateSalePackingListLine(self, sequence, **kw):
    """
    Create an sale packing list line document.
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    line = order.newContent(
        portal_type=self.sale_packing_list_line_portal_type)
    sequence.edit(sale_packing_list_line_uid=line.getUid())

  def stepSetSalePackingListLineSetupResource(self, sequence, **kw):
    """
    Associate the setup service to the sale packing list line.
    """
    line = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_line_uid"])
    line.edit(resource=self.portal.portal_preferences\
        .getPreferredInstanceSetupResource())

  def stepSetSalePackingListLineHostingResource(self, sequence, **kw):
    """
    Associate the hosting service to the sale packing list line.
    """
    line = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_line_uid"])
    line.edit(resource=self.portal.portal_preferences\
        .getPreferredInstanceHostingResource())

  def stepSetSalePackingListLineCleanupResource(self, sequence, **kw):
    """
    Associate the cleanup service to the sale packing list line.
    """
    line = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_line_uid"])
    line.edit(resource=self.portal.portal_preferences\
        .getPreferredInstanceCleanupResource())

  def stepSetSalePackingListLineAccountingResource(self, sequence, **kw):
    """
    Associate an accounting service to the sale packing list line.
    """
    line = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_line_uid"])
    service_uid = sequence['service_uid']
    line.edit(resource_uid=service_uid)

  def stepSetPurchasePackingListLineAccountingResource(self, sequence, **kw):
    """
    Associate an accounting service to the purchase packing list line.
    """
    line = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_line_uid"])
    service_uid = sequence['service_uid']
    line.edit(
        quantity=1,
        resource_uid=service_uid)

  def stepSetSalePackingListLineAggregate(self, sequence, **kw):
    """
    Associate a computer and a software release to the sale packing list line.
    """
    line = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_line_uid"])
    line.edit(
        aggregate_uid_list=[sequence["computer_partition_uid"],
                            sequence["hosting_subscription_uid"],
                            sequence["software_instance_uid"],
                            sequence["software_release_uid"]]
        )

  def stepCheckNotFoundComputerPartitionBuildingAfterRegisterCall(self, sequence,
      **kw):
    """
    Check that calling ComputerPartition.building after just registrationraises a
    NotFoundError
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference_list"][0]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertRaises(slap.NotFoundError, computer_partition.building)

  def stepAssertConfirmSalePackingListRaisesUnsupportedWorkflowMethod(self,
      sequence, **kw):
    """
    Confirm the sale packing list
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    self.assertRaises(UnsupportedWorkflowMethod,
        order.portal_workflow.doActionFor, order, 'confirm_action')

  def stepConfirmSalePackingList(self, sequence, **kw):
    """
    Confirm the sale packing list
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    order.portal_workflow.doActionFor(order, 'confirm_action')

  def stepStartSalePackingList(self, sequence, **kw):
    """
    Start the sale packing list
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    order.portal_workflow.doActionFor(order, 'start_action')

  def stepStopSalePackingList(self, sequence, **kw):
    """
    Stop the sale packing list
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    order.portal_workflow.doActionFor(order, 'stop_action')

  def stepDeliverSalePackingList(self, sequence, **kw):
    """
    Deliver the sale packing list
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    order.portal_workflow.doActionFor(order, 'deliver_action')

  def stepCancelSalePackingList(self, sequence, **kw):
    """
    Cancel the sale packing list
    """
    order = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    order.portal_workflow.doActionFor(order, 'cancel_action')

  def stepCheckTicAndNotFoundComputerPartitionAvailableCall(self, sequence,
      **kw):
    """
    Check that calling ComputerPartition.building raises a NotFoundError
    after using tic.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.tic()
    transaction.commit()

    self.assertRaises(slap.NotFoundError, computer_partition.available)

  def stepCheckTicAndNotFoundComputerPartitionBuildingCall(self, sequence, **kw):
    """
    Check that calling ComputerPartition.building raises a NotFoundError
    after using tic.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.tic()
    transaction.commit()

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
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertRaises(slap.NotFoundError, computer_partition.available)

  def stepCheckUnauthorizedComputerPartitionAvailableCall(self, sequence, **kw):
    """
    Check that calling ComputerPartition.available raises an Unauthorized error
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertRaises(slap.Unauthorized, computer_partition.available)

  def stepCheckNotFoundComputerPartitionAvailableCall(self, sequence, **kw):
    """
    Check that calling ComputerPartition.available raises a NotFoundError
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
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
    self.slap.initializeConnection(self.server_url)
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
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)
    self.assertRaises(slap.NotFoundError, computer_partition.destroyed)

  def stepCheckSuccessComputerPartitionAvailableCall(self, sequence, **kw):
    """
    Check that calling ComputerPartition.available raises an Unauthorized error
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    computer_partition.available()

  def stepCheckTicAndUnauthorizedComputerPartitionAvailableCall(self, sequence,
      **kw):
    """
    Check that calling ComputerPartition.available raises an Unauthorized error
    after using tic.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.tic()
    transaction.commit()

    self.assertRaises(slap.Unauthorized, computer_partition.available)

  def stepCheckNotFoundComputerPartitionErrorAfterRegisterCall(self, sequence,
      **kw):
    """
    Check that calling ComputerPartition.error after just registration raises a
    NotFoundError
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference_list"][0]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    self.slap.registerComputerPartition(
        computer_guid, partition_id)

  def stepCheckNotFoundComputerPartitionErrorCall(self, sequence, **kw):
    """
    Check that calling ComputerPartition.error works.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)
    self.assertRaises(slap.NotFoundError, computer_partition.error, "ErrorLog")

  def stepCheckSuccessComputerPartitionErrorCall(self, sequence, **kw):
    """
    Check that calling ComputerPartition.error works.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)
    computer_partition.error("ErrorLog")

  def stepSelectCurrentlyUsedSalePackingListUid(self, sequence, **kw):
    """Sets sale_packing_list_uid to currently used to mach Computer Partition
    and Software Instance"""
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=sequence['computer_partition_uid'])
    state_list = []
    state_list.extend(self.portal.getPortalCurrentInventoryStateList())
    state_list.extend(self.portal.getPortalReservedInventoryStateList())
    state_list.extend(self.portal.getPortalTransitInventoryStateList())
    service_uid_list = []
    for service_relative_url in \
      (self.portal.portal_preferences.getPreferredInstanceSetupResource(),
       self.portal.portal_preferences.getPreferredInstanceHostingResource(),
       self.portal.portal_preferences.getPreferredInstanceCleanupResource(),
       ):
      service = self.portal.restrictedTraverse(service_relative_url)
      service_uid_list.append(service.getUid())
    delivery_line = self.portal.portal_catalog.getResultValue(
      portal_type=self.sale_packing_list_line_portal_type,
      simulation_state=state_list,
      aggregate_relative_url=computer_partition.getRelativeUrl(),
      default_resource_uid=service_uid_list,
      sort_on=(('movement.start_date', 'DESC'),),
      limit=1,
    )

    self.assertNotEqual(None, delivery_line)
    delivery = delivery_line.getParentValue()
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

  def stepCheckCancelledSalePackingList(self, sequence, **kw):
    """
    Check that the sale packing list is cancelled
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    self.assertEquals("cancelled", packing_list.getSimulationState())

  def stepCheckConfirmedSalePackingList(self, sequence, **kw):
    """
    Check that the sale packing list is confirmed
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    self.assertEquals("confirmed", packing_list.getSimulationState())

  def stepCheckStartedSalePackingList(self, sequence, **kw):
    """
    Check that the sale packing list is started
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    self.assertEquals("started", packing_list.getSimulationState())

  def stepCheckStoppedSalePackingList(self, sequence, **kw):
    """
    Check that the sale packing list is stopped
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    self.assertEquals("stopped", packing_list.getSimulationState())

  def stepCheckDeliveredSalePackingList(self, sequence, **kw):
    """
    Check that the sale packing list is delivered
    """
    packing_list = self.portal.portal_catalog.getResultValue(
        uid=sequence["sale_packing_list_uid"])
    self.assertEquals("delivered", packing_list.getSimulationState())

  def stepCheckTicAndSuccessComputerPartitionErrorCall(self, sequence, **kw):
    """
    Check that calling ComputerPartition.error works.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.tic()
    transaction.commit()

    computer_partition.error("ErrorLog")

  def stepCheckNotFoundComputerPartitionGetSoftwareReleaseAfterRegisterCall(
      self, sequence, **kw):
    """
    Check that calling ComputerPartition.getSoftwareRelease after just
    registration raises a NotFoundError
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference_list"][0]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
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
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    url = sequence["software_release_uri"]
    software_release = computer_partition.getSoftwareRelease()
    self.assertTrue(isinstance(software_release, slap.SoftwareRelease))
    self.assertEquals(url, software_release.getURI())

  def stepCheckNotFoundComputerPartitionGetSoftwareReleaseCall(self, sequence,
      **kw):
    """
    Check that calling ComputerPartition.getSoftwareRelease raise NotFoundError
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertRaises(slap.NotFoundError, computer_partition.getSoftwareRelease)

  def stepCheckTicAndNotFoundComputerPartitionGetSoftwareReleaseCall(self,
      sequence, **kw):
    """
    Check that calling ComputerPartition.getSoftwareRelease raises an
    NotFoundError after using tic.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.tic()
    transaction.commit()

    self.assertRaises(slap.NotFoundError, computer_partition.getSoftwareRelease)

  def stepCheckSuccessComputerPartitionGetInstanceParameterDictCall(self,
      sequence, **kw):
    """
    Check that slap.registerComputerPartition is successfully called.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    computer_partition.getInstanceParameterDict()

  def stepCheckMinimalParametersTransmitted(self, sequence, **kw):
    """
    Check that slap.registerComputerPartition raises a NotFound error
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    result = computer_partition.getInstanceParameterDict()
    self.assertTrue(isinstance(result, dict))
    software_release_uri = sequence['software_release_uri']
    expected = {
        'slap_computer_id': computer_guid,
        'slap_computer_partition_id': partition_id,
        'slap_server_url': self.server_url,
        'slap_software_release_url': software_release_uri,
        'slap_software_type': 'RootSoftwareInstance',
        'slave_instance_list': [],
        'ip_list': [],
    }
    self.assertSameDict(expected, result)

  def stepSetSoftwareInstanceValidTestParameterXML(self, sequence, **kw):
    """
    Set valid XML on the software instance
    """
    software_instance_uid = sequence["software_instance_uid"]
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=software_instance_uid)
    test_parameter_id = 'test_parameter_id'
    test_parameter_value = 'test_parameter_value'
    software_instance.edit(text_content="""<?xml version="1.0" encoding="utf-8"?>
<instance>

<parameter id="%s">%s</parameter>

</instance>""" % (test_parameter_id, test_parameter_value))
    sequence.edit(
      test_parameter_id=test_parameter_id,
      test_parameter_value=test_parameter_value
    )

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

  def stepCheckRequestedComputerPartitionTestParameter(self, sequence, **kw):
    requested_slap_computer_partition = sequence['requested_slap_computer_partition']
    instance_parameter_dict = requested_slap_computer_partition\
        .getInstanceParameterDict()
    test_parameter_id = sequence['test_parameter_id']
    test_parameter_value = sequence['test_parameter_value']
    self.assertTrue(test_parameter_id in instance_parameter_dict)
    self.assertEqual(test_parameter_value, instance_parameter_dict[
      test_parameter_id])

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
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    result = computer_partition.getInstanceParameterDict()
    self.assertTrue(isinstance(result, dict))
    software_release_uri = sequence['software_release_uri']
    expected = {
        'new_test_parameter': 'lala2',
        'slap_computer_id': computer_guid,
        'slap_computer_partition_id': partition_id,
        'slap_server_url': self.server_url,
        'slap_software_release_url': software_release_uri,
        'slap_software_type': 'RootSoftwareInstance',
        'test_parameter': 'lala',
        'slave_instance_list': [],
        'ip_list': [],
    }
    self.assertSameDict(expected, result)

  def stepCheckNotFoundComputerPartitionGetStateCall(self, sequence, **kw):
    """
    Check that ComputerPartition.getState raises a NotFound error
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertRaises(slap.NotFoundError, computer_partition.getState)

  def stepCheckStoppedComputerPartitionGetStateCall(self, sequence, **kw):
    """
    Check that ComputerPartition.getState return 'stopped'
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
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
    self.slap.initializeConnection(self.server_url)
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
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.assertEquals('destroyed', computer_partition.getState())

  def stepCheckTicAndUnauthorizedComputerPartitionGetStateCall(self, sequence,
      **kw):
    """
    Check that calling ComputerPartition.getState raises an
    Unauthorized error after using tic.
    """
    computer_guid = sequence["computer_reference"]
    partition_id = sequence["computer_partition_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)

    self.tic()
    transaction.commit()

    self.assertRaises(slap.Unauthorized,
                      computer_partition.getState)

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
    hosting_date = DateTime()
    setup_date = hosting_date + 1
    for movement in computer_partition.getAggregateRelatedValueList(
        portal_type=self.sale_packing_list_line_portal_type):
      if movement.getResource() == \
          movement.portal_preferences.getPreferredInstanceHostingResource():
        movement.edit(start_date=hosting_date)
      elif movement.getResource() == \
          movement.portal_preferences.getPreferredInstanceSetupResource():
        movement.edit(start_date=setup_date)

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
    setup_date = DateTime()
    hosting_date = setup_date + 1
    for movement in computer_partition.getAggregateRelatedValueList(
        portal_type=self.sale_packing_list_line_portal_type):
      if movement.getResource() == \
          movement.portal_preferences.getPreferredInstanceHostingResource():
        movement.edit(start_date=hosting_date)
      elif movement.getResource() == \
          movement.portal_preferences.getPreferredInstanceSetupResource():
        movement.edit(start_date=setup_date)

  def stepSetPurchasePackingListLineSetupResource(self, sequence, **kw):
    """
    Associate the setup service to the purchase packing list line.
    """
    line = self.portal.portal_catalog.getResultValue(
        uid=sequence["purchase_packing_list_line_uid"])
    line.edit(
        quantity=1,
        resource=self.portal.portal_preferences.\
            getPreferredSoftwareSetupResource())

  def stepSetAccountingBeforeSetupStartDate(self, sequence, **kw):
    """
    Set date on Purchase Packing List Line
    """
    computer_partition_uid = sequence["computer_uid"]
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=computer_partition_uid)
    hosting_date = DateTime()
    setup_date = hosting_date + 1
    service_uid = sequence['service_uid']
    for movement in computer_partition.getAggregateRelatedValueList(
        portal_type=self.purchase_packing_list_line_portal_type):
      if movement.getResourceUid() == service_uid:
        movement.edit(start_date=hosting_date)
      elif movement.getResource() == \
          movement.portal_preferences.getPreferredSoftwareSetupResource():
        movement.edit(start_date=setup_date)

  def stepSetAccountingAfterSetupStartDate(self, sequence, **kw):
    """
    Set date on Purchase Packing List Line
    """
    computer_partition_uid = sequence["computer_uid"]
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=computer_partition_uid)
    setup_date = DateTime()
    hosting_date = setup_date + 1
    service_uid = sequence['service_uid']
    for movement in computer_partition.getAggregateRelatedValueList(
        portal_type=self.sale_packing_list_line_portal_type):
      if movement.getResourceUid() == service_uid:
        movement.edit(start_date=hosting_date)
      elif movement.getResource() == \
          movement.portal_preferences.getPreferredSoftwareSetupResource():
        movement.edit(start_date=setup_date)

  def _checkComputerPartitionAndRelatedSoftwareInstance(self,
      computer_partition):
    sale_packing_list_line_list = computer_partition\
        .getAggregateRelatedValueList(
            portal_type=self.sale_packing_list_line_portal_type)
    self.assertEqual(1, len(sale_packing_list_line_list))
    sale_packing_list_line = sale_packing_list_line_list[0]
    software_instance = sale_packing_list_line.getAggregateValue(
        portal_type=self.software_instance_portal_type)

    software_instance_sale_packing_list_line_list = software_instance\
        .getAggregateRelatedList(
            portal_type=self.sale_packing_list_line_portal_type)
    self.assertEqual(1, len(software_instance_sale_packing_list_line_list))

  def _checkSoftwareInstanceAndRelatedPartition(self, software_instance,
      partition_portal_type=computer_partition_portal_type):
    # There should be only one Sale Packing List Line
    sale_packing_list_line_list = software_instance\
        .getAggregateRelatedValueList(
            portal_type=self.sale_packing_list_line_portal_type)
    self.assertEqual(1, len(sale_packing_list_line_list))
    sale_packing_list_line = sale_packing_list_line_list[0]

    # This Sale Packing List Line shall have only one Computer Partition
    computer_partition_list = sale_packing_list_line.getAggregateValueList(
        portal_type=partition_portal_type)
    self.assertEqual(1, len(computer_partition_list))

    computer_partition = computer_partition_list[0]

    # This Computer Partition shall have only Sale Packing List Line related
    computer_partition_sale_packing_list_line_list = computer_partition\
        .getAggregateRelatedValueList(
            portal_type=self.sale_packing_list_line_portal_type)
    self.assertEqual(1, len(computer_partition_sale_packing_list_line_list))

  def stepCheckPersonRequestedSoftwareInstanceAndRelatedComputerPartition(self,
    sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])
    # in this test it is required to assume that requested_reference
    computer_partition = self._softwareInstance_getComputerPartition(
      software_instance)
    # There should be only one Sale Packing List Line
    sale_packing_list_line_list = software_instance\
        .getAggregateRelatedValueList(
            portal_type=self.sale_packing_list_line_portal_type)
    self.assertEqual(1, len(sale_packing_list_line_list))
    sale_packing_list_line = sale_packing_list_line_list[0]
    # This Sale Packing List Line shall have only one Computer Partition
    computer_partition_list = sale_packing_list_line.getAggregateValueList(
        portal_type='Computer Partition')
    self.assertEqual(1, len(computer_partition_list))

    computer_partition = computer_partition_list[0]

    # This Computer Partition shall have only Sale Packing List Line related
    computer_partition_sale_packing_list_line_list = computer_partition\
        .getAggregateRelatedValueList(
            portal_type=self.sale_packing_list_line_portal_type)
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
    computer_partition_sale_order_line_list = computer_partition\
        .getAggregateRelatedValueList(
            portal_type=self.sale_order_line_portal_type)
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
  # slap.registerSupply
  ########################################

  @skip('Not implemented')
  def test_slap_registerSupply(self):
    """
    """
    raise NotImplementedError

  ########################################
  # Supply.supply
  ########################################

  @skip('Not implemented')
  def test_Supply_supply(self):
    """
    """
    raise NotImplementedError

  ########################################
  # OpenOrder.request
  ########################################

  @skip('Not implemented')
  def test_OpenOrder_request(self):
    """
    """
    raise NotImplementedError

  #########################################
  # SlaveInstance.request
  #########################################

  def stepLoginAsCustomerA(self, sequence):
    global REMOTE_USER
    REMOTE_USER = "test_vifib_customer_a"
    self.login("test_vifib_customer_a")

  def test_SlaveInstance_Person_request_with_Different_User(self):
    """
      Check that user B can declare a slot of slave instance in computer
      partition used by user A
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
    SlapLogout
    LoginAsCustomerA
    PersonRequestSlaveInstance
    Logout
    LoginDefaultUser
    ConfirmOrderedSaleOrderActiveSense
    Tic
    CheckComputerPartitionSaleOrderAggregatedList
    Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_request_after_destroy_SlaveInstance(self):
    """
      Check that a Slave Instance will not be allocated when a Software
      Instance is destroyed 
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_installed_computer_partition_sequence_string + """
        LoginTestVifibCustomer
        RequestSoftwareInstanceDestroy
        Tic
        SlapLogout
        LoginDefaultUser
        CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
        SlapLogout
        LoginTestVifibCustomer
        PersonRequestSlaveInstance
        Tic
        Logout
        LoginDefaultUser
        ConfirmOrderedSaleOrderActiveSense
        Tic
        CheckSlaveInstanceNotReady
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_Person_request_SlaveInstance(self):
    """
      Check that one Slave Instance is created correctly
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
    Tic
    LoginTestVifibCustomer
    PersonRequestSlaveInstance
    Tic
    Logout

    LoginDefaultUser
    ConfirmOrderedSaleOrderActiveSense
    Tic
    
    SetSelectedComputerPartition
    SelectCurrentlyUsedSalePackingListUid
    Logout

    LoginDefaultUser
    CheckComputerPartitionSaleOrderAggregatedList
    Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_getInstanceParameterDict_with_SlaveInstance_stopped(self):
    """
      Check that the Slave Instance is ignored when the state of Sale Packing
      List in stopped.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLogout
      LoginTestVifibCustomer
      SlaveInstanceStopComputerPartitionInstallation
      Tic
      SlaveInstanceStarted
      Tic
      SlaveInstanceStopped
      Tic
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
      SlapLoginCurrentComputer
      CheckEmptySlaveInstanceListFromOneComputerPartition
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_getInstanceParameterDict_with_two_SlaveInstance(self):
    """
      Check that with two Slave Instance installed in different computers, the
      method getInstanceParameterDict returns correctly the slave instance list
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """ 
      Tic
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      ConfirmOrderedSaleOrderActiveSense
      Tic 
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic """ + self.prepare_formated_computer + """
      Tic
      LoginTestVifibDeveloper \
      SelectNewSoftwareReleaseUri \
      CreateSoftwareRelease \
      Tic \
      SubmitSoftwareRelease \
      Tic \
      CreateSoftwareProduct \
      Tic \
      ValidateSoftwareProduct \
      Tic \
      SetSoftwareProductToSoftwareRelease \
      PublishByActionSoftwareRelease \
      Tic
      Logout \
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout
      Tic
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      ConfirmOrderedSaleOrderActiveSense
      Tic
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      CheckSlaveInstanceListFromOneComputerPartition
      """

    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_Person_request_without_SoftwareInstance(self):
    """
      Check that one Slave Instance will wait allocation correctly when no
      exists Software Instance installed
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + \
      self.prepare_published_software_release + """
      Tic
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      Tic
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckSlaveInstanceNotReady
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_Person_request_with_Two_Different_ComputerPartition(self):
    """
      Check that one Slave Instance is allocated correctly when exists two different
      Software Instances and Computer Partition. The slave instance must be
      allocated in Computer Partition that exists one Software Instance with
      the same Software Release.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
    Tic
    StoreSoftwareReleaseUri
    SetRandomComputerReference
    """ + self.prepare_install_requested_computer_partition_sequence_string + """
    Tic
    LoginTestVifibCustomer
    PersonRequestSlaveInstance
    Tic
    ConfirmOrderedSaleOrderActiveSense
    Tic
    CheckSlaveInstanceReady
    CheckSlaveInstanceAllocationWithTwoDifferentSoftwareInstance
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_Person_request_with_Two_Different_SoftwareInstance(self):
    """
      Check that one Slave Instance is allocated correctly when exists two different
      Software Instances. The slave instance must be allocated in the same
      Computer Partition that exists one Software Instance installed.
    """
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      StoreSoftwareReleaseUri
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      ConfirmOrderedSaleOrderActiveSense
      Tic
      """ + self.prepare_published_software_release + """
      Tic
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SelectDifferentSoftwareReleaseUri
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckSlaveInstanceAssociationWithSoftwareInstance
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_Person_request_twice(self):
    """
      Check that request a Slave Instance twice, the instances are created
      correctly
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      LoginAsCustomerA
      PersonRequestSlaveInstance
      SlapLogout

      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckTwoSlaveInstanceRequest
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip("Not Implemented yet")
  def test_request_SlaveInstance_without_enough_slots(self):
    """
     Check the behaviour when one Slave Instance is requested and not exist one
     available slot
    """
    raise NotImplementedError

  def test_SlaveInstance_request_start_when_SoftwareInstance_is_started(self):
    """
      Check that the Slave Instance will be started correctly
      XXX - Review the sequence of steps to verify that the scenario is
      validating the feature of  start a Instance Slave
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SoftwareInstanceStarted
      Tic
      SetDeliveryLineAmountEqualTwo
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_request_stop_from_SoftwareInstance(self):
    """
      Check that the Slave Instance will be stopped correctly when
      a Software Instance is stopped
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      LoginTestVifibCustomer
      StartSoftwareInstanceFromCurrentComputerPartition
      Tic
      SoftwareInstanceStarted
      Tic
      SoftwareInstanceStopped
      Tic
      SetDeliveryLineAmountEqualTwo
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
      CheckComputerPartitionInstanceSetupSalePackingListStopped
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_request_start_from_SoftwareInstance(self):
    """
      Check that the Slave Instance will be started correctly when
      a Software Instance is started
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLogout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      LoginTestVifibCustomer
      StartSoftwareInstanceFromCurrentComputerPartition
      Tic
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SlapLogout
      LoginDefaultUser
      SetDeliveryLineAmountEqualTwo
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      LoginTestVifibCustomer
      RequestStopSoftwareInstanceFromCurrentComputerPartition
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
      StartSoftwareInstanceFromCurrentComputerPartition
      Tic
      SoftwareInstanceStarted
      Tic
      RequestStopSoftwareInstanceFromCurrentComputerPartition
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      StartSoftwareInstanceFromCurrentComputerPartition
      Tic
      SoftwareInstanceStarted
      Tic
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      SetDeliveryLineAmountEqualZero
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLogout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      LoginTestVifibCustomer
      RequestSoftwareInstanceStart
      Tic
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SetDeliveryLineAmountEqualThree
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      RequestStopSoftwareInstanceFromCurrentComputerPartition
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      LoginTestVifibCustomer
      StartSoftwareInstanceFromCurrentComputerPartition
      Tic
      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_call_destroy_from_SoftwareInstance(self):
    """
      Check that the Slave Instance will be stopped correctly when
      a Software Instance is destroyed
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_slave_instance_sequence_string + """
      LoginTestVifibCustomer
      RequestDestroySoftwareInstanceFromCurrentComputerPartition
      Tic
      SetDeliveryLineAmountEqualOne
      CheckComputerPartitionInstanceHostingSalePackingListStopped
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed

      SlapLoginSoftwareInstanceFromCurrentSoftwareInstance
      SoftwareInstanceDestroyed
      Tic
      CheckComputerPartitionInstanceHostingSalePackingListStopped
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_request_stop(self):
    """
      Check that the Slave Instance will be stopped correctly
      XXX - Review the sequence of steps to verify that the scenario is
      validating the feature of stop a Instance Slave
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + """
      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      SlapLogout
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      CheckSuccessComputerGetComputerPartitionCall
      SoftwareInstanceStarted
      Tic
      SlapLogout
      LoginTestVifibCustomer
      RequestSlaveInstanceStop
      Tic
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStopped
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SoftwareInstanceStarted
      Tic
      SlapLogout
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
      Logout
      LoginTestVifibCustomer
      RequestStopSoftwareInstanceFromCurrentComputerPartition
      Tic
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStopped
      Logout
     """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_request_destroy(self):
    """
      Check that the Slave Instance will be destroyed correctly
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      LoginTestVifibCustomer
      RequestSoftwareInstanceDestroy
      Tic
      SlapLogout
      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_check_permission_with_different_customer(self):
    """
      Check that one Customer A can not view the Slave Instance of a Customer B
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLogout
      LoginAsCustomerA
      CheckSlaveInstanceSecurityWithDifferentCustomer
      PersonRequestSlaveInstance
      Tic
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      SlapLogout
      LoginTestVifibCustomer
      CheckSlaveInstanceSecurityWithDifferentCustomer
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_Information_with_getInstanceParameterDict(self):
    """
      Check that Computer Partition of user A is reinstanciated with new
      parameters provided by user B. User B and Aget the right connection
      parameter
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      SlapLoginCurrentComputer
      CheckEmptySlaveInstanceListFromOneComputerPartition
      LoginAsCustomerA
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLoginCurrentComputer
      CheckSlaveInstanceListFromOneComputerPartition
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_security_with_SoftwareInstance_user(self):
    """
      Check that the software instance user can access a Slave Instance
      installed in the same computer partition than your software instance
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      SlapLoginCurrentComputer
      CheckEmptySlaveInstanceListFromOneComputerPartition
      LoginTestVifibCustomer
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      StoreSalePackingListLineFromSlaveInstance
      StoreSaleOrderFromSlaveInstance
      SlapLoginCurrentComputer
      CheckSlaveInstanceListFromOneComputerPartition
      SlapLoginSoftwareInstanceFromCurrentSoftwareInstance
      CheckSlaveInstanceAccessUsingCurrentSoftwareInstanceUser
      CheckSalePackingListFromSlaveInstanceAccessUsingSoftwareInstanceUser
      CheckSaleOrderFromSlaveInstanceAccessUsingSoftwareInstanceUser
      CheckHostingSubscriptionFromSlaveInstanceAccessUsingSoftwareInstanceUser
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SlaveInstance_update_connection_xml(self):
    """
      Check that the connection_xml will be update correctly using portal_slap
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + """
      Tic
      SlapLoginCurrentComputer
      CheckEmptySlaveInstanceListFromOneComputerPartition
      LoginAsCustomerA
      PersonRequestSlaveInstance
      SlapLogout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SlapLoginSoftwareInstanceFromCurrentSoftwareInstance
      SetConnectionXmlToSlaveInstance
      CheckConnectionXmlFromSlaveInstance
      CheckConnectionXmlFromSoftwareInstance
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

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
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  ########################################
  # ComputerPartition.started
  ########################################
  def test_ComputerPartition_started(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_started_computer_partition_sequence_string
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  ########################################
  # ComputerPartition.stopped
  ########################################
  def test_ComputerPartition_stopped(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_stopped_computer_partition_sequence_string
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
      CheckRaisesNotFoundComputerPartitionDestroyedCall \
      SlapLogout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_destroyed_worksOnInstalled(self):
    """Checks default destroy scenario on installed computer partition"""
    sequence_list = SequenceList()
    sequence_string = self.prepare_destroyed_computer_partition
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_destroyed_multiplecalls(self):
    """Checks that destroyed action on free computer partition raises"""
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_installed_computer_partition_sequence_string + '\
      LoginTestVifibCustomer \
      RequestSoftwareInstanceDestroy \
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
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  ########################################
  # Person using PKI/Slap interface
  ########################################

  def _safe_revoke_certificate(self, person):
    from AccessControl import getSecurityManager
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

  def stepPersonRequestSlapSoftwareInstanceNotFoundResponse(self, sequence,
      **kw):
    software_release = sequence['software_release_uri']
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    open_order = self.slap.registerOpenOrder()
    self.assertRaises(slap.NotFoundError, open_order.request,
       software_release=software_release,
       software_type=sequence.get('software_type', 'software_type'),
       partition_reference=sequence.get('requested_reference',
          'requested_reference'),
       partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
       filter_kw=sequence.get('requested_filter_dict', {})
       )

  def stepPersonRequestSlapSoftwareInstanceNotReadyResponse(self, sequence,
      **kw):
    software_release = sequence['software_release_uri']
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    open_order = self.slap.registerOpenOrder()
    self.assertRaises(slap.ResourceNotReady, open_order.request,
       software_release=software_release,
       software_type=sequence.get('software_type', 'software_type'),
       partition_reference=sequence.get('requested_reference',
          'requested_reference'),
       partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
       filter_kw=sequence.get('requested_filter_dict', {})
       )

  def stepSetRandomRequestedReference(self, sequence, **kw):
    sequence['requested_reference'] = self.id() + str(random())

  def stepSetCurrentPersonSlapRequestedSoftwareInstance(self, sequence, **kw):
    software_instance_list = self.portal.portal_catalog(
        portal_type=self.software_instance_portal_type,
        title=sequence['requested_reference'])
    self.assertEqual(1, len(software_instance_list))
    software_instance = software_instance_list[0]
    sequence.edit(
        software_instance_uid=software_instance.getUid(),
        software_instance_reference=software_instance.getReference(),
        hosting_subscription_uid=software_instance.getAggregateRelatedValue(
          portal_type='Sale Order Line').getAggregateValue(
            portal_type='Hosting Subscription').getUid())

  def stepPersonRequestSlapSoftwareInstance(self, sequence, **kw):
    software_release = sequence['software_release_uri']
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url)
    open_order = self.slap.registerOpenOrder()
    requested_slap_computer_partition = open_order.request(
       software_release=software_release,
       software_type=sequence.get('software_type', 'software_type'),
       partition_reference=sequence['requested_reference'],
       partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
       filter_kw=sequence.get('requested_filter_dict', {}))
    sequence.edit(
        requested_slap_computer_partition=requested_slap_computer_partition,
        requested_computer_partition_reference=\
            requested_slap_computer_partition.getId())


  def test_person_request_ComputerPartition(self):
    """Checks that Person using Slap interface is able to request Computer
       Partition"""
    self.computer_partition_amount = 1
    sequence_list = SequenceList()
    sequence_string = self.prepare_published_software_release + \
      self.prepare_formated_computer + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      SetRandomRequestedReference
      SlapLoginTestVifibCustomer
      PersonRequestSlapSoftwareInstanceNotReadyResponse
      Tic
      SlapLogout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout

      SlapLoginTestVifibCustomer
      PersonRequestSlapSoftwareInstance
      Tic
      SlapLogout

      LoginDefaultUser
      SetCurrentPersonSlapRequestedSoftwareInstance
      CheckPersonRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      SlapLogout

      LoginTestVifibCustomer
      CheckViewCurrentSoftwareInstance
      CheckWriteCurrentSoftwareInstance
      Tic
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepSoftwareInstanceSaleOrderConfirmRaisesValueError(self, sequence,
    **kw):
    """Checks that current software instance is realted only with sale order
    
    and that this sale order cannot be confirmed
    
    In Vifib implementation sale order which cannot find free computer partition
    raises ValueError"""
    software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])

    aggregate_value_list = software_instance.getAggregateRelatedValueList(portal_type=[self.sale_packing_list_line_portal_type, self.sale_order_line_portal_type])

    self.assertEqual(1, len(aggregate_value_list))
    self.assertTrue(self.sale_order_line_portal_type in [q.getPortalType() for\
        q in aggregate_value_list])
    sale_order_line = aggregate_value_list[0]
    sale_order = sale_order_line.getParentValue()

    self.assertRaises(ValueError, sale_order.confirm)

  def test_person_request_ComputerPartition_filter_computer_guid(self):
    """Check that requesting with computer_guid in filter_kw works as
       expected in case of person request"""
    self.computer_partition_amount = 1
    sequence_list = SequenceList()
    # There is only one partition on each computer, which has installed
    # software release. But as request has sla parameter, the partition
    # on another computer is not selected, as not following SLA.
    sequence_string = self.prepare_published_software_release + \
      self.prepare_formated_computer + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout
      """ + \
      self.prepare_another_computer_sequence_string + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SetRandomRequestedReference
      SlapLoginTestVifibCustomer
      PersonRequestSlapSoftwareInstanceNotReadyResponse
      Tic
      SlapLogout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      Logout

      SlapLoginTestVifibCustomer
      PersonRequestSlapSoftwareInstance
      Tic
      SlapLogout

      LoginDefaultUser
      SetCurrentPersonSlapRequestedSoftwareInstance
      CheckPersonRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      SelectYetAnotherRequestedReference
      SlapLoginTestVifibCustomer
      PersonRequestSlapSoftwareInstanceNotReadyResponse
      Tic
      SlapLogout

      LoginDefaultUser
      SetCurrentPersonSlapRequestedSoftwareInstance
      SoftwareInstanceSaleOrderConfirmRaisesValueError
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  ########################################
  # Bug related tests
  ########################################

  def test_bug_Person_request_more_then_one_instance(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self.prepare_person_requested_software_instance + '\
      LoginTestVifibCustomer \
      PersonRequestSoftwareInstance \
      Tic \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_ComputerPartition_request_two_similar(self):
    """
    Checks that requesting twice with different arguments from same Computer
    Partition will return different objects."""
    self.computer_partition_amount = 3
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentSoftwareInstance \
      RequestTwoAndCheckDifferentResult \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_doubleClickOnStart(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_stopped_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      RequestSoftwareInstanceStart
      RequestSoftwareInstanceStartRaisesValueError
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_doubleClickOnStart_serializeIsCalled(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_stopped_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      RequestSoftwareInstanceStartCheckSerializeIsCalled
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_doubleClickOnDestroy(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_installed_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      RequestSoftwareInstanceDestroy
      RequestSoftwareInstanceDestroyRaisesValueError
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_doubleClickOnDestroy_serializeIsCalled(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_installed_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      RequestSoftwareInstanceDestroyCheckSerializeIsCalled
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepArchiveSoftwareRelease(self, sequence, **kw):
    """
    Submit the software release document.
    """
    software_release_uid = sequence["software_release_uid"]
    software_release = self.portal.portal_catalog.getResultValue(
        uid=software_release_uid)
    software_release.portal_workflow.doActionFor(software_release,
                                                 'archive_action')

  def test_bug_archived_software_release_access(self):
    """Checks that Computer has access to archived Software Release"""
    sequence_string = self.\
      prepare_start_requested_computer_partition_sequence_string + \
      """
      LoginTestVifibDeveloper
      ArchiveSoftwareRelease
      Tic
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout
    """
    sequence_list = SequenceList()
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepStoreCurrentSoftwareInstanceUidBufferA(self, sequence, **kw):
    sequence['buffer_a_software_instance_uid'] = sequence['software_instance_uid']

  def stepStoreCurrentSoftwareInstanceUidBufferB(self, sequence, **kw):
    sequence['buffer_b_software_instance_uid'] = sequence['software_instance_uid']

  def stepStoreCurrentComputerUidBufferA(self, sequence, **kw):
    sequence['buffer_a_computer_uid'] = sequence['computer_uid']

  def stepStoreCurrentComputerUidBufferB(self, sequence, **kw):
    sequence['buffer_b_computer_uid'] = sequence['computer_uid']

  def stepRestoreSoftwareInstanceUidFromBufferA(self, sequence, **kw):
    sequence['software_instance_uid'] = sequence['buffer_a_software_instance_uid']

  def stepRestoreSoftwareInstanceUidFromBufferB(self, sequence, **kw):
    sequence['software_instance_uid'] = sequence['buffer_b_software_instance_uid']

  def stepRestoreComputerUidFromBufferA(self, sequence, **kw):
    sequence['computer_uid'] = sequence['buffer_a_computer_uid']

  def stepRestoreComputerUidFromBufferB(self, sequence, **kw):
    sequence['computer_uid'] = sequence['buffer_b_computer_uid']

  def stepStoreCurrentComputerReferenceBufferA(self, sequence, **kw):
    sequence['buffer_a_computer_reference'] = sequence['computer_reference']

  def stepStoreCurrentComputerReferenceBufferB(self, sequence, **kw):
    sequence['buffer_b_computer_reference'] = sequence['computer_reference']

  def stepStoreCurrentComputerPartitionUidBufferA(self, sequence, **kw):
    sequence['buffer_a_computer_partition_uid'] = sequence['computer_partition_uid']

  def stepStoreCurrentComputerPartitionUidBufferB(self, sequence, **kw):
    sequence['buffer_b_computer_partition_uid'] = sequence['computer_partition_uid']

  def stepStoreCurrentComputerPartitionReferenceBufferA(self, sequence, **kw):
    sequence['buffer_a_computer_partition_reference'] = sequence['computer_partition_reference']

  def stepStoreCurrentComputerPartitionReferenceBufferB(self, sequence, **kw):
    sequence['buffer_b_computer_partition_reference'] = sequence['computer_partition_reference']

  def stepRestoreComputerReferenceFromBufferA(self, sequence, **kw):
    sequence['computer_reference'] = sequence['buffer_a_computer_reference']

  def stepRestoreComputerReferenceFromBufferB(self, sequence, **kw):
    sequence['computer_reference'] = sequence['buffer_b_computer_reference']

  def stepRestoreComputerPartitionUidFromBufferA(self, sequence, **kw):
    sequence['computer_partition_uid'] = sequence['buffer_a_computer_partition_uid']

  def stepRestoreComputerPartitionUidFromBufferB(self, sequence, **kw):
    sequence['computer_partition_uid'] = sequence['buffer_b_computer_partition_uid']

  def stepRestoreComputerPartitionReferenceFromBufferA(self, sequence, **kw):
    sequence['computer_partition_reference'] = sequence['buffer_a_computer_partition_reference']

  def stepRestoreComputerPartitionReferenceFromBufferB(self, sequence, **kw):
    sequence['computer_partition_reference'] = sequence['buffer_b_computer_partition_reference']

  def stepCheckHostingSubscriptionMultipleComputerAuditor(self, sequence, **kw):
    hosting_subscription = self.portal.portal_catalog.getResultValue(
      uid=sequence['hosting_subscription_uid'])
    role_list = hosting_subscription.get_local_roles()
    setup_packing_list_line_list = [q for q in
      hosting_subscription.getAggregateRelatedValueList(
        portal_type='Sale Packing List Line') if q.getResource() ==
          self.portal.portal_preferences.getPreferredInstanceSetupResource()]
    computer_list = [q.getAggregateValue(
      portal_type='Computer Partition').getParentValue() for q in
        setup_packing_list_line_list]
    for computer in computer_list:
      self.assertTrue((computer.getReference(), ('Auditor',))) in role_list

  def test_bug_destruction_of_partition_originated_from_another_computer(self):
    """Checks that computer is capable to destroy own Software Instance

    If software instance originated on computer comes from another computer it
    shall be possible to sucesfully destroy it.

    Test is done in a way to trigger unstable Assignor role calculation
    on Hosting Subscription which leads to unavailability of Software Instances
    from one computer to another.
    """
    sequence_list = SequenceList()
    sequence_string = """
      # Prepare software release shared by both Computers
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic
      SubmitSoftwareRelease
      Tic
      CreateSoftwareProduct
      Tic
      ValidateSoftwareProduct
      Tic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      Logout

      # Create first computer
      LoginTestVifibAdmin
      CreateComputer
      Tic
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferA
      StoreCurrentComputerUidBufferA

      # Install software on first computer
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      # Now request and instantiate this software release on first computer
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      StoreCurrentComputerPartitionReferenceBufferA
      StoreCurrentComputerPartitionUidBufferA
      StoreCurrentSoftwareInstanceUidBufferA

      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # Start it..
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout

      LoginDefaultUser
      SetSelectedComputerPartition
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout

      # ...stop it...

      LoginDefaultUser
      RequestSoftwareInstanceStop
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStopped
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
      Logout

      # ...and request destruction
      LoginDefaultUser
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      # Now prepare second computer

      LoginTestVifibAdmin
      CreateComputer
      Tic
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferB
      StoreCurrentComputerUidBufferB

      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferB
      StoreCurrentComputerUidBufferB

      # Now request self software release from one computer to another
      RestoreComputerReferenceFromBufferA
      RestoreComputerUidFromBufferA
      RestoreSoftwareInstanceUidFromBufferA
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotReadyResponse
      Tic
      SlapLogout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      LoginDefaultUser
      SetCurrentSoftwareInstanceRequested
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      Logout

      StoreCurrentComputerPartitionReferenceBufferB
      StoreCurrentComputerPartitionUidBufferB
      StoreCurrentSoftwareInstanceUidBufferB

      RestoreComputerReferenceFromBufferB
      RestoreComputerUidFromBufferB

      # Start the requested software instance...

      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout

      LoginDefaultUser
      SetSelectedComputerPartition
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout

      # ...and stop it

      LoginDefaultUser
      RequestSoftwareInstanceStop
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStopped
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListDelivered
      Logout

      # Now request destruction of second software instance...

      LoginDefaultUser
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      # ...and destroy it

      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionIsFree
      Logout

      # Time to switch back to first software instance and destroy it
      RestoreComputerPartitionReferenceFromBufferA
      RestoreComputerPartitionUidFromBufferA
      RestoreSoftwareInstanceUidFromBufferA
      RestoreComputerReferenceFromBufferA
      RestoreComputerUidFromBufferA

      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionIsFree
      Logout

      LoginDefaultUser
      CheckHostingSubscriptionMultipleComputerAuditor
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_destruction_confirmed_instance_setup(self):
    """Proves that all is correctly handled in case of confirmed instance
    setup packing list existence"""
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + \
      """
      LoginTestVifibCustomer
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      # Now there are two packing lists in confirmed state:
      #  * one for instance setup
      #  * one for instance destruction
      # Simulate typical scenario:
      #  * stopped
      #  * commit
      #  * destroyed
      #  * commit
      #  * tic

      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      SoftwareInstanceDestroyed
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionIsFree
      CheckComputerPartitionNoInstanceHostingSalePackingList
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_destruction_with_cancelled_packing_list(self):
    """Proves that even if some packing lists are in cancelled state
    it is possible to destroy software instance"""
    sequence_list = SequenceList()
    sequence_string = self.prepare_stopped_computer_partition_sequence_string + """
      # Request destruction...
      LoginDefaultUser
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      # and cancel current destruction.
      LoginDefaultUser
      SelectCurrentlyUsedSalePackingListUid
      CancelSalePackingList
      Tic
      CheckComputerPartitionInstanceCleanupSalePackingListCancelled
      Logout

      # So all packing lists are finished, but one is cancelled,
      # time to request destruction...

      LoginDefaultUser
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      # ...and destroy it

      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionIsFree
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_bug_destruction_with_unfinished_packing_list(self):
    """Proves that even if some packing lists are not fully delivered
    it is possible to destroy software instance"""
    sequence_list = SequenceList()
    sequence_string = """
      # Prepare software release
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic
      SubmitSoftwareRelease
      Tic
      CreateSoftwareProduct
      Tic
      ValidateSoftwareProduct
      Tic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      Logout

      # Create first computer
      LoginTestVifibAdmin
      CreateComputer
      Tic
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferA
      StoreCurrentComputerUidBufferA

      # Install software on first computer
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      # Now request and instantiate this software release on first computer
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # Request destruction...
      LoginDefaultUser
      RequestSoftwareInstanceDestroy
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout

      # ...and destroy it

      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionIsFree
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepDirectRequestComputerPartitionRaisesDisconnectedSoftwareTree(self,
    sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
      uid = sequence['software_instance_uid'])
    from erp5.document.SoftwareInstance import DisconnectedSoftwareTree
    self.assertRaises(DisconnectedSoftwareTree,
      software_instance.requestSoftwareInstance,
      software_release=sequence['software_release_uri'],
      software_type=sequence['requested_reference'],
      partition_reference=sequence['requested_reference'],
      shared=False,
      instance_xml=self.minimal_correct_xml,
      sla_xml=self.minimal_correct_xml,
      state='started'
    )

  def test_bug_orhpaned_software_instance(self):
    """Check that no orphaned Software Instances would be created

    In below scenario system shall behave like mentioned:

      OpenOrder.request(SR, A)  | SR(A)
      A.request(SR, B)          | SR(A) <- SR(B)
      B.request(SR, C)          | SR(A) <- SR(B) <- SR(C)
      C.request(SR, B) raises immediately, because the result would be:
        SR(A)
        SR(B) <- SR(C)
      do B would become root of orphaned tree.
    """
    # Setup sufficient amount of CP
    self.computer_partition_amount = 3
    sequence_list = SequenceList()
    sequence_string = """
      # Prepare software release
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic
      SubmitSoftwareRelease
      Tic
      CreateSoftwareProduct
      Tic
      ValidateSoftwareProduct
      Tic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      Logout

      # Create the computer
      LoginTestVifibAdmin
      CreateComputer
      Tic
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferA
      StoreCurrentComputerUidBufferA

      # Install the software release
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      # Create Software Instance A (originates from Open Order)
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # From root request B
      SelectRequestedReferenceB
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotReadyResponse
      Tic
      SlapLogout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      LoginDefaultUser
      SetCurrentSoftwareInstanceRequested
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      Logout

      # From B request C
      SelectRequestedReferenceC
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotReadyResponse
      Tic
      SlapLogout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      LoginDefaultUser
      SetCurrentSoftwareInstanceRequested
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      Logout

      # Try to: from C request B and prove that it raises
      SelectRequestedReferenceB

      LoginDefaultUser # login as superuser in order to work in erp5
      DirectRequestComputerPartitionRaisesDisconnectedSoftwareTree
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepDirectRequestComputerPartitionRaisesCyclicSoftwareTree(self,
    sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
      uid = sequence['software_instance_uid'])
    from erp5.document.SoftwareInstance import CyclicSoftwareTree
    self.assertRaises(CyclicSoftwareTree,
      software_instance.requestSoftwareInstance,
      software_release=sequence['software_release_uri'],
      software_type=sequence['requested_reference'],
      partition_reference=sequence['requested_reference'],
      shared=False,
      instance_xml=self.minimal_correct_xml,
      sla_xml=self.minimal_correct_xml,
      state='started'
    )

  def test_bug_cyclic_software_instance(self):
    """Check that no cyclic Software Instance trees would be created

    In below scenario system shall behave like mentioned:

      OpenOrder.request(SR, A)  | SR(A)
      A.request(SR, B)          | SR(A) <- SR(B)
      B.request(SR, A)          | SR(A) <- SR(B) <- SR(C)
      C.request(SR, B) raises immediately, because the result would be:
        SR(A)
        SR(B) <-> SR(C)
      so B and C would be cyclic
    """
    # Setup sufficient amount of CP
    self.computer_partition_amount = 3
    sequence_list = SequenceList()
    sequence_string = """
      # Prepare software release
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic
      SubmitSoftwareRelease
      Tic
      CreateSoftwareProduct
      Tic
      ValidateSoftwareProduct
      Tic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      Logout

      # Create the computer
      LoginTestVifibAdmin
      CreateComputer
      Tic
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferA
      StoreCurrentComputerUidBufferA

      # Install the software release
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      # Create Software Instance A (originates from Open Order)
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # From root request B
      SelectRequestedReferenceB
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotReadyResponse
      Tic
      SlapLogout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      LoginDefaultUser
      SetCurrentSoftwareInstanceRequested
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      Logout

      # From B request C
      SelectRequestedReferenceC
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotReadyResponse
      Tic
      SlapLogout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      LoginDefaultUser
      SetCurrentSoftwareInstanceRequested
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      Logout

      # Try to: from C request B and prove that it raises
      SelectRequestedReferenceB

      LoginDefaultUser # login as superuser in order to work in erp5
      DirectRequestComputerPartitionRaisesCyclicSoftwareTree
      """
    sequence_list.addSequenceString(sequence_string)
    import erp5.document.SoftwareInstance
    def makeTrue(*args, **kwargs):
      return True
    # Disable temporialy checkConnected in order to have only
    # checkCyclic called
    erp5.document.SoftwareInstance.original_checkConnected = \
      erp5.document.SoftwareInstance.checkConnected
    erp5.document.SoftwareInstance.checkConnected = makeTrue
    try:
      sequence_list.play(self)
    finally:
      erp5.document.SoftwareInstance.checkConnected = \
        erp5.document.SoftwareInstance.original_checkConnected
      del(erp5.document.SoftwareInstance.original_checkConnected)

  def stepDirectRequestComputerPartitionRaisesValueError(self,
    sequence, **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
      uid = sequence['software_instance_uid'])
    self.assertRaises(ValueError,
      software_instance.requestSoftwareInstance,
      software_release=sequence['software_release_uri'],
      software_type=sequence['requested_reference'],
      partition_reference=sequence['requested_reference'],
      shared=False,
      instance_xml=self.minimal_correct_xml,
      sla_xml=self.minimal_correct_xml,
      state='started'
    )

  def test_bug_cyclic_software_instance_small_tree(self):
    """Check that no cyclic Software Instance trees would be created

    In below scenario system shall behave like mentioned:

      OpenOrder.request(SR, A)  | SR(A)
      A.request(SR, B)          | SR(A) <- SR(B)
      B.request(SR, A) raises immediately, because the result would be:
        SR(A) <-> SR(B)
      so B and A would be cyclic
    """
    # Setup sufficient amount of CP
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = """
      # Prepare software release
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic
      SubmitSoftwareRelease
      Tic
      CreateSoftwareProduct
      Tic
      ValidateSoftwareProduct
      Tic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      Logout

      # Create the computer
      LoginTestVifibAdmin
      CreateComputer
      Tic
      Logout
      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout
      StoreCurrentComputerReferenceBufferA
      StoreCurrentComputerUidBufferA

      # Install the software release
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout
      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      # Create Software Instance A (originates from Open Order)
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # From root request B
      SelectRequestedReferenceB
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotReadyResponse
      Tic
      SlapLogout

      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartitionNoPackingListCheck
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      LoginDefaultUser
      SetCurrentSoftwareInstanceRequested
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      Logout

      # Try to: From B request root
      SelectRequestedReferenceRootSoftwareInstanceTitle

      LoginDefaultUser # login as superuser in order to work in erp5
      DirectRequestComputerPartitionRaisesValueError
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  ########################################
  # Software Instance graph helpers
  ########################################

  def _test_si_tree(self):
    software_instance = self.portal.software_instance_module.newContent(
      portal_type='Software Instance')
    self.checkConnected = software_instance.checkConnected
    self.checkNotCyclic = software_instance.checkNotCyclic

  def test_si_tree_simple_connected(self):
    """Graph of one element is connected

    A
    """
    self._test_si_tree()
    graph = {'A': []}
    root = 'A'
    self.assertEqual(True, self.checkConnected(graph, root))

  def test_si_tree_simple_list_connected(self):
    """Graph of list is connected

    B->C->A
    """
    self._test_si_tree()
    graph = {'A': [], 'B': ['C'], 'C': ['A']}
    root = 'B'
    self.assertEqual(True, self.checkConnected(graph, root))

  def test_si_tree_complex_connected(self):
    """Tree is connected

    B --> A
      \-> C --> D
            \-> E --> F
    """
    self._test_si_tree()
    graph = {
      'A': [],
      'B': ['A', 'C'],
      'C': ['D', 'E'],
      'D': [],
      'E': ['F'],
      'F': [],
    }
    root = 'B'
    self.assertEqual(True, self.checkConnected(graph, root))

  def test_si_tree_simple_list_disconnected(self):
    """Two lists are disconnected

    A->B
    C
    """
    self._test_si_tree()
    graph = {'A': ['B'], 'B': [], 'C': []}
    root = 'A'
    from erp5.document.SoftwareInstance import DisconnectedSoftwareTree
    self.assertRaises(DisconnectedSoftwareTree, self.checkConnected, graph,
      root)

  # For now limitation of implementation gives false positive
  @expectedFailure
  def test_si_tree_cyclic_connected(self):
    """Cyclic is connected

    A<->B
    """
    self._test_si_tree()
    graph = {'A': ['B'], 'B': ['A']}
    root = 'B'
    self.assertEqual(True, self.checkConnected(graph, root))

  def test_si_tree_cyclic_disconnected(self):
    """Two trees, where one is cyclic are disconnected

    B --> A
      \-> H
    C --> D --> G
    ^ \-> E --> F \
     \------------/
    """
    self._test_si_tree()
    graph = {
      'A': [],
      'B': ['A', 'H'],
      'C': ['D', 'E'],
      'D': ['G'],
      'E': ['F'],
      'F': ['C'],
      'G': [],
      'H': [],
    }
    root = 'B'
    from erp5.document.SoftwareInstance import DisconnectedSoftwareTree
    self.assertRaises(DisconnectedSoftwareTree, self.checkConnected, graph,
      root)

  def test_si_tree_simple_not_cyclic(self):
    """Graph of one element is not cyclic

    A
    """
    self._test_si_tree()
    graph = {'A': []}
    self.assertEqual(True, self.checkNotCyclic(graph))

  def test_si_tree_simple_list_not_cyclic(self):
    """Graph of list is not cyclic

    B->C->A
    """
    self._test_si_tree()
    graph = {'A': [], 'B': ['C'], 'C': ['A']}
    self.assertEqual(True, self.checkNotCyclic(graph))

  def test_si_tree_simple_list_cyclic(self):
    """Graph of cyclic list is cyclic

    B->C->A-\
    ^-------/
    """
    self._test_si_tree()
    graph = {'A': ['B'], 'B': ['C'], 'C': ['A']}
    from erp5.document.SoftwareInstance import CyclicSoftwareTree
    self.assertRaises(CyclicSoftwareTree, self.checkNotCyclic, graph)

  def test_si_tree_simple_list_cyclic_non_root(self):
    """Graph of cyclic list is cyclic

    B->C->D->A-\
       ^-------/
    """
    self._test_si_tree()
    graph = {'A': ['C'], 'B': ['C'], 'C': ['D'], 'D': ['A']}
    from erp5.document.SoftwareInstance import CyclicSoftwareTree
    self.assertRaises(CyclicSoftwareTree, self.checkNotCyclic, graph)

  def test_si_tree_complex_not_cyclic(self):
    """Tree is not cyclic

    B --> A
      \-> C --> D
            \-> E --> F
    """
    self._test_si_tree()
    graph = {
      'A': [],
      'B': ['A', 'C'],
      'C': ['D', 'E'],
      'D': [],
      'E': ['F'],
      'F': [],
    }
    self.assertEqual(True, self.checkNotCyclic(graph))

  def test_si_tree_complex_cyclic(self):
    """Tree is not cyclic

    B --> A
      \-> C --> D
          ^ \-> E --> F -\
           \-------------/
    """
    self._test_si_tree()
    graph = {
      'A': [],
      'B': ['A', 'C'],
      'C': ['D', 'E'],
      'D': [],
      'E': ['F'],
      'F': ['C'],
    }
    from erp5.document.SoftwareInstance import CyclicSoftwareTree
    self.assertRaises(CyclicSoftwareTree, self.checkNotCyclic, graph)

  def test_si_tree_simple_list_disconnected_not_cyclic(self):
    """Two lists are disconnected

    A->B
    C
    """
    self._test_si_tree()
    graph = {'A': ['B'], 'B': [], 'C': []}
    self.assertEqual(True, self.checkNotCyclic(graph))

  def test_si_tree_cyclic(self):
    """Cyclic is connected

    A<->B
    """
    self._test_si_tree()
    graph = {'A': ['B'], 'B': ['A']}
    from erp5.document.SoftwareInstance import CyclicSoftwareTree
    self.assertRaises(CyclicSoftwareTree, self.checkNotCyclic, graph)

  def test_si_tree_cyclic_disconnected_cyclic(self):
    """Two trees, where one is cyclic are disconnected

    B --> A
      \-> H
    C --> D --> G
    ^ \-> E --> F \
     \------------/
    """
    self._test_si_tree()
    graph = {
      'A': [],
      'B': ['A', 'H'],
      'C': ['D', 'E'],
      'D': ['G'],
      'E': ['F'],
      'F': ['C'],
      'G': [],
      'H': ['A'],
    }
    from erp5.document.SoftwareInstance import CyclicSoftwareTree
    self.assertRaises(CyclicSoftwareTree, self.checkNotCyclic, graph)

  ########################################
  # Other tests
  ########################################

  def stepRequestCredentialFromWebSite(self, sequence, **kw):
    sequence['web_user'] = '%s.%s' % (self.id(), random())
    self.portal.ERP5Site_newCredentialRequest(\
        first_name='Homer',
        last_name='Simpson',
        reference=sequence['web_user'],
        password='secret',
        default_email_text='homer.simpson@fox.com',
        )

  def stepSubmitCredentialRequest(self, sequence, **kw):
    """Simulates click of user in email confirmation about account"""
    credential_request = self.portal.portal_catalog.getResultValue(
      portal_type='Credential Request',
      reference=sequence['web_user']
      )
    credential_request.submit()

  def stepAcceptSubmittedCredentialsActiveSense(self, **kw):
    self.portal.portal_alarms.accept_submitted_credentials.activeSense()

  def stepLoginWebUser(self, sequence, **kw):
    self.login(sequence['web_user'])

  def test_person_from_credential_request_software_instance(self):
    """Checks that person created from web can use the system"""
    sequence_list = SequenceList()
    sequence_string = self.prepare_published_software_release + \
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
      AcceptSubmittedCredentialsActiveSense
      Tic
      Logout

      LoginWebUser
      PersonRequestSoftwareInstance
      Tic
      Logout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepPersonRequestCredentialUpdate(self, sequence, **kw):
    sequence['updated_last_name'] = 'Another'
    result = self.portal.ERP5Site_newPersonCredentialUpdate(
        first_name='Homer',
        last_name=sequence['updated_last_name'],
        reference=sequence['web_user'],
        password='secret',
        default_email_text='homer.simpson@fox.com',
    )
    self.assertTrue('Credential%20Update%20Created' in result)

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
      AcceptSubmittedCredentialsActiveSense
      Tic
      Logout

      LoginWebUser
      PersonRequestCredentialUpdate
      Tic
      Logout

      LoginDefaultUser
      AcceptSubmittedCredentialsActiveSense
      Tic

      LoginWebUser
      CheckPersonUpdatedCredential
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
