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
    self._cancelTestSupportRequestList()

  def _cancelTestSupportRequestList(self):
    for support_request in self.portal.portal_catalog(
                        portal_type="Support Request",
                        title="Test Support Request %",
                        simulation_state="validated"):
      support_request.invalidate()
    for support_request in self.portal.portal_catalog(
                        portal_type="Support Request",
                        title="Allocation scope has been changed for TESTCOMPT%",
                        simulation_state="suspended"):
      support_request.invalidate()
    self.tic()
    
  def _updatePersonAssignment(self, person, role='role/member'):
    for assignment in person.contentValues(portal_type="Assignment"):
      assignment.cancel()
    assignment = person.newContent(portal_type='Assignment')
    assignment.setRole(role)
    assignment.setStartDate(DateTime())
    assignment.open()
    return assignment
  
  def _makePerson(self, new_id):
    # Clone computer document
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    person.edit(reference='TESTPERSON-%s' % (new_id, ))
    person.immediateReindexObject()
    return person

  def _makeComputer(self,new_id):
    # Clone computer document
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    computer = self.portal.computer_module\
      .template_computer.Base_createCloneDocument(batch_mode=1)
    computer.edit(
      title="computer ticket %s" % (new_id, ),
      reference="TESTCOMPT-%s" % (new_id, ),
      source_administration_value=person
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

  def _makeSoftwareRelease(self, new_id, software_release_url=None):
    software_release = self.portal.software_release_module\
      .template_software_release.Base_createCloneDocument(batch_mode=1)
    software_release.edit(
      url_string=software_release_url or self.generateNewSoftwareReleaseUrl(),
      reference='TESTSOFTRELS-%s' % new_id,
      title='Start requested for %s' % new_id
    )
    software_release.release()

    return software_release

  def _makeSoftwareInstallation(self, new_id, computer, software_release_url):
     software_installation = self.portal\
       .software_installation_module.template_software_installation\
       .Base_createCloneDocument(batch_mode=1)
     software_installation.edit(
       url_string=software_release_url,
       aggregate=computer.getRelativeUrl(),
       reference='TESTSOFTINSTS-%s' % new_id,
       title='Start requested for %s' % computer.getUid()
     )
     software_installation.validate()
     software_installation.requestStart()

     return software_installation

  def _makeHostingSubscription(self, new_id):
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    hosting_subscription = self.portal\
      .hosting_subscription_module.template_hosting_subscription\
      .Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    hosting_subscription.edit(
        title= "Test hosting sub ticket %s" % new_id,
        reference="TESTHST-%s" % new_id,
        destination_section_value=person
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

  def test_computer_Base_generateSupportRequestForSlapOS(self):
    self._dropBase_generateSupportRequestForSlapOS()
    title = "Test Support Request %s" % self.new_id
    computer = self._makeComputer(self.new_id)
    support_request = computer.Base_generateSupportRequestForSlapOS(
      title, title, computer.getRelativeUrl()
    )
    self.tic()

    self.assertNotEqual(support_request, None)

    support_request = self.portal.restrictedTraverse(support_request)

    # The support request is added to computer owner.
    self.assertEquals(support_request.getDestinationDecision(),
                      computer.getSourceAdministration())

  def test_software_instance_Base_generateSupportRequestForSlapOS(self):
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub,self.generateNewSoftwareReleaseUrl())
    instance = host_sub.getPredecessorValue()

    title = "Test Support Request %s" % self.new_id
    support_request = instance.Base_generateSupportRequestForSlapOS(
      title, title, instance.getRelativeUrl()
    )
    self.tic()

    self.assertNotEqual(support_request, None)

    support_request = self.portal.restrictedTraverse(support_request)
 
    # The support request is added to computer owner.
    self.assertEquals(support_request.getDestinationDecision(),
                      host_sub.getDestinationSection())

  def test_Base_generateSupportRequestForSlapOS_do_not_recreate_if_open(self):
    title = "Test Support Request %s" % self.new_id
    computer = self._makeComputer(self.new_id)
    computer.Base_generateSupportRequestForSlapOS(
      title, title, computer.getRelativeUrl()
    )
    self.tic()

    support_request = computer.Base_generateSupportRequestForSlapOS(
      title, title, computer.getRelativeUrl()
    )
    self.tic()

    self.assertEqual(support_request, None)

  def test_ERP5Site_isSupportRequestCreationClosed(self):
    
    person = self._makePerson(self.new_id)
    other_person = self._makePerson('other-%s' % self.new_id)
    url = person.getRelativeUrl()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed())

    def newSupportRequest():
      sr = self.portal.support_request_module.newContent(\
                        title="Test Support Request POIUY",
                        destination_decision=url)
      sr.validate()
      sr.immediateReindexObject()

    newSupportRequest()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    newSupportRequest()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    newSupportRequest()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    newSupportRequest()
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    newSupportRequest()
    self.assertTrue(self.portal.ERP5Site_isSupportRequestCreationClosed(url))
    
    self.assertTrue(self.portal.ERP5Site_isSupportRequestCreationClosed())
    
    self.assertFalse(self.portal.ERP5Site_isSupportRequestCreationClosed(
                     other_person.getRelativeUrl()))

  def test_Base_generateSupportRequestForSlapOS_recreate_if_closed(self):
    title = "Test Support Request %s" % self.new_id
    computer = self._makeComputer(self.new_id)
    support_request = computer.Base_generateSupportRequestForSlapOS(
      title, title, computer.getRelativeUrl()
    )
    self.tic()

    self.portal.restrictedTraverse(support_request).invalidate()
    self.tic()

    support_request = computer.Base_generateSupportRequestForSlapOS(
      title, title, computer.getRelativeUrl()
    )
    self.tic()

    self.assertNotEqual(support_request,None)

  def _simulateBase_generateSupportRequestForSlapOS(self):
    script_name = 'Base_generateSupportRequestForSlapOS'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""return 'Visited Base_generateSupportRequestForSlapOS'""")
    transaction.commit()

  def _dropBase_generateSupportRequestForSlapOS(self):
    script_name = 'Base_generateSupportRequestForSlapOS'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()
    self.assertFalse(script_name in self.portal.portal_skins.custom.objectIds())

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
      result = computer.Computer_checkState()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()

    self.assertEqual('Visited Base_generateSupportRequestForSlapOS',
      result)

  def test_Computer_checkState_empty_cache(self):
    computer = self._makeComputer(self.new_id)

    self._simulateBase_generateSupportRequestForSlapOS()

    try:
      result = computer.Computer_checkState()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertEqual('Visited Base_generateSupportRequestForSlapOS',
      result)

  def test_SoftwareInstance_checkState_error_new_instance(self):
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub,self.generateNewSoftwareReleaseUrl())
    instance = host_sub.getPredecessorValue()
    
    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

    memcached_dict[instance.getReference()] = json.dumps(
        {"created_at":"%s" % DateTime(), "text":"#error "}
    )

    self._simulateBase_generateSupportRequestForSlapOS()

    try:
      result = instance.SoftwareInstance_checkState()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertNotEqual('Visited Base_generateSupportRequestForSlapOS',
      result)

  def test_SoftwareInstance_checkState_error_out_time(self):
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub,self.generateNewSoftwareReleaseUrl())
    instance = host_sub.getPredecessorValue()
    
    instance.workflow_history['edit_workflow'] = [{
           'comment':'edit',
           'error_message': '',
           'actor': 'ERP5TypeTestCase',
           'state': 'current',
           'time': DateTime('2012/11/30 11:11'),
           'action': 'edit'
       }]

    memcached_dict = self.portal.portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

    memcached_dict[instance.getReference()] = json.dumps(
        {"created_at":"%s" % DateTime(), "text":"#error "}
    )

    self._simulateBase_generateSupportRequestForSlapOS()

    try:
      result = instance.SoftwareInstance_checkState()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertEqual('Visited Base_generateSupportRequestForSlapOS',
      result)

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
      result = instance.SoftwareInstance_checkState()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertNotEqual('Visited Base_generateSupportRequestForSlapOS',
      result)

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
      result = instance.SoftwareInstance_checkState()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertNotEqual('Visited Base_generateSupportRequestForSlapOS',
      result)

  def test_SoftwareInstance_checkState_empty_cache(self):
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub,self.generateNewSoftwareReleaseUrl())
    instance = host_sub.getPredecessorValue()
    
    self._simulateBase_generateSupportRequestForSlapOS()

    try:
      result = instance.SoftwareInstance_checkState()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertNotEqual('Visited Base_generateSupportRequestForSlapOS',
      result)

  def test_SoftwareRelease_testForAllocation(self):
    software_release = self._makeSoftwareRelease(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(allocation_scope = 'open/public', capacity_scope = 'open')
    self._makeComputerPartitions(computer)
    self._makeSoftwareInstallation(
      self.new_id, computer, software_release.getUrlString()
    )

    self.tic()

    self._simulateBase_generateSupportRequestForSlapOS()
    try:
      result = software_release.SoftwareRelease_testForAllocation()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertNotEqual('Visited Base_generateSupportRequestForSlapOS',
      result)

  def test_SoftwareRelease_testForAllocation_no_public_computer(self):
    software_release = self._makeSoftwareRelease(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(capacity_scope = 'open')
    self._makeComputerPartitions(computer)
    self._makeSoftwareInstallation(
      self.new_id, computer, software_release.getUrlString()
    )

    self.tic()

    self._simulateBase_generateSupportRequestForSlapOS()
    try:
      result = software_release.SoftwareRelease_testForAllocation()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertEqual('Visited Base_generateSupportRequestForSlapOS',
      result)

  def test_SoftwareRelease_testForAllocation_no_open_computer(self):
    software_release = self._makeSoftwareRelease(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(allocation_scope = 'open/public')
    self._makeComputerPartitions(computer)
    self._makeSoftwareInstallation(
      self.new_id, computer, software_release.getUrlString()
    )

    self.tic()

    self._simulateBase_generateSupportRequestForSlapOS()
    try:
      result = software_release.SoftwareRelease_testForAllocation()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertEqual('Visited Base_generateSupportRequestForSlapOS',
      result)

  def test_SoftwareRelease_testForAllocation_no_free_partitions(self):
    software_release = self._makeSoftwareRelease(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(allocation_scope = 'open/public', capacity_scope = 'open')
    self._makeComputerPartitions(computer)

    computer.partition1.markBusy()
    computer.partition2.markBusy()
    computer.partition3.markBusy()
    computer.partition4.markBusy()

    self._makeSoftwareInstallation(
      self.new_id, computer, software_release.getUrlString()
    )

    self.tic()

    self._simulateBase_generateSupportRequestForSlapOS()
    try:
      result = software_release.SoftwareRelease_testForAllocation()
    finally:
      self._dropBase_generateSupportRequestForSlapOS()
    
    self.assertEqual('Visited Base_generateSupportRequestForSlapOS',
      result)

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

  def _simulateSoftwareRelease_testForAllocation(self):
    script_name = 'SoftwareRelease_testForAllocation'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by SoftwareRelease_testForAllocation') """ )
    transaction.commit()

  def _dropSoftwareRelease_testForAllocation(self):
    script_name = 'SoftwareRelease_testForAllocation'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_Alarm_checkCloudIsFull(self):
    software_release_preference = self.portal.portal_preferences.getPreferredSoftwareReleaseToTestForSpace()

    if software_release_preference != '':
      software_release_list = software_release_preference.split("\n")

      software_release = self._makeSoftwareRelease(
        self.new_id, software_release_list[0])
    
      self._simulateSoftwareRelease_testForAllocation()

      try:
        self.portal.portal_alarms.slapos_check_cloud_is_full.activeSense()
        self.tic()
      finally:
        self._dropSoftwareRelease_testForAllocation()

      self.assertEqual('Visited by SoftwareRelease_testForAllocation',
        software_release.workflow_history['edit_workflow'][-1]['comment'])
        
  def _simulateComputer_checkAndUpdateAllocationScope(self):
    script_name = 'Computer_checkAndUpdateAllocationScope'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Computer_checkAndUpdateAllocationScope') """ )
    transaction.commit()
    
  def _dropComputer_checkAndUpdateAllocationScope(self):
    script_name = 'Computer_checkAndUpdateAllocationScope'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()
  
  def test_Alarm_notAllowedAllocationScope_OpenPublic(self):
    computer = self._makeComputer(self.new_id)
    computer.edit(allocation_scope = 'open/public')
    
    self._simulateComputer_checkAndUpdateAllocationScope()

    try:
      self.portal.portal_alarms.slapos_crm_check_update_allocation_scope.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkAndUpdateAllocationScope()

    self.assertEqual('Visited by Computer_checkAndUpdateAllocationScope',
      computer.workflow_history['edit_workflow'][-1]['comment'])
  
  def test_Alarm_notAllowedAllocationScope_OpenFriend(self):
    computer = self._makeComputer(self.new_id)
    computer.edit(allocation_scope = 'open/friend')
    
    self._simulateComputer_checkAndUpdateAllocationScope()

    try:
      self.portal.portal_alarms.slapos_crm_check_update_allocation_scope.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkAndUpdateAllocationScope()

    self.assertEqual('Visited by Computer_checkAndUpdateAllocationScope',
      computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_Alarm_notAllowedAllocationScope_OpenPersonal(self):
    computer = self._makeComputer(self.new_id)
    computer.edit(allocation_scope = 'open/personal')
    
    self._simulateComputer_checkAndUpdateAllocationScope()

    try:
      self.portal.portal_alarms.slapos_crm_check_update_allocation_scope.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkAndUpdateAllocationScope()

    self.assertNotEqual('Visited by Computer_checkAndUpdateAllocationScope',
      computer.workflow_history['edit_workflow'][-1]['comment'])
  
  def _simulateHostingSubscription_checkSofwareInstanceState(self):
    script_name = 'HostingSubscription_checkSofwareInstanceState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by HostingSubscription_checkSofwareInstanceState') """ )
    transaction.commit()
  
  def _dropHostingSubscription_checkSofwareInstanceState(self):
    script_name = 'HostingSubscription_checkSofwareInstanceState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()
  
  def test_Alarm_findAndNofitiyUnallocatedSoftwareInstance(self):
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub, self.generateNewSoftwareReleaseUrl())
    instance = host_sub.getPredecessorValue()
    self.assertEqual(instance.getAggregate(""), "")
    
    self._simulateHostingSubscription_checkSofwareInstanceState()

    try:
      self.portal.portal_alarms.slapos_crm_check_partially_allocated_instance.activeSense()
      self.tic()
    finally:
      self._dropHostingSubscription_checkSofwareInstanceState()

    self.assertEqual('Visited by HostingSubscription_checkSofwareInstanceState',
      host_sub.workflow_history['edit_workflow'][-1]['comment'])
    