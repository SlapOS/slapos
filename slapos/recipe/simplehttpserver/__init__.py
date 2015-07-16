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

class Recipe(GenericBaseRecipe):

  def __init__(self, buildout, name, options):

    base_path = options['base-path']
    if options.get('use-hash-url', 'True') in ['true', 'True']:
      pool = string.letters + string.digits
      hash_string = ''.join(random.choice(pool) for i in xrange(64))
      path = os.path.join(base_path, hash_string)
  
      if os.path.exists(base_path):
        path_list = os.listdir(base_path)
        if len(path_list) == 1:
          hash_string = path_list[0]
          path = os.path.join(base_path, hash_string)
        elif len(path_list) > 1:
          raise ValueError("Folder %s should contain 0 or 1 element." % base_path)
  
      options['root-dir'] = path
      options['path'] = hash_string
    else:
      options['root-dir'] = base_path
      options['path'] = ''
    return GenericBaseRecipe.__init__(self, buildout, name, options)


  def install(self):

    if not os.path.exists(self.options['root-dir']):
      os.mkdir( self.options['root-dir'] )
    parameters = {
      'host': self.options['host'],
      'port': int(self.options['port']),
      'cwd': self.options['base-path'],
      'log-file': self.options['log-file'],
      'cert-file': self.options.get('cert-file', ''),
      'key-file': self.options.get('key-file', ''),
      'root-dir': self.options['root-dir']
    }

    server = self.createPythonScript(
        self.options['wrapper'].strip(),
        '%s.simplehttpserver.run' % __name__, parameters
      )

    return [server]
