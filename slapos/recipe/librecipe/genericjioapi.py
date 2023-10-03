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
import json
import logging
import os
from slapos import slap
from slapos.grid.SlapObject import SOFTWARE_INSTANCE_JSON_FILENAME
from slapos.util import (dict2xml, xml2dict, calculate_dict_hash, dumps,
                         SoftwareReleaseSchema)
import time

from .generic import GenericBaseRecipe
from . import updateTransactionFile

CONNECTION_CACHE = {}

class GenericjIOAPIRecipe(GenericBaseRecipe):
  """Base class for all slap.recipe.* needing instance informations like instance
     parameters.
     recipes that don't explicitely need to retrieve from server informations
     should use GenericBaseRecipe."""

  def __init__(self, buildout, name, options):
    """Default initialisation"""
    GenericBaseRecipe.__init__(self, buildout, name, options)
    self.slap = slap.slap()

    # SLAP related information
    slap_connection = buildout['slap-connection']
    self.computer_id = slap_connection['computer-id']
    self.computer_partition_id = slap_connection['partition-id']
    self.server_url = slap_connection['server-url']
    self.slapgrid_jio_uri = slap_connection['slapgrid-jio-uri']
    self.software_release_url = slap_connection['software-release-url']
    self.key_file = slap_connection.get('key-file')
    self.cert_file = slap_connection.get('cert-file')
    self.software_instance_reference = slap_connection.get('software-instance-reference', '')
    self.instance_root = buildout['buildout']['directory']
    self.instance_json_path = os.path.join(
      self.instance_root,
      SOFTWARE_INSTANCE_JSON_FILENAME
    )
    self.backward_compatibility = False

  def install(self):
    self.computer_partition = None

    if os.path.exists(self.instance_json_path):
      with open(self.instance_json_path, "r") as f:
        self.computer_partition = json.load(f)

    self.slap.initializeConnection(self.server_url,
      key_file=self.key_file, cert_file=self.cert_file,
      slapgrid_jio_uri=self.slapgrid_jio_uri)

    # Fallback to requesting to SlapOS Master
    if not self.computer_partition:
      if self.slap.jio_api_connector:
        if self.software_instance_reference:
          self.computer_partition = self.slap.jio_api_connector.get({
            "portal_type": "Software Instance",
            "reference": self.software_instance_reference,
          })
        else:
          self.computer_partition = self.slap.jio_api_connector.get({
            "portal_type": "Software Instance",
            "compute_node_id": self.computer_id,
            "compute_partition_id": self.computer_partition_id,
          })

    self.parameter_dict = None
    if self.computer_partition:
      self.parameter_dict = self.computer_partition.get("parameters", {})
    if self.slap.jio_api_connector:
      self.request = self.requestWithAPI
      self.setConnectionDict = self.setConnectionDictWithAPI
    else:
      self.computer_partition = self.slap.registerComputerPartition(
        self.computer_id,
        self.computer_partition_id)
      CONNECTION_CACHE[cache_key] = self.computer_partition

      self.request = self.computer_partition.request
      self.setConnectionDict = self.computer_partition.setConnectionDict
      if self.parameter_dict is None:
        self.parameter_dict = self.computer_partition.getInstanceParameterDict()

    # call children part of install
    path_list = self._install()

    return path_list

  update = install

  def _install(self):
    """Hook which shall be implemented in children class"""
    raise NotImplementedError('Shall be implemented by subclass')

  def setConnectionUrl(self, *args, **kwargs):
    url = self.unparseUrl(*args, **kwargs)
    self.setConnectionDict(dict(url=url))

  def setConnectionDictWithAPI(self, connection_dict, slave_reference=None):
    # recreate and stabilise connection_dict that it would became the same as on server
    connection_dict = xml2dict(dict2xml(connection_dict))
    if self.computer_partition.get("connection_parameters", {}) == connection_dict:
      return

    if slave_reference is not None:
      # check the connection parameters from the slave

      # Should we check existence?
      slave_parameter_list = self.computer_partition.get("slave_instance_list", [])
      slave_connection_dict = {}
      connection_parameter_hash = None
      for slave_parameter_dict in slave_parameter_list:
        if slave_parameter_dict.get("slave_reference") == slave_reference:
          connection_parameter_hash = slave_parameter_dict.get("connection-parameter-hash", None)
          break

      # Skip as nothing changed for the slave
      if connection_parameter_hash is not None and \
        connection_parameter_hash == calculate_dict_hash(connection_dict):
        return

    if slave_reference:
      reference = slave_reference
    else:
      reference = self.computer_partition.get("reference")

    self.slap.jio_api_connector.put({
      "portal_type": "Software Instance",
      "reference": reference,
      "connection_parameters": connection_dict,
    })

  def requestWithAPI(self, software_release, software_type, partition_reference,
                     shared=False, partition_parameter_kw=None, filter_kw=None,
                     state=None):
    """
      Lot of duplicated code with request recipe
      It doesn't seem to be used
    """
    if partition_parameter_kw is None:
      partition_parameter_kw = {}
    elif not isinstance(partition_parameter_kw, dict):
      raise ValueError("Unexpected type of partition_parameter_kw '%s'" %
                       partition_parameter_kw)

    if filter_kw is None:
      filter_kw = {}
    elif not isinstance(filter_kw, dict):
      raise ValueError("Unexpected type of filter_kw '%s'" %
                       filter_kw)

    # Let enforce a default software type
    if software_type is None:
      software_type = DEFAULT_SOFTWARE_TYPE

    request_dict = {
      "title": partition_reference,
      "software_type": software_type,
      "software_release_uri": software_release,
      "portal_type": "Software Instance",
      "compute_node_id": self.computer_id,
      "compute_partition_id": self.computer_partition_id,
    }
    if partition_parameter_kw:
      request_dict["parameters"] = json.dumps(partition_parameter_kw)
    if filter_kw:
      request_dict["sla_parameters"] = filter_kw
    if shared:
      request_dict["shared"] = True
    if state:
      request_dict["state"] = state

    try:
      SoftwareReleaseSchema(
          request_dict['software_release'],
          request_dict['software_type']
      ).validateInstanceParameterDict(
          loads(request_dict['partition_parameter_xml']))
    except jsonschema.ValidationError as e:
      warnings.warn(
        "Request parameters do not validate against schema definition:\n{e}".format(e=e),
        UserWarning,
      )
    except Exception as e:
      # note that we intentionally catch wide exceptions, so that if anything
      # is wrong with fetching the schema or the schema itself this does not
      # prevent users from requesting instances.
      warnings.warn(
        "Error validating request parameters against schema definition:\n{e.__class__.__name__} {e}".format(e=e),
        UserWarning,
      )

    updateTransactionFile(self.computer_partition_id, partition_reference)
    partition_dict = self.slap.jio_api_connector.post(request_dict)

    if "$schema" in partition_dict and "error-response-schema.json" in partition_dict["$schema"]:
      self.logger.warning(
        'Request for %(request_name)r with software release '
        '%(software_release)r and software type %(software_type)r failed '
        'with partition_parameter_kw=%(partition_parameter_kw)r, '
        'filter_kw=%(filter_kw)r, shared=%(shared)r, state=%(state)r.', dict(
          software_release=software_release,
          software_type=software_type,
          request_name=partition_reference,
          partition_parameter_kw=partition_parameter_kw,
          filter_kw=filter_kw,
          shared=shared,
          state=state
        )
      )
      self._raise_request_exception = slap.NotFoundError
      self._raise_request_exception_formatted = str(partition_dict["message"])
      return request_dict
    return partition_dict
