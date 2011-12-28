##############################################################################
#
# Copyright (c) 2011 Vifib SARL and Contributors. All Rights Reserved.
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
from slapos.recipe.librecipe import GenericBaseRecipe
import pkg_resources

class Recipe(GenericBaseRecipe):
  def install(self):
    path_list = []
    ip = self.options['ip']
    port = self.options['port']
    backend = self.options['backend']
    key = self.options['key-file']
    certificate = self.options['cert-file']
    access_control_string = self.options['access-control-string']
    apache_conf = dict()
    apache_conf['pid_file'] = self.options['pid-file']
    apache_conf['lock_file'] = self.options['lock-file']
    apache_conf['ip'] = ip
    apache_conf['port'] = port
    apache_conf['server_admin'] = 'admin@'
    apache_conf['error_log'] = self.options['error-log']
    apache_conf['access_log'] = self.options['access-log']
    apache_conf['server_name'] = '%s' % apache_conf['ip']
    apache_conf['certificate'] = certificate
    apache_conf['key'] = key
    apache_conf['path'] = '/'
    apache_conf['access_control_string'] = access_control_string
    apache_conf['rewrite_rule'] = "RewriteRule (.*) %s$1 [L,P]" % backend
    apache_conf_string = pkg_resources.resource_string(__name__,
          'template/apache.zope.conf.in') % apache_conf
    apache_config_file = self.createFile(self.options['configuration-file'],
      apache_conf_string)
    path_list.append(apache_config_file)
    wrapper = self.createPythonScript(self.options['wrapper'], __name__ +
      '.apache.runApache', [
            dict(
              required_path_list=[key, certificate],
              binary=self.options['apache-binary'],
              config=apache_config_file
            )
          ])
    path_list.append(wrapper)
    return path_list
