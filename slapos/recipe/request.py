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
import logging
from zc.buildout import UserError
from slapos.recipe.librecipe import wrap, JSON_SERIALISED_MAGIC_KEY
import json
from slapos import slap as slapmodule
from slapos.slap import SoftwareProductCollection
import slapos.recipe.librecipe.generic as librecipe
import traceback

SOFTWARE_PRODUCT_NAMESPACE = "product."
DEFAULT_SOFTWARE_TYPE = 'RootSoftwareInstance'

class Recipe(object):
  """
  Request a partition to a slap master.
  Can provide parameters to that partition and fetches its connection
  parameters.

  Input:
    server-url
    key-file (optional)
    cert-file (optional)
      Used to contact slap master.

    computer-id
    partition-id
      Current partition's identifiers.
      Must match key's credentials if given.

    name (optional, defaults to section name)
      Name (reference) of requested partition.

    software-url
      URL of a software definition to request an instance of.

    software-type
      Software type of requested instance, among those provided by the
      definition from software-url.

    slave (optional, defaults to false)
      Set to "true" when requesting a slave instance, ie just setting a set of
      parameters in an existing instance.

    sla (optional)
      Whitespace-separated list of Service Level Agreement names.
      Each name must correspond to a "sla-<name>" option.
      Used to specify what a suitable partition would be.
      Possible names depend on master's capabilities.

    config (optional)
      Whitespace-separated list of partition parameter names.
      Each name must correspond to a "config-<name>" option.
      Possible names depend on requested partition's software type.

    return (optional)
      Whitespace-separated list of expected partition-published value names.
      Options will be created from them, in the form of "connection-<name>"
      As long as requested partition doesn't publish all those values,
      installation of request section will fail.
      Possible names depend on requested partition's software type.

    state (optional)
     Requested state, default value is the state of the requester.

    Output:
      See "return" input key.
      "instance-state"
          The current state of the instance.
      "requested-state"
          The requested state of the instance.
  """
  failed = None

  def __init__(self, buildout, name, options):
    self.logger = logging.getLogger(name)
    software_url = options['software-url']
    name = options['name']
    return_parameters = options.get('return', '').split()
    if not return_parameters:
      self.logger.debug("No parameter to return to main instance."
        "Be careful about that...")
    software_type = options.get('software-type', DEFAULT_SOFTWARE_TYPE)
    if 'config' in options or 'sla' in options:
      raise UserError("'config' & 'sla' options are obsolete."
                      " Clean up your software release.")
    filter_kw = {k[4:]: v
      for k, v in options.iteritems()
      if k.startswith('sla-') and v}
    partition_parameter_kw = self._filterForStorage({k[7:]: v
      for k, v in options.iteritems()
      if k.startswith('config-')})
    slave = options.get('slave', 'false').lower() in \
      librecipe.GenericBaseRecipe.TRUE_VALUES

    # By default XXXX Way of doing it is ugly and dangerous
    requested_state = options.get('state', buildout['slap-connection'].get('requested','started'))
    options['requested-state'] = requested_state

    slap = slapmodule.slap()
    slap.initializeConnection(
      options['server-url'],
      options.get('key-file'),
      options.get('cert-file'),
    )
    request = slap.registerComputerPartition(
      options['computer-id'],
      options['partition-id'],
    ).request

    if software_url is not None and \
      software_url.startswith(SOFTWARE_PRODUCT_NAMESPACE):
    
      product = SoftwareProductCollection(self.logger, slap)
      
      try:
        software_url = product.__getattr__(
          software_url[len(SOFTWARE_PRODUCT_NAMESPACE):])
      except AttributeError as e:
        self.logger.warning('Error on get software release : %s ' % e.message)
        

    self._raise_request_exception = None
    self._raise_request_exception_formatted = None
    self.instance = None

    # Try to do the request and fetch parameter dict...
    try:
      self.instance = request(software_url, software_type,
          name, partition_parameter_kw=partition_parameter_kw,
          filter_kw=filter_kw, shared=slave, state=requested_state)
      return_parameter_dict = self._getReturnParameterDict(self.instance,
          return_parameters)
      # Fetch the instance-guid and the instance-state
      # Note: SlapOS Master does not support it for slave instances
      if not slave:
        try:
          options['instance-guid'] = self.instance.getInstanceGuid()
          # XXX: deprecated, to be removed
          options['instance_guid'] = self.instance.getInstanceGuid()
          options['instance-state'] = self.instance.getState()
          options['instance-status'] = self.instance.getStatus()
        except (slapmodule.ResourceNotReady, AttributeError):
          # Backward compatibility. Old SlapOS master and core don't know this.
          self.logger.warning("Impossible to fetch instance GUID nor state.")
    except (slapmodule.NotFoundError, slapmodule.ServerError, slapmodule.ResourceNotReady) as exc:
      self._raise_request_exception = exc
      self._raise_request_exception_formatted = traceback.format_exc()
      return_parameter_dict = {}

    # Then try to get all the parameters. In case of problem, put empty string.
    for param in return_parameters:
      options['connection-%s' % param] = ''
      try:
        options['connection-%s' % param] = return_parameter_dict[param]
      except KeyError:
        if self.failed is None:
          self.failed = param

  def _filterForStorage(self, partition_parameter_kw):
    return partition_parameter_kw

  def _getReturnParameterDict(self, instance, return_parameter_list):
    result = {}
    for param in return_parameter_list:
      try:
        result[param] = str(instance.getConnectionParameter(param))
      except slapmodule.NotFoundError:
        pass
    return result

  def install(self):
    if self._raise_request_exception:
      raise self._raise_request_exception

    if self.failed is not None:
      # Check instance status to know if instance has been deployed
      try:
        if self.instance._computer_id is not None:
          status = self.instance.getState()
        else:
          status = 'not ready yet'
      except (slapmodule.NotFoundError, slapmodule.ServerError, slapmodule.ResourceNotReady):
        status = 'not ready yet'
      except AttributeError:
        status = 'unknown'
      error_message = 'Connection parameter %s not found. '\
          'Status of requested instance is: %s. If this error persists, '\
          'check status of this instance.' % (self.failed, status)
      self.logger.error(error_message)
      raise KeyError(error_message)
    return []

  update = install


class RequestOptional(Recipe):
  """
  Request a SlapOS instance. Won't fail if request failed or is not ready.
  Same as slapos.cookbook:request, but won't raise in case of problem.
  """
  def install(self):
    if self._raise_request_exception_formatted:
      self.logger.warning('Optional request failed.')
      if not isinstance(self._raise_request_exception, slapmodule.NotFoundError):
        # full traceback for optional 'not found' is too verbose and confusing
        self.logger.debug(self._raise_request_exception_formatted)
    elif self.failed is not None:
      # Check instance status to know if instance has been deployed
      try:
        if self.instance._computer_id is not None:
          status = self.instance.getState()
        else:
          status = 'not ready yet'
      except (slapmodule.NotFoundError, slapmodule.ServerError, slapmodule.ResourceNotReady):
        status = 'not ready yet'
      except AttributeError:
        status = 'unknown'
      error_message = 'Connection parameter %s not found. '\
          'Requested instance is currently %s. If this error persists, '\
          'check status of this instance.' % (self.failed, status)
      self.logger.warning(error_message)
    return []

  update = install

class Serialised(Recipe):
  def _filterForStorage(self, partition_parameter_kw):
    return wrap(partition_parameter_kw)

  def _getReturnParameterDict(self, instance, return_parameter_list):
    try:
      return json.loads(instance.getConnectionParameter(JSON_SERIALISED_MAGIC_KEY))
    except slapmodule.NotFoundError:
      return {}




CONNECTION_PARAMETER_STRING = 'connection-'

class RequestEdge(Recipe):
  """
  For each country in country-list, do a request.
  """
  def __init__(self, buildout, name, options):
    self.logger = logging.getLogger(name)
    self.options = options
    self.request_dict = {}
    # Keep a copy of original options dict
    original_options = options.copy()
    for country in options['country-list'].split(','):
      # Request will have its own copy of options dict
      local_options = original_options.copy()
      local_options['name'] = '%s-%s' % (country, name)
      local_options['sla-region'] = country

      self.request_dict[country] = Recipe(buildout, name, local_options)
      # "Bubble" all connection parameters
      for option, value in local_options.iteritems():
        if option.startswith(CONNECTION_PARAMETER_STRING):
          self.options['%s-%s' % (option, country)] = value

  def install(self):
    for country, request in self.request_dict.iteritems():
      request.install()
    return []

  update = install

