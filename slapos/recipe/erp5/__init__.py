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
import pkg_resources
import sys
import zc.buildout
import zc.recipe.egg

class Recipe(BaseSlapRecipe):
  def _install(self):
    raise NotImplementedError('Outdated.')

  def installKeyAuthorisationApache(self, ipv6, port, backend, key, certificate,
      ca_conf, key_auth_path='/'):
    if ipv6:
      ip = self.getGlobalIPv6Address()
    else:
      ip = self.getLocalIPv4Address()
    ssl_template = """SSLEngine on
SSLVerifyClient require
RequestHeader set REMOTE_USER %%{SSL_CLIENT_S_DN_CN}s
SSLCertificateFile %(key_auth_certificate)s
SSLCertificateKeyFile %(key_auth_key)s
SSLCACertificateFile %(ca_certificate)s
SSLCARevocationPath %(ca_crl)s"""
    apache_conf = self._getApacheConfigurationDict('key_auth_apache', ip, port)
    apache_conf['ssl_snippet'] = ssl_template % dict(
        key_auth_certificate=certificate,
        key_auth_key=key,
        ca_certificate=ca_conf['ca_certificate'],
        ca_crl=ca_conf['ca_crl']
        )
    prefix = 'ssl_key_auth_apache'
    rewrite_rule_template = \
      "RewriteRule (.*) http://%(backend)s%(key_auth_path)s$1 [L,P]"
    path_template = pkg_resources.resource_string('slapos.recipe.erp5',
      'template/apache.zope.conf.path.in')
    path = path_template % dict(path='/')
    d = dict(
          path=path,
          backend=backend,
          backend_path='/',
          port=apache_conf['port'],
          vhname=path.replace('/', ''),
          key_auth_path=key_auth_path,
    )
    rewrite_rule = rewrite_rule_template % d
    apache_conf.update(**dict(
      path_enable=path,
      rewrite_rule=rewrite_rule
    ))
    apache_config_file = self.createConfigurationFile(prefix + '.conf',
        pkg_resources.resource_string('slapos.recipe.erp5',
          'template/apache.zope.conf.in') % apache_conf)
    self.path_list.append(apache_config_file)
    self.path_list.extend(zc.buildout.easy_install.scripts([(
      'key_auth_apache',
        'slapos.recipe.erp5.apache', 'runApache')], self.ws,
          sys.executable, self.wrapper_directory, arguments=[
            dict(
              required_path_list=[certificate, key, ca_conf['ca_certificate'],
                ca_conf['ca_crl']],
              binary=self.options['httpd_binary'],
              config=apache_config_file
            )
          ]))
    if ipv6:
      return 'https://[%(ip)s:%(port)s]' % apache_conf
    else:
      return 'https://%(ip)s:%(port)s' % apache_conf

  def _getApacheConfigurationDict(self, prefix, ip, port):
    apache_conf = dict()
    apache_conf['pid_file'] = os.path.join(self.run_directory,
        prefix + '.pid')
    apache_conf['lock_file'] = os.path.join(self.run_directory,
        prefix + '.lock')
    apache_conf['ip'] = ip
    apache_conf['port'] = port
    apache_conf['server_admin'] = 'admin@'
    apache_conf['error_log'] = os.path.join(self.log_directory,
        prefix + '-error.log')
    apache_conf['access_log'] = os.path.join(self.log_directory,
        prefix + '-access.log')
    self.registerLogRotation(prefix, [apache_conf['error_log'],
      apache_conf['access_log']], self.killpidfromfile + ' ' +
      apache_conf['pid_file'] + ' SIGUSR1')
    return apache_conf

  def _writeApacheConfiguration(self, prefix, apache_conf, backend,
      access_control_string=None):
    rewrite_rule_template = \
        "RewriteRule (.*) http://%(backend)s$1 [L,P]"
    if access_control_string is None:
      path_template = pkg_resources.resource_string(__name__,
        'template/apache.zope.conf.path.in')
      path = path_template % dict(path='/')
    else:
      path_template = pkg_resources.resource_string(__name__,
        'template/apache.zope.conf.path-protected.in')
      path = path_template % dict(path='/',
          access_control_string=access_control_string)
    d = dict(
          path=path,
          backend=backend,
          backend_path='/',
          port=apache_conf['port'],
          vhname=path.replace('/', ''),
    )
    rewrite_rule = rewrite_rule_template % d
    apache_conf.update(**dict(
      path_enable=path,
      rewrite_rule=rewrite_rule
    ))
    apache_conf_string = pkg_resources.resource_string(__name__,
          'template/apache.zope.conf.in') % apache_conf
    return self.createConfigurationFile(prefix + '.conf', apache_conf_string)

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
