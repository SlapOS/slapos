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

class VifibCookieHashExtractionPlugin(BasePlugin):
  """
  Plugin to authenicate as machines.
  """

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
    """ Extract CookieHash credentials from the request header. """
    creds = {}
    cookie_hash = request.get(self.cookie_name)
    if cookie_hash is not None:
      try:
        user_dict = self.getKey(cookie_hash)
      except KeyError:
        return DumbHTTPExtractor().extractCredentials(request)
      if 'login' in user_dict:
        creds['external_login'] = user_dict['login']
        creds['remote_host'] = request.get('REMOTE_HOST', '')
        try:
          creds['remote_address'] = request.getClientAddr()
        except AttributeError:
          creds['remote_address'] = request.get('REMOTE_ADDR', '')
        return creds
    return DumbHTTPExtractor().extractCredentials(request)

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

class VifibFacebookServerExtractionPlugin(VifibCookieHashExtractionPlugin):
  cache_factory_name = 'facebook_server_auth_token_cache_factory'
  cookie_name = '__ac_facebook_hash'
  meta_type = "Vifib Facebook Server Extraction Plugin"

#List implementation of class
classImplements( VifibFacebookServerExtractionPlugin,
                plugins.ILoginPasswordHostExtractionPlugin
               )
InitializeClass(VifibFacebookServerExtractionPlugin)

#Form for new plugin in ZMI
manage_addVifibGoogleServerExtractionPluginForm = PageTemplateFile(
  'www/Vifib_addVifibGoogleServerExtractionPlugin', globals(),
  __name__='manage_addVifibGoogleServerExtractionPluginForm')

def addVifibGoogleServerExtractionPlugin(dispatcher, id, title=None, REQUEST=None):
  """ Add a VifibGoogleServerExtractionPlugin to a Pluggable Auth Service. """

  plugin = VifibGoogleServerExtractionPlugin(id, title)
  dispatcher._setObject(plugin.getId(), plugin)

  if REQUEST is not None:
      REQUEST['RESPONSE'].redirect(
          '%s/manage_workspace'
          '?manage_tabs_message='
          'VifibGoogleServerExtractionPlugin+added.'
          % dispatcher.absolute_url())

class VifibGoogleServerExtractionPlugin(VifibCookieHashExtractionPlugin):
  cache_factory_name = 'google_server_auth_token_cache_factory'
  cookie_name = '__ac_google_hash'
  meta_type = "Vifib Google Server Extraction Plugin"

#List implementation of class
classImplements( VifibGoogleServerExtractionPlugin,
                plugins.ILoginPasswordHostExtractionPlugin
               )
InitializeClass(VifibGoogleServerExtractionPlugin)

#Form for new plugin in ZMI
manage_addVifibBrowserIDExtractionPluginForm = PageTemplateFile(
  'www/Vifib_addVifibBrowserIDExtractionPlugin', globals(),
  __name__='manage_addVifibBrowserIDExtractionPluginForm')

def addVifibBrowserIDExtractionPlugin(dispatcher, id, title=None, REQUEST=None):
  """ Add a VifibBrowserIDExtractionPlugin to a Pluggable Auth Service. """

  plugin = VifibBrowserIDExtractionPlugin(id, title)
  dispatcher._setObject(plugin.getId(), plugin)

  if REQUEST is not None:
      REQUEST['RESPONSE'].redirect(
          '%s/manage_workspace'
          '?manage_tabs_message='
          'VifibBrowserIDExtractionPlugin+added.'
          % dispatcher.absolute_url())

class VifibBrowserIDExtractionPlugin(VifibCookieHashExtractionPlugin):
  cache_factory_name = 'browser_id_auth_token_cache_factory'
  cookie_name = '__ac_browser_id_hash'
  meta_type = "Vifib Browser ID Extraction Plugin"

#List implementation of class
classImplements( VifibBrowserIDExtractionPlugin,
                plugins.ILoginPasswordHostExtractionPlugin
               )
InitializeClass(VifibBrowserIDExtractionPlugin)

