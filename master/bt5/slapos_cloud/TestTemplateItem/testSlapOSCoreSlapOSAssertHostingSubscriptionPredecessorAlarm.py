# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.tests.utils import createZODBPythonScript

class TestSlapOSCoreSlapOSAssertHostingSubscriptionPredecessorAlarm(
    testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSCoreSlapOSAssertHostingSubscriptionPredecessorAlarm,
        self).afterSetUp()
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

    self.software_instance.edit(
        title=self.request_kw['software_title'],
        reference="TESTSI-%s" % new_id,
        url_string=self.request_kw['software_release'],
        source_reference=self.request_kw['software_type'],
        text_content=self.request_kw['instance_xml'],
        sla_xml=self.request_kw['sla_xml'],
        specialise=self.hosting_subscription.getRelativeUrl(),
    )
    self.portal.portal_workflow._jumpToStateFor(self.software_instance, 'start_requested')
    self.software_instance.validate()
    self.tic()

    self.login()

  def test_HostingSubscription_assertPredecessor(self):
    self.software_instance.rename(new_name=self.generateNewSoftwareTitle())
    self.tic()

    # check that no interaction has recreated the instance
    self.assertFalse(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

    self.hosting_subscription.HostingSubscription_assertPredecessor()
    self.assertTrue(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

  def test_HostingSubscription_assertPredecessor_stop_requested(self):
    self.software_instance.rename(new_name=self.generateNewSoftwareTitle())
    self.portal.portal_workflow._jumpToStateFor(self.hosting_subscription,
        'stop_requested')
    self.tic()

    # check that no interaction has recreated the instance
    self.assertFalse(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

    self.hosting_subscription.HostingSubscription_assertPredecessor()
    self.assertTrue(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

  def test_HostingSubscription_assertPredecessor_destroy_requested(self):
    self.software_instance.rename(new_name=self.generateNewSoftwareTitle())
    self.portal.portal_workflow._jumpToStateFor(self.hosting_subscription,
        'destroy_requested')
    self.tic()

    # check that no interaction has recreated the instance
    self.assertFalse(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

    self.hosting_subscription.HostingSubscription_assertPredecessor()
    self.assertFalse(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

  def test_HostingSubscription_assertPredecessor_invalidated(self):
    self.software_instance.rename(new_name=self.generateNewSoftwareTitle())
    self.hosting_subscription.invalidate()
    self.tic()

    # check that no interaction has recreated the instance
    self.assertFalse(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

    self.hosting_subscription.HostingSubscription_assertPredecessor()
    self.assertFalse(self.hosting_subscription.getTitle() in
        self.hosting_subscription.getPredecessorTitleList())

  def _simulateHostingSubscription_assertPredecessor(self):
    script_name = 'HostingSubscription_assertPredecessor'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by HostingSubscription_assertPredecessor') """ )
    transaction.commit()

  def _dropHostingSubscription_assertPredecessor(self):
    script_name = 'HostingSubscription_assertPredecessor'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_renamed(self):
    self.software_instance.edit(title=self.generateNewSoftwareTitle())
    self.tic()
    self._simulateHostingSubscription_assertPredecessor()
    try:
      self.portal.portal_alarms.slapos_assert_hosting_subscription_predecessor.activeSense()
      self.tic()
    finally:
      self._dropHostingSubscription_assertPredecessor()
    self.assertEqual(
        'Visited by HostingSubscription_assertPredecessor',
        self.hosting_subscription.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_renamed(self):
    self._simulateHostingSubscription_assertPredecessor()
    try:
      self.portal.portal_alarms.slapos_assert_hosting_subscription_predecessor.activeSense()
      self.tic()
    finally:
      self._dropHostingSubscription_assertPredecessor()
    self.assertNotEqual(
        'Visited by HostingSubscription_assertPredecessor',
        self.hosting_subscription.workflow_history['edit_workflow'][-1]['comment'])
