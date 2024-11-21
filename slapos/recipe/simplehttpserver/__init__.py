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
import string, random
import os
from six.moves import range

from zc.buildout import UserError
from zc.buildout.buildout import bool_option


def issubpathof(subpath, path):
  subpath = os.path.abspath(subpath)
  path = os.path.abspath(path)
  relpath = os.path.relpath(subpath, start=path)
  return not relpath.startswith(os.pardir)


class Recipe(GenericBaseRecipe):
  def __init__(self, buildout, name, options):
    base_path = options['base-path']
    root_path = options.get('root-path')
    if root_path:
      if not issubpathof(root_path, base_path):
        raise UserError("root-path must be a subpath of base-path")
    else:
      root_path = base_path
    self.server_parameters = {
      'host': options['host'],
      'port': int(options['port']),
      'cwd': base_path,
      'log-file': options['log-file'],
      'cert-file': options.get('cert-file', ''),
      'key-file': options.get('key-file', ''),
      'root-path': root_path,
      'allow-write': bool_option(options, 'allow-write', 'false')
    }
    return GenericBaseRecipe.__init__(self, buildout, name, options)

  def install(self):
    return self.createPythonScript(
        self.options['wrapper'].strip(),
        __name__ + '.simplehttpserver.run',
        (self.server_parameters,)
      )
