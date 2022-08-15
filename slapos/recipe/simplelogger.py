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
import time

from slapos.recipe.librecipe import GenericBaseRecipe

def log(filename):
  prefix = time.strftime('%Y-%m-%d.%H:%M.%s:')
  with open(filename, 'a') as logfile:
    for line in sys.stdin:
      print >> logfile, prefix, line,
    print >> logfile, prefix, '------------------------'

class Recipe(GenericBaseRecipe):

  def install(self):
    return self.createPythonScript(
      self.options['wrapper'],
      __name__ + '.log',
      (self.options['log'],))
