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

from slapos.recipe.librecipe import BaseSlapRecipe

class Recipe(BaseSlapRecipe):
  def _install(self):
    self.parameter_dict = self.computer_partition.getInstanceParameterDict()
    software_type = self.parameter_dict.get('slap_software_type', 'default')
    if software_type is None or software_type == 'RootSoftwareInstance':
      software_type = 'default'
    if "run_%s" % software_type in dir(self) and \
       callable(getattr(self, "run_%s" % software_type)):
      return getattr(self, "run_%s" % software_type)()
    else:
      raise NotImplementedError("Do not support %s" % software_type)

  def run_default(self):
    return self.run_cubrid()

  def run_cubrid(self):
    """ Run cubrid. """
    config_dict = {}
    config_dict.update(self.options)
    config_dict.update(self.parameter_dict)

    config_dict['cubrid_home'] = self.work_directory

    config_dict['cubrid_ip_address'] = "[%s]" % self.getGlobalIPv6Address()
    config_dict['cubrid_port_id'] = 1523

    config_dict['cubrid_database'] = os.path.join(self.var_directory,"cubrid.db")

    connection_dict = {}
    connection_dict['address'] = config_dict['cubrid_ip_address']
    connection_dict['port'] = config_dict['cubrid_port_id']
    self.computer_partition.setConnectionDict(connection_dict)

    cubrid_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'cubrid.in'))
    cubrid_runner_path = self.createRunningWrapper("cubrid",
          self.substituteTemplate(cubrid_wrapper_template_location, config_dict))

    return [cubrid_runner_path]

