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

import zc.buildout
from slapos.recipe.librecipe import GenericBaseRecipe
import sys

class Recipe(GenericBaseRecipe):
  def install(self):
    path_list = []

    configuration_path = self.options["config"]
    header = """[DEFAULT]
master_url = %s
key = %s

cert = %s

max_install_duration = %s
max_uninstall_duration = %s
max_request_duration = %s
max_destroy_duration = %s
""" % (self.options["master-url"],
      "\n  ".join(self.options["key"].split("\n")),
       "\n  ".join(self.options["cert"].split("\n")),
       self.options["default_max_install_duration"],
       self.options["default_max_uninstall_duration"],
       self.options["default_max_request_duration"],
       self.options["default_max_destroy_duration"])

    with open(configuration_path, "w") as configuration:
      configuration.write(header + self.options["configuration"])

    path_list.append(self.createPythonScript(
                       self.options['wrapper'],
                       'slapos.recipe.librecipe.execute.execute',
                         [self.options["agent_binary"], '--pidfile=%s' % self.options["pidfile"],
                          "--log=%s" % self.options["log"], configuration_path]))

    path_list.append(configuration_path)

    return path_list
