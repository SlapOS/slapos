import glob
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler
from unittest import mock

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import OpenSSL.SSL
import pexpect
import psutil
import requests

from slapos.testing.caucase import CaucaseCertificate, CaucaseService
from slapos.testing.utils import CrontabMixin, ManagedHTTPServer

from . import ERP5InstanceTestCase, setUpModule

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

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'balancer'

  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    return {
        'shared-certificate-authority-path': os.path.join(
            '~', 'srv', 'ssl'),
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
        'apachedex-promise-threshold': 100,
        'haproxy-server-check-path': '/',
        'zope-family-dict': {
            'default': ['dummy_http_server'],
        },
        'dummy_http_server': [[cls.getManagedResource("backend_web_server", EchoHTTPServer).netloc, 1, False]],
        'backend-path-dict': {
            'default': '',
        },
        'ssl-authentication-dict': {'default': False},
        'ssl': {
            'caucase-url': cls.getManagedResource("caucase", CaucaseService).url,
        },
        'timeout-dict': {'default': None},
        'family-path-routing-dict': {},
        'path-routing-list': [],
      }

  @classmethod
  def getInstanceParameterDict(cls) -> dict:
    return {'_': json.dumps(cls._getInstanceParameterDict())}

  def setUp(self) -> None:
    self.default_balancer_url = json.loads(
        self.computer_partition.getConnectionParameterDict()['_'])['default']


class SlowHTTPServer(ManagedHTTPServer):
  """An HTTP Server which reply after a timeout.

  Timeout is 2 seconds by default, and can be specified in the path of the URL
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
        urllib.parse.urljoin(self.default_balancer_url, '/url_path'),
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
        r'([(\d\.)]+) - - \[(.*?)\] "(.*?)" (\d+) (\d+) "(.*?)" "(.*?)" (\d+)',
        access_line
    )
    self.assertTrue(match)
    assert match
    request_time = int(match.groups()[-1])
    # XXX For slapos master, timing is in microsecond (not milisecond)
    self.assertGreater(request_time, 2 * 1000000)
    self.assertLess(request_time, 20 * 1000000)

  def test_access_log_apachedex_report(self) -> None:
    # make a request so that we have something in the logs
    requests.get(self.default_balancer_url, verify=False)

    # crontab for apachedex is executed
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

  def test_access_log_rotation(self) -> None:
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

  def test_error_log(self) -> None:
    # stop backend server
    backend_server = self.getManagedResource("slow_web_server", SlowHTTPServer)
    self.addCleanup(backend_server.open)
    backend_server.close()
    # after a while, balancer should detect and log this event in error log
    time.sleep(5)
    self.assertEqual(
        requests.get(self.default_balancer_url, verify=False).status_code,
        requests.codes.service_unavailable)
    error_log_file = self.computer_partition_root_path / 'var' / 'log' / 'apache-error.log'
    error_line = error_log_file.read_text().splitlines()[-1]
    self.assertIn('apache.conf -D FOREGROUND', error_line)
    # this log also include a timestamp
    # This regex is for haproxy mostly, so keep it commented for now, until we can
    # Merge the slapos-master setup and erp5.
    # self.assertRegexpMatches(error_line, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')


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
        if self.path == '/set_cookie':
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
        {requests.get(self.default_balancer_url, verify=False).text for _ in range(10)},
        {'backend_web_server1', 'backend_web_server2'}
    )

  def test_balancer_server_down(self) -> None:
    # if one backend is down, it is excluded from balancer
    self.getManagedResource("backend_web_server2", BalancerCookieHTTPServer).close()
    self.addCleanup(self.getManagedResource("backend_web_server2", BalancerCookieHTTPServer).open)
    self.assertEqual(
        {requests.get(self.default_balancer_url, verify=False).text for _ in range(10)},
        {'backend_web_server1',}
    )

  def test_balancer_set_cookie(self) -> None:
    # if backend provides a "SERVERID" cookie, balancer will overwrite it with the
    # backend selected by balancing algorithm
    self.assertIn(
        requests.get(urllib.parse.urljoin(self.default_balancer_url, '/set_cookie'), verify=False).cookies['SERVERID'],
        ('default-0', 'default-1'),
    )

  def test_balancer_respects_sticky_cookie(self) -> None:
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
            self.default_balancer_url,
        ]),
        b'1.1',
    )

  def test_keep_alive(self) -> None:
    # when doing two requests, connection is established only once
    with requests.Session() as session:
      session.verify = False

      # do a first request, which establish a first connection
      session.get(self.default_balancer_url).raise_for_status()

      # "break" new connection method and check we can make another request
      with mock.patch(
          "requests.packages.urllib3.connectionpool.HTTPSConnectionPool._new_conn",
      ) as new_conn:
        session.get(self.default_balancer_url).raise_for_status()
      new_conn.assert_not_called()

      parsed_url = urllib.parse.urlparse(self.default_balancer_url)

      # check that we have an open file for the ip connection
      self.assertTrue([
          c for c in psutil.Process(os.getpid()).connections()
          if c.status == 'ESTABLISHED' and c.raddr.ip == parsed_url.hostname
          and c.raddr.port == parsed_url.port
      ])


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
      content_type = self.path[1:]
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

  # Disabled test until we can rework on it for apache, or drop
  # apache on the backend.
  def disabled_test_gzip_encoding(self) -> None:
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
      resp = requests.get(urllib.parse.urljoin(self.default_balancer_url, content_type), verify=False)
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



class TestServerTLSProvidedCertificate(BalancerTestCase):
  """Check that certificate and key can be provided as instance parameters.
  """
  __partition_reference__ = 's'

  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    server_caucase = cls.getManagedResource('server_caucase', CaucaseService)
    server_certificate = cls.getManagedResource('server_certificate', CaucaseCertificate)
    server_certificate.request(cls._ipv4_address, server_caucase)
    parameter_dict = super()._getInstanceParameterDict()
    with open(server_certificate.cert_file) as f:
      parameter_dict['ssl']['cert'] = f.read()
    with open(server_certificate.key_file) as f:
      parameter_dict['ssl']['key'] = f.read()
    return parameter_dict

  def test_certificate_validates_with_provided_ca(self) -> None:
    server_certificate = self.getManagedResource("server_certificate", CaucaseCertificate)
    requests.get(self.default_balancer_url, verify=server_certificate.ca_crt_file)

