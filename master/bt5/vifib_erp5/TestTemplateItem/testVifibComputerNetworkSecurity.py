# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
import unittest
from Products.Vifib.tests.testVifibSlapWebService import \
  TestVifibSlapWebServiceMixin

READ = 'Access contents information'
VIEW = 'View'
ADD = 'Add portal content'
WRITE = 'Modify portal content'
OTHER_AUDITOR = [
  'Access Transient Objects',
  'Access session data',
  'Copy or Move',
  'List folder contents',
  'View History'
  ]
OTHER_AUTHOR = [
  'Add portal folders',
  ]

class TestVifibComputerNetworkSecurity(TestVifibSlapWebServiceMixin):

  def generateNewId(self):
    return self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_core_test'))

  def getTitle(self):
    return "Test Vifib Computer Network Security"

  def createMemberUser(self):
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
    return person_user

  def afterSetUp(self):
    pass

  def beforeTearDown(self):
    pass

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

  def test_ComputerNetworkModuleLocalRoles(self):
    module = self.portal.computer_network_module
    self.assertSecurityGroup(module, ['R-MEMBER', 'ERP5TypeTestCase'], False)
    self.assertRoles(module, 'R-MEMBER', ['Author', 'Auditor'])
    self.assertRoles(module, 'zope', ['Owner'])

  def test_ComputerNetworkModulePermissions(self):
    module = self.portal.computer_network_module
    self.assertPermissionsOfRole(module, 'Owner', [])
    self.assertPermissionsOfRole(module, 'Auditor',
                                 [READ, VIEW] + OTHER_AUDITOR)
    self.assertPermissionsOfRole(module, 'Author',
                                 [READ, ADD] + OTHER_AUDITOR + OTHER_AUTHOR)

  def test_ComputerNetworkLocalRoles(self):
    module = self.portal.computer_network_module
    network = module.newContent(portal_type="Computer Network")

    self.assertSecurityGroup(network, ['ERP5TypeTestCase', 'G-COMPANY'], False)
    self.assertRoles(network, 'ERP5TypeTestCase', ['Owner'])
    self.assertRoles(network, 'G-COMPANY', ['Assignor'])

    # Setting source administration give person the assignee role
    person = self.createMemberUser()
    network.edit(source_administration_value=person)
    self.assertSecurityGroup(network,
        ['ERP5TypeTestCase', 'G-COMPANY', person.getReference()], False)
    self.assertRoles(network, person.getReference(), ['Assignee'])

  def test_ComputerNetworkPermission(self):
    module = self.portal.computer_network_module
    network = module.newContent(portal_type="Computer Network")

    # Check draft state
    self.assertEquals('draft', network.getValidationState())
    self.assertPermissionsOfRole(network, 'Owner',
                                 [READ, VIEW, ADD, WRITE])
    self.assertPermissionsOfRole(network, 'Assignor',
                                 [READ, VIEW, ADD, WRITE])
    self.assertPermissionsOfRole(network, 'Assignee',
                                 [READ, VIEW, ADD, WRITE])

    # Check validated state
    network.validate()
    self.assertEquals('validated', network.getValidationState())
    self.assertPermissionsOfRole(network, 'Owner', [])
    self.assertPermissionsOfRole(network, 'Assignor',
                                 [READ, VIEW, ADD, WRITE])
    self.assertPermissionsOfRole(network, 'Assignee',
                                 [READ, VIEW, ADD, WRITE])

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibComputerNetworkSecurity))
  return suite
