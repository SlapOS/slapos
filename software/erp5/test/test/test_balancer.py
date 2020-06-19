from . import ERP5InstanceTestCase
from . import setUpModule
from slapos.testing.utils import findFreeTCPPort

from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler
import OpenSSL.SSL
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID
import hashlib
import json
import multiprocessing
import os
import requests
import shutil
import subprocess
import tempfile
import time

setUpModule  # pyflakes

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
  __partition_reference__ = 'xff'
  http_server_process = None
  frontend_caucase_dir = None
  frontend_caucased_process = None
  backend_caucase_dir = None
  backend_caucased_process = None

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
    cls.http_server_process.start()
    cls.http_server_netloc = '%s:%s' % (cls._ipv4_address, http_server_port)

    # start a caucased and generate a valid client certificate.
    cls.computer_partition_root_path = os.path.abspath(os.curdir)
    cls.frontend_caucase_dir = tempfile.mkdtemp()
    frontend_caucased_dir = os.path.join(cls.frontend_caucase_dir, 'caucased')
    os.mkdir(frontend_caucased_dir)
    frontend_user_dir = os.path.join(cls.frontend_caucase_dir, 'user')
    os.mkdir(frontend_user_dir)
    frontend_service_dir = os.path.join(cls.frontend_caucase_dir, 'service')
    os.mkdir(frontend_service_dir)
    frontend_caucased_netloc = '%s:%s' % (cls._ipv4_address, findFreeTCPPort(cls._ipv4_address))
    cls.frontend_caucased_url = 'http://' + frontend_caucased_netloc

    cls.user_certificate = frontend_user_key = os.path.join(frontend_user_dir, 'client.key.pem')
    frontend_user_csr = os.path.join(frontend_user_dir, 'client.csr.pem')

    key = rsa.generate_private_key(
      public_exponent=65537,
      key_size=2048,
      backend=default_backend()
    )
    with open(frontend_user_key, 'wb') as f:
      f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
      ))

    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
      x509.NameAttribute(NameOID.COMMON_NAME, u'user'),
    ])).sign(key, hashes.SHA256(), default_backend())
    with open(frontend_user_csr, 'wb') as f:
      f.write(csr.public_bytes(serialization.Encoding.PEM))

    cls.software_release_root_path = os.path.join(
       cls.slap._software_root,
       hashlib.md5(cls.getSoftwareURL()).hexdigest(),
    )
    caucased_path = os.path.join(cls.software_release_root_path, 'bin', 'caucased')
    caucase_path = os.path.join(cls.software_release_root_path, 'bin', 'caucase')
    cls.frontend_caucased_process = subprocess.Popen(
      [
        caucased_path,
        '--db', os.path.join(frontend_caucased_dir, 'caucase.sqlite'),
        '--server-key', os.path.join(frontend_caucased_dir, 'server.key.pem'),
        '--netloc', frontend_caucased_netloc,
        '--service-auto-approve-count', '1',
      ],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
    )
    for _ in range(10):
      try:
        if requests.get(cls.frontend_caucased_url).status_code == 200:
          break
      except Exception:
        pass
      time.sleep(1)
    else:
      raise RuntimeError, 'caucased failed to start.'

    cau_args = [
      caucase_path,
      '--ca-url', cls.frontend_caucased_url,
      '--ca-crt', os.path.join(frontend_user_dir, 'service-ca-crt.pem'),
      '--crl', os.path.join(frontend_user_dir, 'service.crl'),
      '--user-ca-crt', os.path.join(frontend_user_dir, 'user-ca-crt.pem'),
      '--user-crl', os.path.join(frontend_user_dir, 'user.crl'),
    ]

    cas_args = [
      caucase_path,
      '--ca-url', cls.frontend_caucased_url,
      '--ca-crt', os.path.join(frontend_service_dir, 'service-ca-crt.pem'),
      '--crl', os.path.join(frontend_service_dir, 'service.crl'),
      '--user-ca-crt', os.path.join(frontend_service_dir, 'user-ca-crt.pem'),
      '--user-crl', os.path.join(frontend_service_dir, 'user.crl'),
    ]

    caucase_process = subprocess.Popen(
      cau_args + [
        '--mode', 'user',
        '--send-csr', frontend_user_csr,
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
        '--get-crt', csr_id, frontend_user_key,
      ],
    )

    cls.client_certificate = frontend_service_key = os.path.join(frontend_service_dir, 'crt.pem')
    frontend_service_csr = os.path.join(frontend_service_dir, 'csr.pem')

    key = rsa.generate_private_key(
      public_exponent=65537,
      key_size=2048,
      backend=default_backend()
    )
    with open(frontend_service_key, 'wb') as f:
      f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
      ))

    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
      x509.NameAttribute(NameOID.COMMON_NAME, u'service'),
    ])).sign(key, hashes.SHA256(), default_backend())
    with open(frontend_service_csr, 'wb') as f:
      f.write(csr.public_bytes(serialization.Encoding.PEM))

    caucase_process = subprocess.Popen(
      cas_args + [
        '--send-csr', frontend_service_csr,
      ],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
    )
    result = caucase_process.communicate()
    csr_id = result[0].split()[0]

    for _ in range(10):
      if not subprocess.call(
        cas_args + [
          '--get-crt', csr_id, frontend_service_key,
        ],
      ) == 0:
        break
      else:
        time.sleep(1)
    else:
      raise RuntimeError, 'getting service certificate failed.'

    # start a caucased and server certificate.
    cls.backend_caucase_dir = tempfile.mkdtemp()
    backend_caucased_dir = os.path.join(cls.backend_caucase_dir, 'caucased')
    os.mkdir(backend_caucased_dir)
    backend_caucased_netloc = '%s:%s' % (cls._ipv4_address, findFreeTCPPort(cls._ipv4_address))
    cls.backend_caucased_url = 'http://' + backend_caucased_netloc
    cls.backend_caucased_process = subprocess.Popen(
      [
        caucased_path,
        '--db', os.path.join(backend_caucased_dir, 'caucase.sqlite'),
        '--server-key', os.path.join(backend_caucased_dir, 'server.key.pem'),
        '--netloc', backend_caucased_netloc,
        '--service-auto-approve-count', '1',
      ],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
    )
    for _ in range(10):
      try:
        if requests.get(cls.backend_caucased_url).status_code == 200:
          break
      except Exception:
        pass
      time.sleep(1)
    else:
      raise RuntimeError, 'caucased failed to start.'

    super(TestFrontendXForwardedFor, cls).setUpClass()

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      '_': json.dumps({
        'tcpv4-port': 3306,
        'computer-memory-percent-threshold': 100,
        # XXX what is this ? should probably not be needed here
        'name': cls.__name__,
        'monitor-passwd': 'secret',
        'apachedex-configuration': '',
        'apachedex-promise-threshold': 100,
        'haproxy-server-check-path': '/',
        'zope-family-dict': {
          'default': ['dummy_http_server'],
          'default-auth': ['dummy_http_server'],
        },
        'dummy_http_server': [[cls.http_server_netloc, 1, False]],
        'backend-path-dict': {
          'default': '/',
          'default-auth': '/',
        },
        'ssl-authentication-dict': {
          'default': False,
          'default-auth': True,
        },
        'ssl': {
          'caucase-url': cls.backend_caucased_url,
          'frontend-caucase-url-list': [cls.frontend_caucased_url],
        },
      })
    }

  @classmethod
  def _cleanup(cls, snapshot_name):
    if cls.http_server_process:
      cls.http_server_process.terminate()
    if cls.frontend_caucased_process:
      cls.frontend_caucased_process.terminate()
    if cls.frontend_caucase_dir:
      shutil.rmtree(cls.frontend_caucase_dir)
    if cls.backend_caucased_process:
      cls.backend_caucased_process.terminate()
    if cls.backend_caucase_dir:
      shutil.rmtree(cls.backend_caucase_dir)

    super(TestFrontendXForwardedFor, cls)._cleanup(snapshot_name)

  def test_x_forwarded_for_added_when_verified_connection(self):
    for backend in ('default', 'default-auth'):
      balancer_url = json.loads(self.computer_partition.getConnectionParameterDict()['_'])[backend]
      result = requests.get(
        balancer_url,
        headers={'X-Forwarded-For': '1.2.3.4'},
        cert=self.client_certificate,
        verify=False,
      ).json()
      self.assertEqual(result['Incoming Headers'].get('x-forwarded-for').split(', ')[0], '1.2.3.4')

  def test_x_forwarded_for_stripped_when_not_verified_connection(self):
    balancer_url = json.loads(self.computer_partition.getConnectionParameterDict()['_'])['default']
    result = requests.get(
      balancer_url,
      headers={'X-Forwarded-For': '1.2.3.4'},
      verify=False,
    ).json()
    self.assertNotEqual(result['Incoming Headers'].get('x-forwarded-for').split(', ')[0], '1.2.3.4')
    balancer_url = json.loads(self.computer_partition.getConnectionParameterDict()['_'])['default-auth']
    with self.assertRaises(OpenSSL.SSL.Error):
      requests.get(
        balancer_url,
        headers={'X-Forwarded-For': '1.2.3.4'},
        verify=False,
      )
