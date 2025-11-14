import os
import shutil
import tempfile
import time
import unittest

from slapos.test.utils import makeRecipe

try:
  # BBB python2
  import subprocess32 as subprocess
except ImportError:
  import subprocess


class TestCertificateAuthority(unittest.TestCase):

  def setUp(self):
    self.ca_dir = tempfile.mkdtemp()
    self.ca_private_dir = os.path.join(self.ca_dir, 'private')
    os.mkdir(self.ca_private_dir)
    self.ca_newcerts_dir = os.path.join(self.ca_dir, 'newcerts')
    os.mkdir(self.ca_newcerts_dir)
    self.ca_certs_dir = os.path.join(self.ca_dir, 'certs')
    os.mkdir(self.ca_certs_dir)

    self.addCleanup(shutil.rmtree, self.ca_dir)
    self.requests_directory = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.requests_directory)
    self.cert_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.cert_dir)

    self.services_directory = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.services_directory)

    self.wrapper = os.path.join(self.services_directory, self.id())

    from slapos.recipe import certificate_authority
    self.recipe = makeRecipe(
      certificate_authority.Recipe,
      options={
        'ca-dir': self.ca_dir,
        'ca-private': self.ca_private_dir,
        'ca-certs': self.ca_certs_dir,
        'ca-newcerts': self.ca_newcerts_dir,
        'wrapper': self.wrapper,
        'requests-directory': self.requests_directory,
        'openssl-binary': 'openssl',
      },
      name=self.id(),
    )

  def start_certificate_authority_service(self):
    service_process = subprocess.Popen(
      [ self.wrapper ],
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      universal_newlines=True,
    )
    self.addCleanup(service_process.wait)
    self.addCleanup(service_process.terminate)
    return service_process

  def check_no_output_and_terminate(self, service_process):
    service_process.terminate()
    service_process.wait()
    _, stderr = service_process.communicate(timeout=5)
    self.assertFalse(stderr)

  def test_install(self):
    installed = self.recipe.install()
    self.assertEqual(installed, self.wrapper)

    # service creates its CA
    service_process = self.start_certificate_authority_service()
    for i in range(10):
      time.sleep(i)
      if 'cakey.pem' in os.listdir(self.ca_private_dir):
        break
    else:
      self.check_no_output_and_terminate(service_process)
    self.assertIn('cacert.pem', os.listdir(self.ca_dir))
    self.check_no_output_and_terminate(service_process)

    # service processes certificate requests
    with open(os.path.join(self.requests_directory, self.id()), 'w') as f:
      f.write('''
[certificate]
name = test
key_file = %s/key
certificate_file = %s/cert
''' % (self.cert_dir, self.cert_dir,))
    service_process = self.start_certificate_authority_service()
    for i in range(10):
      time.sleep(i)
      if 'key' in os.listdir(self.cert_dir):
        break
    else:
      self.check_no_output_and_terminate(service_process)

    with open(os.path.join(self.cert_dir, 'cert')) as f:
      self.assertIn('BEGIN CERTIFICATE', f.read())
    self.check_no_output_and_terminate(service_process)
