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
#############################################################################

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):
  def install(self):

    config = {
      'xvfb_binary': self.options['xvfb-path'],
      'shell_path': self.options['shell-path'],
      'fbdir_path': self.options['fbdir-path'],
      'tmp_path': self.options['tmp-path'],
      }

    xvfb_path = self.createExecutable(
      self.options['runner-path'],
      self.substituteTemplate(self.getTemplateFilename('xvfb_run.in'),
                              config))
    result = [xvfb_path]

    # Allow to take screenshot if needed
    if ('xwd-path' in self.options) and ('xwd-hook-path' in self.options):

      config['xwd_binary'] = self.options['xwd-path']
      result.append(self.createExecutable(
        self.options['xwd-hook-path'],
        self.substituteTemplate(self.getTemplateFilename('xwd_run.in'),
                                config)))

    return result

