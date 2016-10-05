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
import errno
import re

import zc.buildout

class SlapConfigParser(ConfigParser, object):
  """ 
      This class overrite ConfigParser.write method to fix parse problem when
      configuration like: 
      foo += bar is included in buildout file. softwaretype recipe will generate
      buildout file with foo + = bar because ConfigParser doesn't reconize += 
      delimiter and read key as "foo +", value as "bar".
      Then ConfigParser.write method generate
      
      [section]
      foo + = bar
      ...
      
      This is invalid with buildout version 2.
  """

  def write(self, fp):
    """Write an .ini-format representation of the configuration state."""
    if sys.version_info[0] > 2:
      return super(SlapConfigParser, self).write(fp)

    regex = re.compile(r'^(.*)\s+([+-]{1})$')
    if self._defaults:
      fp.write("[%s]\n" % DEFAULTSECT)
      for (key, value) in self._defaults.items():
        op = ""
        result = regex.match(key)
        if result is not None:
          key, op = result.groups()

        line = "%s %s= %s\n" % (key, op, str(value).replace('\n', '\n\t'))
        fp.write(line)
      fp.write("\n")
    for section in self._sections:
      fp.write("[%s]\n" % section)
      for (key, value) in self._sections[section].items():
        if key == "__name__":
          continue
        if (value is not None) or (self._optcre == self.OPTCRE):
          op = ""
          result = regex.match(key)
          if result is not None:
            key, op = result.groups()
          key = "%s %s= %s" % (key, op, str(value).replace('\n', '\n\t'))

        fp.write("%s\n" % key)
      fp.write("\n")

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

  def _getTapIpAddressList(self, test_method):
    """Internal helper method to fetch full ip address assigned for tap"""
    if not 'full_ip_list' in self.parameter_dict:
      return ()
    for item in self.parameter_dict['full_ip_list']:
      if len(item) == 5:
        tap, ip, gw, mask, net = item
        if tap.startswith('route_') and test_method(ip) and \
                          test_method(gw) and test_method(mask):
          return (ip, gw, mask, net)
    return ()

  def getLocalIPv4Address(self):
    """Returns local IPv4 address available on partition"""
    # XXX: Lack checking for locality of address
    return self._getIpAddress(netaddr.valid_ipv4)

  def getGlobalIPv6Address(self):
    """Returns global IPv6 address available on partition"""
    # XXX: Lack checking for globality of address
    return self._getIpAddress(netaddr.valid_ipv6)
  
  def getLocalTapIPv4AddressList(self):
    """Returns global IPv6 address available for tap interface"""
    # XXX: Lack checking for locality of address
    return self._getTapIpAddressList(netaddr.valid_ipv4)

  def getNetworkInterface(self):
    """Returns the network interface available on partition"""
    if not 'ip_list' in self.parameter_dict:
      raise AttributeError
    for name, ip in self.parameter_dict['ip_list']:
      if name:
        return name
    raise AttributeError, "Not network interface found"
  
  def mkdir_p(self, path, mode=0700):
    """
    Creates a directory and its parents, if needed.
    NB: If the directory already exists, it does not change its permission.
    """

    try:
        os.makedirs(path, mode)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

  def install(self):
    slap = slapos.slap.slap()
    slap_connection = self.buildout['slap_connection']
    computer_id = slap_connection['computer_id']
    computer_partition_id = slap_connection['partition_id']
    server_url = slap_connection['server_url']
    key_file = slap_connection.get('key_file')
    cert_file = slap_connection.get('cert_file')
    instance_root = self.buildout['buildout']['directory']
    storage_configuration_dict = self.buildout.get('storage-configuration')
    network_dict = self.buildout.get('network-information')
    storage_home = ''
    global_ipv4_network = ''
    if storage_configuration_dict:
      storage_home = storage_configuration_dict.get('storage-home')
    if network_dict:
      global_ipv4_network = network_dict.get('global-ipv4-network')
    slap.initializeConnection(server_url, key_file, cert_file)
    self.computer_partition = slap.registerComputerPartition(
      computer_id,
      computer_partition_id)
    self.parameter_dict = self.computer_partition.getInstanceParameterDict()
    software_type = self.parameter_dict['slap_software_type']

    # Raise if request software_type does not exist ...
    if software_type not in self.options:
      # ... Except for backward compatibility. Then use "default".
      if software_type in ['RootSoftwareInstance']:
        software_type = 'default'
      else:
        raise zc.buildout.UserError("This software type (%s) isn't mapped." % \
            software_type)

    instance_file_path = self.options[software_type]

    if not os.path.exists(instance_file_path):
      raise zc.buildout.UserError("The specified buildout config file %r does "
                                  "not exist." % instance_file_path)

    buildout = SlapConfigParser()
    with open(instance_file_path) as instance_path:
      buildout.readfp(instance_path)

    buildout.set('buildout', 'installed', '.installed-%s.cfg' % self.name)

    if not buildout.has_section('slap-parameter'):
      buildout.add_section('slap-parameter')
    for parameter, value in self.parameter_dict.items():
      # All parameters evaluating to False are... False, and shouldn't
      # convey any information.
      # Here, all those parameters are simply ignored.
      if value:
        if isinstance(value, str):
          buildout.set('slap-parameter', parameter, value)
        else:
          buildout.set('slap-parameter', parameter, json.dumps(value))

    buildout.add_section('slap-network-information')
    buildout.set('slap-network-information', 'local-ipv4',
                 self.getLocalIPv4Address())
    buildout.set('slap-network-information', 'global-ipv6',
                 self.getGlobalIPv6Address())
    buildout.set('slap-network-information', 'network-interface',
                 self.getNetworkInterface())
    tap_ip_list = self.getLocalTapIPv4AddressList()
    tap_ipv4 = tap_gateway = tap_netmask = tap_network = ''
    if tap_ip_list:
      tap_ipv4, tap_gateway, tap_netmask, tap_network= tap_ip_list
    buildout.set('slap-network-information', 'tap-ipv4', tap_ipv4)
    buildout.set('slap-network-information', 'tap-gateway', tap_gateway)
    buildout.set('slap-network-information', 'tap-netmask', tap_netmask)
    buildout.set('slap-network-information', 'tap-network', tap_network)
    buildout.set('slap-network-information', 'global-ipv4-network',
                                                          global_ipv4_network)

    # Copy/paste slap_connection
    buildout.add_section('slap-connection')
    for key, value in self.buildout['slap_connection'].iteritems():
      # XXX: Waiting for SlapBaseRecipe to use dash instead of underscores
      buildout.set('slap-connection', key.replace('_', '-'), value)
    # XXX: Needed for lxc. Use non standard API
    buildout.set('slap-connection', 'requested', self.computer_partition._requested_state)

    # setup storage directory
    buildout.add_section('storage-configuration')
    buildout.set('storage-configuration', 'storage-home', storage_home)
    if storage_home and os.path.exists(storage_home) and \
                                  os.path.isdir(storage_home):
      # Create folder instance_root/DATA/ if not exist
      data_home = os.path.join(instance_root, 'DATA')
      self.mkdir_p(data_home)
      for filename in os.listdir(storage_home):
        storage_path = os.path.join(storage_home, filename, computer_partition_id)
        if os.path.exists(storage_path) and os.path.isdir(storage_path):
          storage_link = os.path.join(data_home, filename)
          if os.path.lexists(storage_link):
            if not os.path.islink(storage_link):
              raise zc.buildout.UserError(
                  'Target %r already exists but is not a link' % storage_link)
              #os.unlink(storage_link)
          else:
            os.symlink(storage_path, storage_link)
          buildout.set('storage-configuration', filename, storage_link)

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
