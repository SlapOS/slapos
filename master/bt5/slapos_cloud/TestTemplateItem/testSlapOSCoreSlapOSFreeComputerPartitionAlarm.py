# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.tests.utils import createZODBPythonScript

class TestSlapOSFreeComputerPartitionAlarm(testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSFreeComputerPartitionAlarm, self).afterSetUp()
    self._makeTree()
    self.login()

  def test_Instance_tryToUnallocatePartition(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.software_instance.Instance_tryToUnallocatePartition()
    self.tic()
    self.assertEqual(None, self.software_instance.getAggregate())
    self.assertEqual('free', self.partition.getSlapState())

  def test_Instance_tryToUnallocatePartition_concurrency(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.partition.activate(tag="allocate_%s" % self.partition.getRelativeUrl()\
        ).getId()
    transaction.commit()
    self.software_instance.Instance_tryToUnallocatePartition()
    self.tic()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate())
    self.assertEqual('busy', self.partition.getSlapState())

  def test_Instance_tryToUnallocatePartition_twoInstances(self):
    software_instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)

    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.software_instance.Instance_tryToUnallocatePartition()
    self.tic()
    self.assertEqual(None, self.software_instance.getAggregate())
    self.assertEqual('busy', self.partition.getSlapState())
    self.assertEqual(self.partition.getRelativeUrl(), software_instance.getAggregate())

  def _simulateInstance_tryToUnallocatePartition(self):
    script_name = 'Instance_tryToUnallocatePartition'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Instance_tryToUnallocatePartition') """ )
    transaction.commit()

  def _dropInstance_tryToUnallocatePartition(self):
    script_name = 'Instance_tryToUnallocatePartition'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_allocated(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.software_instance.invalidate()
    self.tic()
    self._simulateInstance_tryToUnallocatePartition()
    try:
      self.portal.portal_alarms.slapos_free_computer_partition.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToUnallocatePartition()
    self.assertEqual(
        'Visited by Instance_tryToUnallocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_unallocated(self):
    self._makeComputer()
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.software_instance.invalidate()
    self.tic()
    self._simulateInstance_tryToUnallocatePartition()
    try:
      self.portal.portal_alarms.slapos_free_computer_partition.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToUnallocatePartition()
    self.assertNotEqual(
        'Visited by Instance_tryToUnallocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_validated(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()
    self._simulateInstance_tryToUnallocatePartition()
    try:
      self.portal.portal_alarms.slapos_free_computer_partition.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToUnallocatePartition()
    self.assertNotEqual(
        'Visited by Instance_tryToUnallocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_start_requested(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.tic()
    self._simulateInstance_tryToUnallocatePartition()
    try:
      self.portal.portal_alarms.slapos_free_computer_partition.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToUnallocatePartition()
    self.assertNotEqual(
        'Visited by Instance_tryToUnallocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSFreeComputerPartitionAlarmWithSlave(testSlapOSMixin):
  def afterSetUp(self):
    super(TestSlapOSFreeComputerPartitionAlarmWithSlave, self).afterSetUp()
    self._makeTree(requested_template_id='template_slave_instance')
    self.login()

  def test_Instance_tryToUnallocatePartition(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.software_instance.Instance_tryToUnallocatePartition()
    self.tic()
    self.assertEqual(None, self.software_instance.getAggregate())
    self.assertEqual('free', self.partition.getSlapState())

  def test_Instance_tryToUnallocatePartition_nonDestroyed(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.partition.markBusy()
    self.tic()

    self.software_instance.Instance_tryToUnallocatePartition()
    self.tic()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate())
    self.assertEqual('busy', self.partition.getSlapState())

