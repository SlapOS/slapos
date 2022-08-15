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
from zc.buildout import UserError

class Recipe(GenericBaseRecipe):

  def __init__(self, buildout, name, options):
    if not options['lockfile'].endswith('.lock'):
      raise UserError('lockfile parameter must end with .lock as equeue process will add .lock suffix')
    super(Recipe, self).__init__(buildout, name, options)

  def install(self):
    args = [
      self.options['equeue-binary'],
      '--database', self.options['database'],
      '--logfile', self.options['log'],
      '--lockfile', self.options['lockfile'][:-5]
    ]

    if 'takeover-triggered-file-path' in self.options:
      args += ('--takeover-triggered-file-path',
               self.options['takeover-triggered-file-path'])

    if 'loglevel' in self.options:
      args += '--loglevel', self.options['loglevel']

    args.append(self.options['socket'])

    return self.createWrapper(self.options['wrapper'], args)
