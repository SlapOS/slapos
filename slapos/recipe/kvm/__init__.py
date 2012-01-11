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
import zc.buildout
import pkg_resources
import ConfigParser
import hashlib

FALSE_VALUE_LIST = ['n', 'no', '0', 'false']

class Recipe(BaseSlapRecipe):

#   # To avoid magic numbers
#   VNC_BASE_PORT = 5900

  def _install(self):
    """
    Set the connection dictionnary for the computer partition and create a list
    of paths to the different wrappers

    Parameters : none

    Returns    : List path_list
    """
    self.path_list = []

    self.requirements, self.ws           = self.egg.working_set()
    self.cron_d                          = self.installCrond()

    self.ca_conf                         = self.installCertificateAuthority()
    self.key_path, self.certificate_path = self.requestCertificate('noVNC')

    # Install the socket_connection_attempt script
    catcher = zc.buildout.easy_install.scripts(
      [('check_port_listening', 'slapos.recipe.kvm.socket_connection_attempt',
        'connection_attempt')],
      self.ws,
      sys.executable,
      self.bin_directory,
    )
    # Save the check_port_listening script path
    check_port_listening_script = catcher[0]
    # Get the port_listening_promise template path, and save it
    self.port_listening_promise_path = pkg_resources.resource_filename(
      __name__, 'template/port_listening_promise.in')
    self.port_listening_promise_conf = dict(
     check_port_listening_script=check_port_listening_script,
    )

    vnc_port = Recipe.VNC_BASE_PORT + kvm_conf['vnc_display']

    noVNC_conf = self.installNoVnc(source_ip   = self.getGlobalIPv6Address(),
                                   source_port = 6080,
                                   target_ip   = kvm_conf['vnc_ip'],
                                   target_port = vnc_port)

    ipv6_url = 'https://[%s]:%s/vnc_auto.html?host=[%s]&port=%s&encrypt=1' % (
      noVNC_conf['source_ip'], noVNC_conf['source_port'],
      noVNC_conf['source_ip'], noVNC_conf['source_port'])

    # Request frontend slave instance, unless contrary is specified
    # XXX-Cedric : HARDCODE : during dev, request is OPT-IN
    request_frontend = self.parameter_dict.get('frontend', 'false')
    #request_frontend = self.parameter_dict.get('frontend', True)
    if not request_frontend in FALSE_VALUE_LIST:
      slave_frontend = self.request(
        # XXX-Cedric : Use KVM Software Type to instantiate kvmfrontend.
        #              kvmfrontend should be in KVM recipe but using different
        #              software type.
        software_release='/opt/slapdev/software/kvm-frontend/software.cfg',
        software_type='RootSoftwareInstance',
        partition_reference='frontend',
        shared=True,
        partition_parameter_kw={"host":noVNC_conf['source_ip'], 
            "port":noVNC_conf['source_port']}
      )
      url = '%s/vnc_auto.html?host=%s&port=%s&encrypt=1&path=%s' % (
        slave_frontend.getConnectionParameter('site_url'),
        slave_frontend.getConnectionParameter('domainname'),
        slave_frontend.getConnectionParameter('port'),
        slave_frontend.getConnectionParameter('resource'))
      connection_dict = dict(
        url = url,
        backend_url = ipv6_url,
        password = kvm_conf['vnc_passwd'])
    else:
      # No frontend : just set raw IPv6
      connection_dict = dict(
          url = ipv6_url,
          password = kvm_conf['vnc_passwd'])

    self.computer_partition.setConnectionDict(connection_dict)

    return self.path_list
