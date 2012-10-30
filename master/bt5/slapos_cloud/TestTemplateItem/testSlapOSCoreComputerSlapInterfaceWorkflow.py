# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.Errors import UnsupportedWorkflowMethod

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
