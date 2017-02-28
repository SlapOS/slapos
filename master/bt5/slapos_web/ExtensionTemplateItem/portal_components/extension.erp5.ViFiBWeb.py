##############################################################################
#
# Copyright (c) 2002-2010 Nexedi SA and Contributors. All Rights Reserved.
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

import facebook
from Products.ERP5Type.Cache import DEFAULT_CACHE_SCOPE
import httplib
import urllib
import urlparse
import json
import apiclient.discovery
import httplib2
import oauth2client.client
import socket


# common methods
def _getCacheFactory(self, cache_factory_name):
  portal = self.getPortalObject()
  cache_tool = portal.portal_caches
  cache_factory = cache_tool.getRamCacheRoot().get(cache_factory_name)
  #XXX This conditional statement should be remove as soon as
  #Broadcasting will be enable among all zeo clients.
  #Interaction which update portal_caches should interact with all nodes.
  if cache_factory is None \
      and getattr(cache_tool, cache_factory_name, None) is not None:
    #ram_cache_root is not up to date for current node
    cache_tool.updateCache()
  return cache_tool.getRamCacheRoot().get(cache_factory_name)

def setServerToken(self, key, body, cache_factory_name):
  cache_factory = _getCacheFactory(self, cache_factory_name)
  cache_duration = cache_factory.cache_duration
  for cache_plugin in cache_factory.getCachePluginList():
    cache_plugin.set(key, DEFAULT_CACHE_SCOPE,
                     body, cache_duration=cache_duration)

def getServerToken(self, key, cache_factory_name):
  cache_factory = _getCacheFactory(self, cache_factory_name)
  for cache_plugin in cache_factory.getCachePluginList():
    cache_entry = cache_plugin.get(key, DEFAULT_CACHE_SCOPE)
    if cache_entry is not None:
      return cache_entry.getValue()
  raise KeyError('Key %r not found' % key)

# Facebook AS
def Facebook_setServerToken(self, key, body):
  setServerToken(self, key, body, 'facebook_server_auth_token_cache_factory')

def Facebook_getServerToken(self, key):
  return getServerToken(self, key, 'facebook_server_auth_token_cache_factory')

def Facebook_getAccessTokenFromCode(self, code, redirect_uri):
  return facebook.get_access_token_from_code(code=code,
    redirect_uri=redirect_uri,
    app_id=self.portal_preferences.getPreferredVifibFacebookApplicationId(),
    app_secret=self.portal_preferences.getPreferredVifibFacebookApplicationSecret())

# Google AS
def Google_setServerToken(self, key, body):
  setServerToken(self, key, body, 'google_server_auth_token_cache_factory')

def Google_getServerToken(self, key):
  return getServerToken(self, key, 'google_server_auth_token_cache_factory')

def Google_getAccessTokenFromCode(self, code, redirect_uri):
  connection_kw = {'host': 'accounts.google.com', 'timeout': 30}
  connection = httplib.HTTPSConnection(**connection_kw)
  data = {
      'client_id': self.portal_preferences.getPreferredVifibGoogleApplicationId(),
      'client_secret': self.portal_preferences.getPreferredVifibGoogleApplicationSecret(),
      'grant_type': 'authorization_code',
      'redirect_uri': redirect_uri,
      'code': code
      }
  data = urllib.urlencode(data)
  headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "*/*"
  }
  connection.request('POST', '/o/oauth2/token', data, headers)
  response = connection.getresponse()

  if response.status != 200:
    return None

  try:
    body = json.loads(response.read())
  except Exception:
    return None

  try:
    return body
  except Exception:
    return None

def Facebook_getUserId(access_token):
  facebook_entry = facebook.GraphAPI(access_token).get_object("me")
  return facebook_entry['id'].encode('utf-8')

def Google_getUserId(access_token):
  timeout = socket.getdefaulttimeout()
  try:
    socket.setdefaulttimeout(10)
    http = oauth2client.client.AccessTokenCredentials(access_token, 'Vifib'
      ).authorize(httplib2.Http())
    service = apiclient.discovery.build("oauth2", "v1", http=http)
    google_entry = service.userinfo().get().execute()
  except Exception:
    google_entry = None
  finally:
    socket.setdefaulttimeout(timeout)

  if google_entry is not None:
    return google_entry['id'].encode('utf-8')
  return None

def Facebook_checkUserExistence(self):
  hash = self.REQUEST.get('__ac_facebook_hash')
  try:
    access_token_dict = Facebook_getServerToken(self, hash)
  except KeyError:
    return False
  access_token = access_token_dict.get('access_token')
  url = urlparse.urlsplit(self.portal_preferences.getPreferredVifibRestApiLoginCheck())
  connection_kw = {'host': url.netloc, 'timeout': 30}
  if url.scheme == 'http':
    connection = httplib.HTTPConnection(**connection_kw)
  else:
    connection = httplib.HTTPSConnection(**connection_kw)
  connection.request('GET', url.path, headers = {
      'Authorization' : 'Facebook %s' % access_token,
      'Accept': 'application/json'})
  response = connection.getresponse()

  # user exist if server gave some correct response without waiting for user
  return response.status in (200, 204)

def Google_checkUserExistence(self):
  hash = self.REQUEST.get('__ac_google_hash')
  try:
    access_token_dict = Google_getServerToken(self, hash)
  except KeyError:
    return False
  access_token = access_token_dict.get('access_token')
  url = urlparse.urlsplit(self.portal_preferences.getPreferredVifibRestApiLoginCheck())
  connection_kw = {'host': url.netloc, 'timeout': 30}
  if url.scheme == 'http':
    connection = httplib.HTTPConnection(**connection_kw)
  else:
    connection = httplib.HTTPSConnection(**connection_kw)
  connection.request('GET', url.path, headers = {
      'Authorization' : 'Google %s' % access_token,
      'Accept': 'application/json'})
  response = connection.getresponse()

  # user exist if server gave some correct response without waiting for user
  return response.status in (200, 204)
