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
from slapos.recipe.localinstancedb import SharedInstanceResultDB, HostedInstanceLocalDB


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
  def __init__(self, set_defaults=False, unstringify=None):
    self.set_defaults = set_defaults
    self.unstringify = unstringify
    self.applied_schemas = []
    self.memoized_defaults = {}
    self.applied_defaults = {}
    self.original_validator_for = jsonschema.validators.validator_for
    # BBB Py2: Accept both str and unicode strings for unstringifying.
    self.strings = (unicode, str) if str is bytes else (str,)

  # Due to conditional constructs like oneOf & anyOf, there may be
  # instances with sub-sub-instances of sub-instances such that
  # a) the instance as a whole valides the whole schema,
  # b) the sub-instance I does not validate some sub-schema S,
  # c) a sub-sub-instance I' of I valides a sub-sub-schema S' of S.
  # Then I' validates S', but still the defaults of S' should not be
  # applied to I', nor the values of I' unstringified according to S'.
  #
  # The defaults from a (sub)schema should only be applied to a (sub)instance
  # if that (sub)instance and (sub)schema are on a valid validation path, and
  # properties of a (sub)instance must only be unstringified according to the
  # (sub)schemas that are on a valid validation path.

  def type_checker(self, v):
    # Create extended type checker to accept stringified values
    original_type_checker = v.TYPE_CHECKER
    original_is_type = original_type_checker.is_type
    def unstringify(value, f):
      try:
        return f(value) if type(value) in self.strings else value
      except ValueError:
        return value
    return original_type_checker.redefine_many({
      t: lambda _, value: original_is_type(unstringify(value, f), t)
      for t, f in self.unstringify.items()
    })

  def iter_errors(self, kls):
    # Due to conditional constructs like oneOf & anyOf, there may be
    # instances with sub-sub-instances of sub-instances such that
    # a) the instance as a whole valides the whole schema,
    # b) the sub-instance I does not validate some sub-schema S,
    # c) a sub-sub-instance I' of I valides a sub-sub-schema S' of S.
    # Then I' validates S', but still the defaults of S' should not be
    # applied to I', nor the values of I' unstringified according to S'.
    #
    # The defaults from a (sub)schema should only be applied to a (sub)instance
    # if that (sub)instance and (sub)schema are on a valid validation path, and
    # properties of a (sub)instance must only be unstringified according to the
    # (sub)schemas that are on a valid validation path.
    original_iter_errors = kls.iter_errors
    def iter_errors(validator, instance, *args):
      # *args: BBB py2 jonschema v3.0.2
      schema = args[0] if args else validator.schema
      e = None
      index = len(self.applied_schemas)
      uri = validator.resolver.base_uri
      for e in original_iter_errors(validator, instance, *args):
        # In case of error, drop all collected subschema *before* yielding
        # control back to the caller.
        del self.applied_schemas[index:]
        yield e
      if e is not None:
        # In case of error, drop all collected subschema *before* yielding
        # control back to the caller. Note that subschema may be collected
        # even after yielding the last error above: control will return to
        # original_iter_errors after the last yield. These must be dropped
        # as well, if any.
        del self.applied_schemas[index:]
      else:
        if not isinstance(schema, bool) and schema.get('properties'):
          # Only collect schemas with properties: we don't need the others.
          # Keep validator to reuse validator, and base_uri to reconstruct
          # a correct resolution scope later.
          uri = validator.resolver.base_uri
          self.applied_schemas.append((validator, schema, uri, instance))
          if self.set_defaults:
            # Defaults may be indirectly defined behind one or several $ref.
            # We resolve and memoize defaults now during validation instead
            # of later in case it affects internal $ref that refer to $defs
            # higher in the validation path.
            self.memoize_defaults(validator, schema.get('properties'))
    return iter_errors

  def unevaluatedProperties(self, v):
    # Extended unevaluatedProperties to drop collected schemas:
    # unevaluatedProperties reevaluates sub-schemas out of the context of
    # their containing schemas, so a sub-schema that locally validates a
    # sub-instance may be collected even though the containing schema
    # does not validate.
    original_unevaluated = v.VALIDATORS.get('unevaluatedProperties')
    # BBB Python2: jsonschema 3.0.2 does not implement unevaluatedProperties
    if original_unevaluated is not None:
      def unevaluated(validator, *args):
        index = len(self.applied_schemas)
        for e in original_unevaluated(validator, *args):
          del self.applied_schemas[index:]
          yield e
        del self.applied_schemas[index:]
      return unevaluated

  def create(self, schema, collect_defaults=True):
    v = self.original_validator_for(schema)
    if not self.unstringify and not collect_defaults:
      # Optimisation: use original validator class
      return v
    type_checker = self.type_checker(v) if self.unstringify else None
    unevaluatedProperties = self.unevaluatedProperties(v)
    validators = {
      'unevaluatedProperties': unevaluatedProperties,
    } if collect_defaults and unevaluatedProperties else ()
    kls = jsonschema.validators.extend(v, validators, None, type_checker)
    kls.iter_errors = self.iter_errors(kls)
    return kls

  @contextmanager
  def propagate(self, *fargs, **fkw):
    # Workaround https://github.com/python-jsonschema/jsonschema/issues/994
    # Reset memoized validators
    self.VALIDATORS = {}
    # Monkey-patch for jsonschema.validators.validator_for
    def validator_for(schema, *args, **kw):
      if isinstance(schema, bool):
        return self.original_validator_for(schema, *args, **kw)
      version = schema.get('$schema')
      try:
        return self.VALIDATORS[version]
      except KeyError:
        kls = self.create(schema, *fargs, **fkw)
        self.VALIDATORS[version] = kls
        return kls
    try: # __enter__
      jsonschema.validators.validator_for = validator_for
      yield validator_for
    finally: # __exit__
      jsonschema.validators.validator_for = self.original_validator_for

  def validate(self, schema, instance):
    with self.propagate(self.create) as validator_for:
      # Validate the instance with the extended validator
      e = None
      for e in validator_for(schema)(schema).iter_errors(instance):
        yield e
      if e is None:
        # Unstringify properties according to schemas that apply
        if self.unstringify:
          self.apply_unstringify()
        # Recursively collect and validate defaults of applying schemas
        if self.set_defaults:
          for e in self.collect_defaults():
            yield e
          if e is None:
            # Apply collected defaults
            self.apply_defaults()
    # Validate the updated instance for sanity and safety
    # Retain unstringified type-checking for consistency, because some values
    # may still need to be unstringified to typecheck against subschemas that
    # are not part of a valid validation path for the whole instance. Because
    # the valid validation path was obtained with unstringification, altering
    # the type checking logic here could result in altered validation paths!
    if e is None and (self.unstringify or self.set_defaults):
      with self.propagate(collect_defaults=False) as validator_for:
        for e in validator_for(schema)(schema).iter_errors(instance):
          yield e

  def fetch_key(self, key, schema, resolver):
    try:
      return schema[key]
    except KeyError:
      pass
    ref = schema['$ref']
    # This uses the internal RefResolver of jsonschema now deprecated in
    # favor of the referencing library. But we still use 4.17.3 which is
    # still using RefResolver. Also referencing library is Python3 only.
    with resolver.resolving(ref) as resolved:
      return self.fetch_key(key, resolved, resolver)

  def memoize_defaults(self, validator, properties):
    # Note: this does not and does not aim to find conditional defaults,
    # e.g. such as defaults specified behind a oneOff, like in:
    # {
    #   "oneOf" [
    #     { type: "integer", "default": 1 },
    #     { type: "string", "default": "hello" }
    #   ]
    # }
    # Such defaults do not make sense anyway, as they do not allow to
    # distinguish between the cases of the oneOf.
    #
    # It could be desirable to find defaults behind allOf, such as:
    # {
    #   "allOf" [
    #     { "type": "integer" },
    #     { "default": 1 }
    #   ]
    # }
    # Such cases are also not supported. But this limitation is acceptable,
    # because it is always possible to move the default outside of the allOf,
    # and if different branches had different defaults there would be no way
    # to choose one above the others.
    #
    # If needed it might be possible to solve this limitation later.
    for subschema in properties.values():
      if id(subschema) in self.memoized_defaults:
        continue
      try:
        default = self.fetch_key('default', subschema, validator.resolver)
      except KeyError:
        continue
      self.memoized_defaults[id(subschema)] = default

  def collect_defaults(self):
    index = 0
    while index < len(self.applied_schemas):
      validator, schema, uri, instance = self.applied_schemas[index]
      index += 1 # iterate over a potentially growing list
      # Reconstruct correct resolution scope
      validator.resolver.push_scope(uri)
      # Recursively collect defaults
      for key, subschema in schema['properties'].items():
        # Only consider defaults that will be applied
        if key in instance:
          continue
        # Obtain the default value if there is one
        try:
          default = self.memoized_defaults[id(subschema)]
        except KeyError:
          continue
        # Record the default value and where it comes from
        try:
          _, record = self.applied_defaults[id(instance)]
        except KeyError:
          record = defaultdict(list)
          self.applied_defaults[id(instance)] = instance, record
        record[key].append((default, subschema, uri))
        # Validate the defaults to recursively collect their defaults
        for error in validator.descend(
          default,
          subschema,
          path='default of ' + key,
          schema_path=key,
        ):
          yield error

  def apply_defaults(self):
    for instance, record in self.applied_defaults.values():
      for key, collected in record.items():
        it = iter(collected)
        default, _, _ = next(it)
        if any(d != default for d, _, _ in it):
          raise UserError(
            "Conflicting defaults for key %s: %r" % (key, collected))
        instance[key] = default

  def apply_unstringify(self):
    for validator, schema, uri, instance in self.applied_schemas:
      # Reconstruct correct resolution scope
      validator.resolver.push_scope(uri)
      # Attempt to unstringify stringified values back to their expected type
      for key, subschema in schema['properties'].items():
        try:
          # Types may be indirectly defined behind one or several $ref.
          # Note: this does not and does not aim to support the case where
          # the type is conditional, e.g. defined behind a oneOf, such as:
          # {
          #   "oneOf" [
          #     { "type": "integer" },
          #     { "type": "string" }
          #   ]
          # }
          # In such cases, we do not aim to support unstringifying.
          t = self.fetch_key('type', subschema, validator.resolver)
        except KeyError:
          continue
        # Support the general case where "type" may be an array of strings
        if isinstance(t, self.strings):
          t = [t]
        value = instance.get(key)
        if type(value) in self.strings:
          for t in t:
            f = self.unstringify.get(t)
            if f:
              try:
                instance[key] = f(value)
                break
              except ValueError:
                pass


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

  def _validateMain(self, schema, validator, parameter_dict):
    instance = parameter_dict if isinstance(parameter_dict, dict) else {}
    errors = list(validator.validate(schema, instance))
    if errors:
      err = SoftwareReleaseSchemaValidationError(errors).format_error(indent=2)
      msg = "Invalid parameters:\n" + err
      raise UserError(msg)
    return instance

  def _validateShared(self, schema, validator, shared_list):
    valid, invalid = [], []
    for instance in shared_list:
      reference = instance.pop('slave_reference')
      instance = unwrap(instance)
      try:
        errors = list(validator.validate(schema, instance))
      except UserError as e:
        errors = list(e.args)
      shared_item = {'reference': reference, 'parameters': instance}
      if errors:
        shared_item['errors'] = [str(e) for e in errors]
        invalid.append(shared_item)
      else:
        valid.append(shared_item)
    return valid, invalid

  ParsedOption = namedtuple("ParsedOption", ['main', 'shared'])
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

  def _expandParameterDict(self, options, parameter_dict):
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
          % software_description.software_type
        )
      validator = DefaultValidator(
        set_defaults.main,
        {'integer': int} if unstringify.main else None,
      )
      parameter_dict = self._validateMain(schema, validator, parameter_dict)
    if validate.shared:
      shared_list = options.pop('slave-instance-list')
      if shared_list:
        schema = self._getSharedSchema(software_description)
        if schema is None:
          raise UserError(
            "requested shared software-type %r seems to have no "
            "JSON schema entry in the software.cfg.json."
            % software_description.software_type
          )
        validator = DefaultValidator(
          set_defaults.shared,
          {'integer': int} if unstringify.shared else None,
        )
      else:
        schema = validator = None
      valid, invalid = self._validateShared(schema, validator, shared_list)
      options['valid-shared-instance-list'] = valid
      options['invalid-shared-instance-list'] = invalid
    options['configuration'] = parameter_dict
    if validate.main or isinstance(parameter_dict, dict):
      return parameter_dict
    return {}


class JsonSchemaWithDB(JsonSchema):
  """
  Extended JsonSchema that stores shared instance validation results
  in a database using HostedInstanceLocalDB and InstanceListComparator.

  This class inherits from JsonSchema and adds database persistence
  for shared instance validation results. The database path is provided
  via options['instance-db-path'] and results are stored with
  the valid_parameter column differentiating valid from invalid instances.

  Input:
    instance-db-path
      Path to the SQLite database file for storing shared instance results.
      Example:
        ${buildout:directory}/shared-instance-db.sqlite
  """
  def _expandParameterDict(self, options, parameter_dict):
    # Add database storage for shared instances
    validate = self._parseOption(options, 'validate-parameters', 'all')
    if validate.shared:
      # Require instance-db-path when shared validation is enabled
      db_path = options.get('instance-db-path')
      if not db_path:
        raise UserError(
          "instance-db-path option is required when using JsonSchemaWithDB "
          "with shared instance validation enabled."
        )

    # Call parent method to do the validation
    result = super(JsonSchemaWithDB, self)._expandParameterDict(options, parameter_dict)

    # Store results in database and remove it from options to avoid spreading
    # it to the logs
    if validate.shared:
      valid = options.pop('valid-shared-instance-list', [])
      invalid = options.pop('invalid-shared-instance-list', [])

      # Create/update database
      db = SharedInstanceResultDB(db_path)
      db.updateFromValidationResults(valid, invalid)

    return result


class JsonSchemaWithDBFromInstanceNode(JsonSchemaWithDB):
  """
  Variant of JsonSchemaWithDB that loads the shared ``slave-instance-list``
  from the local instance database managed by ``slapos.recipe.instancenode``.

  It reads valid instances from the database at ``requestinstance-db-path``
  (using ``HostedInstanceLocalDB``), loads their parameters, and builds
  ``options['slave-instance-list']`` as a list of dicts where:

    - each dict contains all parameters loaded from ``json_parameters``
    - an extra key ``slave_reference`` is added with the instance reference

  This list is then passed to the standard shared-instance validation logic
  implemented by ``JsonSchemaWithDB``.

  If the parameter ``allow-invalid-instance`` is present and has a true value
  (True, 'true', 'yes', '1', or 1) in both ``options`` and ``parameter_dict``,
  all instances (both valid and invalid) will be loaded from the database.
  Otherwise, only valid instances are loaded (default behavior).
  """

  def _load_valid_instances_from_db(self, db_path, valid_only=True):
    """
    Load parameters of instances from the given database path.

    Args:
      db_path: Path to the database file
      valid_only: If True, only load valid instances. If False, load all instances.

    Returns a list of dicts combining the instance parameters with an extra
    ``slave_reference`` key equal to the instance reference.
    """
    instance_db = HostedInstanceLocalDB(db_path)
    rows = instance_db.getInstanceList(
      select_tuple_string="reference, json_parameters",
      valid_only=valid_only,
    )
    slave_instance_list = []
    for row in rows:
      reference = row["reference"]
      raw_params = row["json_parameters"] or "{}"
      try:
        params = json.loads(raw_params)
      except (ValueError, TypeError):
        # If parameters cannot be parsed, skip this instance rather than failing
        continue
      if not isinstance(params, dict):
        # Shared validation expects mapping-like parameters
        continue
      # Copy parameters and add slave_reference
      item = dict(params)
      item["slave_reference"] = reference
      slave_instance_list.append(item)
    return slave_instance_list

  def _expandParameterDict(self, options, parameter_dict):
    """
    Populate ``options['slave-instance-list']`` from instancenode's database
    after delegating to ``JsonSchemaWithDB`` (which pops it during validation).

    Note: We populate it before calling super so validation can use it, then
    repopulate it after since JsonSchema pops it during validation.
    """
    # Database containing valid instances managed by instancenode.Recipe
    # Note: this MUST be different from the database used by JsonSchemaWithDB
    # (instance-db-path) to avoid mixing concerns.
    db_path = options.get('valided-instance-db-path')
    if not db_path:
      raise UserError(
        "valided-instance-db-path option is required when using "
        "JsonSchemaWithDBFromInstanceNode."
      )

    instance_db_path = options.get('instance-db-path')
    if instance_db_path and instance_db_path == db_path:
      raise UserError(
        "valided-instance-db-path must be different from instance-db-path."
      )

    # Delegate to standard JsonSchemaWithDB behavior
    # This will pop 'slave-instance-list' during validation if validate.shared is True
    result = super(JsonSchemaWithDBFromInstanceNode, self)._expandParameterDict(
      options,
      parameter_dict,
    )

    # Repopulate slave-instance-list after validation (it was popped by JsonSchema)
    # Use the original list which still has slave_reference (not the modified copy)
    # Load instances from database
    # Check if allow-invalid-instance parameter is present and true in both options and parameter_dict
    def is_true_value(value):
      """Check if value is a true value (true, yes, 1, etc.)"""
      if isinstance(value, bool):
        return value is True
      if isinstance(value, six.string_types):
        return value.lower() in ('true', 'yes', '1')
      return value == 1
    
    allow_invalid_options = is_true_value(options.get('allow-invalid-instance'))
    allow_invalid_params = False
    if isinstance(parameter_dict, dict):
      allow_invalid_params = is_true_value(result.get('allow-invalid-instance'))
    allow_invalid = allow_invalid_options and allow_invalid_params
    slave_instance_list = self._load_valid_instances_from_db(db_path, valid_only=not allow_invalid)
    options['slave-instance-list'] = slave_instance_list

    return result


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
