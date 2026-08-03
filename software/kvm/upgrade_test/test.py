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

import glob
import json
import os
import subprocess
import time
import unittest
from urllib.parse import urlparse

import requests
import slapos.slap

from slapos.grid.utils import md5digest
from slapos.testing.testcase import (
  installSoftwareUrlList,
  makeModuleSetUpAndTestCaseClass,
)

old_software_release_url = 'https://lab.nexedi.com/nexedi/slapos/-/raw/' \
  '1.0.462/software/kvm/software.cfg'
new_software_release_url = os.path.abspath(
  os.path.join(os.path.dirname(__file__), os.pardir, 'software.cfg'))

has_kvm = os.access('/dev/kvm', os.R_OK | os.W_OK)
skipUnlessKvm = unittest.skipUnless(has_kvm, 'kvm not loaded or not allowed')

_, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  old_software_release_url,
  software_id='upgrade_kvm',
  skip_software_check=True,
)


def setUpModule():
  installSoftwareUrlList(
    SlapOSInstanceTestCase,
    [old_software_release_url, new_software_release_url],
    debug=SlapOSInstanceTestCase._debug,
  )


class KvmUpgradeTestCase(SlapOSInstanceTestCase):
  # short partition names, as the resilient instance tree is deep
  __partition_reference__ = 'u'
  instance_max_retry = 20
  # amount of instantiations the instance tree needs to stabilize
  propagation_amount = 3

  _current_software_url = old_software_release_url

  @classmethod
  def getSoftwareURL(cls):
    return cls._current_software_url

  @classmethod
  def setUpOldInstance(cls):
    """Hook executed on the instance running the old software release"""

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

  @classmethod
  def getPartitionIdByType(cls, instance_type):
    for computer_partition in cls.slap.computer.getComputerPartitionList():
      try:
        partition_type = computer_partition.getType()
      except (
        slapos.slap.exception.NotFoundError,
        slapos.slap.exception.ResourceNotReady
      ):
        continue
      if partition_type == instance_type:
        return computer_partition.getId()
    raise Exception('Partition type %s not found' % (instance_type,))

  @classmethod
  def getPartitionPath(cls, instance_type, *paths):
    return os.path.join(
      cls.slap.instance_directory, cls.getPartitionIdByType(instance_type),
      *paths)

  def getConnectionParameterDictJson(self):
    return json.loads(
      self.computer_partition.getConnectionParameterDict()['_'])

  def assertNoVncIsAccessible(self, prefix=''):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    parsed_url = urlparse(connection_parameter_dict['%surl' % (prefix,)])
    result = requests.get(
      parsed_url._replace(
        netloc='%s:%s@[%s]:%s' % (
          connection_parameter_dict['%susername' % (prefix,)],
          connection_parameter_dict['%spassword' % (prefix,)],
          parsed_url.hostname,
          parsed_url.port)).geturl(),
      verify=False)
    self.assertEqual(requests.codes.ok, result.status_code)
    self.assertIn('<title>noVNC</title>', result.text)

class KvmUpgradedMixin:
  """Assertions common to any upgraded kvm instance"""
  # the standalone instance, and each kvm of a cluster, is of type default
  kvm_instance_type = 'default'

  @classmethod
  def getKvmPartitionPath(cls, *paths):
    return cls.getPartitionPath(cls.kvm_instance_type, *paths)

  @classmethod
  def setUpOldInstance(cls):
    super().setUpOldInstance()
    image_stat = os.stat(cls.getKvmPartitionPath('srv', 'virtual.qcow2'))
    cls.old_disk_image_identity = (image_stat.st_dev, image_stat.st_ino)

  def test_all_partitions_use_new_software_release(self):
    self.assertEqual(
      {
        os.path.basename(os.readlink(software_release))
        for software_release in glob.glob(os.path.join(
          self.slap.instance_directory, '*', 'software_release'))
      },
      {md5digest(new_software_release_url)},
    )

  def test_disk_image_is_not_recreated(self):
    image_stat = os.stat(self.getKvmPartitionPath('srv', 'virtual.qcow2'))
    self.assertEqual(
      self.old_disk_image_identity, (image_stat.st_dev, image_stat.st_ino))

  def test_virtual_machine_runs(self):
    with open(self.getKvmPartitionPath('var', 'run', 'kvm.pid')) as fh:
      # raises if the qemu process of the upgraded instance is gone
      os.kill(int(fh.read()), 0)


@skipUnlessKvm
class TestKvmUpgrade(KvmUpgradedMixin, KvmUpgradeTestCase):
  propagation_amount = 2

  def test_novnc_is_accessible(self):
    self.assertNoVncIsAccessible()


@skipUnlessKvm
class TestKvmClusterUpgrade(KvmUpgradedMixin, KvmUpgradeTestCase):
  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'kvm-partition-dict': {
        'KVM0': {
          'disable-ansible-promise': True
        }
      }
    })}

  def test_novnc_is_accessible(self):
    self.assertNoVncIsAccessible(prefix='KVM0-')


@skipUnlessKvm
class TestKvmResilientUpgrade(KvmUpgradedMixin, KvmUpgradeTestCase):
  kvm_instance_type = 'kvm-export'
  # qmpbackup before 0.63, used by the old software release, named the backup
  # chain directory after the qemu node name
  old_chain_directory_name = 'virtual1'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'

  @classmethod
  def getInstanceParameterDict(cls):
    # the backups of this test are the explicit ones, so that the upgrade finds
    # the exact backup state it is asserted with
    return {'_': json.dumps({'resiliency-backup-periodicity': '0 0 1 1 *'})}

  @classmethod
  def callExporter(cls):
    # backup like the cron entry of the resilient stack does, which also
    # notifies the pull backup server and thus makes the clone import
    try:
      return subprocess.check_output(
        [
          cls.getPartitionPath('kvm-export', 'bin', 'exporter'),
          '--transaction-id', str(int(time.time()))],
        stderr=subprocess.STDOUT).decode('utf-8')
    except subprocess.CalledProcessError as error:
      raise ValueError(
        'Exporter failed with %s' % (error.output.decode('utf-8'),)) from error

  @classmethod
  def awaitImport(cls):
    equeue_log = cls.getPartitionPath('kvm-import', 'var', 'log', 'equeue.log')
    for retry in range(30):
      with open(equeue_log) as fh:
        equeue_log_content = fh.read()
      if 'finished successfully' in equeue_log_content:
        return equeue_log_content
      time.sleep(min(retry, 5))
    raise ValueError('Import not finished: %s' % (equeue_log_content,))

  @classmethod
  def truncateImportLog(cls):
    with open(
      cls.getPartitionPath('kvm-import', 'var', 'log', 'equeue.log'),
      'w') as fh:
      fh.write('')

  @classmethod
  def backup(cls):
    cls.truncateImportLog()
    status_text = cls.callExporter()
    cls.awaitImport()
    return status_text

  @classmethod
  def getChainFileList(cls, chain_directory_name='virtual.qcow2'):
    return os.listdir(cls.getPartitionPath(
      'kvm-export', 'srv', 'backup', 'kvm', chain_directory_name))

  @classmethod
  def setUpOldInstance(cls):
    super().setUpOldInstance()
    # back up with the old software release, so that the upgrade finds a
    # complete backup chain of the old style to migrate
    cls.backup()
    cls.old_chain_file_list = cls.getChainFileList(
      cls.old_chain_directory_name)

  def test_old_backup_chain_was_complete(self):
    # sanity check of the state the upgrade started from
    self.assertEqual(
      1,
      len([q for q in self.old_chain_file_list if q.startswith('FULL-')]),
      self.old_chain_file_list)

  def test_backup_chain_is_migrated(self):
    status_text = self.backup()
    self.assertIn(
      'Migrated from old style backup by removing backup directory and '
      'bitmaps', status_text)
    self.assertFalse(os.path.exists(self.getPartitionPath(
      'kvm-export', 'srv', 'backup', 'kvm', self.old_chain_directory_name)))
    chain_file_list = self.getChainFileList()
    self.assertEqual(
      1, len([q for q in chain_file_list if q.startswith('FULL-')]),
      chain_file_list)
    self.assertEqual(
      0, len([q for q in chain_file_list if q.startswith('INC-')]),
      chain_file_list)

    # the migrated bitmap is what allows the next backup to be incremental
    status_text = self.backup()
    self.assertNotIn('Migrated from old style backup', status_text)
    chain_file_list = self.getChainFileList()
    self.assertEqual(
      1, len([q for q in chain_file_list if q.startswith('INC-')]),
      chain_file_list)

    # and the clone holds what has been exported
    self.assertEqual(
      sorted(chain_file_list),
      sorted(os.listdir(self.getPartitionPath(
        'kvm-import', 'srv', 'backup', 'kvm', 'virtual.qcow2'))))
    self.assertTrue(os.path.exists(self.getPartitionPath(
      'kvm-import', 'srv', 'virtual.qcow2')))
