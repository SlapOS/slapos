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

import os
import sys
import zc.buildout
import slapos.slap
from slapos.recipe.librecipe import BaseSlapRecipe
from slapos.recipe.librecipe import GenericSlapRecipe
import json
import ConfigParser

# XXX: BaseSlapRecipe and GenericSlapRecipe are deprecated, use
# GenericBaseRecipe and move partition parameter fetching to software release.
class Recipe(BaseSlapRecipe, GenericSlapRecipe):
  def install(self):
    self.path_list = []
    crond = self.installCrond()

    slap = slapos.slap.slap()
    slap.initializeConnection(self.server_url, self.key_file, self.cert_file)
    parameter_dict = slap.registerComputerPartition(
      self.computer_id,
      self.computer_partition_id,
    ).getInstanceParameterDict()

    # XXX: should probably expect one more (SR-originating) parameter instead
    # of using self.work_directory .
    configuration_path = os.path.join(self.work_directory, "agent.cfg")
    with open(configuration_path, "w") as configuration:
      configuration.write(parameter_dict["configuration"])
    agent_crond_path = os.path.join(crond, "agent")
    with open(agent_crond_path, "w") as agent_crond:
      agent_crond.write("*/5 * * * * %s -S %s --pidfile=%s --log=%s "
        "%s 2>&1 > /dev/null\n" % (
          self.options["python_binary"],
          self.options["agent_binary"],
          self.options["pidfile"],
          self.options["log"],
          configuration_path,
      ))

    return self.path_list + [configuration_path, agent_crond_path]

  def installCrond(self):
    _, ws = self.egg.working_set()
    timestamps = self.createDataDirectory('cronstamps')
    cron_output = os.path.join(self.log_directory, 'cron-output')
    self._createDirectory(cron_output)
    catcher = zc.buildout.easy_install.scripts([('catchcron',
      __name__ + '.catdatefile', 'catdatefile')], ws, sys.executable,
      self.bin_directory, arguments=[cron_output])[0]
    self.path_list.append(catcher)
    cron_d = os.path.join(self.etc_directory, 'cron.d')
    crontabs = os.path.join(self.etc_directory, 'crontabs')
    self._createDirectory(cron_d)
    self._createDirectory(crontabs)
    wrapper = zc.buildout.easy_install.scripts([('crond',
      'slapos.recipe.librecipe.execute', 'execute')], ws, sys.executable,
      self.wrapper_directory, arguments=[
        self.options['dcrond_binary'].strip(), '-s', cron_d, '-c', crontabs,
        '-t', timestamps, '-f', '-l', '5', '-M', catcher]
      )[0]
    self.path_list.append(wrapper)
    return cron_d
