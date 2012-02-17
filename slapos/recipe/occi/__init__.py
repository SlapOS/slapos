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
    occi_server_port = int(self.options['server-port'])
    occi_server_listen_port = int(self.options['server-listen-port'])
    path_list = []

    config = dict(
      occi_server_binary=self.options['occi-server-binary'],
      occi_server_ip=ip,
      occi_server_log=self.options['occi-server-log'],
      occi_server_port=occi_server_port,
      occi_server_listen_port=occi_server_listen_port,
    )

    path_list.append(self.createExecutable(self.options['server-wrapper'],
      self.substituteTemplate(self.getTemplateFilename('occi_server.in'),
        config)))

    return path_list
