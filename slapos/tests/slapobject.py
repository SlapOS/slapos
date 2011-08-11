from slapos.grid import SlapObject
from slapos.grid import utils
from slapos.tests.slapgrid import BasicMixin
import os
import unittest
import tempfile
import sys


class FakeCallAndRead:
  def __init__(self):
    self.external_command_list = []

  def __call__(self, *args, **kwargs):
    additional_buildout_parametr_list = \
        kwargs.get('additional_buildout_parametr_list')
    self.external_command_list.extend(additional_buildout_parametr_list)

FakeCallAndRead = FakeCallAndRead()
utils.bootstrapBuildout = FakeCallAndRead
utils.launchBuildout = FakeCallAndRead

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

  def tearDown(self):
    BasicMixin.tearDown(self)
    FakeCallAndRead.external_command_list = []

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
            upload_dir_url='http://example.com/uploaddir')

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
