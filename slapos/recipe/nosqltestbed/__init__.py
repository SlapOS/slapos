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

import sys
import pkg_resources
from logging import Formatter
from slapos.recipe.librecipe import BaseSlapRecipe

class NoSQLTestBed(BaseSlapRecipe):

  def _install(self):
    self.parameter_dict = self.computer_partition.getInstanceParameterDict()
    try:
      entry_point = pkg_resources.iter_entry_points(group='slapos.recipe.nosqltestbed.plugin',
                                                    name=self.parameter_dict.get('plugin', 'kumo')).next()
      plugin_class = entry_point.load()

      testbed = plugin_class()
    except:
      print Formatter().formatException(sys.exc_info())
      return None

    software_type = self.parameter_dict.get('slap_software_type', 'default')
    if software_type is None or software_type == 'RootSoftwareInstance':
      software_type = 'default'
    if "run_%s" % software_type in dir(testbed) and \
       callable(getattr(testbed, "run_%s" % software_type)):
      return getattr(testbed, "run_%s" % software_type)(self)
    else:
      raise NotImplementedError("Do not support %s" % software_type)

