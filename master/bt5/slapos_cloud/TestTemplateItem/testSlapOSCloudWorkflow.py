# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.tests.backportUnittest import expectedFailure
from Products.ERP5Type.Errors import UnsupportedWorkflowMethod
from Products.DCWorkflow.DCWorkflow import ValidationFailed
from AccessControl.SecurityManagement import getSecurityManager, \
             setSecurityManager

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
    self.assertNotEqual(None, self.computer.getDestinationReference())
    serial = '0x%x' % int(self.computer.getDestinationReference(), 16)
    self.assertTrue(serial in computer_certificate)
    self.assertTrue(self.computer.getReference() in computer_certificate.decode('string_escape'))

  def test_generateCertificate_twice(self):
    self.login(self.computer.getReference())
    self.computer.generateCertificate()
    computer_key = self.portal.REQUEST.get('computer_key')
    computer_certificate = self.portal.REQUEST.get('computer_certificate')
    self.assertNotEqual(None, computer_key)
    self.assertNotEqual(None, computer_certificate)
    self.assertNotEqual(None, self.computer.getDestinationReference())
    serial = '0x%x' % int(self.computer.getDestinationReference(), 16)
    self.assertTrue(serial in computer_certificate)
    self.assertTrue(self.computer.getReference() in computer_certificate.decode('string_escape'))

    self.assertRaises(ValueError, self.computer.generateCertificate)
    self.assertEqual(None, self.portal.REQUEST.get('computer_key'))
    self.assertEqual(None, self.portal.REQUEST.get('computer_certificate'))

  def test_approveComputerRegistration(self):
    self._makePerson()
    self.login(self.person_user.getReference())
    new_id = self.generateNewId()
    computer = self.portal.computer_module.newContent(portal_type='Computer',
      title="Computer %s for %s" % (new_id, self.person_user.getReference()),
      reference="TESTCOMP-%s" % new_id)
    computer.requestComputerRegistration()
    computer.approveComputerRegistration()
    self.assertEqual('open/personal', computer.getAllocationScope())
    self.assertEqual(self.person_user.getRelativeUrl(),
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

  def test_requestSoftwareRelease_software_release_url_required(self):
    self._makePerson()
    self.computer.edit(source_administration=self.person_user.getRelativeUrl())
    self.tic()
    self.login(self.person_user.getReference())
    self.assertRaises(TypeError, self.computer.requestSoftwareRelease,
        state='available')
    transaction.abort()

  def test_requestSoftwareRelease_state_required(self):
    self._makePerson()
    self.computer.edit(source_administration=self.person_user.getRelativeUrl())
    self.tic()
    self.login(self.person_user.getReference())
    url = self.generateNewSoftwareReleaseUrl()
    self.assertRaises(TypeError, self.computer.requestSoftwareRelease,
        software_release_url=url)
    transaction.abort()

  def test_requestSoftwareRelease_available(self):
    self._makePerson()
    self.computer.edit(source_administration=self.person_user.getRelativeUrl())
    self.tic()
    self.login(self.person_user.getReference())
    url = self.generateNewSoftwareReleaseUrl()
    self.computer.requestSoftwareRelease(software_release_url=url,
        state='available')
    self.tic()
    self.login()
    software_installation = self.computer.getAggregateRelatedValue(
        portal_type='Software Installation')
    self.assertEqual('start_requested', software_installation.getSlapState())
    self.assertEqual(url, software_installation.getUrlString())
    self.assertEqual('validated', software_installation.getValidationState())

  def test_requestSoftwareRelease_destroyed(self):
    self._makePerson()
    self.computer.edit(source_administration=self.person_user.getRelativeUrl())
    self.tic()
    self.login(self.person_user.getReference())
    url = self.generateNewSoftwareReleaseUrl()
    self.computer.requestSoftwareRelease(software_release_url=url,
        state='destroyed')
    self.tic()
    self.login()
    software_installation = self.computer.getAggregateRelatedValue(
        portal_type='Software Installation')
    self.assertEqual(None, software_installation)

  def test_requestSoftwareRelease_available_destroyed(self):
    self._makePerson()
    self.computer.edit(source_administration=self.person_user.getRelativeUrl())
    self.tic()
    self.login(self.person_user.getReference())
    url = self.generateNewSoftwareReleaseUrl()
    self.computer.requestSoftwareRelease(software_release_url=url,
        state='available')
    self.tic()
    self.login()
    software_installation = self.computer.getAggregateRelatedValue(
        portal_type='Software Installation')
    self.assertEqual('start_requested', software_installation.getSlapState())
    self.assertEqual(url, software_installation.getUrlString())
    self.assertEqual('validated', software_installation.getValidationState())

    self.login(self.person_user.getReference())
    self.computer.requestSoftwareRelease(software_release_url=url,
        state='destroyed')

    self.tic()
    self.login()
    software_installation = self.computer.getAggregateRelatedValue(
        portal_type='Software Installation')
    self.assertEqual('destroy_requested', software_installation.getSlapState())
    self.assertEqual(url, software_installation.getUrlString())
    self.assertEqual('validated', software_installation.getValidationState())

  def test_requestSoftwareRelease_not_indexed(self):
    self._makePerson()
    self.computer.edit(source_administration=self.person_user.getRelativeUrl())
    self.tic()
    self.login(self.person_user.getReference())
    url = self.generateNewSoftwareReleaseUrl()
    self.computer.requestSoftwareRelease(software_release_url=url,
        state='available')
    transaction.commit()
    self.assertRaises(NotImplementedError,
        self.computer.requestSoftwareRelease, software_release_url=url,
        state='available')
    transaction.abort()

  @expectedFailure
  def test_requestSoftwareRelease_same_transaction(self):
    self._makePerson()
    self.computer.edit(source_administration=self.person_user.getRelativeUrl())
    self.tic()
    self.login(self.person_user.getReference())
    url = self.generateNewSoftwareReleaseUrl()
    self.computer.requestSoftwareRelease(software_release_url=url,
        state='available')
    self.assertRaises(NotImplementedError,
        self.computer.requestSoftwareRelease, software_release_url=url,
        state='available')
    transaction.abort()

  def test_revokeCertificate(self):
    self.login(self.computer.getReference())
    self.computer.generateCertificate()
    computer_key = self.portal.REQUEST.get('computer_key')
    computer_certificate = self.portal.REQUEST.get('computer_certificate')
    self.assertNotEqual(None, computer_key)
    self.assertNotEqual(None, computer_certificate)
    self.assertNotEqual(None, self.computer.getDestinationReference())
    serial = '0x%x' % int(self.computer.getDestinationReference(), 16)
    self.assertTrue(serial in computer_certificate)
    self.assertTrue(self.computer.getReference() in computer_certificate.decode('string_escape'))

    self.computer.revokeCertificate()
    self.assertEqual(None, self.portal.REQUEST.get('computer_key'))
    self.assertEqual(None, self.portal.REQUEST.get('computer_certificate'))

    self.assertEqual(None, self.computer.getDestinationReference())

  def test_revokeCertificateNoCertificate(self):
    self.login(self.computer.getReference())
    self.assertRaises(ValueError, self.computer.revokeCertificate)
    self.assertEqual(None, self.portal.REQUEST.get('computer_key'))
    self.assertEqual(None, self.portal.REQUEST.get('computer_certificate'))
    self.assertEqual(None, self.computer.getDestinationReference())

  def test_revokeCertificate_twice(self):
    self.login(self.computer.getReference())
    self.computer.generateCertificate()
    computer_key = self.portal.REQUEST.get('computer_key')
    computer_certificate = self.portal.REQUEST.get('computer_certificate')
    self.assertNotEqual(None, computer_key)
    self.assertNotEqual(None, computer_certificate)
    self.assertNotEqual(None, self.computer.getDestinationReference())
    serial = '0x%x' % int(self.computer.getDestinationReference(), 16)
    self.assertTrue(serial in computer_certificate)
    self.assertTrue(self.computer.getReference() in computer_certificate.decode('string_escape'))

    self.computer.revokeCertificate()
    self.assertEqual(None, self.portal.REQUEST.get('computer_key'))
    self.assertEqual(None, self.portal.REQUEST.get('computer_certificate'))

    self.assertEqual(None, self.computer.getDestinationReference())

    self.assertRaises(ValueError, self.computer.revokeCertificate)
    self.assertEqual(None, self.portal.REQUEST.get('computer_key'))
    self.assertEqual(None, self.portal.REQUEST.get('computer_certificate'))
    self.assertEqual(None, self.computer.getDestinationReference())

class TestSlapOSCorePersonComputerSupply(testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSCorePersonComputerSupply, self).afterSetUp()
    portal = self.getPortalObject()
    new_id = self.generateNewId()

    # Clone computer document
    computer = portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    # Clone person document
    person_user = portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    computer.edit(
      title="Computer %s for %s" % (new_id, person_user.getReference()),
      reference="TESTCOMP-%s" % new_id,
      source_administration=person_user.getRelativeUrl()
    )
    computer.validate()
    self.computer = computer
    person_user.validate()
    for assignment in person_user.contentValues(portal_type="Assignment"):
      assignment.open()
    transaction.commit()
    # XXX Tic is needed to reindex the created open order
    self.tic()

    # Login as new user
    self.login(person_user.getReference())
    new_person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()
    self.assertEquals(person_user.getRelativeUrl(), new_person.getRelativeUrl())

  def beforeTearDown(self):
    if 'software_installation_url' in self.computer.REQUEST:
      self.computer.REQUEST['software_installation_url'] = None

  def test_supply_requiredParameter(self):
    software_release = self.generateNewSoftwareReleaseUrl()
    self.assertRaises(TypeError, self.computer.requestSoftwareRelease)
    self.assertRaises(TypeError, self.computer.requestSoftwareRelease,
        state="available")
    self.assertRaises(TypeError, self.computer.requestSoftwareRelease,
        software_release_url=software_release)
    self.assertRaises(ValueError, self.computer.requestSoftwareRelease,
        state="mana", software_release_url=software_release)

  def test_supply_available(self):
    software_release = self.generateNewSoftwareReleaseUrl()

    self.computer.requestSoftwareRelease(state="available",
        software_release_url=software_release)

    software_installation_url = self.computer.REQUEST.get(
        'software_installation_url')

    self.assertNotEqual(None, software_installation_url)
    software_installation = self.computer.restrictedTraverse(
        software_installation_url)
    self.assertEqual(software_release, software_installation.getUrlString())

  def test_supply_destroyed(self):
    software_release = self.generateNewSoftwareReleaseUrl()

    self.computer.requestSoftwareRelease(state="destroyed",
        software_release_url=software_release)

    software_installation_url = self.computer.REQUEST.get(
        'software_installation_url')

    self.assertEqual(None, software_installation_url)

  def test_supply_available_nonIndexed(self):
    software_release = self.generateNewSoftwareReleaseUrl()

    self.computer.requestSoftwareRelease(state="available",
        software_release_url=software_release)

    software_installation_url = self.computer.REQUEST.get(
        'software_installation_url')

    self.assertNotEqual(None, software_installation_url)
    software_installation = self.computer.restrictedTraverse(
        software_installation_url)
    self.assertEqual(software_release, software_installation.getUrlString())

    transaction.commit()

    self.assertRaises(NotImplementedError,
        self.computer.requestSoftwareRelease, state="available",
        software_release_url=software_release)

  def test_supply_available_destroyed_nonIndexed(self):
    software_release = self.generateNewSoftwareReleaseUrl()

    self.computer.requestSoftwareRelease(state="available",
        software_release_url=software_release)

    software_installation_url = self.computer.REQUEST.get(
        'software_installation_url')

    self.assertNotEqual(None, software_installation_url)
    software_installation = self.computer.restrictedTraverse(
        software_installation_url)
    self.assertEqual(software_release, software_installation.getUrlString())

    transaction.commit()

    self.assertRaises(NotImplementedError,
        self.computer.requestSoftwareRelease, state="destroyed",
        software_release_url=software_release)

  def test_supply_available_createdSoftwareInstallation(self):
    previous_id = self.getPortalObject().portal_ids\
        .generateNewId(id_group='slap_software_installation_reference', 
                       id_generator='uid')
    software_release = self.generateNewSoftwareReleaseUrl()

    self.computer.requestSoftwareRelease(state="available",
        software_release_url=software_release)

    software_installation_url = self.computer.REQUEST.get(
        'software_installation_url')

    self.assertNotEqual(None, software_installation_url)
    software_installation = self.computer.restrictedTraverse(
        software_installation_url)
    self.assertEqual(software_release, software_installation.getUrlString())

    self.assertEqual('Software Installation',
        software_installation.getPortalType())
    self.assertEqual('validated', software_installation.getValidationState())
    self.assertEqual('start_requested', software_installation.getSlapState())
    self.assertEqual('SOFTINSTALL-%s' % (previous_id+1),
        software_installation.getReference())

  def test_multiple_supply_available_createdSoftwareInstallation(self):
    previous_id = self.getPortalObject().portal_ids\
        .generateNewId(id_group='slap_software_installation_reference', 
                       id_generator='uid')
    software_release = self.generateNewSoftwareReleaseUrl()

    self.computer.requestSoftwareRelease(state="available",
        software_release_url=software_release)

    software_installation_url = self.computer.REQUEST.get(
        'software_installation_url')

    self.assertNotEqual(None, software_installation_url)
    software_installation = self.computer.restrictedTraverse(
        software_installation_url)
    self.assertEqual(software_release, software_installation.getUrlString())

    self.assertEqual('Software Installation',
        software_installation.getPortalType())
    self.assertEqual('validated', software_installation.getValidationState())
    self.assertEqual('start_requested', software_installation.getSlapState())
    self.assertEqual('SOFTINSTALL-%s' % (previous_id+1),
        software_installation.getReference())

    self.tic()
    self.computer.requestSoftwareRelease(state="available",
        software_release_url=software_release)

    software_installation_url2 = self.computer.REQUEST.get(
        'software_installation_url')
    self.assertEqual(software_installation_url, software_installation_url2)

  def test_supply_available_destroyed(self):
    previous_id = self.getPortalObject().portal_ids\
        .generateNewId(id_group='slap_software_installation_reference', 
                       id_generator='uid')
    software_release = self.generateNewSoftwareReleaseUrl()

    self.computer.requestSoftwareRelease(state="available",
        software_release_url=software_release)

    software_installation_url = self.computer.REQUEST.get(
        'software_installation_url')

    self.assertNotEqual(None, software_installation_url)
    software_installation = self.computer.restrictedTraverse(
        software_installation_url)
    self.assertEqual(software_release, software_installation.getUrlString())

    self.assertEqual('Software Installation',
        software_installation.getPortalType())
    self.assertEqual('validated', software_installation.getValidationState())
    self.assertEqual('start_requested', software_installation.getSlapState())
    self.assertEqual('SOFTINSTALL-%s' % (previous_id+1),
        software_installation.getReference())

    self.tic()
    self.computer.requestSoftwareRelease(state="destroyed",
        software_release_url=software_release)

    software_installation_url2 = self.computer.REQUEST.get(
        'software_installation_url')
    self.assertEqual(software_installation_url, software_installation_url2)

    software_installation = self.computer.restrictedTraverse(
        software_installation_url2)
    self.assertEqual('Software Installation',
        software_installation.getPortalType())
    self.assertEqual('validated', software_installation.getValidationState())
    self.assertEqual('destroy_requested', software_installation.getSlapState())
    self.assertEqual('SOFTINSTALL-%s' % (previous_id+1),
        software_installation.getReference())

  def test_supply_available_destroyed_available(self):
    previous_id = self.getPortalObject().portal_ids\
        .generateNewId(id_group='slap_software_installation_reference', 
                       id_generator='uid')
    software_release = self.generateNewSoftwareReleaseUrl()

    self.computer.requestSoftwareRelease(state="available",
        software_release_url=software_release)

    software_installation_url = self.computer.REQUEST.get(
        'software_installation_url')

    self.assertNotEqual(None, software_installation_url)
    software_installation = self.computer.restrictedTraverse(
        software_installation_url)
    self.assertEqual(software_release, software_installation.getUrlString())

    self.assertEqual('Software Installation',
        software_installation.getPortalType())
    self.assertEqual('validated', software_installation.getValidationState())
    self.assertEqual('start_requested', software_installation.getSlapState())
    self.assertEqual('SOFTINSTALL-%s' % (previous_id+1),
        software_installation.getReference())

    self.tic()
    self.computer.requestSoftwareRelease(state="destroyed",
        software_release_url=software_release)

    software_installation_url2 = self.computer.REQUEST.get(
        'software_installation_url')
    self.assertEqual(software_installation_url, software_installation_url2)

    software_installation = self.computer.restrictedTraverse(
        software_installation_url2)
    self.assertEqual('Software Installation',
        software_installation.getPortalType())
    self.assertEqual('validated', software_installation.getValidationState())
    self.assertEqual('destroy_requested', software_installation.getSlapState())
    self.assertEqual('SOFTINSTALL-%s' % (previous_id+1),
        software_installation.getReference())

    self.tic()
    # XXX: This scenario shall be discussed...
    self.assertRaises(UnsupportedWorkflowMethod,
        self.computer.requestSoftwareRelease, state="available",
        software_release_url=software_release)

  def test_supply_available_destroyed_finalised_available(self):
    previous_id = self.getPortalObject().portal_ids\
        .generateNewId(id_group='slap_software_installation_reference', 
                       id_generator='uid')
    software_release = self.generateNewSoftwareReleaseUrl()

    self.computer.requestSoftwareRelease(state="available",
        software_release_url=software_release)

    software_installation_url = self.computer.REQUEST.get(
        'software_installation_url')

    self.assertNotEqual(None, software_installation_url)
    software_installation = self.computer.restrictedTraverse(
        software_installation_url)
    self.assertEqual(software_release, software_installation.getUrlString())

    self.assertEqual('Software Installation',
        software_installation.getPortalType())
    self.assertEqual('validated', software_installation.getValidationState())
    self.assertEqual('start_requested', software_installation.getSlapState())
    self.assertEqual('SOFTINSTALL-%s' % (previous_id+1),
        software_installation.getReference())

    self.tic()
    self.computer.requestSoftwareRelease(state="destroyed",
        software_release_url=software_release)

    software_installation_url2 = self.computer.REQUEST.get(
        'software_installation_url')
    self.assertEqual(software_installation_url, software_installation_url2)

    software_installation = self.computer.restrictedTraverse(
        software_installation_url2)
    self.assertEqual('Software Installation',
        software_installation.getPortalType())
    self.assertEqual('validated', software_installation.getValidationState())
    self.assertEqual('destroy_requested', software_installation.getSlapState())
    self.assertEqual('SOFTINSTALL-%s' % (previous_id+1),
        software_installation.getReference())

    software_installation.invalidate()
    self.tic()
    self.computer.requestSoftwareRelease(state="available",
        software_release_url=software_release)
    software_installation_url3 = self.computer.REQUEST.get(
        'software_installation_url')
    self.assertNotEqual(software_installation_url, software_installation_url3)
    software_installation = self.computer.restrictedTraverse(
        software_installation_url3)
    self.assertEqual('Software Installation',
        software_installation.getPortalType())
    self.assertEqual('validated', software_installation.getValidationState())
    self.assertEqual('start_requested', software_installation.getSlapState())
    self.assertEqual('SOFTINSTALL-%s' % (previous_id+2),
        software_installation.getReference())

class TestSlapOSCoreInstanceSlapInterfaceWorkflow(testSlapOSMixin):
  def afterSetUp(self):
    super(TestSlapOSCoreInstanceSlapInterfaceWorkflow, self).afterSetUp()

    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.edit(
    )
    hosting_subscription.validate()
    hosting_subscription.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTHS-%s" % self.generateNewId(),
    )
    self.request_kw = dict(
      software_release=\
          self.generateNewSoftwareReleaseUrl(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='started'
    )
    hosting_subscription.requestStart(**self.request_kw)
    hosting_subscription.requestInstance(**self.request_kw)

    self.instance = hosting_subscription.getPredecessorValue()
    self.tic()

  def _countInstanceBang(self, instance, comment):
    return len([q for q in instance.workflow_history[
        'instance_slap_interface_workflow'] if q['action'] == 'bang' and \
            q['comment'] == comment])

  def test_bang_required_comment(self):
    self.login(self.instance.getReference())
    self.assertRaises(KeyError, self.instance.bang, bang_tree=0)
    transaction.abort()

  def test_bang_required_bang_tree(self):
    self.login(self.instance.getReference())
    comment = 'Comment %s' % self.generateNewId()
    self.assertRaises(KeyError, self.instance.bang, comment=comment)
    transaction.abort()

  def test_bang(self):
    self.login(self.instance.getReference())
    comment = 'Comment %s' % self.generateNewId()
    count = self._countInstanceBang(self.instance, comment)
    self.instance.bang(bang_tree=0, comment=comment)
    self.assertEqual(count+1, self._countInstanceBang(self.instance, comment))

  def test_bang_tree(self):
    self.login(self.instance.getReference())
    request_kw = self.request_kw.copy()
    request_kw['software_title'] = 'New %s' % self.generateNewId()
    self.instance.requestInstance(**request_kw)
    request_instance = self.instance.REQUEST['request_instance']
    self.instance.REQUEST['request_instance'] = None
    self.tic()

    comment = 'Comment %s' % self.generateNewId()
    count1 = self._countInstanceBang(self.instance, comment)
    count2 = self._countInstanceBang(request_instance, comment)
    self.instance.bang(bang_tree=1, comment=comment)
    self.tic()
    self.assertEqual(count1+1, self._countInstanceBang(self.instance,
        comment))
    self.assertEqual(count2+1, self._countInstanceBang(request_instance,
        comment))

  def test_allocatePartition_computer_partition_url_required(self):
    self.login(self.instance.getReference())
    self.assertRaises(TypeError, self.instance.allocatePartition)

  def test_allocatePartition(self):
    computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    computer.validate()
    computer_partition = computer.newContent(portal_type='Computer Partition')
    computer_partition.validate()
    computer_partition.markFree()
    computer_partition_url = computer_partition.getRelativeUrl()
    self.instance.allocatePartition(
        computer_partition_url=computer_partition_url)
    self.assertEqual(self.instance.getAggregate(), computer_partition_url)

  def test_unallocatePartition(self):
    computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    computer.validate()
    computer_partition = computer.newContent(portal_type='Computer Partition')
    computer_partition.validate()
    computer_partition.markFree()
    computer_partition_url = computer_partition.getRelativeUrl()
    self.instance.allocatePartition(
        computer_partition_url=computer_partition_url)
    self.assertEqual(self.instance.getAggregate(), computer_partition_url)

    self.instance.requestDestroy(**self.request_kw)
    self.instance.unallocatePartition()
    self.assertEqual(None, self.instance.getAggregate())

  def test_unallocatePartition_twice(self):
    computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    computer.validate()
    computer_partition = computer.newContent(portal_type='Computer Partition')
    computer_partition.validate()
    computer_partition.markFree()
    computer_partition_url = computer_partition.getRelativeUrl()
    self.instance.allocatePartition(
        computer_partition_url=computer_partition_url)
    self.assertEqual(self.instance.getAggregate(), computer_partition_url)

    self.instance.requestDestroy(**self.request_kw)
    self.instance.unallocatePartition()
    self.assertEqual(None, self.instance.getAggregate())
    self.assertRaises(AssertionError, self.instance.unallocatePartition)

  def test_rename_new_name_required(self):
    self.login(self.instance.getReference())
    self.assertRaises(KeyError, self.instance.rename)

  def test_rename(self):
    new_name = 'New %s' % self.generateNewId()
    self.login(self.instance.getReference())
    self.instance.rename(new_name=new_name)
    self.assertEqual(new_name, self.instance.getTitle())
    transaction.abort()

  def test_rename_twice_not_indexed(self):
    new_name = 'New %s' % self.generateNewId()
    self.login(self.instance.getReference())
    self.instance.rename(new_name=new_name)
    self.assertEqual(new_name, self.instance.getTitle())
    transaction.commit()
    self.assertRaises(NotImplementedError, self.instance.rename,
        new_name=new_name)
    transaction.abort()

  @expectedFailure
  def test_rename_twice_same_transaction(self):
    new_name = 'New %s' % self.generateNewId()
    self.login(self.instance.getReference())
    self.instance.rename(new_name=new_name)
    self.assertEqual(new_name, self.instance.getTitle())
    self.assertRaises(NotImplementedError, self.instance.rename,
        new_name=new_name)
    transaction.abort()

  def test_rename_existing(self):
    new_name = 'New %s' % self.generateNewId()
    self.login(self.instance.getReference())

    request_kw = self.request_kw.copy()
    request_kw['software_title'] = new_name

    self.instance.requestInstance(**request_kw)
    request_instance = self.instance.REQUEST['request_instance']
    self.instance.REQUEST['request_instance'] = None
    # test sanity check
    self.assertEqual(new_name, request_instance.getTitle())
    self.tic()

    self.assertRaises(ValueError, self.instance.rename, new_name=new_name)
    transaction.abort()

  def test_requestDestroy(self):
    self.login(self.instance.getReference())

    request_kw = self.request_kw.copy()
    self.instance.requestDestroy(**request_kw)
    self.assertEqual('destroy_requested', self.instance.getSlapState())
    transaction.abort()

  def test_requestDestroy_required(self):
    self.login(self.instance.getReference())

    software_release=self.request_kw['software_release']
    software_type=self.request_kw['software_type']
    instance_xml=self.request_kw['instance_xml']
    sla_xml=self.request_kw['sla_xml']
    shared=self.request_kw['shared']

    self.assertRaises(TypeError, self.instance.requestDestroy)
    transaction.abort()

    # no software_release
    self.assertRaises(TypeError, self.instance.requestDestroy,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
    )
    transaction.abort()

    # no software_type
    self.assertRaises(TypeError, self.instance.requestDestroy,
      software_release=software_release,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
    )
    transaction.abort()

    # no instance_xml
    self.assertRaises(TypeError, self.instance.requestDestroy,
      software_release=software_release,
      software_type=software_type,
      sla_xml=sla_xml,
      shared=shared,
    )
    transaction.abort()

    # no shared
    self.assertRaises(TypeError, self.instance.requestDestroy,
      software_release=software_release,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
    )
    transaction.abort()
    
    # no sla_xml
    self.assertRaises(TypeError, self.instance.requestDestroy,
      software_release=software_release,
      software_type=software_type,
      instance_xml=instance_xml,
      shared=shared,
    )
    transaction.abort()

  def test_requestStop(self):
    self.login(self.instance.getReference())

    request_kw = self.request_kw.copy()
    self.instance.requestStop(**request_kw)
    self.assertEqual('stop_requested', self.instance.getSlapState())
    transaction.abort()

  def test_requestStop_required(self):
    self.login(self.instance.getReference())

    software_release=self.request_kw['software_release']
    software_type=self.request_kw['software_type']
    instance_xml=self.request_kw['instance_xml']
    sla_xml=self.request_kw['sla_xml']
    shared=self.request_kw['shared']

    self.assertRaises(TypeError, self.instance.requestStop)
    transaction.abort()

    # no software_release
    self.assertRaises(TypeError, self.instance.requestStop,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
    )
    transaction.abort()

    # no software_type
    self.assertRaises(TypeError, self.instance.requestStop,
      software_release=software_release,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
    )
    transaction.abort()

    # no instance_xml
    self.assertRaises(TypeError, self.instance.requestStop,
      software_release=software_release,
      software_type=software_type,
      sla_xml=sla_xml,
      shared=shared,
    )
    transaction.abort()

    # no shared
    self.assertRaises(TypeError, self.instance.requestStop,
      software_release=software_release,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
    )
    transaction.abort()
    
    # no sla_xml
    self.assertRaises(TypeError, self.instance.requestStop,
      software_release=software_release,
      software_type=software_type,
      instance_xml=instance_xml,
      shared=shared,
    )
    transaction.abort()

  def test_requestStart(self):
    self.login(self.instance.getReference())

    request_kw = self.request_kw.copy()
    self.instance.requestStop(**request_kw)
    self.instance.requestStart(**request_kw)
    self.assertEqual('start_requested', self.instance.getSlapState())
    transaction.abort()

  def test_requestStart_required(self):
    self.login(self.instance.getReference())

    self.instance.requestStop(**self.request_kw)

    software_release=self.request_kw['software_release']
    software_type=self.request_kw['software_type']
    instance_xml=self.request_kw['instance_xml']
    sla_xml=self.request_kw['sla_xml']
    shared=self.request_kw['shared']

    self.assertRaises(TypeError, self.instance.requestStart)
    transaction.abort()

    # no software_release
    self.assertRaises(TypeError, self.instance.requestStart,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
    )
    transaction.abort()

    # no software_type
    self.assertRaises(TypeError, self.instance.requestStart,
      software_release=software_release,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
    )
    transaction.abort()

    # no instance_xml
    self.assertRaises(TypeError, self.instance.requestStart,
      software_release=software_release,
      software_type=software_type,
      sla_xml=sla_xml,
      shared=shared,
    )
    transaction.abort()

    # no shared
    self.assertRaises(TypeError, self.instance.requestStart,
      software_release=software_release,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
    )
    transaction.abort()
    
    # no sla_xml
    self.assertRaises(TypeError, self.instance.requestStart,
      software_release=software_release,
      software_type=software_type,
      instance_xml=instance_xml,
      shared=shared,
    )
    transaction.abort()

  def test_updateConnection(self):
    self.login(self.instance.getReference())

    request_kw = self.request_kw.copy()
    self.instance.requestStop(**request_kw)
    connection_xml = self.generateSafeXml()
    self.instance.updateConnection(connection_xml=connection_xml)
    self.assertEquals(self.instance.getConnectionXml(), connection_xml)
    transaction.abort()

  def test_updateConnectionRequired(self):
    self.login(self.instance.getReference())

    request_kw = self.request_kw.copy()
    self.instance.requestStop(**request_kw)

    # No connection_xml
    self.assertRaises(TypeError, self.instance.updateConnection)
    transaction.abort()

  def test_updateConnectionBrokenXml(self):
    self.login(self.instance.getReference())

    request_kw = self.request_kw.copy()
    self.instance.requestStop(**request_kw)

    # No connection_xml
    self.assertRaises(ValidationFailed, self.instance.updateConnection,
        connection_xml="<foo bar /<>")
    transaction.abort()

class TestSlapOSCoreSoftwareInstanceRequest(testSlapOSMixin):
  """Tests instance.requestInstance"""
  def afterSetUp(self):
    super(TestSlapOSCoreSoftwareInstanceRequest, self).afterSetUp()
    portal = self.getPortalObject()
    new_id = self.generateNewId()

    self.request_kw = dict(
        software_release=self.generateNewSoftwareReleaseUrl(),
        software_title=self.generateNewSoftwareTitle(),
        software_type=self.generateNewSoftwareType(),
        instance_xml=self.generateSafeXml(),
        sla_xml=self.generateSafeXml(),
        shared=False,
        state="started"
    )

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
        predecessor=self.software_instance.getRelativeUrl()
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
        specialise=hosting_subscription.getRelativeUrl()
    )
    self.portal.portal_workflow._jumpToStateFor(self.software_instance, 'start_requested')
    self.software_instance.validate()
    self.tic()

    # Login as new Software Instance
    self.login(self.software_instance.getReference())

  def beforeTearDown(self):
    transaction.abort()
    if 'request_instance' in self.software_instance.REQUEST:
      self.software_instance.REQUEST['request_instance'] = None

  def test_request_requiredParameter(self):
    good_request_kw = self.request_kw.copy()
    # in order to have unique requested title
    good_request_kw['software_title'] = self.generateNewSoftwareTitle()

    # check that correct request does not raise
    self.software_instance.requestInstance(**good_request_kw)

    # substract parameters
    request_kw = good_request_kw.copy()
    request_kw.pop('software_release')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

    request_kw = good_request_kw.copy()
    request_kw.pop('software_title')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

    request_kw = good_request_kw.copy()
    request_kw.pop('software_type')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

    request_kw = good_request_kw.copy()
    request_kw.pop('instance_xml')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

    request_kw = good_request_kw.copy()
    request_kw.pop('sla_xml')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

    request_kw = good_request_kw.copy()
    request_kw.pop('shared')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

    request_kw = good_request_kw.copy()
    request_kw.pop('state')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

  def test_request_createdInstance(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance)

    self.assertEqual(request_kw['software_title'],
                     requested_instance.getTitle())
    self.assertEqual('Software Instance',
                     requested_instance.getPortalType())
    self.assertEqual('validated',
                     requested_instance.getValidationState())
    self.assertEqual('start_requested',
                     requested_instance.getSlapState())
    self.assertEqual(request_kw['software_release'],
                     requested_instance.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
                     requested_instance.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
                     requested_instance.getSlaXml())
    self.assertEqual(request_kw['software_type'],
                     requested_instance.getSourceReference())

  def test_request_sameTitle(self):
    # check that correct request does not raise
    self.assertRaises(ValueError, self.software_instance.requestInstance,
                      **self.request_kw)

  def test_request_shared_True(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()
    request_kw['shared'] = True

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance)

    self.assertEqual(request_kw['software_title'],
                     requested_instance.getTitle())
    self.assertEqual('Slave Instance',
                     requested_instance.getPortalType())
    self.assertEqual('validated',
                     requested_instance.getValidationState())
    self.assertEqual('start_requested',
                     requested_instance.getSlapState())
    self.assertEqual(request_kw['software_release'],
                     requested_instance.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
                     requested_instance.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
                     requested_instance.getSlaXml())
    self.assertEqual(request_kw['software_type'],
                     requested_instance.getSourceReference())

  def test_request_shared_unsupported(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()
    request_kw['shared'] = 'True'

    self.assertRaises(ValueError, self.software_instance.requestInstance,
                      **request_kw)

  def test_request_unindexed(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance)

    self.assertEqual(request_kw['software_title'],
        requested_instance.getTitle())
    self.assertEqual('Software Instance',
        requested_instance.getPortalType())
    self.assertEqual('validated',
        requested_instance.getValidationState())
    self.assertEqual('start_requested',
        requested_instance.getSlapState())
    self.assertEqual(request_kw['software_release'],
        requested_instance.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance.getSourceReference())

    transaction.commit()

    self.assertRaises(NotImplementedError, self.software_instance.requestInstance,
        **request_kw)

  def test_request_double(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance)

    self.assertEqual(request_kw['software_title'],
        requested_instance.getTitle())
    self.assertEqual('Software Instance',
        requested_instance.getPortalType())
    self.assertEqual('validated',
        requested_instance.getValidationState())
    self.assertEqual('start_requested',
        requested_instance.getSlapState())
    self.assertEqual(request_kw['software_release'],
        requested_instance.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance.getSourceReference())

    self.tic()

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance2 = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance2)
    self.assertEqual(requested_instance2.getRelativeUrl(),
      requested_instance.getRelativeUrl())

    self.assertEqual(request_kw['software_title'],
        requested_instance2.getTitle())
    self.assertEqual('Software Instance',
        requested_instance2.getPortalType())
    self.assertEqual('validated',
        requested_instance2.getValidationState())
    self.assertEqual('start_requested',
        requested_instance2.getSlapState())
    self.assertEqual(request_kw['software_release'],
        requested_instance2.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance2.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance2.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance2.getSourceReference())

  def test_request_duplicated(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()

    duplicate = self.software_instance.Base_createCloneDocument(batch_mode=1)
    duplicate.edit(
        reference='TESTSI-%s' % self.generateNewId(),
        title=request_kw['software_title'])
    duplicate.validate()
    self.portal.portal_workflow._jumpToStateFor(duplicate, 'start_requested')

    duplicate2 = self.software_instance.Base_createCloneDocument(batch_mode=1)
    duplicate2.edit(
        reference='TESTSI-%s' % self.generateNewId(),
        title=request_kw['software_title'])
    duplicate2.validate()
    self.portal.portal_workflow._jumpToStateFor(duplicate2, 'start_requested')

    self.software_instance.getSpecialiseValue(
        portal_type='Hosting Subscription').edit(
            predecessor_list=[
                duplicate.getRelativeUrl(),
                duplicate2.getRelativeUrl(),
                self.software_instance.getRelativeUrl()
            ]
        )
    self.tic()

    self.assertRaises(ValueError, self.software_instance.requestInstance,
        **request_kw)

  def test_request_destroyed_state(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()
    request_kw['state'] = 'destroyed'

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    # requesting with destroyed state shall not create new instance
    self.assertEqual(None, requested_instance)

  def test_request_two_different(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()

    self.software_instance.requestInstance(**request_kw)

    requested_instance2 = self.software_instance.REQUEST.get(
        'request_instance')

    self.assertNotEqual(requested_instance.getRelativeUrl(),
      requested_instance2.getRelativeUrl())

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl()])

  def test_request_tree_change_indexed(self):
    """Checks tree change forced by request

    For a tree like:

    A
    |
    A
    |\
    B C

    When B requests C tree shall change to:

    A
    |
    A
    |
    B
    |
    C"""
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    B_instance = self.software_instance.REQUEST.get('request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    C_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl(), C_instance.getRelativeUrl()])

    self.tic() # in order to recalculate tree

    B_instance.requestInstance(**request_kw)
    C1_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertEqual(C_instance.getRelativeUrl(), C1_instance.getRelativeUrl())

    self.assertSameSet(self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl()])
    self.assertSameSet(B_instance.getPredecessorList(),
        [C_instance.getRelativeUrl()])

  def test_request_tree_change_not_indexed(self):
    """Checks tree change forced by request

    For a tree like:

    A
    |
    A
    |\
    B C

    When B requests C tree in next transaction, but before indexation,
    the system shall disallow the operation."""
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    B_instance = self.software_instance.REQUEST.get('request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    C_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl(), C_instance.getRelativeUrl()])

    transaction.commit()

    self.assertRaises(NotImplementedError, B_instance.requestInstance,
        **request_kw)

  @expectedFailure
  def test_request_tree_change_same_transaction(self):
    """Checks tree change forced by request

    For a tree like:

    A
    |
    A
    |\
    B C

    When B requests C tree in the same transaction the system shall
    disallow the operation."""
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    B_instance = self.software_instance.REQUEST.get('request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    C_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl(), C_instance.getRelativeUrl()])

    self.assertRaises(NotImplementedError, B_instance.requestInstance,
        **request_kw)

  def test_request_started_stopped_destroyed(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance)

    self.assertEqual(request_kw['software_title'],
        requested_instance.getTitle())
    self.assertEqual('Software Instance',
        requested_instance.getPortalType())
    self.assertEqual('validated',
        requested_instance.getValidationState())
    self.assertEqual('start_requested',
        requested_instance.getSlapState())
    self.assertEqual(request_kw['software_release'],
        requested_instance.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance.getSourceReference())

    self.tic()

    request_kw['state'] = 'stopped'
    self.software_instance.requestInstance(**request_kw)
    requested_instance2 = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance2)
    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())

    self.assertEqual(request_kw['software_title'],
        requested_instance2.getTitle())
    self.assertEqual('Software Instance',
        requested_instance2.getPortalType())
    self.assertEqual('validated',
        requested_instance2.getValidationState())
    self.assertEqual('stop_requested',
        requested_instance2.getSlapState())
    self.assertEqual(request_kw['software_release'],
        requested_instance2.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance2.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance2.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance2.getSourceReference())

    self.tic()

    request_kw['state'] = 'destroyed'
    self.software_instance.requestInstance(**request_kw)
    requested_instance3 = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertEqual(None, requested_instance3)

    # in case of destruction instance is not returned, so fetch it
    # directly form document
    requested_instance3 = self.software_instance.getPredecessorValue(
        portal_type='Software Instance')
    self.assertEqual(request_kw['software_title'],
        requested_instance3.getTitle())
    self.assertEqual('Software Instance',
        requested_instance3.getPortalType())
    self.assertEqual('validated',
        requested_instance3.getValidationState())
    self.assertEqual('destroy_requested',
        requested_instance3.getSlapState())
    self.assertEqual(request_kw['software_release'],
        requested_instance3.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance3.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance3.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance3.getSourceReference())

  def _countBang(self, document):
    return len([q for q in document.workflow_history[
        'instance_slap_interface_workflow'] if q['action'] == 'bang'])

  def test_request_started_no_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)
    self.software_instance.requestInstance(**request_kw)
    requested_instance2 = self.software_instance.REQUEST.get(
        'request_instance')
    transaction.commit()

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(bang_amount, self._countBang(requested_instance))

  def test_request_stopped_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)

    request_kw['state'] = 'stopped'
    self.software_instance.requestInstance(**request_kw)
    transaction.commit()
    requested_instance2 = self.software_instance.REQUEST.get(
        'request_instance')

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(bang_amount+1, self._countBang(requested_instance))

  def test_request_destroyed_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)

    request_kw['state'] = 'destroyed'
    self.software_instance.requestInstance(**request_kw)
    transaction.commit()
    requested_instance2 = self.software_instance.getPredecessorValue(
        portal_type='Software Instance')

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(bang_amount+1, self._countBang(requested_instance))

  def test_request_tree_change_indexed_shared(self):
    """Checks tree change forced by request

    For a tree like:

    A
    |
    A
    |\
    B C

    When B requests C tree shall change to:

    A
    |
    A
    |
    B
    |
    C"""
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    request_kw['shared'] = True
    self.software_instance.requestInstance(**request_kw)
    B_instance = self.software_instance.REQUEST.get('request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    C_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl(), C_instance.getRelativeUrl()])

    self.tic() # in order to recalculate tree

    B_instance.requestInstance(**request_kw)
    C1_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertEqual(C_instance.getRelativeUrl(), C1_instance.getRelativeUrl())

    self.assertSameSet(self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl()])
    self.assertSameSet(B_instance.getPredecessorList(),
        [C_instance.getRelativeUrl()])

  def test_request_tree_change_not_indexed_shared(self):
    """Checks tree change forced by request

    For a tree like:

    A
    |
    A
    |\
    B C

    When B requests C tree in next transaction, but before indexation,
    the system shall disallow the operation."""
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    request_kw['shared'] = True
    self.software_instance.requestInstance(**request_kw)
    B_instance = self.software_instance.REQUEST.get('request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    C_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl(), C_instance.getRelativeUrl()])

    transaction.commit()

    self.assertRaises(NotImplementedError, B_instance.requestInstance,
        **request_kw)

  @expectedFailure
  def test_request_tree_change_same_transaction_shared(self):
    """Checks tree change forced by request

    For a tree like:

    A
    |
    A
    |\
    B C

    When B requests C tree in the same transaction the system shall
    disallow the operation."""
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    request_kw['shared'] = True
    self.software_instance.requestInstance(**request_kw)
    B_instance = self.software_instance.REQUEST.get('request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    C_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl(), C_instance.getRelativeUrl()])

    self.assertRaises(NotImplementedError, B_instance.requestInstance,
        **request_kw)

  def test_request_software_release_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)

    request_kw['software_release'] = self.generateNewSoftwareReleaseUrl()
    self.software_instance.requestInstance(**request_kw)
    requested_instance2 = self.software_instance.getPredecessorValue(
        portal_type='Software Instance')

    transaction.commit()

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(request_kw['software_release'],
        requested_instance2.getUrlString())
    self.assertEqual(bang_amount+1, self._countBang(requested_instance))

  def test_request_software_type_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)

    request_kw['software_type'] = self.generateNewSoftwareReleaseUrl()
    self.software_instance.requestInstance(**request_kw)
    requested_instance2 = self.software_instance.getPredecessorValue(
        portal_type='Software Instance')

    transaction.commit()

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(request_kw['software_type'],
        requested_instance2.getSourceReference())
    self.assertEqual(bang_amount+1, self._countBang(requested_instance))

  def test_request_instance_xml_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)

    request_kw['instance_xml'] = self.generateSafeXml()
    self.software_instance.requestInstance(**request_kw)
    requested_instance2 = self.software_instance.getPredecessorValue(
        portal_type='Software Instance')

    transaction.commit()

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance2.getTextContent())
    self.assertEqual(bang_amount+1, self._countBang(requested_instance))

  def test_request_sla_xml_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)

    request_kw['sla_xml'] = self.generateSafeXml()
    self.software_instance.requestInstance(**request_kw)
    requested_instance2 = self.software_instance.getPredecessorValue(
        portal_type='Software Instance')

    transaction.commit()

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance2.getSlaXml())
    self.assertEqual(bang_amount+1, self._countBang(requested_instance))

  def test_update_connection_bang_requester(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(self.software_instance)

    connection_xml = self.generateSafeXml()
    requested_instance.updateConnection(connection_xml=connection_xml)

    transaction.commit()

    self.assertEqual(bang_amount+1, self._countBang(self.software_instance))

class TestSlapOSCorePersonRequest(testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSCorePersonRequest, self).afterSetUp()
    portal = self.getPortalObject()
    new_id = self.generateNewId()

    # Clone person document
    person_user = portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    person_user.validate()
    for assignment in person_user.contentValues(portal_type="Assignment"):
      assignment.open()
    transaction.commit()
    # XXX Tic is needed to reindex the created open order
    self.tic()

    # Login as new user
    self.login(person_user.getReference())
    new_person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()
    self.assertEquals(person_user.getRelativeUrl(), new_person.getRelativeUrl())

  def beforeTearDown(self):
    pass

  def test_Person_requestSoftwareInstance_requiredParameter(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.generateNewSoftwareReleaseUrl()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    self.assertRaises(TypeError, person.requestSoftwareInstance)

    # software_release is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

    # software_title is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

    # software_type is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

    # instance_xml is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

    # instance_xml is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

    # sla_xml is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      shared=shared,
      state=state,
    )

    # shared is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      state=state,
    )

    # state is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
    )

  def test_Person_requestSoftwareInstance_acceptedState(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.generateNewSoftwareReleaseUrl()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True

    # Only started, stopped, destroyed
    self.assertRaises(ValueError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="foo",
    )

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title="started",
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="started",
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals("start_requested", hosting_subscription.getSlapState())

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title="stopped",
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="stopped",
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals("stop_requested", hosting_subscription.getSlapState())

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title="destroyed",
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="destroyed",
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals(None, hosting_subscription)

  def test_Person_requestSoftwareInstance_returnHostingSubscriptionUrl(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.generateNewSoftwareReleaseUrl()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals("Hosting Subscription", 
                      hosting_subscription.getPortalType())

  def test_Person_requestSoftwareInstance_createHostingSubscription(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.generateNewSoftwareReleaseUrl()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    previous_id = self.getPortalObject().portal_ids\
        .generateNewId(id_group='slap_hosting_subscription_reference', 
                       id_generator='uid')

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals(software_release,
                      hosting_subscription.getUrlString())
    self.assertEquals(software_title, hosting_subscription.getTitle())
    self.assertEquals(software_type, hosting_subscription.getSourceReference())
    self.assertEquals(instance_xml, hosting_subscription.getTextContent())
    self.assertEquals(sla_xml, hosting_subscription.getSlaXml())
    self.assertEquals(shared, hosting_subscription.getRootSlave())
    self.assertEquals("start_requested", hosting_subscription.getSlapState())
    self.assertEquals("HOSTSUBS-%s" % (previous_id+1),
                      hosting_subscription.getReference())
    self.assertEquals("validated", hosting_subscription.getValidationState())

  def test_Person_requestSoftwareInstance_HostingSubscriptionNotReindexed(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.generateNewSoftwareReleaseUrl()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )
    transaction.commit()

    self.assertRaises(NotImplementedError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

  @expectedFailure
  def test_Person_requestSoftwareInstance_updateHostingSubscription(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.generateNewSoftwareReleaseUrl()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    hosting_subscription_reference = hosting_subscription.getReference()

    transaction.commit()
    self.tic()

    software_release2 = self.generateNewSoftwareReleaseUrl()
    software_type2 = "test2"
    instance_xml2 = """<?xml version='1.0' encoding='utf-8'?>
<instance>

</instance>"""
    sla_xml2 = """<?xml version='1.0' encoding='utf-8'?>
<instance>

</instance>"""
    shared2 = False
    state2 = "stopped"

    person.requestSoftwareInstance(
      software_release=software_release2,
      software_title=software_title,
      software_type=software_type2,
      instance_xml=instance_xml2,
      sla_xml=sla_xml2,
      shared=shared2,
      state=state2,
    )

    hosting_subscription2 = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals(hosting_subscription.getRelativeUrl(),
                      hosting_subscription2.getRelativeUrl())
    self.assertEquals(hosting_subscription_reference,
                      hosting_subscription2.getReference())

    self.assertEquals(software_release2,
                      hosting_subscription.getUrlString())
    self.assertEquals(software_title, hosting_subscription.getTitle())
    self.assertEquals(software_type2, hosting_subscription.getSourceReference())
    self.assertEquals(instance_xml2, hosting_subscription.getTextContent())
    self.assertEquals(sla_xml2, hosting_subscription.getSlaXml())
    self.assertEquals(shared2, hosting_subscription.getRootSlave())
    self.assertEquals("stop_requested", hosting_subscription.getSlapState())
    self.assertEquals("validated", hosting_subscription.getValidationState())

  def test_Person_requestSoftwareInstance_duplicatedHostingSubscription(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.generateNewSoftwareReleaseUrl()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    transaction.commit()
    hosting_subscription2 = hosting_subscription.Base_createCloneDocument(
                                                                batch_mode=1)
    hosting_subscription2.validate()

    transaction.commit()
    self.tic()

    self.assertRaises(NotImplementedError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

  def test_Person_requestSoftwareInstance_HostingSubscriptionNewTitle(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.generateNewSoftwareReleaseUrl()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version='1.0' encoding='utf-8'?>
<instance>
</instance>"""
    sla_xml = """<?xml version='1.0' encoding='utf-8'?>
<instance>
</instance>"""
    shared = True
    state = "started"

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')

    transaction.commit()

    software_release2 = self.generateNewSoftwareReleaseUrl()
    software_title2 = "test2"
    software_type2 = "test2"
    instance_xml2 = """<?xml version='1.0' encoding='utf-8'?>
<instance>

</instance>"""
    sla_xml2 = """<?xml version='1.0' encoding='utf-8'?>
<instance>

</instance>"""
    shared2 = False
    state2 = "stopped"

    person.requestSoftwareInstance(
      software_release=software_release2,
      software_title=software_title2,
      software_type=software_type2,
      instance_xml=instance_xml2,
      sla_xml=sla_xml2,
      shared=shared2,
      state=state2,
    )

    hosting_subscription2 = person.REQUEST.get('request_hosting_subscription')
    self.assertNotEquals(hosting_subscription.getRelativeUrl(),
                      hosting_subscription2.getRelativeUrl())
    self.assertNotEquals(hosting_subscription.getReference(),
                      hosting_subscription2.getReference())

    self.assertEquals(software_release2,
                      hosting_subscription2.getUrlString())
    self.assertEquals(software_title2, hosting_subscription2.getTitle())
    self.assertEquals(software_type2, hosting_subscription2.getSourceReference())
    self.assertEquals(instance_xml2, hosting_subscription2.getTextContent())
    self.assertEquals(sla_xml2, hosting_subscription2.getSlaXml())
    self.assertEquals(shared2, hosting_subscription2.getRootSlave())
    self.assertEquals("stop_requested", hosting_subscription2.getSlapState())
    self.assertEquals("validated", hosting_subscription2.getValidationState())

  def test_Person_requestSoftwareInstance_deletedHostingSubscription(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.generateNewSoftwareReleaseUrl()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="stopped",
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    transaction.commit()
    self.tic()

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="destroyed",
    )
    hosting_subscription2 = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals(None, hosting_subscription2)
    self.assertEquals("destroy_requested", hosting_subscription.getSlapState())

  def test_Person_requestSoftwareInstance_noConflictWithDeletedHostingSubscription(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.generateNewSoftwareReleaseUrl()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="stopped",
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    transaction.commit()
    self.tic()
    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="destroyed",
    )
    self.assertEquals("destroy_requested", hosting_subscription.getSlapState())
    transaction.commit()
    self.tic()

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="started",
    )
    hosting_subscription2 = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals("start_requested", hosting_subscription2.getSlapState())
    self.assertNotEquals(hosting_subscription.getRelativeUrl(),
                         hosting_subscription2.getRelativeUrl())

class TestSlapOSCorePersonRequestComputer(testSlapOSMixin):

  def generateNewComputerTitle(self):
    return 'My Comp %s' % self.generateNewId()

  def afterSetUp(self):
    super(TestSlapOSCorePersonRequestComputer, self).afterSetUp()
    portal = self.getPortalObject()
    new_id = self.generateNewId()

    # Clone person document
    person_user = portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    person_user.edit(
        title="live_test_%s" % new_id,
        reference="live_test_%s" % new_id,
        default_email_text="live_test_%s@example.org" % new_id,
    )

    person_user.validate()
    for assignment in person_user.contentValues(portal_type="Assignment"):
      assignment.open()
    transaction.commit()
    # XXX Tic is needed to reindex the created open order
    self.tic()

    # Login as new user
    self.login(person_user.getReference())
    new_person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()
    self.assertEquals(person_user.getRelativeUrl(), new_person.getRelativeUrl())

  def beforeTearDown(self):
    pass

  def test_request_requiredParameter(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    # computer_title is mandatory
    self.assertRaises(TypeError, person.requestComputer)

    # if provided does not raise
    computer_title = self.generateNewComputerTitle()
    person.requestComputer(computer_title=computer_title)

  def test_request(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    computer_title = self.generateNewComputerTitle()
    person.requestComputer(computer_title=computer_title)

    # check what is returned via request
    computer_url = person.REQUEST.get('computer')
    computer_absolute_url = person.REQUEST.get('computer_url')
    computer_reference = person.REQUEST.get('computer_reference')

    self.assertNotEqual(None, computer_url)
    self.assertNotEqual(None, computer_absolute_url)
    self.assertNotEqual(None, computer_reference)

  def test_request_createdComputer(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    previous_id = self.getPortalObject().portal_ids\
        .generateNewId(id_group='slap_computer_reference',
                       id_generator='uid')

    computer_title = self.generateNewComputerTitle()
    person.requestComputer(computer_title=computer_title)

    # check what is returned via request
    computer_url = person.REQUEST.get('computer')
    computer_absolute_url = person.REQUEST.get('computer_url')
    computer_reference = person.REQUEST.get('computer_reference')

    self.assertNotEqual(None, computer_url)
    self.assertNotEqual(None, computer_absolute_url)
    self.assertNotEqual(None, computer_reference)

    # check that title is ok
    computer = person.restrictedTraverse(computer_url)
    self.assertEqual(computer_title, computer.getTitle())

    # check that data are sane
    self.assertEqual(computer_absolute_url, computer.absolute_url())
    self.assertEqual(computer_reference, computer.getReference())
    self.assertEqual('COMP-%s' % (previous_id + 1), computer.getReference())
    self.assertEqual('validated', computer.getValidationState())
    self.assertEqual('open/personal', computer.getAllocationScope())
    self.assertEqual('open', computer.getCapacityScope())

  def test_request_notReindexedCompute(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    computer_title = self.generateNewComputerTitle()
    person.requestComputer(computer_title=computer_title)
    transaction.commit()
    self.assertRaises(NotImplementedError, person.requestComputer,
                      computer_title=computer_title)

  def test_multiple_request_createdComputer(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    previous_id = self.getPortalObject().portal_ids\
        .generateNewId(id_group='slap_computer_reference',
                       id_generator='uid')

    computer_title = self.generateNewComputerTitle()
    computer_title2 = self.generateNewComputerTitle()
    person.requestComputer(computer_title=computer_title)

    # check what is returned via request
    computer_url = person.REQUEST.get('computer')
    computer_absolute_url = person.REQUEST.get('computer_url')
    computer_reference = person.REQUEST.get('computer_reference')

    self.assertNotEqual(None, computer_url)
    self.assertNotEqual(None, computer_absolute_url)
    self.assertNotEqual(None, computer_reference)

    # check that title is ok
    computer = person.restrictedTraverse(computer_url)
    self.assertEqual(computer_title, computer.getTitle())

    # check that data are sane
    self.assertEqual(computer_absolute_url, computer.absolute_url())
    self.assertEqual(computer_reference, computer.getReference())
    self.assertEqual('COMP-%s' % (previous_id + 1), computer.getReference())
    self.assertEqual('validated', computer.getValidationState())
    self.assertEqual('open/personal', computer.getAllocationScope())
    self.assertEqual('open', computer.getCapacityScope())

    self.tic()

    # request again the same computer
    person.requestComputer(computer_title=computer_title)

    # check what is returned via request
    computer_url = person.REQUEST.get('computer')
    computer_absolute_url = person.REQUEST.get('computer_url')
    computer_reference = person.REQUEST.get('computer_reference')

    self.assertNotEqual(None, computer_url)
    self.assertNotEqual(None, computer_absolute_url)
    self.assertNotEqual(None, computer_reference)

    # check that title is ok
    computer = person.restrictedTraverse(computer_url)
    self.assertEqual(computer_title, computer.getTitle())

    # check that data are sane
    self.assertEqual(computer_absolute_url, computer.absolute_url())
    self.assertEqual(computer_reference, computer.getReference())
    self.assertEqual('COMP-%s' % (previous_id + 1), computer.getReference())
    self.assertEqual('validated', computer.getValidationState())
    self.assertEqual('open/personal', computer.getAllocationScope())
    self.assertEqual('open', computer.getCapacityScope())

    # and now another one
    person.requestComputer(computer_title=computer_title2)

    # check what is returned via request
    computer_url2 = person.REQUEST.get('computer')
    computer_absolute_url2 = person.REQUEST.get('computer_url')
    computer_reference2 = person.REQUEST.get('computer_reference')

    self.assertNotEqual(None, computer_url2)
    self.assertNotEqual(None, computer_absolute_url2)
    self.assertNotEqual(None, computer_reference2)

    # check that computers are really different objects
    self.assertNotEqual(computer_url2, computer_url)

    # check that title is ok
    computer2 = person.restrictedTraverse(computer_url2)
    self.assertEqual(computer_title2, computer2.getTitle())

    # check that data are sane
    self.assertEqual(computer_absolute_url2, computer2.absolute_url())
    self.assertEqual(computer_reference2, computer2.getReference())
    self.assertEqual('COMP-%s' % (previous_id + 2), computer2.getReference())
    self.assertEqual('validated', computer2.getValidationState())
    self.assertEqual('open/personal', computer2.getAllocationScope())
    self.assertEqual('open', computer2.getCapacityScope())

  def test_request_duplicatedComputer(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    computer_title = self.generateNewComputerTitle()
    person.requestComputer(computer_title=computer_title)

    # check what is returned via request
    computer_url = person.REQUEST.get('computer')
    computer_absolute_url = person.REQUEST.get('computer_url')
    computer_reference = person.REQUEST.get('computer_reference')

    self.assertNotEqual(None, computer_url)
    self.assertNotEqual(None, computer_absolute_url)
    self.assertNotEqual(None, computer_reference)

    # check that title is ok
    computer = person.restrictedTraverse(computer_url)

    sm = getSecurityManager()
    try:
      self.login()
      computer2 = computer.Base_createCloneDocument(batch_mode=1)
      computer2.validate()
    finally:
      setSecurityManager(sm)
    self.tic()

    self.assertRaises(NotImplementedError, person.requestComputer,
                      computer_title=computer_title)

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
