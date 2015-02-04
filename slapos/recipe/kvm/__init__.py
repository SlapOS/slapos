##############################################################################
#
# Copyright (c) 2011 Vifib SARL and Contributors. All Rights Reserved.
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
import os
import sys

class Recipe(GenericBaseRecipe):
  """
  kvm instance configuration.
  """
  def install(self):
    # Sanitize drive type parameter
    self.options.setdefault('disk-type', 'virtio')
    if not self.options.get('disk-type') in ['ide', 'scsi', 'sd',
        'mtd', 'floppy', 'pflash', 'virtio']:
      print 'Warning: "disk-type" parameter is not in allowed values. Using ' \
          '"virtio" value.'
      self.options['disk-type'] = 'virtio'

    self.options['python-path'] = sys.executable

    path_list = []

    if self.isTrueValue(self.options.get('use-nat')):
      # XXX This could be done using Jinja.
      for port in self.options['nat-rules'].split():
        tunnel_port = int(port) + 10000
        tunnel_path = self.createExecutable(
            '%s-%s' % (self.options['6tunnel-wrapper-path'], tunnel_port),
            self.substituteTemplate(
                self.getTemplateFilename('6to4.in'),
                {
                    'ipv6': self.options['ipv6'],
                    'ipv6_port': tunnel_port,
                    'ipv4': self.options['ipv4'],
                    'ipv4_port': tunnel_port,
                    'shell_path': self.options['shell-path'],
                    '6tunnel_path': self.options['6tunnel-path'],
                },
            ),
        )
        path_list.append(tunnel_path)

    runner_path = self.createExecutable(
        self.options['runner-path'],
        self.substituteTemplate(self.getTemplateFilename('kvm_run.in'),
                                self.options))
    path_list.append(runner_path)

    controller_path = self.createExecutable(
      self.options['controller-path'],
      self.substituteTemplate(self.getTemplateFilename('kvm_controller_run.in'),
                              self.options))


    return path_list
