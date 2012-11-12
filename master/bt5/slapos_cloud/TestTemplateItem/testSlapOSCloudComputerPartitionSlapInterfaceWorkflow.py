# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin

class TestSlapOSCoreComputerPartitionSlapInterfaceWorkflow(testSlapOSMixin):
  def afterSetUp(self):
    super(TestSlapOSCoreComputerPartitionSlapInterfaceWorkflow, self).afterSetUp()
    # Clone computer document
    self.computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    new_id = self.generateNewId()
    self.computer.edit(
      title="computer %s" % (new_id, ),
      reference="TESTCOMP-%s" % (new_id, ),
      allocation_scope='open/personal',
      capacity_scope='open',
    )
    self.computer.validate()

    # install an software release
    self.software_installation = self.portal.software_installation_module\
        .newContent(portal_type='Software Installation',
        url_string=self.generateNewSoftwareReleaseUrl(),
        aggregate=self.computer.getRelativeUrl())
    self.software_installation.validate()
    self.software_installation.requestStart()

    self.tic()

  def test_markFree(self):
    self.login(self.computer.getReference())
    partition = self.computer.newContent(portal_type='Computer Partition',
        reference='PART-%s' % self.generateNewId())
    partition.validate()
    partition.markFree()
    self.tic()
    self.assertEqual(1, self.portal.portal_catalog.countResults(
        parent_uid=self.computer.getUid(), free_for_request=1)[0][0])

  def test_markFree_markBusy(self):
    self.login(self.computer.getReference())
    partition = self.computer.newContent(portal_type='Computer Partition',
        reference='PART-%s' % self.generateNewId())
    partition.validate()
    partition.markFree()
    self.tic()
    self.assertEqual(1, self.portal.portal_catalog.countResults(
        parent_uid=self.computer.getUid(), free_for_request=1)[0][0])
    partition.markBusy()
    self.tic()
    self.assertEqual(0, self.portal.portal_catalog.countResults(
        parent_uid=self.computer.getUid(), free_for_request=1)[0][0])

  def test_markFree_markBusy_markFree(self):
    self.login(self.computer.getReference())
    partition = self.computer.newContent(portal_type='Computer Partition',
        reference='PART-%s' % self.generateNewId())
    partition.validate()
    partition.markFree()
    self.tic()
    self.assertEqual(1, self.portal.portal_catalog.countResults(
        parent_uid=self.computer.getUid(), free_for_request=1)[0][0])
    partition.markBusy()
    self.tic()
    self.assertEqual(0, self.portal.portal_catalog.countResults(
        parent_uid=self.computer.getUid(), free_for_request=1)[0][0])
    partition.markFree()
    self.tic()
    self.assertEqual(1, self.portal.portal_catalog.countResults(
        parent_uid=self.computer.getUid(), free_for_request=1)[0][0])

  def test_markInactive(self):
    self.login(self.computer.getReference())
    partition = self.computer.newContent(portal_type='Computer Partition',
        reference='PART-%s' % self.generateNewId())
    partition.validate()
    partition.markInactive()
    self.tic()
    self.assertEqual(0, self.portal.portal_catalog.countResults(
        parent_uid=self.computer.getUid(), free_for_request=1)[0][0])

  def test_markInactive_markFree(self):
    self.login(self.computer.getReference())
    partition = self.computer.newContent(portal_type='Computer Partition',
        reference='PART-%s' % self.generateNewId())
    partition.validate()
    partition.markInactive()
    self.tic()
    self.assertEqual(0, self.portal.portal_catalog.countResults(
        parent_uid=self.computer.getUid(), free_for_request=1)[0][0])
    partition.markFree()
    self.tic()
    self.assertEqual(1, self.portal.portal_catalog.countResults(
        parent_uid=self.computer.getUid(), free_for_request=1)[0][0])
