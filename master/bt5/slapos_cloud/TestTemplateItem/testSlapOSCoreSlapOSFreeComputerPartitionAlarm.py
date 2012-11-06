# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.tests.utils import createZODBPythonScript

class TestSlapOSFreeComputerPartitionAlarm(testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSFreeComputerPartitionAlarm, self).afterSetUp()
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
    hosting_subscription = portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    self.software_instance = portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)

    hosting_subscription.edit(
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
    hosting_subscription.validate()
    self.portal.portal_workflow._jumpToStateFor(hosting_subscription, 'start_requested')

    self.software_instance.edit(
        title=self.request_kw['software_title'],
        reference="TESTSI-%s" % new_id,
        url_string=self.request_kw['software_release'],
        source_reference=self.request_kw['software_type'],
        text_content=self.request_kw['instance_xml'],
        sla_xml=self.request_kw['sla_xml'],
        specialise=hosting_subscription.getRelativeUrl(),
    )
    self.portal.portal_workflow._jumpToStateFor(self.software_instance, 'start_requested')
    self.software_instance.validate()
    self.tic()

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

