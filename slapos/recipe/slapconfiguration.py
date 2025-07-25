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

from collections import defaultdict, namedtuple
from contextlib import contextmanager

import jsonschema
import slapos.slap
from slapos.recipe.librecipe import unwrap
import six
from six.moves.configparser import RawConfigParser
from netaddr import valid_ipv4, valid_ipv6
from slapos.util import (
  mkdir_p,
  SoftwareReleaseSchema,
  SoftwareReleaseSerialisation,
  SoftwareReleaseSchemaValidationError,
  urljoin,
)
from slapos import format as slapformat
from zc.buildout import UserError


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
    url | server-url
      Slap server url.
      Example:
        ${slap-connection:server-url}
    key & cert | key-file & cert-file (optional)
      Path of files containing key and certificate for secure connection to
      slap server.
      Example:
        ${slap-connection:key-file}
        ${slap-connection:cert-file}
    computer | computer-id
      Computer identifier.
      Example:
        ${slap-connection:computer-id}
    partition | partition-id
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
      # BBB: or ... (right side) clauses kept for compatibility;
      # left-side clauses correspond directly to slap-connection.
      slap.initializeConnection(
          options.get('server-url') or options['url'],
          options.get('key-file') or options.get('key'),
          options.get('cert-file') or options.get('cert'),
      )
      computer_partition = slap.registerComputerPartition(
          options.get('computer-id') or options['computer'],
          options.get('partition-id') or options['partition'],
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
      options['root-instance-short-title'] = parameter_dict.pop(
                                            'root_instance_short_title',
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

      # XXX slapproxy is sending 'full_address_list' not 'full_ip_list' (like real slapos master)
      # just pop this value for now. Remove this when slapproxy is fixed.
      parameter_dict.pop('full_address_list', None)

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

      # validate the parameters (only when using JsonSchema recipe)
      # after popping the custom values sent by slapos master
      # but before adding the value from .slapos-resources file
      parameter_dict = self._validateParameterDict(options,parameter_dict)

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

  def _validateParameterDict(self, options, parameter_dict):
      return parameter_dict

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


class DefaultValidator(object):
  def __init__(self, schema, set_defaults=False, unstringify=None):
    self.schema = schema
    self.set_defaults = set_defaults
    self.unstringify = unstringify
    self.validatorfor = v = jsonschema.validators.validator_for(schema)
    # Retain original properties validator
    validate_properties = v.VALIDATORS["properties"]
    # Define new properties validator
    def collect_defaults(validator, properties, instance, schema):
      # Attempt to unstringify stringified values back to their expected type
      if self.unstringify:
        for key, subschema in properties.items():
          unstringify = self.unstringify.get(subschema.get('type'))
          if unstringify:
            value = instance.get(key)
            if type(value) is str or (str is bytes and type(value) is unicode):
              try:
                instance[key] = unstringify(value)
              except ValueError:
                pass
      # Call original properties validator
      error = False
      for e in validate_properties(validator, properties, instance, schema):
        error = True
        yield e
      # Collect defaults if the instance validates this schema
      if self.set_defaults and not error:
        for key, subschema in properties.items():
          if "default" in subschema:
            try:
              _, defaults = self.defaults[id(instance)]
            except KeyError:
              defaults = defaultdict(dict)
              self.defaults[id(instance)] = instance, defaults
            defaults[key][id(subschema)] = subschema["default"]
    # Extend validator class with extended properties validator
    kls = jsonschema.validators.extend(v, {"properties" : collect_defaults})
    self.validator = kls(schema)

  @contextmanager
  def propagate(self):
    # Workaround https://github.com/python-jsonschema/jsonschema/issues/994
    # This only works if all $ref schemas have the same $schema as the first.
    version = self.schema.get("$schema")
    try:
      if version is not None:
        jsonschema.validators.validates(version)(type(self.validator))
      yield
    finally:
      if version is not None:
        jsonschema.validators.validates(version)(self.validatorfor)

  def validate(self, instance):
    if self.set_defaults or self.unstringify:
      # Initialise default collection
      self.defaults = {}
      # Validate instance
      invalid = False
      with self.propagate():
        for error in self.validator.iter_errors(instance):
          invalid = True
          yield error
      # Stop there in case of validation errors
      if invalid:
        return
      # Apply collected defaults
      for data, defaults in self.defaults.values():
        for key, defaultdict in defaults.items():
          if key not in data:
            it = iter(defaultdict.values())
            default = next(it)
            if any(d != default for d in it):
              raise UserError(
                "Conflicting defaults for key %s: %r" % (key, defaultlist))
            data[key] = default
    # Validate the updated instance
    for error in self.validatorfor(self.schema).iter_errors(instance):
      yield error


class JsonSchema(Recipe):
  """
  Input:
    jsonschema
      JSON Schema for the SR.
      All instance schemas must be available at the advertised relative paths.
      Example:
        ${buildout:directory}/software.cfg.json
    validate-parameters
      Enum to control validating instance parameters
      for both/neither/either-of main and shared instances.
      Accepted values: all|main|shared|none.
      Example:
        shared
    set-default
      Enum to control adding defaults specified by the JSON schema
      to both/neither/either-of main and shared instance parameters.
      Accepted values: all|main|shared|none.
      Default value: none.
      Example:
        shared
    unstringify
      Enum to control attempting to unstringify stringified integers
      for values that are expected to be integers by the JSON schema,
      for both/neither/either-of main and shared instance parameters.
      Accepted values: all|main|shared|none.
      Default value: none.
      Example:
        shared
  """
  def _description(self, options):
    path = options['jsonschema']
    # because SoftwareReleaseSchema accepts only file:// paths
    path = path if path.startswith('file://') else 'file://' + path
    # because SoftwareReleaseSchema expects the SR url and adds .json
    path = path[:-5] if path.endswith('.json') else path
    return SoftwareReleaseSchema(path, options['slap-software-type'])

  def _getSharedSchema(self, software_description):
    t = software_description.software_type
    software_json_dict = software_description.getSoftwareSchema()
    for type_dict in software_json_dict['software-type'].values():
      if type_dict['software-type'] == t and type_dict.get('shared') == True:
        url = urljoin(software_description.software_url, type_dict['request'])
        return software_description._readAsJson(url, True)

  def _parseParameterDict(self, validator, parameter_dict):
    instance = parameter_dict if isinstance(parameter_dict, dict) else {}
    errors = list(validator.validate(instance))
    if errors:
      err = SoftwareReleaseSchemaValidationError(errors).format_error(indent=2)
      msg = "Invalid parameters:\n" + err
      raise UserError(msg)
    return instance

  def _parseSharedParameterDict(self, validator, shared_list):
    valid, invalid = [], []
    for instance in shared_list:
      reference = instance.pop('slave_reference')
      instance = unwrap(instance)
      try:
        errors = list(validator.validate(instance))
      except UserError as e:
        errors = list(e.args)
      shared_item = {'reference': reference, 'parameters': instance}
      if errors:
        shared_item['errors'] = errors
        invalid.append(shared_item)
      else:
        valid.append(shared_item)
    return valid, invalid

  ParsedOption = namedtuple('ParsedOption', ['main', 'shared'])
  def _parseOption(self, options, key, default):
    value = options.get(key, default)
    accepted = ('none', 'main', 'shared', 'all')
    try:
      index = accepted.index(value)
    except ValueError:
      raise UserError(
        "%r is not a valid value for option %r. "
        "Accepted values are %r" % (value, key, accepted)
      )
    # return: value in ('main', 'all'), value in ('shared', 'all')
    return self.ParsedOption(index & 1, index & 2)

  def _validateParameterDict(self, options, parameter_dict):
    validate = self._parseOption(options, 'validate-parameters', 'all')
    set_defaults = self._parseOption(options, 'set-default', 'none')
    unstringify = self._parseOption(options, 'unstringify', 'none')
    software_description = self._description(options)
    serialisation = software_description.getSerialisation(strict=True)
    if serialisation == SoftwareReleaseSerialisation.JsonInXml:
      parameter_dict = unwrap(parameter_dict)
    if validate.main:
      schema = software_description.getInstanceRequestParameterSchema()
      if schema is None:
        raise UserError(
          "requested software-type %r seems to have no "
          "JSON schema entry in the software.cfg.json."
        )
      validator = DefaultValidator(
        schema,
        set_defaults.main,
        {'integer': int} if unstringify.main else None,
      )
      parameter_dict = self._parseParameterDict(validator, parameter_dict)
    if validate.shared:
      shared_list = options.pop('slave-instance-list')
      shared_schema = self._getSharedSchema(software_description)
      if shared_schema is None:
        raise UserError(
          "requested shared software-type %r seems to have no "
          "JSON schema entry in the software.cfg.json."
        )
      validator = DefaultValidator(
        shared_schema,
        set_defaults.shared,
        {'integer': int} if unstringify.shared else None,
      ) if shared_list else None # optimisation: skip creating unused validator
      valid, invalid = self._parseSharedParameterDict(validator, shared_list)
      options['valid-shared-instance-list'] = valid
      options['invalid-shared-instance-list'] = invalid
    options['configuration'] = parameter_dict
    if validate.main or isinstance(parameter_dict, dict):
      return parameter_dict
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
