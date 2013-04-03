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

    config = dict(
      tap_interface=self.options['tap'],
      vnc_ip=self.options['vnc-ip'],
      vnc_port=self.options['vnc-port'],
      nbd_ip=self.options['nbd-host'],
      nbd_port=self.options['nbd-port'],
      nbd2_ip=self.options.get('nbd2-host', ''),
      nbd2_port=self.options.get('nbd2-port', 1024),
      disk_path=self.options['disk-path'],
      disk_size=self.options['disk-size'],
      disk_type=self.options['disk-type'],
      mac_address=self.options['mac-address'],
      smp_count=self.options['smp-count'],
      ram_size=self.options['ram-size'],
      socket_path=self.options['socket-path'],
      pid_file_path=self.options['pid-path'],
      python_path=sys.executable,
      shell_path=self.options['shell-path'],
      qemu_path=self.options['qemu-path'],
      qemu_img_path=self.options['qemu-img-path'],
      vnc_passwd=self.options['passwd']
    )

    # Runners
    runner_path = self.createExecutable(
      self.options['runner-path'],
      self.substituteTemplate(self.getTemplateFilename('kvm_run.in'),
                              config))

    controller_path = self.createExecutable(
      self.options['controller-path'],
      self.substituteTemplate(self.getTemplateFilename('kvm_controller_run.in'),
                              config))


    return [runner_path, controller_path]
