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
from slapos.recipe.librecipe import GenericBaseRecipe
import binascii
import os
import sys

class Recipe(GenericBaseRecipe):
  """
  novnc instance configuration.
  """

  def install(self):
    runner_path = self.createPythonScript(
      self.options['path'],
      'slapos.recipe.librecipe.execute.execute_wait',
      [[
        self.options['websockify-path'],
        '--web',
        self.options['novnc-location'],
        '--key=%s' % self.options['ssl-key-path'],
        '--cert=%s' % self.options['ssl-cert-path'],
        '--ssl-only',
        '%s:%s' % (self.options['ip'], self.options['port']),
        '%s:%s' % (self.options['vnc-ip'], self.options['vnc-port']),
      ],
      [self.options['ssl-key-path'], self.options['ssl-cert-path']]],
    )

    return [runner_path]
