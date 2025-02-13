import datetime
import functools
import ipaddress
import json
import logging
import lzma
import os
import re
import socket
import subprocess
import sqlite3
import tempfile
import time
import typing
import urllib.parse
from http.server import BaseHTTPRequestHandler
import http
from unittest import expectedFailure, mock

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import OpenSSL.SSL
import pexpect
import psutil
import requests

from slapos.proxy.db_version import DB_VERSION
from slapos.testing.caucase import CaucaseCertificate, CaucaseService
from slapos.testing.utils import CrontabMixin, ManagedHTTPServer

from . import ERP5InstanceTestCase, default, matrix, setUpModule

_ = setUpModule


class EchoHTTPServer(ManagedHTTPServer):
  """An HTTP Server responding with the request path and incoming headers,
  encoded in json.
  """
  class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
      self.send_response(200)
      self.send_header("Content-Type", "application/json")
      response = json.dumps(
          {
              'Path': self.path,
              'Incoming Headers': dict(self.headers.items()),
          },
          indent=2,
      ).encode('utf-8')
      self.end_headers()
      self.wfile.write(response)

    log_message = logging.getLogger(__name__ + '.EchoHTTPServer').info


class EchoHTTP11Server(ManagedHTTPServer):
  """An HTTP/1.1 Server responding with the request path and incoming headers,
  encoded in json.
  """
  class RequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def do_GET(self) -> None:
      self.send_response(200)
      self.send_header("Content-Type", "application/json")
      response = json.dumps(
          {
              'Path': self.path,
              'Incoming Headers': dict(self.headers.items()),
          },
          indent=2,
      ).encode('utf-8')
      self.send_header("Content-Length", str(len(response)))
      self.end_headers()
      self.wfile.write(response)

    log_message = logging.getLogger(__name__ + '.EchoHTTP11Server').info


class BalancerTestCase(ERP5InstanceTestCase):
  # We explicitly specify 'balancer' as our software type here,
  # therefore we don't request ZODB. We therefore don't
  # need to run these tests with both NEO and ZEO mode,
  # it wouldn't make any difference.
  #   https://lab.nexedi.com/nexedi/slapos/blob/273037c8/stack/erp5/instance.cfg.in#L216-230
  __test_matrix__ = matrix((default,))

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'balancer'

  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    return {
        'tcpv4-port': 8000,
        'computer-memory-percent-threshold': 100,
        # XXX what is this ? should probably not be needed here
        'name': cls.__name__,
        'monitor-passwd': 'secret',
        'apachedex-configuration': [
            '--logformat', '%h %l %u %t "%r" %>s %O "%{Referer}i" "%{User-Agent}i" %{ms}T',
            '--erp5-base', '+erp5', '.*/VirtualHostRoot/erp5(/|\\?|$)',
            '--base', '+other', '/',
            '--skip-user-agent', 'Zabbix',
            '--error-detail',
            '--js-embed',
            '--quiet',
          ],
        'apachedex-promise-threshold': 0,
        'haproxy-server-check-path': '/',
        'zope-family-dict': {
            'default': ['dummy_http_server'],
        },
        'dummy_http_server': [[cls.getManagedResource("backend_web_server", EchoHTTPServer).netloc, 1, False]],
        'ssl-authentication-dict': {'default': False},
        'ssl': {},
        'timeout-dict': {'default': None},
        'frontend-parameter-dict': {
          'default': {
            'internal-path': '',
            'zope-family': 'default',
          },
        },
        'family-path-routing-dict': {},
        'path-routing-list': [],
      }

  @classmethod
  def getInstanceParameterDict(cls) -> dict:
    return {'_': json.dumps(cls._getInstanceParameterDict())}

  def setUp(self) -> None:
    self.default_balancer_direct_url = json.loads(
        self.computer_partition.getConnectionParameterDict()['_'])['default']
    self.default_balancer_zope_url = json.loads(
        self.computer_partition.getConnectionParameterDict()['_'])['url-backend-default']


class TestURLRewrite(BalancerTestCase):
  __partition_reference__ = 'ur'
  def test_direct(self):
    self.assertEqual(requests.get(self.default_balancer_direct_url, verify=False).json()['Path'], '/')
    self.assertEqual(
      requests.get(
        urllib.parse.urljoin(
          self.default_balancer_direct_url,
          '/VirtualHostBase/https/example.com:443/VirtualHostRoot/path'),
        verify=False
      ).json()['Path'],
      '/VirtualHostBase/https/example.com:443/VirtualHostRoot/path')

  def test_zope(self):
    netloc = urllib.parse.urlparse(self.default_balancer_zope_url).netloc
    self.assertEqual(
      requests.get(self.default_balancer_zope_url, verify=False).json()['Path'],
      f'/VirtualHostBase/https/{netloc}/VirtualHostRoot/')
    self.assertEqual(
      requests.get(urllib.parse.urljoin(
        self.default_balancer_zope_url, 'path'), verify=False).json()['Path'],
      f'/VirtualHostBase/https/{netloc}/VirtualHostRoot/path')
    self.assertEqual(
      requests.get(
        urllib.parse.urljoin(
          self.default_balancer_zope_url,
          '/VirtualHostBase/https/example.com:443/VirtualHostRoot/path'),
        verify=False
      ).json()['Path'],
      f'/VirtualHostBase/https/{netloc}/VirtualHostRoot/VirtualHostBase/https/example.com:443/VirtualHostRoot/path')

  def test_bad_host(self):
    self.assertEqual(
      requests.get(self.default_balancer_zope_url, headers={'Host': 'a/b'}, verify=False).status_code,
      requests.codes.bad_request)


class SlowHTTPServer(ManagedHTTPServer):
  """An HTTP Server which reply after a timeout.

  Timeout is 2 seconds by default, and can be specified in the path of the URL:

    GET /{timeout}

  but because balancer rewrites the URL, the actual URL used by this server is:

    GET /VirtualHostBase/https/{host}/VirtualHostRoot/{timeout}

  """
  class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
      timeout = 2
      if self.path == '/':  # for health checks
        timeout = 0
      try:
        timeout = int(self.path.split('/')[5])
      except (ValueError, IndexError):
        pass
      self.send_response(200)
      self.send_header("Content-Type", "text/plain")
      time.sleep(timeout)
      self.end_headers()
      self.wfile.write(b"OK\n")

    log_message = logging.getLogger(__name__ + '.SlowHTTPServer').info


class TestTimeout(BalancerTestCase, CrontabMixin):
  __partition_reference__ = 't'
  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    parameter_dict = super()._getInstanceParameterDict()
    # use a slow server instead
    parameter_dict['dummy_http_server'] = [[cls.getManagedResource("slow_web_server", SlowHTTPServer).netloc, 1, False]]
    # and set timeout of 1 second
    parameter_dict['timeout-dict'] = {'default': 1}
    return parameter_dict

  def test_timeout(self) -> None:
    self.assertEqual(
      requests.get(
          urllib.parse.urljoin(self.default_balancer_zope_url, '/1'),
          verify=False).status_code,
      requests.codes.ok)
    self.assertEqual(
      requests.get(
          urllib.parse.urljoin(self.default_balancer_zope_url, '/5'),
          verify=False).status_code,
      requests.codes.gateway_timeout)


class TestLog(BalancerTestCase, CrontabMixin):
  """Check logs emitted by balancer
  """
  __partition_reference__ = 'l'
  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    parameter_dict = super()._getInstanceParameterDict()
    # use a slow server instead, so that we can test logs with slow requests
    parameter_dict['dummy_http_server'] = [[cls.getManagedResource("slow_web_server", SlowHTTPServer).netloc, 1, False]]
    return parameter_dict

  def test_access_log_format(self) -> None:
    requests.get(
        urllib.parse.urljoin(self.default_balancer_zope_url, '/url_path'),
        verify=False,
    )
    time.sleep(.5) # wait a bit more until access is logged
    with open(os.path.join(self.computer_partition_root_path, 'var', 'log', 'apache-access.log')) as access_log_file:
      access_line = access_log_file.read().splitlines()[-1]
    self.assertIn('/url_path', access_line)

    # last \d is the request time in milli seconds, since this SlowHTTPServer
    # sleeps for 2 seconds, it should take between 2 and 3 seconds to process
    # the request - but our test machines can be slow sometimes, so we tolerate
    # it can take up to 20 seconds.
    match = re.match(
        r'([(\da-fA-F:\.)]+) - - \[(.*?)\] "(.*?)" (\d+) (\d+) "(.*?)" "(.*?)" (\d+)',
        access_line
    )
    self.assertTrue(match)
    assert match
    request_time = int(match.groups()[-1])
    self.assertGreater(request_time, 2 * 1000)
    self.assertLess(request_time, 20 * 1000)

  def test_access_log_apachedex_report(self) -> None:
    # make a request so that we have something in the logs
    requests.get(self.default_balancer_zope_url, verify=False)

    # crontab for daily apachedex is executed
    self._executeCrontabAtDate('generate-apachedex-report', '23:59')
    # it creates a report for the day
    apachedex_report, = (
      self.computer_partition_root_path
        / 'srv'
        / 'monitor'
        / 'private'
        / 'apachedex').glob('ApacheDex-*.html')
    report_text = apachedex_report.read_text()
    self.assertIn('APacheDEX', report_text)
    # having this table means that apachedex could parse some lines.
    self.assertIn('<h2>Hits per status code</h2>', report_text)

    # weekly apachedex uses the logs after rotation, we'll run log rotation
    # until we have a xz file for two days ago and a non compressed file for
    # yesterday
    # run logrotate a first time so that it create state files
    self._executeCrontabAtDate('logrotate', '2000-01-01')
    requests.get(urllib.parse.urljoin(self.default_balancer_zope_url, 'error-two-days-ago'), verify=False)
    self._executeCrontabAtDate('logrotate', 'yesterday 00:00')
    requests.get(urllib.parse.urljoin(self.default_balancer_zope_url, 'error-yesterday'), verify=False)
    self._executeCrontabAtDate('logrotate', '00:00')

    # this apachedex command uses compressed files, verify that our test setup
    # is correct and that the error from two days ago is in the compressed file.
    two_days_ago_log, = (
      self.computer_partition_root_path / 'srv' / 'backup'/ 'logrotate'
    ).glob("apache-access.log-*.xz")
    with lzma.open(two_days_ago_log) as f:
      self.assertIn(b'GET /error-two-days-ago', f.read())

    self._executeCrontabAtDate('generate-weekly-apachedex-report', '23:59')
    # this creates a report for the week
    apachedex_weekly_report, = (
      self.computer_partition_root_path
        / 'srv'
        / 'monitor'
        / 'private'
        / 'apachedex'
        / 'weekly').glob('*.html')
    weekly_report_text = apachedex_weekly_report.read_text()
    self.assertIn('APacheDEX', weekly_report_text)
    # because we run apachedex with error details, we can see our error requests
    self.assertIn('error-two-days-ago', weekly_report_text)
    self.assertIn('error-yesterday', weekly_report_text)

  def test_access_log_rotation(self) -> None:
    # run logrotate a first time so that it create state files
    self._executeCrontabAtDate('logrotate', '2000-01-01')

    # make a request so that we have something in the logs
    requests.get(self.default_balancer_zope_url, verify=False).raise_for_status()

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

    requests.get(self.default_balancer_zope_url, verify=False).raise_for_status()
    # on next day execution of logrotate, log files are compressed
    self._executeCrontabAtDate('logrotate', '2050-01-02')
    self.assertTrue(os.path.exists(rotated_log_file + '.xz'))
    self.assertFalse(os.path.exists(rotated_log_file))

  def test_error_log(self) -> None:
    # stop backend server
    backend_server = self.getManagedResource("slow_web_server", SlowHTTPServer)
    self.addCleanup(backend_server.open)
    backend_server.close()
    # after a while, balancer should detect and log this event in error log
    time.sleep(5)
    self.assertEqual(
        requests.get(self.default_balancer_zope_url, verify=False).status_code,
        requests.codes.service_unavailable)
    error_log_file = self.computer_partition_root_path / 'var' / 'log' / 'apache-error.log'
    error_line = error_log_file.read_text().splitlines()[-1]
    self.assertIn('backend default has no server available!', error_line)
    # this log also include a timestamp
    self.assertRegex(error_line, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')


class BalancerCookieHTTPServer(ManagedHTTPServer):
  """An HTTP Server which can set balancer cookie.

  This server set cookie when requested /set-cookie path (actually
  /VirtualHostBase/https/{host}/VirtualHostRoot/set-cookie , which is
  added by balancer proxy)

  The reply body is the name used when registering this resource
  using getManagedResource. This way we can assert which
  backend replied.
  """

  @property
  def RequestHandler(self):
    server = self
    class RequestHandler(BaseHTTPRequestHandler):
      def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")

        if self.path != '/' and self.path.split('/')[5] == 'set_cookie':
          # the balancer tells the backend what's the name of the balancer cookie with
          # the X-Balancer-Current-Cookie header.
          self.send_header('Set-Cookie', '%s=anything' % self.headers['X-Balancer-Current-Cookie'])
          # The name of this cookie is SERVERID
          assert self.headers['X-Balancer-Current-Cookie'] == 'SERVERID'
        self.end_headers()
        self.wfile.write(server._name.encode('utf-8'))
      log_message = logging.getLogger(__name__ + '.BalancerCookieHTTPServer').info

    return RequestHandler


class TestBalancer(BalancerTestCase):
  """Check balancing capabilities
  """
  __partition_reference__ = 'b'
  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    parameter_dict = super()._getInstanceParameterDict()

    # use two backend servers
    parameter_dict['dummy_http_server'] = [
        [cls.getManagedResource("backend_web_server1", BalancerCookieHTTPServer).netloc, 1, False],
        [cls.getManagedResource("backend_web_server2", BalancerCookieHTTPServer).netloc, 1, False],
    ]
    return parameter_dict

  def test_balancer_round_robin(self) -> None:
    # requests are by default balanced to both servers
    self.assertEqual(
        {requests.get(self.default_balancer_zope_url, verify=False).text for _ in range(10)},
        {'backend_web_server1', 'backend_web_server2'}
    )

  def test_balancer_server_down(self) -> None:
    # if one backend is down, it is excluded from balancer
    self.getManagedResource("backend_web_server2", BalancerCookieHTTPServer).close()
    self.addCleanup(self.getManagedResource("backend_web_server2", BalancerCookieHTTPServer).open)
    self.assertEqual(
        {requests.get(self.default_balancer_zope_url, verify=False).text for _ in range(10)},
        {'backend_web_server1',}
    )

  def test_balancer_set_cookie(self) -> None:
    # if backend provides a "SERVERID" cookie, balancer will overwrite it with the
    # backend selected by balancing algorithm
    self.assertIn(
        requests.get(urllib.parse.urljoin(self.default_balancer_zope_url, '/set_cookie'), verify=False).cookies['SERVERID'],
        ('default-0', 'default-1'),
    )

  def test_balancer_respects_sticky_cookie(self) -> None:
    # if request is made with the sticky cookie, the client stick on one balancer
    cookies = dict(SERVERID='default-1')
    self.assertEqual(
        {requests.get(self.default_balancer_zope_url, verify=False, cookies=cookies).text for _ in range(10)},
        {'backend_web_server2',}
    )

    # if that backend becomes down, requests are balanced to another server
    self.getManagedResource("backend_web_server2", BalancerCookieHTTPServer).close()
    self.addCleanup(self.getManagedResource("backend_web_server2", BalancerCookieHTTPServer).open)
    self.assertEqual(
        requests.get(self.default_balancer_zope_url, verify=False, cookies=cookies).text,
        'backend_web_server1')

  def test_balancer_stats_socket(self) -> None:
    # real time statistics can be obtained by using the stats socket and there
    # is a wrapper which makes this a bit easier.
    socat_process = subprocess.Popen(
        [self.computer_partition_root_path / 'bin' / 'haproxy-socat-stats'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    try:
      output, _ = socat_process.communicate(b"show stat\n")
    except:
      socat_process.kill()
      socat_process.wait()
      raise
    self.assertEqual(socat_process.poll(), 0)
    # output is a csv
    self.assertIn(b'\ndefault,BACKEND,', output)


class TestTestRunnerEntryPoints(BalancerTestCase):
  """Check balancer has some entries for test runner.
  """
  __partition_reference__ = 't'
  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    parameter_dict = super()._getInstanceParameterDict()

    parameter_dict['dummy_http_server-test-runner-address-list'] = [
        [
            cls.getManagedResource("backend_0", EchoHTTPServer).hostname,
            cls.getManagedResource("backend_0", EchoHTTPServer).port,
        ],
        [
            cls.getManagedResource("backend_1", EchoHTTPServer).hostname,
            cls.getManagedResource("backend_1", EchoHTTPServer).port,
        ],
        [
            cls.getManagedResource("backend_2", EchoHTTPServer).hostname,
            cls.getManagedResource("backend_2", EchoHTTPServer).port,
        ],
    ]
    return parameter_dict

  def test_use_proper_backend(self) -> None:
    # requests are directed to proper backend based on URL path
    test_runner_url_list = self.getRootPartitionConnectionParameterDict(
    )['default-test-runner-url-list']
    url_0, url_1, url_2 = test_runner_url_list
    self.assertEqual(
        urllib.parse.urlparse(url_0).netloc,
        urllib.parse.urlparse(url_1).netloc)
    self.assertEqual(
        urllib.parse.urlparse(url_0).netloc,
        urllib.parse.urlparse(url_2).netloc)

    path_0 = '/VirtualHostBase/https/{netloc}/VirtualHostRoot/_vh_unit_test_0/something'.format(
        netloc=urllib.parse.urlparse(url_0).netloc)
    path_1 = '/VirtualHostBase/https/{netloc}/VirtualHostRoot/_vh_unit_test_1/something'.format(
        netloc=urllib.parse.urlparse(url_0).netloc)
    path_2 = '/VirtualHostBase/https/{netloc}/VirtualHostRoot/_vh_unit_test_2/something'.format(
        netloc=urllib.parse.urlparse(url_0).netloc)

    self.assertEqual(
        {
            requests.get(url_0 + 'something', verify=False).json()['Path']
            for _ in range(10)
        }, {path_0})
    self.assertEqual(
        {
            requests.get(url_1 + 'something', verify=False).json()['Path']
            for _ in range(10)
        }, {path_1})
    self.assertEqual(
        {
            requests.get(url_2 + 'something', verify=False).json()['Path']
            for _ in range(10)
        }, {path_2})

    # If a test runner backend is down, others can be accessed.
    self.getManagedResource("backend_0", EchoHTTPServer).close()
    self.assertEqual(
        {
            requests.get(url_0 + 'something', verify=False).status_code
            for _ in range(5)
        }, {503})
    self.assertEqual(
        {
            requests.get(url_1 + 'something', verify=False).json()['Path']
            for _ in range(10)
        }, {path_1})


class TestHTTP(BalancerTestCase):
  """Check HTTP protocol with a HTTP/1.1 backend
  """
  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    parameter_dict = super()._getInstanceParameterDict()
    # use a HTTP/1.1 server instead
    parameter_dict['dummy_http_server'] = [[cls.getManagedResource("HTTP/1.1 Server", EchoHTTP11Server).netloc, 1, False]]
    return parameter_dict

  __partition_reference__ = 'h'

  def test_http_version(self) -> None:
    self.assertEqual(
        subprocess.check_output([
            'curl',
            '--silent',
            '--show-error',
            '--output',
            '/dev/null',
            '--insecure',
            '--write-out',
            '%{http_version}',
            self.default_balancer_zope_url,
        ]),
        b'2',
    )

  def test_keep_alive(self) -> None:
    # when doing two requests, connection is established only once
    with requests.Session() as session:
      session.verify = False

      # do a first request, which establish a first connection
      session.get(self.default_balancer_zope_url).raise_for_status()

      # "break" new connection method and check we can make another request
      with mock.patch(
          "requests.packages.urllib3.connectionpool.HTTPSConnectionPool._new_conn",
      ) as new_conn:
        session.get(self.default_balancer_zope_url).raise_for_status()
      new_conn.assert_not_called()

      parsed_url = urllib.parse.urlparse(self.default_balancer_zope_url)

      # check that we have an open file for the ip connection
      self.assertTrue([
          c for c in psutil.Process(os.getpid()).connections()
          if c.status == 'ESTABLISHED' and c.raddr.ip == parsed_url.hostname
          and c.raddr.port == parsed_url.port
      ])


class TestServerTLSEmbeddedCaucase(BalancerTestCase):
  """Check Server TLS with embedded caucase
  """
  __partition_reference__ = 's'
  def _getCaucaseCACertificatePath(self) -> str:
    """Returns the path of the caucase certificate on file system.
    """
    ca_cert = tempfile.NamedTemporaryFile(
      prefix="ca.crt.pem",
      mode="w",
      delete=False,
    )
    ca_cert.write(
      requests.get(
        urllib.parse.urljoin(
          self.getRootPartitionConnectionParameterDict()['caucase-http-url'],
          '/cas/crt/ca.crt.pem',
        )).text)
    ca_cert.flush()
    self.addCleanup(os.unlink, ca_cert.name)
    return ca_cert.name

  def _getServerCertificate(self, hostname: str, port: int) -> x509.base.Certificate:
    sock = socket.socket(socket.AF_INET6 if ':' in hostname else socket.AF_INET)
    sock.connect((hostname, port))
    ctx = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv23_METHOD)
    sock_ssl = OpenSSL.SSL.Connection(ctx, sock)
    sock_ssl.set_connect_state()
    sock_ssl.set_tlsext_host_name(hostname.encode())
    sock_ssl.do_handshake()
    cert = sock_ssl.get_peer_certificate()
    crypto_cert = cert.to_cryptography()
    sock_ssl.close()
    sock.close()
    return crypto_cert

  def test_certificate_validates_with_caucase_ca(self) -> None:
    requests.get(self.default_balancer_zope_url, verify=self._getCaucaseCACertificatePath())

  def test_certificate_renewal(self) -> None:
    balancer_parsed_url = urllib.parse.urlparse(self.default_balancer_zope_url)
    certificate_before_renewal = self._getServerCertificate(
      balancer_parsed_url.hostname,
      balancer_parsed_url.port)

    # run caucase updater in the future, so that certificate is renewed
    caucase_updater, = (
      self.computer_partition_root_path / 'etc' / 'service'
    ).glob('caucase-updater-haproxy-certificate-*')
    process = pexpect.spawnu(f"faketime +90days {caucase_updater}")
    logger = self.logger
    class DebugLogFile:
      def write(self, msg):
        logger.info("output from caucase_updater: %s", msg)
      def flush(self):
        pass
    process.logfile = DebugLogFile()
    process.expect("Renewing .*\nNext wake-up.*")
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

    # requests are served properly after certificate renewal
    self.test_certificate_validates_with_caucase_ca()


class TestServerTLSExternalCaucase(TestServerTLSEmbeddedCaucase):
  """Check Server TLS with external caucase
  """
  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    parameter_dict = super()._getInstanceParameterDict()
    parameter_dict['ssl']['caucase-url'] = cls.getManagedResource(
      "caucase", CaucaseService).url
    return parameter_dict

  def test_published_caucase_http_url_parameter(self) -> None:
    self.assertEqual(
      self.getRootPartitionConnectionParameterDict()['caucase-http-url'],
      self.getManagedResource("caucase", CaucaseService).url,
    )


class TestServerTLSCSRTemplateParameter(TestServerTLSExternalCaucase):
  """Check Server TLS with a CSR template passed as parameter
  """
  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    # use a CSR template with this subject, we'll assert that the
    # certificate used by haproxy has same subject.
    cls.csr_subject = subject = x509.Name(
      [x509.NameAttribute(NameOID.COMMON_NAME, cls.__name__)])

    # Add all IPs of the computer in SubjectAlternativeName, we don't
    # know what will be the IP of the balancer partition.
    with sqlite3.connect(cls.slap._proxy_database) as db:
      ip_address_list = [
        x509.IPAddress(ipaddress.ip_address(r)) for (r, ) in db.execute(
          f"SELECT address FROM partition_network{DB_VERSION}").fetchall()
      ]
    assert ip_address_list

    csr = x509.CertificateSigningRequestBuilder().subject_name(
      subject).add_extension(
        x509.SubjectAlternativeName(ip_address_list),
        critical=True,
      ).sign(
        rsa.generate_private_key(
          public_exponent=65537,
          key_size=2048,
          backend=default_backend(),
        ),
        hashes.SHA256(),
        default_backend(),
      )

    parameter_dict = super()._getInstanceParameterDict()
    parameter_dict['ssl']['csr'] = csr.public_bytes(serialization.Encoding.PEM).decode()
    return parameter_dict

  def test_certificate_validates_with_caucase_ca(self) -> None:
    super().test_certificate_validates_with_caucase_ca()
    balancer_parsed_url = urllib.parse.urlparse(self.default_balancer_zope_url)
    cert = self._getServerCertificate(
      balancer_parsed_url.hostname,
      balancer_parsed_url.port,
    )
    self.assertEqual(
      cert.subject.rfc4514_string(),
      self.csr_subject.rfc4514_string())


class ContentTypeHTTPServer(ManagedHTTPServer):
  """An HTTP/1.1 Server which reply with content type from path.

  For example when requested http://host/text/plain it will reply
  with Content-Type: text/plain header.
  This actually uses a URL like this to support zope style virtual host:
  GET /VirtualHostBase/https/{host}/VirtualHostRoot/text/plain

  The body is always "OK"
  """
  class RequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def do_GET(self) -> None:
      self.send_response(200)
      if self.path == '/':
        self.send_header("Content-Length", '0')
        return self.end_headers()
      content_type = '/'.join(self.path.split('/')[5:])
      body = b"OK"
      self.send_header("Content-Type", content_type)
      self.send_header("Content-Length", str(len(body)))
      self.end_headers()
      self.wfile.write(body)

    log_message = logging.getLogger(__name__ + '.ContentTypeHTTPServer').info


class TestContentEncoding(BalancerTestCase):
  """Test how responses are gzip encoded or not depending on content type header.
  """
  __partition_reference__ = 'ce'
  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    parameter_dict = super()._getInstanceParameterDict()
    parameter_dict['dummy_http_server'] = [
        [cls.getManagedResource("content_type_server", ContentTypeHTTPServer).netloc, 1, False],
    ]
    return parameter_dict

  def test_gzip_encoding(self) -> None:
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
      resp = requests.get(urllib.parse.urljoin(self.default_balancer_zope_url, content_type), verify=False)
      self.assertEqual(resp.headers['Content-Type'], content_type)
      self.assertEqual(
          resp.headers.get('Content-Encoding'),
          'gzip',
          '{} uses wrong encoding: {}'.format(content_type, resp.headers.get('Content-Encoding')))
      self.assertEqual(resp.text, 'OK')

  def test_no_gzip_encoding(self) -> None:
    resp = requests.get(urllib.parse.urljoin(self.default_balancer_zope_url, '/image/png'), verify=False)
    self.assertNotIn('Content-Encoding', resp.headers)
    self.assertEqual(resp.text, 'OK')



class TestFrontendXForwardedFor(BalancerTestCase):
  __partition_reference__ = 'xff'

  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    frontend_caucase = cls.getManagedResource('frontend_caucase', CaucaseService)
    certificate = cls.getManagedResource('client_certificate', CaucaseCertificate)
    certificate.request('shared frontend', frontend_caucase)

    parameter_dict = super()._getInstanceParameterDict()
    # add another "-auth" backend, that will have ssl-authentication enabled
    parameter_dict['zope-family-dict']['default-auth'] = ['dummy_http_server']
    parameter_dict['ssl-authentication-dict'] = {
        'default': False,
        'default-auth': True,
    }
    parameter_dict['timeout-dict']['default-auth'] = None
    parameter_dict['ssl']['frontend-caucase-url-list'] = [frontend_caucase.url]
    return parameter_dict

  def test_x_forwarded_for_added_when_verified_connection(self) -> None:
    client_certificate = self.getManagedResource('client_certificate', CaucaseCertificate)

    for backend in ('default', 'default-auth'):
      balancer_url = json.loads(self.computer_partition.getConnectionParameterDict()['_'])[backend]
      result = requests.get(
        balancer_url,
        headers={'X-Forwarded-For': '1.2.3.4'},
        cert=(client_certificate.cert_file, client_certificate.key_file),
        verify=False,
      ).json()
      self.assertEqual(result['Incoming Headers'].get('x-forwarded-for', '').split(', ')[0], '1.2.3.4')

  def test_x_forwarded_for_stripped_when_no_certificate(self) -> None:
    balancer_url = json.loads(self.computer_partition.getConnectionParameterDict()['_'])['default']
    result = requests.get(
      balancer_url,
      headers={'X-Forwarded-For': '1.2.3.4'},
      verify=False,
    ).json()
    self.assertNotIn('x-fowarded-for', [k.lower() for k in result['Incoming Headers'].keys()])
    balancer_url = json.loads(self.computer_partition.getConnectionParameterDict()['_'])['default-auth']
    with self.assertRaisesRegex(Exception, "certificate required"):
      requests.get(
        balancer_url,
        headers={'X-Forwarded-For': '1.2.3.4'},
        verify=False,
      )

  def test_x_forwarded_for_stripped_when_not_verified_certificate(self) -> None:
    balancer_url = json.loads(self.computer_partition.getConnectionParameterDict()['_'])['default']

    # certificate from an unknown CA
    another_unrelated_caucase = self.getManagedResource('another_unrelated_caucase', CaucaseService)
    unknown_client_certificate = self.getManagedResource('unknown_client_certificate', CaucaseCertificate)
    unknown_client_certificate.request('unknown client certificate', another_unrelated_caucase)

    result = requests.get(
      balancer_url,
      headers={'X-Forwarded-For': '1.2.3.4'},
      cert=(unknown_client_certificate.cert_file, unknown_client_certificate.key_file),
      verify=False,
    ).json()
    self.assertNotIn('x-fowarded-for', [k.lower() for k in result['Incoming Headers'].keys()])

    balancer_url = json.loads(self.computer_partition.getConnectionParameterDict()['_'])['default-auth']
    with self.assertRaisesRegex(Exception, "unknown ca"):
      requests.get(
        balancer_url,
        headers={'X-Forwarded-For': '1.2.3.4'},
        cert=(unknown_client_certificate.cert_file, unknown_client_certificate.key_file),
        verify=False,
      )


class TestServerTLSProvidedCertificate(BalancerTestCase):
  """Check that certificate and key can be provided as instance parameters.
  """
  __partition_reference__ = 's'

  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    server_caucase = cls.getManagedResource('server_caucase', CaucaseService)
    server_certificate = cls.getManagedResource('server_certificate', CaucaseCertificate)
    # Add all IPs of the computer in SubjectAlternativeName, we don't
    # know what will be the IP of the balancer partition.
    with sqlite3.connect(cls.slap._proxy_database) as db:
      ip_address_list = [
        x509.IPAddress(ipaddress.ip_address(r)) for (r, ) in db.execute(
          f"SELECT address FROM partition_network{DB_VERSION}").fetchall()
      ]
    assert ip_address_list
    server_certificate.request(
      cls.__name__,
      server_caucase,
      x509.SubjectAlternativeName(ip_address_list))

    parameter_dict = super()._getInstanceParameterDict()
    with open(server_certificate.cert_file) as f:
      parameter_dict['ssl']['cert'] = f.read()
    with open(server_certificate.key_file) as f:
      parameter_dict['ssl']['key'] = f.read()
    return parameter_dict

  def test_certificate_validates_with_provided_ca(self) -> None:
    server_certificate = self.getManagedResource("server_certificate", CaucaseCertificate)
    requests.get(self.default_balancer_zope_url, verify=server_certificate.ca_crt_file)


class TestClientTLS(BalancerTestCase):
  __partition_reference__ = 'c'

  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    frontend_caucase1 = cls.getManagedResource('frontend_caucase1', CaucaseService)
    certificate1 = cls.getManagedResource('client_certificate1', CaucaseCertificate)
    certificate1.request('client_certificate1', frontend_caucase1)

    frontend_caucase2 = cls.getManagedResource('frontend_caucase2', CaucaseService)
    certificate2 = cls.getManagedResource('client_certificate2', CaucaseCertificate)
    certificate2.request('client_certificate2', frontend_caucase2)

    parameter_dict = super()._getInstanceParameterDict()
    parameter_dict['ssl-authentication-dict'] = {
        'default': True,
    }
    parameter_dict['ssl']['frontend-caucase-url-list'] = [
        frontend_caucase1.url,
        frontend_caucase2.url,
    ]
    return parameter_dict

  def test_refresh_crl(self) -> None:
    logger = self.logger

    class DebugLogFile:
      def write(self, msg):
        logger.info("output from caucase_updater: %s", msg)
      def flush(self):
        pass

    for client_certificate_name, caucase_name in (
        ('client_certificate1', 'frontend_caucase1'),
        ('client_certificate2', 'frontend_caucase2'),
    ):
      client_certificate = self.getManagedResource(client_certificate_name,
                                                   CaucaseCertificate)

      # when client certificate can be authenticated, backend receive the CN of
      # the client certificate in "remote-user" header
      def _make_request() -> dict:
        return requests.get(
            self.default_balancer_zope_url,
            cert=(client_certificate.cert_file, client_certificate.key_file),
            verify=False,
        ).json()

      self.assertEqual(_make_request()['Incoming Headers'].get('remote-user'),
                       client_certificate_name)

      # when certificate is revoked, updater service should update the CRL
      # used by balancer from the caucase service used for client certificates
      # (ie. the one used by frontend).
      caucase = self.getManagedResource(caucase_name, CaucaseService)
      client_certificate.revoke(caucase)

      # until the CRL is updated, the client certificate is still accepted.
      self.assertEqual(_make_request()['Incoming Headers'].get('remote-user'),
                       client_certificate_name)

      # We have two services in charge of updating CRL and CA certificates for
      # each frontend CA, plus the one for the balancer's own certificate
      caucase_updater_list = list((
        self.computer_partition_root_path / 'etc' / 'service'
      ).glob('caucase-updater-*'))
      self.assertEqual(len(caucase_updater_list), 3)

      # find the one corresponding to this caucase
      for caucase_updater_candidate in caucase_updater_list:
        if caucase.url in caucase_updater_candidate.read_text():
          caucase_updater = caucase_updater_candidate
          break
      else:
        self.fail("Could not find caucase updater script for %s" % caucase.url)

      # simulate running updater service in the future, to confirm that it fetches
      # the new CRL and make sure balancer uses that new CRL.
      process = pexpect.spawnu("faketime +1day %s" % caucase_updater)

      process.logfile = DebugLogFile()
      process.expect("Got new CRL.*Next wake-up at.*")
      process.terminate()
      process.wait()

      with self.assertRaisesRegex(Exception, 'certificate revoked'):
        _make_request()


class TestPathBasedRouting(BalancerTestCase):
  """Check path-based routing rewrites URLs as expected.
  """
  __partition_reference__ = 'pbr'

  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    parameter_dict = super()._getInstanceParameterDict()
    parameter_dict['zope-family-dict'][
      'second'
    ] = parameter_dict['zope-family-dict'][
      'default'
    ]
    parameter_dict['timeout-dict']['second'] = None
    parameter_dict['ssl-authentication-dict']['second'] = False
    # Routing rules outermost slashes mean nothing. They are internally
    # stripped and rebuilt in order to correctly represent the request's URL.
    parameter_dict['family-path-routing-dict'] = {
      'default': [
        ['foo/bar', 'erp5/boo/far/faz'], # no outermost slashes
        ['/foo', '/erp5/somewhere'],
        ['/foo/shadowed', '/foo_shadowed'], # unreachable
        ['/next', '/erp5/web_site_module/another_next_website'],
      ],
    }
    parameter_dict['path-routing-list'] = [
      ['/next', '/erp5/web_site_module/the_next_website'],
      ['/next2', '/erp5/web_site_module/the_next2_website'],
      ['//', '//erp5/web_site_module/123//'], # extraneous slashes
    ]
    return parameter_dict

  def test_routing(self) -> None:
    published_dict = json.loads(self.computer_partition.getConnectionParameterDict()['_'])
    scheme = 'scheme'
    netloc = 'example.com:8080'
    prefix = '/VirtualHostBase/' + scheme + '//' + urllib.parse.quote(
      netloc,
      safe='',
    )
    # For easier reading of test data, visually separating the virtual host
    # base from the virtual host root
    vhr = '/VirtualHostRoot'
    def assertRoutingEqual(family: str, path: str, expected_path: str) -> None:
      # sanity check: unlike the rules, this test is sensitive to outermost
      # slashes, and paths must be absolute-ish for code simplicity.
      assert path.startswith('/')
      # Frontend is expected to provide URLs with the following path structure:
      #   /VirtualHostBase/<scheme>//<netloc>/VirtualHostRoot<path>
      # where:
      # - scheme is the user-input scheme
      # - netloc is the user-input netloc
      # - path is the user-input path
      # Someday, frontends will instead propagate scheme and netloc via other
      # means (likely: HTTP headers), in which case this test and the SR will
      # need to be amended to reconstruct Virtual Host urls itself, and this
      # test will need to be updated accordingly.
      self.assertEqual(
        requests.get(
          urllib.parse.urljoin(published_dict[family], prefix + vhr + path),
          verify=False,
        ).json()['Path'],
        expected_path,
      )
    # Trailing slash presence is preserved.
    assertRoutingEqual('default', '/foo/bar',       prefix + '/erp5/boo/far/faz' + vhr + '/_vh_foo/_vh_bar')
    assertRoutingEqual('default', '/foo/bar/',      prefix + '/erp5/boo/far/faz' + vhr + '/_vh_foo/_vh_bar/')
    # Subpaths are preserved.
    assertRoutingEqual('default', '/foo/bar/hey',   prefix + '/erp5/boo/far/faz' + vhr + '/_vh_foo/_vh_bar/hey')
    # Rule precedence: later less-specific rules are applied.
    assertRoutingEqual('default', '/foo',           prefix + '/erp5/somewhere' + vhr + '/_vh_foo')
    assertRoutingEqual('default', '/foo/',          prefix + '/erp5/somewhere' + vhr + '/_vh_foo/')
    assertRoutingEqual('default', '/foo/baz',       prefix + '/erp5/somewhere' + vhr + '/_vh_foo/baz')
    # Rule precedence: later more-specific rules are meaningless.
    assertRoutingEqual('default', '/foo/shadowed',  prefix + '/erp5/somewhere' + vhr + '/_vh_foo/shadowed')
    # Rule precedence: family rules applied before general rules.
    assertRoutingEqual('default', '/next',          prefix + '/erp5/web_site_module/another_next_website' + vhr + '/_vh_next')
    # Fallback on general rules when no family-specific rule matches
    # Note: the root is special in that there is always a trailing slash in the
    # produced URL.
    assertRoutingEqual('default', '/',              prefix + '/erp5/web_site_module/123' + vhr + '/')
    # Rule-less family reach general rules.
    assertRoutingEqual('second',  '/foo/bar',       prefix + '/erp5/web_site_module/123' + vhr + '/foo/bar')    # Rules match whole-elements, so the rule order does not matter to
    # elements which share a common prefix.
    assertRoutingEqual('second',  '/next',          prefix + '/erp5/web_site_module/the_next_website' + vhr + '/_vh_next')
    assertRoutingEqual('second',  '/next2',         prefix + '/erp5/web_site_module/the_next2_website' + vhr + '/_vh_next2')


class StatusCodeHTTPServer(ManagedHTTPServer):
  """An HTTP Server which replies with the status code passed as path element,
  for example, it would reply with 418 for the following requests:

    GET /418

  because balancer rewrites the URL, the actual URL used by this server is:

    GET /VirtualHostBase/https/{host}/VirtualHostRoot/418

  """
  class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
      path_elements = [p for p in self.path.split('/') if p]
      if path_elements[:1] == ['VirtualHostBase']:
        path_elements = path_elements[4:]
      if not path_elements:
        path_elements = ['200']

      status = int(path_elements[0])
      self.send_response(status)
      self.send_header("Content-Type", "text/plain")
      self.end_headers()
      self.wfile.write(http.HTTPStatus(status).phrase.encode() + b"\n")

    def log_message(self, format: str, *args) -> None:
      logging.getLogger(__name__ + '.StatusCodeHTTPServer').info(format, *args)


class TestRateLimiting(BalancerTestCase):
  __partition_reference__ = 'rl'
  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    parameter_dict = super()._getInstanceParameterDict()
    # use our server with status code control instead
    parameter_dict['dummy_http_server'] = [[cls.getManagedResource("status_code_server", StatusCodeHTTPServer).netloc, 1, False]]
    # and set some rate limiting rules:
    parameter_dict["rate-limits"] = {
      "tarpit-duration": "5s",
      "rules": [
        # one based on the path
        {
          "max-requests": 3,
          "time-window": "20s",
          "url-path-pattern": "/200/.*limited",
          "action": "tarpit",
          "expire": "20s"
        },
        # one based on the HTTP status code
        {
          "max-requests": 5,
          "time-window": "10s",
          "status-code": "400:599",
          "table-name": "errors",
          "expire": "10s"
        },
      ],
    }

    # we'll connect to the backend with a certificate, so that the backend trusts our
    # X-Forwarded-For header and that we can simulate multiple clients from different
    # source IPs.
    frontend_caucase = cls.getManagedResource('frontend_caucase', CaucaseService)
    certificate = cls.getManagedResource('client_certificate', CaucaseCertificate)
    certificate.request('shared frontend', frontend_caucase)
    parameter_dict['ssl']['frontend-caucase-url-list'] = [frontend_caucase.url]

    return parameter_dict

  def tearDown(self):
    # restart haproxy between tests to reset the stick tables
    with self.slap.instance_supervisor_rpc as supervisor:
      info, = [i for i in
         supervisor.getAllProcessInfo() if i['name'].startswith('haproxy-')]
      haproxy_process_name = f"{info['group']}:{info['name']}"
      supervisor.stopProcess(haproxy_process_name)
      supervisor.startProcess(haproxy_process_name)
    self.slap.waitForInstance()

  def do_get(self, url_path:str, client_ip:typing.Union[str, None] = None) -> requests.Response:
    default_balancer_url = json.loads(
      self.computer_partition.getConnectionParameterDict()['_'])['url-backend-default']
    client_certificate = self.getManagedResource('client_certificate', CaucaseCertificate)
    headers = {}
    cert = None
    if client_ip:
      headers['X-Forwarded-For'] = client_ip
      cert = (client_certificate.cert_file, client_certificate.key_file)
    return requests.get(default_balancer_url + url_path, verify=False, headers=headers, cert=cert)

  def test_backend_rate_limiting_per_url(self) -> None:
    for client_ip in ('1.2.3.4', '::1', None):
      with self.subTest(client_ip):
        for _ in range(3):
          self.do_get('/200/rate_limited', client_ip).raise_for_status()
        limited_request = self.do_get('/200/rate_limited', client_ip)
        self.assertEqual(limited_request.status_code, requests.codes.too_many_requests)
        self.assertGreater(limited_request.elapsed , datetime.timedelta(seconds=5))
        self.do_get('/200/other_url', client_ip).raise_for_status()

  def test_backend_rate_limiting_per_status_code(self) -> None:
    for client_ip in ('1.2.3.4', '::1', None):
      with self.subTest(client_ip):
        self.assertEqual(self.do_get('/400', client_ip).status_code, 400)
        self.assertEqual(self.do_get('/401', client_ip).status_code, 401)
        self.assertEqual(self.do_get('/404', client_ip).status_code, 404)
        # status codes 2* and 3* do not increase the counter
        self.assertEqual(self.do_get('/200', client_ip).status_code, 200)
        self.assertEqual(self.do_get('/302', client_ip).status_code, 302)

        self.assertEqual(self.do_get('/500', client_ip).status_code, 500)
        self.assertEqual(self.do_get('/500', client_ip).status_code, 500)

        limited_request = self.do_get('/200', client_ip)
        self.assertEqual(limited_request.status_code, requests.codes.too_many_requests)

    self.do_get('/500', '4.5.6.7')
    self.assertIn(
      'key=4.5.6.7',
      subprocess.check_output(
        self.computer_partition_root_path / 'bin' / 'haproxy-socat-stats',
        input='show table stick_table_errors\n',
        text=True,
      )
    )

  @expectedFailure
  def test_status_code_only_track_matching_status_code(self):
    self.do_get('/200', '1.2.3.4')
    self.assertNotIn(
      'key=1.2.3.4',
      subprocess.check_output(
        self.computer_partition_root_path / 'bin' / 'haproxy-socat-stats',
        input='show table stick_table_errors\n',
        text=True,
      )
    )
