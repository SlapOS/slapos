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
import pkg_resources
import os
import zc.buildout

class Recipe(GenericBaseRecipe):
  """
  fontconfig instance configuration.

  conf-path -- location of the configuration file

  font-system-folder -- fonts installed by software release

  font-folder -- location where to download fonts

  url-list -- From where to download fonts
  """

  def install(self):
    created_file_list = []
    font_folder = self.options['font-folder']
    service_folder = self.options['service-folder']
    snippet_filename = self.getTemplateFilename(
                                    'fontconfig-snippet.cfg.in')
    font_snippet_list = [self.substituteTemplate(snippet_filename,
                    dict(font_folder_path=self.options['font-system-folder']))]
    font_snippet_list.append(self.substituteTemplate(snippet_filename,
                                           dict(font_folder_path=font_folder)))

    config = dict(
        font_folder_path_snippet=''.join(font_snippet_list),
        )
    template_filename = self.getTemplateFilename('fontconfig.cfg.in')
    configuration_path = self.createFile(
        self.options['conf-path'],
        self.substituteTemplate(template_filename, config))

    created_file_list.append(configuration_path)
    # Instanciate onetimedownloads, one for each url
    wrapper_template_location = pkg_resources.resource_filename(
                                        __name__, os.path.join(
                                        'template', 'onetimedownload_run.in'))

    onetimedownload_config = {}
    onetimedownload_config.update(self.options)
    for index, url in enumerate(self.options['url-list'].split()):
      if not url.strip():
        continue
      bin_path = os.path.join(service_folder, 'onetimedownload%s' % index)
      file_path = os.path.join(font_folder, '%s' % index)
      onetimedownload_config['url'] = url
      onetimedownload_config['file_path'] = file_path
      onetimedownload_runner_path = self.createExecutable(bin_path,
          self.substituteTemplate(wrapper_template_location, 
                                  onetimedownload_config))

      created_file_list.append(onetimedownload_runner_path)

    return created_file_list
