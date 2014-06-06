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

  Output:
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
    configuration
      Dict of all parameters.
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
      parameter_dict = self.fetch_parameter_dict(options)

      match = self.OPTCRE_match
      for key, value in parameter_dict.iteritems():
          if match(key) is not None:
              continue
          options['configuration.' + key] = value

  def fetch_parameter_dict(self, options):
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
      ipv4_set = set()
      v4_add = ipv4_set.add
      ipv6_set = set()
      v6_add = ipv6_set.add
      tap_set = set()
      tap_add = tap_set.add
      for tap, ip in parameter_dict.pop('ip_list'):
          tap_add(tap)
          if valid_ipv4(ip):
              v4_add(ip)
          elif valid_ipv6(ip):
              v6_add(ip)
          # XXX: emit warning on unknown address type ?
      options['ipv4'] = ipv4_set
      options['ipv6'] = ipv6_set

      # also export single ip values for those recipes that don't support sets.
      if ipv4_set:
          options['ipv4-random'] = list(ipv4_set)[0].encode('UTF-8')
      if ipv6_set:
          options['ipv6-random'] = list(ipv6_set)[0].encode('UTF-8')

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
    with os.fdopen(os.open(self._json_output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0600), 'w') as fout:
      fout.write(json.dumps(parameter_dict, indent=2, sort_keys=True))

    def install(self):
        return [self._json_output]

    update = install

