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
import ConfigParser
import json
import os
import StringIO

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):
  def install(self):
    path_list = []
    options = self.options.copy()
    del options['recipe']
    CONFIG = {k.replace('-', '_'): v for k, v in options.iteritems()}
    CONFIG['PATH'] = os.environ['PATH']

    if CONFIG['bt5_path']:
      additional_bt5_repository_id_list = CONFIG['bt5_path'].split(",")
      CONFIG['bt5_path'] = ''
      for bt5_repository_id in additional_bt5_repository_id_list:
        id_path = os.path.join(CONFIG['slapos_directory'], bt5_repository_id)
        bt_path = os.path.join(id_path, "bt5")
        CONFIG['bt5_path'] += "%s,%s," % (id_path, bt_path)

    if self.options['instance-dict']:
      config_instance_dict = ConfigParser.ConfigParser()
      config_instance_dict.add_section('instance_dict')
      instance_dict = json.loads(self.options['instance-dict'])

      for k ,v in instance_dict.iteritems():
        config_instance_dict.set('instance_dict', k, v)
      value = StringIO.StringIO()
      config_instance_dict.write(value)
      CONFIG['instance_dict'] = value.getvalue()

    vcs_repository_list = json.loads(self.options['repository-list'])
    config_repository_list = ConfigParser.ConfigParser()
    i = 0
    for repository in vcs_repository_list:
      section_name = 'vcs_repository_%d' % i
      config_repository_list.add_section(section_name)
      config_repository_list.set(section_name, 'url', repository['url'])
      if 'branch' in repository:
        config_repository_list.set(section_name, 'branch', repository['branch'])
      if 'profile_path' in repository:
        config_repository_list.set(section_name, 'profile_path',
                                   repository['profile_path'])
      if 'buildout_section_id' in repository:
        config_repository_list.set(section_name, 'buildout_section_id',
                                   repository['buildout_section_id'])
      i += 1
    value = StringIO.StringIO()
    config_repository_list.write(value)
    CONFIG['repository_list'] = value.getvalue()

    configuration_file = self.createFile(
      self.options['configuration-file'],
      self.substituteTemplate(
        self.getTemplateFilename('erp5testnode.cfg.in'),
        CONFIG
      ),
    )
    path_list.append(configuration_file)
    path_list.append(
      self.createPythonScript(
        self.options['wrapper'],
        'slapos.recipe.librecipe.execute.executee',
        [ # Executable
          [ self.options['testnode'], '-l', self.options['log-file'],
            configuration_file],
          # Environment
          {
            'GIT_SSL_NO_VERIFY': '1',
          }
        ],
      )
    )
    return path_list
