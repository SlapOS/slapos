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
import os
from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):
  def install(self):
    ip = self.options['ip']
    kumo_manager_port = int(self.options['manager-port'])
    kumo_server_port = int(self.options['server-port'])
    kumo_server_listen_port = int(self.options['server-listen-port'])
    kumo_gateway_port = int(self.options['gateway-port'])
    path_list = []
    # XXX: kumo is not storing pid in file, unless it is not running as daemon
    #      but running daemons is incompatible with SlapOS, so there is currently
    #      no way to have Kumo's pid files to rotate logs and send signals to them
    config = dict(
      kumo_gateway_binary=self.options['kumo-gateway-binary'],
      kumo_gateway_ip=ip,
      kumo_gateway_log=self.options['kumo-gateway-log'],
      kumo_manager_binary=self.options['kumo-manager-binary'],
      kumo_manager_ip=ip,
      kumo_manager_log=self.options['kumo-manager-log'],
      kumo_server_binary=self.options['kumo-server-binary'],
      kumo_server_ip=ip,
      kumo_server_log=self.options['kumo-server-log'],
      kumo_server_storage=os.path.join(self.options['data-directory'], "kumodb.tch"),
      kumo_manager_port=kumo_manager_port,
      kumo_server_port=kumo_server_port,
      kumo_server_listen_port=kumo_server_listen_port,
      kumo_gateway_port=kumo_gateway_port
    )

    path_list.append(self.createExecutable(self.options['gateway-wrapper'],
      self.substituteTemplate(self.getTemplateFilename('kumo_gateway.in'),
        config)))

    path_list.append(self.createExecutable(self.options['manager-wrapper'],
      self.substituteTemplate(self.getTemplateFilename('kumo_manager.in'),
        config)))

    path_list.append(self.createExecutable(self.options['server-wrapper'],
      self.substituteTemplate(self.getTemplateFilename('kumo_server.in'),
        config)))

    return path_list
