from slapos.grid import SlapObject
from slapos.grid import utils
from slapos.tests.slapgrid import BasicMixin
import os
import unittest
import tempfile
import sys


class FakeCallAndRead:
  def __init__(self):
    self.external_command_dict = {}

  def __call__(self, *args, **kwargs):
    self.external_command_dict.update(kwargs)

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
    FakeCallAndRead.external_command_dict = {}

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

    additional_buildout_parameter = ' '.join(
        FakeCallAndRead.external_command_dict.\
            get('additional_buildout_parametr_list'))
    self.assertTrue('networkcache' in additional_buildout_parameter)
    self.assertTrue(self.upload_cache_url in additional_buildout_parameter)
    self.assertTrue(self.upload_dir_url in additional_buildout_parameter)
    self.assertTrue(self.signature_private_key_file in additional_buildout_parameter)

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

    additional_buildout_parameter = ' '.join(FakeCallAndRead.\
        external_command_dict.\
            get('additional_buildout_parametr_list'))
    self.assertFalse('networkcache' in additional_buildout_parameter)
    self.assertFalse(self.upload_cache_url in additional_buildout_parameter)
    self.assertFalse(self.upload_dir_url in additional_buildout_parameter)
    self.assertFalse(self.signature_private_key_file in additional_buildout_parameter)
