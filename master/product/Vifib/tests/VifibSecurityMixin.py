# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Nexedi SA and Contributors. All Rights Reserved.
#                    Romain Courteaud <romain@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
from Testing.ZopeTestCase.PortalTestCase import PortalTestCase
from Products.ERP5Type.tests.SecurityTestCase import SecurityTestCase
from AccessControl import getSecurityManager
from VifibMixin import testVifibMixin
from Products.ERP5Type.tests.utils import DummyMailHost
import transaction

use_verbose_security = 0
if use_verbose_security:
  import AccessControl
  AccessControl.Implementation.setImplementation('python')
  AccessControl.ImplPython.setDefaultBehaviors(
              ownerous=True,
              authenticated=True,
              verbose=True)


class testVifibSecurityMixin(SecurityTestCase, testVifibMixin):
  """
  Mixin class for security unit test of Vifib.
  """
  run_all_test = 1

  def createManagerAndLogin(self):
    """
    Create a simple user in user_folder with manager rights.
    This user will be used to initialize data in the method afterSetup
    """
    self.getUserFolder()._doAddUser('manager', 'manager', ['Manager'], [])
    self.login('manager')

  def createERP5Users(self, user_dict):
    """
    Create all ERP5 users needed for the test.
    ERP5 user = Person object + Assignment object in erp5 person_module.
    """
    portal = self.getPortal()
    user = getSecurityManager().getUser()
    user_name = user.getUserName()
    # Check that user has access on the module
    module = portal.getDefaultModule("Person")
    if user_name != 'manager':
      self.assertTrue(user.has_permission('Access contents information',
                                          module))
      self.assertTrue(user.has_permission('View',
                                          module))
      self.assertTrue(user.has_permission('Add portal content',
                                          module))
      self.assertFalse(user.has_permission('Modify portal content',
                                          module))
    # Create the Person.
    for user_login, user_data in user_dict.items():
      self.logMessage("Create user: %s" % user_login)
      # Create the Person.
      person = module.newContent(
        portal_type='Person', 
        first_name=user_login,
        reference=user_login, 
        default_email_text='romain@nexedi.com', 
        career_role='internal',
#         password='hackme',
      )
      if user_name != 'manager':
        self.assertTrue(user.has_permission('Access contents information',
                                            person))
        self.assertTrue(user.has_permission('View',
                                            person))
        self.assertTrue(user.has_permission('Add portal content',
                                            person))
        self.assertTrue(user.has_permission('Modify portal content',
                                            person))

      # Create the Assignment.
      assignment = person.newContent( 
        portal_type = 'Assignment',
        destination_project = user_data[0],
        group = user_data[1],
        function = user_data[2],
        role = user_data[3],
        start_date = '01/01/1900',
        stop_date = '01/01/2900',
      )
      if user_name != 'manager':
        self.assertTrue(user.has_permission('Access contents information',
                                            assignment))
        self.assertTrue(user.has_permission('View',
                                            assignment))
        self.assertTrue(user.has_permission('Add portal content',
                                            assignment))
        self.assertTrue(user.has_permission('Modify portal content',
                                            assignment))
      # User assignment to security groups is also required
      self.portal.portal_workflow.doActionFor(
                            assignment,
                            'open_action')
    # Reindexing is required for the security to work
    transaction.commit()
    self.tic()

  def createAdministratorUser(self):
    """
    Create Administrator user.
    """
    user_dict = {
      'administrator': [None, None, None, None]
                        
    }
    self.createERP5Users(user_dict)

  def stepLoginAsAdministrator(self, sequence=None, sequence_list=None, **kw):
    """
    Login as administrator
    """
    self.login("administrator")

  def stepLoginAsManager(self, sequence=None, sequence_list=None, **kw):
    """
    Login as manager
    """
    self.login("manager")

  def createVifibUsers(self):
    """
    Create all users needed for the test
    """
    self.createERP5Users(self.getUserDict())

  def getUserDict(self):
    """
    Return dict of users needed for the test
    """
    return {}


  def createVifibDocumentList(self):
    """
    Call by bootstrapSite, can be overwritten
    """
    pass

  def validateRule(self):
    """
    Call by bootstrapSite, can be overwritten
    """
    pass

  def bootstrapSite(self):
    """
    Manager has to create an administrator user first.
    """
    portal = self.getPortal()
    if 'MailHost' in portal.objectIds():
      portal.manage_delObjects(['MailHost'])
    portal._setObject('MailHost', DummyMailHost('MailHost'))

    portal.email_from_address = 'romain@nexedi.com'
    portal.email_to_address = 'romain@nexedi.com'

    self.clearCache()

    self.logMessage("Bootstrap Vifib...")
    self.logMessage("Create Manager")
    self.createManagerAndLogin()
    self.createVifibDocumentList()
    self.validateRule()
    self.logMessage("Create Administrator")
    self.createAdministratorUser()
    self.logout()
    self.logMessage("Bootstrap Finished")
    # XXX Hardcoded
    # XXX-Fx: No security is defined so administrator has no rights
    # so impossible to create vifib user with administrator
    #self.login("administrator")
    self.login('manager')
    # XXX-Fx
    # XXX XXX
    self.createVifibUsers()
    self.logout()

  def stepLogout(self, sequence=None, sequence_list=None, **kw):
    """
    Logout
    """
    self.logout()

  def stepAddObject(self, sequence=None, sequence_list=None, **kw):
    """
    Add an object in the module
    """
    portal = self.getPortal()
    portal_type = sequence.get('object_portal_type')
    module = portal.getDefaultModule(portal_type)
    obj = module.newContent(portal_type=portal_type)
    sequence.edit(
      obj_id=obj.getId()
    )
    transaction.commit()
    self.tic()
