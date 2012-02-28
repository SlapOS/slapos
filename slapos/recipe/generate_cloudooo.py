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
from slapos.recipe.librecipe import GenericSlapRecipe
import os
import json
import traceback


class Recipe(GenericSlapRecipe):
  def _options(self, options):
    self.dirname = os.path.join(self.buildout['buildout']['parts-directory'],
                                self.name)
    options['output'] = os.path.join(self.dirname, self.name + '.cfg')

  def _generateRealTemplate(self):
    # TODO check json against schema
    json_data = {}
    if self.parameter_dict.get('cloudooo-json', None):
      json_data = json.loads(self.parameter_dict['cloudooo-json'])
    # dymanic fonts
    font_url_list = json_data.get('font_url_list', [])
    fontconfig_template = open(self.options['template']).read()
    fontconfig = open(self.options['snippet-fontconfig']).read()
    fontconfig_extension = fontconfig % dict(font_url_list=' '.join(font_url_list))
    with open(self.options['output'], 'w') as f:
      f.write(fontconfig_template + fontconfig_extension)

  def _install(self):
    if not os.path.exists(self.dirname):
      os.mkdir(self.dirname)
    try:
      self._generateRealTemplate()
    except Exception:
      print 'Ignored issue during template generation:\n%s' % \
        traceback.format_exc()
    return [self.dirname]
