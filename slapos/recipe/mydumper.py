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
import subprocess

from slapos.recipe.librecipe import GenericBaseRecipe

def dump(args):
  mydumper_binary = args['mydumper']
  database = args['database']
  socket = args['socket']
  directory = args['directory']

  mydumper_cmd = [mydumper_binary,
                  '-B', database,
                  '-u', 'root',
                  '-S', socket,
                  '-o', directory,
                 ]

  subprocess.check_call(mydumper_cmd)

class Recipe(GenericBaseRecipe):

  def install(self):
    # Host or socket should be defined
    try:
      self.options['host']
    except:
      self.options['socket']

    config = dict(database=self.options['database'],
                  socket=self.options.get('socket'),
                  host=self.options.get('host'),
                  port=self.options.get('port', 3306),
                  directory=self.options['backup-directory'],
                  user=self.options['user'],
                  password=self.options.get('password'),
                  compression=self.optionIsTrue('compression', default=False)
                 )

    name = __name__
    if self.optionIsTrue('import', False):
      config.update(mydumper=self.options['myloader-binary'])
      name += '.do_import'
    else:
      config.update(mydumper=self.options['mydumper-binary'])
      name += '.dump'

    wrapper = self.createPythonScript(self.options['wrapper'],
                                      name,
                                      config)

    return [wrapper]
