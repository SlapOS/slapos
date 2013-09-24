##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors. All Rights Reserved.
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

class Recipe(GenericBaseRecipe):
  """
  squid instance configuration.

  wrapper-path -- location of the init script to generate

  prepare-path -- location of the directory creation script to generate

  binary-path -- location of the squid command

  conf-path -- location of the configuration file

  cache-path -- location of the cache directory

  XXXX No good, specific...
  open_port -- entrance port to the host and allowed to use cache

  ip -- ip of the squid server

  port -- port of the squid server

  backend-ip -- ip of the service to cache

  backend-port -- port of the service to cache

  access-log-path -- location of the access log

  cache-log-path -- location of the cache log

  pid-filename-path -- location of the pid filename

  """

  def install(self):
    config = dict(
      ip=self.options['ip'], 
      port=self.options['port'],
      backend_ip=self.options['backend-ip'], 
      backend_port=self.options['backend-port'],
      cache_path=self.options['cache-path'],
      access_log_path=self.options['access-log-path'],
      cache_log_path=self.options['cache-log-path'],
      pid_filename_path=self.options['pid-filename-path'],
      open_port=self.options['open-port'],
      )

    template_filename = self.getTemplateFilename('squid.conf.in')
    configuration_path = self.createFile(
      self.options['conf-path'],
      self.substituteTemplate(template_filename, config))

    # Prepare directories
    prepare_path = self.createPythonScript(
      self.options['prepare-path'],
      'slapos.recipe.librecipe.execute.execute',
      arguments=[self.options['binary-path'].strip(), 
                 '-z',
                 '-f', configuration_path,
                 ],)

    # Create running wrapper
    wrapper_path = self.createPythonScript(
      self.options['wrapper-path'],
      'slapos.recipe.librecipe.execute.execute',
      arguments=[self.options['binary-path'].strip(), 
                 '-N',
                 '-f', configuration_path,
                 ],)

    return [configuration_path, wrapper_path, prepare_path]
