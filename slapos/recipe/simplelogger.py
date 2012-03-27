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
import shutil
import os
import sys
import time

from slapos.recipe.librecipe import GenericBaseRecipe

def log(args):
  directory, suffix = args
  filename = time.strftime('%Y-%m-%d.%H:%M.%s') + suffix
  with open(os.path.join(directory, filename), 'aw') as logfile:
    shutil.copyfileobj(sys.stdin, logfile)

class Recipe(GenericBaseRecipe):

  def install(self):
    self.logger.info("Simple logger installation")
    binary = self.options['binary']
    output = self.options['output']
    suffix = self.options.get('suffix', '.log')

    script = self.createPythonScript(binary,
                                     'slapos.recipe.simplelogger.log',
                                     arguments=[output, suffix])
    self.logger.debug("Logger script created at : %r", script)
    self.logger.info("Simple logger installed.")

    return [script]
