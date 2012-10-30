# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from Products.ERP5Type.tests.SecurityTestCase import SecurityTestCase
from Products.ERP5Type.tests.backportUnittest import expectedFailure
from AccessControl import Unauthorized

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


class TestSlapOSCache(testSlapOSMixin, SecurityTestCase):

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
  
  def test_anonymous_can_not_create_document(self):
    """
      Annonymous should not be able to create any kind of document
      under document_module and image_module.
    """
    self.logout()
    self.assertTrue(self.portal.portal_membership.isAnonymousUser())

    for module in ('image_module', 'document_module',):
      module = getattr(self.portal, module)
      for portal_type in module.getVisibleAllowedContentTypeList():
        def tryToCreateDataSet():
          module.newContent(portal_type=portal_type,
                            reference=self.key)

        self.assertRaises(Unauthorized, tryToCreateDataSet)

  def test_anonymous_can_not_view_document_module(self):
    """
      Anonymous should not be able to view document module.
    """
    self.logout()
    self.assertTrue(self.portal.portal_membership.isAnonymousUser())
    self.assertRaises(Unauthorized, self.portal.document_module.view)
    self.assertRaises(Unauthorized, self.portal.document_module)

  def test_anonymous_can_not_view_image_module(self):
    """
      Anonymous should not be able to view image module.
    """
    self.logout()
    self.assertTrue(self.portal.portal_membership.isAnonymousUser())
    self.assertRaises(Unauthorized, self.portal.image_module.view)
    self.assertRaises(Unauthorized, self.portal.image_module)

  def _createDocumentList(self):
    document_list = []
    self.login()
    self.assertFalse(self.portal.portal_membership.isAnonymousUser())

    for module in ('image_module', 'document_module',):
      module = getattr(self.portal, module)

      for portal_type in module.getVisibleAllowedContentTypeList():
        document = self._getDocumentForTestSecurity(module, portal_type)
        document.updateLocalRolesOnSecurityGroups()

    return document_list

  def test_anonymous_can_not_read_document_list(self):
    """
      Anonymous can not read any document object under document_module
      and image_module.
    """
    document_list = self._createDocumentList()

    self.logout()
    self.assertTrue(self.portal.portal_membership.isAnonymousUser())

    for document in document_list:
      self.assertRaises(Unauthorized, document.view)
      self.assertRaises(Unauthorized, document)

  def _getDocumentForTestSecurity(self, module, portal_type):
    """
      User must be able to create and view any document object under
      document_module and image_module.

      It also must check if document can be published alive.
    """    
    self.login()
    self.assertFalse(self.portal.portal_membership.isAnonymousUser())
    id = "test_document_01_%s" % portal_type
    document = getattr(module, id, None)
    if document is None:
      document = module.newContent(portal_type=portal_type, id=id)

    if document.getValidationState() != "published_alive":
      document.publishAlive()

    return document
  
  def _testDocumentLocalRole(self, module, portal_type):
    document = self._getDocumentForTestSecurity(module, portal_type)
    if portal_type in ["Image", "File"]:
      self.assertSecurityGroup(document, 
          ['ERP5TypeTestCase', 'R-COMPUTER', 
                             'R-INSTANCE', 'R-MEMBER'] , 1)
    else:
      self.assertSecurityGroup(document, 
         ['ERP5TypeTestCase', 'G-COMPANY', 'R-COMPUTER', 
                             'R-INSTANCE', 'R-MEMBER'] , False)


    # Computer, Instance and User are Author on The module 
    self.assertRoles(document, 'R-MEMBER', ['Auditor'])
    self.assertRoles(document, 'R-INSTANCE', ['Auditor'])
    self.assertRoles(document, 'R-COMPUTER', ['Auditor'])
    self.assertRoles(document, 'ERP5TypeTestCase', ['Owner'])

  def _testDocumentPermission(self, module, portal_type):
    document = self._getDocumentForTestSecurity(module, portal_type)    
    self.assertPermissionsOfRole(document, 'Owner', [READ, VIEW])
    # Author can Read, ADD, and View
    self.assertPermissionsOfRole(document, 'Auditor', [READ, VIEW])

  def _testModuleLocalRole(self, module):
    """ """
    self.assertSecurityGroup(module, 
        ['R-MEMBER','G-COMPANY', 'R-COMPUTER', 'R-INSTANCE', 'zope'], 1)

    # Computer, Instance and User are Author on The module 
    # We don't test G-COMPANY related security here.
    self.assertRoles(module, 'R-MEMBER', ['Author'])
    self.assertRoles(module, 'R-INSTANCE', ['Author'])
    self.assertRoles(module, 'R-COMPUTER', ['Author'])
    self.assertRoles(module, 'zope', ['Owner'])

  def _testModulePermission(self, module):
    self.assertPermissionsOfRole(module, 'Owner', [])
    # Author can Read, ADD but not view
    self.assertPermissionsOfRole(module, 'Author',
                                 [READ, ADD] + OTHER_AUDITOR + OTHER_AUTHOR)

  def test_PresentationPermission(self):
    self._testDocumentPermission(self.portal.document_module, "Presentation")

  def test_FilePermissions(self):
    self._testDocumentPermission(self.portal.document_module, "File")

  def test_TextPermissions(self):
    self._testDocumentPermission(self.portal.document_module, "Text")

  def test_SpreadsheetPermission(self):
    self._testDocumentPermission(self.portal.document_module, "Spreadsheet")

  def test_PDFPermission(self):
    self._testDocumentPermission(self.portal.document_module, "PDF")

  def test_ImagePermission(self):
    self._testDocumentPermission(self.portal.image_module, "Image")

  def test_PresentationLocalRole(self):
    self._testDocumentLocalRole(self.portal.document_module, "Presentation")

  def test_FileLocalRole(self):
    self._testDocumentLocalRole(self.portal.document_module, "File")

  def test_TextLocalRole(self):
    self._testDocumentLocalRole(self.portal.document_module, "Text")

  def test_SpreadsheetLocalRole(self):
    self._testDocumentLocalRole(self.portal.document_module, "Spreadsheet")

  def test_PDFLocalRole(self):
    self._testDocumentLocalRole(self.portal.document_module, "PDF")

  def test_DrawingLocalRole(self):
    self._testDocumentLocalRole(self.portal.document_module, "Drawing")

  def test_ImageLocalRole(self):
    self._testDocumentLocalRole(self.portal.image_module, "Image")
    
  def test_DocumentModuleLocalRole(self):
    self._testModuleLocalRole(self.portal.document_module)

  def test_ImageModuleLocalRole(self):
    self._testModuleLocalRole(self.portal.image_module)

  def test_PortalContributionsLocalRole(self):
    self._testModuleLocalRole(self.portal.portal_contributions)

  def test_PortalContributionsPermission(self):
    self._testModulePermission(self.portal.document_module)

  def test_DocumentModulePermission(self):
    self._testModulePermission(self.portal.document_module)

  # Contribution Tool
  @expectedFailure
  def test_user_create_document_using_contribution_tool(self):
    """
      User must be able to create a document using contribution.
    """
    raise NotImplementedError
