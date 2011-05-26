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
import os
import binascii
from slapos.recipe.librecipe import BaseSlapRecipe

import pkg_resources

class Recipe(BaseSlapRecipe):

  def _install(self):

    # Image path
    cdrom_iso = os.path.join(self.data_root_directory, 'cdrom.iso')

    #Get the IP list
    ip = self.getGlobalIPv6Address()
    http_port = 9999
    nbd_port = 1024

    # Instanciate onetimeupload
    onetimeupload_config = {}
    onetimeupload_config.update(self.options)
    onetimeupload_config['port'] = http_port
    onetimeupload_config['ip'] = ip
    onetimeupload_config['image'] = cdrom_iso
    onetimeupload_config['key'] = binascii.hexlify(os.urandom(24))
    onetimeupload_config['log_path'] = os.path.join(self.log_directory, 
                                                    'onetimeupload.log')

    wrapper_template_location = pkg_resources.resource_filename(
                                       __name__, os.path.join(
                                       'template', 'onetimeupload_run.in'))
    onetimeupload_runner_path = self.createRunningWrapper("onetimeupload",
        self.substituteTemplate(wrapper_template_location, 
                                onetimeupload_config))

    # Instanciate qemu
    qemu_config = {}
    qemu_config.update(self.options)
    qemu_config['ip'] = ip
    qemu_config['port'] = nbd_port
    qemu_config['image'] = cdrom_iso

    wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'nbdserver_run.in'))
    nbdserver_runner_path = self.createRunningWrapper("nbdserver",
        self.substituteTemplate(wrapper_template_location, qemu_config))

    # Publish connection dict
    self.computer_partition.setConnectionDict(dict(
      upload_connection_string="https://[%s]:%s/" % (ip, http_port),
      upload_key=onetimeupload_config['key'],
      nbd_connection_string="nbd:[%s]:%s" % (ip, nbd_port),
      ))

    return [onetimeupload_runner_path, nbdserver_runner_path]
