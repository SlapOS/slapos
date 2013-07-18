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
import ConfigParser

class Recipe(GenericBaseRecipe):
  """
  Generate ERP5 promise configuration file
  """

  def install(self):
    promise_parser = ConfigParser.RawConfigParser()
    for section_name, option_id_list in (
          ('portal_templates', (
            ('repository', 'bt5-repository-url'),
            ('expected_bt5', 'bt5'),
          )),
          ('external_service', (
            ('cloudooo_url', 'cloudooo-url'),
            ('memcached_url', 'memcached-url'),
            ('kumofs_url', 'kumofs-url'),
            ('smtp_url', 'smtp-url'),
          )),
        ):
      promise_parser.add_section(section_name)
      for internal_id, option_id in option_id_list:
        option = self.options.get(option_id)
        if option:
          promise_parser.set(section_name, internal_id, option)
    promise_parser.write(open(self.options['promise-path'], 'w'))
    return [self.options['promise-path']]
