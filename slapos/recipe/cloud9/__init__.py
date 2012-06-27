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
from slapos.recipe.librecipe import GenericBaseRecipe
import os

class Recipe(GenericBaseRecipe):
  """Deploy a fully operational cloud9 service."""

  def _options(self, options):
    self.ip = options['ip'].strip()
    self.port = options['port'].strip()
    self.git = options['git-binary'].strip()
    self.node_executable = options['node-binary'].strip()
    self.cloud9 = options['cloud9'].strip()
    self.workdir = options['working-directory'].strip()
    self.wrapper = options['wrapper'].strip()
    # Set cloud9 access URL
    options['access-url'] = 'http://[%s]:%s' % (self.ip, self.port)

  def install(self):
    path_list = []

    environment = {
        'PATH': os.path.dirname(self.git) + ':' + os.environ['PATH'],
    }

    cloud9_args = [self.node_executable, self.cloud9, '-l', self.ip, '-p',
        self.port, '-w', self.workdir]

    wrapper = self.createPythonScript(self.wrapper,
        'slapos.recipe.librecipe.execute.executee',
        (cloud9_args, environment)
    )
    path_list.append(wrapper)

    return path_list
