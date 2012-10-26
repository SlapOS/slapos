# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.tests.backportUnittest import expectedFailure
from Products.ERP5Type.Errors import UnsupportedWorkflowMethod

class TestSlapOSCorePersonComputerSupply(testSlapOSMixin):

  def generateNewId(self):
    return self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_core_test'))

  def generateNewSoftwareReleaseUrl(self):
    return 'http://example.org/test%s.cfg' % self.generateNewId()

  def afterSetUp(self):
    portal = self.getPortalObject()
    new_id = self.generateNewId()

    # XXX setupPortalCertificateAuthority is deprecated but it 
    #     cannot be completly removed yet, This is going to be
    #     replace such logic by promise alarms.
    if not self.isLiveTest():    
      self.setupPortalCertificateAuthority()

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
    computer.updateLocalRolesOnSecurityGroups()
    computer.validate()
    self.computer = computer
    person_user.updateLocalRolesOnSecurityGroups()
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
