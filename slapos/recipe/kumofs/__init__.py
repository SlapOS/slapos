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
import zc.buildout
import zc.recipe.egg

class Recipe(BaseSlapRecipe):
  def getTemplateFilename(self, template_name):
    return pkg_resources.resource_filename(__name__,
        'template/%s' % template_name)

  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()
    # XXX-Cedric : add logrotate?
    kumo_conf = self.installKumo(self.getLocalIPv4Address())
    
    ca_conf = self.installCertificateAuthority()
    key, certificate = self.requestCertificate('Login Based Access')
    
    stunnel_conf = self.installStunnel(self.getGlobalIPv6Address(), 12345,
        kumo_conf_conf['kumo_gateway_port'],
        certificate, key, ca_conf['ca_crl'],
        ca_conf['certificate_authority_path'])
    
    self.linkBinary()
    self.setConnectionDict(dict(
      kumofs_local_ip = kumo_conf['kumo_gateway_ip'],
      stunnel_ip = stunnel_conf['ip'],
      stunnel_port = stunnel_conf['port'],
    ))
    return self.path_list

  def linkBinary(self):
    """Links binaries to instance's bin directory for easier exposal"""
    for linkline in self.options.get('link_binary_list', '').splitlines():
      if not linkline:
        continue
      target = linkline.split()
      if len(target) == 1:
        target = target[0]
        path, linkname = os.path.split(target)
      else:
        linkname = target[1]
        target = target[0]
      link = os.path.join(self.bin_directory, linkname)
      if os.path.lexists(link):
        if not os.path.islink(link):
          raise zc.buildout.UserError(
              'Target link already %r exists but it is not link' % link)
        os.unlink(link)
      os.symlink(target, link)
      self.logger.debug('Created link %r -> %r' % (link, target))
      self.path_list.append(link)
  
  def installKumo(self, ip, kumo_manager_port=13101, kumo_server_port=13201,
      kumo_server_listen_port=13202, kumo_gateway_port=13301):
    # XXX: kumo is not storing pid in file, unless it is not running as daemon
    #      but running daemons is incompatible with SlapOS, so there is currently
    #      no way to have Kumo's pid files to rotate logs and send signals to them
    config = dict(
      kumo_gateway_binary=self.options['kumo_gateway_binary'],
      kumo_gateway_ip=ip,
      kumo_gateway_log=os.path.join(self.log_directory, "kumo-gateway.log"),
      kumo_manager_binary=self.options['kumo_manager_binary'],
      kumo_manager_ip=ip,
      kumo_manager_log=os.path.join(self.log_directory, "kumo-manager.log"),
      kumo_server_binary=self.options['kumo_server_binary'],
      kumo_server_ip=ip,
      kumo_server_log=os.path.join(self.log_directory, "kumo-server.log"),
      kumo_server_storage=os.path.join(self.data_root_directory, "kumodb.tch"),
      kumo_manager_port=kumo_manager_port,
      kumo_server_port=kumo_server_port,
      kumo_server_listen_port=kumo_server_listen_port,
      kumo_gateway_port=kumo_gateway_port
    )

    self.path_list.append(self.createRunningWrapper('kumo_gateway',
      self.substituteTemplate(self.getTemplateFilename('kumo_gateway.in'),
        config)))

    self.path_list.append(self.createRunningWrapper('kumo_manager',
      self.substituteTemplate(self.getTemplateFilename('kumo_manager.in'),
        config)))

    self.path_list.append(self.createRunningWrapper('kumo_server',
      self.substituteTemplate(self.getTemplateFilename('kumo_server.in'),
        config)))

    return dict(
      kumo_address = '%s:%s' % (config['kumo_gateway_ip'],
        config['kumo_gateway_port']),
      kumo_gateway_ip=config['kumo_gateway_ip'],
      kumo_gateway_port=config['kumo_gateway_port'],
    )