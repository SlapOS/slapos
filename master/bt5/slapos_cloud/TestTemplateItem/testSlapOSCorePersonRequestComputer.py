# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import testSlapOSMixin
import transaction


class TestSlapOSCorePersonRequestComputer(testSlapOSMixin):

  def generateNewId(self):
    return self.getPortalObject().portal_ids.generateNewId(
        id_group=('slapos_core_test'))

  def generateNewComputerTitle(self):
    return 'My Comp %s' % self.generateNewId()

  def afterSetUp(self):
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

    computer2 = computer.Base_createCloneDocument(batch_mode=1)
    computer2.validate()
    self.tic()

    self.assertRaises(NotImplementedError, person.requestComputer,
                      computer_title=computer_title)
