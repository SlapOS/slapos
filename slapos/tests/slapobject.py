from slapos.grid import SlapObject
from slapos.grid import utils
from slapos.tests.slapgrid import BasicMixin
import os
import unittest
import tempfile
import sys

def mockBootstrapBuildout(*args, **kwargs):
  print args, kwargs
utils.bootstrapBuildout = mockBootstrapBuildout

def mockLaunchBuildout(*args, **kwargs):
  print args, kwargs
utils.launchBuildout = mockLaunchBuildout

class TestSoftwareSlapObject(BasicMixin, unittest.TestCase):
  """
    Test for Software class.
  """

  def setUp(self):
    BasicMixin.setUp(self)
    os.mkdir(self.software_root)
    self.output_file = tempfile.NamedTemporaryFile()
    self.stdout = sys.stdout
    self.signature_private_key_file = '/signature/private/key_file'
    self.upload_cache_url = 'http://example.com/uploadcache'
    self.upload_dir_url = 'http://example.com/uploaddir'

  def tearDown(self):
    BasicMixin.tearDown(self)
    self.output_file.close()

  # Utils methods
  def _printToFile(self):
    self.output_file.seek(0)
    sys.stdout = self.output_file

  def _printToScreen(self):
    self.output_file.seek(0)
    sys.stdout = self.stdout

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

    self._printToFile()
    software.install()
    self._printToScreen()

    content = self.output_file.read()
    self.assertTrue('networkcache' in content)
    self.assertTrue(self.upload_cache_url in content)
    self.assertTrue(self.upload_dir_url in content)
    self.assertTrue(self.signature_private_key_file in content)

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

    self._printToFile()
    software.install()
    self._printToScreen()

    content = self.output_file.read()
    self.assertFalse('networkcache' in content)
    self.assertFalse(self.upload_cache_url in content)
    self.assertFalse(self.upload_dir_url in content)
    self.assertFalse(self.signature_private_key_file in content)
