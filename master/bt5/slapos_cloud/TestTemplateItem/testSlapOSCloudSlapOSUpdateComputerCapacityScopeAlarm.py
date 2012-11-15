# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.tests.utils import createZODBPythonScript
import json

class TestSlapOSGarbageCollectDestroyedRootTreeAlarm(testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSGarbageCollectDestroyedRootTreeAlarm, self).afterSetUp()
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
        'text': '#access ok'
    })
    transaction.commit()

  def test_Computer_checkAndUpdateCapacityScope(self):
    self.computer.Computer_checkAndUpdateCapacityScope()
    self.assertEqual('open', self.computer.getCapacityScope())

  def test_Computer_checkAndUpdateCapacityScope_no_capacity_quantity(self):
    self._makeTree()
    self.computer.edit(capacity_quantity=1)
    partition = self.computer.newContent(portal_type='Computer Partition',
        reference='part1')
    partition.markFree()
    partition.markBusy()
    partition.validate()
    self.software_instance.setAggregate(partition.getRelativeUrl())
    self.tic()

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
