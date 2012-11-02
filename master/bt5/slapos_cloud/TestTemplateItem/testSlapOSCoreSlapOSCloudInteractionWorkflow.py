# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from Products.ERP5Type.tests.utils import createZODBPythonScript
import transaction

class TestSlapOSCoreSlapOSCloudInteractionWorkflow(testSlapOSMixin):

  def _makePerson(self):
    new_id = self.generateNewId()
    self.person_user = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    self.person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    self.person_user.validate()
    for assignment in self.person_user.contentValues(portal_type="Assignment"):
      assignment.open()
    self.tic()

  def test_Computer_setSubjectList(self):
    self._makePerson()
    self.login(self.person_user.getReference())

    new_id = self.generateNewId()
    computer = self.portal.computer_module.newContent(
      portal_type='Computer',
      title="Computer %s for %s" % (new_id, self.person_user.getReference()),
      reference="TESTCOMP-%s" % new_id)
    self.tic()
    assert computer.getDestinationSectionValue() is None

    computer.edit(subject_list=[self.person_user.getDefaultEmailText()])
    self.tic()
    assert computer.getDestinationSection() == \
      self.person_user.getRelativeUrl()

  def check_Instance_validate(self, portal_type):
    self._makePerson()
    self.login(self.person_user.getReference())

    new_id = self.generateNewId()
    instance = self.portal.software_instance_module.newContent(
      portal_type=portal_type,
      title="Instance %s for %s" % (new_id, self.person_user.getReference()),
      reference="TESTINST-%s" % new_id)

    def verify_activeSense_call(self):
      if self.getRelativeUrl() == 'portal_alarms/slapos_allocate_instance':
        instance.portal_workflow.doActionFor(instance, action='edit_action', 
          comment='activeSense triggered')
      else:
        return self.activeSense_call()

    # Replace activeSense by a dummy method
    from Products.ERP5Type.Document.Alarm import Alarm
    Alarm.activeSense_call = Alarm.activeSense
    Alarm.activeSense = verify_activeSense_call
    try:
      instance.validate()
      # instance.portal_alarms.slapos_allocate_instance.activeSense()
      self.tic()
    finally:
      Alarm.activeSense = Alarm.activeSense_call
    self.assertEqual(
        'activeSense triggered',
        instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareInstance_validate(self):
    return self.check_Instance_validate("Software Instance")

  def test_SlaveInstance_validate(self):
    return self.check_Instance_validate("Slave Instance")

  def test_SlaveInstance_requestDestroy(self):
    self._makePerson()
    self.login(self.person_user.getReference())
    new_id = self.generateNewId()
    instance = self.portal.software_instance_module.newContent(
      portal_type='Slave Instance',
      title="Instance %s for %s" % (new_id, self.person_user.getReference()),
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      )
    request_kw = dict(
      software_release='http://example.org',
      software_type='http://example.org',
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=True,
    )
    instance.requestStop(**request_kw)
    self.assertEqual(instance.getValidationState(), 'draft')
    instance.validate()
    self.assertEqual(instance.getValidationState(), 'validated')
    instance.requestDestroy(**request_kw)
    self.assertEqual(instance.getValidationState(), 'invalidated')

  def check_SoftwareInstallation_changeState(self, method_id):
    self._makePerson()
    self.login(self.person_user.getReference())
    new_id = self.generateNewId()
    computer = self.portal.computer_module.newContent(
      portal_type='Computer',
      title="Computer %s for %s" % (new_id, self.person_user.getReference()),
      reference="TESTCOMP-%s" % new_id)
    installation = self.portal.software_installation_module.newContent(
      portal_type='Software Installation',
      title="Installation %s for %s" % (new_id, self.person_user.getReference()),
      aggregate_value=computer,
      )
    self.tic()

    def verify_reindexObject_call(self, *args, **kw):
      if self.getRelativeUrl() == computer.getRelativeUrl():
        computer.portal_workflow.doActionFor(computer, action='edit_action', 
          comment='reindexObject triggered on %s' % method_id)
      else:
        return self.reindexObject_call(*args, **kw)

    # Replace activeSense by a dummy method
    from Products.ERP5Type.Base import Base
    Base.reindexObject_call = Base.reindexObject
    Base.reindexObject = verify_reindexObject_call
    try:
      getattr(installation, method_id)()
      self.tic()
    finally:
      Base.reindexObject = Base.reindexObject_call
    self.assertEqual(
        'reindexObject triggered on %s' % method_id,
        computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareInstallation_changeState_onStart(self):
    return self.check_SoftwareInstallation_changeState('requestStart')

  def test_SoftwareInstallation_changeState_onDestroy(self):
    return self.check_SoftwareInstallation_changeState('requestDestroy')

  def check_SoftwareInstance_changeState(self, method_id):
    self._makePerson()
    self.login(self.person_user.getReference())

    new_id = self.generateNewId()
    computer = self.portal.computer_module.newContent(
      portal_type='Computer',
      title="Computer %s for %s" % (new_id, self.person_user.getReference()),
      reference="TESTCOMP-%s" % new_id)
    partition = computer.newContent(
      portal_type='Computer Partition',
      title="Partition Computer %s for %s" % (new_id,
        self.person_user.getReference()),
      reference="TESTPART-%s" % new_id)
    instance = self.portal.software_instance_module.newContent(
      portal_type="Software Instance",
      title="Instance %s for %s" % (new_id, self.person_user.getReference()),
      reference="TESTINST-%s" % new_id,
      aggregate_value=partition,
      destination_reference="TESTINST-%s" % new_id,
      ssl_certificate="foo",
      ssl_key="bar",
      )

    request_kw = dict(
      software_release='http://example.org',
      software_type='http://example.org',
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
    )
    if method_id == 'requestDestroy':
      instance.requestStop(**request_kw)
    self.tic()

    def verify_reindexObject_call(self, *args, **kw):
      if self.getRelativeUrl() == partition.getRelativeUrl():
        partition.portal_workflow.doActionFor(partition, action='edit_action', 
          comment='reindexObject triggered on %s' % method_id)
      else:
        return self.reindexObject_call(*args, **kw)

    # Replace activeSense by a dummy method
    from Products.ERP5Type.Base import Base
    Base.reindexObject_call = Base.reindexObject
    Base.reindexObject = verify_reindexObject_call
    try:
      getattr(instance, method_id)(**request_kw)
      self.tic()
    finally:
      Base.reindexObject = Base.reindexObject_call
    self.assertEqual(
        'reindexObject triggered on %s' % method_id,
        partition.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareInstance_changeState_onStart(self):
    return self.check_SoftwareInstance_changeState("requestStart")

  def test_SoftwareInstance_changeState_onStop(self):
    return self.check_SoftwareInstance_changeState("requestStop")

  def test_SoftwareInstance_changeState_onDestroy(self):
    return self.check_SoftwareInstance_changeState("requestDestroy")

  def check_change_instance_parameter(self, portal_type, method_id):
    self._makePerson()
    self.login(self.person_user.getReference())

    new_id = self.generateNewId()
    instance = self.portal.software_instance_module.newContent(
      portal_type=portal_type,
      title="Instance %s for %s" % (new_id, self.person_user.getReference()),
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      ssl_certificate="foo",
      ssl_key="bar",
      )

    self.tic()
    self.assertEqual(None,
      instance.workflow_history['instance_slap_interface_workflow'][-1]['action'])

    instance.edit(**{method_id: self.generateSafeXml()})
    self.tic()
    self.assertEqual('bang',
      instance.workflow_history['instance_slap_interface_workflow'][-1]['action'])

  def test_change_instance_parameter_onInstanceUrlString(self):
    return self.check_change_instance_parameter("Software Instance",
                                                'url_string')

  def test_change_instance_parameter_onInstanceTextContent(self):
    return self.check_change_instance_parameter("Software Instance",
                                                'text_content')

  def test_change_instance_parameter_onInstanceSourceReference(self):
    return self.check_change_instance_parameter("Software Instance",
                                                'source_reference')

  def test_change_instance_parameter_onInstanceSlaXML(self):
    return self.check_change_instance_parameter("Software Instance",
                                                'sla_xml')

  def test_change_instance_parameter_onSlaveUrlString(self):
    return self.check_change_instance_parameter("Slave Instance",
                                                'url_string')

  def test_change_instance_parameter_onSlaveTextContent(self):
    return self.check_change_instance_parameter("Slave Instance",
                                                'text_content')

  def test_change_instance_parameter_onSlaveSourceReference(self):
    return self.check_change_instance_parameter("Slave Instance",
                                                'source_reference')

  def test_change_instance_parameter_onSlaveSlaXML(self):
    return self.check_change_instance_parameter("Slave Instance",
                                                'sla_xml')

  def test_SoftwareInstance_setPredecessorList(self):
    portal_type = "Software Instance"

    self._makePerson()
    self.login(self.person_user.getReference())

    new_id = self.generateNewId()
    instance3 = self.portal.software_instance_module.newContent(
      portal_type=portal_type,
      title="Instance %s for %s" % (new_id, self.person_user.getReference()),
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      ssl_certificate="foo",
      ssl_key="bar",
      )

    new_id = self.generateNewId()
    instance2 = self.portal.software_instance_module.newContent(
      portal_type=portal_type,
      title="Instance %s for %s" % (new_id, self.person_user.getReference()),
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      ssl_certificate="foo",
      ssl_key="bar",
      predecessor_value=instance3,
      )

    new_id = self.generateNewId()
    instance1 = self.portal.software_instance_module.newContent(
      portal_type=portal_type,
      title="Instance %s for %s" % (new_id, self.person_user.getReference()),
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      ssl_certificate="foo",
      ssl_key="bar",
      predecessor_value=instance2,
      )

    self.tic()

    def verify_reindexObject_call(self, *args, **kw):
      if self.getRelativeUrl() in (instance2.getRelativeUrl(),
                                   instance3.getRelativeUrl()):
        self.portal_workflow.doActionFor(instance1, action='edit_action', 
          comment='reindexObject triggered')
      else:
        return self.reindexObject_call(*args, **kw)

    # Replace activeSense by a dummy method
    from Products.ERP5Type.Base import Base
    Base.reindexObject_call = Base.reindexObject
    Base.reindexObject = verify_reindexObject_call
    try:
      instance1.edit(predecessor_value=instance3)
      self.tic()
    finally:
      Base.reindexObject = Base.reindexObject_call
    self.assertEqual(
        'reindexObject triggered',
        instance1.workflow_history['edit_workflow'][-1]['comment'])
    self.assertEqual(
        'reindexObject triggered',
        instance1.workflow_history['edit_workflow'][-2]['comment'])
    self.assertEqual(
        None,
        instance1.workflow_history['edit_workflow'][-3]['comment'])
