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
from slapos.recipe.librecipe import GenericSlapRecipe
import zc.buildout

class Recipe(GenericSlapRecipe):
  def _install(self):
    path_list = []

    # Check for mandatory arguments
    domain_name = self.options['domain']
    if not domain_name:
      raise zc.buildout.UserError('No domain name specified. Please define '
          'the "domain" instance parameter.')

    # Fetch all parameters
    https_port_number = self.options['https-port']
    http_port_number = self.options['http-port']
    smtp_port_number = self.options['smtp-port']
    slave_instance_list = self.options['slave-instance-list']
    ipv4 = self.options['ipv4']
    ipv6 = '[%s]' % self.options['ipv6']
    access_log = self.options['access-log']
    error_log = self.options['error-log']
    htdocs = self.options['htdocs']

    # Parse list of slaves

    # Generate Nginx configuration
    nginx_configuration_dict = {
      'listen_local_ipv4': ipv4,
      'listen_global_ipv6': ipv6,
      'domain_name': domain_name,
      'smtp_port_number': smtp_port_number,
      'error_log': error_log,
      'access_log': access_log,
      'htdocs': htdocs,
    }
    nginx_configuration_file = self.createFile(
        self.options['configuration-file'],
        self.substituteTemplate(self.getTemplateFilename('nginx.conf.in'),
        nginx_configuration_dict)
    )
    path_list.append(nginx_configuration_file)
    
    # Generate Nginx wrapper
    wrapper = self.createWrapper(
        name=self.options['wrapper'],
        command=self.options['nginx-executable'],
        parameters=[
            '-c', self.options['configuration-file'],
            '-p', self.options['home-directory']
        ]
    )

    # Send connection parameters for master instance
    
    # Send connection parameters for each slave instance

    return path_list
