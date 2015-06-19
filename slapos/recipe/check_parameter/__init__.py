# vim: set et sts=2:
##############################################################################
#
# Copyright (c) 2015 Vifib SARL and Contributors. All Rights Reserved.
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
import sys

class Recipe(GenericBaseRecipe):
  """
  Check listening port promise
  """

  def install(self):
    config = dict(
      value=self.options['value'],
      python_path=sys.executable,
    )

    if self.options.get('expected-type') == "ipv6":
      template = self.getTemplateFilename('check_ipv6.py.in')

    elif self.options.get('expected-type') == "ipv4":
      template = self.getTemplateFilename('check_ipv4.py.in')
    else:
      config["expected-value"] = self.options.get('expected-value')
 
      config["expected-not-value"] = self.options.get('expected-not-value')

      template = self.getTemplateFilename('check_parameter.py.in')

    promise = self.createExecutable(
      self.options['path'],
      self.substituteTemplate(template, config))

    return [promise]
