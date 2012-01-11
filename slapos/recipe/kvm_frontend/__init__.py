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
import os
import pkg_resources
import hashlib
import string
import sys
import zc.buildout
import zc.recipe.egg
import ConfigParser

TRUE_VALUE_LIST = ['y', 'yes', '1', 'true']
FALSE_VALUE_LIST = ['n', 'no', '0', 'false']

class Recipe(BaseSlapRecipe):

  def getTemplateFilename(self, template_name):
    return pkg_resources.resource_filename(__name__,
        'template/%s' % template_name)

  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()

#     frontend_port_number = self.parameter_dict.get("port", 4443)
#     frontend_domain_name = self.parameter_dict.get("domain",
#         "host.vifib.net")

    # Create http server redirecting (302) to https proxy?
    redirect_plain_http = self.parameter_dict.get("redirect_plain_http", '')
    if redirect_plain_http in TRUE_VALUE_LIST:
      redirect_plain_http = '1'
    
    # Cert stuffs
    valid_certificate_str = self.parameter_dict.get('domain_ssl_ca_cert')
    valid_key_str = self.parameter_dict.get('domain_ssl_ca_key')
    if valid_certificate_str is None and valid_key_str is None:
      ca_conf = self.installCertificateAuthority()
      key, certificate = self.requestCertificate(frontend_domain_name)
    else:
      ca_conf = self.installValidCertificateAuthority(
          frontend_domain_name, valid_certificate_str, valid_key_str)
      key = ca_conf.pop('key')
      certificate = ca_conf.pop('certificate')

    # Install node + js script
#     node_parameter_dict = self.installFrontendNode(
#         ip=self.getGlobalIPv6Address(),
#         port=frontend_port_number,
#         plain_http=redirect_plain_http,
#         name=frontend_domain_name,
#         slave_instance_list=self.parameter_dict.get('slave_instance_list', []),
#         key=key, certificate=certificate)

    # Send connection parameters of master instance
    site_url = node_parameter_dict['site_url']
    self.setConnectionDict(
      dict(site_url=site_url,
           domain_ipv6_address=self.getGlobalIPv6Address()))
    # Send connection parameters of slave instances
    for slave in node_parameter_dict['rewrite_rule_list']:
      self.setConnectionDict(
          dict(site_url="%s%s" % (site_url, slave['resource']),
               domainname=frontend_domain_name,
               port=frontend_port_number,
               resource=slave['resource']),
          slave['reference'])

    return self.path_list


  def installFrontendNode(self, ip, port, key, certificate, plain_http,
                            name, slave_instance_list):

    return dict(site_url="https://%s:%s/" % (name, port),
                rewrite_rule_list=rewrite_rule_list)
