# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Vifib SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################

from zLOG import LOG, PROBLEM
from Products.ERP5Type.Globals import InitializeClass
from AccessControl import ClassSecurityInfo
import sys

from AccessControl.SecurityManagement import newSecurityManager,\
    getSecurityManager, setSecurityManager
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PluggableAuthService.PluggableAuthService import \
    _SWALLOWABLE_PLUGIN_EXCEPTIONS
from Products.PluggableAuthService.interfaces import plugins
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.ERP5Type.Cache import transactional_cached
from Products.ERP5Security.ERP5UserManager import SUPER_USER
from ZODB.POSException import ConflictError
from Products.ERP5Security.ERP5GroupManager import ConsistencyError, NO_CACHE_MODE
from Products.ERP5Type.Cache import CachingMethod
from Products.ZSQLCatalog.SQLCatalog import Query, ComplexQuery
from Products.ERP5Security.ERP5UserManager import getValidAssignmentList

# some usefull globals
LOGGABLE_PORTAL_TYPE_LIST = ["Person", "Computer", "Software Instance"]
LOGIN_PREFIX = 'SHADOW-'
LOGIN_PREFIX_LENGTH = len(LOGIN_PREFIX)

#Form for new plugin in ZMI
manage_addSlapOSShadowAuthenticationPluginForm = PageTemplateFile(
  'www/SlapOS_addSlapOSShadowAuthenticationPlugin', globals(),
  __name__='manage_addSlapOSShadowAuthenticationPluginForm')

def addSlapOSShadowAuthenticationPlugin(dispatcher, id, title=None, REQUEST=None):
  """ Add a SlapOSShadowAuthenticationPlugin to a Pluggable Auth Service. """

  plugin = SlapOSShadowAuthenticationPlugin(id, title)
  dispatcher._setObject(plugin.getId(), plugin)

  if REQUEST is not None:
      REQUEST['RESPONSE'].redirect(
          '%s/manage_workspace'
          '?manage_tabs_message='
          'SlapOSShadowAuthenticationPlugin+added.'
          % dispatcher.absolute_url())

@transactional_cached(lambda portal, *args: args)
def getUserByLogin(portal, login):
  if isinstance(login, basestring):
    login = login,

  if len(login) != 1:
    return []

  login = login[0]
  if login.startswith(LOGIN_PREFIX):
    login = login[LOGIN_PREFIX_LENGTH:]
  else:
    return []

  machine_query = Query(portal_type=["Computer", "Software Instance"],
      validation_state="validated",
      reference=dict(query=login, key='ExactMatch'))
  person_query = Query(portal_type=["Person"],
      reference=dict(query=login, key='ExactMatch'))
  result = portal.portal_catalog.unrestrictedSearchResults(
    query=ComplexQuery(machine_query, person_query, operator="OR"),
    select_expression='reference')
  result = [x for x in result if \
    (x.getPortalType() == 'Person' and x.getValidationState() != 'deleted') or \
    (x.getPortalType() in ("Computer", "Software Instance") and \
      x.getValidationState() == 'validated')]
  # XXX: Here, we filter catalog result list ALTHOUGH we did pass
  # parameters to unrestrictedSearchResults to restrict result set.
  # This is done because the following values can match person with
  # reference "foo":
  # "foo " because of MySQL (feature, PADSPACE collation):
  #  mysql> SELECT reference as r FROM catalog
  #      -> WHERE reference="foo      ";
  #  +-----+
  #  | r   |
  #  +-----+
  #  | foo |
  #  +-----+
  #  1 row in set (0.01 sec)
  # "bar OR foo" because of ZSQLCatalog tokenizing searched strings
  #  by default (feature).
  return [x.getObject() for x in result if x['reference'] in login]

class SlapOSShadowAuthenticationPlugin(BasePlugin):
  """
  Plugin to authenicate as shadows.
  """

  meta_type = "SlapOS Shadow Authentication Plugin"
  security = ClassSecurityInfo()

  def __init__(self, id, title=None):
    #Register value
    self._setId(id)
    self.title = title

  ################################
  #     IAuthenticationPlugin    #
  ################################
  security.declarePrivate('authenticateCredentials')
  def authenticateCredentials(self, credentials):
    """Authentificate with credentials"""
    login = credentials.get('machine_login', None)
    # Forbidden the usage of the super user.
    if login == SUPER_USER:
      return None

    #Search the user by his login
    user_list = self.getUserByLogin(login)
    if len(user_list) != 1:
      return None
    user = user_list[0]
    if user.getPortalType() == 'Person':
      if len(getValidAssignmentList(user)) == 0:
        return None
    return (login, login)

  def getUserByLogin(self, login):
    # Search the Catalog for login and return a list of person objects
    # login can be a string or a list of strings
    # (no docstring to prevent publishing)
    if not login:
      return []
    if isinstance(login, list):
      login = tuple(login)
    elif not isinstance(login, tuple):
      login = str(login)
    try:
      return getUserByLogin(self.getPortalObject(), login)
    except ConflictError:
      raise
    except:
      LOG('SlapOSShadowAuthenticationPlugin', PROBLEM, 'getUserByLogin failed',
        error=sys.exc_info())
      # Here we must raise an exception to prevent callers from caching
      # a result of a degraded situation.
      # The kind of exception does not matter as long as it's catched by
      # PAS and causes a lookup using another plugin or user folder.
      # As PAS does not define explicitely such exception, we must use
      # the _SWALLOWABLE_PLUGIN_EXCEPTIONS list.
      raise _SWALLOWABLE_PLUGIN_EXCEPTIONS[0]

  #################################
  #   IGroupsPlugin               #
  #################################
  # This is patched version of
  #   Products.ERP5Security.ERP5GroupManager.ERP5GroupManager.getGroupsForPrincipal
  # which allows to treat Computer and Software Instance as loggable user
  loggable_portal_type_list = LOGGABLE_PORTAL_TYPE_LIST
  def getGroupsForPrincipal(self, principal, request=None):
    """ See IGroupsPlugin.
    """
    # If this is the super user, skip the check.
    if principal.getId() == SUPER_USER:
      return ()

    def _getGroupsForPrincipal(user_name, path):
      if user_name.startswith(LOGIN_PREFIX):
        user_name = user_name[LOGIN_PREFIX_LENGTH:]
      else:
        return ( )
      # because we aren't logged in, we have to create our own
      # SecurityManager to be able to access the Catalog
      sm = getSecurityManager()
      if sm.getUser().getId() != SUPER_USER:
        newSecurityManager(self, self.getUser(SUPER_USER))
      try:
        # get the loggable document from its reference - no security check needed
        catalog_result = self.portal_catalog.unrestrictedSearchResults(
            portal_type=self.loggable_portal_type_list,
            reference=dict(query=user_name, key='ExactMatch'))
        if len(catalog_result) != 1: # we won't proceed with groups
          if len(catalog_result) > 1: # configuration is screwed
            raise ConsistencyError, 'There is more than one of %s whose \
                login is %s : %s' % (','.join(self.loggable_portal_type_list),
                user_name,
                repr([r.getObject() for r in catalog_result]))
          else:
            return ()
        else:
          portal_type = catalog_result[0].getPortalType()

      finally:
        setSecurityManager(sm)
      return (
        'R-SHADOW-%s' % portal_type.replace(' ', '').upper(), # generic group
        'SHADOW-%s' % user_name # user specific shadow
        )

    if not NO_CACHE_MODE:
      _getGroupsForPrincipal = CachingMethod(_getGroupsForPrincipal,
                                             id='ERP5GroupManager_getGroupsForPrincipal',
                                             cache_factory='erp5_content_short')

    return _getGroupsForPrincipal(
                user_name=principal.getId(),
                path=self.getPhysicalPath())

  #
  #   IUserEnumerationPlugin implementation
  #
  security.declarePrivate( 'enumerateUsers' )
  def enumerateUsers(self, id=None, login=None, exact_match=False,
                   sort_by=None, max_results=None, **kw):
    """ See IUserEnumerationPlugin.
    """
    if id is None:
      id = login
    if isinstance(id, str):
      id = (id,)
    if isinstance(id, list):
      id = tuple(id)

    user_info = []
    plugin_id = self.getId()

    id_list = []
    for user_id in id:
      if SUPER_USER == user_id:
        info = { 'id' : SUPER_USER
                , 'login' : SUPER_USER
                , 'pluginid' : plugin_id
                }
        user_info.append(info)
      else:
        id_list.append(user_id)

    if id_list:
      for user in self.getUserByLogin(tuple(id_list)):
          info = { 'id' : LOGIN_PREFIX + user.getReference()
                 , 'login' : LOGIN_PREFIX + user.getReference()
                 , 'pluginid' : plugin_id
                 }

          user_info.append(info)

    return tuple(user_info)

#List implementation of class
classImplements(SlapOSShadowAuthenticationPlugin,
                plugins.IAuthenticationPlugin)
classImplements( SlapOSShadowAuthenticationPlugin,
               plugins.IGroupsPlugin
               )
classImplements( SlapOSShadowAuthenticationPlugin,
               plugins.IUserEnumerationPlugin
               )
InitializeClass(SlapOSShadowAuthenticationPlugin)
