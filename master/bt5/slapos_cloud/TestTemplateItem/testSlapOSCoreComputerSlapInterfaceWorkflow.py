# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin

class TestSlapOSCoreComputerSlapInterfaceWorkflow(testSlapOSMixin):
  def afterSetUp(self):
    super(TestSlapOSCoreComputerSlapInterfaceWorkflow, self).afterSetUp()
    # Clone computer document
    self.computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    new_id = self.generateNewId()
    self.computer.edit(
      title="computer %s" % (new_id, ),
      reference="TESTCOMP-%s" % (new_id, )
    )
    self.computer.validate()
    self.tic()

  def beforeTearDown(self):
    super(TestSlapOSCoreComputerSlapInterfaceWorkflow, self).beforeTearDown()
    self.portal.REQUEST['computer_key'] = None
    self.portal.REQUEST['computer_certificate'] = None

  def test_generateCertificate(self):
    self.login(self.computer.getReference())
    self.computer.generateCertificate()
    computer_key = self.portal.REQUEST.get('computer_key')
    computer_certificate = self.portal.REQUEST.get('computer_certificate')
    self.assertNotEqual(None, computer_key)
    self.assertNotEqual(None, computer_certificate)
    self.assertTrue(self.computer.getReference() in computer_certificate)

  def test_generateCertificate_twice(self):
    self.login(self.computer.getReference())
    self.computer.generateCertificate()
    computer_key = self.portal.REQUEST.get('computer_key')
    computer_certificate = self.portal.REQUEST.get('computer_certificate')
    self.assertNotEqual(None, computer_key)
    self.assertNotEqual(None, computer_certificate)
    self.assertTrue(self.computer.getReference() in computer_certificate)

    self.assertRaises(ValueError, self.computer.generateCertificate)
    self.assertEqual(None, self.portal.REQUEST.get('computer_key'))
    self.assertEqual(None, self.portal.REQUEST.get('computer_certificate'))

  def test_approveComputerRegistration(self):
    # Clone person document
    new_id = self.generateNewId()
    person_user = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    person_user.validate()
    for assignment in person_user.contentValues(portal_type="Assignment"):
      assignment.open()
    self.tic()
    self.login(person_user.getReference())
    computer = self.portal.computer_module.newContent(portal_type='Computer',
      title="Computer %s for %s" % (new_id, person_user.getReference()),
      reference="TESTCOMP-%s" % new_id)
    computer.requestComputerRegistration()
    computer.approveComputerRegistration()
    self.assertEqual('open/personal', computer.getAllocationScope())
    self.assertEqual(person_user.getRelativeUrl(),
        computer.getSourceAdministration())
    self.assertEqual('validated', computer.getValidationState())

  def _countInstanceBang(self, instance, comment):
    return len([q for q in instance.workflow_history[
        'instance_slap_interface_workflow'] if q['action'] == 'bang' and \
            q['comment'] == comment])

  def _countComputereBang(self, computer, comment):
    return len([q for q in computer.workflow_history[
        'computer_slap_interface_workflow'] if q['action'] == \
            'report_computer_bang' and q['comment'] == comment])

  def test_reportComputerBang(self):
    self._makeComplexComputer()
    self.login(self.computer.getReference())
    comment = 'Bang from computer'
    started_instance = self.computer.partition1.getAggregateRelatedValue(
        portal_type='Software Instance')
    stopped_instance = self.computer.partition2.getAggregateRelatedValue(
        portal_type='Software Instance')
    destroyed_instance1 = self.computer.partition3.getAggregateRelatedValue(
        portal_type='Software Instance')
    destroyed_instance2 = self.computer.partition4.getAggregateRelatedValue(
        portal_type='Software Instance')

    # test sanity check -- do not trust _makeComplexComputer
    self.assertEqual('start_requested', started_instance.getSlapState())
    self.assertEqual('stop_requested', stopped_instance.getSlapState())
    self.assertEqual('destroy_requested', destroyed_instance1.getSlapState())
    self.assertEqual('destroy_requested', destroyed_instance2.getSlapState())

    # store counts before bang
    computer_bang_count = self._countComputereBang(self.computer, comment)
    started_instance_bang_count = self._countInstanceBang(started_instance,
        comment)
    stopped_instance_bang_count = self._countInstanceBang(stopped_instance,
        comment)
    destroyed_instance1_bang_count = self._countInstanceBang(
        destroyed_instance1, comment)
    destroyed_instance2_bang_count = self._countInstanceBang(
        destroyed_instance2, comment)

    self.computer.reportComputerBang(comment=comment)
    self.tic()

    self.assertEqual(1+computer_bang_count,
        self._countComputereBang(self.computer, comment))
    self.assertEqual(1+started_instance_bang_count,
        self._countInstanceBang(started_instance, comment))
    self.assertEqual(1+stopped_instance_bang_count,
        self._countInstanceBang(stopped_instance, comment))
    self.assertEqual(destroyed_instance1_bang_count,
        self._countInstanceBang(destroyed_instance1, comment))
    self.assertEqual(destroyed_instance2_bang_count,
        self._countInstanceBang(destroyed_instance2, comment))
