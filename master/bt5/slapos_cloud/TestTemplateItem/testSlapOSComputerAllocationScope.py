# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import testSlapOSMixin
from AccessControl import getSecurityManager
from DateTime import DateTime
import transaction

class TestAllocationScope(testSlapOSMixin):
  def afterSetUp(self):
    super(TestAllocationScope, self).afterSetUp()
    self.user_id = getSecurityManager().getUser().getId()

  def beforeTearDown(self):
    transaction.abort()

  def generateNewId(self):
    return self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_core_test'))
  
  def test_GroupCompany(self):
    computer = self.portal.computer_module.newContent(portal_type='Computer')
    computer.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(computer,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(computer, 'G-COMPANY', ['Assignor'])
    self.assertRoles(computer, self.user_id, ['Owner'])

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
    self.assertRoles(computer, self.user_id, ['Owner'])

  def test_NotAllowedAllocationScope(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    computer_ref = 'TESTCOMP-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    assignment = person.newContent(portal_type='Assignment')
    assignment.setRole('role/member')
    assignment.setStartDate(DateTime())
    assignment.open()
    assignment.updateLocalRolesOnSecurityGroups()
    
    computer = self.portal.computer_module.newContent(portal_type='Computer',
        source_administration=person.getRelativeUrl(),
        reference=computer_ref)
        	
    # open/public
    computer.edit(allocation_scope='open/public')
    computer.updateLocalRolesOnSecurityGroups()
    computer.Computer_checkAndUpdateAllocationScope()
    self.assertEquals(computer.getAllocationScope(), 'open/personal')
    
    # open/personal
    computer.edit(allocation_scope='open/personal',
        source_administration=person.getRelativeUrl()
    )
    computer.updateLocalRolesOnSecurityGroups()
    computer.Computer_checkAndUpdateAllocationScope()
    self.assertEquals(computer.getAllocationScope(), 'open/personal')
    
    # open/friend
    friend_reference = 'TESTPERSON-%s' % self.generateNewId()
    friend_person = self.portal.person_module.newContent(portal_type='Person',
        reference=friend_reference)
    computer.edit(allocation_scope='open/friend',
        destination_section=friend_person.getRelativeUrl()
    )
    computer.updateLocalRolesOnSecurityGroups()
    computer.Computer_checkAndUpdateAllocationScope()
    self.assertEquals(computer.getAllocationScope(), 'open/personal')

  def test_AllowedAllocationScope(self):    
    # Test computer allocation scope with 'service_provider' user assignment
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    assignment = person.newContent(portal_type='Assignment')
    assignment.setRole('role/service_provider')
    assignment.setStartDate(DateTime())
    assignment.open()
    assignment.updateLocalRolesOnSecurityGroups()
    
    computer = self.portal.computer_module.newContent(portal_type='Computer',
        source_administration=person.getRelativeUrl())
    
    # open/public
    computer.edit(allocation_scope='open/public')
    computer.updateLocalRolesOnSecurityGroups()
    computer.Computer_checkAndUpdateAllocationScope()
    self.assertEquals(computer.getAllocationScope(), 'open/public')
    
    # open/personal
    computer.edit(allocation_scope='open/personal',
        source_administration=person.getRelativeUrl()
    )
    computer.updateLocalRolesOnSecurityGroups()
    computer.Computer_checkAndUpdateAllocationScope()
    self.assertEquals(computer.getAllocationScope(), 'open/personal')
    
    # open/friend
    friend_reference = 'TESTPERSON-%s' % self.generateNewId()
    friend_person = self.portal.person_module.newContent(portal_type='Person',
        reference=friend_reference)
    computer.edit(allocation_scope='open/friend',
        destination_section=friend_person.getRelativeUrl()
    )
    computer.updateLocalRolesOnSecurityGroups()
    computer.Computer_checkAndUpdateAllocationScope()
    self.assertEquals(computer.getAllocationScope(), 'open/friend')
    
    