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
    self._makeTree()
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

  def test_HostingSubscription_assertPredecessor_archived(self):
    self.software_instance.rename(new_name=self.generateNewSoftwareTitle())
    self.hosting_subscription.archive()
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
