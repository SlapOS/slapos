# -*- coding:utf-8 -*-
##############################################################################
#
# Copyright (c) 2002-2013 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#
##############################################################################

import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from Products.ERP5Type.tests.utils import createZODBPythonScript
import json
from DateTime import DateTime

class TestSlapOSCloudSupportRequestGeneration(testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSCloudSupportRequestGeneration, self).afterSetUp()
    self.new_id = self.generateNewId()

  def _makeComputer(self,new_id):
    # Clone computer document
    computer = self.portal.computer_module\
      .template_computer.Base_createCloneDocument(batch_mode=1)
    computer.edit(
      title="computer ticket %s" % (new_id, ),
      reference="TESTCOMPT-%s" % (new_id, )
    )
    computer.validate()

    return computer

  def _makeComputerPartitions(self,computer):
    for i in range(1, 5):
      id_ = 'partition%s' % (i, )
      p = computer.newContent(portal_type='Computer Partition',
        id=id_,
        title=id_,
        reference=id_,
        default_network_address_ip_address='ip_address_%s' % i,
        default_network_address_netmask='netmask_%s' % i)
      p.markFree()
      p.validate()

  def _makeHostingSubscription(self, new_id):
    hosting_subscription = self.portal\
      .hosting_subscription_module.template_hosting_subscription\
      .Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    hosting_subscription.edit(
        title= "Test hosting sub ticket %s" % new_id,
        reference="TESTHST-%s" % new_id,
    )

    return hosting_subscription

  def _makeSoftwareInstance(self, hosting_subscription, software_url):

    kw = dict(
      software_release=software_url,
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='started'
    )
    hosting_subscription.requestStart(**kw)
    hosting_subscription.requestInstance(**kw)

  def test_Base_generateSupportRequestForSlapOS(self):
    title = "Test Support Request %s" % self.new_id
    computer = self._makeComputer(self.new_id)
    computer.Base_generateSupportRequestForSlapOS(title,title)
    self.tic()
    support_request = self.portal.portal_catalog.getResultValue(
      portal_type = 'Support Request',
      title = title,
      simulation_state = ["validated","submitted","suspended"]
    )

    self.assertNotEqual(support_request,None)

  def test_Base_generateSupportRequestForSlapOS_do_not_recreate_if_open(self):
    title = "Test Support Request %s" % self.new_id
    computer = self._makeComputer(self.new_id)
    computer.Base_generateSupportRequestForSlapOS(title,title)
    self.tic()

    computer.Base_generateSupportRequestForSlapOS(title,title)
    self.tic()

    support_request_list = self.portal.portal_catalog(
      portal_type = 'Support Request',
      title = title,
      simulation_state = ["validated","submitted","suspended"]
    )

    self.assertEqual(len(support_request_list),1)

  def test_Base_generateSupportRequestForSlapOS_recreate_if_closed(self):
    title = "Test Support Request %s" % self.new_id
    computer = self._makeComputer(self.new_id)
    computer.Base_generateSupportRequestForSlapOS(title,title)
    self.tic()

    support_request = self.portal.portal_catalog.getResultValue(
      portal_type = 'Support Request',
      title = title,
      simulation_state = ["validated","submitted","suspended"]
    )
    support_request.invalidate()
    self.tic()

    computer.Base_generateSupportRequestForSlapOS(title,title)
    self.tic()

    support_request_list = self.portal.portal_catalog(
      portal_type = 'Support Request',
      title = title
    )

    self.assertEqual(len(support_request_list),2)

    support_request_list = self.portal.portal_catalog(
      portal_type = 'Support Request',
      title = title,
      simulation_state = ["validated","submitted","suspended"]
    )

    self.assertEqual(len(support_request_list),1)

  def _simulateBase_generateSupportRequestForSlapOS(self):
    script_name = 'Base_generateSupportRequestForSlapOS'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Base_generateSupportRequestForSlapOS') """ )
    transaction.commit()

  def _dropBase_generateSupportRequestForSlapOS(self):
    script_name = 'Base_generateSupportRequestForSlapOS'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_Computer_checkState(self):
    computer = self._makeComputer(self.new_id)
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

    memcached_dict[computer.getReference()] = json.dumps(
        {"created_at":"%s" % (DateTime() - 1.1)}
    )

    self._simulateBase_generateSupportRequestForSlapOS()

    try:
      computer.Computer_checkState()
      self.tic()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertEqual('Visited by Base_generateSupportRequestForSlapOS',
      computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_Computer_checkState_empty_cache(self):
    computer = self._makeComputer(self.new_id)

    self._simulateBase_generateSupportRequestForSlapOS()

    try:
      computer.Computer_checkState()
      self.tic()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertNotEqual('Visited by Base_generateSupportRequestForSlapOS',
      computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareInstance_checkState_error_out_time(self):
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub,self.generateNewSoftwareReleaseUrl())
    instance = host_sub.getPredecessorValue()
    
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

    memcached_dict[instance.getReference()] = json.dumps(
        {"created_at":"%s" % (DateTime() - 0.1), "text":"#error "}
    )

    self._simulateBase_generateSupportRequestForSlapOS()

    try:
      instance.SoftwareInstance_checkState()
      self.tic()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertEqual('Visited by Base_generateSupportRequestForSlapOS',
      instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareInstance_checkState_error_in_time(self):
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub,self.generateNewSoftwareReleaseUrl())
    instance = host_sub.getPredecessorValue()
    
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

    memcached_dict[instance.getReference()] = json.dumps(
        {"created_at":"%s" % (DateTime()), "text":"#error "}
    )

    self._simulateBase_generateSupportRequestForSlapOS()

    try:
      instance.SoftwareInstance_checkState()
      self.tic()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertNotEqual('Visited by Base_generateSupportRequestForSlapOS',
      instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareInstance_checkState_access_out_time(self):
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub,self.generateNewSoftwareReleaseUrl())
    instance = host_sub.getPredecessorValue()
    
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

    memcached_dict[instance.getReference()] = json.dumps(
        {"created_at":"%s" % (DateTime() - 1.1), "text":"#access "}
    )

    self._simulateBase_generateSupportRequestForSlapOS()

    try:
      instance.SoftwareInstance_checkState()
      self.tic()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertEqual('Visited by Base_generateSupportRequestForSlapOS',
      instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareInstance_checkState_access_in_time(self):
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub,self.generateNewSoftwareReleaseUrl())
    instance = host_sub.getPredecessorValue()
    
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

    memcached_dict[instance.getReference()] = json.dumps(
        {"created_at":"%s" % (DateTime()), "text":"#access "}
    )

    self._simulateBase_generateSupportRequestForSlapOS()

    try:
      instance.SoftwareInstance_checkState()
      self.tic()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertNotEqual('Visited by Base_generateSupportRequestForSlapOS',
      instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareInstance_checkState_empty_cache(self):
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub,self.generateNewSoftwareReleaseUrl())
    instance = host_sub.getPredecessorValue()
    
    self._simulateBase_generateSupportRequestForSlapOS()

    try:
      instance.SoftwareInstance_checkState()
      self.tic()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertNotEqual('Visited by Base_generateSupportRequestForSlapOS',
      instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_Alarm_checkCloudIsFull(self):
    computer = self._makeComputer(self.new_id)
    computer.edit(capacity_scope='close')

    self._simulateBase_generateSupportRequestForSlapOS()
    try:
      self.portal.portal_alarms.slapos_check_cloud_is_full.activeSense()
      self.tic()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()

    self.assertEqual('Visited by Base_generateSupportRequestForSlapOS',
      self.portal.portal_alarms.slapos_check_cloud_is_full.workflow_history['edit_workflow'][-1]['comment'])

  def test_Alarm_checkCloudIsFull_open_computer(self):
    computer = self._makeComputer(self.new_id)
    computer.edit(capacity_scope='open')
    self.tic()

    # Reset slapos_check_cloud_is_full workflow_history for edit_workflow last action
    self.portal.portal_alarms.slapos_check_cloud_is_full.workflow_history['edit_workflow'][-1]['comment'] = ''

    self._simulateBase_generateSupportRequestForSlapOS()
    try:
      self.portal.portal_alarms.slapos_check_cloud_is_full.activeSense()
      self.tic()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()

    self.assertNotEqual('Visited by Base_generateSupportRequestForSlapOS',
                        self.portal.portal_alarms.slapos_check_cloud_is_full.workflow_history['edit_workflow'][-1]['comment'])

  def _simulateSoftwareInstance_checkState(self):
    script_name = 'SoftwareInstance_checkState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by SoftwareInstance_checkState') """ )
    transaction.commit()

  def _dropSoftwareInstance_checkState(self):
    script_name = 'SoftwareInstance_checkState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_Computer_checkSoftwareInstanceState(self):
    computer = self._makeComputer(self.new_id)
    self._makeComputerPartitions(computer)
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub, self.generateNewSoftwareReleaseUrl())
    instance = host_sub.getPredecessorValue()
    instance.edit(aggregate_value = computer.partition1.getRelativeUrl())
    computer.partition1.markBusy()
    self.tic()
    
    self._simulateSoftwareInstance_checkState()
    try:
      computer.Computer_checkSoftwareInstanceState()
      self.tic()
    finally:
      self._dropSoftwareInstance_checkState()

    self.assertEqual('Visited by SoftwareInstance_checkState',
      instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_Computer_checkSoftwareInstanceState_instance_not_allocated(self):
    computer = self._makeComputer(self.new_id)
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub, self.generateNewSoftwareReleaseUrl())
    instance = host_sub.getPredecessorValue()
    self.tic()
    
    self._simulateSoftwareInstance_checkState()
    try:
      computer.Computer_checkSoftwareInstanceState()
      self.tic()
    finally:
      self._dropSoftwareInstance_checkState()

    self.assertNotEqual('Visited by SoftwareInstance_checkState',
      instance.workflow_history['edit_workflow'][-1]['comment'])

  def _simulateComputer_checkState(self):
    script_name = 'Computer_checkState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Computer_checkState') """ )
    transaction.commit()

  def _dropComputer_checkState(self):
    script_name = 'Computer_checkState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_Alarm_checkComputerState(self):
    computer = self._makeComputer(self.new_id)
    computer.edit(allocation_scope = 'open/public')
    
    self._simulateComputer_checkState()

    try:
      self.portal.portal_alarms.slapos_check_computer_state.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkState()

    self.assertEqual('Visited by Computer_checkState',
      computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_Alarm_checkComputerState_no_public_computer(self):
    computer = self._makeComputer(self.new_id)
    
    self._simulateComputer_checkState()

    try:
      self.portal.portal_alarms.slapos_check_computer_state.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkState()

    self.assertNotEqual('Visited by Computer_checkState',
      computer.workflow_history['edit_workflow'][-1]['comment'])

  def _simulateComputer_checkSoftwareInstanceState(self):
    script_name = 'Computer_checkSoftwareInstanceState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Computer_checkSoftwareInstanceState') """ )
    transaction.commit()

  def _dropComputer_checkSoftwareInstanceState(self):
    script_name = 'Computer_checkSoftwareInstanceState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_Alarm_checkSoftwareInstanceState(self):
    computer = self._makeComputer(self.new_id)
    computer.edit(allocation_scope = 'open/public')
    
    self._simulateComputer_checkSoftwareInstanceState()

    try:
      self.portal.portal_alarms.slapos_check_software_instance_state.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkSoftwareInstanceState()

    self.assertEqual('Visited by Computer_checkSoftwareInstanceState',
      computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_Alarm_checkSoftwareInstanceState_no_public_computer(self):
    computer = self._makeComputer(self.new_id)
    
    self._simulateComputer_checkSoftwareInstanceState()

    try:
      self.portal.portal_alarms.slapos_check_software_instance_state.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkSoftwareInstanceState()

    self.assertNotEqual('Visited by Computer_checkSoftwareInstanceState',
      computer.workflow_history['edit_workflow'][-1]['comment'])
