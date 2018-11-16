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

import glob
import os
import requests
import httplib
from requests_toolbelt.adapters import source
import json
import multiprocessing
import subprocess
from unittest import skip
import ssl
from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler
from forcediphttpsadapter.adapters import ForcedIPHTTPSAdapter
import time
import tempfile
import ipaddress

from utils import SlapOSInstanceTestCase
from utils import findFreeTCPPort

import datetime

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

LOCAL_IPV4 = os.environ['LOCAL_IPV4']
GLOBAL_IPV6 = os.environ['GLOBAL_IPV6']
KEDIFA_IPV6_BASE = 'https://[%s]:7879' % (GLOBAL_IPV6,)

# ports chosen to not collide with test systems
HTTP_PORT = '11080'
HTTPS_PORT = '11443'
NGINX_HTTP_PORT = '12080'
NGINX_HTTPS_PORT = '12443'
MONITOR_HTTPD_PORT = '13000'
MONITOR_F1_HTTPD_PORT = '13001'
MONITOR_F2_HTTPD_PORT = '13002'


# for development: debugging logs and install Ctrl+C handler
if os.environ.get('DEBUG'):
  import logging
  logging.basicConfig(level=logging.DEBUG)
  import unittest
  unittest.installHandler()


def der2pem(der):
  certificate = x509.load_der_x509_certificate(der, default_backend())
  return certificate.public_bytes(serialization.Encoding.PEM)


def createKey():
  key = rsa.generate_private_key(
    public_exponent=65537, key_size=2048, backend=default_backend())
  key_pem = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
  )
  return key, key_pem


def createSelfSignedCertificate(name_list):
  key, key_pem = createKey()
  subject_alternative_name_list = x509.SubjectAlternativeName(
    [x509.DNSName(unicode(q)) for q in name_list]
  )
  subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, u'Test Self Signed Certificate'),
  ])
  certificate = x509.CertificateBuilder().subject_name(
    subject
  ).issuer_name(
    issuer
  ).add_extension(
      subject_alternative_name_list,
      critical=False,
  ).public_key(
    key.public_key()
  ).serial_number(
    x509.random_serial_number()
  ).not_valid_before(
    datetime.datetime.utcnow() - datetime.timedelta(days=2)
  ).not_valid_after(
    datetime.datetime.utcnow() + datetime.timedelta(days=5)
  ).sign(key, hashes.SHA256(), default_backend())
  certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
  return key, key_pem, certificate, certificate_pem


def createCSR(common_name, ip=None):
  key, key_pem = createKey()
  subject_alternative_name_list = []
  if ip is not None:
    subject_alternative_name_list.append(
      x509.IPAddress(ipaddress.ip_address(unicode(ip)))
    )
  csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
     x509.NameAttribute(NameOID.COMMON_NAME, unicode(common_name)),
  ]))

  if len(subject_alternative_name_list):
    csr = csr.add_extension(
      x509.SubjectAlternativeName(subject_alternative_name_list),
      critical=False
    )

  csr = csr.sign(key, hashes.SHA256(), default_backend())
  csr_pem = csr.public_bytes(serialization.Encoding.PEM)
  return key, key_pem, csr, csr_pem


class CertificateAuthority(object):
  def __init__(self, common_name):
    self.key, self.key_pem = createKey()
    public_key = self.key.public_key()
    builder = x509.CertificateBuilder()
    builder = builder.subject_name(x509.Name([
      x509.NameAttribute(NameOID.COMMON_NAME, unicode(common_name)),
    ]))
    builder = builder.issuer_name(x509.Name([
      x509.NameAttribute(NameOID.COMMON_NAME, unicode(common_name)),
    ]))
    builder = builder.not_valid_before(
      datetime.datetime.utcnow() - datetime.timedelta(days=2))
    builder = builder.not_valid_after(
      datetime.datetime.utcnow() + datetime.timedelta(days=30))
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.public_key(public_key)
    builder = builder.add_extension(
      x509.BasicConstraints(ca=True, path_length=None), critical=True,
    )
    self.certificate = builder.sign(
      private_key=self.key, algorithm=hashes.SHA256(),
      backend=default_backend()
    )
    self.certificate_pem = self.certificate.public_bytes(
      serialization.Encoding.PEM)

  def signCSR(self, csr):
    builder = x509.CertificateBuilder(
      subject_name=csr.subject,
      extensions=csr.extensions,
      issuer_name=self.certificate.subject,
      not_valid_before=datetime.datetime.utcnow() - datetime.timedelta(days=1),
      not_valid_after=datetime.datetime.utcnow() + datetime.timedelta(days=30),
      serial_number=x509.random_serial_number(),
      public_key=csr.public_key(),
    )
    certificate = builder.sign(
      private_key=self.key,
      algorithm=hashes.SHA256(),
      backend=default_backend()
    )
    return certificate, certificate.public_bytes(serialization.Encoding.PEM)


def isHTTP2(domain, ip):
  curl_command = 'curl --http2 -v -k -H "Host: %(domain)s" ' \
    'https://%(domain)s:%(https_port)s/ '\
    '--resolve %(domain)s:%(https_port)s:%(ip)s' % dict(
      ip=ip, domain=domain, https_port=HTTPS_PORT)
  prc = subprocess.Popen(
    curl_command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
  )
  out, err = prc.communicate()
  assert prc.returncode == 0, "Problem running %r. Output:\n%s\nError:\n%s" % (
    curl_command, out, err)
  return 'Using HTTP2, server supports multi-use' in err


def getQUIC(url, ip, port):
  quic_client_command = 'quic_client --disable-certificate-verification '\
    '--port=%(port)s --host=%(host)s %(url)s' % dict(
      port=port, host=ip, url=url)
  try:
    return True, subprocess.check_output(
      quic_client_command.split(), stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError as e:
    return False, e.output


class TestDataMixin(object):
  @staticmethod
  def generateHashFromFiles(file_list):
    import hashlib
    hasher = hashlib.md5()
    for path in file_list:
      with open(path, 'r') as afile:
        buf = afile.read()
      hasher.update("%s\n" % len(buf))
      hasher.update(buf)
    hash = hasher.hexdigest()
    return hash

  def getTrimmedProcessInfo(self):
    return '\n'.join(sorted([
      '%(group)s:%(name)s %(statename)s' % q for q
      in self.getSupervisorRPCServer().supervisor.getAllProcessInfo()]))

  def assertTestData(self, runtime_data, hash_value=None):
    filename = '%s-%s.txt' % (self.id(), 'CADDY')
    test_data_file = os.path.join(
      os.path.dirname(os.path.realpath(__file__)), 'test_data', filename)

    try:
      test_data = open(test_data_file).read().strip()
    except IOError:
      test_data = ''

    if hash_value is not None:
      runtime_data = runtime_data.replace(hash_value, '{hash}')

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

  def test_plugin_list(self):
    runtime_data = '\n'.join(sorted([
      q[len(self.instance_path) + 1:]
      for q in glob.glob(os.path.join(
        self.instance_path, '*', 'etc', 'plugin', '*'))
      if not q.endswith('pyc')  # ignore compiled python
    ]))

    self.assertTestData(runtime_data)

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
      # no control at all when cron would kick in, ignore it
      'cron.log',
      # appears late, not needed for assertion
      'trafficserver/diags.log',
      'trafficserver/squid.blog',
      'trafficserver/.squid.blog.meta',
      # not important, appears sometimes
      'trafficserver/.error.log.meta',
      'trafficserver/error.log',
    ])

  def test_file_list_run(self):
    self._test_file_list('run', [
      # run by cron from time to time
      'monitor/monitor-collect.pid',
    ])

  def test_supervisor_state(self):
    # give a chance for etc/run scripts to finish
    time.sleep(1)

    hash_files = [
      'software_release/buildout.cfg',
    ]
    hash_files = [os.path.join(self.computer_partition_root_path, path)
                  for path in hash_files]
    h = self.generateHashFromFiles(hash_files)

    runtime_data = self.getTrimmedProcessInfo()
    self.assertTestData(runtime_data, hash_value=h)


class HttpFrontendTestCase(SlapOSInstanceTestCase):
  # show full diffs, as it is required for proper analysis of problems
  maxDiff = None

  @classmethod
  def getSoftwareURLList(cls):
    return [os.path.realpath(os.environ['TEST_SR'])]

  @classmethod
  def setUpClass(cls):
    super(HttpFrontendTestCase, cls).setUpClass()
    # extra class attributes used in HttpFrontendTestCase

    # expose instance directory
    cls.instance_path = os.path.join(
        cls.config['working_directory'],
        'inst')
    # expose software directory, extract from found computer partition
    cls.software_path = os.path.realpath(os.path.join(
        cls.computer_partition_root_path, 'software_release'))

  def assertLogAccessUrlWithPop(self, parameter_dict):
    log_access_url = parameter_dict.pop('log-access-url')

    self.assertTrue(len(log_access_url) >= 1)
    # check only the first one, as second frontend will be stopped
    log_access = log_access_url[0]
    entry = log_access.split(': ')
    if len(entry) != 2:
      self.fail('Cannot parse %r' % (log_access,))
    frontend, url = entry
    result = requests.get(url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code,
      'While accessing %r of %r the status code was %r' % (
        url, frontend, result.status_code))

  def assertKedifaKeysWithPop(self, parameter_dict, prefix=''):
    generate_auth_url = parameter_dict.pop('%skey-generate-auth-url' % (
      prefix,))
    upload_url = parameter_dict.pop('%skey-upload-url' % (prefix,))
    base = '^' + KEDIFA_IPV6_BASE.replace(
      '[', r'\[').replace(']', r'\]') + '/.{32}'
    self.assertRegexpMatches(
      generate_auth_url,
      base + r'\/generateauth$'
    )
    self.assertRegexpMatches(
      upload_url,
      base + r'\?auth=$'
    )

    return generate_auth_url, upload_url

  def assertKeyWithPop(self, key, d):
    self.assertTrue(key in d, 'Key %r is missing in %r' % (key, d))
    d.pop(key)

  def assertEqualResultJson(self, result, key, value):
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertTrue(key in j, 'No key %r in %s' % (key, j))
    self.assertEqual(value, j[key])

  def parseParameterDict(self, parameter_dict):
    parsed_parameter_dict = {}
    for key, value in parameter_dict.items():
      if key in [
        'rejected-slave-dict',
        'request-error-list',
        'log-access-url']:
        value = json.loads(value)
      parsed_parameter_dict[key] = value
    return parsed_parameter_dict

  def parseConnectionParameterDict(self):
    return self.parseParameterDict(
      self.computer_partition.getConnectionParameterDict()
    )


class TestMasterRequest(HttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  def test(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertEqual(
      {
        'monitor-base-url': None,
        'domain': 'None',
        'kedifa-caucase-url': 'http://[%s]:8890' % (GLOBAL_IPV6,),
        'accepted-slave-amount': '0',
        'rejected-slave-amount': '0',
        'slave-amount': '0',
        'rejected-slave-dict': {}},
      parameter_dict
    )


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
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  def test(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')

    self.assertEqual(
      {
        'monitor-base-url': None,
        'domain': 'example.com',
        'kedifa-caucase-url': 'http://[%s]:8890' % (GLOBAL_IPV6,),
        'accepted-slave-amount': '0',
        'rejected-slave-amount': '0',
        'slave-amount': '0',
        'rejected-slave-dict': {}
      },
      parameter_dict
    )


class TestHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.send_header('Set-Cookie', 'secured=value;secure')
    self.send_header('Set-Cookie', 'nonsecured=value')
    self.end_headers()
    response = {
      'Path': self.path,
      'Incoming Headers': self.headers.dict
    }
    self.wfile.write(json.dumps(response, indent=2))


class SlaveHttpFrontendTestCase(HttpFrontendTestCase):
  @classmethod
  def startServerProcess(cls):
    server = HTTPServer(
      (LOCAL_IPV4, findFreeTCPPort(LOCAL_IPV4)),
      TestHandler)

    server_https = HTTPServer(
      (LOCAL_IPV4, findFreeTCPPort(LOCAL_IPV4)),
      TestHandler)

    cls.another_server_ca = CertificateAuthority("Another Server Root CA")
    cls.test_server_ca = CertificateAuthority("Test Server Root CA")
    key, key_pem, csr, csr_pem = createCSR(
      "testserver.example.com", LOCAL_IPV4)
    _, cls.test_server_certificate_pem = cls.test_server_ca.signCSR(csr)

    cls.test_server_certificate_file = tempfile.NamedTemporaryFile(
      delete=False
    )

    cls.test_server_certificate_file.write(
        cls.test_server_certificate_pem + key_pem
      )
    cls.test_server_certificate_file.close()
    server_https.socket = ssl.wrap_socket(
      server_https.socket,
      certfile=cls.test_server_certificate_file.name,
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
    if getattr(cls, 'test_server_certificate_file', None) is not None:
      os.unlink(cls.test_server_certificate_file.name)
    if getattr(cls, 'server_process', None) is None:
      return
    cls.server_process.terminate()
    cls.server_https_process.terminate()

  @classmethod
  def setUpMaster(cls):
    # run partition few more times for AIKC and reservation to kick in
    # properlly
    cls.runComputerPartition(max_quantity=4)
    parameter_dict = cls.computer_partition.getConnectionParameterDict()
    ca_certificate = requests.get(
      parameter_dict['kedifa-caucase-url'] + '/cas/crt/ca.crt.pem')
    assert ca_certificate.status_code == httplib.OK
    cls.ca_certificate_file = os.path.join(cls.working_directory, 'ca.crt.pem')
    open(cls.ca_certificate_file, 'w').write(ca_certificate.text)
    auth = requests.get(
      parameter_dict['master-key-generate-auth-url'],
      verify=cls.ca_certificate_file)
    assert auth.status_code == httplib.CREATED
    upload = requests.put(
      parameter_dict['master-key-upload-url'] + auth.text,
      data=cls.key_pem + cls.certificate_pem,
      verify=cls.ca_certificate_file)
    assert upload.status_code == httplib.CREATED

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
    # run partition few more times for slaves to be setup
    cls.runComputerPartition(max_quantity=5)
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
  def createWildcardExampleComCertificate(cls):
    _, cls.key_pem, _, cls.certificate_pem = createSelfSignedCertificate(
      [
        '*.customdomain.example.com',
        '*.example.com',
        '*.nginx.example.com',
        '*.alias1.example.com',
      ])

  @classmethod
  def setUpClass(cls):
    try:
      cls.createWildcardExampleComCertificate()
      cls.startServerProcess()
      super(SlaveHttpFrontendTestCase, cls).setUpClass()
      cls.setUpMaster()
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
      verify=False,
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

  def parseSlaveParameterDict(self, key):
    return self.parseParameterDict(
      self.slave_connection_parameter_dict_dict[
        key
      ]
    )


class TestSlave(SlaveHttpFrontendTestCase, TestDataMixin):
  caddy_custom_https = '''# caddy_custom_https_filled_in_accepted
https://caddycustomhttpsaccepted.example.com:%%(https_port)s {
  bind %%(local_ipv4)s
  tls %%(certificate)s %%(certificate)s

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

  apache_custom_https = '''# apache_custom_https_filled_in_accepted
https://apachecustomhttpsaccepted.example.com:%%(https_port)s {
  bind %%(local_ipv4)s
  tls %%(certificate)s %%(certificate)s

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

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'nginx-domain': 'nginx.example.com',
      'public-ipv4': LOCAL_IPV4,
      '-frontend-authorized-slave-string':
      '_apache_custom_http_s-accepted _caddy_custom_http_s-accepted',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
      'mpm-graceful-shutdown-timeout': 2,
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  @classmethod
  def setUpSlaves(cls):
    cls.ca = CertificateAuthority('TestSlave')
    _, cls.customdomain_ca_key_pem, csr, _ = createCSR(
      'customdomainsslcrtsslkeysslcacrt.example.com')
    _, cls.customdomain_ca_certificate_pem = cls.ca.signCSR(csr)
    _, cls.customdomain_key_pem, _, cls.customdomain_certificate_pem = \
        createSelfSignedCertificate(['customdomainsslcrtsslkey.example.com'])
    super(TestSlave, cls).setUpSlaves()

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
      'server-alias-wildcard': {
        'url': cls.backend_url,
        'server-alias': '*.alias1.example.com',
      },
      'server-alias-duplicated': {
        'url': cls.backend_url,
        'server-alias': 'alias3.example.com alias3.example.com',
      },
      'server-alias_custom_domain-duplicated': {
        'url': cls.backend_url,
        'custom_domain': 'alias4.example.com',
        'server-alias': 'alias4.example.com alias4.example.com',
      },
      'ssl-proxy-verify_ssl_proxy_ca_crt': {
        'url': cls.backend_https_url,
        'ssl-proxy-verify': True,
        'ssl_proxy_ca_crt': cls.test_server_ca.certificate_pem,
      },
      'ssl-proxy-verify_ssl_proxy_ca_crt-unverified': {
        'url': cls.backend_https_url,
        'ssl-proxy-verify': True,
        'ssl_proxy_ca_crt': cls.another_server_ca.certificate_pem,
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
      'custom_domain_wildcard': {
        'url': cls.backend_url,
        'custom_domain': '*.customdomain.example.com',
      },
      'custom_domain_ssl_crt_ssl_key': {
        'url': cls.backend_url,
        'custom_domain': 'customdomainsslcrtsslkey.example.com'
      },
      'custom_domain_ssl_crt_ssl_key_ssl_ca_crt': {
        'url': cls.backend_url,
        'custom_domain': 'customdomainsslcrtsslkeysslcacrt.example.com',
      },
      'ssl_ca_crt_only': {
        'url': cls.backend_url,
      },
      'ssl_ca_crt_garbage': {
        'url': cls.backend_url,
      },
      'ssl_ca_crt_does_not_match': {
        'url': cls.backend_url,
      },
      'type-zope': {
        'url': cls.backend_url,
        'type': 'zope',
      },
      'type-zope-ssl-proxy-verify_ssl_proxy_ca_crt': {
        'url': cls.backend_https_url,
        'type': 'zope',
        'ssl-proxy-verify': True,
        'ssl_proxy_ca_crt': cls.test_server_ca.certificate_pem,
      },
      'type-zope-ssl-proxy-verify_ssl_proxy_ca_crt-unverified': {
        'url': cls.backend_https_url,
        'type': 'zope',
        'ssl-proxy-verify': True,
        'ssl_proxy_ca_crt': cls.another_server_ca.certificate_pem,
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
        'ssl_proxy_ca_crt': cls.test_server_ca.certificate_pem,
        'ssl-proxy-verify': True,
      },
      'enable_cache-ssl-proxy-verify_ssl_proxy_ca_crt-unverified': {
        'url': cls.backend_https_url,
        'enable_cache': True,
        'ssl_proxy_ca_crt': cls.another_server_ca.certificate_pem,
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
        'apache_custom_https': cls.apache_custom_https % dict(
          url=cls.backend_url),
        'apache_custom_http': cls.apache_custom_http % dict(
          url=cls.backend_url),
      },
      'caddy_custom_http_s-rejected': {
        'url': cls.backend_url,
        'caddy_custom_https': '# caddy_custom_https_filled_in_rejected',
        'caddy_custom_http': '# caddy_custom_http_filled_in_rejected',
      },
      'caddy_custom_http_s-accepted': {
        'url': cls.backend_url,
        'caddy_custom_https': cls.caddy_custom_https % dict(
          url=cls.backend_url),
        'caddy_custom_http': cls.caddy_custom_http % dict(
          url=cls.backend_url),
      },
      # this has to be rejected
      'caddy_custom_http_s': {
        'url': cls.backend_url,
        'caddy_custom_https': '# caddy_custom_https_filled_in_rejected_2',
        'caddy_custom_http': '# caddy_custom_http_filled_in_rejected_2',
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
      if not os.path.exists(
        os.path.join(q, 'etc', 'trafficserver')) and os.path.exists(
          os.path.join(q, 'buildout.cfg'))][0]

  def getSlavePartitionPath(self):
    # partition w/ etc/trafficserver
    return [
      q for q in glob.glob(os.path.join(self.instance_path, '*',))
      if os.path.exists(os.path.join(q, 'etc', 'trafficserver'))][0]

  def test_master_partition_state(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')

    expected_parameter_dict = {
      'monitor-base-url': None,
      'domain': 'example.com',
      'accepted-slave-amount': '44',
      'rejected-slave-amount': '3',
      'slave-amount': '47',
      'kedifa-caucase-url': 'http://[%s]:8890' % (GLOBAL_IPV6,),
      'rejected-slave-dict': {
        '_apache_custom_http_s-rejected': ['slave not authorized'],
        '_caddy_custom_http_s': ['slave not authorized'],
        '_caddy_custom_http_s-rejected': ['slave not authorized'],
      }
    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

    partition_path = self.getMasterPartitionPath()

    self.assertEqual(
      set([
        'monitor-http-frontend',
        'monitor-httpd-listening-on-tcp',
        'promise-monitor-httpd-is-process-older-than-dependency-set',
      ]),
      set(os.listdir(os.path.join(partition_path, 'etc', 'promise'))))

    self.assertEqual(
      set([
        'monitor-bootstrap-status.py',
        'check-free-disk-space.py',
        'buildout-TestSlave-0-status.py',
        '__init__.py',
      ]),
      set([
        q for q in os.listdir(os.path.join(partition_path, 'etc', 'plugin'))
        if not q.endswith('.pyc')]))

    self.assertEqual(
      set(),
      set(os.listdir(os.path.join(partition_path, 'etc', 'monitor-promise'))))

    # check that monitor cors domains are correctly setup by file presence, as
    # we trust monitor stack being tested in proper place and it is too hard
    # to have working monitor with local proxy
    self.assertTestData(
      open(
        os.path.join(
          partition_path, 'etc', 'httpd-cors.cfg'), 'r').read().strip())

  def test_promise_monitor_httpd_listening_on_tcp(self):
      result = set([
        subprocess.call(q) for q in glob.glob(
          os.path.join(
            self.instance_path, '*', 'etc', 'promise',
            'monitor-httpd-listening-on-tcp'))])
      self.assertEqual(
        set([0]),
        result
      )

  def test_slave_partition_state(self):
    partition_path = self.getSlavePartitionPath()
    self.assertTrue(
      '-grace 2s' in
      open(os.path.join(partition_path, 'bin', 'caddy-wrapper'), 'r').read()
    )

    self.assertTrue(
      '-grace 2s' in
      open(os.path.join(partition_path, 'bin', 'nginx-wrapper'), 'r').read()
    )

  def assertSlaveBase(self, reference):
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, '')
    hostname = reference.translate(None, '_-')
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': LOCAL_IPV4
      },
      parameter_dict
    )

    return parameter_dict

  def test_empty(self):
    parameter_dict = self.assertSlaveBase('empty')
    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.NOT_FOUND, result.status_code)

    # check that log file contains verbose log
    log_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'var', 'log', 'httpd', '_empty_access_log'
      ))[0]

    log_regexp = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3} SOME_REMOTE_USER ' \
                 r'\[\d{2}\/.{3}\/\d{4}\:\d{2}\:\d{2}\:\d{2} \+\d{4}\] ' \
                 r'"GET \/test-path HTTP\/1.1" 404 \d+ "-" '\
                 r'"python-requests.*" \d+'

    self.assertRegexpMatches(
      open(log_file, 'r').read(),
      log_regexp)
    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(httplib.NOT_FOUND, result_http.status_code)

    # check that 404 is as configured
    result_missing = self.fakeHTTPSResult(
      'forsuredoesnotexists.example.com', parameter_dict['public-ipv4'], '')
    self.assertEqual(httplib.NOT_FOUND, result_missing.status_code)
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
    parameter_dict = self.assertSlaveBase('url')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertFalse('remote_user' in j['Incoming Headers'].keys())

    self.assertEqual(
      'gzip',
      result.headers['Content-Encoding']
    )

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result.headers['Set-Cookie']
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
      'gzip',
      result_http.headers['Content-Encoding']
    )

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result_http.headers['Set-Cookie']
    )

  @skip('Feature postponed')
  def test_url_ipv6_access(self):
    parameter_dict = self.parseSlaveParameterDict('url')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'url.example.com',
        'replication_number': '1',
        'url': 'http://url.example.com',
        'site_url': 'http://url.example.com',
        'secure_access': 'https://url.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result_ipv6 = self.fakeHTTPSResult(
      parameter_dict['domain'], GLOBAL_IPV6, 'test-path',
      source_ip=GLOBAL_IPV6)

    self.assertEqual(
       GLOBAL_IPV6,
       result_ipv6.json()['Incoming Headers']['x-forwarded-for']
    )

    self.assertEqual(
      self.certificate_pem,
      der2pem(result_ipv6.peercert))

    self.assertEqualResultJson(result_ipv6, 'Path', '/test-path')

  def test_type_zope_path(self):
    parameter_dict = self.assertSlaveBase('type-zope-path')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//'
      'typezopepath.example.com:443/path/VirtualHostRoot/test-path'
    )

  def test_type_zope_default_path(self):
    parameter_dict = self.assertSlaveBase('type-zope-default-path')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], '')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      'https://typezopedefaultpath.example.com:%s/default-path' % (
        HTTPS_PORT,),
      result.headers['Location']
    )

  def test_server_alias(self):
    parameter_dict = self.assertSlaveBase('server-alias')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = self.fakeHTTPSResult(
      'alias1.example.com', parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = self.fakeHTTPSResult(
      'alias2.example.com', parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

  def test_server_alias_wildcard(self):
    parameter_dict = self.parseSlaveParameterDict('server-alias-wildcard')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'serveraliaswildcard.example.com',
        'replication_number': '1',
        'url': 'http://serveraliaswildcard.example.com',
        'site_url': 'http://serveraliaswildcard.example.com',
        'secure_access': 'https://serveraliaswildcard.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = self.fakeHTTPSResult(
      'wild.alias1.example.com', parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_server_alias_duplicated(self):
    parameter_dict = self.parseSlaveParameterDict('server-alias-duplicated')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'serveraliasduplicated.example.com',
        'replication_number': '1',
        'url': 'http://serveraliasduplicated.example.com',
        'site_url': 'http://serveraliasduplicated.example.com',
        'secure_access': 'https://serveraliasduplicated.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = self.fakeHTTPSResult(
      'alias3.example.com', parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_server_alias_custom_domain_duplicated(self):
    parameter_dict = self.parseSlaveParameterDict(
      'server-alias_custom_domain-duplicated')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'alias4.example.com',
        'replication_number': '1',
        'url': 'http://alias4.example.com',
        'site_url': 'http://alias4.example.com',
        'secure_access': 'https://alias4.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  @skip('Feature postponed')
  def test_check_error_log(self):
    # Caddy: Need to implement similar thing like check-error-on-apache-log
    raise NotImplementedError(self.id())

  def test_ssl_ca_crt(self):
    parameter_dict = self.parseSlaveParameterDict(
      'custom_domain_ssl_crt_ssl_key_ssl_ca_crt')
    self.assertLogAccessUrlWithPop(parameter_dict)
    generate_auth, upload_url = self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'customdomainsslcrtsslkeysslcacrt.example.com',
        'replication_number': '1',
        'url': 'http://customdomainsslcrtsslkeysslcacrt.example.com',
        'site_url': 'http://customdomainsslcrtsslkeysslcacrt.example.com',
        'secure_access':
        'https://customdomainsslcrtsslkeysslcacrt.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    # as now the place to put the key is known put the key there
    auth = requests.get(
      generate_auth,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, auth.status_code)

    data = self.customdomain_ca_certificate_pem + \
        self.customdomain_ca_key_pem + \
        self.ca.certificate_pem

    upload = requests.put(
      upload_url + auth.text,
      data=data,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, upload.status_code)

    # after partitions being processed the key will be used for this slave
    self.runComputerPartition(max_quantity=1)

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.customdomain_ca_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    certificate_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'srv', 'autocert',
      '_custom_domain_ssl_crt_ssl_key_ssl_ca_crt', 'certificate.pem'))
    self.assertEqual(1, len(certificate_file_list))
    certificate_file = certificate_file_list[0]
    with open(certificate_file) as out:
      stored_cert_data = out.read()
      self.assertTrue(self.customdomain_ca_certificate_pem in stored_cert_data)
      self.assertTrue(self.customdomain_ca_key_pem in stored_cert_data)
      self.assertTrue(self.ca.certificate_pem in stored_cert_data)

  def test_ssl_ca_crt_only(self):
    parameter_dict = self.parseSlaveParameterDict('ssl_ca_crt_only')
    self.assertLogAccessUrlWithPop(parameter_dict)
    generate_auth, upload_url = self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'sslcacrtonly.example.com',
        'replication_number': '1',
        'url': 'http://sslcacrtonly.example.com',
        'site_url': 'http://sslcacrtonly.example.com',
        'secure_access':
        'https://sslcacrtonly.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )
    # as now the place to put the key is known put the key there
    auth = requests.get(
      generate_auth,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, auth.status_code)

    data = self.ca.certificate_pem

    upload = requests.put(
      upload_url + auth.text,
      data=data,
      verify=self.ca_certificate_file)

    self.assertEqual(httplib.UNPROCESSABLE_ENTITY, upload.status_code)
    self.assertEqual('Key incorrect', upload.text)

  def test_ssl_ca_crt_garbage(self):
    parameter_dict = self.parseSlaveParameterDict('ssl_ca_crt_garbage')
    self.assertLogAccessUrlWithPop(parameter_dict)
    generate_auth, upload_url = self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'sslcacrtgarbage.example.com',
        'replication_number': '1',
        'url': 'http://sslcacrtgarbage.example.com',
        'site_url': 'http://sslcacrtgarbage.example.com',
        'secure_access':
        'https://sslcacrtgarbage.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    # as now the place to put the key is known put the key there
    auth = requests.get(
      generate_auth,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, auth.status_code)

    data = self.customdomain_ca_certificate_pem + \
        self.customdomain_ca_key_pem + 'some garbage'
    upload = requests.put(
      upload_url + auth.text,
      data=data,
      verify=self.ca_certificate_file)

    self.assertEqual(httplib.CREATED, upload.status_code)

    # after partitions being processed the key will be used for this slave
    self.runComputerPartition(max_quantity=1)

    with self.assertRaises(requests.exceptions.SSLError):
      self.fakeHTTPSResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    certificate_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'srv', 'autocert',
      '_custom_domain_ssl_crt_ssl_key_ssl_ca_crt', 'certificate.pem'))
    self.assertEqual(1, len(certificate_file_list))
    certificate_file = certificate_file_list[0]
    with open(certificate_file) as out:
      stored_cert_data = out.read()
      self.assertTrue(self.customdomain_ca_certificate_pem in stored_cert_data)
      self.assertTrue(self.customdomain_ca_key_pem in stored_cert_data)
      self.assertTrue('some garbage' in stored_cert_data)

  def test_ssl_ca_crt_does_not_match(self):
    parameter_dict = self.parseSlaveParameterDict('ssl_ca_crt_does_not_match')
    self.assertLogAccessUrlWithPop(parameter_dict)
    generate_auth, upload_url = self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'sslcacrtdoesnotmatch.example.com',
        'replication_number': '1',
        'url': 'http://sslcacrtdoesnotmatch.example.com',
        'site_url': 'http://sslcacrtdoesnotmatch.example.com',
        'secure_access':
        'https://sslcacrtdoesnotmatch.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )
    # as now the place to put the key is known put the key there
    auth = requests.get(
      generate_auth,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, auth.status_code)

    data = self.certificate_pem + self.key_pem + self.ca.certificate_pem

    upload = requests.put(
      upload_url + auth.text,
      data=data,
      verify=self.ca_certificate_file)

    self.assertEqual(httplib.CREATED, upload.status_code)

    # after partitions being processed the key will be used for this slave
    self.runComputerPartition(max_quantity=1)

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    certificate_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'srv', 'autocert',
      '_ssl_ca_crt_garbage', 'certificate.pem'))
    self.assertEqual(1, len(certificate_file_list))
    certificate_file = certificate_file_list[0]
    with open(certificate_file) as out:
      stored_cert_data = out.read()
      self.assertTrue(self.certificate_pem in stored_cert_data)
      self.assertTrue(self.key_pem in stored_cert_data)
      self.assertTrue(self.ca.certificate_pem in stored_cert_data)

  def test_https_only(self):
    parameter_dict = self.assertSlaveBase('https-only')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      'https://httpsonly.example.com/test-path',
      result_http.headers['Location']
    )

  def test_custom_domain(self):
    parameter_dict = self.assertSlaveBase('custom_domain')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_custom_domain_wildcard(self):
    parameter_dict = self.parseSlaveParameterDict('custom_domain_wildcard')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': '*.customdomain.example.com',
        'replication_number': '1',
        'url': 'http://*.customdomain.example.com',
        'site_url': 'http://*.customdomain.example.com',
        'secure_access': 'https://*.customdomain.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      'wild.customdomain.example.com', parameter_dict['public-ipv4'],
      'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_custom_domain_ssl_crt_ssl_key(self):
    reference = 'custom_domain_ssl_crt_ssl_key'
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    generate_auth, upload_url = self.assertKedifaKeysWithPop(parameter_dict)

    hostname = reference.translate(None, '_-')
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': LOCAL_IPV4
      },
      parameter_dict
    )

    # as now the place to put the key is known put the key there
    auth = requests.get(
      generate_auth,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, auth.status_code)
    data = self.customdomain_certificate_pem + \
        self.customdomain_key_pem
    upload = requests.put(
      upload_url + auth.text,
      data=data,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, upload.status_code)

    # after partitions being processed the key will be used for this slave
    self.runComputerPartition(max_quantity=1)

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.customdomain_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_type_zope(self):
    parameter_dict = self.assertSlaveBase('type-zope')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

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
    parameter_dict = self.assertSlaveBase(
      'type-zope-virtualhostroot-http-port')

    result = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/http//typezopevirtualhostroothttpport'
      '.example.com:12345//VirtualHostRoot/test-path'
    )

  def test_type_zope_virtualhostroot_https_port(self):
    parameter_dict = self.assertSlaveBase(
      'type-zope-virtualhostroot-https-port')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//typezopevirtualhostroothttpsport'
      '.example.com:12345//VirtualHostRoot/test-path'
    )

  def test_type_notebook(self):
    reference = 'type-notebook'
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    hostname = reference.translate(None, '_-')
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': '%s.nginx.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.nginx.example.com' % (hostname, ),
        'site_url': 'http://%s.nginx.example.com' % (hostname, ),
        'secure_access': 'https://%s.nginx.example.com' % (hostname, ),
        'public-ipv4': LOCAL_IPV4
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      NGINX_HTTPS_PORT)

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  @skip('Feature postponed')
  def test_type_websocket(self):
    # Pure websocket configurable frontend
    raise NotImplementedError

  @skip('Feature postponed')
  def test_apache_ca_certificate(self):
    raise NotImplementedError

  @skip('Feature postponed')
  def test_type_eventsource(self):
    # Caddy: For event source, if I understand
    #        https://github.com/mholt/caddy/issues/1355 correctly, we could use
    #        Caddy as a proxy in front of nginx-push-stream . If we have a
    #        "central shared" caddy instance, can it handle keeping connections
    #        opens for many clients ?
    parameter_dict = self.parseSlaveParameterDict('type-eventsource')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'typeeventsource.nginx.example.com',
        'replication_number': '1',
        'url': 'http://typeeventsource.nginx.example.com',
        'site_url': 'http://typeeventsource.nginx.example.com',
        'secure_access': 'https://typeeventsource.nginx.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'pub',
      NGINX_HTTPS_PORT)

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      '',
      result.content
    )
    headers = result.headers.copy()
    self.assertKeyWithPop('Expires', headers)
    self.assertKeyWithPop('Date', headers)
    self.assertEqual(
      {
        'X-Nginx-PushStream-Explain': 'No channel id provided.',
        'Content-Length': '0',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Connection': 'keep-alive',
        'Server': 'nginx'
      },
      headers
    )

  def test_type_redirect(self):
    parameter_dict = self.assertSlaveBase('type-redirect')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      '%s/test-path' % (self.backend_url,),
      result.headers['Location']
    )

  def test_ssl_proxy_verify_ssl_proxy_ca_crt_unverified(self):
    parameter_dict = self.parseSlaveParameterDict(
      'ssl-proxy-verify_ssl_proxy_ca_crt-unverified')

    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'sslproxyverifysslproxycacrtunverified.example.com',
        'replication_number': '1',
        'url': 'http://sslproxyverifysslproxycacrtunverified.example.com',
        'site_url':
        'http://sslproxyverifysslproxycacrtunverified.example.com',
        'secure_access':
        'https://sslproxyverifysslproxycacrtunverified.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.BAD_GATEWAY,
      result.status_code
    )

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      httplib.BAD_GATEWAY,
      result_http.status_code
    )

  def test_ssl_proxy_verify_ssl_proxy_ca_crt(self):
    parameter_dict = self.assertSlaveBase('ssl-proxy-verify_ssl_proxy_ca_crt')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertFalse('remote_user' in j['Incoming Headers'].keys())

    self.assertEqual(
      'gzip',
      result.headers['Content-Encoding']
    )

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result.headers['Set-Cookie']
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
      'gzip',
      result_http.headers['Content-Encoding']
    )

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result_http.headers['Set-Cookie']
    )

  def test_ssl_proxy_verify_unverified(self):
    parameter_dict = self.assertSlaveBase('ssl-proxy-verify-unverified')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.BAD_GATEWAY,
      result.status_code
    )

  def test_enable_cache_ssl_proxy_verify_ssl_proxy_ca_crt_unverified(self):
    parameter_dict = self.parseSlaveParameterDict(
      'enable_cache-ssl-proxy-verify_ssl_proxy_ca_crt-unverified')

    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain':
        'enablecachesslproxyverifysslproxycacrtunverified.example.com',
        'replication_number': '1',
        'url':
        'http://enablecachesslproxyverifysslproxycacrtunverified.example.com',
        'site_url':
        'http://enablecachesslproxyverifysslproxycacrtunverified.example.com',
        'secure_access':
        'https://enablecachesslproxyverifysslproxycacrtunverified.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.BAD_GATEWAY,
      result.status_code
    )

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      httplib.BAD_GATEWAY,
      result_http.status_code
    )

  def test_enable_cache_ssl_proxy_verify_ssl_proxy_ca_crt(self):
    parameter_dict = self.assertSlaveBase(
      'enable_cache-ssl-proxy-verify_ssl_proxy_ca_crt')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = result.headers.copy()

    self.assertKeyWithPop('Via', headers)
    self.assertKeyWithPop('Server', headers)
    self.assertKeyWithPop('Date', headers)
    self.assertKeyWithPop('Age', headers)

    # drop keys appearing randomly in headers
    headers.pop('Transfer-Encoding', None)
    headers.pop('Content-Length', None)
    headers.pop('Connection', None)
    headers.pop('Keep-Alive', None)

    self.assertEqual(
      {'Content-type': 'application/json',
       'Set-Cookie': 'secured=value;secure, nonsecured=value',
       'Content-Encoding': 'gzip', 'Vary': 'Accept-Encoding'},
      headers
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
      'gzip',
      result_direct.headers['Content-Encoding']
    )

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result_direct.headers['Set-Cookie']
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
      'gzip',
      result_direct_https_backend.headers['Content-Encoding']
    )

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result_direct_https_backend.headers['Set-Cookie']
    )

  def test_enable_cache_ssl_proxy_verify_unverified(self):
    parameter_dict = self.assertSlaveBase(
      'enable_cache-ssl-proxy-verify-unverified')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.BAD_GATEWAY,
      result.status_code
    )

  def test_type_zope_ssl_proxy_verify_ssl_proxy_ca_crt_unverified(self):
    parameter_dict = self.parseSlaveParameterDict(
      'type-zope-ssl-proxy-verify_ssl_proxy_ca_crt-unverified')

    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'typezopesslproxyverifysslproxycacrtunverified.example.com',
        'replication_number': '1',
        'url':
        'http://typezopesslproxyverifysslproxycacrtunverified.example.com',
        'site_url':
        'http://typezopesslproxyverifysslproxycacrtunverified.example.com',
        'secure_access':
        'https://typezopesslproxyverifysslproxycacrtunverified.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.BAD_GATEWAY,
      result.status_code
    )

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      httplib.BAD_GATEWAY,
      result_http.status_code
    )

  def test_type_zope_ssl_proxy_verify_ssl_proxy_ca_crt(self):
    parameter_dict = self.assertSlaveBase(
      'type-zope-ssl-proxy-verify_ssl_proxy_ca_crt')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertFalse('remote_user' in j['Incoming Headers'].keys())

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//'
      'typezopesslproxyverifysslproxycacrt.example.com:443/'
      '/VirtualHostRoot/test-path'
    )

    result = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/http//'
      'typezopesslproxyverifysslproxycacrt.example.com:80/'
      '/VirtualHostRoot/test-path'
    )

  def test_type_zope_ssl_proxy_verify_unverified(self):
    parameter_dict = self.assertSlaveBase(
      'type-zope-ssl-proxy-verify-unverified')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.BAD_GATEWAY,
      result.status_code
    )

  def test_monitor_ipv6_test(self):
    parameter_dict = self.assertSlaveBase('monitor-ipv6-test')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.NOT_FOUND, result.status_code)

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(httplib.NOT_FOUND, result_http.status_code)

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
    parameter_dict = self.assertSlaveBase('monitor-ipv4-test')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.NOT_FOUND, result.status_code)

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(httplib.NOT_FOUND, result_http.status_code)

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
    parameter_dict = self.assertSlaveBase('re6st-optimal-test')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.NOT_FOUND, result.status_code)

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(httplib.NOT_FOUND, result_http.status_code)

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
    parameter_dict = self.assertSlaveBase('enable_cache')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = result.headers.copy()

    self.assertKeyWithPop('Via', headers)
    self.assertKeyWithPop('Server', headers)
    self.assertKeyWithPop('Date', headers)
    self.assertKeyWithPop('Age', headers)

    # drop keys appearing randomly in headers
    headers.pop('Transfer-Encoding', None)
    headers.pop('Content-Length', None)
    headers.pop('Connection', None)
    headers.pop('Keep-Alive', None)

    self.assertEqual(
      {'Content-type': 'application/json',
       'Set-Cookie': 'secured=value;secure, nonsecured=value',
       'Content-Encoding': 'gzip', 'Vary': 'Accept-Encoding'},
      headers
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
      'gzip',
      result_direct.headers['Content-Encoding']
    )

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result_direct.headers['Set-Cookie']
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
      'gzip',
      result_direct_https_backend.headers['Content-Encoding']
    )

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result_direct_https_backend.headers['Set-Cookie']
    )

  def test_enable_cache_disable_no_cache_request(self):
    parameter_dict = self.assertSlaveBase(
      'enable_cache-disable-no-cache-request')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      headers={'Pragma': 'no-cache', 'Cache-Control': 'something'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = result.headers.copy()

    self.assertKeyWithPop('Via', headers)
    self.assertKeyWithPop('Server', headers)
    self.assertKeyWithPop('Date', headers)
    self.assertKeyWithPop('Age', headers)

    # drop keys appearing randomly in headers
    headers.pop('Transfer-Encoding', None)
    headers.pop('Content-Length', None)
    headers.pop('Connection', None)
    headers.pop('Keep-Alive', None)

    self.assertEqual(
      {'Content-type': 'application/json',
       'Set-Cookie': 'secured=value;secure, nonsecured=value',
       'Content-Encoding': 'gzip', 'Vary': 'Accept-Encoding'},
      headers
    )

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertFalse('pragma' in j['Incoming Headers'].keys())

  def test_enable_cache_disable_via_header(self):
    parameter_dict = self.assertSlaveBase('enable_cache-disable-via-header')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = result.headers.copy()

    self.assertKeyWithPop('Server', headers)
    self.assertKeyWithPop('Date', headers)
    self.assertKeyWithPop('Age', headers)

    # drop keys appearing randomly in headers
    headers.pop('Transfer-Encoding', None)
    headers.pop('Content-Length', None)
    headers.pop('Connection', None)
    headers.pop('Keep-Alive', None)

    self.assertEqual(
      {'Content-type': 'application/json',
       'Set-Cookie': 'secured=value;secure, nonsecured=value',
       'Content-Encoding': 'gzip', 'Vary': 'Accept-Encoding'},
      headers
    )

  def test_enable_http2_false(self):
    parameter_dict = self.assertSlaveBase('enable-http2-false')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

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
      {
        'Vary': 'Accept-Encoding',
        'Content-Type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
        'Content-Encoding': 'gzip',
      },
      headers
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_enable_http2_default(self):
    parameter_dict = self.assertSlaveBase('enable-http2-default')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

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
      {
        'Vary': 'Accept-Encoding',
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
        'Content-Encoding': 'gzip',
      },
      headers
    )

    self.assertTrue(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_prefer_gzip_encoding_to_backend(self):
    parameter_dict = self.assertSlaveBase('prefer-gzip-encoding-to-backend')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      headers={'Accept-Encoding': 'deflate'})

    self.assertEqualResultJson(result, 'Path', '/test-path')

    self.assertEqual(
      'deflate', result.json()['Incoming Headers']['accept-encoding'])

  def test_disabled_cookie_list(self):
    parameter_dict = self.assertSlaveBase('disabled-cookie-list')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      cookies=dict(
          Chocolate='absent',
          Vanilia='absent',
          Coffee='present'
        ))

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    self.assertEqual(
      'Coffee=present', result.json()['Incoming Headers']['cookie'])

  def test_apache_custom_http_s_rejected(self):
    parameter_dict = self.parseSlaveParameterDict(
      'apache_custom_http_s-rejected')
    self.assertEqual(
      {
        'request-error-list': ["slave not authorized"]
      },
      parameter_dict)
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
    parameter_dict = self.parseSlaveParameterDict(
      'apache_custom_http_s-accepted')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'replication_number': '1',
        'public-ipv4': LOCAL_IPV4
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      'apachecustomhttpsaccepted.example.com',
      parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

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
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value'
      },
      headers
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

  def test_caddy_custom_http_s_rejected(self):
    parameter_dict = self.parseSlaveParameterDict(
      'caddy_custom_http_s-rejected')
    self.assertEqual(
      {
        'request-error-list': ["slave not authorized"]
      },
      parameter_dict)
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

  def test_caddy_custom_http_s(self):
    parameter_dict = self.parseSlaveParameterDict(
      'caddy_custom_http_s')
    self.assertEqual(
      {
        'request-error-list': ["slave not authorized"]
      },
      parameter_dict)
    slave_configuration_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'etc', '*slave-conf.d', '*.conf'))
    # no configuration file contains provided custom http
    configuration_file_with_custom_https_list = [
      q for q in slave_configuration_file_list
      if 'caddy_custom_https_filled_in_rejected_2' in open(q).read()]
    self.assertEqual([], configuration_file_with_custom_https_list)

    configuration_file_with_custom_http_list = [
      q for q in slave_configuration_file_list
      if 'caddy_custom_http_filled_in_rejected_2' in open(q).read()]
    self.assertEqual([], configuration_file_with_custom_http_list)

  def test_caddy_custom_http_s_accepted(self):
    parameter_dict = self.parseSlaveParameterDict(
      'caddy_custom_http_s-accepted')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'replication_number': '1',
        'public-ipv4': LOCAL_IPV4
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      'caddycustomhttpsaccepted.example.com',
      parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

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
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value'
      },
      headers
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
    parameter_dict = self.assertSlaveBase('url_https-url')

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

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
      'public-ipv4': LOCAL_IPV4,
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
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'replicate': {
        'url': cls.backend_url,
      },
    }

  def test(self):
    parameter_dict = self.parseSlaveParameterDict('replicate')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'replicate.example.com',
        'replication_number': '2',
        'url': 'http://replicate.example.com',
        'site_url': 'http://replicate.example.com',
        'secure_access': 'https://replicate.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

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
      'public-ipv4': LOCAL_IPV4,
      'enable-http2-by-default': 'false',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
      'automatic-internal-kedifa-caucase-csr': 'true',
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
    parameter_dict = self.parseSlaveParameterDict('enable-http2-default')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'enablehttp2default.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2default.example.com',
        'site_url': 'http://enablehttp2default.example.com',
        'secure_access':
        'https://enablehttp2default.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_enable_http2_false(self):
    parameter_dict = self.parseSlaveParameterDict('enable-http2-false')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'enablehttp2false.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2false.example.com',
        'site_url': 'http://enablehttp2false.example.com',
        'secure_access':
        'https://enablehttp2false.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_enable_http2_true(self):
    parameter_dict = self.parseSlaveParameterDict('enable-http2-true')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'enablehttp2true.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2true.example.com',
        'site_url': 'http://enablehttp2true.example.com',
        'secure_access':
        'https://enablehttp2true.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
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
      'public-ipv4': LOCAL_IPV4,
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
      'automatic-internal-kedifa-caucase-csr': 'true',
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
    parameter_dict = self.parseSlaveParameterDict('enable-http2-default')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'enablehttp2default.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2default.example.com',
        'site_url': 'http://enablehttp2default.example.com',
        'secure_access':
        'https://enablehttp2default.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    self.assertTrue(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_enable_http2_false(self):
    parameter_dict = self.parseSlaveParameterDict('enable-http2-false')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'enablehttp2false.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2false.example.com',
        'site_url': 'http://enablehttp2false.example.com',
        'secure_access':
        'https://enablehttp2false.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_enable_http2_true(self):
    parameter_dict = self.parseSlaveParameterDict('enable-http2-true')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'enablehttp2true.example.com',
        'replication_number': '1',
        'url': 'http://enablehttp2true.example.com',
        'site_url': 'http://enablehttp2true.example.com',
        'secure_access':
        'https://enablehttp2true.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
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
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'default': {
      },
    }

  def test_default(self):
    parameter_dict = self.parseSlaveParameterDict('default')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'default.None',
        'replication_number': '1',
        'url': 'http://default.None',
        'site_url': 'http://default.None',
        'secure_access': 'https://default.None',
        'public-ipv4': None,
      },
      parameter_dict
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
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'default': {
      },
    }

  def test_default(self):
    parameter_dict = self.parseSlaveParameterDict('default')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'default.None',
        'replication_number': '1',
        'url': 'http://default.None',
        'site_url': 'http://default.None',
        'secure_access': 'https://default.None',
        'public-ipv4': None,
      },
      parameter_dict
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


class TestMalformedBackenUrlSlave(SlaveHttpFrontendTestCase,
                                  TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'nginx-domain': 'nginx.example.com',
      'public-ipv4': LOCAL_IPV4,
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'empty': {
      },
      'url': {
        'url': "https://[fd46::c2ae]:!py!u'123123'",
      },
      'https-url': {
        'https-url': "https://[fd46::c2ae]:!py!u'123123'",
      }
    }

  def test_master_partition_state(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')

    expected_parameter_dict = {
      'monitor-base-url': None,
      'domain': 'example.com',
      'accepted-slave-amount': '1',
      'rejected-slave-amount': '2',
      'kedifa-caucase-url': 'http://[%s]:8890' % (GLOBAL_IPV6,),
      'slave-amount': '3',
      'rejected-slave-dict': {
        '_https-url': ['slave https-url "https://[fd46::c2ae]:!py!u\'123123\'"'
                       ' invalid'],
        '_url': [u'slave url "https://[fd46::c2ae]:!py!u\'123123\'" invalid']
      }
    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

  def test_empty(self):
    parameter_dict = self.parseSlaveParameterDict('empty')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'empty.example.com',
        'replication_number': '1',
        'url': 'http://empty.example.com',
        'site_url': 'http://empty.example.com',
        'secure_access': 'https://empty.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.NOT_FOUND, result.status_code)

  def test_url(self):
    parameter_dict = self.parseSlaveParameterDict('url')
    self.assertEqual(
      {
        'request-error-list': [
          "slave url \"https://[fd46::c2ae]:!py!u'123123'\" invalid"]
      },
      parameter_dict
    )

  def test_https_url(self):
    parameter_dict = self.parseSlaveParameterDict('https-url')
    self.assertEqual(
      {
        'request-error-list': [
          "slave https-url \"https://[fd46::c2ae]:!py!u'123123'\" invalid"]
      },
      parameter_dict
    )


class TestDefaultMonitorHttpdPort(SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      '-frontend-1-state': 'stopped',
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'test': {
        'url': cls.backend_url,
      },
    }

  def test(self):
    parameter_dict = self.parseSlaveParameterDict('test')
    self.assertKeyWithPop('log-access-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'test.None', 'replication_number': '1',
        'url': 'http://test.None', 'site_url': 'http://test.None',
        'secure_access': 'https://test.None', 'public-ipv4': None},
      parameter_dict
    )
    master_monitor_conf = open(os.path.join(
      self.instance_path, 'TestDefaultMonitorHttpdPort-0', 'etc',
      'monitor-httpd.conf')).read()
    slave_monitor_conf = open(os.path.join(
      self.instance_path, 'TestDefaultMonitorHttpdPort-2', 'etc',
      'monitor-httpd.conf')).read()

    self.assertTrue(
      'Listen [%s]:8196' % (GLOBAL_IPV6,) in master_monitor_conf)
    self.assertTrue(
      'Listen [%s]:8072' % (GLOBAL_IPV6,) in slave_monitor_conf)


class TestQuicEnabled(SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'nginx-domain': 'nginx.example.com',
      'public-ipv4': LOCAL_IPV4,
      'enable-quic': 'true',
      '-frontend-authorized-slave-string':
      '_apache_custom_http_s-accepted _caddy_custom_http_s-accepted',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
      'mpm-graceful-shutdown-timeout': 2,
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'url': {
        'url': cls.backend_url,
      },
    }

  def getMasterPartitionPath(self):
    # partition w/o etc/trafficserver, but with buildout.cfg
    return [
      q for q in glob.glob(os.path.join(self.instance_path, '*',))
      if not os.path.exists(
        os.path.join(q, 'etc', 'trafficserver')) and os.path.exists(
          os.path.join(q, 'buildout.cfg'))][0]

  def getSlavePartitionPath(self):
    # partition w/ etc/trafficserver
    return [
      q for q in glob.glob(os.path.join(self.instance_path, '*',))
      if os.path.exists(os.path.join(q, 'etc', 'trafficserver'))][0]

  def test_url(self):
    parameter_dict = self.parseSlaveParameterDict('url')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'url.example.com',
        'replication_number': '1',
        'url': 'http://url.example.com',
        'site_url': 'http://url.example.com',
        'secure_access': 'https://url.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertFalse('remote_user' in j['Incoming Headers'].keys())

    self.assertKeyWithPop('Date', result.headers)
    self.assertKeyWithPop('Content-Length', result.headers)

    quic_status, quic_result = getQUIC(
      'https://%s/%s' % (parameter_dict['domain'], 'test-path'),
      parameter_dict['public-ipv4'],
      HTTPS_PORT
    )

    self.assertTrue(quic_status, quic_result)

    try:
      quic_jsoned = quic_result.split('body: ')[2].split('trailers')[0]
    except Exception:
      raise ValueError('JSON not found at all in QUIC result:\n%s' % (
        quic_result,))
    try:
      j = json.loads(quic_jsoned)
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (quic_jsoned,))
    key = 'Path'
    self.assertTrue(key in j, 'No key %r in %s' % (key, j))
    self.assertEqual('/test-path', j[key])


class TestSlaveBadParameters(SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'nginx-domain': 'nginx.example.com',
      'public-ipv4': LOCAL_IPV4,
      '-frontend-authorized-slave-string': '_caddy_custom_http_s-reject',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
      'mpm-graceful-shutdown-timeout': 2,
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'caddy_custom_http_s-reject': {
        'caddy_custom_https': """DestroyCaddyHttps
For sure
This shall not be valid
https://www.google.com {}""",
        'caddy_custom_http': """DestroyCaddyHttp
For sure
This shall not be valid
https://www.google.com {}""",
      },
      're6st-optimal-test-nocomma': {
        're6st-optimal-test': 'nocomma',
      },
      're6st-optimal-test-unsafe': {
        're6st-optimal-test':
        'new\nline;rm -fr ~;,new\\line\n[s${esection:eoption}',
      },
      'custom_domain-unsafe': {
        'custom_domain': '${section:option} afterspace\nafternewline',
      },
      'server-alias-unsafe': {
        'server-alias': '${section:option} afterspace',
      },
      'server-alias-same': {
        'url': cls.backend_url,
        'server-alias': 'serveraliassame.example.com',
      },
      'virtualhostroot-http-port-unsafe': {
        'type': 'zope',
        'url': cls.backend_url,
        'virtualhostroot-http-port': '${section:option}',
      },
      'virtualhostroot-https-port-unsafe': {
        'type': 'zope',
        'url': cls.backend_url,
        'virtualhostroot-https-port': '${section:option}',
      },
      'default-path-unsafe': {
        'type': 'zope',
        'url': cls.backend_url,
        'default-path': '${section:option}\nn"\newline\n}\n}proxy\n/slashed',
      },
      'monitor-ipv4-test-unsafe': {
        'monitor-ipv4-test': '${section:option}\nafternewline ipv4',
      },
      'monitor-ipv6-test-unsafe': {
        'monitor-ipv6-test': '${section:option}\nafternewline ipv6',
      }
    }

  def test_master_partition_state(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')

    expected_parameter_dict = {
      'monitor-base-url': None,
      'domain': 'example.com',
      'kedifa-caucase-url': 'http://[%s]:8890' % (GLOBAL_IPV6,),
      'accepted-slave-amount': '8',
      'rejected-slave-amount': '4',
      'slave-amount': '12',
      'rejected-slave-dict': {
        '_caddy_custom_http_s-reject': [
          'slave caddy_custom_http configuration invalid',
          'slave caddy_custom_https configuration invalid'],
        '_custom_domain-unsafe': [
          "custom_domain '${section:option} afterspace\\nafternewline' invalid"
        ],
        '_server-alias-unsafe': [
          "server-alias '${section:option}' not valid",
          "server-alias 'afterspace' not valid"
        ],
        '_ssl_key-ssl_crt-unsafe': [
          'slave ssl_key and ssl_crt does not match'
        ]
      }
    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

  def test_server_alias_same(self):
    parameter_dict = self.parseSlaveParameterDict('server-alias-same')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'serveraliassame.example.com',
        'replication_number': '1',
        'url': 'http://serveraliassame.example.com',
        'site_url': 'http://serveraliassame.example.com',
        'secure_access': 'https://serveraliassame.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_re6st_optimal_test_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict('re6st-optimal-test-unsafe')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 're6stoptimaltestunsafe.example.com',
        'replication_number': '1',
        'url': 'http://re6stoptimaltestunsafe.example.com',
        'site_url': 'http://re6stoptimaltestunsafe.example.com',
        'secure_access': 'https://re6stoptimaltestunsafe.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.NOT_FOUND, result.status_code)

    # rewrite SR/bin/is-icmp-packet-lost
    open(
      os.path.join(
        self.software_path, 'bin', 'check-re6st-optimal-status'), 'w'
    ).write('echo "$@"')
    # call the monitor for this partition
    monitor_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'monitor-promise',
        'check-_re6st-optimal-test-unsafe-re6st-optimal-test'))[0]

    # Note: The result is a bit differnt from the request (newlines stripped),
    #       but good enough to prove, that ${esection:eoption} has been
    #       correctly passed to the script.
    self.assertEqual(
      '-4 newline [s${esection:eoption} -6 new line;rm -fr ~;',
      subprocess.check_output(monitor_file).strip()
    )

  def test_re6st_optimal_test_nocomma(self):
    parameter_dict = self.parseSlaveParameterDict('re6st-optimal-test-nocomma')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 're6stoptimaltestnocomma.example.com',
        'replication_number': '1',
        'url': 'http://re6stoptimaltestnocomma.example.com',
        'site_url': 'http://re6stoptimaltestnocomma.example.com',
        'secure_access': 'https://re6stoptimaltestnocomma.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.NOT_FOUND, result.status_code)

    # assert that there is no nocomma file
    monitor_file_list = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'monitor-promise',
        'check-_re6st-optimal-test-nocomma-re6st-optimal-test'))
    self.assertEqual(
      [],
      monitor_file_list
    )

  def test_custom_domain_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict('custom_domain-unsafe')
    self.assertEqual(
      {
        'request-error-list': [
          "custom_domain '${section:option} afterspace\\nafternewline' invalid"
        ]
      },
      parameter_dict
    )

  def test_server_alias_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict('server-alias-unsafe')
    self.assertEqual(
      {
        'request-error-list': [
          "server-alias '${section:option}' not valid", "server-alias "
          "'afterspace' not valid"]
      },
      parameter_dict
    )

  def test_virtualhostroot_http_port_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict(
      'virtualhostroot-http-port-unsafe')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'virtualhostroothttpportunsafe.example.com',
        'replication_number': '1',
        'url': 'http://virtualhostroothttpportunsafe.example.com',
        'site_url': 'http://virtualhostroothttpportunsafe.example.com',
        'secure_access':
        'https://virtualhostroothttpportunsafe.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/http//virtualhostroothttpportunsafe'
      '.example.com:0//VirtualHostRoot/test-path'
    )

  def test_virtualhostroot_https_port_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict(
      'virtualhostroot-https-port-unsafe')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'virtualhostroothttpsportunsafe.example.com',
        'replication_number': '1',
        'url': 'http://virtualhostroothttpsportunsafe.example.com',
        'site_url': 'http://virtualhostroothttpsportunsafe.example.com',
        'secure_access':
        'https://virtualhostroothttpsportunsafe.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//virtualhostroothttpsportunsafe'
      '.example.com:0//VirtualHostRoot/test-path'
    )

  def default_path_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict('default-path-unsafe')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertEqual(
      {
        'domain': 'defaultpathunsafe.example.com',
        'replication_number': '1',
        'url': 'http://defaultpathunsafe.example.com',
        'site_url': 'http://defaultpathunsafe.example.com',
        'secure_access': 'https://defaultpathunsafe.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], '')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      'https://defaultpathunsafe.example.com:%s/%%24%%7Bsection%%3Aoption%%7D'
      '%%0An%%22%%0Aewline%%0A%%7D%%0A%%7Dproxy%%0A/slashed' % (HTTPS_PORT,),
      result.headers['Location']
    )

  def test_monitor_ipv4_test_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict('monitor-ipv4-test-unsafe')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'monitoripv4testunsafe.example.com',
        'replication_number': '1',
        'url': 'http://monitoripv4testunsafe.example.com',
        'site_url': 'http://monitoripv4testunsafe.example.com',
        'secure_access': 'https://monitoripv4testunsafe.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.NOT_FOUND, result.status_code)

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(httplib.NOT_FOUND, result_http.status_code)

    # rewrite SR/bin/is-icmp-packet-lost
    open(
      os.path.join(self.software_path, 'bin', 'is-icmp-packet-lost'), 'w'
    ).write('echo "$@"')
    # call the monitor for this partition
    monitor_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'monitor-promise',
        'check-_monitor-ipv4-test-unsafe-ipv4-packet-list-test'))[0]
    self.assertEqual(
      '-4 -a ${section:option} afternewline ipv4',
      subprocess.check_output(monitor_file).strip()
    )

  def test_monitor_ipv6_test_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict('monitor-ipv6-test-unsafe')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'monitoripv6testunsafe.example.com',
        'replication_number': '1',
        'url': 'http://monitoripv6testunsafe.example.com',
        'site_url': 'http://monitoripv6testunsafe.example.com',
        'secure_access': 'https://monitoripv6testunsafe.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.NOT_FOUND, result.status_code)

    result_http = self.fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(httplib.NOT_FOUND, result_http.status_code)

    # rewrite SR/bin/is-icmp-packet-lost
    open(
      os.path.join(self.software_path, 'bin', 'is-icmp-packet-lost'), 'w'
    ).write('echo "$@"')
    # call the monitor for this partition
    monitor_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'monitor-promise',
        'check-_monitor-ipv6-test-unsafe-ipv6-packet-list-test'))[0]
    self.assertEqual(
      '-a ${section:option} afternewline ipv6',
      subprocess.check_output(monitor_file).strip()
    )

  def test_ssl_key_ssl_crt_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict('ssl_key-ssl_crt-unsafe')
    self.assertEqual(
      {'request-error-list': ["slave ssl_key and ssl_crt does not match"]},
      parameter_dict
    )

  def test_caddy_custom_http_s_reject(self):
    parameter_dict = self.parseSlaveParameterDict('caddy_custom_http_s-reject')
    self.assertEqual(
      {
        'request-error-list': [
          "slave caddy_custom_http configuration invalid",
          "slave caddy_custom_https configuration invalid"
        ]
      },
      parameter_dict
    )


class TestDuplicateSiteKeyProtection(SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'nginx-domain': 'nginx.example.com',
      'public-ipv4': LOCAL_IPV4,
      '-frontend-authorized-slave-string': '_caddy_custom_http_s-reject',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
      'mpm-graceful-shutdown-timeout': 2,
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'site_1': {
        'custom_domain': 'duplicate.example.com',
      },
      'site_2': {
        'custom_domain': 'duplicate.example.com',
      },
      'site_3': {
        'server-alias': 'duplicate.example.com',
      },
      'site_4': {
        'custom_domain': 'duplicate.example.com',
        'server-alias': 'duplicate.example.com',
      },
    }

  def test_master_partition_state(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')

    expected_parameter_dict = {
      'monitor-base-url': None,
      'domain': 'example.com',
      'kedifa-caucase-url': 'http://[%s]:8890' % (GLOBAL_IPV6,),
      'accepted-slave-amount': '1',
      'rejected-slave-amount': '3',
      'slave-amount': '4',
      'rejected-slave-dict': {
        '_site_1': ["custom_domain 'duplicate.example.com' clashes"],
        '_site_3': ["server-alias 'duplicate.example.com' clashes"],
        '_site_4': ["custom_domain 'duplicate.example.com' clashes"]
      }
    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

  def test_site_1(self):
    parameter_dict = self.parseSlaveParameterDict('site_1')
    self.assertEqual(
      {
        'request-error-list': ["custom_domain 'duplicate.example.com' clashes"]
      },
      parameter_dict
    )

  def test_site_2(self):
    parameter_dict = self.parseSlaveParameterDict('site_2')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'duplicate.example.com',
        'replication_number': '1',
        'url': 'http://duplicate.example.com',
        'site_url': 'http://duplicate.example.com',
        'secure_access': 'https://duplicate.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

  def test_site_3(self):
    parameter_dict = self.parseSlaveParameterDict('site_3')
    self.assertEqual(
      {
        'request-error-list': ["server-alias 'duplicate.example.com' clashes"]
      },
      parameter_dict,
    )

  def test_site_4(self):
    parameter_dict = self.parseSlaveParameterDict('site_4')
    self.assertEqual(
      {
        'request-error-list': ["custom_domain 'duplicate.example.com' clashes"]
      },
      parameter_dict
    )


class AutoRestartTestCase(SlaveHttpFrontendTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      '-frontend-1-state': 'stopped',
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'test': {
        'url': cls.backend_url,
      },
    }

  @staticmethod
  def generateHashFromFiles(file_list):
    import hashlib
    hasher = hashlib.md5()
    for path in file_list:
      with open(path, 'r') as afile:
        buf = afile.read()
      hasher.update("%s\n" % len(buf))
      hasher.update(buf)
    hash = hasher.hexdigest()
    return hash

  def test_hashes(self):
    hash_files = [
      'software_release/buildout.cfg',
    ]
    expected_process_names = [
      'frontend_caddy-{hash}-on-watch',
      'frontend_nginx-{hash}-on-watch',
      'trafficserver-{hash}-on-watch',
      'certificate_authority-{hash}-on-watch',
      'crond-{hash}',
    ]

    supervisor = self.getSupervisorRPCServer().supervisor
    process_names = [process['name']
                     for process in supervisor.getAllProcessInfo()]

    hash_files = [os.path.join(self.computer_partition_root_path, path)
                  for path in hash_files]

    for name in expected_process_names:
      h = self.generateHashFromFiles(hash_files)
      expected_process_name = name.format(hash=h)

      self.assertIn(expected_process_name, process_names)


class TestSlaveSlapOSMasterCertificateCompatibility(
  SlaveHttpFrontendTestCase, TestDataMixin):

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'nginx-domain': 'nginx.example.com',
      'public-ipv4': LOCAL_IPV4,
      'apache-certificate': cls.certificate_pem,
      'apache-key': cls.key_pem,
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'nginx_port': NGINX_HTTPS_PORT,
      'plain_nginx_port': NGINX_HTTP_PORT,
      'monitor-httpd-port': MONITOR_HTTPD_PORT,
      '-frontend-config-1-monitor-httpd-port': MONITOR_F1_HTTPD_PORT,
      'mpm-graceful-shutdown-timeout': 2,
      'automatic-internal-kedifa-caucase-csr': 'true',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'ssl_from_master': {
        'url': cls.backend_url,
      },
      'ssl_from_slave': {
        'url': cls.backend_url,
        'ssl_crt': cls.ssl_from_slave_ca_certificate_pem,
        'ssl_key': cls.ssl_from_slave_ca_key_pem,
        'ssl_ca_crt': cls.ca.certificate_pem,
      },
      'custom_domain_ssl_crt_ssl_key': {
        'url': cls.backend_url,
        'ssl_crt': cls.customdomain_certificate_pem,
        'ssl_key': cls.customdomain_key_pem,
        'custom_domain': 'customdomainsslcrtsslkey.example.com'
      },
      'custom_domain_ssl_crt_ssl_key_ssl_ca_crt': {
        'url': cls.backend_url,
        'ssl_crt': cls.customdomain_ca_certificate_pem,
        'ssl_key': cls.customdomain_ca_key_pem,
        'ssl_ca_crt': cls.ca.certificate_pem,
        'custom_domain': 'customdomainsslcrtsslkeysslcacrt.example.com',
      },
      'ssl_ca_crt_only': {
        'url': cls.backend_url,
        'ssl_ca_crt': cls.ca.certificate_pem,
      },
      'ssl_ca_crt_garbage': {
        'url': cls.backend_url,
        'ssl_crt': cls.customdomain_ca_certificate_pem,
        'ssl_key': cls.customdomain_ca_key_pem,
        'ssl_ca_crt': 'some garbage',
      },
      'ssl_ca_crt_does_not_match': {
        'url': cls.backend_url,
        'ssl_crt': cls.certificate_pem,
        'ssl_key': cls.key_pem,
        'ssl_ca_crt': cls.ca.certificate_pem,
      },
    }

  def test_master_partition_state(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')

    expected_parameter_dict = {
      'monitor-base-url': None,
      'domain': 'example.com',
      'accepted-slave-amount': '2',
      'rejected-slave-amount': '0',
      'slave-amount': '2',
      'kedifa-caucase-url': 'http://[%s]:8890' % (GLOBAL_IPV6,),
      'warning-list': [
        'apache-certificate is obsolete, please use kedifa-caucase-url',
        'apache-key is obsolete, please use kedifa-caucase-url',
      ],
      'warning-slave-dict': [
        {
          '_ssl_from_slave': [
            'ssl_crt is obsolete, please use kedifa-caucase-url',
            'ssl_key is obsolete, please use kedifa-caucase-url',
            'ssl_ca_crt is obsolete, please use kedifa-caucase-url',
          ]
        }
      ],
    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

  def test_ssl_from_master(self):
    parameter_dict = self.parseSlaveParameterDict('ssl_from_master')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, '')
    hostname = 'ssl_from_master'.translate(None, '_-')
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': LOCAL_IPV4
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      open('wildcard.example.com.crt').read(),
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    raise NotImplementedError(
      'Show that old style certificate is used from master partition '
      'until something is uploaded to KeDiFa.')

  def test_ssl_from_slave(self):
    raise NotImplementedError(
      'Show that old style certificate is used from slave partition '
      'until something is uploaded to KeDifa. Assert that warning is '
      'emitted to the requester.')

  def test_type_notebook_ssl_from_master(self):
    raise NotImplementedError(
      'Show that old style certificate is used from master partition '
      'until something is uploaded to KeDiFa.')

  def test_type_notebook_ssl_from_slave(self):
    raise NotImplementedError(
      'Show that old style certificate is used from slave partition '
      'until something is uploaded to KeDifa. Assert that warning is '
      'emitted to the requester.')

  def test_ssl_ca_crt_only(self):
    parameter_dict = self.parseSlaveParameterDict('ssl_ca_crt_only')

    self.assertEqual(
      parameter_dict,
      {
        'request-error-list': [
          "ssl_ca_crt is present, so ssl_crt and ssl_key are required"]}
    )
    raise NotImplementedError(
      'Show that old style certificate is used from slave partition '
      'until something is uploaded to KeDifa. Assert that warning is '
      'emitted to the requester.')

  def test_custom_domain_ssl_crt_ssl_key(self):
    reference = 'custom_domain_ssl_crt_ssl_key'
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    generate_auth, upload_url = self.assertKedifaKeysWithPop(parameter_dict)

    hostname = reference.translate(None, '_-')
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': LOCAL_IPV4
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.customdomain_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')
    raise NotImplementedError(
      'Show that old style certificate is used from slave partition '
      'until something is uploaded to KeDifa. Assert that warning is '
      'emitted to the requester.')

  def test_ssl_ca_crt(self):
    parameter_dict = self.parseSlaveParameterDict(
      'custom_domain_ssl_crt_ssl_key_ssl_ca_crt')
    self.assertLogAccessUrlWithPop(parameter_dict)
    generate_auth, upload_url = self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'customdomainsslcrtsslkeysslcacrt.example.com',
        'replication_number': '1',
        'url': 'http://customdomainsslcrtsslkeysslcacrt.example.com',
        'site_url': 'http://customdomainsslcrtsslkeysslcacrt.example.com',
        'secure_access':
        'https://customdomainsslcrtsslkeysslcacrt.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.customdomain_ca_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    raise NotImplementedError('ssl_ca_crt assertion presence is missing, '
                              'only cert...')

    raise NotImplementedError(
      'Show that old style certificate is used from slave partition '
      'until something is uploaded to KeDifa. Assert that warning is '
      'emitted to the requester.')

  def test_ssl_ca_crt_garbage(self):
    parameter_dict = self.parseSlaveParameterDict('ssl_ca_crt_garbage')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'sslcacrtgarbage.example.com',
        'replication_number': '1',
        'url': 'http://sslcacrtgarbage.example.com',
        'site_url': 'http://sslcacrtgarbage.example.com',
        'secure_access':
        'https://sslcacrtgarbage.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    with self.assertRaises(requests.exceptions.SSLError):
      self.fakeHTTPSResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    raise NotImplementedError(
      'Show that old style certificate is used from slave partition '
      'until something is uploaded to KeDifa. Assert that warning is '
      'emitted to the requester.')

  def test_ssl_ca_crt_does_not_match(self):
    parameter_dict = self.parseSlaveParameterDict('ssl_ca_crt_does_not_match')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'sslcacrtdoesnotmatch.example.com',
        'replication_number': '1',
        'url': 'http://sslcacrtdoesnotmatch.example.com',
        'site_url': 'http://sslcacrtdoesnotmatch.example.com',
        'secure_access':
        'https://sslcacrtdoesnotmatch.example.com',
        'public-ipv4': LOCAL_IPV4,
      },
      parameter_dict
    )

    result = self.fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')
    raise NotImplementedError(
      'Show that old style certificate is used from slave partition '
      'until something is uploaded to KeDifa. Assert that warning is '
      'emitted to the requester.')
