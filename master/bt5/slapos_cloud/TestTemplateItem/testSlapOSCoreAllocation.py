# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.tests.utils import createZODBPythonScript

class TestSlapOSAllocation(testSlapOSMixin):

  def generateNewId(self):
    return self.getPortalObject().portal_ids.generateNewId(
        id_group=('slapos_core_test'))

  def generateNewSoftwareReleaseUrl(self):
    return 'http://example.org/test%s.cfg' % self.generateNewId()

  def generateNewSoftwareType(self):
    return 'Type%s' % self.generateNewId()

  def generateNewSoftwareTitle(self):
    return 'Title%s' % self.generateNewId()

  def generateSafeXml(self):
    return '<?xml version="1.0" encoding="utf-8"?><instance><parameter '\
      'id="param">%s</parameter></instance>' % self.generateNewId()

  def generateEmptyXml(self):
    return '<?xml version="1.0" encoding="utf-8"?><instance></instance>'

  def afterSetUp(self):
    super(TestSlapOSAllocation, self).afterSetUp()
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

    self.person_user.updateLocalRolesOnSecurityGroups()
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
    hosting_subscription.updateLocalRolesOnSecurityGroups()
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
    self.software_instance.updateLocalRolesOnSecurityGroups()
    self.tic()

    self.login()

  def beforeTearDown(self):
    pass

  def test_allocation_no_free_partition(self):
    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))

  def _makeComputer(self):
    self.computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    reference = 'TESTCOMP-%s' % self.generateNewId()
    self.computer.edit(
        allocation_scope='open/public',
        capacity_scope='open',
        reference=reference,
        title=reference
        )
    self.computer.validate()
    reference = 'TESTPART-%s' % self.generateNewId()
    self.partition = self.computer.newContent(portal_type='Computer Partition',
      reference=reference,
      title=reference
    )
    self.partition.markFree()
    self.partition.validate()
    self.tic()

  def _installSoftware(self, computer, url):
    software_installation = self.portal.software_installation_module\
        .template_software_installation.Base_createCloneDocument(batch_mode=1)
    software_installation.edit(url_string=url,
        reference='TESTSOFTINST-%s' % self.generateNewId(),
        aggregate=computer.getRelativeUrl())
    software_installation.validate()
    software_installation.requestStart()
    self.tic()

  def test_allocation_free_partition(self):
    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  def test_allocation_capacity_scope_close(self):
    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())
    self.computer.edit(capacity_scope='close')
    self.tic()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None,
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  def test_allocation_allocation_scope_close(self):
    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())
    self.computer.edit(allocation_scope='close')
    self.tic()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(None,
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  def test_allocation_allocation_scope_open_personal(self):
    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())
    self.computer.edit(allocation_scope='open/personal',
      source_administration=self.person_user.getRelativeUrl())
    self.tic()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  def test_allocation_allocation_scope_open_friend(self):
    self._makeComputer()
    self._installSoftware(self.computer,
        self.software_instance.getUrlString())
    # change computer owner
    new_id = self.generateNewId()
    person_user = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    person_user.updateLocalRolesOnSecurityGroups()
    person_user.validate()
    for assignment in person_user.contentValues(portal_type="Assignment"):
      assignment.open()

    self.computer.edit(
      source_administration=person_user.getRelativeUrl(),
      destination_section=self.person_user.getRelativeUrl(),
      allocation_scope='open/friend')
    self.tic()

    self.assertEqual(None, self.software_instance.getAggregateValue(
        portal_type='Computer Partition'))
    self.software_instance.SoftwareInstance_tryToAllocatePartition()
    self.assertEqual(self.partition.getRelativeUrl(),
        self.software_instance.getAggregate(portal_type='Computer Partition'))

  def _simulateSoftwareInstance_tryToAllocatePartition(self):
    script_name = 'SoftwareInstance_tryToAllocatePartition'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by SoftwareInstance_tryToAllocatePartition') """ )
    transaction.commit()

  def _dropSoftwareInstance_tryToAllocatePartition(self):
    script_name = 'SoftwareInstance_tryToAllocatePartition'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_unallocated(self):
    self._simulateSoftwareInstance_tryToAllocatePartition()
    try:
      self.portal.portal_alarms.slapos_allocate_instance.activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_tryToAllocatePartition()
    self.assertEqual(
        'Visited by SoftwareInstance_tryToAllocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_allocated(self):
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.tic()
    self._simulateSoftwareInstance_tryToAllocatePartition()
    try:
      self.portal.portal_alarms.slapos_allocate_instance.activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_tryToAllocatePartition()
    self.assertNotEqual(
        'Visited by SoftwareInstance_tryToAllocatePartition',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])
