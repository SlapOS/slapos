##############################################################################
#
# Copyright (c) 2012-2013 Vifib SARL and Contributors. All Rights Reserved.
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
import os
from slapos.recipe.librecipe import GenericBaseRecipe
from zc.buildout import UserError

class NeoBaseRecipe(GenericBaseRecipe):

  _binding_port_mandatory = True

  def install(self):
    options = self.options
    if not options['masters']:
      # All parameters are always provided.
      # This parameter needs special care, because it is initially generated
      # empty, until all requested master nodes get their partitions
      # allocated.
      # Only then can this recipe start succeeding and actually doing anything
      # useful, as per NEO deploying constraints.
      raise UserError('"masters" parameter is mandatory')
    option_list = [
      '-l', options['logfile'],
      '-m', options['masters'],
      '-b', self._getBindingAddress(),
      # TODO: reuse partition reference for better log readability.
      #'-n', options['name'],
      '-c', options['cluster'],
    ]
    if options['ssl']:
      etc = os.path.join(self.buildout['buildout']['directory'], 'etc', '')
      option_list += (
        '--ca', etc + 'ca.crt',
        '--cert', etc + 'neo.crt',
        '--key', etc + 'neo.key',
        )
    option_list.extend(self._getOptionList())
    return [self.createWrapper(
      options['wrapper'],
      options['binary'],
      option_list
    )]

  def _getBindingAddress(self):
    options = self.options
    bind = options['ip']
    if 'port' in options:
      # Some node types support port auto-allocation when no binding port is
      # requested.
      bind = bind + ':' + options['port']
    elif self._binding_port_mandatory:
      raise ValueError('"port" option is mandatory.')
    return bind

  def _getOptionList(self):
    raise NotImplementedError

class Storage(NeoBaseRecipe):

  _binding_port_mandatory = False

  def _getOptionList(self):
    r = [
      '-d', self.options['database-parameters'],
      '-a', self.options['database-adapter'],
      '-w', self.options['wait-database'],
    ]
    engine = self.options.get('engine')
    if engine: # old versions of NEO don't support -e
      r  += '-e', engine
    return r

class Admin(NeoBaseRecipe):
  def _getOptionList(self):
    return []

class Master(NeoBaseRecipe):
  def _getOptionList(self):
    options = self.options
    r = [
      '-p', options['partitions'],
      '-r', options['replicas'],
      '-A', options['autostart'],
    ]
    for x in (('-C', options['upstream-cluster']),
              ('-M', options['upstream-masters'])):
      if x[1]:
        r += x
    return r
