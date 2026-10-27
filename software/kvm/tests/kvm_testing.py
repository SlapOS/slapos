##############################################################################
#
# Copyright (c) 2026 Nexedi SA and Contributors. All Rights Reserved.
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
"""What the kvm and the upgrade_kvm test suites share

The tap interface part exists because the standalone of the test framework
creates no tap interface for the partitions it formats, while qemu refuses to
start when it is given an empty tap interface name, so the tests hand their
partitions the tap of the outermost partition they run in.
"""

import json
import os
from urllib.parse import urlparse

import slapos.slap


def getTopLevelPartitionPath(path):
  """Return the outermost partition containing path, or None"""
  index = 0
  while True:
    index = path.find(os.path.sep, index + 1)
    candidate = path if index == -1 else path[:index]
    if os.path.exists(os.path.join(candidate, '.slapos-resource')):
      return candidate
    if index == -1:
      return None


def updateResource(partition_path, **kw):
  """Update the resource file of a partition"""
  with open(os.path.join(partition_path, '.slapos-resource'), 'r+') as fh:
    resource = json.load(fh)
    resource.update(kw)
    fh.seek(0)
    fh.truncate()
    json.dump(resource, fh, indent=2)


def getTopLevelTap(path):
  """Return the tap of the outermost partition which contains path"""
  top_level_partition_path = getTopLevelPartitionPath(path)
  if top_level_partition_path is None:
    return {}
  with open(os.path.join(
    top_level_partition_path, '.slapos-resource')) as fh:
    return json.load(fh).get('tap', {})


def stealTopLevelTap(instance_directory, partition_reference):
  """Give the tap of the outermost partition to the partitions of a test"""
  tap = getTopLevelTap(instance_directory)
  for partition in os.listdir(instance_directory):
    if partition.startswith(partition_reference):
      updateResource(os.path.join(instance_directory, partition), tap=tap)


class KvmPartitionMixin:
  """Locate the partitions of a kvm instance tree, and their parameters"""
  # an upgrade test requests the same instance on another software release, so
  # the partitions are not matched by the software release by default
  match_software_url = False

  @classmethod
  def getPartitionIdByType(cls, instance_type):
    software_url = cls.getSoftwareURL() if cls.match_software_url else None
    for computer_partition in cls.slap.computer.getComputerPartitionList():
      try:
        partition_type = computer_partition.getType()
        partition_url = computer_partition.\
          getSoftwareRelease()._software_release
      except (
        slapos.slap.exception.NotFoundError,
        slapos.slap.exception.ResourceNotReady
      ):
        continue
      if partition_type == instance_type and software_url in (
        None, partition_url):
        return computer_partition.getId()
    raise ValueError('Partition type %s not found' % (instance_type,))

  @classmethod
  def getPartitionPath(cls, instance_type='kvm-export', *paths):
    return os.path.join(
      cls.slap.instance_directory, cls.getPartitionIdByType(instance_type),
      *paths)

  def getConnectionParameterDictJson(self):
    return json.loads(
      self.computer_partition.getConnectionParameterDict()['_'])

  @classmethod
  def getAuthenticatedUrl(cls, connection_parameter_dict, prefix='',
                          additional=False):
    parsed_url = urlparse(
      connection_parameter_dict['%surl%s' % (
        prefix, '-additional' if additional else '')])
    return parsed_url._replace(
      netloc='{}:{}@[{}]:{}'.format(
        connection_parameter_dict['%susername' % prefix],
        connection_parameter_dict['%spassword' % prefix],
        parsed_url.hostname,
        parsed_url.port,
      )).geturl()
