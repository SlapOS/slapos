from . import ERP5InstanceTestCase
from . import setUpModule
from slapos.testing.utils import findFreeTCPPort

from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID
import json
import multiprocessing
import os
import requests
import shutil
import subprocess
import tempfile
import time

class TestHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    response = {
      'Path': self.path,
      'Incoming Headers': self.headers.dict
    }
    response = json.dumps(response, indent=2)
    self.end_headers()
    self.wfile.write(response)

class TestFrontendXForwardedFor(ERP5InstanceTestCase):
  http_server_process = None
  caucase_dir = None
  caucase_caucased_process = None

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'balancer'

  @classmethod
  def setUpClass(cls):
    # start a dummy web server echoing headers.
    http_server_port = findFreeTCPPort(cls._ipv4_address)
    server = HTTPServer(
      (cls._ipv4_address, http_server_port),
      TestHandler)
    cls.http_server_process = multiprocessing.Process(
      target=server.serve_forever, name='HTTPServer')
    cls.http_server_url = 'http://%s:%s/' % (cls._ipv4_address, http_server_port)

    # start a caucased and generate a valid client certificate.
    cls.computer_partition_root_path = os.path.abspath(os.curdir)
    cls.caucase_dir = tempfile.mkdtemp()
    _caucase_caucased_dir = os.path.join(cls.caucase_dir, 'caucased')
    os.mkdir(_caucase_caucased_dir)
    _caucase_user_dir = os.path.join(cls.caucase_dir, 'user')
    os.mkdir(_caucase_user_dir)
    _caucase_service_dir = os.path.join(cls.caucase_dir, 'service')
    os.mkdir(_caucase_service_dir)
    _caucase_caucased_netloc = '%s:%s' % (cls._ipv4_address, findFreeTCPPort(cls._ipv4_address))
    cls.caucase_caucased_url = 'http://' + _caucase_caucased_netloc

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

    cls.caucase_caucased_process = subprocess.Popen(
      [
        os.path.join(cls.computer_partition_root_path, 'software_release', 'bin', 'caucased'),
        '--db', os.path.join(_caucase_caucased_dir, 'caucase.sqlite'),
        '--server-key', os.path.join(_caucase_caucased_dir, 'server.key.pem'),
        '--netloc', _caucase_caucased_netloc,
      ],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
    )
    time.sleep(3) # XXX how to check if caucased service is ready ?

    cau_args = [
      os.path.join(cls.computer_partition_root_path, 'software_release', 'bin', 'caucase'),
      '--ca-url', cls.caucase_caucased_url,
      '--ca-crt', os.path.join(_caucase_user_dir, 'service-ca-crt.pem'),
      '--crl', os.path.join(_caucase_user_dir, 'service.crl'),
      '--user-ca-crt', os.path.join(_caucase_user_dir, 'user-ca-crt.pem'),
      '--user-crl', os.path.join(_caucase_user_dir, 'user.crl'),
    ]

    cas_args = [
      os.path.join(cls.computer_partition_root_path, 'software_release', 'bin', 'caucase'),
      '--ca-url', cls.caucase_caucased_url,
      '--ca-crt', os.path.join(_caucase_service_dir, 'service-ca-crt.pem'),
      '--crl', os.path.join(_caucase_service_dir, 'service.crl'),
      '--user-ca-crt', os.path.join(_caucase_service_dir, 'user-ca-crt.pem'),
      '--user-crl', os.path.join(_caucase_service_dir, 'user.crl'),
    ]

    caucase_process = subprocess.Popen(
      cau_args + [
        '--mode', 'user',
        '--send-csr', _caucase_user_csr,
      ],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
    )
    result = caucase_process.communicate()
    print result
    csr_id = result[0].split()[0]

    subprocess.check_call(
      cau_args + [
        '--mode', 'user',
        '--get-crt', csr_id, _caucase_user_key,
      ],
    )

    cls.client_cerfiticate = _caucase_service_key = os.path.join(_caucase_service_dir, 'crt.pem')
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

    caucase_process = subprocess.Popen(
      cas_args + [
        '--send-csr', _caucase_service_csr,
      ],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
    )
    result = caucase_process.communicate()
    csr_id = result[0].split()[0]

    subprocess.check_call(
      cau_args + [
        '--user-key', _caucase_user_key,
        '--sign-csr', csr_id,
      ],
    )
    time.sleep(3) # XXX should retry until the cert is ready

    subprocess.check_call(
      cas_args + [
        '--get-crt', csr_id, _caucase_service_key,
      ],
    )

    super(TestFrontendXForwardedFor, cls).setUpClass()

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      '_': json.dumps({
        'zope-family-dict': {'default': ['dummy_http_server']},
        'dummy_http_server': [[cls.http_server_url, 1, False]],
        'backend-path-dict': {'default': '/'},
        'ssl': {
          'frontend-caucase-url-list': [cls.caucase_caucased_url],
        },
      })
    }

  @classmethod
  def tearDownClass(cls):
    if cls.http_server_process:
      cls.http_server_process.terminate()
    if cls.caucase_caucased_process:
      cls.caucase_caucased_process.terminate()
    if cls.caucase_dir:
      shutil.rmtree(cls.caucase_dir)

    super(TestFrontendXForwardedFor, cls).tearDownClass()

  def test_x_forwarded_for_added_when_verified_connection(self):
    balancer_url = json.loads(self.computer_partition.getConnectionParameterDict()['_'])['default']
    result = requests.get(
      balancer_url,
      headers={'X-Forwarded-For': '1.2.3.4'},
      cert=self.client_certificate,
    ).json()
    self.assertEqual(result['Incoming Headers'].get('x-forwarded-for'), '1.2.3.4')

  def test_x_forwarded_for_stripped_when_not_verified_connection(self):
    balancer_url = json.loads(self.computer_partition.getConnectionParameterDict()['_'])['default']
    result = requests.get(
      balancer_url,
      headers={'X-Forwarded-For': '1.2.3.4'},
      cert=self.client_certificate,
    ).json()
    self.assertNotEqual(result['Incoming Headers'].get('x-forwarded-for'), '1.2.3.4')
