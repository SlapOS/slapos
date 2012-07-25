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

import ConfigParser

# XXX : This is in order to get the computer_partition object
#       which exposes the state of the current partition.
#
# XXX : We could have modify slapgrid in order to put the
#       state of the current partition offline. But this is
#       written to have the most minimal impact.
from slapos.recipe.librecipe import GenericSlapRecipe

class Recipe(GenericSlapRecipe):

    def _install(self):
        path_list = []

        self.logger.info("Putting slapcontainer configuration file...")

        config = ConfigParser.ConfigParser()
        config.add_section('requested')
        config.set('requested', 'status',
                   self.computer_partition.getState())
        config.add_section('network')
        config.set('network', 'ipv6', self.options['ipv6'])
        config.set('network', 'ipv4', self.options['ipv4'])
        config.set('network', 'interface', self.options['interface'])
        config.add_section('rootfs')
        config.set('rootfs', 'directory', self.options['rootfs'])
        config.set('rootfs', 'tmp', self.options['tmp-dir'])
        config.add_section('config')
        config.set('config', 'file', self.options['config-file'])
        config.add_section('tar')
        config.set('tar', 'binary', self.options['tar-binary'])
        config.set('tar', 'path', self.options['tar-path'])

        config_filename = self.options['config']
        with open(config_filename, 'w') as config_file:
            config.write(config_file)
        path_list.append(config_filename)

        return path_list
