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
import unittest

from slapos.slap import ComputerPartition as SlapComputerPartition

from slapos.grid.SlapObject import Partition, Software
from slapos.grid import utils
from slapos.grid import networkcache
# XXX: BasicMixin should be in a separated module, not in slapgrid test module.
from slapos.tests.slapgrid import BasicMixin


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
    self.shacache_cert_file = '/path/to/shacache/cert/file'
    self.shacache_key_file = '/path/to/shacache/key/file'
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
        shacache_cert_file=self.shacache_cert_file,
        shacache_key_file=self.shacache_key_file,
        shadir_cert_file=self.shadir_cert_file,
        shadir_key_file=self.shadir_key_file)

    software.install()

    command_list = self.fakeCallAndRead.external_command_list
    self.assertIn('buildout:networkcache-section=networkcache', command_list)
    self.assertIn('networkcache:signature-private-key-file=%s' % self.signature_private_key_file, command_list)
    self.assertIn('networkcache:upload-cache-url=%s' % self.upload_cache_url, command_list)
    self.assertIn('networkcache:upload-dir-url=%s' % self.upload_dir_url, command_list)
    self.assertIn('networkcache:shacache-cert-file=%s' % self.shacache_cert_file, command_list)
    self.assertIn('networkcache:shacache-key-file=%s' % self.shacache_key_file, command_list)
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
        shacache_cert_file=self.shacache_cert_file,
        shacache_key_file=self.shacache_key_file,
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
        shacache_cert_file=self.shacache_cert_file,
        shacache_key_file=self.shacache_key_file,
        shadir_cert_file=self.shadir_cert_file,
        shadir_key_file=self.shadir_key_file,
        upload_to_binary_cache_url_blacklist=
            upload_to_binary_cache_url_blacklist,
    )
    software.install()
    self.assertTrue(getattr(self, 'uploaded', False))
