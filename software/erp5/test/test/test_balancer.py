from . import ERP5InstanceTestCase
from . import setUpModule
from slapos.testing.utils import findFreeTCPPort

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID
import json
import os
import shutil
import subprocess
import tempfile
import time

class TestFrontendXForwardedFor(ERP5InstanceTestCase):

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'balancer'

  @classmethod
  def setUpClass(cls):
    cls.computer_partition_root_path = os.path.abspath(os.curdir)
    cls._caucase_dir = tempfile.mkdtemp()
    _caucase_caucased_dir = os.path.join(cls._caucase_dir, 'caucased')
    os.mkdir(_caucase_caucased_dir)
    _caucase_user_dir = os.path.join(cls._caucase_dir, 'user')
    os.mkdir(_caucase_user_dir)
    _caucase_service_dir = os.path.join(cls._caucase_dir, 'service')
    os.mkdir(_caucase_service_dir)
    cls._caucase_caucased_netloc = '%s:%s' % (cls._ipv4_address, findFreeTCPPort(cls._ipv4_address))

    _caucase_user_key = os.path.join(_caucase_user_dir, 'client.key.pem')
    _caucase_user_csr = os.path.join(_caucase_user_dir, 'client.csr.pem')

    key = rsa.generate_private_key(
      public_exponent=65537,
      key_size=2048,
      backend=default_backend()
    )
    with open(_caucase_user_key, 'wb') as f:
      f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
      ))

    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
      x509.NameAttribute(NameOID.COMMON_NAME, u'user'),
    ])).sign(key, hashes.SHA256(), default_backend())
    with open(_caucase_user_csr, 'wb') as f:
      f.write(csr.public_bytes(serialization.Encoding.PEM))

    cls._caucase_caucased_proc = subprocess.Popen(
      [
        os.path.join(cls.computer_partition_root_path, 'software_release', 'bin', 'caucased'),
        '--db', os.path.join(_caucase_caucased_dir, 'caucase.sqlite'),
        '--server-key', os.path.join(_caucase_caucased_dir, 'server.key.pem'),
        '--netloc', cls._caucase_caucased_netloc,
      ],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
    )
    time.sleep(3) # XXX how to check if caucased service is ready ?

    cau_args = [
      os.path.join(cls.computer_partition_root_path, 'software_release', 'bin', 'caucase'),
      '--ca-url', 'http://' + cls._caucase_caucased_netloc,
      '--ca-crt', os.path.join(_caucase_user_dir, 'service-ca-crt.pem'),
      '--crl', os.path.join(_caucase_user_dir, 'service.crl'),
      '--user-ca-crt', os.path.join(_caucase_user_dir, 'user-ca-crt.pem'),
      '--user-crl', os.path.join(_caucase_user_dir, 'user.crl'),
    ]

    cas_args = [
      os.path.join(cls.computer_partition_root_path, 'software_release', 'bin', 'caucase'),
      '--ca-url', 'http://' + cls._caucase_caucased_netloc,
      '--ca-crt', os.path.join(_caucase_service_dir, 'service-ca-crt.pem'),
      '--crl', os.path.join(_caucase_service_dir, 'service.crl'),
      '--user-ca-crt', os.path.join(_caucase_service_dir, 'user-ca-crt.pem'),
      '--user-crl', os.path.join(_caucase_service_dir, 'user.crl'),
    ]

    proc = subprocess.Popen(
      cau_args + [
        '--mode', 'user',
        '--send-csr', _caucase_user_csr,
      ],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
    )
    result = proc.communicate()
    print result
    csr_id = result[0].split()[0]

    proc = subprocess.Popen(
      cau_args + [
        '--mode', 'user',
        '--get-crt', csr_id, _caucase_user_key,
      ],
    )

    _caucase_service_key = os.path.join(_caucase_service_dir, 'crt.pem')
    _caucase_service_csr = os.path.join(_caucase_service_dir, 'csr.pem')

    key = rsa.generate_private_key(
      public_exponent=65537,
      key_size=2048,
      backend=default_backend()
    )
    with open(_caucase_service_key, 'wb') as f:
      f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
      ))

    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
      x509.NameAttribute(NameOID.COMMON_NAME, u'service'),
    ])).sign(key, hashes.SHA256(), default_backend())
    with open(_caucase_service_csr, 'wb') as f:
      f.write(csr.public_bytes(serialization.Encoding.PEM))

    proc = subprocess.Popen(
      cas_args + [
        '--send-csr', _caucase_service_csr,
      ],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
    )
    result = proc.communicate()
    csr_id = result[0].split()[0]

    proc = subprocess.Popen(
      cau_args + [
        '--user-key', _caucase_user_key,
        '--sign-csr', csr_id,
      ],
    )
    time.sleep(3) # XXX should retry until the cert is ready

    proc = subprocess.Popen(
      cas_args + [
        '--get-crt', csr_id, _caucase_service_key,
      ],
    )

    super(TestFrontendXForwardedFor, cls).setUpClass()

  @classmethod
  def getInstanceParameterDict(cls):
    # start a dummy web server echoing headers, like the one from caddy-frontend tests.
    # see software/caddy-frontend/test/test.py
    url = startDummyWebServer()

    return {
        '_': json.dumps({
          'url': url,  
          'ssl': {'frontend-caucase-url-list': ['http://' + cls._caucase_caucased_netloc]},
        })
    }

  @classmethod
  def tearDownClass(cls):
    if cls._caucase_caucased_proc:
      cls._caucase_caucased_proc.terminate()
    if cls._caucase_dir:
      shutil.rmtree(cls._caucase_dir)

    super(TestFrontendXForwardedFor, cls).tearDownClass()

  def test_x_forwarded_for_added_when_verified_connection(self):
    # connect through frontend, check there's a X-Forwarded-For header
    pass

  def test_x_forwarded_for_stripped_when_not_verified_connection(self):
    # connect directly to backend without authentication, with a X-Forwarded-For header, check it is X-Forwarded-For for is stripped
    pass
