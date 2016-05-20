##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors. All Rights Reserved.
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

import json
import os

import slapos.slap
from slapos.recipe.librecipe import unwrap
from ConfigParser import RawConfigParser
from netaddr import valid_ipv4, valid_ipv6
from slapos.util import mkdir_p

class Recipe(object):
  """
  Retrieves slap partition parameters, and makes them available to other
  buildout section in various ways, and in various encodings.
  Populates the buildout section it is used in with all slap partition
  parameters.
  Also provides access to partition properties: all IPv4, IPv6 and tap
  interfaces it is allowed to use.

  Input:
    url
      Slap server url.
      Example:
        ${slap-connection:server-url}
    key & cert (optional)
      Path of files containing key and certificate for secure connection to
      slap server.
      Example:
        ${slap-connection:key-file}
        ${slap-connection:cert-file}
    computer
      Computer identifier.
      Example:
        ${slap-connection:computer-id}
    partition
      Partition identifier.
      Example:
        ${slap-connection:partition-id}
    storage-home
      Path of folder configured for data storage
      Example:
        ${storage-configuration:storage-home}

  Output:
    root-instance-title
      Hosting subscription or root instance title
    instance-title
      Title of instance running into this partition
    slap-software-type
      Current partition's software type.
    ipv4
      Set of IPv4 addresses.
    ipv6
      Set of IPv6 addresses.
    ipv4-random
      One of the IPv4 addresses.
    ipv6-random
      One of the IPv6 addresses.
    tap
      Set of TAP interfaces.
    tap-network-information-dict
      Dict of set of all TAP network information
    tap-ipv4
      ipv4 allowed for this TAP
    tap-gateway
      ipv4 of gateway interface of this TAP
    tap-netmask
      ipv4 netmask address of this TAP
    tap-network
      ipv4 network address of this TAP
    configuration
      Dict of all parameters.
    storage-dict
      Dict of partition data path when it is configured
    configuration.<key>
      One key per partition parameter.
      Partition parameter whose name cannot be represented unambiguously in
      buildout syntax are ignored. They cannot be accessed from buildout syntax
      anyway, and are available through "configuration" output key.
    instance-state
      The instance state.
  """

  # XXX: used to detect if a configuration key is a valid section key. This
  # assumes buildout uses ConfigParser - which is currently the case.
  OPTCRE_match = RawConfigParser.OPTCRE.match

  def __init__(self, buildout, name, options):
      parameter_dict = self.fetch_parameter_dict(options,
                                      buildout['buildout']['directory'])

      match = self.OPTCRE_match
      for key, value in parameter_dict.iteritems():
          if match(key) is not None:
              continue
          options['configuration.' + key] = value

  def fetch_parameter_dict(self, options, instance_root):
      slap = slapos.slap.slap()
      slap.initializeConnection(
          options['url'],
          options.get('key'),
          options.get('cert'),
      )
      computer_partition = slap.registerComputerPartition(
          options['computer'],
          options['partition'],
      )
      parameter_dict = computer_partition.getInstanceParameterDict()
      options['instance-state'] = computer_partition.getState()
      # XXX: those are not partition parameters, strictly speaking.
      # Make them available as individual section keys.
      for his_key in (
                  'slap_software_type',
                  'slap_computer_partition_id',
                  'slap_computer_id',
                  'slap_software_release_url',
                  'slave_instance_list',
                  'timestamp',
              ):
          try:
              value = parameter_dict.pop(his_key)
          except KeyError:
              pass
          else:
              options[his_key.replace('_', '-')] = value
      # Get Instance and root instance title or return UNKNOWN if not set
      options['instance-title'] = parameter_dict.pop('instance_title',
                                            'UNKNOWN Instance').encode('UTF-8')
      options['root-instance-title'] = parameter_dict.pop('root_instance_title',
                                            'UNKNOWN').encode('UTF-8')

      ipv4_set = set()
      v4_add = ipv4_set.add
      ipv6_set = set()
      v6_add = ipv6_set.add
      tap_set = set()
      tap_add = tap_set.add
      route_gw_set = set()
      route_gw_add = route_gw_set.add
      route_mask_set = set()
      route_mask_add = route_mask_set.add
      route_ipv4_set = set()
      route_v4_add = route_ipv4_set.add
      route_network_set = set()
      route_net_add = route_network_set.add
      for tap, ip in parameter_dict.pop('ip_list'):
          tap_add(tap)
          if valid_ipv4(ip):
              v4_add(ip)
          elif valid_ipv6(ip):
              v6_add(ip)
          # XXX: emit warning on unknown address type ?

      if 'full_ip_list' in parameter_dict:
        for item in parameter_dict.pop('full_ip_list'):
          if len(item) == 5:
            tap, ip, gw, netmask, network = item
            if  tap.startswith('route_'):
              if valid_ipv4(gw):
                route_gw_add(gw)
              if valid_ipv4(netmask):
                route_mask_add(netmask)
              if valid_ipv4(ip):
                route_v4_add(ip)
              if valid_ipv4(network):
                route_net_add(network)

      options['ipv4'] = ipv4_set
      options['ipv6'] = ipv6_set

      # also export single ip values for those recipes that don't support sets.
      if ipv4_set:
          options['ipv4-random'] = list(ipv4_set)[0].encode('UTF-8')
      if ipv6_set:
          options['ipv6-random'] = list(ipv6_set)[0].encode('UTF-8')
      if route_ipv4_set:
        options['tap-ipv4'] = list(route_ipv4_set)[0].encode('UTF-8')
        options['tap-network-information-dict'] = dict(ipv4=route_ipv4_set,
                                    netmask=route_mask_set,
                                    gateway=route_gw_set,
                                    network=route_network_set)
      else:
        options['tap-network-information-dict'] = {}
      if route_gw_set:
        options['tap-gateway'] = list(route_gw_set)[0].encode('UTF-8')
      if route_mask_set:
        options['tap-netmask'] = list(route_mask_set)[0].encode('UTF-8')
      if route_network_set:
        options['tap-network'] = list(route_network_set)[0].encode('UTF-8')

      storage_home = options.get('storage-home')
      storage_dict = {}
      if storage_home and os.path.exists(storage_home) and \
                                  os.path.isdir(storage_home):
        for filename in os.listdir(storage_home):
          storage_path = os.path.join(storage_home, filename, 
                                    options['slap-computer-partition-id'])
          if os.path.exists(storage_path) and os.path.isdir(storage_path):
            storage_link = os.path.join(instance_root, 'DATA', filename)
            mkdir_p(os.path.join(instance_root, 'DATA'))
            if not os.path.lexists(storage_link):
              os.symlink(storage_path, storage_link)
            storage_dict[filename] = storage_link
      options['storage-dict'] = storage_dict

      options['tap'] = tap_set
      return self._expandParameterDict(options, parameter_dict)

  def _expandParameterDict(self, options, parameter_dict):
      options['configuration'] = parameter_dict
      return parameter_dict

  install = update = lambda self: []

class Serialised(Recipe):
  def _expandParameterDict(self, options, parameter_dict):
      options['configuration'] = parameter_dict = unwrap(parameter_dict)
      if isinstance(parameter_dict, dict):
          return parameter_dict
      else:
          return {}

class JsonDump(Recipe):
  def __init__(self, buildout, name, options):
    parameter_dict = self.fetch_parameter_dict(options)
    self._json_output = options['json-output']
    with os.fdopen(os.open(self._json_output, os.O_WRONLY | os.O_CREAT, 0600), 'w') as fout:
      fout.write(json.dumps(parameter_dict, indent=2, sort_keys=True))

    def install(self):
        return [self._json_output]

    update = install

