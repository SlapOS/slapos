##############################################################################
#
# Copyright (c) 2018 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

# Note for SSL
#  This test comes with certificates and keys. There is even root Certificate
#  Authority, for the backends
#  Please follow https://datacenteroverlords.com/2012/03/01/\
#     creating-your-own-ssl-certificate-authority/
#  in order to add more certificates for backend.
#  Frontend still uses self-signed certificates.

import glob
import os
import requests
from requests_toolbelt.adapters import source
import json
import multiprocessing
import subprocess
from unittest import skipIf, skip
import ssl
from BaseHTTPServer import HTTPServer
from forcediphttpsadapter.adapters import ForcedIPHTTPSAdapter
import time

import utils


# ports chosen to not collide with test systems
HTTP_PORT = '11080'
HTTPS_PORT = '11443'
NGINX_HTTP_PORT = '12080'
NGINX_HTTPS_PORT = '12443'
MONITOR_HTTPD_PORT = '13000'
MONITOR_F1_HTTPD_PORT = '13001'
MONITOR_F2_HTTPD_PORT = '13002'


if os.environ['TEST_SR'].endswith('caddy-frontend/software.cfg'):
  IS_CADDY = True
else:
  IS_CADDY = False

# response_code difference
if IS_CADDY:
  no_backend_response_code = 404
else:
  no_backend_response_code = 502

caddy_custom_https = '''# caddy_custom_https_filled_in_accepted
https://caddycustomhttpsaccepted.example.com:%%(https_port)s {
  bind %%(local_ipv4)s
  tls %%(ssl_crt)s %%(ssl_key)s

  log / %%(access_log)s {combined}
  errors %%(error_log)s

  proxy / %(url)s {
    transparent
    timeout 600s
    insecure_skip_verify
  }
}
'''
caddy_custom_http = '''# caddy_custom_http_filled_in_accepted
http://caddycustomhttpsaccepted.example.com:%%(http_port)s {
  bind %%(local_ipv4)s
  log / %%(access_log)s {combined}
  errors %%(error_log)s

  proxy / %(url)s {
    transparent
    timeout 600s
    insecure_skip_verify
  }
}
'''

# apache_custom_http[s] difference
if IS_CADDY:
  LOG_REGEXP = '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3} SOME_REMOTE_USER ' \
      '\[\d{2}\/.{3}\/\d{4}\:\d{2}\:\d{2}\:\d{2} \+\d{4}\] ' \
      '"GET \/test-path HTTP\/1.1" 404 \d+ "-" "python-requests.*" \d+'
  apache_custom_https = '''# apache_custom_https_filled_in_accepted
https://apachecustomhttpsaccepted.example.com:%%(https_port)s {
  bind %%(local_ipv4)s
  tls %%(ssl_crt)s %%(ssl_key)s

  log / %%(access_log)s {combined}
  errors %%(error_log)s

  proxy / %(url)s {
    transparent
    timeout 600s
    insecure_skip_verify
  }
}
'''
  apache_custom_http = '''# apache_custom_http_filled_in_accepted
http://apachecustomhttpsaccepted.example.com:%%(http_port)s {
  bind %%(local_ipv4)s
  log / %%(access_log)s {combined}
  errors %%(error_log)s

  proxy / %(url)s {
    transparent
    timeout 600s
    insecure_skip_verify
  }
}
'''
else:
  LOG_REGEXP = '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3} - - ' \
      '\[\d{2}\/.{3}\/\d{4}\:\d{2}\:\d{2}\:\d{2} \+\d{4}\] ' \
      '"GET \/test-path HTTP\/1.1" 502 \d+ "-" "python-requests.*" \d+'
  apache_custom_https = '''# apache_custom_https_filled_in_accepted
ServerName apachecustomhttpsaccepted.example.com
ServerAlias apachecustomhttpsaccepted.example.com
SSLEngine on
SSLProxyEngine on

ErrorLog %%(error_log)s
LogLevel notice
CustomLog %%(access_log)s combined

# Rewrite part
ProxyPreserveHost On
ProxyTimeout 600
RewriteEngine On

RewriteRule ^/(.*)$ %(url)s/$1 [L,P]
'''
  apache_custom_http = '''# apache_custom_http_filled_in_accpeted
ServerName apachecustomhttpsaccepted.example.com
ServerAlias apachecustomhttpsaccepted.example.com

ErrorLog %%(error_log)s
LogLevel notice
CustomLog %%(access_log)s combined

# Rewrite part
ProxyPreserveHost On
ProxyTimeout 600
RewriteEngine On

RewriteRule ^/(.*)$ %(url)s/$1 [L,P]
'''

# for development: debugging logs and install Ctrl+C handler
if os.environ.get('DEBUG'):
  import logging
  logging.basicConfig(level=logging.DEBUG)
  import unittest
  unittest.installHandler()


def isHTTP2(domain, ip):
  curl_command = '%(curl)s --http2 -v -k -H "Host: %(domain)s" ' \
    'https://%(domain)s:%(https_port)s/ '\
    '--resolve %(domain)s:%(https_port)s:%(ip)s' % dict(
      ip=ip, domain=domain, curl=os.environ['CURL'], https_port=HTTPS_PORT)
  prc = subprocess.Popen(
    curl_command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
  )
  out, err = prc.communicate()
  assert prc.returncode == 0, "Problem running %r. Output:\n%s\nError:\n%s" % (
    curl_command, out, err)
  return 'Using HTTP2, server supports multi-use' in err


class TestDataMixin(object):
  def getTrimmedProcessInfo(self):
    return '\n'.join(sorted([
      '%(group)s:%(name)s %(statename)s' % q for q
      in self.getSupervisorRPCServer().supervisor.getAllProcessInfo()]))

  def assertTestData(self, runtime_data):
    filename = '%s-%s.txt' % (self.id(), self.frontend_type)
    test_data_file = os.path.join(
      os.path.dirname(os.path.realpath(__file__)), 'test_data', filename)

    try:
      test_data = open(test_data_file).read().strip()
    except IOError:
      test_data = ''

    maxDiff = self.maxDiff
    self.maxDiff = None
    try:
      self.assertMultiLineEqual(
        test_data,
        runtime_data
      )
    except AssertionError:
      if os.environ.get('SAVE_TEST_DATA', '0') == '1':
        open(test_data_file, 'w').write(runtime_data.strip())
      raise
    finally:
      self.maxDiff = maxDiff

  def test_promise_list(self):
    runtime_data = '\n'.join(sorted([
      q[len(self.instance_path) + 1:]
      for q in glob.glob(os.path.join(
        self.instance_path, '*', 'etc', 'promise', '*'))]))

    self.assertTestData(runtime_data)

  def test_monitor_promise_list(self):
    runtime_data = '\n'.join(sorted([
      q[len(self.instance_path) + 1:]
      for q in glob.glob(os.path.join(
        self.instance_path, '*', 'etc', 'monitor-promise', '*'))]))
    self.assertTestData(runtime_data)

  def _test_file_list(self, slave_dir, IGNORE_PATH_LIST):
    runtime_data = []
    for slave_var in glob.glob(os.path.join(self.instance_path, '*', 'var')):
      for entry in os.walk(os.path.join(slave_var, slave_dir)):
        for filename in entry[2]:
          path = os.path.join(
            entry[0][len(self.instance_path) + 1:], filename)
          if not any([path.endswith(q) for q in IGNORE_PATH_LIST]):
            runtime_data.append(path)
    runtime_data = '\n'.join(sorted(runtime_data))
    self.assertTestData(runtime_data)

  def test_file_list_log(self):
    self._test_file_list('log', [
      # appears late, not needed for assertion
      'trafficserver/diags.log',
      'trafficserver/squid.blog',
      'trafficserver/.squid.blog.meta',
    ])

  def test_file_list_run(self):
    self._test_file_list('run', [
      # run by cron from time to time
      'monitor/monitor-collect.pid',
    ])

  @skipIf(not IS_CADDY, 'Feature not needed for Apache')
  def test_supervisor_state(self):
    # give a chance for etc/run scripts to finish
    time.sleep(1)
    runtime_data = self.getTrimmedProcessInfo()
    self.assertTestData(runtime_data)


class HttpFrontendTestCase(utils.SlapOSInstanceTestCase):
  frontend_type = 'CADDY' if IS_CADDY else 'APACHE'

  def assertLogAccessUrlWithPop(self, parameter_dict, reference):
    log_access_url = parameter_dict.pop('log-access-url')
    try:
      log_access_url_json = json.loads(log_access_url)
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (log_access_url,))

    self.assertTrue(len(log_access_url_json) >= 1)
    # check only the first one, as second frontend will be stopped
    log_access = log_access_url_json[0]
    entry = log_access.split(': ')
    if len(entry) != 2:
      self.fail('Cannot parse %r' % (log_access,))
    frontend, url = entry
    result = requests.get(url, verify=False)
    self.assertEqual(
      result.status_code,
      200,
      'While accessing %r of %r the status code was %r' % (
        url, frontend, result.status_code))

  def assertKeyWithPop(self, key, d):
    self.assertTrue(key in d, 'Key %r is missing in %r' % (key, d))
    d.pop(key)

  def assertEqualResultJson(self, result, key, value):
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertTrue(key in j, 'No key %r in %s' % (key, j))
    self.assertEqual(j[key], value)


class TestMasterRequest(HttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
    }

  def test(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertEqual(
      {
        'monitor-base-url': None,
        'domain': 'None',
        'accepted-slave-amount': '0',
        'rejected-slave-amount': '0',
        'slave-amount': '0',
        'rejected-slave-list': '[]'},
      parameter_dict
    )

  @skip('Feature postponed')
  def test_caddy_key_caddy_certificate(self):
    # Caddy: Need to use caddy_key and caddy_certificate with backward
    #        compatilibty to apache_key and apache_certificate
    raise NotImplementedError


class TestMasterRequestDomain(HttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
    }

  def test(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)

    self.assertEqual(
      {
        'monitor-base-url': None,
        'domain': 'example.com',
        'accepted-slave-amount': '0',
        'rejected-slave-amount': '0',
        'slave-amount': '0',
        'rejected-slave-list': '[]'
      },
      parameter_dict
    )


class SlaveHttpFrontendTestCase(HttpFrontendTestCase):
  @classmethod
  def startServerProcess(cls):
    server = HTTPServer(
      (utils.LOCAL_IPV4, utils.findFreeTCPPort(utils.LOCAL_IPV4)),
      utils.TestHandler)

    server_https = HTTPServer(
      (utils.LOCAL_IPV4, utils.findFreeTCPPort(utils.LOCAL_IPV4)),
      utils.TestHandler)

    server_https.socket = ssl.wrap_socket(
      server_https.socket,
      certfile=os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'testserver.example.com.pem'),
      server_side=True)

    cls.backend_url = 'http://%s:%s' % server.server_address
    cls.server_process = multiprocessing.Process(target=server.serve_forever)
    cls.server_process.start()
    cls.backend_https_url = 'https://%s:%s' % server_https.server_address
    cls.server_https_process = multiprocessing.Process(
      target=server_https.serve_forever)
    cls.server_https_process.start()

  @classmethod
  def stopServerProcess(cls):
    cls.server_process.terminate()
    cls.server_https_process.terminate()

  @classmethod
  def setUpSlaves(cls):
    cls.slave_connection_parameter_dict_dict = {}
    request = cls.slapos_controler.slap.registerOpenOrder().request
    for slave_reference, partition_parameter_kw in cls\
            .getSlaveParameterDictDict().items():
      slave_instance = request(
        software_release=cls.software_url_list[0],
        partition_reference=slave_reference,
        partition_parameter_kw=partition_parameter_kw,
        shared=True
      )
    cls.runComputerPartition()
    for slave_reference, partition_parameter_kw in cls\
            .getSlaveParameterDictDict().items():
      slave_instance = request(
        software_release=cls.software_url_list[0],
        partition_reference=slave_reference,
        partition_parameter_kw=partition_parameter_kw,
        shared=True
      )
      cls.slave_connection_parameter_dict_dict[slave_reference] = \
          slave_instance.getConnectionParameterDict()

  @classmethod
  def setUpClass(cls):
    try:
      cls.startServerProcess()
      super(SlaveHttpFrontendTestCase, cls).setUpClass()
      cls.setUpSlaves()
    except Exception:
      cls.tearDownClass()
      raise

  @classmethod
  def tearDownClass(cls):
    super(SlaveHttpFrontendTestCase, cls).tearDownClass()
    cls.stopServerProcess()

  def fakeHTTPSResult(self, domain, real_ip, path, port=HTTPS_PORT,
                      headers=None, cookies=None, source_ip=None):
    if headers is None:
      headers = {}
    headers.setdefault('REMOTE_USER', 'SOME_REMOTE_USER')
    session = requests.Session()
    session.mount(
      'https://%s:%s' % (domain, port),
      ForcedIPHTTPSAdapter(
        dest_ip=real_ip))
    if source_ip is not None:
      new_source = source.SourceAddressAdapter(source_ip)
      session.mount('http://', new_source)
      session.mount('https://', new_source)
    return session.get(
      'https://%s:%s/%s' % (domain, port, path),
      verify='example.com.root.ca.crt',
      allow_redirects=False,
      headers=headers,
      cookies=cookies
    )

  def fakeHTTPResult(self, domain, real_ip, path, port=HTTP_PORT,
                     headers=None):
    if headers is None:
      headers = {}
    headers.setdefault('REMOTE_USER', 'SOME_REMOTE_USER')
    headers['Host'] = domain
    return requests.get(
      'http://%s:%s/%s' % (real_ip, port, path),
      headers=headers,
      allow_redirects=False,
    )

  def patchRequests(self):
    HTTPResponse = requests.packages.urllib3.response.HTTPResponse
    HTTPResponse.orig__init__ = HTTPResponse.__init__

    def new_HTTPResponse__init__(self, *args, **kwargs):
      self.orig__init__(*args, **kwargs)
      try:
        self.peercert = self._connection.sock.getpeercert(binary_form=True)
      except AttributeError:
        pass
    HTTPResponse.__init__ = new_HTTPResponse__init__

    HTTPAdapter = requests.adapters.HTTPAdapter
    HTTPAdapter.orig_build_response = HTTPAdapter.build_response

    def new_HTTPAdapter_build_response(self, request, resp):
      response = self.orig_build_response(request, resp)
      try:
        response.peercert = resp.peercert
      except AttributeError:
        pass
      return response
    HTTPAdapter.build_response = new_HTTPAdapter_build_response

  def unpatchRequests(self):
    HTTPResponse = requests.packages.urllib3.response.HTTPResponse
    if getattr(HTTPResponse, 'orig__init__', None) is not None:
      HTTPResponse.__init__ = HTTPResponse.orig__init__
      del(HTTPResponse.orig__init__)

    HTTPAdapter = requests.adapters.HTTPAdapter
    if getattr(HTTPAdapter, 'orig_build_response', None) is not None:
      HTTPAdapter.build_response = HTTPAdapter.orig_build_response
      del(HTTPAdapter.orig_build_response)

  def setUp(self):
    # patch requests in order to being able to extract SSL certs
    self.patchRequests()

  def tearDown(self):
    self.unpatchRequests()


class TestSlave(SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'nginx-domain': 'nginx.example.com',
      'public-ipv4': utils.LOCAL_IPV4,
      'apache-certificate': open('wildcard.example.com.crt').read(),
      'apache-ca-certificate': open('example.com.root.ca.crt').read(),
      'apache-key': open('wildcard.example.com.key').read(),
      '-frontend-authorized-slave-string':
      '_apache_custom_http_s-accepted _caddy_custom_http_s-accepted',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'empty': {
      },
      'url': {
        'url': cls.backend_url,
      },
      'url_https-url': {
        'url': cls.backend_url + '/http',
        'https-url': cls.backend_url + '/https',
      },
      'server-alias': {
        'url': cls.backend_url,
        'server-alias': 'alias1.example.com alias2.example.com',
      },
      'ssl-proxy-verify_ssl_proxy_ca_crt': {
        'url': cls.backend_https_url,
        'ssl-proxy-verify': True,
        'ssl_proxy_ca_crt': open('testserver.root.ca.crt').read(),
      },
      'ssl-proxy-verify-unverified': {
        'url': cls.backend_https_url,
        'ssl-proxy-verify': True,
      },
      'https-only': {
        'url': cls.backend_url,
        'https-only': True,
      },
      'custom_domain': {
        'url': cls.backend_url,
        'custom_domain': 'customdomain.example.com',
      },
      'custom_domain_ssl_crt_ssl_key': {
        'url': cls.backend_url,
        'custom_domain': 'customdomainsslcrtsslkey.example.com',
        'ssl_crt': open('customdomainsslcrtsslkey.example.com.crt').read(),
        'ssl_ca_crt': open('example.com.root.ca.crt').read(),
        'ssl_key': open('customdomainsslcrtsslkey.example.com.key').read(),
      },
      'type-zope': {
        'url': cls.backend_url,
        'type': 'zope',
      },
      'type-zope-ssl-proxy-verify_ssl_proxy_ca_crt': {
        'url': cls.backend_https_url,
        'type': 'zope',
        'ssl-proxy-verify': True,
        'ssl_proxy_ca_crt': open('testserver.root.ca.crt').read(),
      },
      'type-zope-ssl-proxy-verify-unverified': {
        'url': cls.backend_https_url,
        'type': 'zope',
        'ssl-proxy-verify': True,
      },
      'type-zope-virtualhostroot-http-port': {
        'url': cls.backend_url,
        'type': 'zope',
        'virtualhostroot-http-port': '12345'
      },
      'type-zope-virtualhostroot-https-port': {
        'url': cls.backend_url,
        'type': 'zope',
        'virtualhostroot-https-port': '12345'
      },
      'type-zope-path': {
        'url': cls.backend_url,
        'type': 'zope',
        'path': 'path',
      },
      'type-zope-default-path': {
        'url': cls.backend_url,
        'type': 'zope',
        'default-path': 'default-path',
      },
      'type-notebook': {
        'url': cls.backend_url,
        'type': 'notebook',
      },
      'type-eventsource': {
        'url': cls.backend_url,
        'type': 'eventsource',
      },
      'type-redirect': {
        'url': cls.backend_url,
        'type': 'redirect',
      },
      'enable_cache': {
        'url': cls.backend_url,
        'enable_cache': True,
      },
      'enable_cache-disable-no-cache-request': {
        'url': cls.backend_url,
        'enable_cache': True,
        'disable-no-cache-request': True,
      },
      'enable_cache-disable-via-header': {
        'url': cls.backend_url,
        'enable_cache': True,
        'disable-via-header': True,
      },
      'enable-http2-false': {
        'url': cls.backend_url,
        'enable-http2': False,
      },
      'enable_cache-ssl-proxy-verify-unverified': {
        'url': cls.backend_https_url,
        'enable_cache': True,
        'ssl-proxy-verify': True,
      },
      'enable_cache-ssl-proxy-verify_ssl_proxy_ca_crt': {
        'url': cls.backend_https_url,
        'enable_cache': True,
        'ssl_proxy_ca_crt': open('testserver.root.ca.crt').read(),
        'ssl-proxy-verify': True,
      },
      'enable-http2-default': {
        'url': cls.backend_url,
      },
      'apache_custom_http_s-rejected': {
        'url': cls.backend_url,
        'apache_custom_https': '# apache_custom_https_filled_in_rejected',
        'apache_custom_http': '# apache_custom_http_filled_in_rejected',
      },
      'apache_custom_http_s-accepted': {
        'url': cls.backend_url,
        'apache_custom_https': apache_custom_https % dict(url=cls.backend_url),
        'apache_custom_http': apache_custom_http % dict(url=cls.backend_url),
      },
      'caddy_custom_http_s-rejected': {
        'url': cls.backend_url,
        'caddy_custom_https': '# caddy_custom_https_filled_in_rejected',
        'caddy_custom_http': '# caddy_custom_http_filled_in_rejected',
      },
      'caddy_custom_http_s-accepted': {
        'url': cls.backend_url,
        'caddy_custom_https': caddy_custom_https % dict(url=cls.backend_url),
        'caddy_custom_http': caddy_custom_http % dict(url=cls.backend_url),
      },
      'prefer-gzip-encoding-to-backend': {
        'url': cls.backend_url,
        'prefer-gzip-encoding-to-backend': 'true',
      },
      'disabled-cookie-list': {
        'url': cls.backend_url,
        'disabled-cookie-list': 'Chocolate Vanilia',
      },
      'monitor-ipv4-test': {
        'monitor-ipv4-test': 'monitor-ipv4-test',
      },
      'monitor-ipv6-test': {
        'monitor-ipv6-test': 'monitor-ipv6-test',
      },
      're6st-optimal-test': {
        're6st-optimal-test': 'ipv6,ipv4',
      }
    }

  def getMasterPartitionPath(self):
    # partition w/o etc/trafficserver, but with buildout.cfg
    return [
      q for q in glob.glob(os.path.join(self.instance_path, '*',))
      if not os.path.exists(os.path.join(q, 'etc', 'trafficserver')) and
      os.path.exists(os.path.join(q, 'buildout.cfg'))][0]

  def getSlavePartitionPath(self):
    # partition w/ etc/trafficserver
    return [
      q for q in glob.glob(os.path.join(self.instance_path, '*',))
      if os.path.exists(os.path.join(q, 'etc', 'trafficserver'))][0]

  def test_master_partition_state(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)

    self.assertEqual(
      {
        'monitor-base-url': None,
        'domain': 'example.com',
        'accepted-slave-amount': '33',
        'rejected-slave-amount': '2',
        'slave-amount': '35',
        'rejected-slave-list':
        '["_caddy_custom_http_s-rejected", "_apache_custom_http_s-rejected"]'},
      parameter_dict
    )

    partition_path = self.getMasterPartitionPath()

    self.assertEqual(
      set([
        'check-free-disk-space',
        'monitor-http-frontend',
        'monitor-httpd-listening-on-tcp',
        'promise-monitor-httpd-is-process-older-than-dependency-set',
      ]),
      set(os.listdir(os.path.join(partition_path, 'etc', 'promise'))))

    self.assertEqual(
      set(),
      set(os.listdir(os.path.join(partition_path, 'etc', 'monitor-promise'))))

  def test_empty(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'empty']
    self.assertLogAccessUrlWithPop(parameter_dict, 'empty')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'empty.example.com',
        'replication_number': '1',
        'url': 'http://empty.example.com',
        'site_url': 'http://empty.example.com',
        'secure_access': 'https://empty.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqual(result.status_code, no_backend_response_code)

    # check that log file contains verbose log
    log_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'var', 'log', 'httpd', '_empty_access_log'
      ))[0]

    self.assertRegexpMatches(
      open(log_file, 'r').read(),
      LOG_REGEXP)
    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(result_http.status_code, no_backend_response_code)

    # check that 404 is as configured
    result_missing = self.fakeHTTPSResult(
      'forsuredoesnotexists.example.com', parameter_dict['public-ipv4'], '')
    self.assertEqual(404, result_missing.status_code)
    self.assertEqual(
      """<html>
<head>
  <title>Instance not found</title>
</head>
<body>
<h1>This instance has not been found.</h1>
<p>If this error persists, please check your instance URL and status on S"""
      """lapOS Master.</p>
</body>
</html>
""",
      result_missing.text
    )

  def test_url(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'url'].copy()
    self.assertLogAccessUrlWithPop(parameter_dict, 'url')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'url.example.com',
        'replication_number': '1',
        'url': 'http://url.example.com',
        'site_url': 'http://url.example.com',
        'secure_access': 'https://url.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertFalse('remote_user' in j['Incoming Headers'].keys())

    self.assertEqual(
      result.headers['Content-Encoding'],
      'gzip'
    )

    self.assertEqual(
      result.headers['Set-Cookie'],
      'secured=value;secure, nonsecured=value'
    )

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqualResultJson(result_http, 'Path', '/test-path')

    try:
      j = result_http.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertFalse('remote_user' in j['Incoming Headers'].keys())

    self.assertEqual(
      result_http.headers['Content-Encoding'],
      'gzip'
    )

    self.assertEqual(
      result_http.headers['Set-Cookie'],
      'secured=value;secure, nonsecured=value'
    )

  @skipIf(IS_CADDY, 'Feature postponed')
  def test_url_ipv6_access(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'url'].copy()
    self.assertLogAccessUrlWithPop(parameter_dict, 'url')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'url.example.com',
        'replication_number': '1',
        'url': 'http://url.example.com',
        'site_url': 'http://url.example.com',
        'secure_access': 'https://url.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result_ipv6 = self.fakeHTTPSResult(
      parameter_dict['domain'], utils.GLOBAL_IPV6, 'test-path',
      source_ip=utils.GLOBAL_IPV6)

    self.assertEqual(
       result_ipv6.json()['Incoming Headers']['x-forwarded-for'],
       utils.GLOBAL_IPV6
    )

    self.assertEqual(
      utils.der2pem(result_ipv6.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result_ipv6, 'Path', '/test-path')

  def test_type_zope_path(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'type-zope-path']
    self.assertLogAccessUrlWithPop(parameter_dict, 'type-zope-path')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'typezopepath.example.com',
        'replication_number': '1',
        'url': 'http://typezopepath.example.com',
        'site_url': 'http://typezopepath.example.com',
        'secure_access': 'https://typezopepath.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//'
      'typezopepath.example.com:443/path/VirtualHostRoot/test-path'
    )

  def test_type_zope_default_path(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'type-zope-default-path']
    self.assertLogAccessUrlWithPop(parameter_dict, 'type-zope-default-path')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'typezopedefaultpath.example.com',
        'replication_number': '1',
        'url': 'http://typezopedefaultpath.example.com',
        'site_url': 'http://typezopedefaultpath.example.com',
        'secure_access': 'https://typezopedefaultpath.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], '')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqual(
      result.headers['Location'],
      'https://typezopedefaultpath.example.com:%s/default-path' % (HTTPS_PORT,)
    )

  def test_server_alias(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'server-alias']
    self.assertLogAccessUrlWithPop(parameter_dict, 'server-alias')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'serveralias.example.com',
        'replication_number': '1',
        'url': 'http://serveralias.example.com',
        'site_url': 'http://serveralias.example.com',
        'secure_access': 'https://serveralias.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = self.fakeHTTPSResult(
      'alias1.example.com', parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = self.fakeHTTPSResult(
      'alias2.example.com', parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

  @skip('Feature postponed')
  def test_check_error_log(self):
    # Caddy: Need to implement similar thing like check-error-on-apache-log
    raise NotImplementedError(self.id())

  @skip('Feature postponed')
  def test_ssl_ca_crt(self):
    raise NotImplementedError(self.id())

  @skip('Feature postponed')
  def test_path_to_ssl_ca_crt(self):
    raise NotImplementedError(self.id())

  def test_https_only(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'https-only']
    self.assertLogAccessUrlWithPop(parameter_dict, 'https-only')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'httpsonly.example.com',
        'replication_number': '1',
        'url': 'http://httpsonly.example.com',
        'site_url': 'http://httpsonly.example.com',
        'secure_access': 'https://httpsonly.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      result_http.headers['Location'],
      'https://httpsonly.example.com/test-path'
    )

  def test_custom_domain(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'custom_domain']
    self.assertLogAccessUrlWithPop(parameter_dict, 'custom_domain')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'customdomain.example.com',
        'replication_number': '1',
        'url': 'http://customdomain.example.com',
        'site_url': 'http://customdomain.example.com',
        'secure_access': 'https://customdomain.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_custom_domain_ssl_crt_ssl_key(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'custom_domain_ssl_crt_ssl_key']
    self.assertLogAccessUrlWithPop(parameter_dict, 'custom_domain_ssl_crt_key')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'customdomainsslcrtsslkey.example.com',
        'replication_number': '1',
        'url': 'http://customdomainsslcrtsslkey.example.com',
        'site_url': 'http://customdomainsslcrtsslkey.example.com',
        'secure_access': 'https://customdomainsslcrtsslkey.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('customdomainsslcrtsslkey.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_type_zope(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'type-zope']
    self.assertLogAccessUrlWithPop(parameter_dict, 'type-zope')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'typezope.example.com',
        'replication_number': '1',
        'url': 'http://typezope.example.com',
        'site_url': 'http://typezope.example.com',
        'secure_access': 'https://typezope.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertFalse('remote_user' in j['Incoming Headers'].keys())

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//typezope.example.com:443/'
      '/VirtualHostRoot/test-path'
    )

    result = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/http//typezope.example.com:80/'
      '/VirtualHostRoot/test-path'
    )

  def test_type_zope_virtualhostroot_http_port(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'type-zope-virtualhostroot-http-port']
    self.assertLogAccessUrlWithPop(
      parameter_dict, 'type-zope-virtualhostroot-http-port')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'typezopevirtualhostroothttpport.example.com',
        'replication_number': '1',
        'url': 'http://typezopevirtualhostroothttpport.example.com',
        'site_url': 'http://typezopevirtualhostroothttpport.example.com',
        'secure_access':
        'https://typezopevirtualhostroothttpport.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/http//typezopevirtualhostroothttpport'
      '.example.com:12345//VirtualHostRoot/test-path'
    )

  def test_type_zope_virtualhostroot_https_port(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'type-zope-virtualhostroot-https-port']
    self.assertLogAccessUrlWithPop(
      parameter_dict, 'type-zope-virtualhostroot-https-port')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'typezopevirtualhostroothttpsport.example.com',
        'replication_number': '1',
        'url': 'http://typezopevirtualhostroothttpsport.example.com',
        'site_url': 'http://typezopevirtualhostroothttpsport.example.com',
        'secure_access':
        'https://typezopevirtualhostroothttpsport.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//typezopevirtualhostroothttpsport'
      '.example.com:12345//VirtualHostRoot/test-path'
    )

  def test_type_notebook(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'type-notebook']
    self.assertLogAccessUrlWithPop(parameter_dict, 'type-notebook')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'typenotebook.nginx.example.com',
        'replication_number': '1',
        'url': 'http://typenotebook.nginx.example.com',
        'site_url': 'http://typenotebook.nginx.example.com',
        'secure_access': 'https://typenotebook.nginx.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      NGINX_HTTPS_PORT)

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

  @skip('Feature postponed')
  def test_type_websocket(self):
    # Pure websocket configurable frontend
    raise NotImplementedError

  @skip('Feature postponed')
  def test_apache_ca_certificate(self):
    # merge with apache-certificate
    raise NotImplementedError

  @skipIf(IS_CADDY, 'Feature postponed')
  def test_type_eventsource(self):
    # Caddy: For event source, if I understand
    #        https://github.com/mholt/caddy/issues/1355 correctly, we could use
    #        Caddy as a proxy in front of nginx-push-stream . If we have a
    #        "central shared" caddy instance, can it handle keeping connections
    #        opens for many clients ?
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'type-eventsource']
    self.assertLogAccessUrlWithPop(parameter_dict, 'type-eventsource')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'typeeventsource.nginx.example.com',
        'replication_number': '1',
        'url': 'http://typeeventsource.nginx.example.com',
        'site_url': 'http://typeeventsource.nginx.example.com',
        'secure_access': 'https://typeeventsource.nginx.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'pub',
      NGINX_HTTPS_PORT)

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqual(
      result.content,
      ''
    )
    headers = result.headers.copy()
    self.assertKeyWithPop('Expires', headers)
    self.assertKeyWithPop('Date', headers)
    self.assertEqual(
      headers,
      {
        'X-Nginx-PushStream-Explain': 'No channel id provided.',
        'Content-Length': '0',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Connection': 'keep-alive',
        'Server': 'nginx'
      }
    )

  def test_type_redirect(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'type-redirect']
    self.assertLogAccessUrlWithPop(parameter_dict, 'type-redirect')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'typeredirect.example.com',
        'replication_number': '1',
        'url': 'http://typeredirect.example.com',
        'site_url': 'http://typeredirect.example.com',
        'secure_access': 'https://typeredirect.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqual(
      result.headers['Location'],
      '%s/test-path' % (self.backend_url,)
    )

  def test_ssl_proxy_verify_ssl_proxy_ca_crt(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'ssl-proxy-verify_ssl_proxy_ca_crt']

    self.assertLogAccessUrlWithPop(
      parameter_dict, 'ssl-proxy-verify_ssl_proxy_ca_crt')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'sslproxyverifysslproxycacrt.example.com',
        'replication_number': '1',
        'url': 'http://sslproxyverifysslproxycacrt.example.com',
        'site_url': 'http://sslproxyverifysslproxycacrt.example.com',
        'secure_access': 'https://sslproxyverifysslproxycacrt.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    if IS_CADDY:
      self.assertEqual(
        result.status_code,
        501
      )

      result_http = self.fakeHTTPResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

      self.assertEqual(
        result_http.status_code,
        501
      )
    else:
      self.assertEqualResultJson(result, 'Path', '/test-path')

      try:
        j = result.json()
      except Exception:
        raise ValueError('JSON decode problem in:\n%s' % (result.text,))
      self.assertFalse('remote_user' in j['Incoming Headers'].keys())

      self.assertEqual(
        result.headers['Content-Encoding'],
        'gzip'
      )

      self.assertEqual(
        result.headers['Set-Cookie'],
        'secured=value;secure, nonsecured=value'
      )

      result_http = self.fakeHTTPResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
      self.assertEqualResultJson(result_http, 'Path', '/test-path')

      try:
        j = result_http.json()
      except Exception:
        raise ValueError('JSON decode problem in:\n%s' % (result.text,))
      self.assertFalse('remote_user' in j['Incoming Headers'].keys())

      self.assertEqual(
        result_http.headers['Content-Encoding'],
        'gzip'
      )

      self.assertEqual(
        result_http.headers['Set-Cookie'],
        'secured=value;secure, nonsecured=value'
      )

  def test_ssl_proxy_verify_unverified(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'ssl-proxy-verify-unverified']

    self.assertLogAccessUrlWithPop(
      parameter_dict, 'ssl-proxy-verify-unverified')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'sslproxyverifyunverified.example.com',
        'replication_number': '1',
        'url': 'http://sslproxyverifyunverified.example.com',
        'site_url': 'http://sslproxyverifyunverified.example.com',
        'secure_access': 'https://sslproxyverifyunverified.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqual(
      result.status_code,
      502
    )

  def test_enable_cache_ssl_proxy_verify_ssl_proxy_ca_crt(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable_cache-ssl-proxy-verify_ssl_proxy_ca_crt']

    self.assertLogAccessUrlWithPop(
      parameter_dict, 'enable_cache-ssl-proxy-verify_ssl_proxy_ca_crt')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablecachesslproxyverifysslproxycacrt.example.com',
        'replication_number': '1',
        'url': 'http://enablecachesslproxyverifysslproxycacrt.example.com',
        'site_url':
        'http://enablecachesslproxyverifysslproxycacrt.example.com',
        'secure_access':
        'https://enablecachesslproxyverifysslproxycacrt.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    if IS_CADDY:
      self.assertEqual(
        result.status_code,
        501
      )

      result_http = self.fakeHTTPResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

      self.assertEqual(
        result_http.status_code,
        501
      )
    else:
      self.assertEqualResultJson(result, 'Path', '/test-path')

      headers = result.headers.copy()

      self.assertKeyWithPop('Via', headers)
      self.assertKeyWithPop('Server', headers)
      self.assertKeyWithPop('Date', headers)

      # drop keys appearing randomly in headers
      headers.pop('Transfer-Encoding', None)
      headers.pop('Content-Length', None)
      headers.pop('Connection', None)
      headers.pop('Keep-Alive', None)

      self.assertEqual(
        headers,
        {'Age': '0', 'Content-type': 'application/json',
         'Set-Cookie': 'secured=value;secure, nonsecured=value'}
      )

      result_http = self.fakeHTTPResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

      self.assertEqualResultJson(result_http, 'Path', '/test-path')

      headers = result_http.headers.copy()

      self.assertKeyWithPop('Via', headers)
      self.assertKeyWithPop('Server', headers)
      self.assertKeyWithPop('Date', headers)

      # drop keys appearing randomly in headers
      headers.pop('Transfer-Encoding', None)
      headers.pop('Content-Length', None)
      headers.pop('Connection', None)
      headers.pop('Keep-Alive', None)

      self.assertEqual(
        headers,
        {'Age': '0', 'Content-type': 'application/json',
         'Set-Cookie': 'secured=value;secure, nonsecured=value'}
      )

  def test_enable_cache_ssl_proxy_verify_unverified(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable_cache-ssl-proxy-verify-unverified']

    self.assertLogAccessUrlWithPop(
      parameter_dict, 'enable_cache-ssl-proxy-verify-unverified')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablecachesslproxyverifyunverified.example.com',
        'replication_number': '1',
        'url': 'http://enablecachesslproxyverifyunverified.example.com',
        'site_url': 'http://enablecachesslproxyverifyunverified.example.com',
        'secure_access':
        'https://enablecachesslproxyverifyunverified.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqual(
      result.status_code,
      502
    )

  def test_type_zope_ssl_proxy_verify_ssl_proxy_ca_crt(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'type-zope-ssl-proxy-verify_ssl_proxy_ca_crt']

    self.assertLogAccessUrlWithPop(
      parameter_dict, 'type-zope-ssl-proxy-verify_ssl_proxy_ca_crt')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'typezopesslproxyverifysslproxycacrt.example.com',
        'replication_number': '1',
        'url': 'http://typezopesslproxyverifysslproxycacrt.example.com',
        'site_url': 'http://typezopesslproxyverifysslproxycacrt.example.com',
        'secure_access':
        'https://typezopesslproxyverifysslproxycacrt.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    if IS_CADDY:
      self.assertEqual(
        result.status_code,
        501
      )

      result_http = self.fakeHTTPResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

      self.assertEqual(
        result_http.status_code,
        501
      )
    else:
      try:
        j = result.json()
      except Exception:
        raise ValueError('JSON decode problem in:\n%s' % (result.text,))
      self.assertFalse('remote_user' in j['Incoming Headers'].keys())

      self.assertEqualResultJson(
        result,
        'Path',
        '/VirtualHostBase/https//typezopesslproxyverifysslproxycacrt.example'
        '.com:443//VirtualHostRoot/test-path'
      )

      result = self.fakeHTTPResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

      self.assertEqualResultJson(
        result,
        'Path',
        '/VirtualHostBase/http//typezopesslproxyverifysslproxycacrt.example'
        '.com:80//VirtualHostRoot/test-path'
      )

  def test_type_zope_ssl_proxy_verify_unverified(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'type-zope-ssl-proxy-verify-unverified']

    self.assertLogAccessUrlWithPop(
      parameter_dict, 'type-zope-ssl-proxy-verify-unverified')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'typezopesslproxyverifyunverified.example.com',
        'replication_number': '1',
        'url': 'http://typezopesslproxyverifyunverified.example.com',
        'site_url': 'http://typezopesslproxyverifyunverified.example.com',
        'secure_access':
        'https://typezopesslproxyverifyunverified.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqual(
      result.status_code,
      502
    )

  def test_monitor_ipv6_test(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'monitor-ipv6-test']
    self.assertLogAccessUrlWithPop(parameter_dict, 'monitor-ipv6-test')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'monitoripv6test.example.com',
        'replication_number': '1',
        'url': 'http://monitoripv6test.example.com',
        'site_url': 'http://monitoripv6test.example.com',
        'secure_access': 'https://monitoripv6test.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqual(result.status_code, no_backend_response_code)

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(result_http.status_code, no_backend_response_code)

    # rewrite SR/bin/is-icmp-packet-lost
    open(
      os.path.join(self.software_path, 'bin', 'is-icmp-packet-lost'), 'w'
    ).write('echo "$@"')
    # call the monitor for this partition
    monitor_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'monitor-promise',
        'check-_monitor-ipv6-test-ipv6-packet-list-test'))[0]
    self.assertEqual(
      '-a monitor-ipv6-test',
      subprocess.check_output(monitor_file).strip()
    )

  def test_monitor_ipv4_test(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'monitor-ipv4-test']
    self.assertLogAccessUrlWithPop(parameter_dict, 'monitor-ipv4-test')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'monitoripv4test.example.com',
        'replication_number': '1',
        'url': 'http://monitoripv4test.example.com',
        'site_url': 'http://monitoripv4test.example.com',
        'secure_access': 'https://monitoripv4test.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqual(result.status_code, no_backend_response_code)

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(result_http.status_code, no_backend_response_code)

    # rewrite SR/bin/is-icmp-packet-lost
    open(
      os.path.join(self.software_path, 'bin', 'is-icmp-packet-lost'), 'w'
    ).write('echo "$@"')
    # call the monitor for this partition
    monitor_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'monitor-promise',
        'check-_monitor-ipv4-test-ipv4-packet-list-test'))[0]
    self.assertEqual(
      '-4 -a monitor-ipv4-test',
      subprocess.check_output(monitor_file).strip()
    )

  def test_re6st_optimal_test(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      're6st-optimal-test']
    self.assertLogAccessUrlWithPop(parameter_dict, 're6st-optimal-test')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 're6stoptimaltest.example.com',
        'replication_number': '1',
        'url': 'http://re6stoptimaltest.example.com',
        'site_url': 'http://re6stoptimaltest.example.com',
        'secure_access': 'https://re6stoptimaltest.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqual(result.status_code, no_backend_response_code)

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(result_http.status_code, no_backend_response_code)

    # rewrite SR/bin/is-icmp-packet-lost
    open(
      os.path.join(
        self.software_path, 'bin', 'check-re6st-optimal-status'), 'w'
    ).write('echo "$@"')
    # call the monitor for this partition
    monitor_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'monitor-promise',
        'check-_re6st-optimal-test-re6st-optimal-test'))[0]
    self.assertEqual(
      '-4 ipv4 -6 ipv6',
      subprocess.check_output(monitor_file).strip()
    )

  def test_enable_cache(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable_cache']
    self.assertLogAccessUrlWithPop(parameter_dict, 'enable_cache')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablecache.example.com',
        'replication_number': '1',
        'url': 'http://enablecache.example.com',
        'site_url': 'http://enablecache.example.com',
        'secure_access': 'https://enablecache.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = result.headers.copy()

    self.assertKeyWithPop('Via', headers)
    self.assertKeyWithPop('Server', headers)
    self.assertKeyWithPop('Date', headers)

    # drop keys appearing randomly in headers
    headers.pop('Transfer-Encoding', None)
    headers.pop('Content-Length', None)
    headers.pop('Connection', None)
    headers.pop('Keep-Alive', None)

    self.assertEqual(
      headers,
      {'Age': '0', 'Content-type': 'application/json',
       'Set-Cookie': 'secured=value;secure, nonsecured=value',
       'Content-Encoding': 'gzip', 'Vary': 'Accept-Encoding'}
    )

    result_direct = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      port=26011)

    self.assertEqualResultJson(result_direct, 'Path', '/test-path')

    try:
      j = result_direct.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result_direct.text,))
    self.assertFalse('remote_user' in j['Incoming Headers'].keys())

    self.assertEqual(
      result_direct.headers['Content-Encoding'],
      'gzip'
    )

    self.assertEqual(
      result_direct.headers['Set-Cookie'],
      'secured=value;secure, nonsecured=value'
    )

    result_direct_https_backend = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      port=26012)

    self.assertEqualResultJson(
      result_direct_https_backend, 'Path', '/test-path')

    try:
      j = result_direct_https_backend.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (
        result_direct_https_backend.text,))
    self.assertFalse('remote_user' in j['Incoming Headers'].keys())

    self.assertEqual(
      result_direct_https_backend.headers['Content-Encoding'],
      'gzip'
    )

    self.assertEqual(
      result_direct_https_backend.headers['Set-Cookie'],
      'secured=value;secure, nonsecured=value'
    )

  def test_enable_cache_disable_no_cache_request(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable_cache-disable-no-cache-request']
    self.assertLogAccessUrlWithPop(
      parameter_dict, 'enable_cache-disable-no-cache-request')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablecachedisablenocacherequest.example.com',
        'replication_number': '1',
        'url': 'http://enablecachedisablenocacherequest.example.com',
        'site_url': 'http://enablecachedisablenocacherequest.example.com',
        'secure_access':
        'https://enablecachedisablenocacherequest.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      headers={'Pragma': 'no-cache', 'Cache-Control': 'something'})

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = result.headers.copy()

    self.assertKeyWithPop('Via', headers)
    self.assertKeyWithPop('Server', headers)
    self.assertKeyWithPop('Date', headers)

    # drop keys appearing randomly in headers
    headers.pop('Transfer-Encoding', None)
    headers.pop('Content-Length', None)
    headers.pop('Connection', None)
    headers.pop('Keep-Alive', None)

    self.assertEqual(
      headers,
      {'Age': '0', 'Content-type': 'application/json',
       'Set-Cookie': 'secured=value;secure, nonsecured=value',
       'Content-Encoding': 'gzip', 'Vary': 'Accept-Encoding'}
    )

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertFalse('pragma' in j['Incoming Headers'].keys())

  def test_enable_cache_disable_via_header(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable_cache-disable-via-header']
    self.assertLogAccessUrlWithPop(
      parameter_dict, 'enable_cache-disable-via-header')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablecachedisableviaheader.example.com',
        'replication_number': '1',
        'url': 'http://enablecachedisableviaheader.example.com',
        'site_url': 'http://enablecachedisableviaheader.example.com',
        'secure_access':
        'https://enablecachedisableviaheader.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = result.headers.copy()

    self.assertKeyWithPop('Server', headers)
    self.assertKeyWithPop('Date', headers)

    # drop keys appearing randomly in headers
    headers.pop('Transfer-Encoding', None)
    headers.pop('Content-Length', None)
    headers.pop('Connection', None)
    headers.pop('Keep-Alive', None)

    self.assertEqual(
      headers,
      {'Age': '0', 'Content-type': 'application/json',
       'Set-Cookie': 'secured=value;secure, nonsecured=value',
       'Content-Encoding': 'gzip', 'Vary': 'Accept-Encoding'}
    )

  def test_enable_http2_false(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable-http2-false']
    self.assertLogAccessUrlWithPop(parameter_dict, 'enable-http2-false')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablehttp2false.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2false.example.com',
        'site_url': 'http://enablehttp2false.example.com',
        'secure_access':
        'https://enablehttp2false.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = result.headers.copy()

    self.assertKeyWithPop('Server', headers)
    self.assertKeyWithPop('Date', headers)

    # drop vary-keys
    headers.pop('Content-Length', None)
    headers.pop('Transfer-Encoding', None)
    headers.pop('Connection', None)
    headers.pop('Keep-Alive', None)

    self.assertEqual(
      headers,
      {
        'Vary': 'Accept-Encoding',
        'Content-Type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
        'Content-Encoding': 'gzip',
      }
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_enable_http2_default(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable-http2-default']
    self.assertLogAccessUrlWithPop(parameter_dict, 'enable-http2-default')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablehttp2default.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2default.example.com',
        'site_url': 'http://enablehttp2default.example.com',
        'secure_access':
        'https://enablehttp2default.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = result.headers.copy()

    self.assertKeyWithPop('Server', headers)
    self.assertKeyWithPop('Date', headers)

    # drop vary-keys
    headers.pop('Content-Length', None)
    headers.pop('Transfer-Encoding', None)
    headers.pop('Connection', None)
    headers.pop('Keep-Alive', None)

    self.assertEqual(
      headers,
      {
        'Vary': 'Accept-Encoding',
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
        'Content-Encoding': 'gzip',
      }
    )

    self.assertTrue(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_prefer_gzip_encoding_to_backend(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'prefer-gzip-encoding-to-backend']
    self.assertLogAccessUrlWithPop(
      parameter_dict, 'prefer-gzip-encoding-to-backend')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'prefergzipencodingtobackend.example.com',
        'replication_number': '1',
        'url': 'http://prefergzipencodingtobackend.example.com',
        'site_url': 'http://prefergzipencodingtobackend.example.com',
        'secure_access':
        'https://prefergzipencodingtobackend.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    self.assertEqual(
      result.json()['Incoming Headers']['accept-encoding'], 'gzip')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      headers={'Accept-Encoding': 'deflate'})

    self.assertEqualResultJson(result, 'Path', '/test-path')

    self.assertEqual(
      result.json()['Incoming Headers']['accept-encoding'], 'deflate')

  @skipIf(IS_CADDY, 'Feature postponed')
  def test_disabled_cookie_list(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'disabled-cookie-list']
    self.assertLogAccessUrlWithPop(parameter_dict, 'disabled-cookie-list')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'disabledcookielist.example.com',
        'replication_number': '1',
        'url': 'http://disabledcookielist.example.com',
        'site_url': 'http://disabledcookielist.example.com',
        'secure_access': 'https://disabledcookielist.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      cookies=dict(
          Chocolate='absent',
          Vanilia='absent',
          Coffee='present'
        ))

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    self.assertEqual(
      result.json()['Incoming Headers']['cookie'], 'Coffee=present')

  def test_apache_custom_http_s_rejected(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'apache_custom_http_s-rejected']
    self.assertEqual({}, parameter_dict)
    slave_configuration_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'etc', '*slave-conf.d', '*.conf'))
    # no configuration file contains provided custom http
    configuration_file_with_custom_https_list = [
      q for q in slave_configuration_file_list
      if 'apache_custom_https_filled_in_rejected' in open(q).read()]
    self.assertEqual([], configuration_file_with_custom_https_list)

    configuration_file_with_custom_http_list = [
      q for q in slave_configuration_file_list
      if 'apache_custom_http_filled_in_rejected' in open(q).read()]
    self.assertEqual([], configuration_file_with_custom_http_list)

  def test_apache_custom_http_s_accepted(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'apache_custom_http_s-accepted']
    self.assertLogAccessUrlWithPop(
      parameter_dict, 'apache_custom_http_s-accepted')
    self.assertEqual(
      parameter_dict,
      {'replication_number': '1', 'public-ipv4': utils.LOCAL_IPV4}
    )

    result = self.fakeHTTPSResult(
      'apachecustomhttpsaccepted.example.com',
      parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = result.headers.copy()

    self.assertKeyWithPop('Server', headers)
    self.assertKeyWithPop('Date', headers)

    # drop vary-keys
    headers.pop('Content-Length', None)
    headers.pop('Transfer-Encoding', None)
    headers.pop('Connection', None)
    headers.pop('Keep-Alive', None)

    self.assertEqual(
      headers,
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value'
      }
    )

    result_http = self.fakeHTTPResult(
      'apachecustomhttpsaccepted.example.com',
      parameter_dict['public-ipv4'], 'test-path')
    self.assertEqualResultJson(result_http, 'Path', '/test-path')

    slave_configuration_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'etc', '*slave-conf.d', '*.conf'))
    # no configuration file contains provided custom http
    configuration_file_with_custom_https_list = [
      q for q in slave_configuration_file_list
      if 'apache_custom_https_filled_in_accepted' in open(q).read()]
    self.assertEqual(1, len(configuration_file_with_custom_https_list))

    configuration_file_with_custom_http_list = [
      q for q in slave_configuration_file_list
      if 'apache_custom_http_filled_in_accepted' in open(q).read()]
    self.assertEqual(1, len(configuration_file_with_custom_http_list))

  @skipIf(not IS_CADDY, 'Feature not applicable')
  def test_caddy_custom_http_s_rejected(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'caddy_custom_http_s-rejected']
    self.assertEqual({}, parameter_dict)
    slave_configuration_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'etc', '*slave-conf.d', '*.conf'))
    # no configuration file contains provided custom http
    configuration_file_with_custom_https_list = [
      q for q in slave_configuration_file_list
      if 'caddy_custom_https_filled_in_rejected' in open(q).read()]
    self.assertEqual([], configuration_file_with_custom_https_list)

    configuration_file_with_custom_http_list = [
      q for q in slave_configuration_file_list
      if 'caddy_custom_http_filled_in_rejected' in open(q).read()]
    self.assertEqual([], configuration_file_with_custom_http_list)

  @skipIf(not IS_CADDY, 'Feature not applicable')
  def test_caddy_custom_http_s_accepted(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'caddy_custom_http_s-accepted']
    self.assertLogAccessUrlWithPop(
      parameter_dict, 'caddy_custom_http_s-accepted')
    self.assertEqual(
      parameter_dict,
      {'replication_number': '1', 'public-ipv4': utils.LOCAL_IPV4}
    )

    result = self.fakeHTTPSResult(
      'caddycustomhttpsaccepted.example.com',
      parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = result.headers.copy()

    self.assertKeyWithPop('Server', headers)
    self.assertKeyWithPop('Date', headers)

    # drop vary-keys
    headers.pop('Content-Length', None)
    headers.pop('Transfer-Encoding', None)
    headers.pop('Connection', None)
    headers.pop('Keep-Alive', None)

    self.assertEqual(
      headers,
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value'
      }
    )

    result_http = self.fakeHTTPResult(
      'caddycustomhttpsaccepted.example.com',
      parameter_dict['public-ipv4'], 'test-path')
    self.assertEqualResultJson(result_http, 'Path', '/test-path')

    slave_configuration_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'etc', '*slave-conf.d', '*.conf'))
    # no configuration file contains provided custom http
    configuration_file_with_custom_https_list = [
      q for q in slave_configuration_file_list
      if 'caddy_custom_https_filled_in_accepted' in open(q).read()]
    self.assertEqual(1, len(configuration_file_with_custom_https_list))

    configuration_file_with_custom_http_list = [
      q for q in slave_configuration_file_list
      if 'caddy_custom_http_filled_in_accepted' in open(q).read()]
    self.assertEqual(1, len(configuration_file_with_custom_http_list))

  def test_https_url(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'url_https-url']
    self.assertLogAccessUrlWithPop(parameter_dict, 'url_https-url')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'urlhttpsurl.example.com',
        'replication_number': '1',
        'url': 'http://urlhttpsurl.example.com',
        'site_url': 'http://urlhttpsurl.example.com',
        'secure_access': 'https://urlhttpsurl.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/https/test-path')

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqualResultJson(result_http, 'Path', '/http/test-path')


class TestReplicateSlave(SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'nginx-domain': 'nginx.example.com',
      'public-ipv4': utils.LOCAL_IPV4,
      'apache-certificate': open('wildcard.example.com.crt').read(),
      'apache-ca-certificate': open('example.com.root.ca.crt').read(),
      'apache-key': open('wildcard.example.com.key').read(),
      '-frontend-quantity': 2,
      '-sla-2-computer_guid': 'slapos.test',
      '-frontend-2-state': 'stopped',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
      '-frontend-config-2-monitor-httpd-port': MONITOR_F2_HTTPD_PORT,
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'replicate': {
        'url': cls.backend_url,
      },
    }

  def test(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'replicate']
    self.assertLogAccessUrlWithPop(parameter_dict, 'replicate')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'replicate.example.com',
        'replication_number': '2',
        'url': 'http://replicate.example.com',
        'site_url': 'http://replicate.example.com',
        'secure_access': 'https://replicate.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      utils.der2pem(result.peercert),
      open('wildcard.example.com.crt').read())

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqualResultJson(result_http, 'Path', '/test-path')

    # prove 2nd frontend by inspection of the instance
    slave_configuration_name = '_replicate.conf'
    slave_configuration_file_list = [
      '/'.join([f[0], slave_configuration_name]) for f in [
        q for q in os.walk(self.instance_path)
        if slave_configuration_name in q[2]
      ]
    ]

    self.assertEqual(
      2, len(slave_configuration_file_list), slave_configuration_file_list)


class TestEnableHttp2ByDefaultFalseSlave(SlaveHttpFrontendTestCase,
                                         TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'nginx-domain': 'nginx.example.com',
      'public-ipv4': utils.LOCAL_IPV4,
      'apache-certificate': open('wildcard.example.com.crt').read(),
      'apache-ca-certificate': open('example.com.root.ca.crt').read(),
      'apache-key': open('wildcard.example.com.key').read(),
      'enable-http2-by-default': 'false',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'enable-http2-default': {
      },
      'enable-http2-false': {
        'enable-http2': 'false',
      },
      'enable-http2-true': {
        'enable-http2': 'true',
      },
    }

  def test_enable_http2_default(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable-http2-default']
    self.assertLogAccessUrlWithPop(parameter_dict, 'enable-http2-default')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablehttp2default.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2default.example.com',
        'site_url': 'http://enablehttp2default.example.com',
        'secure_access':
        'https://enablehttp2default.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_enable_http2_false(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable-http2-false']
    self.assertLogAccessUrlWithPop(parameter_dict, 'enable-http2-false')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablehttp2false.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2false.example.com',
        'site_url': 'http://enablehttp2false.example.com',
        'secure_access':
        'https://enablehttp2false.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_enable_http2_true(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable-http2-true']
    self.assertLogAccessUrlWithPop(parameter_dict, 'enable-http2-true')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablehttp2true.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2true.example.com',
        'site_url': 'http://enablehttp2true.example.com',
        'secure_access':
        'https://enablehttp2true.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    self.assertTrue(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))


class TestEnableHttp2ByDefaultDefaultSlave(SlaveHttpFrontendTestCase,
                                           TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'nginx-domain': 'nginx.example.com',
      'public-ipv4': utils.LOCAL_IPV4,
      'apache-certificate': open('wildcard.example.com.crt').read(),
      'apache-ca-certificate': open('example.com.root.ca.crt').read(),
      'apache-key': open('wildcard.example.com.key').read(),
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'enable-http2-default': {
      },
      'enable-http2-false': {
        'enable-http2': 'false',
      },
      'enable-http2-true': {
        'enable-http2': 'true',
      },
    }

  def test_enable_http2_default(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable-http2-default']
    self.assertLogAccessUrlWithPop(parameter_dict, 'enable-http2-default')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablehttp2default.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2default.example.com',
        'site_url': 'http://enablehttp2default.example.com',
        'secure_access':
        'https://enablehttp2default.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    self.assertTrue(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_enable_http2_false(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable-http2-false']
    self.assertLogAccessUrlWithPop(parameter_dict, 'enable-http2-false')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablehttp2false.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2false.example.com',
        'site_url': 'http://enablehttp2false.example.com',
        'secure_access':
        'https://enablehttp2false.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_enable_http2_true(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'enable-http2-true']
    self.assertLogAccessUrlWithPop(parameter_dict, 'enable-http2-true')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'enablehttp2true.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2true.example.com',
        'site_url': 'http://enablehttp2true.example.com',
        'secure_access':
        'https://enablehttp2true.example.com',
        'public-ipv4': utils.LOCAL_IPV4,
      }
    )

    self.assertTrue(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))


class TestRe6stVerificationUrlDefaultSlave(SlaveHttpFrontendTestCase,
                                           TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'default': {
      },
    }

  def test_default(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'default']
    self.assertLogAccessUrlWithPop(parameter_dict, 'default')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'default.None',
        'replication_number': '1',
        'url': 'http://default.None',
        'site_url': 'http://default.None',
        'secure_access': 'https://default.None',
        'public-ipv4': None,
      }
    )

    re6st_connectivity_promise_list = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'promise',
        're6st-connectivity'))

    self.assertEqual(1, len(re6st_connectivity_promise_list))

    self.assertTrue(
      'URL="http://[2001:67c:1254:4::1]/index.html"' in
      open(re6st_connectivity_promise_list[0]).read()
    )


class TestRe6stVerificationUrlSlave(SlaveHttpFrontendTestCase,
                                    TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
      're6st-verification-url': 'some-re6st-verification-url',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'default': {
      },
    }

  def test_default(self):
    parameter_dict = self.slave_connection_parameter_dict_dict[
      'default']
    self.assertLogAccessUrlWithPop(parameter_dict, 'default')
    self.assertEqual(
      parameter_dict,
      {
        'domain': 'default.None',
        'replication_number': '1',
        'url': 'http://default.None',
        'site_url': 'http://default.None',
        'secure_access': 'https://default.None',
        'public-ipv4': None,
      }
    )

    re6st_connectivity_promise_list = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'promise',
        're6st-connectivity'))

    self.assertEqual(1, len(re6st_connectivity_promise_list))

    self.assertTrue(
      'URL="some-re6st-verification-url"' in
      open(re6st_connectivity_promise_list[0]).read()
    )
