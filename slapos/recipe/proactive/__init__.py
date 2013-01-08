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
from slapos.recipe.librecipe import BaseSlapRecipe
import os
import pkg_resources

class Recipe(BaseSlapRecipe):

  def _install(self):
    parameter_dict = self.computer_partition.getInstanceParameterDict()
    #ipv4 = self.getLocalIPv4Address(parameter_dict)
    #ipv6 = self.getGlobalIPv6Address(parameter_dict)

    proactive_home = self.options['proactive_location']

    # ProActive parameters
    proactive_rmUrl = parameter_dict.get('rmURL')
    proactive_credential = parameter_dict.get('credentials')
    proactive_nsname = parameter_dict.get('nsName')

    #proactive conf
    conf_dir = os.path.join(self.work_directory, ".proactive")
    proactive_configuration_file = os.path.join(conf_dir,
        "ProActiveConfiguration.xml")
    if not os.path.isdir(conf_dir):
      os.mkdir(conf_dir)
    proactive_dict = dict(
      # Proactive daemon need to connect to a router.
      router_address="2a01:e34:ec03:8610:20c:29ff:feda:5d3f", #parameter_dict['router_address'],
      port=8090 #parameter_dict['router_port']
        )
    self._writeFile(proactive_configuration_file, pkg_resources.resource_string(
      __name__, 'template/ProActiveConfiguration.xml.in') % proactive_dict)

    # ProActive wrapper
    #proactive = os.path.join(proactive_home, 'bin', 'unix', 'rm-start-node')
    proactive_pa_bundle = os.path.join(proactive_home, 'PABundle')
    proactive = os.path.join(proactive_pa_bundle, 'startNode.sh')
    proactive_wrapper = self.createRunningWrapper('proactive_wrapper',
        """#!/bin/sh
export JAVA_HOME=%(java_home)s
cd %(bundle)s
sh %(proactive)s %(rmUrl)s %(nsname)s %(credential)s
""" % dict(java_home=self.options['java_home'].strip(),
  bundle = proactive_pa_bundle,
  proactive = proactive,
  rmUrl = proactive_rmUrl,
  credential = proactive_credential,
  nsname = proactive_nsname))
    self.computer_partition.setConnectionDict(dict(
      #proactive_ip="[%s]" % (ipv6),
      ))
    return [proactive_configuration_file, proactive_wrapper]
