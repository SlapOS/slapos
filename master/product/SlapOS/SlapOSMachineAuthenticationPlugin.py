# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Nexedi SA and Contributors. All Rights Reserved.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################

from Products.ERP5Type.Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PluggableAuthService.interfaces import plugins
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.PluggableAuthService import DumbHTTPExtractor

#Form for new plugin in ZMI
manage_addSlapOSMachineAuthenticationPluginForm = PageTemplateFile(
  'www/SlapOS_addSlapOSMachineAuthenticationPlugin', globals(),
  __name__='manage_addSlapOSMachineAuthenticationPluginForm')

def addSlapOSMachineAuthenticationPlugin(dispatcher, id, title=None, REQUEST=None):
  """ Add a SlapOSMachineAuthenticationPlugin to a Pluggable Auth Service. """

  plugin = SlapOSMachineAuthenticationPlugin(id, title)
  dispatcher._setObject(plugin.getId(), plugin)

  if REQUEST is not None:
      REQUEST['RESPONSE'].redirect(
          '%s/manage_workspace'
          '?manage_tabs_message='
          'SlapOSMachineAuthenticationPlugin+added.'
          % dispatcher.absolute_url())

class SlapOSMachineAuthenticationPlugin(BasePlugin):
  """
  Plugin to authenicate as machines.
  """

  meta_type = "SlapOS Machine Authentication Plugin"
  security = ClassSecurityInfo()

  def __init__(self, id, title=None):
    #Register value
    self._id = self.id = id
    self.title = title

  security.declarePrivate('extractCredentials')
  def extractCredentials(self, request):
    """ Extract credentials from the request header. """
    creds = {}
    getHeader = getattr(request, 'getHeader', None)
    if getHeader is None:
      # use get_header instead for Zope-2.8
      getHeader = request.get_header
    user_id = getHeader('REMOTE_USER')
    if user_id is not None:
      creds['external_login'] = user_id
      creds['remote_host'] = request.get('REMOTE_HOST', '')
      creds['login_portal_type'] = "ERP5 Login"
      try:
        creds['remote_address'] = request.getClientAddr()
      except AttributeError:
        creds['remote_address'] = request.get('REMOTE_ADDR', '')
      return creds
    else:
      # fallback to default way
      return DumbHTTPExtractor().extractCredentials(request)

classImplements( SlapOSMachineAuthenticationPlugin,
                plugins.ILoginPasswordHostExtractionPlugin)

InitializeClass(SlapOSMachineAuthenticationPlugin)
