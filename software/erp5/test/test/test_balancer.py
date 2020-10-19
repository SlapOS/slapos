import glob
import hashlib
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
import urlparse
from BaseHTTPServer import BaseHTTPRequestHandler
from typing import Any, Dict, Optional

import idna
import mock
import OpenSSL.SSL
import pexpect
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

  @property
  def ca_crt_path(self):
    # type: () -> str
    """Path of the CA certificate from this caucase.
    """
    ca_crt_path = os.path.join(self.directory, 'ca.crt.pem')
    if not os.path.exists(ca_crt_path):
      with open(ca_crt_path, 'w') as f:
        f.write(
            requests.get(urlparse.urljoin(
                self.url,
                '/cas/crt/ca.crt.pem',
            )).text)
    return ca_crt_path

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


class SlowHTTPServer(ManagedHTTPServer):
  """An HTTP Server which reply after 3 seconds.
  """
  class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
      # type: () -> None
      self.send_response(200)
      self.send_header("Content-Type", "text/plain")
      time.sleep(3)
      self.end_headers()
      self.wfile.write("OK\n")

    log_message = logging.getLogger(__name__ + '.SlowHandler').info


class TestAccessLog(BalancerTestCase, CrontabMixin):
  """Check access logs emitted by balancer
  """
  __partition_reference__ = 'l'
  @classmethod
  def _getInstanceParameterDict(cls):
    # type: () -> Dict
    parameter_dict = super(TestAccessLog, cls)._getInstanceParameterDict()
    # use a slow server instead
    parameter_dict['dummy_http_server'] = [[cls.getManagedResource("slow_web_server", SlowHTTPServer).netloc, 1, False]]
    return parameter_dict

  def test_access_log_format(self):
    # type: () -> None
    requests.get(
        urlparse.urljoin(self.default_balancer_url, '/url_path'),
        verify=False,
    )
    with open(os.path.join(self.computer_partition_root_path, 'var', 'log', 'apache-access.log')) as access_log_file:
      access_line = access_log_file.read()
    self.assertIn('/url_path', access_line)

    # last \d is the request time in micro seconds, since this SlowHTTPServer
    # sleeps for 3 seconds, it should take between 3 and 4 seconds to process
    # the request - but our test machines can be slow sometimes, so we tolerate
    # it can take up to 20 seconds.
    match = re.match(
        r'([(\d\.)]+) - - \[(.*?)\] "(.*?)" (\d+) (\d+) "(.*?)" "(.*?)" (\d+)',
        access_line
    )
    self.assertTrue(match)
    assert match
    request_time = int(match.groups()[-1])
    self.assertGreater(request_time, 3 * 1000 * 1000)
    self.assertLess(request_time, 20 * 1000 * 1000)

  def test_access_log_apachedex_report(self):
    # type: () -> None
    # make a request so that we have something in the logs
    requests.get(self.default_balancer_url, verify=False)

    # crontab for apachedex is executed
    self._executeCrontabAtDate('generate-apachedex-report', '23:59')
    # it creates a report for the day
    apachedex_report, = glob.glob(
        os.path.join(
            self.computer_partition_root_path,
            'srv',
            'monitor',
            'private',
            'apachedex',
            'ApacheDex-*.html',
        ))
    with open(apachedex_report, 'r') as f:
      report_text = f.read()
    self.assertIn('APacheDEX', report_text)
    # having this table means that apachedex could parse some lines.
    self.assertIn('<h2>Hits per status code</h2>', report_text)

  def test_access_log_rotation(self):
    # type: () -> None
    # run logrotate a first time so that it create state files
    self._executeCrontabAtDate('logrotate', '2000-01-01')

    # make a request so that we have something in the logs
    requests.get(self.default_balancer_url, verify=False).raise_for_status()

    # slow query crontab depends on crontab for log rotation
    # to be executed first.
    self._executeCrontabAtDate('logrotate', '2050-01-01')
    # this logrotate leaves the log for the day as non compressed
    rotated_log_file = os.path.join(
        self.computer_partition_root_path,
        'srv',
        'backup',
        'logrotate',
        'apache-access.log-20500101',
    )
    self.assertTrue(os.path.exists(rotated_log_file))

    requests.get(self.default_balancer_url, verify=False).raise_for_status()
    # on next day execution of logrotate, log files are compressed
    self._executeCrontabAtDate('logrotate', '2050-01-02')
    self.assertTrue(os.path.exists(rotated_log_file + '.xz'))
    self.assertFalse(os.path.exists(rotated_log_file))


class BalancerCookieHTTPServer(ManagedHTTPServer):
  """An HTTP Server which can set balancer cookie.

  This server set cookie when requested /set-cookie path.

  The reply body is the name used when registering this resource
  using getManagedResource. This way we can assert which
  backend replied.
  """

  @property
  def RequestHandler(self):
    server = self
    class RequestHandler(BaseHTTPRequestHandler):
      def do_GET(self):
        # type: () -> None
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        if self.path == '/set_cookie':
          # the balancer tells the backend what's the name of the balancer cookie with
          # the X-Balancer-Current-Cookie header.
          self.send_header('Set-Cookie', '%s=anything' % self.headers['X-Balancer-Current-Cookie'])
          # The name of this cookie is SERVERID
          assert self.headers['X-Balancer-Current-Cookie'] == 'SERVERID'
        self.end_headers()
        self.wfile.write(server._name)

    return RequestHandler

  log_message = logging.getLogger(__name__ + '.BalancerCookieHTTPServer').info


class TestBalancer(BalancerTestCase):
  """Check balancing capabilities
  """
  __partition_reference__ = 'b'
  @classmethod
  def _getInstanceParameterDict(cls):
    # type: () -> Dict
    parameter_dict = super(TestBalancer, cls)._getInstanceParameterDict()

    # use two backend servers
    parameter_dict['dummy_http_server'] = [
        [cls.getManagedResource("backend_web_server1", BalancerCookieHTTPServer).netloc, 1, False],
        [cls.getManagedResource("backend_web_server2", BalancerCookieHTTPServer).netloc, 1, False],
    ]
    return parameter_dict

  def test_balancer_round_robin(self):
    # requests are by default balanced to both servers
    self.assertEqual(
        {requests.get(self.default_balancer_url, verify=False).text for _ in range(10)},
        {'backend_web_server1', 'backend_web_server2'}
    )

  def test_balancer_server_down(self):
    # if one backend is down, it is excluded from balancer
    self.getManagedResource("backend_web_server2", BalancerCookieHTTPServer).close()
    self.addCleanup(self.getManagedResource("backend_web_server2", BalancerCookieHTTPServer).open)
    self.assertEqual(
        {requests.get(self.default_balancer_url, verify=False).text for _ in range(10)},
        {'backend_web_server1',}
    )

  def test_balancer_set_cookie(self):
    # if backend provides a "SERVERID" cookie, balancer will overwrite it with the
    # backend selected by balancing algorithm
    self.assertIn(
        requests.get(urlparse.urljoin(self.default_balancer_url, '/set_cookie'), verify=False).cookies['SERVERID'],
        ('default-0', 'default-1'),
    )

  def test_balancer_respects_sticky_cookie(self):
    # if request is made with the sticky cookie, the client stick on one balancer
    cookies = dict(SERVERID='default-1')
    self.assertEqual(
        {requests.get(self.default_balancer_url, verify=False, cookies=cookies).text for _ in range(10)},
        {'backend_web_server2',}
    )

    # if that backend becomes down, requests are balanced to another server
    self.getManagedResource("backend_web_server2", BalancerCookieHTTPServer).close()
    self.addCleanup(self.getManagedResource("backend_web_server2", BalancerCookieHTTPServer).open)
    self.assertEqual(
        requests.get(self.default_balancer_url, verify=False, cookies=cookies).text,
        'backend_web_server1')


class TestTLS(BalancerTestCase):
  """Check TLS
  """
  __partition_reference__ = 's'

  def _getServerCertificate(self, hostname, port):
    # type: (Optional[str], Optional[int]) -> Any
    hostname_idna = idna.encode(hostname)
    sock = socket.socket()

    sock.connect((hostname, port))
    ctx = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv23_METHOD)
    ctx.check_hostname = False
    ctx.verify_mode = OpenSSL.SSL.VERIFY_NONE

    sock_ssl = OpenSSL.SSL.Connection(ctx, sock)
    sock_ssl.set_connect_state()
    sock_ssl.set_tlsext_host_name(hostname_idna)
    sock_ssl.do_handshake()
    cert = sock_ssl.get_peer_certificate()
    crypto_cert = cert.to_cryptography()
    sock_ssl.close()
    sock.close()
    return crypto_cert

  def test_certificate_validates_with_caucase_ca(self):
    # type: () -> None
    caucase = self.getManagedResource("caucase", CaucaseService)
    requests.get(self.default_balancer_url, verify=caucase.ca_crt_path)

  def test_certificate_renewal(self):
    # type: () -> None
    caucase = self.getManagedResource("caucase", CaucaseService)
    balancer_parsed_url = urlparse.urlparse(self.default_balancer_url)
    certificate_before_renewal = self._getServerCertificate(
        balancer_parsed_url.hostname,
        balancer_parsed_url.port)

    # run caucase updater 90 days in the future, so that certificate is
    # renewed.
    caucase_updater = os.path.join(
        self.computer_partition_root_path,
        'etc',
        'service',
        'caucase-updater',
    )
    process = pexpect.spawnu(
       "faketime +90days %s" % caucase_updater,
        env=dict(os.environ, PYTHONPATH=''),
    )
    logger = self.logger
    class DebugLogFile:
      def write(self, msg):
        logger.info("output from caucase_updater: %s", msg)
      def flush(self):
        pass
    process.logfile = DebugLogFile()
    process.expect(u"Renewing .*\nNext wake-up.*")
    process.terminate()
    process.wait()

    # wait for server to use new certificate
    for _ in range(30):
      certificate_after_renewal = self._getServerCertificate(
          balancer_parsed_url.hostname,
          balancer_parsed_url.port)
      if certificate_after_renewal.not_valid_before > certificate_before_renewal.not_valid_before:
        break
      time.sleep(.5)

    self.assertGreater(
        certificate_after_renewal.not_valid_before,
        certificate_before_renewal.not_valid_before,
    )

    # requests are served properly after cert renewal
    requests.get(self.default_balancer_url, verify=caucase.ca_crt_path).raise_for_status()


class ContentTypeHTTPServer(ManagedHTTPServer):
  """An HTTP Server which reply with content type from path.

  For example when requested http://host/text/plain it will reply
  with Content-Type: text/plain header.

  The body is always "OK"
  """

  class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
      # type: () -> None
      self.send_response(200)
      if self.path == '/':
        return self.end_headers()
      content_type = self.path[1:]
      self.send_header("Content-Type", content_type)
      self.end_headers()
      self.wfile.write("OK")

  log_message = logging.getLogger(__name__ + '.ContentTypeHTTPServer').info


class TestContentEncoding(BalancerTestCase):
  """Test how responses are gzip encoded or not depending on content type header.
  """
  __partition_reference__ = 'ce'
  @classmethod
  def _getInstanceParameterDict(cls):
    # type: () -> Dict
    parameter_dict = super(TestContentEncoding, cls)._getInstanceParameterDict()
    parameter_dict['dummy_http_server'] = [
        [cls.getManagedResource("content_type_server", ContentTypeHTTPServer).netloc, 1, False],
    ]
    return parameter_dict

  def test_gzip_encoding(self):
    for content_type in (
        'text/cache-manifest',
        'text/html',
        'text/plain',
        'text/css',
        'application/hal+json',
        'application/json',
        'application/x-javascript',
        'text/xml',
        'application/xml',
        'application/rss+xml',
        'text/javascript',
        'application/javascript',
        'image/svg+xml',
        'application/x-font-ttf',
        'application/font-woff',
        'application/font-woff2',
        'application/x-font-opentype',
        'application/wasm',):
      resp = requests.get(urlparse.urljoin(self.default_balancer_url, content_type), verify=False)
      self.assertEqual(resp.headers['Content-Type'], content_type)
      self.assertEqual(
          resp.headers['Content-Encoding'],
          'gzip',
          '%s uses wrong encoding: %s' % (content_type, resp.headers['Content-Encoding']))
      self.assertEqual(resp.text, 'OK')

  def test_no_gzip_encoding(self):
    resp = requests.get(urlparse.urljoin(self.default_balancer_url, '/image/png'), verify=False)
    self.assertNotIn('Content-Encoding', resp.headers)
    self.assertEqual(resp.text, 'OK')


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
