import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from BaseHTTPServer import BaseHTTPRequestHandler
from typing import Dict

import mock
import OpenSSL.SSL
import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from slapos.testing.testcase import ManagedResource
from slapos.testing.utils import (CrontabMixin, ManagedHTTPServer,
                                  findFreeTCPPort)

from . import ERP5InstanceTestCase, setUpModule

setUpModule  # pyflakes


class EchoHTTPServer(ManagedHTTPServer):
  """An HTTP Server responding with the request path and incoming headers,
  encoded in json.
  """
  class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
      # type: () -> None
      self.send_response(200)
      self.send_header("Content-Type", "application/json")
      response = json.dumps(
          {
              'Path': self.path,
              'Incoming Headers': self.headers.dict
          },
          indent=2,
      )
      self.end_headers()
      self.wfile.write(response)

    log_message = logging.getLogger(__name__ + '.HeaderEchoHandler').info


class CaucaseService(ManagedResource):
  """A caucase service.
  """
  url = None # type: str
  directory = None # type: str
  _caucased_process = None # type: subprocess.Popen

  def open(self):
    # type: () -> None
    # start a caucased and server certificate.
    software_release_root_path = os.path.join(
        self._cls.slap._software_root,
        hashlib.md5(self._cls.getSoftwareURL().encode()).hexdigest(),
    )
    caucased_path = os.path.join(software_release_root_path, 'bin', 'caucased')

    self.directory = tempfile.mkdtemp()
    caucased_dir = os.path.join(self.directory, 'caucased')
    os.mkdir(caucased_dir)
    os.mkdir(os.path.join(caucased_dir, 'user'))
    os.mkdir(os.path.join(caucased_dir, 'service'))

    backend_caucased_netloc = '%s:%s' % (self._cls._ipv4_address, findFreeTCPPort(self._cls._ipv4_address))
    self.url = 'http://' + backend_caucased_netloc
    self._caucased_process = subprocess.Popen(
        [
            caucased_path,
            '--db', os.path.join(caucased_dir, 'caucase.sqlite'),
            '--server-key', os.path.join(caucased_dir, 'server.key.pem'),
            '--netloc', backend_caucased_netloc,
            '--service-auto-approve-count', '1',
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    for _ in range(30):
      try:
        if requests.get(self.url).status_code == 200:
          break
      except Exception:
        pass
      time.sleep(1)
    else:
      raise RuntimeError('caucased failed to start.')

  def close(self):
    # type: () -> None
    self._caucased_process.terminate()
    self._caucased_process.wait()
    shutil.rmtree(self.directory)


class BalancerTestCase(ERP5InstanceTestCase):

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'balancer'

  @classmethod
  def _getInstanceParameterDict(cls):
    # type: () -> Dict
    return {
        'tcpv4-port': 8000,
        'computer-memory-percent-threshold': 100,
        # XXX what is this ? should probably not be needed here
        'name': cls.__name__,
        'monitor-passwd': 'secret',
        'apachedex-configuration': '--erp5-base +erp5 .*/VirtualHostRoot/erp5(/|\\?|$) --base +other / --skip-user-agent Zabbix --error-detail --js-embed --quiet',
        'apachedex-promise-threshold': 100,
        'haproxy-server-check-path': '/',
        'zope-family-dict': {
            'default': ['dummy_http_server'],
        },
        'dummy_http_server': [[cls.getManagedResource("backend_web_server", EchoHTTPServer).netloc, 1, False]],
        'backend-path-dict': {
            'default': '',
        },
        'ssl-authentication-dict': {},
        'ssl': {
            'caucase-url': cls.getManagedResource("caucase", CaucaseService).url,
        }
      }

  @classmethod
  def getInstanceParameterDict(cls):
    # type: () -> Dict
    return {'_': json.dumps(cls._getInstanceParameterDict())}

  def setUp(self):
    self.default_balancer_url = json.loads(
        self.computer_partition.getConnectionParameterDict()['_'])['default']


class CaucaseClientCertificate(ManagedResource):
  """A client certificate issued by a caucase services.
  """

  ca_crt_file = None # type: str
  crl_file = None # type: str
  csr_file = None # type: str
  cert_file = None # type: str
  key_file = None # type: str

  def open(self):
    # type: () -> None
    self.tmpdir = tempfile.mkdtemp()
    self.ca_crt_file = os.path.join(self.tmpdir, 'ca-crt.pem')
    self.crl_file = os.path.join(self.tmpdir, 'ca-crl.pem')
    self.csr_file = os.path.join(self.tmpdir, 'csr.pem')
    self.cert_file = os.path.join(self.tmpdir, 'crt.pem')
    self.key_file = os.path.join(self.tmpdir, 'key.pem')

  def close(self):
    # type: () -> None
    shutil.rmtree(self.tmpdir)

  def request(self, common_name, caucase):
    # type: (str, CaucaseService) -> None
    """Generate certificate and request signature to the caucase service.

    This overwrite any previously requested certificate for this instance.
    """
    software_release_root_path = os.path.join(
        self._cls.slap._software_root,
        hashlib.md5(self._cls.getSoftwareURL().encode()).hexdigest(),
    )
    caucase_path = os.path.join(software_release_root_path, 'bin', 'caucase')

    cas_args = [
        caucase_path,
        '--ca-url', caucase.url,
        '--ca-crt', self.ca_crt_file,
        '--crl', self.crl_file,
    ]

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    with open(self.key_file, 'wb') as f:
      f.write(
          key.private_bytes(
              encoding=serialization.Encoding.PEM,
              format=serialization.PrivateFormat.TraditionalOpenSSL,
              encryption_algorithm=serialization.NoEncryption(),
          ))

    csr = x509.CertificateSigningRequestBuilder().subject_name(
        x509.Name([
            x509.NameAttribute(
                NameOID.COMMON_NAME,
                common_name,
            ),
        ])).sign(
            key,
            hashes.SHA256(),
            default_backend(),
        )
    with open(self.csr_file, 'wb') as f:
      f.write(csr.public_bytes(serialization.Encoding.PEM))

    csr_id = subprocess.check_output(
      cas_args + [
          '--send-csr', self.csr_file,
      ],
    ).split()[0]
    assert csr_id

    for _ in range(30):
      if not subprocess.call(
        cas_args + [
            '--get-crt', csr_id, self.cert_file,
        ],
      ) == 0:
        break
      else:
        time.sleep(1)
    else:
      raise RuntimeError('getting service certificate failed.')
    with open(self.cert_file) as f:
      assert 'BEGIN CERTIFICATE' in f.read()


class TestFrontendXForwardedFor(BalancerTestCase):
  __partition_reference__ = 'xff'

  @classmethod
  def _getInstanceParameterDict(cls):
    # type: () -> Dict
    frontend_caucase = cls.getManagedResource('frontend_caucase', CaucaseService)
    certificate = cls.getManagedResource('client_certificate', CaucaseClientCertificate)
    certificate.request(u'shared frontend', frontend_caucase)

    parameter_dict = super(TestFrontendXForwardedFor, cls)._getInstanceParameterDict()
    # add another "-auth" backend, that will have ssl-authentication enabled
    parameter_dict['zope-family-dict']['default-auth'] = ['dummy_http_server']
    parameter_dict['backend-path-dict']['default-auth'] = '/'
    parameter_dict['ssl-authentication-dict'] = {
        'default': False,
        'default-auth': True,
    }
    parameter_dict['ssl']['frontend-caucase-url-list'] = [frontend_caucase.url]
    return parameter_dict

  def test_x_forwarded_for_added_when_verified_connection(self):
    # type: () -> None
    client_certificate = self.getManagedResource('client_certificate', CaucaseClientCertificate)

    for backend in ('default', 'default-auth'):
      balancer_url = json.loads(self.computer_partition.getConnectionParameterDict()['_'])[backend]
      result = requests.get(
        balancer_url,
        headers={'X-Forwarded-For': '1.2.3.4'},
        cert=(client_certificate.cert_file, client_certificate.key_file),
        verify=False,
      ).json()
      self.assertEqual(result['Incoming Headers'].get('x-forwarded-for').split(', ')[0], '1.2.3.4')

  def test_x_forwarded_for_stripped_when_not_verified_connection(self):
    # type: () -> None
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
