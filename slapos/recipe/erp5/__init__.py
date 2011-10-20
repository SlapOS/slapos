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
from slapos.recipe.librecipe import BaseSlapRecipe
import binascii
import os
import pkg_resources
import pprint
import hashlib
import sys
import zc.buildout
import zc.recipe.egg
import ConfigParser
import re

class Recipe(BaseSlapRecipe):
  def getTemplateFilename(self, template_name):
    return pkg_resources.resource_filename(__name__,
        'template/%s' % template_name)

  site_id = 'erp5'

  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()
    # self.cron_d is a directory, where cron jobs can be registered
    self.cron_d = self.installCrond()
    self.logrotate_d, self.logrotate_backup = self.installLogrotate()
    ca_conf = self.installCertificateAuthority()

#     memcached_conf = self.installMemcached(ip=self.getLocalIPv4Address(),
#         port=11000)
#     kumo_conf = self.installKumo(self.getLocalIPv4Address())
#    conversion_server_conf = self.installConversionServer(
#        self.getLocalIPv4Address(), 23000, 23060)
#    mysql_conf = self.installMysqlServer(self.getLocalIPv4Address(), 45678)
    user, password = self.installERP5()

    if self.parameter_dict.get("slap_software_type", "").lower() == "cluster":
      # Site access is done by HAProxy
      zope_access, site_access, key_access = self.installZopeCluster(ca_conf)
    else:
      zope_access = self.installZopeStandalone()
      site_access = zope_access
      key_access = None

    key, certificate = self.requestCertificate('Login Based Access')
#    apache_conf = dict(
#         apache_login=self.installBackendApache(ip=self.getGlobalIPv6Address(),
#         port=13000, backend=site_access, key=key, certificate=certificate))

    connection_dict = dict(site_url=apache_conf['apache_login'])

    if self.parameter_dict.get("domain_name") is not None:
      connection_dict["backend_url"] = apache_conf['apache_login']
      connection_dict["domain_ip"] = self.getGlobalIPv6Address()

      # XXX Define a fake domain_name for now.
      frontend_name = self.parameter_dict.get("domain_name")
      frontend_key, frontend_certificate = \
             self.requestCertificate(frontend_name)

      connection_dict["site_url"] = self.installFrontendZopeApache(
        ip=self.getGlobalIPv6Address(), port=4443, name=frontend_name,
        frontend_path='/', backend_path='',
        backend_url=apache_conf['apache_login'], key=frontend_key,
        certificate=frontend_certificate)


#    self.installTestRunner(ca_conf, mysql_conf, conversion_server_conf,
#                           memcached_conf, kumo_conf)
#    self.installTestSuiteRunner(ca_conf, mysql_conf, conversion_server_conf,
#                           memcached_conf, kumo_conf)
    self.linkBinary()
    connection_dict.update(**dict(
      site_user=user,
      site_password=password,
      memcached_url=memcached_conf['memcached_url'],
      kumo_url=kumo_conf['kumo_address']
    ))
    if key_access is not None:
      connection_dict['key_access'] = key_access
    self.setConnectionDict(connection_dict)
    return self.path_list

  def installFrontendZopeApache(self, ip, port, name, frontend_path, backend_url,
      backend_path, key, certificate, access_control_string=None):
    ident = 'frontend_' + name
    apache_conf = self._getApacheConfigurationDict(ident, ip, port)
    apache_conf['server_name'] = name
    apache_conf['frontend_path'] = frontend_path
    apache_conf['ssl_snippet'] = pkg_resources.resource_string(__name__,
        'template/apache.ssl-snippet.conf.in') % dict(
        login_certificate=certificate, login_key=key)

    path = pkg_resources.resource_string(__name__,
           'template/apache.zope.conf.path-protected.in') % \
              dict(path='/', access_control_string='none')

    if access_control_string is None:
      path_template = pkg_resources.resource_string(__name__,
        'template/apache.zope.conf.path.in')
      path += path_template % dict(path=frontend_path)
    else:
      path_template = pkg_resources.resource_string(__name__,
        'template/apache.zope.conf.path-protected.in')
      path += path_template % dict(path=frontend_path,
          access_control_string=access_control_string)

    rewrite_rule_template = \
        "RewriteRule ^%(path)s($|/.*) %(backend_url)s/VirtualHostBase/https/%(server_name)s:%(port)s%(backend_path)s/VirtualHostRoot/%(vhname)s$1 [L,P]\n"

    if frontend_path not in ["", None, "/"]:
      vhname = "_vh_%s" % frontend_path.replace('/', '')
    else:
      vhname = ""
      frontend_path = ""

    rewrite_rule = rewrite_rule_template % dict(
          path=frontend_path,
          backend_url=backend_url,
          backend_path=backend_path,
          port=apache_conf['port'],
          vhname=vhname,
          server_name=name)

    apache_conf.update(**dict(
      path_enable=path,
      rewrite_rule=rewrite_rule
    ))
    apache_conf_string = pkg_resources.resource_string(__name__,
          'template/apache.zope.conf.in') % apache_conf
    apache_config_file = self.createConfigurationFile(ident + '.conf',
        apache_conf_string)
    self.path_list.append(apache_config_file)
    self.path_list.extend(zc.buildout.easy_install.scripts([(
      ident, __name__ + '.apache', 'runApache')], self.ws,
          sys.executable, self.wrapper_directory, arguments=[
            dict(
              required_path_list=[key, certificate],
              binary=self.options['httpd_binary'],
              config=apache_config_file
            )
          ]))
    # Note: IPv6 is assumed always
    return 'https://%(server_name)s:%(port)s%(frontend_path)s' % (apache_conf)
