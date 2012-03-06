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
import shutil
from slapos.recipe.librecipe import GenericBaseRecipe
from subprocess import Popen

class Recipe(GenericBaseRecipe):
  def install(self):
    path_list = []
    poc_location = self.buildout['pocdirectory']['poc']

    # Generate os-config.xml
    os_config_parameters = dict(
        userid=self.options['userid'],
        password=self.options['password'],
        domain=self.options['domain'],
    )
    os_config_file = self.createFile(self.options['os-config'],
        self.substituteTemplate(self.getTemplateFilename('os-config.xml.in'),
        os_config_parameters))
    path_list.append(os_config_file)
    
    # Initiate configuration
    Popen('./accords-config',
          cwd=poc_location
    ).communicate()

    # Generate manifest
    manifest_origin_location = self.options['manifest-source']
    manifest_location = self.options['manifest-destination']
    
    shutil.copy(manifest_origin_location, manifest_location)
    path_list.append(manifest_location)

    # Generate wrapper
    wrapper_config_dict = dict(
        poc_location=poc_location,
        manifest_name=self.options['manifest-name'],
        # XXX this is workaround
        accords_lib_directory=self.options['accords_lib_directory'])
    path_list.append(self.createExecutable(self.options['accords'],
      self.substituteTemplate(self.getTemplateFilename('accords.in'),
        wrapper_config_dict)))

    return path_list
