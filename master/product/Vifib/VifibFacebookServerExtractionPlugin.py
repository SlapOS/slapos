# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
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
from Products.ERP5Type.Cache import DEFAULT_CACHE_SCOPE

#Form for new plugin in ZMI
manage_addVifibFacebookServerExtractionPluginForm = PageTemplateFile(
  'www/Vifib_addVifibFacebookServerExtractionPlugin', globals(),
  __name__='manage_addVifibFacebookServerExtractionPluginForm')

def addVifibFacebookServerExtractionPlugin(dispatcher, id, title=None, REQUEST=None):
  """ Add a VifibFacebookServerExtractionPlugin to a Pluggable Auth Service. """

  plugin = VifibFacebookServerExtractionPlugin(id, title)
  dispatcher._setObject(plugin.getId(), plugin)

  if REQUEST is not None:
      REQUEST['RESPONSE'].redirect(
          '%s/manage_workspace'
          '?manage_tabs_message='
          'VifibFacebookServerExtractionPlugin+added.'
          % dispatcher.absolute_url())

class VifibFacebookServerExtractionPlugin(BasePlugin):
  """
  Plugin to authenicate as machines.
  """

  meta_type = "Vifib Facebook Server Extraction Plugin"
  # cache_fatory_name proposal to begin configurable
  cache_factory_name = 'facebook_server_auth_token_cache_factory'
  reference_prefix = 'fb_'
  security = ClassSecurityInfo()

  def __init__(self, id, title=None):
    #Register value
    self._setId(id)
    self.title = title

  #####################
  # memcached helpers #
  #####################
  def _getCacheFactory(self):
    portal = self.getPortalObject()
    cache_tool = portal.portal_caches
    cache_factory = cache_tool.getRamCacheRoot().get(self.cache_factory_name)
    #XXX This conditional statement should be remove as soon as
    #Broadcasting will be enable among all zeo clients.
    #Interaction which update portal_caches should interact with all nodes.
    if cache_factory is None \
        and getattr(cache_tool, self.cache_factory_name, None) is not None:
      #ram_cache_root is not up to date for current node
      cache_tool.updateCache()
    cache_factory = cache_tool.getRamCacheRoot().get(self.cache_factory_name)
    if cache_factory is None:
      raise KeyError
    return cache_factory

  def setFacebookToken(self, key, body):
    cache_factory = self._getCacheFactory()
    cache_duration = cache_factory.cache_duration
    for cache_plugin in cache_factory.getCachePluginList():
      cache_plugin.set(key, DEFAULT_CACHE_SCOPE,
                       body, cache_duration=cache_duration)

  def getKey(self, key):
    cache_factory = self._getCacheFactory()
    for cache_plugin in cache_factory.getCachePluginList():
      cache_entry = cache_plugin.get(key, DEFAULT_CACHE_SCOPE)
      if cache_entry is not None:
        return cache_entry.getValue()
    raise KeyError('Key %r not found' % key)

  ####################################
  #ILoginPasswordHostExtractionPlugin#
  ####################################
  security.declarePrivate('extractCredentials')
  def extractCredentials(self, request):
    """ Extract facebook credentials from the request header. """
    creds = {}
    facebook_cookie = request.get('__ac_facebook_hash')
    if facebook_cookie is not None:
      try:
        facebook_dict = self.getKey(facebook_cookie)
      except KeyError:
        return DumbHTTPExtractor().extractCredentials(request)
      if 'login' in facebook_dict:
        creds['external_login'] = facebook_dict['login']
        creds['remote_host'] = request.get('REMOTE_HOST', '')
        try:
          creds['remote_address'] = request.getClientAddr()
        except AttributeError:
          creds['remote_address'] = request.get('REMOTE_ADDR', '')
        return creds
    return DumbHTTPExtractor().extractCredentials(request)

  manage_editVifibFacebookServerExtractionPluginForm = PageTemplateFile(
      'www/Vifib_editVifibFacebookServerExtractionPlugin',
      globals(),
      __name__='manage_editVifibFacebookServerExtractionPluginForm')

#List implementation of class
classImplements( VifibFacebookServerExtractionPlugin,
                plugins.ILoginPasswordHostExtractionPlugin
               )
InitializeClass(VifibFacebookServerExtractionPlugin)

