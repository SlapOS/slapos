# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.tests.utils import createZODBPythonScript

class TestSlapOSGarbageCollectDestroyedRootTreeAlarm(testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSGarbageCollectDestroyedRootTreeAlarm, self).afterSetUp()
    portal = self.getPortalObject()
    new_id = self.generateNewId()

    self.request_kw = dict(
        software_release=self.generateNewSoftwareReleaseUrl(),
        software_title=self.generateNewSoftwareTitle(),
        software_type=self.generateNewSoftwareType(),
        instance_xml=self.generateSafeXml(),
        sla_xml=self.generateEmptyXml(),
        shared=False,
        state="started"
    )

    # Clone person document
    self.person_user = portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    self.person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    self.person_user.validate()
    for assignment in self.person_user.contentValues(portal_type="Assignment"):
      assignment.open()
    transaction.commit()
    # prepare part of tree
    self.hosting_subscription = portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    self.software_instance = portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)

    self.hosting_subscription.edit(
        title=self.request_kw['software_title'],
        reference="TESTHS-%s" % new_id,
        url_string=self.request_kw['software_release'],
        source_reference=self.request_kw['software_type'],
        text_content=self.request_kw['instance_xml'],
        sla_xml=self.request_kw['sla_xml'],
        root_slave=self.request_kw['shared'],
        predecessor=self.software_instance.getRelativeUrl(),
        destination_section=self.person_user.getRelativeUrl()
    )
    self.hosting_subscription.validate()
    self.portal.portal_workflow._jumpToStateFor(self.hosting_subscription, 'start_requested')

    self.requested_software_instance = portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    self.software_instance.edit(
        title=self.request_kw['software_title'],
        reference="TESTSI-%s" % new_id,
        url_string=self.request_kw['software_release'],
        source_reference=self.request_kw['software_type'],
        text_content=self.request_kw['instance_xml'],
        sla_xml=self.request_kw['sla_xml'],
        specialise=self.hosting_subscription.getRelativeUrl(),
        predecessor=self.requested_software_instance.getRelativeUrl()
    )
    self.portal.portal_workflow._jumpToStateFor(self.software_instance, 'start_requested')
    self.software_instance.validate()

    self.requested_software_instance.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTSI-%s" % self.generateNewId(),
        url_string=self.request_kw['software_release'],
        source_reference=self.request_kw['software_type'],
        text_content=self.request_kw['instance_xml'],
        sla_xml=self.request_kw['sla_xml'],
        specialise=self.hosting_subscription.getRelativeUrl(),
    )
    self.portal.portal_workflow._jumpToStateFor(self.requested_software_instance, 'start_requested')
    self.requested_software_instance.validate()
    self.tic()

    self.login()

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

