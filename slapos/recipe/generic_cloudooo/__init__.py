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
import zc.buildout
from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):
  def install(self):
    path_list = []
    conversion_server_dict = dict(
      working_path=self.options['data-directory'],
      uno_path=self.options['ooo-uno-path'],
      office_binary_path=self.options['ooo-binary-path'],
      ip=self.options['ip'],
      port=int(self.options['port']),
      openoffice_port=int(self.options['openoffice-port']),
    )
    for env_line in self.options['environment'].splitlines():
      env_line = env_line.strip()
      if not env_line:
        continue
      if '=' in env_line:
        env_key, env_value = env_line.split('=')
        conversion_server_dict[env_key.strip()] = env_value.strip()
      else:
        raise zc.buildout.UserError('Line %r in environment parameter is '
            'incorrect' % env_line)
    config_file = self.createFile(self.options['configuration-file'],
        self.substituteTemplate(self.getTemplateFilename('cloudooo.cfg.in'),
          conversion_server_dict))
    path_list.append(config_file)
    path_list.append(self.createPythonScript(self.options['wrapper'],
     'slapos.recipe.librecipe.execute.execute_with_signal_translation',
      [self.options['ooo-paster'].strip(), 'serve', config_file]))
    return path_list
