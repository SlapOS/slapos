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
import sys
from slapos.lib.recipe.BaseSlapRecipe import BaseSlapRecipe
import subprocess
import binascii
import random

import pkg_resources


class Recipe(BaseSlapRecipe):

  def _install(self):

    #Get the IP list
    connection_found = False
    ip = self.getGlobalIPv6Address()
    for tap, dummy in self.parameter_dict['ip_list']:
      # Get an ip associated to a tap interface
      if tap:
        connection_found = True
    if not connection_found:
      raise NotImplementedError("Do not support ip without tap interface")

    # Disk path
    disk_path = os.path.join(self.data_root_directory, 'virtual.qcow2')
    socket_path = os.path.join(self.var_directory, 'qmp_socket')
    # XXX Weak password
    vnc_passwd = binascii.hexlify(os.urandom(4))

    #XXX pid_file path, database_path and xml path
    pid_file_path = os.path.join(self.run_directory, 'pid_file')
    database_path = os.path.join(self.data_root_directory, 'slapmonitor_database')
    #xml_path = os.path.join(self.var_directory, 'slapreport.xml' )

    # Create disk if needed
    if not os.path.exists(disk_path):
      retcode = subprocess.call(["%s create -f qcow2 %s %iG" % (
          self.options['qemu_img_path'], disk_path,
          int(self.options['disk_size']))], shell=True)
      if retcode != 0:
        raise OSError, "Disk creation failed!"

    # Instanciate KVM
    kvm_config = {}
    # Options nbd_ip and nbd_port are provided by slapos master
    kvm_config.update(self.options)
    #raise NotImplementedError("%s" % self.parameter_dict)
    kvm_config['vnc_ip'] = ip
    kvm_config['tap_interface'] = tap
    kvm_config['nbd_ip'] = self.parameter_dict['nbd_ip']
    kvm_config['nbd_port'] = self.parameter_dict['nbd_port']
    #XXX
    kvm_config['pid_file'] = pid_file_path 
    kvm_config['image'] = disk_path
    # First octet has to represent a locally administered address
    octet_list = [254] + [random.randint(0x00, 0xff) for x in range(5)]
    kvm_config['mac_address'] = ':'.join(['%02x' % x for x in octet_list])
    kvm_config['qmp_socket'] = socket_path
    kvm_config['hostname'] = "slaposkvm"

    kvm_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'kvm_run.in'))
    kvm_runner_path = self.createRunningWrapper("kvm",
          self.substituteTemplate(kvm_wrapper_template_location, kvm_config))


    # Instanciate KVM controller
    controller_config = {}
    # Options nbd_ip and nbd_port are provided by slapos master
    controller_config.update(self.options)
    controller_config['qmp_socket'] = socket_path
    controller_config['vnc_passwd'] = vnc_passwd
    controller_config['python_path'] = sys.executable

    controller_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'kvm_controller_run.in'))
    controller_runner_path = self.createRunningWrapper("kvm_controller",
          self.substituteTemplate(controller_wrapper_template_location, controller_config))

    #XXX Instanciate Slapmonitor
    slapmonitor_config={}
    slapmonitor_config.update(self.options)
    slapmonitor_config['database_path'] = database_path 
    slapmonitor_config['pid_file'] = pid_file_path
    slapmonitor_config['python_path'] = sys.executable
    slapmonitor_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'slapmonitor_run.in'))
    slapmonitor_runner_path = self.createRunningWrapper("slapmonitor",
          self.substituteTemplate(slapmonitor_wrapper_template_location, slapmonitor_config))


    #XXX Instanciate Slapreport
    slapreport_config={}
    slapreport_config.update(self.options)
    slapreport_config['database_path'] = database_path 
    slapreport_config['python_path'] = sys.executable
    slapreport_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'slapreport_run.in'))
    slapreport_runner_path = self.createReportRunningWrapper(self.substituteTemplate(
                      slapreport_wrapper_template_location, slapreport_config))
    



    self.computer_partition.setConnectionDict(dict(
      vnc_connection_string="vnc://[%s]:1" % ip,
      vnc_password=vnc_passwd,
    ))

    return [kvm_runner_path, controller_runner_path]

