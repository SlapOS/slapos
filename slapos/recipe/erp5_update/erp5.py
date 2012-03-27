##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
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
# as published by the Free Software Foundation; either version 3
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

import httplib
import json
import base64
import socket
import time


class ERP5Updater(object):

  erp5_catalog_storage = "erp5_mysql_innodb_catalog"
  header_dict = {}

  sleeping_time = 300
  short_sleeping_time = 60

  def __init__(self, user, password, host,
      site_id, mysql_url, memcached_address,
      conversion_server_address, persistent_cache_address,
      bt5_list, bt5_repository_list, certificate_authority_path,
      openssl_binary):

    authentication_string = '%s:%s' % (user, password)
    base64string = base64.encodestring(authentication_string).strip()

    self.header_dict['Authorization'] = 'Basic %s' % base64string

    self.host = host
    self.site_id = site_id
    self.business_template_repository_list = bt5_repository_list
    self.business_template_list = bt5_list
    self.memcached_address = memcached_address
    self.persistent_cached_address = persistent_cache_address
    self.mysql_url = mysql_url

    host, port = conversion_server_address.split(":")
    self.conversion_server_address = host
    self.conversion_server_port = int(port)

    # Certificate Authority Tool configuration
    self.certificate_authority_path = certificate_authority_path
    self.openssl_binary = openssl_binary

  def log(self, level, message):
    date = time.strftime("%a, %d %b %Y %H:%M:%S +0000")
    print "%s - %s : %s" % (date, level, message)

  def getConnectionToZope(self):
    return httplib.HTTPConnection(self.host)

  def GET(self, path):
    zope_connection = self.getConnectionToZope()
    self.log("INFO", "GET ZOPE: %s, PATH: %s" % (self.host, path))
    try:
      zope_connection.request('GET', path, headers=self.header_dict)
      result = zope_connection.getresponse()
      data = result.read()
      status = result.status
    except socket.error, e:
      data = "Unable to connect to %s (socket.error: %s)" % (self.host, e)
      self.log("ERROR", data)
      status = 0
    finally:
      zope_connection.close()

    return status, data

  def POST(self, path, post_dict):
    zope_connection = self.getConnectionToZope()
    param_list = []
    for item in post_dict:
      value = post_dict[item]
      if isinstance(value, type([])):
        for v in value:
          param_list.append("%s:list=%s" % (item, v))
      else:
        param_list.append("%s=%s" % (item, value))

    params = "&".join(param_list)
    self.log("INFO", "GET ZOPE: %s, PATH: %s, PARAMS: %s" % \
                     (self.host, path, params))
    try:
      zope_connection.request('POST', path, params, headers=self.header_dict)
      result = zope_connection.getresponse()
      data = result.read()
      status = result.status
    except socket.error, e:
      data = "Unable to connect to %s (socket.error: %s)" % (self.host, e)
      self.log("ERROR", data)
      status = 0
    finally:
      zope_connection.close()

    return status, data

  def isERP5Present(self):
    status, data = self.GET("/isERP5SitePresent")
    self.log("DEBUG", "isERP5Present : %s, %s" % (status, data))
    return status == 200 and not (data == "False")

  def loadSystemSignatureDict(self):
    base_path = \
        "/%s/portal_introspections/getSystemSignatureAsJSON" % self.site_id
    status, data = self.GET(base_path)
    if status == 200:
      data_dict = json.loads(data)
      self.system_signature_dict = data_dict
    elif status == 404:
      # Unable to find portal_introspection, this means erp5_base is not
      # installed yet.
      self.system_signature_dict = None
      self.log("DEBUG", "Unable to find portal_introspection, this means " + \
                        "erp5_base is not installed yet.")
    else:
      self.log("ERROR", "Unable to get SystemSignature to %s (status: %s, data: %s)" % \
          (self.host, status, data))

  def getSystemSignatureDict(self, item=None, default=None):
    system_signature_dict = getattr(self, 'system_signature_dict', None)
    if system_signature_dict is not None and item is not None:
        return system_signature_dict.get(item, default)
    return system_signature_dict

  def getMissingBusinessTemplateRepositoryList(self):
    found_list = self.getSystemSignatureDict(
                "business_template_repository_list", [])
    return [i for i in self.business_template_repository_list
                    if i not in found_list]

  def getMissingBusinessTemplateSet(self):
    found_dict = self.getSystemSignatureDict("business_template_dict", {})
    return set(self.business_template_list).difference(found_dict)

  def updateBusinessTemplateList(self):
    """ Update Business Template Configuration, including the repositories
    """
    missing_business_template_set = self.getMissingBusinessTemplateSet()
    if missing_business_template_set:
      # Before updating  the business templates,  it is required to  make sure
      # the  repositories are  updated,  thus  update them  even  if they  are
      # already present because there may be new business templates...
      repository_list = self.getSystemSignatureDict(
        "business_template_repository_list", [])
      repository_list.extend(self.getMissingBusinessTemplateRepositoryList())
      self._setRepositoryList(repository_list)

      # Require to update Business template
      self._installBusinessTemplateList(list(missing_business_template_set))
      return True

    return False

  def _setRepositoryList(self, repository_list):
    """ Set repository list on portal_templates """
    set_path = "/%s/portal_templates/updateRepositoryBusinessTemplateList" % self.site_id
    self.POST(set_path, {"repository_list": repository_list})

  def _installBusinessTemplateList(self, name_list, update_catalog=False):
    """ Install a Business Template on Remote ERP5 setup """
    set_path = "/%s/portal_templates/installBusinessTemplateListFromRepository" % self.site_id
    self.POST(set_path, {"template_list": name_list,
                         "only_newer": 1,
                         "update_catalog": int(update_catalog),
                         "activate": 1,
                         "install_dependency": 1})

  def _createActiveSystemPreference(self, edit_kw={}):
    """ Assert that at least one enabled System Preference is present on
        the erp5 instance.
    """
    self.log("INFO", "Try to create New System Preference into ERP5!")
    path = "/%s/portal_preferences/createActiveSystemPreference" % self.site_id
    status, data = self.POST(path, edit_kw)
    if status != 200:
      self.log("ERROR", "Unable to create System Preference, an error ocurred %s." % data)

  def updateConversionServer(self):
    """ Update Conversion server Configuration """
    external_connection_dict = self.getSystemSignatureDict("external_connection_dict")
    host_key = None
    port_key = None
    for external_connection in external_connection_dict:
      # Search for Configurated value for Conversion Server
      if external_connection.endswith("getPreferredOoodocServerAddress"):
         host_key = external_connection
      elif external_connection.endswith("getPreferredOoodocServerPortNumber"):
         port_key = external_connection
      if None not in [host_key, port_key]:
        break

    if None in [host_key, port_key]:
      self.log("ERROR", "Unable to find the Active System Preference to Update!")
      self._createActiveSystemPreference(
          {"preferred_ooodoc_server_address" : self.conversion_server_address,
           "preferred_ooodoc_server_port_number": self.conversion_server_port })
      return True

    is_updated = self._assertAndUpdateDocument(host_key, self.conversion_server_address,
         "setPreferredOoodocServerAddress")

    is_updated = self._assertAndUpdateDocument(port_key,
         self.conversion_server_port,
         "setPreferredOoodocServerPortNumber") or is_updated

    return is_updated

  def updateCertificateAuthority(self):
    """ Update the certificate authority only if is not configured yet """
    if self.isCertificateAuthorityAvailable():
      if self.isCertificateAuthorityConfigured():
        return True

      path = "/%s/portal_certificate_authority/" \
             "manage_editCertificateAuthorityTool" % self.site_id
      self.POST(path, {"certificate_authority_path": self.certificate_authority_path,
                       "openssl_binary": self.openssl_binary})


  def isCertificateAuthorityAvailable(self):
    """ Check if certificate Authority is available. """
    external_connection_dict = self.system_signature_dict[
      'external_connection_dict']
    if 'portal_certificate_authority/certificate_authority_path' in \
      external_connection_dict:
      return True
    return False

  def isCertificateAuthorityConfigured(self):
    """ Check if certificate Authority is configured correctly. """
    external_connection_dict = self.system_signature_dict[
      'external_connection_dict']
    if self.certificate_authority_path == external_connection_dict.get(
          'portal_certificate_authority/certificate_authority_path') and \
       self.openssl_binary == external_connection_dict.get(
          'portal_certificate_authority/openssl_binary'):
      return True
    return False

  def updateMemcached(self):
    # Assert Memcached configuration
    self._assertAndUpdateDocument(
       "portal_memcached/default_memcached_plugin/getUrlString",
       self.memcached_address,
       "setUrlString")

    # Assert Persistent cache configuration (Kumofs)
    self._assertAndUpdateDocument(
      "portal_memcached/persistent_memcached_plugin/getUrlString",
      self.persistent_cached_address,
      "setUrlString")

  def _assertAndUpdateDocument(self, key, expected_value, update_method):
    external_connection_dict = self.getSystemSignatureDict("external_connection_dict")

    # Assert Memcached configuration
    found_address = external_connection_dict.get(key)
    if found_address != expected_value:
      document_path = "/".join(key.split("/")[:-1])
      self.log("INFO",
               "Document require update at %s (Found: %s, Expected: %s)" % \
                            (document_path, found_address, expected_value))

      set_path = "/%s/%s/%s" % (self.site_id, document_path, update_method)
      self.POST(set_path, {"value": expected_value})
      return True
    return False

  def updateERP5Site(self):
    if not self.isERP5Present():
      self.log('INFO', 'No site present, adding new with id %r' % self.site_id)
      self.POST('/manage_addProduct/ERP5/manage_addERP5Site', {
          "id": self.site_id,
          "erp5_catalog_storage": self.erp5_catalog_storage,
          "erp5_sql_connection_string": self.mysql_url,
          "cmf_activity_sql_connection_string": self.mysql_url})
      return True
    return False

  def _hasActivityPresent(self):
    activity_dict = self.getSystemSignatureDict("activity_dict")
    if activity_dict["total"] > 0:
      self.log("DEBUG", "Waiting for activities on ERP5...")
      return True
    return False

  def _hasFailureActivity(self):
    activity_dict = self.getSystemSignatureDict("activity_dict")
    if activity_dict["failure"] > 0:
       self.log("ERROR", "Update progress found Failure activities" +\
                         "and it will not be able to progress until" +\
                         " activites issue be solved")
       return True
    return False

  def run(self):
    """ Keep running until kill"""
    while 1:
      self.log('INFO', 'Sleeping for %s' % self.short_sleeping_time)
      time.sleep(self.short_sleeping_time)
      if not self.updateERP5Site():
        self.loadSystemSignatureDict()
        if self._hasFailureActivity():
          time.sleep(self.sleeping_time)
          continue
          
        if self._hasActivityPresent():
          continue

        if self.updateBusinessTemplateList():
          continue

        self.updateMemcached()
        if self.updateConversionServer():
          continue
        self.updateCertificateAuthority()
        time.sleep(self.sleeping_time)

def updateERP5(argument_list):
  site_id = argument_list[0]
  mysql_url = argument_list[1]
  user, password, host = argument_list[2]
  memcached_address = argument_list[3]
  conversion_server_address = argument_list[4]
  persistent_cache_provider = argument_list[5]
  bt5_list = argument_list[6]
  certificate_authority_path = argument_list[8]
  openssl_binary = argument_list[9]
  bt5_repository_list = []

  if len(argument_list) > 7:
    bt5_repository_list = argument_list[7]

  if len(bt5_list) > 0 and len(bt5_repository_list) == 0:
    bt5_repository_list = ["http://www.erp5.org/dists/snapshot/bt5"]

  erp5_upgrader = ERP5Updater(
    user=user,
    password=password,
    host=host,
    site_id=site_id,
    mysql_url=mysql_url,
    memcached_address=memcached_address,
    conversion_server_address=conversion_server_address,
    persistent_cache_address=persistent_cache_provider,
    bt5_list=bt5_list,
    bt5_repository_list=bt5_repository_list,
    certificate_authority_path=certificate_authority_path,
    openssl_binary=openssl_binary)

  erp5_upgrader.run()
