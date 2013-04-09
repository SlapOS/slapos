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
import operator
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

    # XXX: add HTTP support
    #https_port_number = self.options['https-port']
    #http_port_number = self.options['http-port']

    # Parse list of slaves
    slave_instance_list = sorted(self.options['slave-instance-list'],
                                 key=operator.itemgetter('slave_reference'))

    # Now, we only take first instance and only use this one.
    # XXX: TODO real implementation of slaves
    zimbra_slave_instance = slave_instance_list[0]

    # Generate Nginx configuration
    nginx_configuration_dict = {
      'listen-local-ipv4': self.options['ipv4'],
      'listen-global-ipv6': '[%s]' % self.options['ipv6'],
      'domain-name': domain_name,
      'smtp-port-number': self.options['smtp-port'],
      'error-log': self.options['error-log'],
      'access-log': self.options['access-log'],
      'htdocs': self.options['htdocs'],
      'smtp-upstream-host': zimbra_slave_instance['smtp-upstream-host'],
      'smtp-upstream-port': zimbra_slave_instance['smtp-upstream-port'],
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

    # TODO: reload configuration or have feature like apache_map

    # Send connection informations about each slave
    for slave_instance in slave_instance_list:
      reference = slave_instance.get("slave_reference")
      self.logger.debug('Sending connection parameters of slave '
          'instance: %s' % reference)
      try:
        connection_dict = {
            'listening-ipv6': self.options['ipv6'],
            # Arbitrary, as the instance doesn't know its public IP.
            'listening-ipv4': self.options['public-ipv4'],
            # XXX-TODO
            #'site_url': url,
        }
        self.setConnectionDict(connection_dict, reference)
      except:
        self.logger.fatal("Error while sending slave %s informations: %s",
            reference, traceback.format_exc())

    return path_list
