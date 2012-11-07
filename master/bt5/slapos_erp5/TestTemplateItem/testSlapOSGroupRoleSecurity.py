# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import testSlapOSMixin
from AccessControl import getSecurityManager
import transaction

class TestSlapOSGroupRoleSecurityMixin(testSlapOSMixin):
  def afterSetUp(self):
    super(TestSlapOSGroupRoleSecurityMixin, self).afterSetUp()
    self.login()
    self.user_id = getSecurityManager().getUser().getId()

  def beforeTearDown(self):
    transaction.abort()

  def generateNewId(self):
    return self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_core_test'))

  def _getLocalRoles(self, context):
    return [x[0] for x in context.get_local_roles()]

  def _permissionsOfRole(self, context, role):
    return [x['name'] for x in context.permissionsOfRole(role) \
          if x['selected'] == 'SELECTED']

  def assertPermissionsOfRole(self, context, role, permission_list):
    self.assertSameSet(
      permission_list,
      self._permissionsOfRole(context, role))

  def assertSecurityGroup(self, context, security_group_list, acquired):
    self.assertEquals(acquired, context._getAcquireLocalRoles())
    self.assertSameSet(
      security_group_list,
      self._getLocalRoles(context)
    )

  def assertRoles(self, context, security_group, role_list):
    self.assertSameSet(
      role_list,
      context.get_local_roles_for_userid(security_group)
    )

class TestAssignment(TestSlapOSGroupRoleSecurityMixin):
  def test_Company_Group(self):
    assignment = self.portal.person_module.newContent(
        portal_type='Person').newContent(portal_type='Assignment')
    assignment.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(assignment,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(assignment, 'G-COMPANY', ['Auditor', 'Assignor'])

class TestComputer(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    computer = self.portal.computer_module.newContent(portal_type='Computer')
    computer.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(computer,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(computer, 'G-COMPANY', ['Assignor'])

  def test_ComputerAgent(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    computer = self.portal.computer_module.newContent(portal_type='Computer',
        source_administration=person.getRelativeUrl())
    computer.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(computer,
        [self.user_id, 'G-COMPANY', reference], False)
    self.assertRoles(computer, reference, ['Assignee'])

  def test_AllocationScope(self):
    computer = self.portal.computer_module.newContent(portal_type='Computer')

    # open/public
    computer.edit(allocation_scope='open/public')
    computer.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(computer,
        [self.user_id, 'G-COMPANY', 'R-SHADOW-PERSON'], False)
    self.assertRoles(computer, 'R-SHADOW-PERSON', ['Auditor'])

    # open/personal
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    computer.edit(allocation_scope='open/personal',
        source_administration=person.getRelativeUrl()
    )
    computer.updateLocalRolesOnSecurityGroups()
    shadow_reference = 'SHADOW-%s' % reference
    self.assertSecurityGroup(computer,
        [self.user_id, 'G-COMPANY', shadow_reference, reference], False)
    self.assertRoles(computer, shadow_reference, ['Auditor'])

    # open/friend
    friend_reference = 'TESTPERSON-%s' % self.generateNewId()
    friend_person = self.portal.person_module.newContent(portal_type='Person',
        reference=friend_reference)
    computer.edit(allocation_scope='open/friend',
        destination_section=friend_person.getRelativeUrl()
    )
    computer.updateLocalRolesOnSecurityGroups()
    shadow_friend_reference = 'SHADOW-%s' % friend_reference
    self.assertSecurityGroup(computer,
        [self.user_id, 'G-COMPANY', shadow_friend_reference, reference], False)
    self.assertRoles(computer, shadow_friend_reference, ['Auditor'])

  def test_selfComputer(self):
    reference = 'TESTCOMP-%s' % self.generateNewId()
    computer = self.portal.computer_module.newContent(portal_type='Computer',
        reference=reference)
    computer.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(computer,
        [self.user_id, 'G-COMPANY', reference], False)
    self.assertRoles(computer, reference, ['Assignor'])

