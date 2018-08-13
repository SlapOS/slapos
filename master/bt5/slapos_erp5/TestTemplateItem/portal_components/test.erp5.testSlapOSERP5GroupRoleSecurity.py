# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
from erp5.component.test.SlapOSTestCaseMixin import SlapOSTestCaseMixinWithAbort
from AccessControl import getSecurityManager

class TestSlapOSGroupRoleSecurityMixin(SlapOSTestCaseMixinWithAbort):

  def afterSetUp(self):
    SlapOSTestCaseMixinWithAbort.afterSetUp(self)
    self.user_id = getSecurityManager().getUser().getId()

  def changeOwnership(self, document):
    """ Change the ownership of the document to the right and
        expected user. Normally the user which setups the site.
    """
    document.changeOwnership(getSecurityManager().getUser(), False)
    document.updateLocalRolesOnSecurityGroups()

  def _getLocalRoles(self, context):
    return [x[0] for x in context.get_local_roles()]

  def _permissionsOfRole(self, context, role):
    return [x['name'] for x in context.permissionsOfRole(role) \
          if x['selected'] == 'SELECTED']

  def _acquirePermissions(self, context):
    return [x['name'] for x in context.permission_settings() \
          if x['acquire'] == 'CHECKED']

  def assertPermissionsOfRole(self, context, role, permission_list):
    self.assertSameSet(
      permission_list,
      self._permissionsOfRole(context, role))

  def assertAcquiredPermissions(self, context, permission_list):
    self.assertSameSet(
      permission_list,
      self._acquirePermissions(context))

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
    self.assertRoles(assignment, self.user_id, ['Owner'])

class TestComputer(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    computer = self.portal.computer_module.newContent(portal_type='Computer')
    computer.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(computer,
        ['G-COMPANY', self.user_id, computer.getUserId()], False)
    self.assertRoles(computer, 'G-COMPANY', ['Assignor'])
    self.assertRoles(computer, self.user_id, ['Owner'])
    self.assertRoles(computer, computer.getUserId(), ['Assignor'])

  def test_ComputerAgent(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    computer = self.portal.computer_module.newContent(portal_type='Computer',
        source_administration=person.getRelativeUrl())
    computer.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(computer,
        [self.user_id, 'G-COMPANY', person.getUserId(), computer.getUserId()], False)
    self.assertRoles(computer, person.getUserId(), ['Assignee'])
    self.assertRoles(computer, self.user_id, ['Owner'])
    self.assertRoles(computer, computer.getUserId(), ['Assignor'])

  def test_AllocationScope(self):
    computer = self.portal.computer_module.newContent(portal_type='Computer')

    # open/public
    computer.edit(allocation_scope='open/public')
    computer.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(computer,
        [self.user_id, 'G-COMPANY', 'R-SHADOW-PERSON', computer.getUserId()], False)
    self.assertRoles(computer, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(computer, self.user_id, ['Owner'])
    self.assertRoles(computer, computer.getUserId(), ['Assignor'])

    # open/personal
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    computer.edit(allocation_scope='open/personal',
        source_administration=person.getRelativeUrl()
    )
    computer.updateLocalRolesOnSecurityGroups()
    shadow_user_id = 'SHADOW-%s' % person.getUserId()

    self.assertSecurityGroup(computer,
        [self.user_id, 'G-COMPANY', shadow_user_id,
         person.getUserId(), computer.getUserId()], False)
    self.assertRoles(computer, shadow_user_id, ['Auditor'])
    self.assertRoles(computer, self.user_id, ['Owner'])
    self.assertRoles(computer, computer.getUserId(), ['Assignor'])

    # open/friend
    friend_reference = 'TESTPERSON-%s' % self.generateNewId()
    friend_person = self.portal.person_module.newContent(portal_type='Person',
        reference=friend_reference)
    computer.edit(allocation_scope='open/friend',
        destination_section=friend_person.getRelativeUrl()
    )
    computer.updateLocalRolesOnSecurityGroups()
    shadow_friend_user_id = 'SHADOW-%s' % friend_person.getUserId()
    self.assertSecurityGroup(computer,
        [self.user_id, 'G-COMPANY', shadow_friend_user_id,
         person.getUserId(), computer.getUserId()], False)
    self.assertRoles(computer, shadow_friend_user_id, ['Auditor'])
    self.assertRoles(computer, self.user_id, ['Owner'])
    self.assertRoles(computer, computer.getUserId(), ['Assignor'])


  def test_selfComputer(self):
    reference = 'TESTCOMP-%s' % self.generateNewId()
    computer = self.portal.computer_module.newContent(portal_type='Computer',
        reference=reference)
    computer.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(computer,
        [self.user_id, 'G-COMPANY', computer.getUserId()], False)
    self.assertRoles(computer, computer.getUserId(), ['Assignor'])
    self.assertRoles(computer, self.user_id, ['Owner'])

class TestComputerModel(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    model = self.portal.computer_model_module.newContent(
        portal_type='Computer Model')
    model.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(model,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(model, 'G-COMPANY', ['Assignor'])
    self.assertRoles(model, self.user_id, ['Owner'])

  def test_ComputerAgent(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    model = self.portal.computer_model_module.newContent(
        portal_type='Computer Model',
        source_administration=person.getRelativeUrl())
    model.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(model,
        ['G-COMPANY', self.user_id, person.getUserId()], False)
    self.assertRoles(model, person.getUserId(), ['Assignee'])
    self.assertRoles(model, self.user_id, ['Owner'])

class TestComputerModelModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.computer_model_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-MEMBER', self.user_id], False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestComputerModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.computer_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-COMPUTER', 'R-MEMBER', 'R-SHADOW-PERSON', self.user_id],
        False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(module, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestComputerNetwork(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    network = self.portal.computer_network_module.newContent(
        portal_type='Computer Network')
    network.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(network,
        ['G-COMPANY', 'R-SHADOW-PERSON', self.user_id], False)
    self.assertRoles(network, 'G-COMPANY', ['Assignor'])
    self.assertRoles(network, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(network, self.user_id, ['Assignee', 'Owner'])

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
        ['G-COMPANY', 'R-SHADOW-PERSON', self.user_id, person.getUserId()], False)
    self.assertRoles(network, person.getUserId(), ['Assignee'])
    self.assertRoles(network, self.user_id, ['Assignee', 'Owner'])

class TestComputerNetworkModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.computer_network_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-MEMBER', 'R-SHADOW-PERSON', self.user_id], False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

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
        [self.user_id, instance_customer.getUserId(), slave_customer.getUserId(),
          instance_subscription_reference], True)
    self.assertRoles(partition, instance_customer.getUserId(), ['Auditor'])
    self.assertRoles(partition, slave_customer.getUserId(), ['Auditor'])
    self.assertRoles(partition, instance_subscription_reference, ['Auditor'])
    self.assertRoles(partition, self.user_id, ['Owner'])

  test_SoftwareInstanceGroupRelatedToComputerPartition = \
      test_CustomerOfThePartition

class TestCredentialUpdateModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.credential_update_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        [self.user_id, 'R-MEMBER', 'G-COMPANY'], False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestDataSet(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    data_set = self.portal.data_set_module.newContent(portal_type='Data Set')
    data_set.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(data_set,
        [self.user_id, 'G-COMPANY', 'R-COMPUTER', 'R-INSTANCE', 'R-MEMBER'],
        False)
    self.assertRoles(data_set, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(data_set, 'R-INSTANCE', ['Auditor'])
    self.assertRoles(data_set, 'R-MEMBER', ['Auditor'])
    self.assertRoles(data_set, 'G-COMPANY', ['Assignor'])
    self.assertRoles(data_set, self.user_id, ['Owner'])

class TestDataSetModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.data_set_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-COMPUTER', 'R-INSTANCE', 'R-MEMBER', self.user_id], False)
    self.assertRoles(module, 'R-COMPUTER', ['Author'])
    self.assertRoles(module, 'R-INSTANCE', ['Author'])
    self.assertRoles(module, 'R-MEMBER', ['Author'])
    self.assertRoles(module, 'G-COMPANY', ['Author', 'Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestDocumentModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.document_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['R-COMPUTER', 'R-INSTANCE', 'R-MEMBER', self.user_id, 'G-COMPANY'], False)
    self.assertRoles(module, 'R-COMPUTER', ['Author'])
    self.assertRoles(module, 'R-INSTANCE', ['Author'])
    self.assertRoles(module, 'R-MEMBER', ['Author'])
    self.assertRoles(module, 'G-COMPANY', ['Author', 'Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestDrawing(TestSlapOSGroupRoleSecurityMixin):
  def test_SecurityForShacache(self):
    drawing = self.portal.document_module.newContent(portal_type='Drawing')
    drawing.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(drawing,
        ['G-COMPANY', self.user_id, 'R-COMPUTER', 'R-INSTANCE', 'R-MEMBER'],
        False)
    self.assertRoles(drawing, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(drawing, 'R-INSTANCE', ['Auditor'])
    self.assertRoles(drawing, 'R-MEMBER', ['Auditor'])
    self.assertRoles(drawing, 'G-COMPANY', ['Assignor'])
    self.assertRoles(drawing, self.user_id, ['Owner'])

  test_GroupCompany = test_SecurityForShacache

class TestFile(TestSlapOSGroupRoleSecurityMixin):
  def test_SecurityForShacache(self):
    file_ = self.portal.document_module.newContent(portal_type='File')
    file_.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(file_,
        ['G-COMPANY', self.user_id, 'R-COMPUTER', 'R-INSTANCE', 'R-MEMBER'],
        False)
    self.assertRoles(file_, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(file_, 'R-INSTANCE', ['Auditor'])
    self.assertRoles(file_, 'R-MEMBER', ['Auditor'])
    self.assertRoles(file_, 'G-COMPANY', ['Assignor'])
    self.assertRoles(file_, self.user_id, ['Owner'])

  test_GroupCompany = test_SecurityForShacache

class TestHostingSubscription(TestSlapOSGroupRoleSecurityMixin):
  def test_RelatedSoftwareInstanceGroup(self):
    reference = 'TESTHS-%s' % self.generateNewId()
    subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription', reference=reference)
    subscription.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(subscription, [self.user_id, reference,
        'G-COMPANY'], False)
    self.assertRoles(subscription, reference, ['Assignor'])
    self.assertRoles(subscription, self.user_id, ['Owner'])
    self.assertRoles(subscription, 'G-COMPANY', ['Assignor'])

  def test_CustomOfTheHostingSubscription(self):
    customer_reference = 'TESTPERSON-%s' % self.generateNewId()
    customer = self.portal.person_module.newContent(
        portal_type='Person', reference=customer_reference)
    reference = 'TESTHS-%s' % self.generateNewId()
    subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription', reference=reference,
        destination_section=customer.getRelativeUrl())
    subscription.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(subscription, [self.user_id, reference,
        customer.getUserId(), 'G-COMPANY'], False)
    self.assertRoles(subscription, reference, ['Assignor'])
    self.assertRoles(subscription, customer.getUserId(), ['Assignee'])
    self.assertRoles(subscription, self.user_id, ['Owner'])
    self.assertRoles(subscription, 'G-COMPANY', ['Assignor'])

class TestHostingSubscriptionModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.hosting_subscription_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-COMPUTER', 'R-MEMBER', 'R-INSTANCE', self.user_id], False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(module, 'R-INSTANCE', ['Auditor'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestImage(TestSlapOSGroupRoleSecurityMixin):
  def test_SecurityForShacache(self):
    image = self.portal.image_module.newContent(portal_type='Image')
    image.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(image,
        ['G-COMPANY', self.user_id, 'R-COMPUTER', 'R-INSTANCE', 'R-MEMBER'],
        False)
    self.assertRoles(image, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(image, 'R-INSTANCE', ['Auditor'])
    self.assertRoles(image, 'R-MEMBER', ['Auditor'])
    self.assertRoles(image, 'G-COMPANY', ['Assignor'])
    self.assertRoles(image, self.user_id, ['Owner'])

  test_GroupCompany = test_SecurityForShacache

class TestImageModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.image_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['R-COMPUTER', 'R-INSTANCE', 'R-MEMBER', self.user_id, 'G-COMPANY'], False)
    self.assertRoles(module, 'R-COMPUTER', ['Author'])
    self.assertRoles(module, 'R-INSTANCE', ['Author'])
    self.assertRoles(module, 'R-MEMBER', ['Author'])
    self.assertRoles(module, 'G-COMPANY', ['Author', 'Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestOrganisation(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    organisation = self.portal.organisation_module.newContent(
        portal_type='Organisation')
    organisation.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(organisation,
        ['G-COMPANY', self.user_id, 'R-MEMBER', 'R-SHADOW-PERSON'], False)
    self.assertRoles(organisation, 'G-COMPANY', ['Assignor'])
    self.assertRoles(organisation, 'R-MEMBER', ['Auditor'])
    self.assertRoles(organisation, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(organisation, self.user_id, ['Owner', 'Assignee'])

  test_Member = test_GroupCompany

class TestOrganisationModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.organisation_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-COMPUTER', 'R-MEMBER', self.user_id, 'R-SHADOW-PERSON'], False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestProjectModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.project_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-COMPUTER', 'R-MEMBER', self.user_id, 'R-SHADOW-PERSON'], True)
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestProject(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    project = self.portal.project_module.newContent(
        portal_type='Project')
    project.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(project,
        ['G-COMPANY', self.user_id, 'R-MEMBER', 'R-SHADOW-PERSON'], False)
    self.assertRoles(project, 'G-COMPANY', ['Assignor'])
    self.assertRoles(project, 'R-MEMBER', ['Auditor'])
    self.assertRoles(project, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(project, self.user_id, ['Owner', 'Assignee'])

class TestPDF(TestSlapOSGroupRoleSecurityMixin):
  def test_SecurityForShacache(self):
    pdf = self.portal.document_module.newContent(portal_type='PDF')
    pdf.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(pdf,
        ['G-COMPANY', self.user_id, 'R-COMPUTER', 'R-INSTANCE', 'R-MEMBER'],
        False)
    self.assertRoles(pdf, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(pdf, 'R-INSTANCE', ['Auditor'])
    self.assertRoles(pdf, 'R-MEMBER', ['Auditor'])
    self.assertRoles(pdf, 'G-COMPANY', ['Assignor'])
    self.assertRoles(pdf, self.user_id, ['Owner'])

  test_GroupCompany = test_SecurityForShacache

class TestPerson(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    person = self.portal.person_module.newContent(portal_type='Person')
    person.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(person,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(person, 'G-COMPANY', ['Assignor'])
    self.assertRoles(person, self.user_id, ['Owner'])

  def test_TheUserHimself(self, login_portal_type="ERP5 Login"):
    person = self.portal.person_module.newContent(portal_type='Person')
    person.newContent(portal_type=login_portal_type)
    person.updateLocalRolesOnSecurityGroups()

    shadow_reference = 'SHADOW-%s' % person.getUserId()
    self.assertSecurityGroup(person,
        ['G-COMPANY', self.user_id, person.getUserId(), shadow_reference], False)
    self.assertRoles(person, 'G-COMPANY', ['Assignor'])
    self.assertRoles(person, person.getUserId(), ['Associate'])
    self.assertRoles(person, shadow_reference, ['Auditor'])
    self.assertRoles(person, self.user_id, ['Owner'])

  # XXX Uncommment once facebook and google login be merged.
  # def test_TheUserHimself_Facebook(self):
  #   self.test_TheUserHimself(login_portal_type="Facebook Login")

  # def test_TheUserHimself_Google(self):
  #   self.test_TheUserHimself(login_portal_type="Google Login")

class TestPersonModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.person_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-MEMBER', self.user_id, 'R-SHADOW-PERSON'], False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestPresentation(TestSlapOSGroupRoleSecurityMixin):
  def test_SecurityForShacache(self):
    presentation = self.portal.document_module.newContent(
        portal_type='Presentation')
    presentation.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(presentation,
        ['G-COMPANY', self.user_id, 'R-COMPUTER', 'R-INSTANCE', 'R-MEMBER'],
        False)
    self.assertRoles(presentation, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(presentation, 'R-INSTANCE', ['Auditor'])
    self.assertRoles(presentation, 'R-MEMBER', ['Auditor'])
    self.assertRoles(presentation, 'G-COMPANY', ['Assignor'])
    self.assertRoles(presentation, self.user_id, ['Owner'])

  test_GroupCompany = test_SecurityForShacache

class TestSlaveInstance(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    instance = self.portal.software_instance_module.newContent(
        portal_type='Slave Instance')
    instance.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(instance, ['G-COMPANY', self.user_id], False)
    self.assertRoles(instance, 'G-COMPANY', ['Assignor'])
    self.assertRoles(instance, self.user_id, ['Owner', 'Assignee'])

  test_OwnerBecomeAssignee = test_GroupCompany

  def test_CustomerOfTheInstance(self):
    customer_reference = 'TESTPERSON-%s' % self.generateNewId()
    customer = self.portal.person_module.newContent(
        portal_type='Person', reference=customer_reference)

    subscription_reference = 'TESTHS-%s ' % self.generateNewId()
    subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription',
        reference=subscription_reference,
        destination_section=customer.getRelativeUrl())

    instance = self.portal.software_instance_module.newContent(
        portal_type='Slave Instance', specialise=subscription.getRelativeUrl())
    instance.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(instance, ['G-COMPANY', customer.getUserId(),
        subscription_reference, self.user_id], False)
    self.assertRoles(instance, 'G-COMPANY', ['Assignor'])
    self.assertRoles(instance, customer.getUserId(), ['Assignee'])
    self.assertRoles(instance, subscription_reference, ['Assignor'])
    self.assertRoles(instance, self.user_id, ['Owner', 'Assignee'])

  test_InstanceRelatedByHostingSubscription = test_CustomerOfTheInstance

  def test_SoftwareInstanceWhichProvidesThisSlaveInstance(self):
    computer_reference = 'TESTCOMP-%s' % self.generateNewId()
    computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    computer.edit(reference=computer_reference)
    partition = computer.newContent(portal_type='Computer Partition')

    provider_reference = 'TESTSI-%s' % self.generateNewId()

    provider = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)

    provider.edit(reference=provider_reference,
        aggregate=partition.getRelativeUrl())
    provider.validate()

    provider.recursiveImmediateReindexObject()
    partition.recursiveImmediateReindexObject()

    instance = self.portal.software_instance_module.newContent(
        portal_type='Slave Instance', aggregate=partition.getRelativeUrl())
    instance.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(instance, ['G-COMPANY', provider.getUserId(),
        computer.getUserId(), self.user_id], False)
    self.assertRoles(instance, 'G-COMPANY', ['Assignor'])
    self.assertRoles(instance, provider.getUserId(), ['Assignor'])
    self.assertRoles(instance, computer.getUserId(), ['Assignor'])
    self.assertRoles(instance, self.user_id, ['Owner', 'Assignee'])

  test_Computer = test_SoftwareInstanceWhichProvidesThisSlaveInstance

class TestSoftwareInstallation(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    installation = self.portal.software_installation_module.newContent(
        portal_type='Software Installation')
    installation.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(installation, [self.user_id,
        'G-COMPANY'], False)
    self.assertRoles(installation, 'G-COMPANY', ['Assignor'])
    self.assertRoles(installation, self.user_id, ['Owner', 'Assignee'])

  test_OwnerBecomeAssignee = test_GroupCompany

  def test_Computer(self):
    computer_reference = 'TESTCOMP-%s' % self.generateNewId()
    computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    computer.edit(reference=computer_reference)

    installation = self.portal.software_installation_module.newContent(
        portal_type='Software Installation',
        aggregate=computer.getRelativeUrl())
    installation.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(installation, [self.user_id,
        'G-COMPANY', computer.getUserId()], False)
    self.assertRoles(installation, 'G-COMPANY', ['Assignor'])
    self.assertRoles(installation, computer.getUserId(), ['Assignor'])
    self.assertRoles(installation, self.user_id, ['Owner', 'Assignee'])

  def test_ProviderOfTheInstallation(self):
    provider_reference = 'TESTPERSON-%s' % self.generateNewId()
    provider = self.portal.person_module.newContent(
        portal_type='Person', reference=provider_reference)

    installation = self.portal.software_installation_module.newContent(
        portal_type='Software Installation',
        destination_section=provider.getRelativeUrl())
    installation.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(installation, [self.user_id,
        'G-COMPANY', provider.getUserId()], False)
    self.assertRoles(installation, 'G-COMPANY', ['Assignor'])
    self.assertRoles(installation, provider.getUserId(), ['Assignee'])
    self.assertRoles(installation, self.user_id, ['Owner', 'Assignee'])

class TestSoftwareInstallationModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.software_installation_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-MEMBER', 'R-COMPUTER', self.user_id], False)
    self.assertRoles(module, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestSoftwareInstance(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    instance = self.portal.software_instance_module.newContent(
        portal_type='Software Instance')
    instance.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(instance, ['G-COMPANY', self.user_id], False)
    self.assertRoles(instance, 'G-COMPANY', ['Assignor'])
    self.assertRoles(instance, self.user_id, ['Owner', 'Assignee'])

  test_OwnerBecomeAssignee = test_GroupCompany

  def test_CustomerOfTheInstance(self):
    customer_reference = 'TESTPERSON-%s' % self.generateNewId()
    customer = self.portal.person_module.newContent(
        portal_type='Person', reference=customer_reference)

    subscription_reference = 'TESTHS-%s ' % self.generateNewId()
    subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription',
        reference=subscription_reference,
        destination_section=customer.getRelativeUrl())

    instance = self.portal.software_instance_module.newContent(
        portal_type='Software Instance', specialise=subscription.getRelativeUrl())
    instance.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(instance, ['G-COMPANY', customer.getUserId(),
        subscription_reference, self.user_id], False)
    self.assertRoles(instance, 'G-COMPANY', ['Assignor'])
    self.assertRoles(instance, customer.getUserId(), ['Assignee'])
    self.assertRoles(instance, subscription_reference, ['Assignor'])
    self.assertRoles(instance, self.user_id, ['Owner', 'Assignee'])

  test_InstanceRelatedByHostingSubscription = test_CustomerOfTheInstance

  def test_Computer(self):
    computer_reference = 'TESTCOMP-%s' % self.generateNewId()
    computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    computer.edit(reference=computer_reference)
    partition = computer.newContent(portal_type='Computer Partition')

    partition.recursiveImmediateReindexObject()

    instance = self.portal.software_instance_module.newContent(
        portal_type='Software Instance', aggregate=partition.getRelativeUrl())
    instance.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(instance, ['G-COMPANY', computer.getUserId(),
        self.user_id], False)
    self.assertRoles(instance, 'G-COMPANY', ['Assignor'])
    self.assertRoles(instance, computer.getUserId(), ['Assignor'])
    self.assertRoles(instance, self.user_id, ['Owner', 'Assignee'])

class TestSoftwareInstanceModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.software_instance_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-COMPUTER', 'R-INSTANCE', 'R-MEMBER', self.user_id], False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(module, 'R-INSTANCE', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestSoftwareProduct(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.software_product_module.newContent(
        portal_type='Software Product')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', 'R-MEMBER', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, 'R-MEMBER', ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  test_Member = test_GroupCompany

class TestSoftwareProductModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.software_product_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-MEMBER', self.user_id], False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestSoftwareRelease(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    release = self.portal.software_release_module.newContent(
        portal_type='Software Release')
    release.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(release,
        ['G-COMPANY', 'R-MEMBER', self.user_id], False)
    self.assertRoles(release, 'G-COMPANY', ['Assignor'])
    self.assertRoles(release, 'R-MEMBER', ['Auditor'])
    self.assertRoles(release, self.user_id, ['Owner'])

  test_Member = test_GroupCompany

class TestSoftwareReleaseModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.software_release_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-MEMBER', self.user_id], False)
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestSpreadsheet(TestSlapOSGroupRoleSecurityMixin):
  def test_SecurityForShacache(self):
    spreadsheet = self.portal.document_module.newContent(
        portal_type='Spreadsheet')
    spreadsheet.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(spreadsheet,
        ['G-COMPANY', self.user_id, 'R-COMPUTER', 'R-INSTANCE', 'R-MEMBER'],
        False)
    self.assertRoles(spreadsheet, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(spreadsheet, 'R-INSTANCE', ['Auditor'])
    self.assertRoles(spreadsheet, 'R-MEMBER', ['Auditor'])
    self.assertRoles(spreadsheet, 'G-COMPANY', ['Assignor'])
    self.assertRoles(spreadsheet, self.user_id, ['Owner'])

  test_GroupCompany = test_SecurityForShacache

class TestText(TestSlapOSGroupRoleSecurityMixin):
  def test_SecurityForShacache(self):
    text = self.portal.document_module.newContent(
        portal_type='Text')
    text.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(text,
        ['G-COMPANY', self.user_id, 'R-COMPUTER', 'R-INSTANCE', 'R-MEMBER'],
        False)
    self.assertRoles(text, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(text, 'R-INSTANCE', ['Auditor'])
    self.assertRoles(text, 'R-MEMBER', ['Auditor'])
    self.assertRoles(text, 'G-COMPANY', ['Assignor'])
    self.assertRoles(text, self.user_id, ['Owner'])

  test_GroupCompany = test_SecurityForShacache

class TestContributionTool(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.portal_contributions
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['R-COMPUTER', 'R-INSTANCE', 'R-MEMBER', self.user_id, 'G-COMPANY'], True)
    self.assertRoles(module, 'R-COMPUTER', ['Author'])
    self.assertRoles(module, 'R-INSTANCE', ['Author'])
    self.assertRoles(module, 'R-MEMBER', ['Author'])
    self.assertRoles(module, 'G-COMPANY', ['Author', 'Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestOpenSaleOrderModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.open_sale_order_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestOpenSaleOrder(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.open_sale_order_module.newContent(
        portal_type='Open Sale Order')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestSaleOrderModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.sale_order_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestSaleOrder(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.sale_order_module.newContent(
        portal_type='Sale Order')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestSalePackingListModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.sale_packing_list_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id, 'R-MEMBER'], False)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor'])

class TestSalePackingList(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_GroupCustomerSubscription(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List',
        destination_decision_value=person,
        specialise_value=self.portal.sale_trade_condition_module.\
                           slapos_subscription_trade_condition,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, person.getUserId()], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])

  def test_GroupCustomerAggregation(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List',
        destination_decision_value=person,
        specialise_value=self.portal.sale_trade_condition_module.\
                           slapos_aggregated_trade_condition,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, person.getUserId()], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])

class TestAccountingTransactionModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.accounting_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id, 'R-SHADOW-PERSON', 'R-MEMBER'], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-SHADOW-PERSON', ['Assignor'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestAccountingTransaction(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.accounting_module.newContent(
        portal_type='Accounting Transaction')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestBalanceTransaction(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.accounting_module.newContent(
        portal_type='Balance Transaction')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestPaymentTransaction(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.accounting_module.newContent(
        portal_type='Payment Transaction')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, 'R-SHADOW-PERSON'], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_ShadowUser(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.accounting_module.newContent(
        portal_type='Payment Transaction')
    product.edit(
        destination_section_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    shadow_user_id = 'SHADOW-%s' % person.getUserId()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, person.getUserId(), shadow_user_id, 
         'R-SHADOW-PERSON'], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, shadow_user_id, ['Auditor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_User(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.accounting_module.newContent(
        portal_type='Payment Transaction')
    product.edit(
        destination_section_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    shadow_user_id = 'SHADOW-%s' % person.getUserId()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, person.getUserId(),
         shadow_user_id, 'R-SHADOW-PERSON'], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, shadow_user_id, ['Auditor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestPurchaseInvoiceTransaction(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.accounting_module.newContent(
        portal_type='Purchase Invoice Transaction')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestSaleInvoiceTransaction(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.accounting_module.newContent(
        portal_type='Sale Invoice Transaction')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, 'R-SHADOW-PERSON'], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_User(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.accounting_module.newContent(
        portal_type='Sale Invoice Transaction')
    product.edit(
        destination_section_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, person.getUserId(), 
         'R-SHADOW-PERSON'], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestServiceModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.service_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id, 'R-MEMBER'], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestService(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.service_module.newContent(
        portal_type='Service')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, 'R-MEMBER'], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, 'R-MEMBER', ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestAccountModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.account_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id, 'R-SHADOW-PERSON', 'R-MEMBER'], False)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestAccount(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.account_module.newContent(
        portal_type='Account')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, 'R-SHADOW-PERSON', 'R-MEMBER'], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(product, 'R-MEMBER', ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestCurrencyModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.currency_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id, 'R-SHADOW-PERSON', 'R-MEMBER'], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestCurrency(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.currency_module.newContent(
        portal_type='Currency')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, 'R-SHADOW-PERSON', 'R-MEMBER'], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(product, 'R-MEMBER', ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestSaleTradeConditionModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.sale_trade_condition_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id, 'R-MEMBER'], False)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestSaleTradeCondition(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.sale_trade_condition_module.newContent(
        portal_type='Sale Trade Condition')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, 'R-MEMBER'], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, 'R-MEMBER', ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestAccountingPeriod(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.organisation_module.newContent(
        portal_type='Organisation').newContent(
        portal_type='Accounting Period')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestAcknowledgement(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.event_module.newContent(
        portal_type='Acknowledgement')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_SourceCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Acknowledgement',
        source_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_DestinationCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Acknowledgement',
        destination_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestBankAccount(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.organisation_module.newContent(
        portal_type='Organisation').newContent(
        portal_type='Bank Account')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestCampaignModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.campaign_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestCampaign(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.campaign_module.newContent(
        portal_type='Campaign')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestCashRegister(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.organisation_module.newContent(
        portal_type='Organisation').newContent(
        portal_type='Cash Register')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestComponentModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.component_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestComponent(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.component_module.newContent(
        portal_type='Component')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestCreditCard(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.organisation_module.newContent(
        portal_type='Organisation').newContent(
        portal_type='Credit Card')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestDocumentIngestionModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.document_ingestion_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestEventModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.event_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-MEMBER', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestFaxMessage(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.event_module.newContent(
        portal_type='Fax Message')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_SourceCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Fax Message',
        source_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_DestinationCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Fax Message',
        destination_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestGadget(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.portal_gadgets.newContent(
        portal_type='Gadget')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestGadgetTool(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.portal_gadgets
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestInventory(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.inventory_module.newContent(
        portal_type='Inventory')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestInventoryModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.inventory_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestKnowledgeBox(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.knowledge_pad_module.newContent(
        portal_type='Knowledge Pad').newContent(
        portal_type='Knowledge Box')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestKnowledgePad(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.knowledge_pad_module.newContent(
        portal_type='Knowledge Pad')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestKnowledgePadModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.knowledge_pad_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestLetter(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.event_module.newContent(
        portal_type='Letter')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_SourceCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Letter',
        source_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_DestinationCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Letter',
        destination_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestMailMessage(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.event_module.newContent(
        portal_type='Mail Message')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_SourceCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Mail Message',
        source_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_DestinationCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Mail Message',
        destination_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestMeeting(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.meeting_module.newContent(
        portal_type='Meeting')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestMeetingModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.meeting_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestNote(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.event_module.newContent(
        portal_type='Note')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_SourceCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Note',
        source_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_DestinationCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Note',
        destination_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestPhoneCall(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.event_module.newContent(
        portal_type='Phone Call')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_SourceCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Phone Call',
        source_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_DestinationCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Phone Call',
        destination_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestVisit(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.event_module.newContent(
        portal_type='Visit')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_SourceCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Visit',
        source_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_DestinationCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Visit',
        destination_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestNotificationMessageModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.notification_message_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestNotificationMessage(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.notification_message_module.newContent(
        portal_type='Notification Message')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestProductModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.product_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestProduct(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.product_module.newContent(
        portal_type='Product')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestPurchaseOrderModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.purchase_order_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestPurchaseOrder(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.purchase_order_module.newContent(
        portal_type='Purchase Order')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestPurchaseTradeConditionModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.purchase_trade_condition_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestPurchaseTradeCondition(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.purchase_trade_condition_module.newContent(
        portal_type='Purchase Trade Condition')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestQueryModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.query_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestQuery(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.query_module.newContent(
        portal_type='Query')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestSaleOpportunityModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.sale_opportunity_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestSaleOpportunity(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.sale_opportunity_module.newContent(
        portal_type='Sale Opportunity')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestShortMessage(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.event_module.newContent(
        portal_type='Short Message')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_SourceCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Short Message',
        source_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_DestinationCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Short Message',
        destination_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestSiteMessage(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.event_module.newContent(
        portal_type='Site Message')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_SourceCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Site Message',
        source_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_DestinationCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Site Message',
        destination_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestWebMessage(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.event_module.newContent(
        portal_type='Web Message')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_SourceCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Web Message',
        source_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_DestinationCustomer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.event_module.newContent(
        portal_type='Web Message',
        destination_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_Template(self):
    product = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredWebMessageTemplate())
    assert product.getPortalType() == 'Web Message'
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', product.Base_getOwnerId(), 'R-MEMBER'], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, product.Base_getOwnerId(), ['Owner'])
    self.assertRoles(product, 'R-MEMBER', ['Auditor'])
    self.assertPermissionsOfRole(product, 'Auditor',
        ['Access contents information', 'View'])

class TestSupportRequestModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.support_request_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-MEMBER', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestSupportRequest(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.support_request_module.newContent(
        portal_type='Support Request')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_Customer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.support_request_module.newContent(
        portal_type='Support Request',
        destination_decision_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_Template(self):
    product = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredSupportRequestTemplate())
    assert product.getPortalType() == 'Support Request'
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', product.Base_getOwnerId(), 'R-MEMBER'], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, product.Base_getOwnerId(), ['Owner'])
    self.assertRoles(product, 'R-MEMBER', ['Auditor'])
    self.assertPermissionsOfRole(product, 'Auditor',
        ['Access contents information', 'View'])

class TestTransformationModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.transformation_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestTransformation(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.transformation_module.newContent(
        portal_type='Transformation')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestWebPageModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.web_page_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestWebPage(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.web_page_module.newContent(
        portal_type='Web Page')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestIntegrationTool(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.portal_integrations
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['R-SHADOW-PERSON', 'ERP5TypeTestCase', 'G-COMPANY'], False)
    self.assertRoles(module, 'R-SHADOW-PERSON', ['Auditor'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'ERP5TypeTestCase', ['Owner'])

class TestIntegrationSite(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.portal_integrations
    self.changeOwnership(module)
    product = module.newContent(
        portal_type='Integration Site')
    self.assertSecurityGroup(product,
        ['R-SHADOW-PERSON', self.user_id, 'G-COMPANY'], False)
    self.assertRoles(product, 'R-SHADOW-PERSON', ['Auditor', 'Author'])
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestSystemEventModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.system_event_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['R-SHADOW-PERSON', self.user_id, 'G-COMPANY'], False)
    self.assertRoles(module, 'R-SHADOW-PERSON', ['Author'])
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestPayzenEvent(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.system_event_module.newContent(
        portal_type='Payzen Event')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_ShadowUser(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.system_event_module.newContent(
        portal_type='Payzen Event')
    product.edit(
        destination_section_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    shadow_user_id = 'SHADOW-%s' % person.getUserId()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, shadow_user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, shadow_user_id, ['Assignee'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestSecurePaymentTool(TestSlapOSGroupRoleSecurityMixin):
  def test_no_permissions_for_users(self):
    tool = self.portal.portal_secure_payments
    self.assertPermissionsOfRole(tool, 'Anonymous', [])
    self.assertPermissionsOfRole(tool, 'Assignee', [])
    self.assertPermissionsOfRole(tool, 'Assignor', [])
    self.assertPermissionsOfRole(tool, 'Associate', [])
    self.assertPermissionsOfRole(tool, 'Auditor', [])
    self.assertPermissionsOfRole(tool, 'Authenticated', [])
    self.assertPermissionsOfRole(tool, 'Author', [])
    self.assertPermissionsOfRole(tool, 'Member', [])
    self.assertPermissionsOfRole(tool, 'Owner', [])
    self.assertPermissionsOfRole(tool, 'Reviewer', [])

    self.assertAcquiredPermissions(tool, ['Add ERP5 SQL Methods', 'Add Vifib Tools'])

class TestBusinessProcessModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.business_process_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', self.user_id, 'R-MEMBER'], False)
    self.assertRoles(module, 'G-COMPANY', ['Auditor'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestBusinessProcess(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.business_process_module.newContent(
        portal_type='Business Process')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id, 'R-MEMBER'], False)
    self.assertRoles(product, 'G-COMPANY', ['Auditor'])
    self.assertRoles(product, 'R-MEMBER', ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestRegularisationRequestModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.regularisation_request_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-MEMBER', self.user_id], False)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestRegularisationRequest(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.regularisation_request_module.newContent(
        portal_type='Regularisation Request')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_Customer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.regularisation_request_module.newContent(
        portal_type='Regularisation Request',
        destination_decision_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Auditor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_Template(self):
    product = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredRegularisationRequestTemplate())
    assert product.getPortalType() == 'Regularisation Request'
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', product.Base_getOwnerId(), 'R-MEMBER'], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, product.Base_getOwnerId(), ['Owner'])
    self.assertRoles(product, 'R-MEMBER', ['Auditor'])
    self.assertPermissionsOfRole(product, 'Auditor',
        ['Access contents information', 'View'])

class TestAccessTokenModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.access_token_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-MEMBER', self.user_id], False)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-MEMBER', ['Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestOneTimeRestrictedAccessToken(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.access_token_module.newContent(
        portal_type='One Time Restricted Access Token')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestRestrictedAccessToken(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.access_token_module.newContent(
        portal_type='Restricted Access Token')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

class TestConsumptionDocumentModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.consumption_document_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['R-COMPUTER', 'R-MEMBER', self.user_id, 'G-COMPANY'], False)
    self.assertRoles(module, 'R-COMPUTER', ['Author'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, 'G-COMPANY', ['Author', 'Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestComputerConsumptionTioXMLFile(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    text = self.portal.consumption_document_module.newContent(
        portal_type='Computer Consumption TioXML File')

    self.assertSecurityGroup(text,
        ['G-COMPANY', self.user_id],
        False)
    self.assertRoles(text, 'G-COMPANY', ['Assignor'])
    self.assertRoles(text, self.user_id, ['Owner'])

class TestUserConsumptionHTMLFile(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    text = self.portal.consumption_document_module.newContent(
        portal_type='User Consumption HTML File')

    self.assertSecurityGroup(text,
        ['G-COMPANY', self.user_id],
        False)
    self.assertRoles(text, 'G-COMPANY', ['Assignor'])
    self.assertRoles(text, self.user_id, ['Owner'])

  def test_CustomerAssignee(self):
    customer_reference = 'TESTPERSON-%s' % self.generateNewId()
    customer = self.portal.person_module.newContent(
        portal_type='Person', reference=customer_reference)
    reference = 'TESTRC-%s' % self.generateNewId()
    html_document = self.portal.consumption_document_module.newContent(
        portal_type='User Consumption HTML File', reference=reference,
        contributor=customer.getRelativeUrl())
    html_document.updateLocalRolesOnSecurityGroups()

    self.assertSecurityGroup(html_document,
        ['G-COMPANY', customer.getUserId(), self.user_id], False)
    self.assertRoles(html_document, 'G-COMPANY', ['Assignor'])
    self.assertRoles(html_document, customer.getUserId(), ['Assignee'])
    self.assertRoles(html_document, self.user_id, ['Owner'])

class TestCloudContractModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.cloud_contract_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        [self.user_id, 'G-COMPANY'], False)
    self.assertRoles(module, 'G-COMPANY', ['Author', 'Auditor'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestCloudContract(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    text = self.portal.cloud_contract_module.newContent(
        portal_type='Cloud Contract')

    self.assertSecurityGroup(text,
        ['G-COMPANY', self.user_id],
        False)
    self.assertRoles(text, 'G-COMPANY', ['Assignor'])
    self.assertRoles(text, self.user_id, ['Owner'])

class TestUpgradeDecisionModule(TestSlapOSGroupRoleSecurityMixin):
  def test(self):
    module = self.portal.upgrade_decision_module
    self.changeOwnership(module)
    self.assertSecurityGroup(module,
        ['G-COMPANY', 'R-MEMBER', self.user_id], True)
    self.assertRoles(module, 'G-COMPANY', ['Auditor', 'Author'])
    self.assertRoles(module, 'R-MEMBER', ['Auditor', 'Author'])
    self.assertRoles(module, self.user_id, ['Owner'])

class TestUpgradeDecision(TestSlapOSGroupRoleSecurityMixin):
  def test_GroupCompany(self):
    product = self.portal.upgrade_decision_module.newContent(
        portal_type='Upgrade Decision')
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, self.user_id, ['Owner'])

  def test_Customer(self):
    reference = 'TESTPERSON-%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
        reference=reference)
    product = self.portal.upgrade_decision_module.newContent(
        portal_type='Upgrade Decision',
        destination_decision_value=person,
        )
    product.updateLocalRolesOnSecurityGroups()
    self.assertSecurityGroup(product,
        ['G-COMPANY', person.getUserId(), self.user_id], False)
    self.assertRoles(product, 'G-COMPANY', ['Assignor'])
    self.assertRoles(product, person.getUserId(), ['Assignee'])
    self.assertRoles(product, self.user_id, ['Owner'])
