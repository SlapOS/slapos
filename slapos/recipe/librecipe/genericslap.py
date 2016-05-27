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
from slapos import slap
import time

from generic import GenericBaseRecipe

CONNECTION_CACHE = {}

class GenericSlapRecipe(GenericBaseRecipe):
  """Base class for all slap.recipe.* needing SLAP informations like instance
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
    self.software_release_url = slap_connection['software-release-url']
    self.key_file = slap_connection.get('key-file')
    self.cert_file = slap_connection.get('cert-file')

  def install(self):

    cache_key = "%s_%s" % (self.computer_id, self.computer_partition_id)
    self.computer_partition = CONNECTION_CACHE.get(cache_key, None)

    self.slap.initializeConnection(self.server_url, self.key_file,
        self.cert_file)
    if self.computer_partition is None:
      self.computer_partition = self.slap.registerComputerPartition(
        self.computer_id,
        self.computer_partition_id)
      CONNECTION_CACHE[cache_key] = self.computer_partition

    self.request = self.computer_partition.request
    self.setConnectionDict = self.computer_partition.setConnectionDict
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
