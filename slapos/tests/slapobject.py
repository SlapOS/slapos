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

from slapos.grid import SlapObject
from slapos.grid import utils
from slapos.tests.slapgrid import BasicMixin
import os
import unittest


class FakeCallAndRead:
  def __init__(self):
    self.external_command_list = []

  def __call__(self, *args, **kwargs):
    additional_buildout_parametr_list = \
        kwargs.get('additional_buildout_parametr_list')
    self.external_command_list.extend(additional_buildout_parametr_list)

FakeCallAndRead = FakeCallAndRead()
originalBootstrapBuildout = utils.bootstrapBuildout
originalLaunchBuildout = utils.launchBuildout

class TestSoftwareSlapObject(BasicMixin, unittest.TestCase):
  """
    Test for Software class.
  """

  def setUp(self):
    BasicMixin.setUp(self)
    os.mkdir(self.software_root)
    self.signature_private_key_file = '/signature/private/key_file'
    self.upload_cache_url = 'http://example.com/uploadcache'
    self.upload_dir_url = 'http://example.com/uploaddir'
    self.shacache_cert_file = '/path/to/shacache/cert/file'
    self.shacache_key_file = '/path/to/shacache/key/file'
    self.shadir_cert_file = '/path/to/shadir/cert/file'
    self.shadir_key_file = '/path/to/shadir/key/file'

    # Monkey patch utils module
    utils.bootstrapBuildout = FakeCallAndRead
    utils.launchBuildout = FakeCallAndRead

  def tearDown(self):
    global originalBootstrapBuildout
    global originalLaunchBuildout
    BasicMixin.tearDown(self)
    FakeCallAndRead.external_command_list = []

    # Un-monkey patch utils module
    utils.bootstrapBuildout = originalBootstrapBuildout
    utils.launchBuildout = originalLaunchBuildout

  # Test methods
  def test_software_install_with_networkcache(self):
    """
      Check if the networkcache parameters are propagated.
    """
    software = SlapObject.Software(
            url='http://example.com/software.cfg',
            software_root=self.software_root,
            console=False,
            buildout=self.buildout,
            signature_private_key_file='/signature/private/key_file',
            upload_cache_url='http://example.com/uploadcache',
            upload_dir_url='http://example.com/uploaddir',
            shacache_cert_file=self.shacache_cert_file,
            shacache_key_file=self.shacache_key_file,
            shadir_cert_file=self.shadir_cert_file,
            shadir_key_file=self.shadir_key_file)

    software.install()

    command_list = FakeCallAndRead.external_command_list
    self.assertTrue('buildout:networkcache-section=networkcache'
                    in command_list)
    self.assertTrue('networkcache:signature-private-key-file=%s' %
                    self.signature_private_key_file in command_list)
    self.assertTrue('networkcache:upload-cache-url=%s' % self.upload_cache_url
                    in command_list)
    self.assertTrue('networkcache:upload-dir-url=%s' % self.upload_dir_url
                    in command_list)
    self.assertTrue('networkcache:shacache-cert-file=%s' % self.shacache_cert_file
                    in command_list)
    self.assertTrue('networkcache:shacache-key-file=%s' % self.shacache_key_file
                    in command_list)
    self.assertTrue('networkcache:shadir-cert-file=%s' % self.shadir_cert_file
                    in command_list)
    self.assertTrue('networkcache:shadir-key-file=%s' % self.shadir_key_file
                    in command_list)

  def test_software_install_without_networkcache(self):
    """
      Check if the networkcache parameters are not propagated if they are not
      available.
    """
    software = SlapObject.Software(
            url='http://example.com/software.cfg',
            software_root=self.software_root,
            console=False,
            buildout=self.buildout)

    software.install()

    command_list = FakeCallAndRead.external_command_list
    self.assertFalse('buildout:networkcache-section=networkcache'
                    in command_list)
    self.assertFalse('networkcache:signature-private-key-file=%s' %
                    self.signature_private_key_file in command_list)
    self.assertFalse('networkcache:upload-cache-url=%s' % self.upload_cache_url
                    in command_list)
    self.assertFalse('networkcache:upload-dir-url=%s' % self.upload_dir_url
                    in command_list)
