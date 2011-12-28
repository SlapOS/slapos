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
    path_list = []
    a = path_list.append
    configuration_file = self.createFile(self.options['configuration-path'], self.substituteTemplate(self.getTemplateFilename('tidstorage.py.in'), self.options))
    a(configuration_file)
    tidstorage_wrapper = self.createPythonScript(self.options['tidstorage-wrapper'], 'slapos.recipe.librecipe.execute.execute', [self.options['tidstoraged-binary'], '--nofork', '--config', configuration_file])
    a(tidstorage_wrapper)
    repozo_wrapper = self.createPythonScript(self.options['repozo-wrapper'], 'slapos.recipe.librecipe.execute.execute', [self.options['tidstorage-repozo-binary'], '--config', configuration_file, '--repozo', self.options['repozo-binary'], '-z'])
    a(repozo_wrapper)

    return path_list
