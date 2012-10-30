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
    self.computer.generateCertificate()
    computer_key = self.portal.REQUEST.get('computer_key')
    computer_certificate = self.portal.REQUEST.get('computer_certificate')
    self.assertNotEqual(None, computer_key)
    self.assertNotEqual(None, computer_certificate)
    self.assertTrue(self.computer.getReference() in computer_certificate)

  def test_generateCertificate_twice(self):
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
