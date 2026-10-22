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

import json
import os

from slapos.slap.slap import slap
from slapos.testing.testcase import (
  installSoftwareUrlList,
  makeModuleSetUpAndTestCaseClass,
)
from slapos.util import dumps

# 1.0.511 is the release that introduced slapos.core 1.25.0, the last version
# whose proxy database schema (version 17) has no requester_id column on the
# slave table. Bump this as releases advance.
old_software_release_url = 'https://lab.nexedi.com/nexedi/slapos/-/raw/' \
  '1.0.511/software/slapproxy/software.cfg'
new_software_release_url = os.path.abspath(
  os.path.join(os.path.dirname(__file__), os.pardir, 'software.cfg'))

_, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  old_software_release_url,
  software_id='upgrade_slapproxy',
  skip_software_check=True,
)


def setUpModule():
  installSoftwareUrlList(
    SlapOSInstanceTestCase,
    [old_software_release_url, new_software_release_url],
    debug=SlapOSInstanceTestCase._debug,
  )


class TestSlapproxyUpgrade(SlapOSInstanceTestCase):
  __partition_reference__ = 'u'
  # amount of instantiations the instance tree needs to stabilize
  propagation_amount = 2

  _current_software_url = old_software_release_url

  # computer registered on the nested proxy this test deploys and drives,
  # distinct from the outer standalone computer running this test
  nested_computer_id = 'NESTED-COMP'
  nested_software_release = 'http://sr//'
  nested_instance_reference = 'NestedInstance'
  nested_shared_reference = 'NestedSharedInstance'

  @classmethod
  def getSoftwareURL(cls):
    return cls._current_software_url

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'accepted-client-ipv6': cls._ipv6_address,
      'json-schema-repository': {
        'url': os.path.abspath(os.path.join(__file__, '../' * 4)),
        'revision': '',
      },
    })}

  @classmethod
  def getNestedSlap(cls):
    """A slap client connected to the proxy this test's own instance runs,
    simulating a compute node using it as its SlapOS master."""
    proxy_url = cls.computer_partition.getConnectionParameterDict()[
      'slapproxy-ipv4-url']
    nested_slap = slap()
    nested_slap.initializeConnection(proxy_url)
    return nested_slap

  @classmethod
  def formatNestedComputer(cls, partition_amount):
    """Register a computer with some free partitions on the nested proxy,
    simulating a first `slapos node format` run."""
    computer = cls.nested_slap.registerComputer(cls.nested_computer_id)
    computer.updateConfiguration(dumps({
      'reference': cls.nested_computer_id,
      'address': '12.34.56.78',
      'netmask': '255.255.255.255',
      'partition_list': [
        {
          'reference': 'nestedpart%s' % i,
          'address_list': [
            {'addr': '1.2.3.4', 'netmask': '255.255.255.255'},
          ],
          'tap': {'name': 'tap0'},
        }
        for i in range(partition_amount)
      ],
    }))

  @classmethod
  def nestedRequest(cls, software_release, partition_reference, **kw):
    # scope the request to the computer this test formatted: without this,
    # the server falls back to its own ambient computer_id, which is the
    # outer standalone's, not the nested one this test is driving
    kw.setdefault('filter_kw', {})
    kw['filter_kw'].setdefault('computer_guid', cls.nested_computer_id)
    return cls.nested_slap.registerOpenOrder().request(
      software_release, partition_reference, **kw)

  @classmethod
  def getNestedPartitionInformation(cls, partition_id):
    """The full, server-synchronised information of a partition of the
    nested computer, as held by the nested proxy (not from the local cache
    a ComputerPartition keeps after a request)."""
    computer = cls.nested_slap.registerComputer(cls.nested_computer_id)
    for computer_partition in computer.getComputerPartitionList():
      if computer_partition._partition_id == partition_id:
        return computer_partition
    raise AssertionError('Partition %r not found' % (partition_id,))

  @classmethod
  def getNestedSlaveReference(cls, host_partition_id):
    # mirrors how a master instance would discover the slave reference of a
    # shared instance it hosts, through its own parameter dict
    host_partition = cls.getNestedPartitionInformation(host_partition_id)
    slave_instance_list = host_partition._parameter_dict['slave_instance_list']
    assert len(slave_instance_list) == 1, slave_instance_list
    return slave_instance_list[0]['slave_reference']

  @classmethod
  def setUpOldInstance(cls):
    """Populate the nested proxy with data while it still runs the old
    software release, so that the upgrade has something to migrate."""
    cls.nested_slap = cls.getNestedSlap()
    cls.formatNestedComputer(2)

    instance = cls.nestedRequest(
      cls.nested_software_release, cls.nested_instance_reference)
    cls.old_instance_partition_id = instance._partition_id
    instance.setConnectionDict({'foo': 'bar'})

    shared_instance = cls.nestedRequest(
      cls.nested_software_release, cls.nested_shared_reference, shared=True)
    cls.old_shared_instance_partition_id = shared_instance._partition_id
    cls.old_slave_reference = cls.getNestedSlaveReference(
      cls.old_instance_partition_id)
    shared_instance.setConnectionDict(
      {'baz': 'qux'}, slave_reference=cls.old_slave_reference)

  @classmethod
  def setUpClass(cls):
    # request and instantiate with the old software release
    super().setUpClass()

    cls.setUpOldInstance()

    cls._current_software_url = new_software_release_url
    cls.logger.debug('Requesting instance on new software release')
    cls.requestDefaultInstance()
    snapshot_name = '%s.%s.setUpClass new instance' % (
      cls.__module__, cls.__name__)
    try:
      for _ in range(cls.propagation_amount):
        cls.slap.waitForInstance(
          max_retry=cls.instance_max_retry, debug=cls._debug)
      cls.logger.debug('Instance on new software release done')
    except BaseException:
      cls.logger.exception('Error during instance on new software release')
      cls._storeSystemSnapshot(snapshot_name)
      cls._cleanup(snapshot_name)
      cls.setUp = lambda self: self.fail('Setup Class failed.')
      raise
    else:
      cls._storeSystemSnapshot(snapshot_name)

    cls.computer_partition = cls.requestDefaultInstance()
    # the proxy restarted on the new software release: reconnect
    cls.nested_slap = cls.getNestedSlap()

  def test_instance_survives_upgrade(self):
    # requesting the same reference again must return the very same
    # partition, with the connection parameters set before the upgrade
    instance = self.nestedRequest(
      self.nested_software_release, self.nested_instance_reference)
    self.assertEqual(
      self.old_instance_partition_id, instance._partition_id)
    self.assertEqual(
      {'foo': 'bar'}, instance.getConnectionParameterDict())

  def test_shared_instance_survives_upgrade(self):
    # the slave table has been migrated to the new schema: both the
    # connection parameters set before the upgrade and the ability to set
    # new ones must still work
    shared_instance = self.nestedRequest(
      self.nested_software_release, self.nested_shared_reference,
      shared=True)
    self.assertEqual(
      self.old_shared_instance_partition_id, shared_instance._partition_id)
    self.assertEqual(
      {'baz': 'qux'}, shared_instance.getConnectionParameterDict())
    slave_reference = self.getNestedSlaveReference(
      self.old_instance_partition_id)
    self.assertEqual(self.old_slave_reference, slave_reference)
    shared_instance.setConnectionDict(
      {'baz': 'updated'}, slave_reference=slave_reference)
    shared_instance = self.nestedRequest(
      self.nested_software_release, self.nested_shared_reference,
      shared=True)
    self.assertEqual(
      {'baz': 'updated'}, shared_instance.getConnectionParameterDict())

  def test_can_request_new_partition_after_upgrade(self):
    # a partition requested for the first time after the upgrade must work
    # as well, on a freshly allocated partition
    instance = self.nestedRequest(
      self.nested_software_release, 'NewInstanceAfterUpgrade')
    self.assertNotIn(
      instance._partition_id,
      (self.old_instance_partition_id,
       self.old_shared_instance_partition_id))
    instance.setConnectionDict({'new': 'value'})
    instance = self.nestedRequest(
      self.nested_software_release, 'NewInstanceAfterUpgrade')
    self.assertEqual({'new': 'value'}, instance.getConnectionParameterDict())
