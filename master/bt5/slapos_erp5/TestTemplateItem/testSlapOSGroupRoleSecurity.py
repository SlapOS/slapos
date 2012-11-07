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

class TestComputerModel(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    model = self.portal.computer_model_module.newContent(
        portal_type='Computer Model')
    model.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(model,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(model, 'G-COMPANY', ['Assignor'])

  def test_ComputerAgent(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    model = self.portal.computer_model_module.newContent(
        portal_type='Computer Model',
        source_administration=person.getRelativeUrl())
    model.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(model,
        ['G-COMPANY', self.user_id, reference], False)
    self.assertRoles(model, reference, ['Assignee'])

class TestComputerModelModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.computer_model_module
    self.assertSecurityGroup(module,
        ['R-MEMBER', 'zope'], False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'zope', ['Owner'])

class TestComputerModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.computer_module
    self.assertSecurityGroup(module,
        ['R-COMPUTER', 'R-MEMBER', 'R-SHADOW-PERSON', 'zope'], False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(module, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(module, 'zope', ['Owner'])

class TestComputerNetwork(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    network = self.portal.computer_network_module.newContent(
        portal_type='Computer Network')
    network.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(network,
        ['G-COMPANY', 'R-SHADOW-PERSON', self.user_id], False)
    self.assertRoles(network, 'G-COMPANY', ['Assignor'])
    self.assertRoles(network, 'R-SHADOW-PERSON', ['Auditor'])

  test_PersonShadow = test_GroupCompany

  def test_ComputerAgent(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    network = self.portal.computer_network_module.newContent(
        portal_type='Computer Network',
        source_administration=person.getRelativeUrl())
    network.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(network,
        ['G-COMPANY', 'R-SHADOW-PERSON', self.user_id, reference], False)
    self.assertRoles(network, reference, ['Assignee'])

class TestComputerNetworkModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.computer_network_module
    self.assertSecurityGroup(module,
        ['R-MEMBER', 'R-SHADOW-PERSON', 'zope'], False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(module, 'zope', ['Owner'])

class TestComputerPartition(TestSlapOSGroupRoleSecurityMixin):
  def test_CustomerOfThePartition(self):
    partition = self.portal.computer_module.newContent(
        portal_type='Computer').newContent(portal_type='Computer Partition')
    self.portal.portal_workflow._jumpToStateFor(partition, 'busy')
    partition.recursiveImmediateReindexObject()

    instance_customer_reference = 'TESTPERSON-%s' % self.generateNewId()
    slave_customer_reference = 'TESTPERSON-%s' % self.generateNewId()
    instance_customer = self.portal.person_module.newContent(
        portal_type='Person', reference=instance_customer_reference)
    slave_customer = self.portal.person_module.newContent(
        portal_type='Person', reference=slave_customer_reference)

    instance_subscription_reference = 'TESTHS-%s' % self.generateNewId()
    instance_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    instance_subscription.edit(
        destination_section=instance_customer.getRelativeUrl(),
        reference=instance_subscription_reference)
    instance = self.portal.software_instance_module.template_software_instance\
        .Base_createCloneDocument(batch_mode=1)
    instance.edit(specialise=instance_subscription.getRelativeUrl(),
        aggregate=partition.getRelativeUrl())
    instance.validate()
    instance.recursiveImmediateReindexObject()

    slave_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    slave_subscription.edit(
        destination_section=slave_customer.getRelativeUrl())
    slave = self.portal.software_instance_module.template_slave_instance\
        .Base_createCloneDocument(batch_mode=1)
    slave.validate()
    slave.edit(specialise=slave_subscription.getRelativeUrl(),
        aggregate=partition.getRelativeUrl())
    slave.recursiveImmediateReindexObject()

    partition.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(partition,
        [self.user_id, instance_customer_reference, slave_customer_reference,
          instance_subscription_reference], True)
    self.assertRoles(partition, instance_customer_reference, ['Auditor'])
    self.assertRoles(partition, slave_customer_reference, ['Auditor'])
    self.assertRoles(partition, instance_subscription_reference, ['Auditor'])

  test_SoftwareInstanceGroupRelatedToComputerPartition = \
      test_CustomerOfThePartition
