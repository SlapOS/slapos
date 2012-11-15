# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.tests.utils import createZODBPythonScript

class TestSlapOSGarbageCollectDestroyedRootTreeAlarm(testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSGarbageCollectDestroyedRootTreeAlarm, self).afterSetUp()
    self._makeTree()

  def test_Instance_tryToGarbageCollect(self):
    self.hosting_subscription.archive()
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.requested_software_instance.Instance_tryToGarbageCollect()
    self.tic()
    self.assertEqual('destroy_requested',
        self.requested_software_instance.getSlapState())
    self.assertEqual('validated',
        self.requested_software_instance.getValidationState())

  def test_Instance_tryToGarbageCollect_not_destroy_requested(self):
    self.requested_software_instance.Instance_tryToGarbageCollect()
    self.tic()
    self.assertEqual('start_requested',
        self.requested_software_instance.getSlapState())
    self.assertEqual('validated',
        self.requested_software_instance.getValidationState())

  def test_Instance_tryToGarbageCollect_not_archived(self):
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.requested_software_instance.Instance_tryToGarbageCollect()
    self.tic()
    self.assertEqual('start_requested',
        self.requested_software_instance.getSlapState())
    self.assertEqual('validated',
        self.requested_software_instance.getValidationState())

  def test_Instance_tryToGarbageCollect_only_instance_destroy_requested(self):
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.tic()

    self.requested_software_instance.Instance_tryToGarbageCollect()
    self.tic()
    self.assertEqual('start_requested',
        self.requested_software_instance.getSlapState())
    self.assertEqual('validated',
        self.requested_software_instance.getValidationState())

  def _simulateInstance_tryToGarbageCollect(self):
    script_name = 'Instance_tryToGarbageCollect'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Instance_tryToGarbageCollect') """ )
    transaction.commit()

  def _dropInstance_tryToGarbageCollect(self):
    script_name = 'Instance_tryToGarbageCollect'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm(self):
    self.hosting_subscription.archive()
    self.tic()
    self._simulateInstance_tryToGarbageCollect()
    try:
      self.portal.portal_alarms.slapos_garbage_collect_destroyed_root_tree.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToGarbageCollect()
    self.assertEqual(
        'Visited by Instance_tryToGarbageCollect',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_invalidated(self):
    self.hosting_subscription.archive()
    self.software_instance.invalidate()
    self.tic()
    self._simulateInstance_tryToGarbageCollect()
    try:
      self.portal.portal_alarms.slapos_garbage_collect_destroyed_root_tree.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToGarbageCollect()
    self.assertNotEqual(
        'Visited by Instance_tryToGarbageCollect',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_archived(self):
    self.tic()
    self._simulateInstance_tryToGarbageCollect()
    try:
      self.portal.portal_alarms.slapos_garbage_collect_destroyed_root_tree.activeSense()
      self.tic()
    finally:
      self._dropInstance_tryToGarbageCollect()
    self.assertNotEqual(
        'Visited by Instance_tryToGarbageCollect',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

