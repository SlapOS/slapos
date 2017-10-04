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
from functools import partial
from Products.ERP5Type.Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products import ERP5Security
from Products.ERP5Type.UnrestrictedMethod import UnrestrictedMethod
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.PluggableAuthService.interfaces import plugins
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.ERP5Security.ERP5GroupManager import NO_CACHE_MODE
from Products.ERP5Type.Cache import CachingMethod
from Products.ERP5Security.ERP5LoginUserManager import SYSTEM_USER_USER_NAME,\
                                                   SPECIAL_USER_NAME_SET

# some usefull globals
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

  #################################
  #   IGroupsPlugin               #
  #################################
  # This is patched version of
  #   Products.ERP5Security.ERP5GroupManager.ERP5GroupManager.getGroupsForPrincipal
  # which allows to treat Computer and Software Instance as loggable user
  def getGroupsForPrincipal(self, principal, request=None):
    """ See IGroupsPlugin.
    """
    # If this is the super user, skip the check.
    if principal.getId() == ERP5Security.SUPER_USER:
      return ()

    @UnrestrictedMethod
    def _getGroupsForPrincipal(user_id, path):
      if user_id.startswith(LOGIN_PREFIX):
        user_id = user_id[LOGIN_PREFIX_LENGTH:]
      else:
        return ( )

      # get the person from its login - no security check needed
      user_path_set = {
        x['path']
        for x in self.searchUsers(id=user_id, exact_match=True)
        if 'path' in x
      }
      if not user_path_set:
        return ()
      user_path, = user_path_set
      person_object = self.getPortalObject().unrestrictedTraverse(user_path)

      portal_type = person_object.getPortalType()

      return (
        'R-SHADOW-%s' % portal_type.replace(' ', '').upper(), # generic group
        'SHADOW-%s' % user_id # user specific shadow
        )

    if not NO_CACHE_MODE:
      _getGroupsForPrincipal = CachingMethod(_getGroupsForPrincipal,
                                             id='ERP5GroupManager_getGroupsForPrincipal',
                                             cache_factory='erp5_content_short')

    return _getGroupsForPrincipal(
                user_id=principal.getId(),
                path=self.getPhysicalPath())

  #
  #   IUserEnumerationPlugin implementation
  #
  security.declarePrivate('enumerateUsers')
  def enumerateUsers(self, id=None, login=None, exact_match=False,
             sort_by=None, max_results=None, login_portal_type=None, **kw):
    """ See IUserEnumerationPlugin.
    """
    portal = self.getPortalObject()
    if login_portal_type is None:
      login_portal_type = portal.getPortalLoginTypeList()
    unrestrictedSearchResults = portal.portal_catalog.unrestrictedSearchResults
    searchUser = lambda **kw: unrestrictedSearchResults(
      select_list=('user_id', ),
      **kw
    ).dictionaries()
    searchLogin = lambda **kw: unrestrictedSearchResults(
      select_list=('parent_uid', 'reference'),
      validation_state='validated',
      **kw
    ).dictionaries()
    if login_portal_type is not None:
      searchLogin = partial(searchLogin, portal_type=login_portal_type)
    special_user_name_set = set()
    if login is None:
      # Only search by id if login is not given. Same logic as in
      # PluggableAuthService.searchUsers.

      # CUSTOM: Modify the id to remove the prefix before search the User
      if id.startswith(LOGIN_PREFIX):
        id = id[LOGIN_PREFIX_LENGTH:]
      else:
        return ( )
      # END OF CUSTOM CODE

      if isinstance(id, str):
        id = (id, )

      # Short-cut "System Processes" as not being searchable by user_id.
      # This improves performance in proxy-role'd execution by avoiding an
      # sql query expected to find no user.
      id = [x for x in id if x != SYSTEM_USER_USER_NAME]
      if id:
        if exact_match:
          requested = set(id).__contains__
        else:
          requested = lambda x: True
        user_list = [
          x for x in searchUser(
            user_id={
              'query': id,
              'key': 'ExactMatch' if exact_match else 'Keyword',
            },
            limit=max_results,
          )
          if requested(x['user_id'])
        ]
      else:
        user_list = []
      login_dict = {}
      if user_list:
        for login in searchLogin(parent_uid=[x['uid'] for x in user_list]):
          login_dict.setdefault(login['parent_uid'], []).append(login)
    else:

      # CUSTOM: Modify the login to remove the prefix before search the User
      if login.startswith(LOGIN_PREFIX):
        login = login[LOGIN_PREFIX_LENGTH:]
      else:
        return ( )
      # END OF CUSTOM CODE

      if isinstance(login, str):
        login = (login, )

      login_list = []
      for user_login in login:
        if user_login in SPECIAL_USER_NAME_SET:
          special_user_name_set.add(user_login)
        else:
          login_list.append(user_login)
      login_dict = {}
      if exact_match:
        requested = set(login_list).__contains__
      else:
        requested = lambda x: True
      if login_list:
        for login in searchLogin(
          reference={
            'query': login_list,
            'key': 'ExactMatch' if exact_match else 'Keyword',
          },
          limit=max_results,
        ):
          if requested(login['reference']):
            login_dict.setdefault(login['parent_uid'], []).append(login)
      if login_dict:
        user_list = searchUser(uid=list(login_dict))
      else:
        user_list = []
    plugin_id = self.getId()

    # CUSTOM: In the block below the LOGIN_PREFIX is added before id and login
    # to keep compatibility.

    result = [
      {
        'id': LOGIN_PREFIX + user['user_id'],
        # Note: PAS forbids us from returning more than one entry per given id,
        # so take any available login.
        'login': LOGIN_PREFIX + login_dict.get(user['uid'], [{'reference': None}])[0]['reference'],
        'pluginid': plugin_id,

        # Extra properties, specific to ERP5
        'path': user['path'],
        'uid': user['uid'],
        'login_list': [
          {
            'reference': LOGIN_PREFIX + login['reference'],
            'path': login['path'],
            'uid': login['uid'],
          }
          for login in login_dict.get(user['uid'], [])
        ],
      }
      for user in user_list if user['user_id']
    ]
    # END OF CUSTOM CODE

    return tuple(result)

#List implementation of class
classImplements( SlapOSShadowAuthenticationPlugin,
               plugins.IGroupsPlugin
               )
classImplements( SlapOSShadowAuthenticationPlugin,
               plugins.IUserEnumerationPlugin
               )
InitializeClass(SlapOSShadowAuthenticationPlugin)
