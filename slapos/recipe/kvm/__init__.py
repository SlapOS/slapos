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
from slapos.recipe.librecipe import BaseSlapRecipe
import subprocess
import binascii
import random

import pkg_resources


class Recipe(BaseSlapRecipe):

  def _install(self):

    #Get the IP list
    connection_found = False
    proxy_ip   = self.getGlobalIPv6Address()
    proxy_port = 6080
    vnc_ip     = self.getLocalIPv4Address()
    vnc_port   = 5901

    for tap_interface, dummy in self.parameter_dict['ip_list']:
      # Get an ip associated to a tap interface
      if tap_interface:
        connection_found = True
    if not connection_found:
      raise NotImplementedError("Do not support ip without tap interface")

    # Disk path
    disk_path   = os.path.join(self.data_root_directory, 'virtual.qcow2')
    socket_path = os.path.join(self.var_directory, 'qmp_socket')
    # XXX Weak password
    ##XXX -Vivien: add an option to generate one password for all instances and/or to input it yourself
    vnc_passwd  = binascii.hexlify(os.urandom(4))

    #XXX pid_file path, database_path, path to python binary and xml path
    pid_file_path = os.path.join(self.run_directory, 'pid_file')
    database_path = os.path.join(self.data_root_directory, 'slapmonitor_database')
    python_path   = sys.executable
    #xml_path = os.path.join(self.var_directory, 'slapreport.xml' )

    # Create disk if needed
    if not os.path.exists(disk_path):
      retcode = subprocess.call(["%s create -f qcow2 %s %iG" % (
          self.options['qemu_img_path'], disk_path,
          int(self.options['disk_size']))], shell=True)
      if retcode != 0:
        raise OSError, "Disk creation failed!"
    
    # Options nbd_ip and nbd_port are provided by slapos master
    nbd_ip   = self.parameter_dict['nbd_ip']
    nbd_port = self.parameter_dict['nbd_port']

    # First octet has to represent a locally administered address
    octet_list  = [254] + [random.randint(0x00, 0xff) for x in range(5)]
    mac_address = ':'.join(['%02x' % x for x in octet_list])

    hostname = "slaposkvm"

    #raise NotImplementedError("%s" % self.parameter_dict)

    self.computer_partition.setConnectionDict(dict(
      vnc_connection_string = "vnc://[%s]:1" % vnc_ip,
      vnc_password          = vnc_passwd,
    ))

    # Instanciate KVM
    kvm_runner_path            = self.instanciate("kvm", [vnc_ip, tap_interface, nbd_ip, nbd_port, pid_file_path, disk_path, mac_address, socket_path, hostname])
    # Instanciate KVM controller
    kvm_controller_runner_path = self.instanciate("kvm_controller", [socket_path, vnc_passwd, python_path])
    #XXX Instanciate Slapmonitor
    ##slapmonitor_runner_path    = self.instanciate("slapmonitor", [database_path, pid_file_path, python_path])
    #XXX Instanciate Slapreport
    ##slapreport_runner_path     = self.instanciate("slapreport", [database_path, python_path])
    #XXX Instanciate Websockify
    websockify_runner_path     = self.instanciate("websockify", [python_path, vnc_ip, proxy_ip, vnc_port, proxy_port])


    return [kvm_runner_path, kvm_controller_runner_path, websockify_runner_path]
  
  def instanciate(self, name, list):
    """
    Define the path to the wrapper of the thing you are instanciating
    
    Parameters : name of what you are instanciating, list of arguments for the configuration dictionnary of the wrapper
    
    Returns    : path to the running wrapper
    """
    name_config = {}
    name_config.update(self.options)

    for e in list:
      name_config['i'] = i

    name_wrapper_template_location = pkg_resources.resource_filename(          
                                             __name__, os.path.join(          
                                             'template', 'name_run.in'))       
    
    name_runner_path = self.createRunningWrapper(name,                        
          self.substituteTemplate(name_wrapper_template_location, name_config))
    
    return name_runner_path
