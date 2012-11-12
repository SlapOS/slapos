# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.tests.backportUnittest import expectedFailure
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
    self.assertTrue(self.computer.getReference() in computer_certificate)

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
    self.assertTrue(self.computer.getReference() in computer_certificate)

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
    self.assertTrue(self.computer.getReference() in computer_certificate)

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
    self.assertTrue(self.computer.getReference() in computer_certificate)

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
