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
import binascii
import os
import sys

class Recipe(GenericBaseRecipe):
  """
  nginx instance configuration.
  """

  def install(self):
    config = dict(
      nb_workers = self.options["nb_workers"]
      path_pid = self.options["path_pid"]
      path_log = self.options["path_log"]
      path_access_log = self.options["path_access_log"]
      root = self.options["root"]
      ip = self.options["ip"]
      port = self.options["port"]
      path_shell = self.options["path_shell"]
      config_file = self.options["config_file"]
      path = self.options["path"]
    )
    
    # Configs
    nginx_conf_file = self.createFile(
      self.options['config_file'],
      self.substituteTemplate(self.getTemplateFilename('nginx_conf.in', config))
    )
    
    # Index default
    nginx_index_file = self.createFile(
      '/'.join([root,"index.html"),
      self.substituteTemplate(self.getTemplateFilename('nginx_index.in', config))
    )
    
    # Runners
    runner_path = self.createExecutable(
      self.options['path'],
      self.substituteTemplate(self.getTemplateFilename('nginx_run.in'),config))

    return [runner_path]
