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
import logging
import os

import slapos.slap
from slapos.recipe.librecipe import unwrap
import six
from six.moves.configparser import RawConfigParser
from netaddr import valid_ipv4, valid_ipv6
from slapos.util import mkdir_p
from slapos import format as slapformat


logger = logging.getLogger("slapos")


class Recipe(object):
  """
  Retrieve slap partition parameters and make them available in buildout section.

  There are two sources of parameters. First is configuration file slapos.cfg and
  derived information.
  Second is partition's resource_file which is made available in form of keys joined
  with "-" and with all "_" replaced by "-".
  For example {"tun": {"ipv4": <addr>}} would be available in buildout as ${instance:tun-ipv4}.

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

  Output (keys derived from SlapOS configuration):
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
    global_ipv4_network
      The global IPv4 network
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

    Also note that all information from resource file will be appended
  """

  # XXX: used to detect if a configuration key is a valid section key. This
  # assumes buildout uses ConfigParser - which is currently the case.
  OPTCRE_match = RawConfigParser.OPTCRE.match

  def __init__(self, buildout, name, options):
      parameter_dict = self.fetch_parameter_dict(options,
                                      buildout['buildout']['directory'])

      match = self.OPTCRE_match
      for key, value in six.iteritems(parameter_dict):
          if match(key) is not None:
              continue
          options['configuration.' + key] = value

  def fetch_parameter_dict(self, options, instance_root):
      """Gather parameters about current computer and partition.

      Use two sources of truth
      1. SlapOS Master - for external computer/partition information
      2. format.Partition.resource_file - for partition specific details
      """
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
                                            'UNKNOWN Instance')
      options['root-instance-title'] = parameter_dict.pop('root_instance_title',
                                            'UNKNOWN')
      options['instance-guid'] = computer_partition.getInstanceGuid()

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
          options['ipv4-random'] = min(ipv4_set)
      if ipv6_set:
          options['ipv6-random'] = min(ipv6_set)

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

      # The external information transfered from Slap Master has been processed
      # so we extend with information gathered from partition resource file
      if hasattr(slapformat.Partition, "resource_file"):
        resource_home = instance_root
        while not os.path.exists(os.path.join(resource_home, slapformat.Partition.resource_file)):
          resource_home = os.path.normpath(os.path.join(resource_home, '..'))
          if resource_home == "/":
            break
        else:
          # no break happened - let's add partition resources into options
          logger.debug("Using partition resource file {}".format(
            os.path.join(resource_home, slapformat.Partition.resource_file)))
          with open(os.path.join(resource_home, slapformat.Partition.resource_file)) as fi:
            partition_params = json.load(fi)
          # be very careful with overriding master's information
          for key, value in flatten_dict(partition_params).items():
            if key not in options:
              if six.PY2 and isinstance(value, unicode):
                value = value.encode('UTF-8')
              options[key] = value
      # print out augmented options to see what we are passing
      logger.debug(str(options))
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
    # XXX: do not touch file if there's no change to avoid excessive IO
    #      (see https://lab.nexedi.com/nexedi/slapos.recipe.template/commit/14d26bc8c77a1940f389026bdbd3a9b229b241f4
    #       for an example to fix this)
    with os.fdopen(os.open(self._json_output, os.O_WRONLY | os.O_CREAT, 0o600), 'w') as fout:
      json.dump(parameter_dict, fout, indent=2, sort_keys=True)

    def install(self):
        return [self._json_output]

    update = install


def flatten_dict(data, key_prefix=''):
  """Transform folded dict into one-level key-subkey-subsubkey dictionary."""
  output = {}
  for key, value in data.items():
    prefixed_key = key_prefix + key.replace("_", "-")  # to be consistent with `fetch_parameter_dict`
    if isinstance(value, dict):
      output.update(flatten_dict(value, key_prefix=prefixed_key + "-"))
      continue
    output[prefixed_key] = value
  return output
