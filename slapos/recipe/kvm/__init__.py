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
    self.path_list = []
    
    kvm_conf = self.installKvm(vnc_ip = self.getLocalIPv4Address())
    
    vnc_port = 5900 + kvm_conf['vnc_display']
    
    novnc_conf = self.installNovnc(source_ip = self.getGlobalIPv6Address(),
                                   source_port = 6080,
                                   target_ip = kvm_conf['vnc_ip'],
                                   target_port = vnc_port)
    
    self.linkBinary()
    self.computer_partition.setConnectionDict(dict(
        vnc_connection_string = "vnc://[%s]:%s" % (vnc_port['vnc_ip'],
                                                   vnc_port),
        vnc_password = vnc_passwd,
    ))
    return self.path_list

  def installKvm(self, vnc_ip):
    kvm_conf = dict(vnc_ip = vnc_ip)
    
    connection_found = False
    for tap_interface, dummy in self.parameter_dict['ip_list']:
      # Get an ip associated to a tap interface
      if tap_interface:
        connection_found = True
    if not connection_found:
      raise NotImplementedError("Do not support ip without tap interface")

    kvm_conf['tap_interface'] = tap_interface
    
    # Disk path
    kvm_conf['disk_path'] = os.path.join(self.data_root_directory,
        'virtual.qcow2')
    kvm_conf['socket_path'] = os.path.join(self.var_directory, 'qmp_socket')
    # XXX Weak password
    ##XXX -Vivien: add an option to generate one password for all instances 
    # and/or to input it yourself
    kvm_conf['vnc_passwd'] = binascii.hexlify(os.urandom(4))

    #XXX pid_file path, database_path, path to python binary and xml path
    kvm_conf['pid_file_path'] = os.path.join(self.run_directory, 'pid_file')
    kvm_conf['database_path'] = os.path.join(self.data_root_directory,
        'slapmonitor_database')
    kvm_conf['python_path'] = sys.executable
    #xml_path = os.path.join(self.var_directory, 'slapreport.xml' )

    # Create disk if needed
    if not os.path.exists(kvm_conf['disk_path']):
      retcode = subprocess.call(["%s create -f qcow2 %s %iG" % (
          self.options['qemu_img_path'], disk_path,
          int(self.options['disk_size']))], shell=True)
      if retcode != 0:
        raise OSError, "Disk creation failed!"
    
    # Options nbd_ip and nbd_port are provided by slapos master
    kvm_conf['nbd_ip'] = self.parameter_dict['nbd_ip']
    kvm_conf['nbd_port'] = self.parameter_dict['nbd_port']

    # First octet has to represent a locally administered address
    octet_list = [254] + [random.randint(0x00, 0xff) for x in range(5)]
    kvm_conf['mac_address'] = ':'.join(['%02x' % x for x in octet_list])

    kvm_conf['hostname'] = "slaposkvm"

    # Instanciate KVM

    kvm_runner_path = self.instanciate("kvm", kvm_conf)
    self.path_list.append(kvm_runner_path)
    # Instanciate KVM controller
    kvm_controller_runner_path = self.instanciate("kvm_controller", kvm_conf)
    self.path_list.append(kvm_controller_runner_path)
    # Instanciate Slapmonitor
    ##slapmonitor_runner_path = self.instanciate("slapmonitor",
    #    [database_path, pid_file_path, python_path])
    # Instanciate Slapreport
    ##slapreport_runner_path = self.instanciate("slapreport",
    #    [database_path, python_path])
    
    kvm_conf['vnc_display'] = 1
    return kvm_conf

  def installNoVnc(self, source_ip, source_port, target_ip, target_port):
    # Instanciate Websockify
    websockify_runner_path = self.instanciate("websockify",
        [python_path, vnc_ip, proxy_ip, vnc_port, proxy_port])
    self.path_list.append(websockify_runner_path)


  
  
  def instanciate_Wrapper(self, name, config_dictionnary):

    """
    Define the path to the wrapper of the thing you are instanciating
    
    Parameters : name of what you are instanciating, list of arguments for the 
    configuration dictionnary of the wrapper
    
    Returns    : path to the running wrapper
    """
    
    config_dictionnary.update(self.options)

    wrapper_template_location = pkg_resources.resource_filename(          
                                             __name__, os.path.join(          
                                             'template', 'name_run.in'))       
    
    runner_path = self.createRunningWrapper(name,                        
          self.substituteTemplate(wrapper_template_location, config_dictionnary))
    

    return name_runner_path

  def linkBinary(self):
    """Links binaries to instance's bin directory for easier exposal"""
    for linkline in self.options.get('link_binary_list', '').splitlines():
      if not linkline:
        continue
      target = linkline.split()
      if len(target) == 1:
        target = target[0]
        path, linkname = os.path.split(target)
      else:
        linkname = target[1]
        target = target[0]
      link = os.path.join(self.bin_directory, linkname)
      if os.path.lexists(link):
        if not os.path.islink(link):
          raise zc.buildout.UserError(
              'Target link already %r exists but it is not link' % link)
        os.unlink(link)
      os.symlink(target, link)
      self.logger.debug('Created link %r -> %r' % (link, target))
      self.path_list.append(link)

    return runner_path
