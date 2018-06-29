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
import os
import time
import unittest

from slapos.slap import ComputerPartition as SlapComputerPartition

from slapos.grid.SlapObject import Partition, Software
from slapos.grid import utils
from slapos.grid import networkcache
# XXX: BasicMixin should be in a separated module, not in slapgrid test module.
from slapos.tests.slapgrid import BasicMixin

# Mockup
# XXX: Ambiguous name
# XXX: Factor with common SlapOS tests
class FakeCallAndStore(object):
  """
  Used to check if the mocked method has been called.
  """
  def __init__(self):
    self.called = False

  def __call__(self, *args, **kwargs):
    self.called = True

class FakeCallAndNoop(object):
  """
  Used to no-op a method.
  """
  def __call__(self, *args, **kwargs):
    pass

# XXX: change name and behavior to be more generic and factor with other tests
class FakeNetworkCacheCallAndRead(object):
  """
  Short-circuit normal calls to slapos buildout helpers, get and store
  'additional_buildout_parameter_list' for future analysis.
  """
  def __init__(self):
    self.external_command_list = []

  def __call__(self, *args, **kwargs):
    additional_buildout_parameter_list = \
        kwargs.get('additional_buildout_parameter_list')
    self.external_command_list.extend(additional_buildout_parameter_list)

# Backup modules
original_install_from_buildout = Software._install_from_buildout
original_upload_network_cached = networkcache.upload_network_cached
originalBootstrapBuildout = utils.bootstrapBuildout
originalLaunchBuildout = utils.launchBuildout
originalUploadSoftwareRelease = Software.uploadSoftwareRelease
originalPartitionGenerateSupervisorConfigurationFile = Partition.generateSupervisorConfigurationFile

class MasterMixin(BasicMixin, unittest.TestCase):
  """
  Master Mixin of slapobject test classes.
  """
  def setUp(self):
    BasicMixin.setUp(self)
    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)

  def tearDown(self):
    BasicMixin.tearDown(self)

    # Un-monkey patch possible modules
    global originalBootstrapBuildout
    global originalLaunchBuildout
    utils.bootstrapBuildout = originalBootstrapBuildout
    utils.launchBuildout = originalLaunchBuildout

  # Helper functions
  def createSoftware(self, url=None, empty=False):
    """
    Create an empty software, and return a Software object from
    dummy parameters.
    """
    if url is None:
      url = 'mysoftware'

    software_path = os.path.join(self.software_root, utils.md5digest(url))
    os.mkdir(software_path)

    if not empty:
      # Populate the Software Release directory so that it is "complete" and
      # "working" from a slapos point of view.
      open(os.path.join(software_path, 'instance.cfg'), 'w').close()

    return Software(
      url=url,
      software_root=self.software_root,
      buildout=self.buildout,
      logger=logging.getLogger(),
    )

  def createPartition(
      self,
      software_release_url,
      partition_id=None,
      slap_computer_partition=None,
      retention_delay=None,
  ):
    """
    Create a partition, and return a Partition object created
    from dummy parameters.
    """
    # XXX dirty, should disappear when Partition is cleaned up
    software_path = os.path.join(
        self.software_root,
        utils.md5digest(software_release_url)
    )

    if partition_id is None:
      partition_id = 'mypartition'

    if slap_computer_partition is None:
      slap_computer_partition = SlapComputerPartition(
        computer_id='bidon',
        partition_id=partition_id)

    instance_path = os.path.join(self.instance_root, partition_id)
    os.mkdir(instance_path)
    os.chmod(instance_path, 0o750)

    supervisor_configuration_path = os.path.join(
          self.instance_root, 'supervisor')
    os.mkdir(supervisor_configuration_path)

    partition = Partition(
      software_path=software_path,
      instance_path=instance_path,
      supervisord_partition_configuration_path=os.path.join(
          supervisor_configuration_path, partition_id),
      supervisord_socket=os.path.join(
          supervisor_configuration_path, 'supervisor.sock'),
      computer_partition=slap_computer_partition,
      computer_id='bidon',
      partition_id=partition_id,
      server_url='bidon',
      software_release_url=software_release_url,
      buildout=self.buildout,
      logger=logging.getLogger(),
    )

    partition.updateSupervisor = FakeCallAndNoop
    if retention_delay:
      partition.retention_delay = retention_delay

    return partition

class TestSoftwareNetworkCacheSlapObject(MasterMixin, unittest.TestCase):
  """
  Test for Network Cache related features in Software class.
  """
  def setUp(self):
    MasterMixin.setUp(self)
    self.fakeCallAndRead = FakeNetworkCacheCallAndRead()
    utils.bootstrapBuildout = self.fakeCallAndRead
    utils.launchBuildout = self.fakeCallAndRead

    self.signature_private_key_file = '/signature/private/key_file'
    self.upload_cache_url = 'http://example.com/uploadcache'
    self.upload_dir_url = 'http://example.com/uploaddir'
    self.shacache_ca_file = '/path/to/shacache/ca/file'
    self.shacache_cert_file = '/path/to/shacache/cert/file'
    self.shacache_key_file = '/path/to/shacache/key/file'
    self.shadir_ca_file = '/path/to/shadir/ca/file'
    self.shadir_cert_file = '/path/to/shadir/cert/file'
    self.shadir_key_file = '/path/to/shadir/key/file'

  def tearDown(self):
    MasterMixin.tearDown(self)

    Software._install_from_buildout = original_install_from_buildout
    networkcache.upload_network_cached = original_upload_network_cached
    Software.uploadSoftwareRelease = originalUploadSoftwareRelease

  # Test methods
  def test_software_install_with_networkcache(self):
    """
      Check if the networkcache parameters are propagated.
    """
    software = Software(
        url='http://example.com/software.cfg',
        software_root=self.software_root,
        buildout=self.buildout,
        logger=logging.getLogger(),
        signature_private_key_file='/signature/private/key_file',
        upload_cache_url='http://example.com/uploadcache',
        upload_dir_url='http://example.com/uploaddir',
        shacache_ca_file=self.shacache_ca_file,
        shacache_cert_file=self.shacache_cert_file,
        shacache_key_file=self.shacache_key_file,
        shadir_ca_file=self.shadir_ca_file,
        shadir_cert_file=self.shadir_cert_file,
        shadir_key_file=self.shadir_key_file)

    software.install()

    command_list = self.fakeCallAndRead.external_command_list
    self.assertIn('buildout:networkcache-section=networkcache', command_list)
    self.assertIn('networkcache:signature-private-key-file=%s' % self.signature_private_key_file, command_list)
    self.assertIn('networkcache:upload-cache-url=%s' % self.upload_cache_url, command_list)
    self.assertIn('networkcache:upload-dir-url=%s' % self.upload_dir_url, command_list)
    self.assertIn('networkcache:shacache-ca-file=%s' % self.shacache_ca_file, command_list)
    self.assertIn('networkcache:shacache-cert-file=%s' % self.shacache_cert_file, command_list)
    self.assertIn('networkcache:shacache-key-file=%s' % self.shacache_key_file, command_list)
    self.assertIn('networkcache:shadir-ca-file=%s' % self.shadir_ca_file, command_list)
    self.assertIn('networkcache:shadir-cert-file=%s' % self.shadir_cert_file, command_list)
    self.assertIn('networkcache:shadir-key-file=%s' % self.shadir_key_file, command_list)

  def test_software_install_without_networkcache(self):
    """
      Check if the networkcache parameters are not propagated if they are not
      available.
    """
    software = Software(url='http://example.com/software.cfg',
                                   software_root=self.software_root,
                                   buildout=self.buildout,
                                   logger=logging.getLogger())
    software.install()

    command_list = self.fakeCallAndRead.external_command_list
    self.assertNotIn('buildout:networkcache-section=networkcache', command_list)
    self.assertNotIn('networkcache:signature-private-key-file=%s' %
                     self.signature_private_key_file,
                     command_list)
    self.assertNotIn('networkcache:upload-cache-url=%s' % self.upload_cache_url,
                     command_list)
    self.assertNotIn('networkcache:upload-dir-url=%s' % self.upload_dir_url,
                     command_list)

  # XXX-Cedric: do the same with upload
  def test_software_install_networkcache_upload_blacklist(self):
    """
      Check if the networkcache upload blacklist parameters are propagated.
    """
    def fakeBuildout(*args, **kw):
      pass

    Software._install_from_buildout = fakeBuildout

    def fake_upload_network_cached(*args, **kw):
      self.assertFalse(True)

    networkcache.upload_network_cached = fake_upload_network_cached

    upload_to_binary_cache_url_blacklist = ["http://example.com"]

    software = Software(
        url='http://example.com/software.cfg',
        software_root=self.software_root,
        buildout=self.buildout,
        logger=logging.getLogger(),
        signature_private_key_file='/signature/private/key_file',
        upload_cache_url='http://example.com/uploadcache',
        upload_dir_url='http://example.com/uploaddir',
        shacache_ca_file=self.shacache_ca_file,
        shacache_cert_file=self.shacache_cert_file,
        shacache_key_file=self.shacache_key_file,
        shadir_ca_file=self.shadir_ca_file,
        shadir_cert_file=self.shadir_cert_file,
        shadir_key_file=self.shadir_key_file,
        upload_to_binary_cache_url_blacklist=
            upload_to_binary_cache_url_blacklist,
    )
    software.install()

  def test_software_install_networkcache_upload_blacklist_side_effect(self):
    """
      Check if the networkcache upload blacklist parameters only prevent
      blacklisted Software Release to be uploaded.
    """
    def fakeBuildout(*args, **kw):
      pass
    Software._install_from_buildout = fakeBuildout

    def fakeUploadSoftwareRelease(*args, **kw):
      self.uploaded = True

    Software.uploadSoftwareRelease = fakeUploadSoftwareRelease

    upload_to_binary_cache_url_blacklist = ["http://anotherexample.com"]

    software = Software(
        url='http://example.com/software.cfg',
        software_root=self.software_root,
        buildout=self.buildout,
        logger=logging.getLogger(),
        signature_private_key_file='/signature/private/key_file',
        upload_cache_url='http://example.com/uploadcache',
        upload_dir_url='http://example.com/uploaddir',
        upload_binary_cache_url='http://example.com/uploadcache',
        upload_binary_dir_url='http://example.com/uploaddir',
        shacache_ca_file=self.shacache_ca_file,
        shacache_cert_file=self.shacache_cert_file,
        shacache_key_file=self.shacache_key_file,
        shadir_ca_file=self.shadir_ca_file,
        shadir_cert_file=self.shadir_cert_file,
        shadir_key_file=self.shadir_key_file,
        upload_to_binary_cache_url_blacklist=
            upload_to_binary_cache_url_blacklist,
    )
    software.install()
    self.assertTrue(getattr(self, 'uploaded', False))

class TestPartitionSlapObject(MasterMixin, unittest.TestCase):
  def setUp(self):
    MasterMixin.setUp(self)

    Partition.generateSupervisorConfigurationFile = FakeCallAndNoop()
    utils.bootstrapBuildout = FakeCallAndNoop()

    utils.launchBuildout = FakeCallAndStore()

  def tearDown(self):
    MasterMixin.tearDown(self)
    Partition.generateSupervisorConfigurationFile = originalPartitionGenerateSupervisorConfigurationFile

  def test_instance_is_deploying_if_software_release_exists(self):
    """
    Test that slapgrid deploys an instance if its Software Release exists and
    instance.cfg in the Software Release exists.
    """
    software = self.createSoftware()

    partition = self.createPartition(software.url)
    partition.install()

    self.assertTrue(utils.launchBuildout.called)

  def test_backward_compatibility_instance_is_deploying_if_template_cfg_is_used(self):
    """
    Backward compatibility test, for old software releases.
    Test that slapgrid deploys an instance if its Software Release exists and
    template.cfg in the Software Release exists.
    """

    software = self.createSoftware(empty=True)
    open(os.path.join(software.software_path, 'template.cfg'), 'w').close()

    partition = self.createPartition(software.url)
    partition.install()

    self.assertTrue(utils.launchBuildout.called)

  def test_instance_slapgrid_raise_if_software_release_instance_profile_does_not_exist(self):
    """
    Test that slapgrid raises XXX when deploying an instance if the Software Release
    related to the instance is not correctly installed (i.e there is no
    instance.cfg in it).
    """
    software = self.createSoftware(empty=True)

    partition = self.createPartition(software.url)

    # XXX: What should it raise?
    self.assertRaises(IOError, partition.install)

  def test_instance_slapgrid_raise_if_software_release_does_not_exist(self):
    """
    Test that slapgrid raises XXX when deploying an instance if the Software Release
    related to the instance is not present at all (i.e its directory does not
    exist at all).
    """
    software = self.createSoftware(empty=True)
    os.rmdir(software.software_path)

    partition = self.createPartition(software.url)

    # XXX: What should it raise?
    self.assertRaises(IOError, partition.install)

class TestPartitionSupervisorConfig(MasterMixin, unittest.TestCase):

  def setUp(self):
    MasterMixin.setUp(self)

    self.software = self.createSoftware()
    self.partition = self.createPartition(self.software.url)
    self.partition.generateSupervisorConfiguration()

    utils.bootstrapBuildout = FakeCallAndNoop()
    utils.launchBuildout = FakeCallAndNoop()

  def test_grouped_program(self):
    self.assertEqual(self.partition.supervisor_configuration_group, '')
    self.assertEqual(self.partition.partition_supervisor_configuration, '')

    partition_id = self.partition.partition_id

    group_id = self.partition.addCustomGroup('test', partition_id,
                                             ['sample-1'])

    self.assertIn('group:{}-test'.format(partition_id),
                  self.partition.supervisor_configuration_group)

    self.partition.addProgramToGroup(group_id, 'sample-1', 'sample-1',
                                     '/bin/ls')

    self.assertIn('program:{}-test_sample-1'.format(partition_id),
                  self.partition.partition_supervisor_configuration)

  def test_simple_service(self):
    self.assertEqual(self.partition.supervisor_configuration_group, '')
    self.assertEqual(self.partition.partition_supervisor_configuration, '')

    partition_id = self.partition.partition_id

    runners = ['runner-{}'.format(i) for i in range(3)]
    path = os.path.join(self.partition.instance_path, 'etc/run')
    self.partition.addServiceToGroup(partition_id, runners, path)

    for i in range(3):
      self.assertIn('program:{}_runner-{}'.format(partition_id, i),
                    self.partition.partition_supervisor_configuration)

      runner_path = os.path.join(self.partition.instance_path, 'etc/run',
                                 'runner-{}'.format(i))

class TestPartitionDestructionLock(MasterMixin, unittest.TestCase):
  def setUp(self):
    MasterMixin.setUp(self)
    Partition.generateSupervisorConfigurationFile = FakeCallAndNoop()
    utils.bootstrapBuildout = FakeCallAndNoop()
    utils.launchBuildout = FakeCallAndStore()

  def test_retention_lock_delay_creation(self):
    delay = 42
    software = self.createSoftware()
    partition = self.createPartition(software.url, retention_delay=delay)
    partition.install()
    deployed_delay = int(open(partition.retention_lock_delay_file_path).read())
    self.assertEqual(delay, deployed_delay)

  def test_no_retention_lock_delay(self):
    software = self.createSoftware()
    partition = self.createPartition(software.url)
    partition.install()
    delay = open(partition.retention_lock_delay_file_path).read()
    self.assertTrue(delay, '0')

    self.assertTrue(partition.destroy())

  def test_retention_lock_delay_does_not_change(self):
    delay = 42
    software = self.createSoftware()
    partition = self.createPartition(software.url, retention_delay=delay)
    partition.install()

    partition.retention_delay = 23
    # install/destroy many times
    partition.install()
    partition.destroy()
    partition.destroy()
    partition.install()
    partition.destroy()

    deployed_delay = int(open(partition.retention_lock_delay_file_path).read())
    self.assertEqual(delay, deployed_delay)

  def test_retention_lock_delay_is_respected(self):
    delay = 2.0 / (3600 * 24)
    software = self.createSoftware()
    partition = self.createPartition(software.url, retention_delay=delay)
    partition.install()

    deployed_delay = float(open(partition.retention_lock_delay_file_path).read())
    self.assertEqual(int(delay), int(deployed_delay))

    self.assertFalse(partition.destroy())
    time.sleep(1)
    self.assertFalse(partition.destroy())
    time.sleep(1)
    self.assertTrue(partition.destroy())

  def test_retention_lock_date_creation(self):
    delay = 42
    software = self.createSoftware()
    partition = self.createPartition(software.url, retention_delay=delay)
    partition.install()
    self.assertFalse(os.path.exists(partition.retention_lock_date_file_path))
    partition.destroy()
    deployed_date = float(open(partition.retention_lock_date_file_path).read())
    self.assertEqual(delay * 3600 * 24 + int(time.time()), int(deployed_date))

  def test_retention_lock_date_does_not_change(self):
    delay = 42
    software = self.createSoftware()
    partition = self.createPartition(software.url, retention_delay=delay)
    now = time.time()
    partition.install()
    partition.destroy()

    partition.retention_delay = 23
    # install/destroy many times
    partition.install()
    partition.destroy()
    partition.destroy()
    partition.install()
    partition.destroy()

    deployed_date = float(open(partition.retention_lock_date_file_path).read())
    self.assertEqual(delay * 3600 * 24 + int(now), int(deployed_date))
