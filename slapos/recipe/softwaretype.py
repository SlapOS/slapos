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
import copy
from ConfigParser import ConfigParser
import json
import subprocess
import slapos.slap
import netaddr
import logging

import zc.buildout

class Recipe:

  def __init__(self, buildout, name, options):
    self.buildout = buildout
    self.options = options
    self.name = name
    self.logger = logging.getLogger(self.name)

  def _getIpAddress(self, test_method):
    """Internal helper method to fetch ip address"""
    if not 'ip_list' in self.parameter_dict:
      raise AttributeError
    for name, ip in self.parameter_dict['ip_list']:
      if test_method(ip):
        return ip
    raise AttributeError

  def getLocalIPv4Address(self):
    """Returns local IPv4 address available on partition"""
    # XXX: Lack checking for locality of address
    return self._getIpAddress(netaddr.valid_ipv4)

  def getGlobalIPv6Address(self):
    """Returns global IPv6 address available on partition"""
    # XXX: Lack checking for globality of address
    return self._getIpAddress(netaddr.valid_ipv6)

  def install(self):
    slap = slapos.slap.slap()
    slap_connection = self.buildout['slap_connection']
    computer_id = slap_connection['computer_id']
    computer_partition_id = slap_connection['partition_id']
    server_url = slap_connection['server_url']
    key_file = slap_connection.get('key_file')
    cert_file = slap_connection.get('cert_file')
    slap.initializeConnection(server_url, key_file, cert_file)
    self.computer_partition = slap.registerComputerPartition(
      computer_id,
      computer_partition_id)
    self.parameter_dict = self.computer_partition.getInstanceParameterDict()
    software_type = self.parameter_dict['slap_software_type']

    if software_type not in self.options:
      if 'default' in self.options:
        software_type = 'default'
      else:
        raise zc.buildout.UserError("This software type isn't mapped. And "
                                    "there's no default software type.")

    instance_file_path = self.options[software_type]

    if not os.path.exists(instance_file_path):
      raise zc.buildout.UserError("The specified buildout config file %r does "
                                  "not exist." % instance_file_path)

    buildout = ConfigParser()
    with open(instance_file_path) as instance_path:
      buildout.readfp(instance_path)

    buildout.set('buildout', 'installed', '.installed-%s.cfg' % self.name)

    if not buildout.has_section('slap-parameter'):
      buildout.add_section('slap-parameter')
    for parameter, value in self.parameter_dict.items():
      if isinstance(value, str):
        buildout.set('slap-parameter', parameter, value)
      else:
        buildout.set('slap-parameter', parameter, json.dumps(value))

    buildout.add_section('slap-network-information')
    buildout.set('slap-network-information', 'local-ipv4',
                 self.getLocalIPv4Address())
    buildout.set('slap-network-information', 'global-ipv6',
                 self.getGlobalIPv6Address())

    # Copy/paste slap_connection
    buildout.add_section('slap-connection')
    for key, value in self.buildout['slap_connection'].iteritems():
      # XXX: Waiting for SlapBaseRecipe to use dash instead of underscores
      buildout.set('slap-connection', key.replace('_', '-'), value)

    work_directory = os.path.abspath(self.buildout['buildout'][
      'directory'])
    buildout_filename = os.path.join(work_directory,
                                     'buildout-%s.cfg' % self.name)
    with open(buildout_filename, 'w') as buildout_file:
      buildout.write(buildout_file)

    # XXX-Antoine: We gotta find a better way to do this. I tried to check
    # out how slapgrid-cp was running buildout. But it is worse than that.
    command_line_args = copy.copy(sys.argv) + ['-c', buildout_filename]

    self.logger.info("Invoking commandline : '%s'",
                     ' '.join(command_line_args))

    subprocess.check_call(command_line_args, cwd=work_directory,
                          env=os.environ.copy())
    return []
  update = install
