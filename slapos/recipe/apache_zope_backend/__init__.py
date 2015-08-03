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
    try:
      backend_list = self.options['backend-list']
    except KeyError:
      backend_list = [(self.options['port'], self.options['backend'])]

    scheme = self.options['scheme']
    if scheme == 'http':
      required_path_list = []
      ssl_enable = ssl_snippet = ''
    elif scheme == 'https':
      key = self.options['key-file']
      certificate = self.options['cert-file']
      required_path_list = [key, certificate]
      ssl_snippet = self.substituteTemplate(self.getTemplateFilename('snippet.ssl.in'), {
        'key': key,
        'certificate': certificate,
        'ssl_session_cache': self.options['ssl-session-cache'],
      })
      if 'ssl-authentication' in self.options and self.optionIsTrue(
          'ssl-authentication'):
        ssl_snippet += self.substituteTemplate(self.getTemplateFilename('snippet.ssl.ca.in'), {
          'ca_certificate': self.options['ssl-authentication-certificate'],
          'ca_crl': self.options['ssl-authentication-crl'],
        })
      ssl_enable = 'SSLEngine on'
    else:
      raise ValueError('Unsupported scheme %s' % scheme)

    ip_list = self.options['ip']
    if isinstance(ip_list, basestring):
      ip_list = [ip_list]
    backend_path = self.options.get('backend-path', '/')
    vhost_template_name = self.getTemplateFilename('vhost.in')
    apache_config_file = self.createFile(
      self.options['configuration-file'],
      self.substituteTemplate(
        self.getTemplateFilename('apache.zope.conf.in'),
        {
          'path': '/',
          'server_admin': 'admin@',
          'pid_file': self.options['pid-file'],
          'lock_file': self.options['lock-file'],
          'error_log': self.options['error-log'],
          'access_log': self.options['access-log'],
          'access_control_string': self.options['access-control-string'],
          'ssl_snippet': ssl_snippet,
          'vhosts': ''.join(self.substituteTemplate(vhost_template_name, {
            'ip': ip,
            'port': port,
            'backend': ('%s/%s' % (backend.rstrip('/'), backend_path.strip('/'))).rstrip('/'),
            'ssl_enable': ssl_enable,
          }) for (port, backend) in backend_list for ip in ip_list),
        },
      )
    )
    return [
      apache_config_file,
      self.createPythonScript(
        self.options['wrapper'],
        __name__ + '.apache.runApache',
        [
          {
            'required_path_list': required_path_list,
            'binary': self.options['apache-binary'],
            'config': apache_config_file,
          },
        ],
      ),
    ]
