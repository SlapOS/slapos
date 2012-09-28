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

class TestVifibComputerModelSecurity(TestVifibSlapWebServiceMixin):

  def generateNewId(self):
    return self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_core_test'))

  def getTitle(self):
    return "Test Vifib Computer Model Security"

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

  def test_ComputerModelModuleLocalRoles(self):
    module = self.portal.computer_model_module
    self.assertSecurityGroup(module,
        ['R-MEMBER', 'zope'], False)
    self.assertRoles(module, 'R-MEMBER', ['Author', 'Auditor'])
    self.assertRoles(module, 'zope', ['Owner'])

  def test_ComputerModelModulePermissions(self):
    module = self.portal.computer_model_module
    self.assertPermissionsOfRole(module, 'Owner', [])
    self.assertPermissionsOfRole(module, 'Auditor',
                                 [READ, VIEW] + OTHER_AUDITOR)
    self.assertPermissionsOfRole(module, 'Author',
                                 [READ, ADD] + OTHER_AUDITOR + OTHER_AUTHOR)

  def test_ComputerModelLocalRoles(self):
    module = self.portal.computer_model_module
    Model = module.newContent(portal_type="Computer Model")

    self.assertSecurityGroup(Model,
      ['ERP5TypeTestCase', 'G-COMPANY'], False)
    self.assertRoles(Model, 'ERP5TypeTestCase', ['Owner'])
    self.assertRoles(Model, 'G-COMPANY', ['Assignor'])

    # Setting source administration give person the assignee role
    person = self.createMemberUser()
    Model.edit(source_administration_value=person)
    self.assertSecurityGroup(Model,
        ['ERP5TypeTestCase', 'G-COMPANY', person.getReference()], False)
    self.assertRoles(Model, person.getReference(), ['Assignee'])

  def test_ComputerModelPermission(self):
    module = self.portal.computer_model_module
    Model = module.newContent(portal_type="Computer Model")

    # Check draft state
    self.assertEquals('draft', Model.getValidationState())
    self.assertPermissionsOfRole(Model, 'Owner',
                                 [READ, VIEW, ADD, WRITE])
    self.assertPermissionsOfRole(Model, 'Assignor',
                                 [READ, VIEW, ADD, WRITE])
    self.assertPermissionsOfRole(Model, 'Assignee',
                                 [READ, VIEW, ADD, WRITE])

    # Check validated state
    Model.validate()
    self.assertEquals('validated', Model.getValidationState())
    self.assertPermissionsOfRole(Model, 'Owner', [])
    self.assertPermissionsOfRole(Model, 'Assignor',
                                 [READ, VIEW, ADD, WRITE])
    self.assertPermissionsOfRole(Model, 'Assignee',
                                 [READ, VIEW, ADD, WRITE])

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibComputerModelSecurity))
  return suite
