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
from slapos.recipe.librecipe import wrap, JSON_SERIALISED_MAGIC_KEY
import json
from slapos import slap as slapmodule

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

    Output:
      See "return" input key.
  """
  failed = None

  def __init__(self, buildout, name, options):
    self.logger = logging.getLogger(name)

    slap = slapmodule.slap()

    software_url = options['software-url']
    name = options['name']

    slap.initializeConnection(options['server-url'],
                              options.get('key-file'),
                              options.get('cert-file'),
                             )
    request = slap.registerComputerPartition(
      options['computer-id'], options['partition-id']).request

    isSlave = options.get('slave', '').lower() in ['y', 'yes', 'true', '1']

    return_parameters = []
    if 'return' in options:
      return_parameters = [str(parameter).strip()
        for parameter in options['return'].split()]
    else:
      self.logger.debug("No parameter to return to main instance."
        "Be careful about that...")

    software_type = options.get('software-type', 'RootInstanceSoftware')

    filter_kw = {}
    if 'sla' in options:
      for sla_parameter in options['sla'].split():
        filter_kw[sla_parameter] = options['sla-%s' % sla_parameter]

    partition_parameter_kw = {}
    if 'config' in options:
      for config_parameter in options['config'].split():
        partition_parameter_kw[config_parameter] = \
            options['config-%s' % config_parameter]
    partition_parameter_kw = self._filterForStorage(partition_parameter_kw)

    self.instance = instance = request(software_url, software_type,
      name, partition_parameter_kw=partition_parameter_kw,
      filter_kw=filter_kw, shared=isSlave)
    return_parameter_dict = self._getReturnParameterDict(instance,
      return_parameters)
    for param in return_parameters:
      try:
        value = return_parameter_dict[param]
      except KeyError:
        value = ''
        if self.failed is None:
          self.failed = param
      options['connection-%s' % param] = value

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
    if self.failed is not None:
      # Check instance status to know if instance has been deployed
      try:
        status = self.instance.getState()
      except slapmodule.NotFoundError:
        status = 'not ready yet, please try again'
      except AttributeError:
        status = 'unknown'
      error_message = 'Connection parameter %s not found. '\
          'Status of requested instance is: %s. If this error persists, '\
          'check status of this instance.' % (self.failed, status)
      self.logger.error(error_message)
      raise KeyError(error_message)
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
