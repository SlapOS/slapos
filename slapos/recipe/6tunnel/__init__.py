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

class Recipe(GenericBaseRecipe):
  """
  ipv4toipv6 tunnel configuration.
  """
  # Override in subclasses
  template_name = None

  def install(self):
    return [
      self.createExecutable(
        self.options['runner-path'],
        self.substituteTemplate(
          self.getTemplateFilename(self.template_name),
          {
            'ipv6': self.options['ipv6'],
            'ipv6_port': self.options['ipv6-port'],
            'ipv4': self.options['ipv4'],
            'ipv4_port': self.options['ipv4-port'],
            'shell_path': self.options['shell-path'],
            '6tunnel_path': self.options['6tunnel-path'],
          },
        ),
      )
    ]

class SixToFour(Recipe):
    template_name = '6to4.in'

class FourToSix(Recipe):
    template_name = '4to6.in'
