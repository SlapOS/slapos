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
import time
import tempfile
import ipaddress
import StringIO
import gzip
import base64
import re
from slapos.recipe.librecipe import generateHashFromFiles
import xml.etree.ElementTree as ET
import urlparse
import socket


try:
    import lzma
except ImportError:
    from backports import lzma

import datetime

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.testing.utils import findFreeTCPPort
setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


# ports chosen to not collide with test systems
HTTP_PORT = '11080'
HTTPS_PORT = '11443'
CAUCASE_PORT = '15090'
KEDIFA_PORT = '15080'

# IP to originate requests from
# has to be not partition one
SOURCE_IP = '127.0.0.1'

# "--resolve" inspired from https://stackoverflow.com/a/44378047/9256748
DNS_CACHE = {}


def add_custom_dns(domain, port, ip):
  port = int(port)
  key = (domain, port)
  value = (socket.AF_INET, 1, 6, '', (ip, port))
  DNS_CACHE[key] = [value]


def new_getaddrinfo(*args):
  return DNS_CACHE[args[:2]]


# for development: debugging logs and install Ctrl+C handler
if os.environ.get('SLAPOS_TEST_DEBUG'):
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


def subprocess_status_output(*args, **kwargs):
  prc = subprocess.Popen(
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    *args,
    **kwargs)
  out, err = prc.communicate()
  return prc.returncode, out


def subprocess_output(*args, **kwargs):
  return subprocess_status_output(*args, **kwargs)[1]


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


def getPluginParameterDict(software_path, filepath):
  """Load the slapos monitor plugin and returns the configuration used by this plugin.

  This allow to check that monitoring plugin are using a proper config.
  """
  # This is implemented by creating a wrapper script that loads the plugin wrapper
  # script and returns its `extra_config_dict`. This might have to be adjusted if
  # internals of slapos promise plugins change.

  bin_file = os.path.join(software_path, 'bin', 'test-plugin-promise')

  monitor_python_with_eggs = os.path.join(software_path, 'bin', 'monitor-pythonwitheggs')
  if not os.path.exists(monitor_python_with_eggs):
    raise ValueError("Monitoring stack's python does not exist at %s" % monitor_python_with_eggs)

  with open(bin_file, 'w') as f:
    f.write("""#!%s
import os
import importlib
import sys
import json

filepath = sys.argv[1]
sys.path[0:0] = [os.path.dirname(filepath)]
filename = os.path.basename(filepath)
module = importlib.import_module(os.path.splitext(filename)[0])

print json.dumps(module.extra_config_dict)
    """ % monitor_python_with_eggs)

  os.chmod(bin_file, 0o755)
  result = subprocess_output([bin_file, filepath]).strip()
  try:
    return json.loads(result)
  except ValueError, e:
    raise ValueError("%s\nResult was: %s" % (e, result))


class TestDataMixin(object):
  def getTrimmedProcessInfo(self):
    return '\n'.join(sorted([
      '%(group)s:%(name)s %(statename)s' % q for q
      in self.callSupervisorMethod('getAllProcessInfo')
      if q['name'] != 'watchdog' and q['group'] != 'watchdog']))

  def assertTestData(self, runtime_data, hash_value_dict=None, msg=None):
    if hash_value_dict is None:
      hash_value_dict = {}
    filename = '%s-%s.txt' % (self.id(), 'CADDY')
    test_data_file = os.path.join(
      os.path.dirname(os.path.realpath(__file__)), 'test_data', filename)

    try:
      test_data = open(test_data_file).read().strip()
    except IOError:
      test_data = ''

    for hash_type, hash_value in hash_value_dict.items():
      runtime_data = runtime_data.replace(hash_value, '{hash-%s}' % (
        hash_type),)

    maxDiff = self.maxDiff
    self.maxDiff = None
    longMessage = self.longMessage
    self.longMessage = True
    try:
      self.assertMultiLineEqual(
        test_data,
        runtime_data,
        msg=msg
      )
    except AssertionError:
      if os.environ.get('SAVE_TEST_DATA', '0') == '1':
        open(test_data_file, 'w').write(runtime_data.strip() + '\n')
      raise
    finally:
      self.maxDiff = maxDiff
      self.longMessage = longMessage

  def _test_file_list(self, slave_dir_list, IGNORE_PATH_LIST=None):
    if IGNORE_PATH_LIST is None:
      IGNORE_PATH_LIST = []
    runtime_data = []
    for slave_var in glob.glob(os.path.join(self.instance_path, '*')):
      for entry in os.walk(os.path.join(slave_var, *slave_dir_list)):
        for filename in entry[2]:
          path = os.path.join(
            entry[0][len(self.instance_path) + 1:], filename)
          if not any([path.endswith(q) for q in IGNORE_PATH_LIST]):
            runtime_data.append(path)
    runtime_data = '\n'.join(sorted(runtime_data))
    self.assertTestData(runtime_data)

  def test_file_list_log(self):
    self._test_file_list(['var', 'log'], [
      # no control at all when cron would kick in, ignore it
      'cron.log',
      # appears late and is quite unstable, no need to assert
      'trafficserver/.diags.log.meta',
      'trafficserver/.manager.log.meta',
      'trafficserver/.squid.log.meta',
      'trafficserver/.traffic.out.meta',
      'trafficserver/diags.log',
      'trafficserver/squid.log',
      # not important, appears sometimes
      'trafficserver/.error.log.meta',
      'trafficserver/error.log',
    ])

  def test_file_list_run(self):
    self._test_file_list(['var', 'run'], [
      # can't be sure regarding its presence
      'caddy_configuration_last_state',
      'validate_configuration_state_signature',
      # run by cron from time to time
      'monitor/monitor-collect.pid',
      # no control regarding if it would or not be running
      'monitor/monitor-bootstrap.pid',
    ])

  def test_file_list_etc_cron_d(self):
    self._test_file_list(['etc', 'cron.d'])

  def test_file_list_plugin(self):
    self._test_file_list(['etc', 'plugin'], ['.pyc'])

  def test_supervisor_state(self):
    # give a chance for etc/run scripts to finish
    time.sleep(1)

    hash_file_list = [os.path.join(
        self.computer_partition_root_path, 'software_release/buildout.cfg')]
    hash_value_dict = {
      'generic': generateHashFromFiles(hash_file_list),
    }
    for caddy_wrapper_path in glob.glob(os.path.join(
      self.instance_path, '*', 'bin', 'caddy-wrapper')):
      partition_id = caddy_wrapper_path.split('/')[-3]
      hash_value_dict[
        'caddy-%s' % (partition_id)] = generateHashFromFiles(
        [caddy_wrapper_path] + hash_file_list
      )
    for backend_haproxy_wrapper_path in glob.glob(os.path.join(
      self.instance_path, '*', 'bin', 'backend-haproxy-wrapper')):
      partition_id = backend_haproxy_wrapper_path.split('/')[-3]
      hash_value_dict[
        'backend-haproxy-%s' % (partition_id)] = generateHashFromFiles(
        [backend_haproxy_wrapper_path] + hash_file_list
      )
    for rejected_slave_publish_path in glob.glob(os.path.join(
      self.instance_path, '*', 'etc', 'Caddyfile-rejected-slave')):
      partition_id = rejected_slave_publish_path.split('/')[-3]
      rejected_slave_pem_path = os.path.join(
        self.instance_path, partition_id, 'etc', 'rejected-slave.pem')
      hash_value_dict[
        'rejected-slave-publish'
      ] = generateHashFromFiles(
        [rejected_slave_publish_path, rejected_slave_pem_path] + hash_file_list
      )

    runtime_data = self.getTrimmedProcessInfo()
    self.assertTestData(runtime_data, hash_value_dict=hash_value_dict)


def fakeHTTPSResult(domain, real_ip, path, port=HTTPS_PORT,
                    headers=None, cookies=None, source_ip=SOURCE_IP):
  if headers is None:
    headers = {}
  # workaround request problem of setting Accept-Encoding
  # https://github.com/requests/requests/issues/2234
  headers.setdefault('Accept-Encoding', 'dummy')
  # Headers to tricks the whole system, like rouge user would do
  headers.setdefault('X-Forwarded-For', '192.168.0.1')
  headers.setdefault('X-Forwarded-Proto', 'irc')
  headers.setdefault('X-Forwarded-Port', '17')

  session = requests.Session()
  if source_ip is not None:
    new_source = source.SourceAddressAdapter(source_ip)
    session.mount('http://', new_source)
    session.mount('https://', new_source)
  socket_getaddrinfo = socket.getaddrinfo
  try:
    add_custom_dns(domain, port, real_ip)
    socket.getaddrinfo = new_getaddrinfo
    return session.get(
      'https://%s:%s/%s' % (domain, port, path),
      verify=False,
      allow_redirects=False,
      headers=headers,
      cookies=cookies
    )
  finally:
    socket.getaddrinfo = socket_getaddrinfo


def fakeHTTPResult(domain, real_ip, path, port=HTTP_PORT,
                   headers=None, source_ip=SOURCE_IP):
  if headers is None:
    headers = {}
  # workaround request problem of setting Accept-Encoding
  # https://github.com/requests/requests/issues/2234
  headers.setdefault('Accept-Encoding', 'dummy')
  # Headers to tricks the whole system, like rouge user would do
  headers.setdefault('X-Forwarded-For', '192.168.0.1')
  headers.setdefault('X-Forwarded-Proto', 'irc')
  headers.setdefault('X-Forwarded-Port', '17')
  headers['Host'] = '%s:%s' % (domain, port)
  session = requests.Session()
  if source_ip is not None:
    new_source = source.SourceAddressAdapter(source_ip)
    session.mount('http://', new_source)
    session.mount('https://', new_source)
  return session.get(
    'http://%s:%s/%s' % (real_ip, port, path),
    headers=headers,
    allow_redirects=False,
  )


class TestHandler(BaseHTTPRequestHandler):
  identification = None

  def do_GET(self):
    timeout = int(self.headers.dict.get('timeout', '0'))
    compress = int(self.headers.dict.get('compress', '0'))
    time.sleep(timeout)
    self.send_response(200)

    if self.identification is not None:
      self.send_header('X-Backend-Identification', self.identification)

    drop_header_list = []
    for header in self.headers.dict.get('x-drop-header', '').split():
      drop_header_list.append(header)
    prefix = 'x-reply-header-'
    length = len(prefix)
    for key, value in self.headers.dict.items():
      if key.startswith(prefix):
        self.send_header(
          '-'.join([q.capitalize() for q in key[length:].split('-')]),
          value.strip()
        )

    if 'Content-Type' not in drop_header_list:
      self.send_header("Content-Type", "application/json")
    if 'Set-Cookie' not in drop_header_list:
      self.send_header('Set-Cookie', 'secured=value;secure')
      self.send_header('Set-Cookie', 'nonsecured=value')

    if 'x-reply-body' not in self.headers.dict:
      response = {
        'Path': self.path,
        'Incoming Headers': self.headers.dict
      }
      response = json.dumps(response, indent=2)
    else:
      response = base64.b64decode(self.headers.dict['x-reply-body'])
    if compress:
      self.send_header('Content-Encoding', 'gzip')
      out = StringIO.StringIO()
      # compress with level 0, to find out if in the middle someting would
      # like to alter the compression
      with gzip.GzipFile(fileobj=out, mode="w", compresslevel=0) as f:
        f.write(response)
      response = out.getvalue()
      self.send_header('Backend-Content-Length', len(response))
    if 'Content-Length' not in drop_header_list:
      self.send_header('Content-Length', len(response))
    self.end_headers()
    self.wfile.write(response)


class HttpFrontendTestCase(SlapOSInstanceTestCase):
  # show full diffs, as it is required for proper analysis of problems
  maxDiff = None

  # minimise partition path
  __partition_reference__ = 'T-'

  @classmethod
  def getInstanceSoftwareType(cls):
    # Because of unknown problem yet, the root instance software type changes
    # from RootSoftwareInstance to '', so always request it with given type
    return "RootSoftwareInstance"

  @classmethod
  def prepareCertificate(cls):
    cls.another_server_ca = CertificateAuthority("Another Server Root CA")
    cls.test_server_ca = CertificateAuthority("Test Server Root CA")
    key, key_pem, csr, csr_pem = createCSR(
      "testserver.example.com", cls._ipv4_address)
    _, cls.test_server_certificate_pem = cls.test_server_ca.signCSR(csr)

    cls.test_server_certificate_file = tempfile.NamedTemporaryFile(
      delete=False
    )

    cls.test_server_certificate_file.write(
        cls.test_server_certificate_pem + key_pem
      )
    cls.test_server_certificate_file.close()

  @classmethod
  def startServerProcess(cls):
    server = HTTPServer(
      (cls._ipv4_address, cls._server_http_port),
      TestHandler)

    server_https = HTTPServer(
      (cls._ipv4_address, cls._server_https_port),
      TestHandler)

    server_https.socket = ssl.wrap_socket(
      server_https.socket,
      certfile=cls.test_server_certificate_file.name,
      server_side=True)

    cls.backend_url = 'http://%s:%s/' % server.server_address
    cls.server_process = multiprocessing.Process(
      target=server.serve_forever, name='HTTPServer')
    cls.server_process.start()
    cls.logger.debug('Started process %s' % (cls.server_process,))

    cls.backend_https_url = 'https://%s:%s/' % server_https.server_address
    cls.server_https_process = multiprocessing.Process(
      target=server_https.serve_forever, name='HTTPSServer')
    cls.server_https_process.start()
    cls.logger.debug('Started process %s' % (cls.server_https_process,))

  @classmethod
  def cleanUpCertificate(cls):
    if getattr(cls, 'test_server_certificate_file', None) is not None:
      os.unlink(cls.test_server_certificate_file.name)

  @classmethod
  def stopServerProcess(cls):
    for server in ['server_process', 'server_https_process']:
      process = getattr(cls, server, None)
      if process is not None:
        cls.logger.debug('Stopping process %s' % (process,))
        process.join(10)
        process.terminate()
        time.sleep(0.1)
        if process.is_alive():
          cls.logger.warning(
            'Process %s still alive' % (process, ))

  @classmethod
  def setUpMaster(cls):
    # run partition until AIKC finishes
    cls.runComputerPartitionUntil(
      cls.untilNotReadyYetNotInMasterKeyGenerateAuthUrl)
    parameter_dict = cls.requestDefaultInstance().getConnectionParameterDict()
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
  def runKedifaUpdater(cls):
    kedifa_updater = None
    for kedifa_updater in sorted(glob.glob(
        os.path.join(
          cls.instance_path, '*', 'etc', 'service', 'kedifa-updater*'))):
      # fetch first kedifa-updater, as by default most of the tests are using
      # only one running partition; in case if test does not need
      # kedifa-updater this method can be overridden
      break
    if kedifa_updater is not None:
      # try few times kedifa_updater
      for i in range(10):
        return_code, output = subprocess_status_output(
          [kedifa_updater, '--once'])
        if return_code == 0:
          break
        # wait for the other updater to work
        time.sleep(2)
      # assert that in the worst case last run was correct
      assert return_code == 0, output
      # give caddy a moment to refresh its config, as sending signal does not
      # block until caddy is refreshed
      time.sleep(2)

  @classmethod
  def createWildcardExampleComCertificate(cls):
    _, cls.key_pem, _, cls.certificate_pem = createSelfSignedCertificate(
      [
        '*.customdomain.example.com',
        '*.example.com',
        '*.alias1.example.com',
      ])

  @classmethod
  def runComputerPartitionUntil(cls, until):
    max_try = 10
    try_num = 1
    while True:
      if until():
        break
      if try_num > max_try:
        raise ValueError('Failed to run computer partition with %r' % (until,))
      try:
        cls.slap.waitForInstance()
      except Exception:
        cls.logger.exception("Error during until run")
      try_num += 1

  @classmethod
  def untilNotReadyYetNotInMasterKeyGenerateAuthUrl(cls):
    parameter_dict = cls.requestDefaultInstance().getConnectionParameterDict()
    key = 'master-key-generate-auth-url'
    if key not in parameter_dict:
      return False
    if 'NotReadyYet' in parameter_dict[key]:
      return False
    return True

  @classmethod
  def callSupervisorMethod(cls, method, *args, **kwargs):
    with cls.slap.instance_supervisor_rpc as instance_supervisor:
      return getattr(instance_supervisor, method)(*args, **kwargs)

  def assertRejectedSlavePromiseWithPop(self, parameter_dict):
    rejected_slave_promise_url = parameter_dict.pop(
      'rejected-slave-promise-url')

    try:
      result = requests.get(rejected_slave_promise_url, verify=False)
      if result.text == '':
        result_json = {}
      else:
        result_json = result.json()
      self.assertEqual(
        parameter_dict['rejected-slave-dict'],
        result_json
      )
    except AssertionError:
      raise
    except Exception as e:
      self.fail(e)

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
    self.assertEqual(
      httplib.OK,
      requests.get(url + 'access.log', verify=False).status_code
    )
    self.assertEqual(
      httplib.OK,
      requests.get(url + 'error.log', verify=False).status_code
    )

  def assertKedifaKeysWithPop(self, parameter_dict, prefix=''):
    generate_auth_url = parameter_dict.pop('%skey-generate-auth-url' % (
      prefix,))
    upload_url = parameter_dict.pop('%skey-upload-url' % (prefix,))
    kedifa_ipv6_base = 'https://[%s]:%s' % (self._ipv6_address, KEDIFA_PORT)
    base = '^' + kedifa_ipv6_base.replace(
      '[', r'\[').replace(']', r'\]') + '/.{32}'
    self.assertRegexpMatches(
      generate_auth_url,
      base + r'\/generateauth$'
    )
    self.assertRegexpMatches(
      upload_url,
      base + r'\?auth=$'
    )

    kedifa_caucase_url = parameter_dict.pop('kedifa-caucase-url')
    self.assertEqual(
      kedifa_caucase_url,
      'http://[%s]:%s' % (self._ipv6_address, CAUCASE_PORT),
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
    super(HttpFrontendTestCase, self).tearDown()

  def parseParameterDict(self, parameter_dict):
    parsed_parameter_dict = {}
    for key, value in parameter_dict.items():
      if key in [
        'rejected-slave-dict',
        'warning-slave-dict',
        'warning-list',
        'request-error-list',
        'log-access-url']:
        value = json.loads(value)
      parsed_parameter_dict[key] = value
    return parsed_parameter_dict

  def getMasterPartitionPath(self):
    return '/' + os.path.join(
      *glob.glob(
        os.path.join(
          self.instance_path, '*', 'etc', 'Caddyfile-rejected-slave'
        )
      )[0].split('/')[:-2])

  def parseConnectionParameterDict(self):
    return self.parseParameterDict(
      self.requestDefaultInstance().getConnectionParameterDict()
    )

  @classmethod
  def waitForMethod(cls, name, method):
    wait_time = 600
    begin = time.time()
    try_num = 0
    cls.logger.debug('%s for %is' % (name, wait_time,))
    while True:
      try:
        try_num += 1
        method()
      except Exception:
        if time.time() - begin > wait_time:
          cls.logger.exception(
            "Error during %s after %.2fs" % (name, (time.time() - begin),))
          raise
        else:
          time.sleep(0.5)
      else:
        cls.logger.info("%s took %.2fs" % (name, (time.time() - begin),))
        break

  @classmethod
  def waitForCaddy(cls):
    def method():
      fakeHTTPSResult(
        cls._ipv4_address, cls._ipv4_address,
        '/',
      )
    cls.waitForMethod('waitForCaddy', method)

  @classmethod
  def _cleanup(cls, snapshot_name):
    cls.cleanUpCertificate()
    cls.stopServerProcess()
    super(HttpFrontendTestCase, cls)._cleanup(snapshot_name)

  @classmethod
  def setUpClass(cls):
    try:
      cls.createWildcardExampleComCertificate()
      cls.prepareCertificate()
      # find ports once to be able startServerProcess many times
      cls._server_http_port = findFreeTCPPort(cls._ipv4_address)
      cls._server_https_port = findFreeTCPPort(cls._ipv4_address)
      cls._server_https_auth_port = findFreeTCPPort(cls._ipv4_address)
      cls.startServerProcess()
    except BaseException:
      cls.logger.exception("Error during setUpClass")
      cls._cleanup("{}.{}.setUpClass".format(cls.__module__, cls.__name__))
      cls.setUp = lambda self: self.fail('Setup Class failed.')
      raise

    super(HttpFrontendTestCase, cls).setUpClass()

    try:
      # expose instance directory
      cls.instance_path = cls.slap.instance_directory
      # expose software directory, extract from found computer partition
      cls.software_path = os.path.realpath(os.path.join(
          cls.computer_partition_root_path, 'software_release'))
      # do working directory
      cls.working_directory = os.path.join(os.path.realpath(
          os.environ.get(
              'SLAPOS_TEST_WORKING_DIR',
              os.path.join(os.getcwd(), '.slapos'))),
          'caddy-frontend-test')
      if not os.path.isdir(cls.working_directory):
        os.mkdir(cls.working_directory)
      cls.setUpMaster()
      cls.waitForCaddy()
    except BaseException:
      cls.logger.exception("Error during setUpClass")
      # "{}.{}.setUpClass".format(cls.__module__, cls.__name__) is already used
      # by SlapOSInstanceTestCase.setUpClass so we use another name for
      # snapshot, to make sure we don't store another snapshot in same
      # directory.
      cls._cleanup("{}.SlaveHttpFrontendTestCase.{}.setUpClass".format(
        cls.__module__, cls.__name__))
      cls.setUp = lambda self: self.fail('Setup Class failed.')
      raise


class SlaveHttpFrontendTestCase(HttpFrontendTestCase):
  @classmethod
  def requestDefaultInstance(cls, state='started'):
    default_instance = super(
      SlaveHttpFrontendTestCase, cls).requestDefaultInstance(state=state)
    if state != 'destroyed':
      cls.requestSlaves()
    return default_instance

  @classmethod
  def requestSlaves(cls):
    software_url = cls.getSoftwareURL()
    for slave_reference, partition_parameter_kw in cls\
            .getSlaveParameterDictDict().items():
      cls.logger.debug(
        'requesting slave "%s" software:%s parameters:%s',
        slave_reference, software_url, partition_parameter_kw)
      cls.slap.request(
        software_release=software_url,
        partition_reference=slave_reference,
        partition_parameter_kw=partition_parameter_kw,
        shared=True
      )

  @classmethod
  def setUpClass(cls):
    super(SlaveHttpFrontendTestCase, cls).setUpClass()

    try:
      cls.setUpSlaves()
      cls.waitForSlave()
    except BaseException:
      cls.logger.exception("Error during setUpClass")
      # "{}.{}.setUpClass".format(cls.__module__, cls.__name__) is already used
      # by SlapOSInstanceTestCase.setUpClass so we use another name for
      # snapshot, to make sure we don't store another snapshot in same
      # directory.
      cls._cleanup("{}.SlaveHttpFrontendTestCase.{}.setUpClass".format(
        cls.__module__, cls.__name__))
      cls.setUp = lambda self: self.fail('Setup Class failed.')
      raise

  @classmethod
  def waitForSlave(cls):
    def method():
      for parameter_dict in cls.getSlaveConnectionParameterDictList():
        if 'domain' in parameter_dict and 'public-ipv4' in parameter_dict:
          try:
            fakeHTTPSResult(
              parameter_dict['domain'], parameter_dict['public-ipv4'], '/')
          except requests.exceptions.InvalidURL:
            # ignore slaves to which connection is impossible by default
            continue
    cls.waitForMethod('waitForSlave', method)

  @classmethod
  def getSlaveConnectionParameterDictList(cls):
    parameter_dict_list = []

    for slave_reference, partition_parameter_kw in cls\
            .getSlaveParameterDictDict().items():
      parameter_dict_list.append(cls.slap.request(
        software_release=cls.getSoftwareURL(),
        partition_reference=slave_reference,
        partition_parameter_kw=partition_parameter_kw,
        shared=True
      ).getConnectionParameterDict())
    return parameter_dict_list

  @classmethod
  def untilSlavePartitionReady(cls):
    # all on-watch services shall not be exited
    for process in cls.callSupervisorMethod('getAllProcessInfo'):
      if process['name'].endswith('-on-watch') and \
        process['statename'] == 'EXITED':
        if process['name'].startswith('monitor-http'):
          continue
        return False

    for parameter_dict in cls.getSlaveConnectionParameterDictList():
      log_access_ready = 'log-access-url' in parameter_dict
      key = 'key-generate-auth-url'
      key_generate_auth_ready = key in parameter_dict \
          and 'NotReadyYet' not in parameter_dict[key]
      if not(log_access_ready and key_generate_auth_ready):
        return False

    return True

  @classmethod
  def setUpSlaves(cls):
    cls.runComputerPartitionUntil(
      cls.untilSlavePartitionReady)
    cls.updateSlaveConnectionParameterDictDict()

  @classmethod
  def updateSlaveConnectionParameterDictDict(cls):
    cls.slave_connection_parameter_dict_dict = {}
    # run partition for slaves to be setup
    request = cls.slap.request
    for slave_reference, partition_parameter_kw in cls\
            .getSlaveParameterDictDict().items():
      slave_instance = request(
        software_release=cls.getSoftwareURL(),
        partition_reference=slave_reference,
        partition_parameter_kw=partition_parameter_kw,
        shared=True
      )
      cls.slave_connection_parameter_dict_dict[slave_reference] = \
          slave_instance.getConnectionParameterDict()

  def parseSlaveParameterDict(self, key):
    return self.parseParameterDict(
      self.slave_connection_parameter_dict_dict[
        key
      ]
    )

  def assertSlaveBase(self, reference):
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, '')
    hostname = reference.translate(None, '_-').lower()
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    return parameter_dict


class TestMasterRequestDomain(HttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
    }

  def test(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertRejectedSlavePromiseWithPop(parameter_dict)

    self.assertEqual(
      {
        'monitor-base-url': 'https://[%s]:8401' % self._ipv6_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
        'domain': 'example.com',
        'accepted-slave-amount': '0',
        'rejected-slave-amount': '0',
        'slave-amount': '0',
        'rejected-slave-dict': {}
      },
      parameter_dict
    )


class TestMasterRequest(HttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
    }

  def test(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertRejectedSlavePromiseWithPop(parameter_dict)
    self.assertEqual(
      {
        'monitor-base-url': 'https://[%s]:8401' % self._ipv6_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
        'domain': 'None',
        'accepted-slave-amount': '0',
        'rejected-slave-amount': '0',
        'slave-amount': '0',
        'rejected-slave-dict': {}},
      parameter_dict
    )


class TestSlave(SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'public-ipv4': cls._ipv4_address,
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
      'mpm-graceful-shutdown-timeout': 2,
      'request-timeout': '12',
    }

  @classmethod
  def prepareCertificate(cls):
    cls.ca = CertificateAuthority('TestSlave')
    _, cls.customdomain_ca_key_pem, csr, _ = createCSR(
      'customdomainsslcrtsslkeysslcacrt.example.com')
    _, cls.customdomain_ca_certificate_pem = cls.ca.signCSR(csr)
    _, cls.customdomain_key_pem, _, cls.customdomain_certificate_pem = \
        createSelfSignedCertificate(['customdomainsslcrtsslkey.example.com'])
    super(TestSlave, cls).prepareCertificate()

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'empty': {
      },
      'Url': {
        # make URL "incorrect", with whitespace, nevertheless it shall be
        # correctly handled
        'url': ' ' + cls.backend_url + ' ',
        # authenticating to http backend shall be no-op
        'authenticate-to-backend': True,
      },
      'auth-to-backend': {
        # in here use reserved port for the backend, which is going to be
        # started later
        'url': 'https://%s:%s/' % (
          cls._ipv4_address, cls._server_https_auth_port),
        'authenticate-to-backend': True,
      },
      'auth-to-backend-not-configured': {
        # in here use reserved port for the backend, which is going to be
        # started later
        'url': 'https://%s:%s/' % (
          cls._ipv4_address, cls._server_https_auth_port),
      },
      'auth-to-backend-backend-ignore': {
        'url': cls.backend_https_url,
        'authenticate-to-backend': True,
      },
      'url_https-url': {
        'url': cls.backend_url + 'http',
        'https-url': cls.backend_url + 'https',
        'backend-connect-timeout': 10,
        'backend-connect-retries': 5,
        'request-timeout': 15,
      },
      'server-alias': {
        'url': cls.backend_url,
        'server-alias': 'alias1.example.com alias2.example.com',
      },
      'server-alias-empty': {
        'url': cls.backend_url,
        'server-alias': '',
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
        'https-only': False,
      },
      'custom_domain': {
        'url': cls.backend_url,
        'custom_domain': 'mycustomdomain.example.com',
      },
      'custom_domain_wildcard': {
        'url': cls.backend_url,
        'custom_domain': '*.customdomain.example.com',
      },
      'custom_domain_server_alias': {
        'url': cls.backend_url,
        'custom_domain': 'mycustomdomainserveralias.example.com',
        'server-alias': 'mycustomdomainserveralias1.example.com',
      },
      'custom_domain_ssl_crt_ssl_key': {
        'url': cls.backend_url,
        'custom_domain': 'customdomainsslcrtsslkey.example.com',
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
      'type-zope-prefer-gzip-encoding-to-backend': {
        'url': cls.backend_url,
        'prefer-gzip-encoding-to-backend': 'true',
        'type': 'zope',
      },
      'type-zope-prefer-gzip-encoding-to-backend-https-only': {
        'url': cls.backend_url,
        'prefer-gzip-encoding-to-backend': 'true',
        'type': 'zope',
        'https-only': 'false',
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
        'virtualhostroot-http-port': '12345',
        'https-only': 'false',
      },
      'type-zope-virtualhostroot-https-port': {
        'url': cls.backend_url,
        'type': 'zope',
        'virtualhostroot-https-port': '12345'
      },
      'type-zope-path': {
        'url': cls.backend_url,
        'type': 'zope',
        'path': '///path/to/some/resource///',
      },
      'type-zope-default-path': {
        'url': cls.backend_url,
        'type': 'zope',
        'default-path': '///default-path/to/some/resource///',
      },
      'type-notebook': {
        'url': cls.backend_url,
        'type': 'notebook',
      },
      'type-websocket': {
        'url': cls.backend_url,
        'type': 'websocket',
      },
      'type-websocket-websocket-path-list': {
        'url': cls.backend_url,
        'type': 'websocket',
        'websocket-path-list': '////ws//// /with%20space/',
      },
      'type-websocket-websocket-transparent-false': {
        'url': cls.backend_url,
        'type': 'websocket',
        'websocket-transparent': 'false',
      },
      'type-websocket-websocket-path-list-websocket-transparent-false': {
        'url': cls.backend_url,
        'type': 'websocket',
        'websocket-path-list': '////ws//// /with%20space/',
        'websocket-transparent': 'false',
      },
      # 'type-eventsource': {
      #   'url': cls.backend_url,
      #   'type': 'eventsource',
      # },
      'type-redirect': {
        'url': cls.backend_url,
        'type': 'redirect',
      },
      'type-redirect-custom_domain': {
        'url': cls.backend_url,
        'type': 'redirect',
        'custom_domain': 'customdomaintyperedirect.example.com',
      },
      'enable_cache': {
        'url': cls.backend_url,
        'enable_cache': True,
      },
      'enable_cache_custom_domain': {
        'url': cls.backend_url,
        'enable_cache': True,
        'custom_domain': 'customdomainenablecache.example.com',
      },
      'enable_cache_server_alias': {
        'url': cls.backend_url,
        'enable_cache': True,
        'server-alias': 'enablecacheserveralias1.example.com',
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
      'prefer-gzip-encoding-to-backend': {
        'url': cls.backend_url,
        'prefer-gzip-encoding-to-backend': 'true',
      },
      'prefer-gzip-encoding-to-backend-https-only': {
        'url': cls.backend_url,
        'prefer-gzip-encoding-to-backend': 'true',
        'https-only': 'false',
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
      'ciphers': {
        'ciphers': 'RSA-3DES-EDE-CBC-SHA RSA-AES128-CBC-SHA',
      }
    }

  monitor_setup_url_key = 'monitor-setup-url'

  def test_monitor_setup(self):
    IP = self._ipv6_address
    self.monitor_configuration_list = [
      {
        'htmlUrl': 'https://[%s]:8401/public/feed' % (IP,),
        'text': 'testing partition 0',
        'title': 'testing partition 0',
        'type': 'rss',
        'url': 'https://[%s]:8401/share/private/' % (IP,),
        'version': 'RSS',
        'xmlUrl': 'https://[%s]:8401/public/feed' % (IP,),
      },
      {
        'htmlUrl': 'https://[%s]:8402/public/feed' % (IP,),
        'text': 'kedifa',
        'title': 'kedifa',
        'type': 'rss',
        'url': 'https://[%s]:8402/share/private/' % (IP,),
        'version': 'RSS',
        'xmlUrl': 'https://[%s]:8402/public/feed' % (IP,),
      },
      {
        'htmlUrl': 'https://[%s]:8411/public/feed' % (IP,),
        'text': 'caddy-frontend-1',
        'title': 'caddy-frontend-1',
        'type': 'rss',
        'url': 'https://[%s]:8411/share/private/' % (IP,),
        'version': 'RSS',
        'xmlUrl': 'https://[%s]:8411/public/feed' % (IP,),
      },
    ]
    connection_parameter_dict = self\
        .computer_partition.getConnectionParameterDict()
    self.assertTrue(
      self.monitor_setup_url_key in connection_parameter_dict,
      '%s not in %s' % (self.monitor_setup_url_key, connection_parameter_dict))
    monitor_setup_url_value = connection_parameter_dict[
      self.monitor_setup_url_key]
    monitor_url_match = re.match(r'.*url=(.*)', monitor_setup_url_value)
    self.assertNotEqual(
      None, monitor_url_match, '%s not parsable' % (monitor_setup_url_value,))
    self.assertEqual(1, len(monitor_url_match.groups()))
    monitor_url = monitor_url_match.groups()[0]
    monitor_url_split = monitor_url.split('&')
    self.assertEqual(
      3, len(monitor_url_split), '%s not splitabble' % (monitor_url,))
    self.monitor_url = monitor_url_split[0]
    monitor_username = monitor_url_split[1].split('=')
    self.assertEqual(
      2, len(monitor_username), '%s not splittable' % (monitor_username))
    monitor_password = monitor_url_split[2].split('=')
    self.assertEqual(
      2, len(monitor_password), '%s not splittable' % (monitor_password))
    self.monitor_username = monitor_username[1]
    self.monitor_password = monitor_password[1]

    opml_text = requests.get(self.monitor_url, verify=False).text
    opml = ET.fromstring(opml_text)

    body = opml[1]
    self.assertEqual('body', body.tag)

    outline_list = body[0].findall('outline')

    self.assertEqual(
      self.monitor_configuration_list,
      [q.attrib for q in outline_list]
    )

    expected_status_code_list = []
    got_status_code_list = []
    for monitor_configuration in self.monitor_configuration_list:
      status_code = requests.get(
          monitor_configuration['url'],
          verify=False,
          auth=(self.monitor_username, self.monitor_password)
        ).status_code
      expected_status_code_list.append(
        {
          'url': monitor_configuration['url'],
          'status_code': 200
        }
      )
      got_status_code_list.append(
        {
          'url': monitor_configuration['url'],
          'status_code': status_code
        }
      )
    self.assertEqual(
      expected_status_code_list,
      got_status_code_list
    )

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

  def test_trafficserver_logrotate(self):
    ats_partition = [
      q for q in glob.glob(os.path.join(self.instance_path, '*',))
      if os.path.exists(os.path.join(q, 'bin', 'trafficserver-rotate'))][0]
    ats_log_dir = os.path.join(ats_partition, 'var', 'log', 'trafficserver')
    ats_logrotate_dir = os.path.join(
      ats_partition, 'srv', 'backup', 'logrotate', 'trafficserver')
    ats_rotate = os.path.join(ats_partition, 'bin', 'trafficserver-rotate')

    old_file_name = 'log-old.old'
    older_file_name = 'log-older.old'
    with open(os.path.join(ats_log_dir, old_file_name), 'w') as fh:
      fh.write('old')
    with open(os.path.join(ats_log_dir, older_file_name), 'w') as fh:
      fh.write('older')

    # check rotation
    result, output = subprocess_status_output([ats_rotate])

    self.assertEqual(0, result)

    self.assertEqual(
      set(['log-old.old.xz', 'log-older.old.xz']),
      set(os.listdir(ats_logrotate_dir)))
    self.assertFalse(old_file_name + '.xz' in os.listdir(ats_log_dir))
    self.assertFalse(older_file_name + '.xz' in os.listdir(ats_log_dir))

    with lzma.open(
      os.path.join(ats_logrotate_dir, old_file_name + '.xz')) as fh:
      self.assertEqual(
        'old',
        fh.read()
      )
    with lzma.open(
      os.path.join(ats_logrotate_dir, older_file_name + '.xz')) as fh:
      self.assertEqual(
        'older',
        fh.read()
      )

    # check retention
    old_time = time.time() - (400 * 24 * 3600)
    os.utime(
      os.path.join(ats_logrotate_dir, older_file_name + '.xz'),
      (old_time, old_time))
    result, output = subprocess_status_output([ats_rotate])

    self.assertEqual(0, result)
    self.assertEqual(
      ['log-old.old.xz'],
      os.listdir(ats_logrotate_dir))

  def test_master_partition_state(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertRejectedSlavePromiseWithPop(parameter_dict)

    expected_parameter_dict = {
      'monitor-base-url': 'https://[%s]:8401' % self._ipv6_address,
      'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      'domain': 'example.com',
      'accepted-slave-amount': '56',
      'rejected-slave-amount': '0',
      'slave-amount': '56',
      'rejected-slave-dict': {
      },
      'warning-slave-dict': {
        '_Url': [
          "slave url ' %(backend)s ' has been converted to '%(backend)s'" % {
            'backend': self.backend_url}]}
    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

    partition_path = self.getMasterPartitionPath()

    # check that monitor cors domains are correctly setup by file presence, as
    # we trust monitor stack being tested in proper place and it is too hard
    # to have working monitor with local proxy
    self.assertTestData(
      open(
        os.path.join(
          partition_path, 'etc', 'httpd-cors.cfg'), 'r').read().strip())

  def test_slave_partition_state(self):
    partition_path = self.getSlavePartitionPath()
    self.assertTrue(
      '-grace 2s' in
      open(os.path.join(partition_path, 'bin', 'caddy-wrapper'), 'r').read()
    )

  def test_monitor_conf(self):
    monitor_conf_list = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'monitor.conf'
      ))
    self.assertEqual(3, len(monitor_conf_list))
    expected = [(False, q) for q in monitor_conf_list]
    got = [('!py!' in open(q).read(), q) for q in monitor_conf_list]
    # check that no monitor.conf in generated configuratio has magic !py!
    self.assertEqual(
      expected,
      got
    )

  def test_empty(self):
    parameter_dict = self.assertSlaveBase('empty')
    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.SERVICE_UNAVAILABLE, result.status_code)

    # check that log file contains verbose log
    log_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'var', 'log', 'httpd', '_empty_access_log'
      ))[0]

    log_regexp = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3} - - ' \
                 r'\[\d{2}\/.{3}\/\d{4}\:\d{2}\:\d{2}\:\d{2} \+\d{4}\] ' \
                 r'"GET \/test-path HTTP\/1.1" \d{3} \d+ "-" '\
                 r'"python-requests.*" \d+'

    self.assertRegexpMatches(
      open(log_file, 'r').readlines()[-1],
      log_regexp)
    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(
      httplib.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://empty.example.com:%s/test-path' % (HTTP_PORT,),
      result_http.headers['Location']
    )

    # check that 404 is as configured
    result_missing = fakeHTTPSResult(
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

  def test_server_polluted_keys_removed(self):
    buildout_file = os.path.join(
      self.getMasterPartitionPath(), 'buildout-switch-softwaretype.cfg')
    for line in [
      q for q in open(buildout_file).readlines()
      if q.startswith('config-slave-list') or q.startswith(
          'config-extra_slave_instance_list')]:
      self.assertFalse('slave_title' in line)
      self.assertFalse('slap_software_type' in line)
      self.assertFalse('connection-parameter-hash' in line)
      self.assertFalse('timestamp' in line)

  def assertBackendHeaders(
    self, backend_header_dict, domain, source_ip=SOURCE_IP, port=HTTPS_PORT,
    proto='https', ignore_header_list=None):
    if ignore_header_list is None:
      ignore_header_list = []
    self.assertFalse('remote_user' in backend_header_dict.keys())
    if 'Host' not in ignore_header_list:
      self.assertEqual(
        backend_header_dict['host'],
        '%s:%s' % (domain, port))
    self.assertEqual(
      backend_header_dict['x-forwarded-for'],
      source_ip
    )
    self.assertEqual(
      backend_header_dict['x-forwarded-port'],
      port
    )
    self.assertEqual(
      backend_header_dict['x-forwarded-proto'],
      proto
    )

  def test_url(self):
    parameter_dict = self.assertSlaveBase('Url')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={
        'Timeout': '10',  # more than default backend-connect-timeout == 5
        'Accept-Encoding': 'gzip',
      }
    )

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))

    self.assertEqual(j['Incoming Headers']['timeout'], '10')
    self.assertFalse('Content-Encoding' in result.headers)
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result.headers['Set-Cookie']
    )

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      httplib.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://url.example.com:%s/test-path/deeper' % (HTTP_PORT,),
      result_http.headers['Location']
    )

    # check that timeouts are correctly set in the haproxy configuration
    backend_configuration_file = glob.glob(os.path.join(
      self.instance_path, '*', 'etc', 'backend-haproxy.cfg'))[0]
    with open(backend_configuration_file) as fh:
      content = fh.read()
      self.assertTrue("""backend _Url-http
  timeout server 12s
  timeout connect 5s
  retries 3""" in content)
      self.assertTrue("""  timeout queue 60s
  timeout server 12s
  timeout client 12s
  timeout connect 5s
  retries 3""" in content)

  def test_auth_to_backend(self):
    parameter_dict = self.assertSlaveBase('auth-to-backend')
    # 1. fetch certificate from backend-client-caucase-url
    master_parameter_dict = self.parseConnectionParameterDict()
    caucase_url = master_parameter_dict['backend-client-caucase-url']
    ca_certificate = requests.get(caucase_url + '/cas/crt/ca.crt.pem')
    assert ca_certificate.status_code == httplib.OK
    ca_certificate_file = os.path.join(
      self.working_directory, 'ca-backend-client.crt.pem')
    with open(ca_certificate_file, 'w') as fh:
      fh.write(ca_certificate.text)

    # 2. start backend with this certificate
    class OwnTestHandler(TestHandler):
      identification = 'Auth Backend'

    server_https_auth = HTTPServer(
      (self._ipv4_address, self._server_https_auth_port),
      OwnTestHandler)

    server_https_auth.socket = ssl.wrap_socket(
      server_https_auth.socket,
      certfile=self.test_server_certificate_file.name,
      cert_reqs=ssl.CERT_REQUIRED,
      ca_certs=ca_certificate_file,
      server_side=True)

    backend_https_auth_url = 'https://%s:%s/' \
        % server_https_auth.server_address

    server_https_auth_process = multiprocessing.Process(
      target=server_https_auth.serve_forever, name='HTTPSServerAuth')
    server_https_auth_process.start()
    self.logger.debug('Started process %s' % (server_https_auth_process,))
    try:
      # 3. assert that you can't fetch nothing without key
      try:
        requests.get(backend_https_auth_url, verify=False)
      except Exception:
        pass
      else:
        self.fail(
          'Access to %r shall be not possible without certificate' % (
            backend_https_auth_url,))
      # 4. check that you can access this backend via frontend
      #    (so it means that auth to backend worked)
      result = fakeHTTPSResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'],
        'test-path/deep/.././deeper',
        headers={
          'Timeout': '10',  # more than default backend-connect-timeout == 5
          'Accept-Encoding': 'gzip',
        }
      )

      self.assertEqual(
        self.certificate_pem,
        der2pem(result.peercert))

      self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

      try:
        j = result.json()
      except Exception:
        raise ValueError('JSON decode problem in:\n%s' % (result.text,))

      self.assertEqual(j['Incoming Headers']['timeout'], '10')
      self.assertFalse('Content-Encoding' in result.headers)
      self.assertBackendHeaders(
         j['Incoming Headers'], parameter_dict['domain'])

      self.assertEqual(
        'secured=value;secure, nonsecured=value',
        result.headers['Set-Cookie']
      )
      # proof that proper backend was accessed
      self.assertEqual(
        'Auth Backend',
        result.headers['X-Backend-Identification']
      )
    finally:
      self.logger.debug('Stopping process %s' % (server_https_auth_process,))
      server_https_auth_process.join(10)
      server_https_auth_process.terminate()
      time.sleep(0.1)
      if server_https_auth_process.is_alive():
        self.logger.warning(
          'Process %s still alive' % (server_https_auth_process, ))

  def test_auth_to_backend_not_configured(self):
    parameter_dict = self.assertSlaveBase('auth-to-backend-not-configured')
    # 1. fetch certificate from backend-client-caucase-url
    master_parameter_dict = self.parseConnectionParameterDict()
    caucase_url = master_parameter_dict['backend-client-caucase-url']
    ca_certificate = requests.get(caucase_url + '/cas/crt/ca.crt.pem')
    assert ca_certificate.status_code == httplib.OK
    ca_certificate_file = os.path.join(
      self.working_directory, 'ca-backend-client.crt.pem')
    with open(ca_certificate_file, 'w') as fh:
      fh.write(ca_certificate.text)

    # 2. start backend with this certificate
    class OwnTestHandler(TestHandler):
      identification = 'Auth Backend'

    server_https_auth = HTTPServer(
      (self._ipv4_address, self._server_https_auth_port),
      OwnTestHandler)

    server_https_auth.socket = ssl.wrap_socket(
      server_https_auth.socket,
      certfile=self.test_server_certificate_file.name,
      cert_reqs=ssl.CERT_REQUIRED,
      ca_certs=ca_certificate_file,
      server_side=True)

    backend_https_auth_url = 'https://%s:%s/' \
        % server_https_auth.server_address

    server_https_auth_process = multiprocessing.Process(
      target=server_https_auth.serve_forever, name='HTTPSServerAuth')
    server_https_auth_process.start()
    self.logger.debug('Started process %s' % (server_https_auth_process,))
    try:
      # 3. assert that you can't fetch nothing without key
      try:
        requests.get(backend_https_auth_url, verify=False)
      except Exception:
        pass
      else:
        self.fail(
          'Access to %r shall be not possible without certificate' % (
            backend_https_auth_url,))
      # 4. check that you can access this backend via frontend
      #    (so it means that auth to backend worked)
      result = fakeHTTPSResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'],
        'test-path/deep/.././deeper',
        headers={
          'Timeout': '10',  # more than default backend-connect-timeout == 5
          'Accept-Encoding': 'gzip',
        }
      )

      self.assertEqual(
        self.certificate_pem,
        der2pem(result.peercert))

      self.assertEqual(
        result.status_code,
        httplib.BAD_GATEWAY
      )
    finally:
      self.logger.debug('Stopping process %s' % (server_https_auth_process,))
      server_https_auth_process.join(10)
      server_https_auth_process.terminate()
      time.sleep(0.1)
      if server_https_auth_process.is_alive():
        self.logger.warning(
          'Process %s still alive' % (server_https_auth_process, ))

  def test_auth_to_backend_backend_ignore(self):
    parameter_dict = self.assertSlaveBase('auth-to-backend-backend-ignore')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={
        'Timeout': '10',  # more than default backend-connect-timeout == 5
        'Accept-Encoding': 'gzip',
      }
    )

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))

    self.assertEqual(j['Incoming Headers']['timeout'], '10')
    self.assertFalse('Content-Encoding' in result.headers)
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result.headers['Set-Cookie']
    )

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      httplib.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://authtobackendbackendignore.example.com:%s/test-path/deeper' % (
        HTTP_PORT,),
      result_http.headers['Location']
    )

  def test_compressed_result(self):
    parameter_dict = self.assertSlaveBase('Url')
    result_compressed = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={
        'Accept-Encoding': 'gzip',
        'Compress': '1',
      }
    )
    self.assertEqual(
      'gzip',
      result_compressed.headers['Content-Encoding']
    )

    # Assert that no tampering was done with the request
    # (compression/decompression)
    # Backend compresses with 0 level, so decompression/compression
    # would change somthing
    self.assertEqual(
      result_compressed.headers['Content-Length'],
      result_compressed.headers['Backend-Content-Length']
    )

    result_not_compressed = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={
        'Accept-Encoding': 'gzip',
      }
    )
    self.assertFalse('Content-Encoding' in result_not_compressed.headers)

  def test_no_content_type_alter(self):
    parameter_dict = self.assertSlaveBase('Url')
    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={
        'Accept-Encoding': 'gzip',
        'X-Reply-Body': base64.b64encode(
          b"""<?xml version="1.0" encoding="UTF-8"?>
<note>
  <to>Tove</to>
  <from>Jani</from>
  <heading>Reminder</heading>
  <body>Don't forget me this weekend!</body>
</note>"""),
        'X-Drop-Header': 'Content-Type'
      }
    )

    self.assertEqual(
      'text/xml; charset=utf-8',
      result.headers['Content-Type']
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
        'public-ipv4': self._ipv4_address,
      },
      parameter_dict
    )

    result_ipv6 = fakeHTTPSResult(
      parameter_dict['domain'], self._ipv6_address, 'test-path',
      source_ip=self._ipv6_address)

    self.assertEqual(
       self._ipv6_address,
       result_ipv6.json()['Incoming Headers']['x-forwarded-for']
    )

    self.assertEqual(
      self.certificate_pem,
      der2pem(result_ipv6.peercert))

    self.assertEqualResultJson(result_ipv6, 'Path', '/test-path')

  def test_type_zope_path(self):
    parameter_dict = self.assertSlaveBase('type-zope-path')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/'
      'https//typezopepath.example.com:443/path/to/some/resource'
      '/VirtualHostRoot/'
      'test-path/deeper'
    )

  def test_type_zope_default_path(self):
    parameter_dict = self.assertSlaveBase('type-zope-default-path')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], '')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.MOVED_PERMANENTLY,
      result.status_code
    )

    self.assertEqual(
      'https://typezopedefaultpath.example.com:%s/'
      'default-path/to/some/resource' % (
        HTTPS_PORT,),
      result.headers['Location']
    )

  def test_server_alias(self):
    parameter_dict = self.assertSlaveBase('server-alias')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPSResult(
      'alias1.example.com', parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPSResult(
      'alias2.example.com', parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

  def test_server_alias_empty(self):
    parameter_dict = self.assertSlaveBase('server-alias-empty')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={
        'Timeout': '10',  # more than default backend-connect-timeout == 5
        'Accept-Encoding': 'gzip',
      }
    )

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))

    self.assertEqual(j['Incoming Headers']['timeout'], '10')
    self.assertFalse('Content-Encoding' in result.headers)
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result.headers['Set-Cookie']
    )

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = fakeHTTPSResult(
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = fakeHTTPSResult(
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
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
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.customdomain_ca_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    certificate_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'srv', 'autocert',
      '_custom_domain_ssl_crt_ssl_key_ssl_ca_crt.pem'))
    self.assertEqual(1, len(certificate_file_list))
    certificate_file = certificate_file_list[0]
    with open(certificate_file) as out:
      self.assertEqual(data, out.read())

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    # as now the place to put the key is known put the key there
    auth = requests.get(
      generate_auth,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, auth.status_code)

    _, ca_key_pem, csr, _ = createCSR(
      parameter_dict['domain'])
    _, ca_certificate_pem = self.ca.signCSR(csr)

    data = ca_certificate_pem + ca_key_pem + 'some garbage'
    upload = requests.put(
      upload_url + auth.text,
      data=data,
      verify=self.ca_certificate_file)

    self.assertEqual(httplib.CREATED, upload.status_code)
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      ca_certificate_pem,
      der2pem(result.peercert)
    )

    self.assertEqualResultJson(result, 'Path', '/test-path')

    certificate_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'srv', 'autocert',
      '_ssl_ca_crt_garbage.pem'))
    self.assertEqual(1, len(certificate_file_list))
    certificate_file = certificate_file_list[0]
    with open(certificate_file) as out:
      self.assertEqual(data, out.read())

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
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
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    certificate_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'srv', 'autocert',
      '_ssl_ca_crt_does_not_match.pem'))
    self.assertEqual(1, len(certificate_file_list))
    certificate_file = certificate_file_list[0]
    with open(certificate_file) as out:
      self.assertEqual(data, out.read())

  def test_https_only(self):
    parameter_dict = self.assertSlaveBase('https-only')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqualResultJson(result_http, 'Path', '/test-path/deeper')

  def test_custom_domain(self):
    reference = 'custom_domain'
    hostname = 'mycustomdomain'
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, '')
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_custom_domain_server_alias(self):
    reference = 'custom_domain_server_alias'
    hostname = 'mycustomdomainserveralias'
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, '')
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = fakeHTTPSResult(
      'mycustomdomainserveralias1.example.com', parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
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
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.customdomain_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_type_zope(self):
    parameter_dict = self.assertSlaveBase('type-zope')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//typezope.example.com:443/'
      '/VirtualHostRoot/test-path/deeper'
    )

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      httplib.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://typezope.example.com:%s/test-path/deep/.././deeper' % (
        HTTP_PORT,),
      result.headers['Location']
    )

  def test_type_zope_prefer_gzip_encoding_to_backend_https_only(self):
    parameter_dict = self.assertSlaveBase(
      'type-zope-prefer-gzip-encoding-to-backend-https-only')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//'
      'typezopeprefergzipencodingtobackendhttpsonly.example.com:443/'
      '/VirtualHostRoot/test-path/deeper'
    )

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/http//'
      'typezopeprefergzipencodingtobackendhttpsonly.example.com:80/'
      '/VirtualHostRoot/test-path/deeper'
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//'
      'typezopeprefergzipencodingtobackendhttpsonly.example.com:443/'
      '/VirtualHostRoot/test-path/deeper'
    )
    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/http//'
      'typezopeprefergzipencodingtobackendhttpsonly.example.com:80/'
      '/VirtualHostRoot/test-path/deeper'
    )
    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

  def test_type_zope_prefer_gzip_encoding_to_backend(self):
    parameter_dict = self.assertSlaveBase(
      'type-zope-prefer-gzip-encoding-to-backend')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//'
      'typezopeprefergzipencodingtobackend.example.com:443/'
      '/VirtualHostRoot/test-path/deeper'
    )

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      httplib.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://%s:%s/test-path/deep/.././deeper' % (
        parameter_dict['domain'], HTTP_PORT),
      result.headers['Location']
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//'
      'typezopeprefergzipencodingtobackend.example.com:443/'
      '/VirtualHostRoot/test-path/deeper'
    )
    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      httplib.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://%s:%s/test-path/deep/.././deeper' % (
        parameter_dict['domain'], HTTP_PORT),
      result.headers['Location']
    )

  def test_type_zope_virtualhostroot_http_port(self):
    parameter_dict = self.assertSlaveBase(
      'type-zope-virtualhostroot-http-port')

    result = fakeHTTPResult(
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

    result = fakeHTTPSResult(
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
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path',
      HTTPS_PORT)

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test/terminals/websocket/test',
      HTTPS_PORT)

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/terminals/websocket')
    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_type_websocket(self):
    parameter_dict = self.assertSlaveBase(
      'type-websocket')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      headers={'Connection': 'Upgrade'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(
      result,
      'Path',
      '/test-path'
    )
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'Upgrade',
      j['Incoming Headers']['connection']
    )
    self.assertTrue('x-real-ip' in j['Incoming Headers'])
    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_type_websocket_websocket_transparent_false(self):
    parameter_dict = self.assertSlaveBase(
      'type-websocket-websocket-transparent-false')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      headers={'Connection': 'Upgrade'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(
      result,
      'Path',
      '/test-path'
    )
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    parsed = urlparse.urlparse(self.backend_url)
    self.assertBackendHeaders(
      j['Incoming Headers'], parsed.hostname, port='17', proto='irc',
      ignore_header_list=['Host'])
    self.assertEqual(
      'Upgrade',
      j['Incoming Headers']['connection']
    )
    self.assertFalse('x-real-ip' in j['Incoming Headers'])
    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_type_websocket_websocket_path_list(self):
    parameter_dict = self.assertSlaveBase(
      'type-websocket-websocket-path-list')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      headers={'Connection': 'Upgrade'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(
      result,
      'Path',
      '/test-path'
    )
    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])
    self.assertTrue('x-real-ip' in j['Incoming Headers'])

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'ws/test-path',
      headers={'Connection': 'Upgrade'})

    self.assertEqualResultJson(
      result,
      'Path',
      '/ws/test-path'
    )
    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'Upgrade',
      j['Incoming Headers']['connection']
    )
    self.assertTrue('x-real-ip' in j['Incoming Headers'])

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'with%20space/test-path', headers={'Connection': 'Upgrade'})

    self.assertEqualResultJson(
      result,
      'Path',
      '/with%20space/test-path'
    )
    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'Upgrade',
      j['Incoming Headers']['connection']
    )
    self.assertTrue('x-real-ip' in j['Incoming Headers'])

  def test_type_websocket_websocket_path_list_websocket_transparent_false(
    self):
    parameter_dict = self.assertSlaveBase(
      'type-websocket-websocket-path-list-websocket-transparent-false')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      headers={'Connection': 'Upgrade'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(
      result,
      'Path',
      '/test-path'
    )
    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    parsed = urlparse.urlparse(self.backend_url)
    self.assertBackendHeaders(
      j['Incoming Headers'], parsed.hostname, port='17', proto='irc',
      ignore_header_list=['Host'])
    self.assertFalse('x-real-ip' in j['Incoming Headers'])

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'ws/test-path',
      headers={'Connection': 'Upgrade'})

    self.assertEqualResultJson(
      result,
      'Path',
      '/ws/test-path'
    )
    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(
      j['Incoming Headers'], parsed.hostname, port='17', proto='irc',
      ignore_header_list=['Host'])
    self.assertEqual(
      'Upgrade',
      j['Incoming Headers']['connection']
    )
    self.assertFalse('x-real-ip' in j['Incoming Headers'])

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'with%20space/test-path', headers={'Connection': 'Upgrade'})

    self.assertEqualResultJson(
      result,
      'Path',
      '/with%20space/test-path'
    )
    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(
      j['Incoming Headers'], parsed.hostname, port='17', proto='irc',
      ignore_header_list=['Host'])
    self.assertEqual(
      'Upgrade',
      j['Incoming Headers']['connection']
    )
    self.assertFalse('x-real-ip' in j['Incoming Headers'])

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'pub',
      #  NGINX_HTTPS_PORT
    )

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

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.FOUND,
      result.status_code
    )

    self.assertEqual(
      '%stest-path/deeper' % (self.backend_url,),
      result.headers['Location']
    )

  def test_type_redirect_custom_domain(self):
    reference = 'type-redirect-custom_domain'
    hostname = 'customdomaintyperedirect'
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, '')
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.FOUND,
      result.status_code
    )

    self.assertEqual(
      '%stest-path/deeper' % (self.backend_url,),
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.SERVICE_UNAVAILABLE,
      result.status_code
    )

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      httplib.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://sslproxyverifysslproxycacrtunverified.example.com:%s/'
      'test-path' % (HTTP_PORT,),
      result_http.headers['Location']
    )

  def test_ssl_proxy_verify_ssl_proxy_ca_crt(self):
    parameter_dict = self.assertSlaveBase('ssl-proxy-verify_ssl_proxy_ca_crt')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertFalse('Content-Encoding' in result.headers)

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result.headers['Set-Cookie']
    )

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      httplib.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://sslproxyverifysslproxycacrt.example.com:%s/test-path' % (
        HTTP_PORT,),
      result_http.headers['Location']
    )

  def test_ssl_proxy_verify_unverified(self):
    parameter_dict = self.assertSlaveBase('ssl-proxy-verify-unverified')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.SERVICE_UNAVAILABLE,
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.SERVICE_UNAVAILABLE,
      result.status_code
    )

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deeper')

    self.assertEqual(
      httplib.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://enablecachesslproxyverifysslproxycacrtunverified.example.com'
      ':%s/test-path/deeper' % (HTTP_PORT,),
      result_http.headers['Location']
    )

  def test_enable_cache_ssl_proxy_verify_ssl_proxy_ca_crt(self):
    parameter_dict = self.assertSlaveBase(
      'enable_cache-ssl-proxy-verify_ssl_proxy_ca_crt')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

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
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
      },
      headers
    )

  def test_enable_cache_ssl_proxy_verify_unverified(self):
    parameter_dict = self.assertSlaveBase(
      'enable_cache-ssl-proxy-verify-unverified')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.SERVICE_UNAVAILABLE,
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.SERVICE_UNAVAILABLE,
      result.status_code
    )

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      httplib.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://typezopesslproxyverifysslproxycacrtunverified.example.com:%s/'
      'test-path' % (HTTP_PORT,),
      result_http.headers['Location']
    )

  def test_type_zope_ssl_proxy_verify_ssl_proxy_ca_crt(self):
    parameter_dict = self.assertSlaveBase(
      'type-zope-ssl-proxy-verify_ssl_proxy_ca_crt')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertBackendHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https//'
      'typezopesslproxyverifysslproxycacrt.example.com:443/'
      '/VirtualHostRoot/test-path'
    )

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      httplib.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://typezopesslproxyverifysslproxycacrt.example.com:'
      '%s/test-path' % (HTTP_PORT,),
      result.headers['Location']
    )

  def test_type_zope_ssl_proxy_verify_unverified(self):
    parameter_dict = self.assertSlaveBase(
      'type-zope-ssl-proxy-verify-unverified')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.SERVICE_UNAVAILABLE,
      result.status_code
    )

  def test_monitor_ipv6_test(self):
    parameter_dict = self.assertSlaveBase('monitor-ipv6-test')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.SERVICE_UNAVAILABLE, result.status_code)

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(
      httplib.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://monitoripv6test.example.com:%s/test-path' % (HTTP_PORT,),
      result_http.headers['Location']
    )

    monitor_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'plugin',
        'check-_monitor-ipv6-test-ipv6-packet-list-test.py'))[0]
    # get promise module and check that parameters are ok
    self.assertEqual(
      getPluginParameterDict(self.software_path, monitor_file),
      {
        'frequency': '720',
        'address': 'monitor-ipv6-test'
      }
    )

  def test_monitor_ipv4_test(self):
    parameter_dict = self.assertSlaveBase('monitor-ipv4-test')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.SERVICE_UNAVAILABLE, result.status_code)

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(
      httplib.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://monitoripv4test.example.com:%s/test-path' % (HTTP_PORT,),
      result_http.headers['Location']
    )

    monitor_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'plugin',
        'check-_monitor-ipv4-test-ipv4-packet-list-test.py'))[0]
    # get promise module and check that parameters are ok
    self.assertEqual(
      getPluginParameterDict(self.software_path, monitor_file),
      {
        'frequency': '720',
        'ipv4': 'true',
        'address': 'monitor-ipv4-test',
      }
    )

  def test_ciphers(self):
    parameter_dict = self.assertSlaveBase('ciphers')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.SERVICE_UNAVAILABLE, result.status_code)

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      httplib.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://ciphers.example.com:%s/test-path' % (HTTP_PORT,),
      result_http.headers['Location']
    )

    configuration_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'caddy-slave-conf.d', '_ciphers.conf'
      ))[0]
    self.assertTrue(
      'ciphers RSA-3DES-EDE-CBC-SHA RSA-AES128-CBC-SHA'
      in open(configuration_file).read()
    )

  def test_enable_cache_custom_domain(self):
    reference = 'enable_cache_custom_domain'
    hostname = 'customdomainenablecache'
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, '')
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

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
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
        'Cache-Control': 'max-age=1, stale-while-revalidate=3600, '
                         'stale-if-error=3600'
      },
      headers
    )

    backend_headers = result.json()['Incoming Headers']
    self.assertBackendHeaders(backend_headers, parameter_dict['domain'])
    via = backend_headers.pop('via', None)
    self.assertNotEqual(via, None)
    self.assertRegexpMatches(
      via,
      r'^http\/1.1 caddy-frontend-1\[.*\] \(ApacheTrafficServer\/7.1.11\)$'
    )

  def test_enable_cache_server_alias(self):
    parameter_dict = self.assertSlaveBase('enable_cache_server_alias')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

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
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
        'Cache-Control': 'max-age=1, stale-while-revalidate=3600, '
                         'stale-if-error=3600'
      },
      headers
    )

    backend_headers = result.json()['Incoming Headers']
    self.assertBackendHeaders(backend_headers, parameter_dict['domain'])
    via = backend_headers.pop('via', None)
    self.assertNotEqual(via, None)
    self.assertRegexpMatches(
      via,
      r'^http\/1.1 caddy-frontend-1\[.*\] \(ApacheTrafficServer\/7.1.11\)$'
    )

    result = fakeHTTPResult(
      'enablecacheserveralias1.example.com', parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600'})
    self.assertEqual(
      httplib.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://enablecacheserveralias1.example.com:%s/test-path/deeper' % (
        HTTP_PORT,),
      result.headers['Location']
    )

  def test_enable_cache(self):
    parameter_dict = self.assertSlaveBase('enable_cache')

    source_ip = '127.0.0.1'
    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600',
      },
      source_ip=source_ip
    )

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

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
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
        'Cache-Control': 'max-age=1, stale-while-revalidate=3600, '
                         'stale-if-error=3600'
      },
      headers
    )

    backend_headers = result.json()['Incoming Headers']
    self.assertBackendHeaders(backend_headers, parameter_dict['domain'])
    via = backend_headers.pop('via', None)
    self.assertNotEqual(via, None)
    self.assertRegexpMatches(
      via,
      r'^http\/1.1 caddy-frontend-1\[.*\] \(ApacheTrafficServer\/7.1.11\)$'
    )

    # check stale-if-error support (assumes stale-while-revalidate is same)
    # wait a bit for max-age to expire
    time.sleep(2)
    # real check: cache access provides old data, access cache directly, as
    # caddy has to be stopped
    try:
      # stop the backend, to have error on while connecting to it
      self.stopServerProcess()

      result = fakeHTTPSResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'],
        'test-path/deep/.././deeper', headers={
          'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
          'revalidate=3600, stale-if-error=3600',
        },
        source_ip=source_ip
      )
      self.assertEqual(result.status_code, httplib.OK)
      self.assertEqualResultJson(result, 'Path', '/test-path/deeper')
      headers = result.headers.copy()
      self.assertKeyWithPop('Server', headers)
      self.assertKeyWithPop('Date', headers)
      self.assertKeyWithPop('Age', headers)
      self.assertKeyWithPop('Expires', headers)
      # drop keys appearing randomly in headers
      headers.pop('Transfer-Encoding', None)
      headers.pop('Content-Length', None)
      headers.pop('Connection', None)
      headers.pop('Keep-Alive', None)

      self.assertEqual(
        {
          'Content-type': 'application/json',
          # ATS does not cache the cookied text content, see:
          # https://docs.trafficserver.apache.org/en/7.1.x/admin-guide/\
          # configuration/cache-basics.en.html#caching-cookied-objects
          # 'Set-Cookie': 'secured=value;secure, nonsecured=value',
          'Cache-Control': 'max-age=1, stale-while-revalidate=3600, '
                           'stale-if-error=3600',
        },
        headers
      )

      backend_headers = result.json()['Incoming Headers']
      self.assertBackendHeaders(backend_headers, parameter_dict['domain'])
      via = backend_headers.pop('via', None)
      self.assertNotEqual(via, None)
      self.assertRegexpMatches(
        via,
        r'^http\/1.1 caddy-frontend-1\[.*\] \(ApacheTrafficServer\/7.1.11\)$'
      )
    finally:
      self.startServerProcess()
    # END: check stale-if-error support

  def test_enable_cache_ats_timeout(self):
    parameter_dict = self.assertSlaveBase('enable_cache')
    # check that timeout seen by ATS does not result in many queries done
    # to the backend and that next request works like a charm
    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test_enable_cache_ats_timeout', headers={
        'Timeout': '15',
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600'})

    # ATS timed out
    self.assertEqual(
      httplib.GATEWAY_TIMEOUT,
      result.status_code
    )

    backend_haproxy_log_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'var', 'log', 'backend-haproxy.log'
      ))[0]

    matching_line_amount = 0
    pattern = re.compile(
      r'.* _enable_cache-http.backend .* 504 .*'
      '"GET .test_enable_cache_ats_timeout HTTP.1.1"$')
    with open(backend_haproxy_log_file) as fh:
      for line in fh.readlines():
        if pattern.match(line):
          matching_line_amount += 1

    # Haproxy backend received maximum one connection
    self.assertIn(matching_line_amount, [0, 1])

    timeout = 5
    b = time.time()
    # ATS created squid.log with a delay
    while True:
      if (time.time() - b) > timeout:
        self.fail('Squid log file did not appear in %ss' % (timeout,))
      ats_log_file_list = glob.glob(
        os.path.join(
          self.instance_path, '*', 'var', 'log', 'trafficserver', 'squid.log'
        ))
      if len(ats_log_file_list) == 1:
        ats_log_file = ats_log_file_list[0]
        break
      time.sleep(0.1)

    pattern = re.compile(
      r'.*ERR_READ_TIMEOUT/504 .*test_enable_cache_ats_timeout'
      '.*TIMEOUT_DIRECT*')
    timeout = 5
    b = time.time()
    # ATS needs some time to flush logs
    while True:
      matching_line_amount = 0
      if (time.time() - b) > timeout:
        break
      with open(ats_log_file) as fh:
        for line in fh.readlines():
          if pattern.match(line):
            matching_line_amount += 1
      if matching_line_amount > 0:
        break
      time.sleep(0.1)

    # ATS has maximum one entry for this query
    self.assertIn(matching_line_amount, [0, 1])

    # the result is available immediately after
    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

  def test_enable_cache_disable_no_cache_request(self):
    parameter_dict = self.assertSlaveBase(
      'enable_cache-disable-no-cache-request')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      headers={'Pragma': 'no-cache', 'Cache-Control': 'something'})

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
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value'
      },
      headers
    )

    backend_headers = result.json()['Incoming Headers']
    self.assertBackendHeaders(backend_headers, parameter_dict['domain'])
    via = backend_headers.pop('via', None)
    self.assertNotEqual(via, None)
    self.assertRegexpMatches(
      via,
      r'^http\/1.1 caddy-frontend-1\[.*\] \(ApacheTrafficServer\/7.1.11\)$'
    )

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertFalse('pragma' in j['Incoming Headers'].keys())

  def test_enable_cache_disable_via_header(self):
    parameter_dict = self.assertSlaveBase('enable_cache-disable-via-header')

    result = fakeHTTPSResult(
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
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
      },
      headers
    )

    backend_headers = result.json()['Incoming Headers']
    self.assertBackendHeaders(backend_headers, parameter_dict['domain'])
    via = backend_headers.pop('via', None)
    self.assertNotEqual(via, None)
    self.assertRegexpMatches(
      via,
      r'^http\/1.1 caddy-frontend-1\[.*\] \(ApacheTrafficServer\/7.1.11\)$'
    )

  def test_enable_http2_false(self):
    parameter_dict = self.assertSlaveBase('enable-http2-false')

    result = fakeHTTPSResult(
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
        'Content-Type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
      },
      headers
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_enable_http2_default(self):
    parameter_dict = self.assertSlaveBase('enable-http2-default')

    result = fakeHTTPSResult(
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
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
      },
      headers
    )

    self.assertTrue(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

  def test_prefer_gzip_encoding_to_backend_https_only(self):
    parameter_dict = self.assertSlaveBase(
      'prefer-gzip-encoding-to-backend-https-only')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    self.assertBackendHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'deflate'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    self.assertBackendHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'deflate', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    self.assertBackendHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'],
      port=HTTP_PORT, proto='http')
    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'deflate'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    self.assertBackendHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'],
      port=HTTP_PORT, proto='http')
    self.assertEqual(
      'deflate', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

  def test_prefer_gzip_encoding_to_backend(self):
    parameter_dict = self.assertSlaveBase(
      'prefer-gzip-encoding-to-backend')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    self.assertBackendHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'deflate'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    self.assertBackendHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'deflate', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      httplib.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://%s:%s/test-path/deeper' % (parameter_dict['domain'], HTTP_PORT),
      result.headers['Location']
    )

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'deflate'})

    self.assertEqual(
      httplib.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://%s:%s/test-path/deeper' % (parameter_dict['domain'], HTTP_PORT),
      result.headers['Location']
    )

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      httplib.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://%s:%s/test-path/deeper' % (parameter_dict['domain'], HTTP_PORT),
      result.headers['Location']
    )

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      httplib.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://%s:%s/test-path/deeper' % (parameter_dict['domain'], HTTP_PORT),
      result.headers['Location']
    )

  def test_disabled_cookie_list(self):
    parameter_dict = self.assertSlaveBase('disabled-cookie-list')

    result = fakeHTTPSResult(
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

    self.assertBackendHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'Coffee=present', result.json()['Incoming Headers']['cookie'])

  def test_https_url(self):
    parameter_dict = self.assertSlaveBase('url_https-url')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/https/test-path/deeper')

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      httplib.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://urlhttpsurl.example.com:%s/test-path/deeper' % (HTTP_PORT,),
      result_http.headers['Location']
    )

    # check that timeouts are correctly set in the haproxy configuration
    backend_configuration_file = glob.glob(os.path.join(
      self.instance_path, '*', 'etc', 'backend-haproxy.cfg'))[0]
    with open(backend_configuration_file) as fh:
      content = fh.read()
      self.assertTrue("""backend _url_https-url-http
  timeout server 15s
  timeout connect 10s
  retries 5""" in content)


@skip('Impossible to instantiate cluster with stopped partition')
class TestReplicateSlave(SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'public-ipv4': cls._ipv4_address,
      '-frontend-quantity': 2,
      '-sla-2-computer_guid': cls.slap._computer_id,
      '-frontend-2-state': 'stopped',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'replicate': {
        'url': cls.backend_url,
        'enable_cache': True,
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result_http = fakeHTTPResult(
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


@skip('Impossible to instantiate cluster with destroyed partition')
class TestReplicateSlaveOtherDestroyed(SlaveHttpFrontendTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'public-ipv4': cls._ipv4_address,
      '-frontend-quantity': 2,
      '-sla-2-computer_guid': cls.slap._computer_id,
      '-frontend-2-state': 'destroyed',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'empty': {
        'url': cls.backend_url,
        'enable_cache': True,
      }
    }

  def test_extra_slave_instance_list_not_present_destroyed_request(self):
    buildout_file = os.path.join(
      self.getMasterPartitionPath(), 'buildout-switch-softwaretype.cfg')
    with open(buildout_file) as fh:
      buildout_file_content = fh.read()
      node_1_present = re.search(
        "^config-frontend-name = !py!'caddy-frontend-1'$",
        buildout_file_content, flags=re.M) is not None
      node_2_present = re.search(
        "^config-frontend-name = !py!'caddy-frontend-2'$",
        buildout_file_content, flags=re.M) is not None
    self.assertTrue(node_1_present)
    self.assertFalse(node_2_present)


class TestEnableHttp2ByDefaultFalseSlave(SlaveHttpFrontendTestCase,
                                         TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'public-ipv4': cls._ipv4_address,
      'enable-http2-by-default': 'false',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
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
      'dummy-cached': {
        'url': cls.backend_url,
        'enable_cache': True,
      }
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
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
      'public-ipv4': cls._ipv4_address,
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
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
      'dummy-cached': {
        'url': cls.backend_url,
        'enable_cache': True,
      }
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
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
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
        'replication_number': '1',
        'url': 'http://enablehttp2true.example.com',
        'site_url': 'http://enablehttp2true.example.com',
        'secure_access':
        'https://enablehttp2true.example.com',
        'public-ipv4': self._ipv4_address,
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
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'default': {
        'url': cls.backend_url,
        'enable_cache': True
      },
    }

  @classmethod
  def waitForSlave(cls):
    # no need to wait for slave availability here
    return True

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
        'public-ipv4': 'None',
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    re6st_connectivity_promise_list = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'plugin',
        're6st-connectivity.py'))

    self.assertEqual(1, len(re6st_connectivity_promise_list))
    re6st_connectivity_promise_file = re6st_connectivity_promise_list[0]

    self.assertEqual(
      getPluginParameterDict(
        self.software_path, re6st_connectivity_promise_file),
      {
        'url': 'http://[2001:67c:1254:4::1]/index.html',
      }
    )


@skip('New test system cannot be used with failing promises')
class TestRe6stVerificationUrlSlave(SlaveHttpFrontendTestCase,
                                    TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      're6st-verification-url': 'some-re6st-verification-url',
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'default': {
        'url': cls.backend_url,
        'enable_cache': True,
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
        'public-ipv4': 'None',
      },
      parameter_dict
    )

    re6st_connectivity_promise_list = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'plugin',
        're6st-connectivity.py'))

    self.assertEqual(1, len(re6st_connectivity_promise_list))
    re6st_connectivity_promise_file = re6st_connectivity_promise_list[0]

    self.assertEqual(
      getPluginParameterDict(
        self.software_path, re6st_connectivity_promise_file),
      {
        'url': 'some-re6st-verification-url',
      }
    )


@skip('Impossible to instantiate cluster with stopped partition')
class TestDefaultMonitorHttpdPort(SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      '-frontend-1-state': 'stopped',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
    }

  @classmethod
  def runKedifaUpdater(cls):
    return

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'test': {
        'url': cls.backend_url,
      },
      'testcached': {
        'url': cls.backend_url,
        'enable_cache': True,
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
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
        'secure_access': 'https://test.None', 'public-ipv4': 'None'},
      parameter_dict
    )
    master_monitor_conf = open(os.path.join(
      self.instance_path, 'T-0', 'etc',
      'monitor-httpd.conf')).read()
    slave_monitor_conf = open(os.path.join(
      self.instance_path, 'T-2', 'etc',
      'monitor-httpd.conf')).read()

    self.assertTrue(
      'Listen [%s]:8196' % (self._ipv6_address,) in master_monitor_conf)
    self.assertTrue(
      'Listen [%s]:8072' % (self._ipv6_address,) in slave_monitor_conf)


class TestSlaveGlobalDisableHttp2(TestSlave):
  @classmethod
  def getInstanceParameterDict(cls):
    instance_parameter_dict = super(
      TestSlaveGlobalDisableHttp2, cls).getInstanceParameterDict()
    instance_parameter_dict['global-disable-http2'] = 'TrUe'
    return instance_parameter_dict

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
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
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
      },
      headers
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))


class TestEnableHttp2ByDefaultFalseSlaveGlobalDisableHttp2(
  TestEnableHttp2ByDefaultFalseSlave):
  @classmethod
  def getInstanceParameterDict(cls):
    instance_parameter_dict = super(
      TestEnableHttp2ByDefaultFalseSlaveGlobalDisableHttp2,
      cls).getInstanceParameterDict()
    instance_parameter_dict['global-disable-http2'] = 'TrUe'
    return instance_parameter_dict

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))


class TestEnableHttp2ByDefaultDefaultSlaveGlobalDisableHttp2(
  TestEnableHttp2ByDefaultDefaultSlave):
  @classmethod
  def getInstanceParameterDict(cls):
    instance_parameter_dict = super(
      TestEnableHttp2ByDefaultDefaultSlaveGlobalDisableHttp2,
      cls).getInstanceParameterDict()
    instance_parameter_dict['global-disable-http2'] = 'TrUe'
    return instance_parameter_dict

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    self.assertFalse(
      isHTTP2(parameter_dict['domain'], parameter_dict['public-ipv4']))


class TestSlaveSlapOSMasterCertificateCompatibilityOverrideMaster(
  SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def setUpMaster(cls):
    # run partition until AIKC finishes
    cls.runComputerPartitionUntil(
      cls.untilNotReadyYetNotInMasterKeyGenerateAuthUrl)

    parameter_dict = cls.requestDefaultInstance().getConnectionParameterDict()
    ca_certificate = requests.get(
      parameter_dict['kedifa-caucase-url'] + '/cas/crt/ca.crt.pem')
    assert ca_certificate.status_code == httplib.OK
    cls.ca_certificate_file = os.path.join(cls.working_directory, 'ca.crt.pem')
    open(cls.ca_certificate_file, 'w').write(ca_certificate.text)
    # Do not upload certificates for the master partition

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'public-ipv4': cls._ipv4_address,
      'apache-certificate': cls.certificate_pem,
      'apache-key': cls.key_pem,
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
      'mpm-graceful-shutdown-timeout': 2,
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'ssl_from_master_kedifa_overrides_master_certificate': {
        'url': cls.backend_url,
        'enable_cache': True
      },
    }

  def test_ssl_from_master_kedifa_overrides_master_certificate(self):
    reference = 'ssl_from_master_kedifa_overrides_master_certificate'
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    hostname = reference.translate(None, '_-')
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    _, key_pem, _, certificate_pem = \
        createSelfSignedCertificate([parameter_dict['domain']])

    master_parameter_dict = \
        self.requestDefaultInstance().getConnectionParameterDict()
    auth = requests.get(
      master_parameter_dict['master-key-generate-auth-url'],
      verify=self.ca_certificate_file)
    requests.put(
      master_parameter_dict['master-key-upload-url'] + auth.text,
      data=key_pem + certificate_pem,
      verify=self.ca_certificate_file)
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')


class TestSlaveSlapOSMasterCertificateCompatibility(
  SlaveHttpFrontendTestCase, TestDataMixin):

  @classmethod
  def setUpMaster(cls):
    # run partition until AIKC finishes
    cls.runComputerPartitionUntil(
      cls.untilNotReadyYetNotInMasterKeyGenerateAuthUrl)

    parameter_dict = cls.requestDefaultInstance().getConnectionParameterDict()
    ca_certificate = requests.get(
      parameter_dict['kedifa-caucase-url'] + '/cas/crt/ca.crt.pem')
    assert ca_certificate.status_code == httplib.OK
    cls.ca_certificate_file = os.path.join(cls.working_directory, 'ca.crt.pem')
    open(cls.ca_certificate_file, 'w').write(ca_certificate.text)
    # Do not upload certificates for the master partition

  @classmethod
  def prepareCertificate(cls):
    _, cls.ssl_from_slave_key_pem, _, cls.ssl_from_slave_certificate_pem = \
      createSelfSignedCertificate(
        [
          'sslfromslave.example.com',
        ])
    _, cls.ssl_from_slave_kedifa_overrides_key_pem, _, \
        cls.ssl_from_slave_kedifa_overrides_certificate_pem = \
        createSelfSignedCertificate(
          [
            'sslfromslavekedifaoverrides.example.com',
          ])
    _, cls.type_notebook_ssl_from_slave_key_pem, _, \
        cls.type_notebook_ssl_from_slave_certificate_pem = \
        createSelfSignedCertificate(
          [
            'typenotebooksslfromslave.example.com',
          ])
    _, cls.type_notebook_ssl_from_slave_kedifa_overrides_key_pem, _, \
        cls.type_notebook_ssl_from_slave_kedifa_overrides_certificate_pem = \
        createSelfSignedCertificate(
          [
            'typenotebooksslfromslavekedifaoverrides.example.com',
          ])

    cls.ca = CertificateAuthority(
      'TestSlaveSlapOSMasterCertificateCompatibility')

    _, cls.customdomain_ca_key_pem, csr, _ = createCSR(
      'customdomainsslcrtsslkeysslcacrt.example.com')
    _, cls.customdomain_ca_certificate_pem = cls.ca.signCSR(csr)

    _, cls.sslcacrtgarbage_ca_key_pem, csr, _ = createCSR(
      'sslcacrtgarbage.example.com')
    _, cls.sslcacrtgarbage_ca_certificate_pem = cls.ca.signCSR(csr)

    _, cls.ssl_from_slave_ca_key_pem, csr, _ = createCSR(
      'sslfromslave.example.com')
    _, cls.ssl_from_slave_ca_certificate_pem = cls.ca.signCSR(csr)

    _, cls.customdomain_key_pem, _, cls.customdomain_certificate_pem = \
        createSelfSignedCertificate(['customdomainsslcrtsslkey.example.com'])

    super(
      TestSlaveSlapOSMasterCertificateCompatibility, cls).prepareCertificate()

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'public-ipv4': cls._ipv4_address,
      'apache-certificate': cls.certificate_pem,
      'apache-key': cls.key_pem,
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
      'mpm-graceful-shutdown-timeout': 2,
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'ssl_from_master': {
        'url': cls.backend_url,
        'enable_cache': True,
      },
      'ssl_from_master_kedifa_overrides': {
        'url': cls.backend_url,
      },
      'ssl_from_slave': {
        'url': cls.backend_url,
        'ssl_crt': cls.ssl_from_slave_certificate_pem,
        'ssl_key': cls.ssl_from_slave_key_pem,
      },
      'ssl_from_slave_kedifa_overrides': {
        'url': cls.backend_url,
        'ssl_crt': cls.ssl_from_slave_kedifa_overrides_certificate_pem,
        'ssl_key': cls.ssl_from_slave_kedifa_overrides_key_pem,
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
      'ssl_ca_crt_garbage': {
        'url': cls.backend_url,
        'ssl_crt': cls.sslcacrtgarbage_ca_certificate_pem,
        'ssl_key': cls.sslcacrtgarbage_ca_key_pem,
        'ssl_ca_crt': 'some garbage',
      },
      'ssl_ca_crt_does_not_match': {
        'url': cls.backend_url,
        'ssl_crt': cls.certificate_pem,
        'ssl_key': cls.key_pem,
        'ssl_ca_crt': cls.ca.certificate_pem,
      },
      'type-notebook-ssl_from_master': {
        'url': cls.backend_url,
        'type': 'notebook',
      },
      'type-notebook-ssl_from_slave': {
        'url': cls.backend_url,
        'ssl_crt': cls.type_notebook_ssl_from_slave_certificate_pem,
        'ssl_key': cls.type_notebook_ssl_from_slave_key_pem,
        'type': 'notebook',
      },
      'type-notebook-ssl_from_master_kedifa_overrides': {
        'url': cls.backend_url,
        'type': 'notebook',
      },
      'type-notebook-ssl_from_slave_kedifa_overrides': {
        'url': cls.backend_url,
        'ssl_crt':
        cls.type_notebook_ssl_from_slave_kedifa_overrides_certificate_pem,
        'ssl_key':
        cls.type_notebook_ssl_from_slave_kedifa_overrides_key_pem,
        'type': 'notebook',
      }
    }

  def test_master_partition_state(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertRejectedSlavePromiseWithPop(parameter_dict)

    expected_parameter_dict = {
      'monitor-base-url': 'https://[%s]:8401' % self._ipv6_address,
      'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      'domain': 'example.com',
      'accepted-slave-amount': '12',
      'rejected-slave-amount': '0',
      'slave-amount': '12',
      'rejected-slave-dict': {
        # u"_ssl_ca_crt_only":
        # [u"ssl_ca_crt is present, so ssl_crt and ssl_key are required"],
        # u"_ssl_key-ssl_crt-unsafe":
        # [u"slave ssl_key and ssl_crt does not match"]
      },
      'warning-list': [
        u'apache-certificate is obsolete, please use master-key-upload-url',
        u'apache-key is obsolete, please use master-key-upload-url',
      ],
      'warning-slave-dict': {
        u'_custom_domain_ssl_crt_ssl_key': [
          u'ssl_key is obsolete, please use key-upload-url',
          u'ssl_crt is obsolete, please use key-upload-url'
        ],
        u'_custom_domain_ssl_crt_ssl_key_ssl_ca_crt': [
          u'ssl_key is obsolete, please use key-upload-url',
          u'ssl_crt is obsolete, please use key-upload-url',
          u'ssl_ca_crt is obsolete, please use key-upload-url'
        ],
        u'_ssl_ca_crt_does_not_match': [
          u'ssl_key is obsolete, please use key-upload-url',
          u'ssl_crt is obsolete, please use key-upload-url',
          u'ssl_ca_crt is obsolete, please use key-upload-url',
        ],
        u'_ssl_ca_crt_garbage': [
          u'ssl_key is obsolete, please use key-upload-url',
          u'ssl_crt is obsolete, please use key-upload-url',
          u'ssl_ca_crt is obsolete, please use key-upload-url',
        ],
        # u'_ssl_ca_crt_only': [
        #   u'ssl_ca_crt is obsolete, please use key-upload-url',
        # ],
        u'_ssl_from_slave': [
          u'ssl_key is obsolete, please use key-upload-url',
          u'ssl_crt is obsolete, please use key-upload-url',
        ],
        u'_ssl_from_slave_kedifa_overrides': [
          u'ssl_key is obsolete, please use key-upload-url',
          u'ssl_crt is obsolete, please use key-upload-url',
        ],
        # u'_ssl_key-ssl_crt-unsafe': [
        #   u'ssl_key is obsolete, please use key-upload-url',
        #   u'ssl_crt is obsolete, please use key-upload-url',
        # ],
        u'_type-notebook-ssl_from_slave': [
          u'ssl_key is obsolete, please use key-upload-url',
          u'ssl_crt is obsolete, please use key-upload-url',
        ],
        u'_type-notebook-ssl_from_slave_kedifa_overrides': [
          u'ssl_key is obsolete, please use key-upload-url',
          u'ssl_crt is obsolete, please use key-upload-url',
        ],
      }
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_ssl_from_master_kedifa_overrides(self):
    reference = 'ssl_from_master_kedifa_overrides'
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    _, key_pem, _, certificate_pem = \
        createSelfSignedCertificate([parameter_dict['domain']])

    # as now the place to put the key is known put the key there
    auth = requests.get(
      generate_auth,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, auth.status_code)

    data = certificate_pem + key_pem

    upload = requests.put(
      upload_url + auth.text,
      data=data,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, upload.status_code)
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_ssl_from_slave(self):
    reference = 'ssl_from_slave'
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)

    hostname = reference.translate(None, '_-')
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
        'warning-list': [
          'ssl_key is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
         ]
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.ssl_from_slave_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_ssl_from_slave_kedifa_overrides(self):
    reference = 'ssl_from_slave_kedifa_overrides'
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
        'warning-list': [
          'ssl_key is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
         ]
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.ssl_from_slave_kedifa_overrides_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    _, key_pem, _, certificate_pem = \
        createSelfSignedCertificate([parameter_dict['domain']])

    # as now the place to put the key is known put the key there
    auth = requests.get(
      generate_auth,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, auth.status_code)

    data = certificate_pem + key_pem

    upload = requests.put(
      upload_url + auth.text,
      data=data,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, upload.status_code)

    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_type_notebook_ssl_from_master(self):
    reference = 'type-notebook-ssl_from_master'
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    hostname = reference.translate(None, '_-')
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      HTTPS_PORT)

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_type_notebook_ssl_from_master_kedifa_overrides(self):
    reference = 'type-notebook-ssl_from_master_kedifa_overrides'
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      HTTPS_PORT)

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    _, key_pem, _, certificate_pem = \
        createSelfSignedCertificate([parameter_dict['domain']])

    # as now the place to put the key is known put the key there
    auth = requests.get(
      generate_auth,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, auth.status_code)

    data = certificate_pem + key_pem

    upload = requests.put(
      upload_url + auth.text,
      data=data,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, upload.status_code)

    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      HTTPS_PORT)

    self.assertEqual(
      certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_type_notebook_ssl_from_slave(self):
    reference = 'type-notebook-ssl_from_slave'
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    hostname = reference.translate(None, '_-')
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': '%s.example.com' % (hostname,),
        'replication_number': '1',
        'url': 'http://%s.example.com' % (hostname, ),
        'site_url': 'http://%s.example.com' % (hostname, ),
        'secure_access': 'https://%s.example.com' % (hostname, ),
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
        'warning-list': [
          'ssl_key is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
         ]
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      HTTPS_PORT)

    self.assertEqual(
      self.type_notebook_ssl_from_slave_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_type_notebook_ssl_from_slave_kedifa_overrides(self):
    reference = 'type-notebook-ssl_from_slave_kedifa_overrides'
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
        'warning-list': [
          'ssl_key is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
         ]
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      HTTPS_PORT)

    self.assertEqual(
      self.type_notebook_ssl_from_slave_kedifa_overrides_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    _, key_pem, _, certificate_pem = \
        createSelfSignedCertificate([parameter_dict['domain']])

    # as now the place to put the key is known put the key there
    auth = requests.get(
      generate_auth,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, auth.status_code)

    data = certificate_pem + key_pem

    upload = requests.put(
      upload_url + auth.text,
      data=data,
      verify=self.ca_certificate_file)
    self.assertEqual(httplib.CREATED, upload.status_code)

    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path',
      HTTPS_PORT)

    self.assertEqual(
      certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  @skip('Not implemented in new test system')
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
        'warning-list': ['ssl_key is obsolete, please use key-upload-url',
                         'ssl_crt is obsolete, please use key-upload-url']
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.customdomain_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
        'warning-list': [
          'ssl_key is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_ca_crt is obsolete, please use key-upload-url'
        ]
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.customdomain_ca_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    certificate_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'srv', 'bbb-ssl',
      '_custom_domain_ssl_crt_ssl_key_ssl_ca_crt.crt'))
    self.assertEqual(1, len(certificate_file_list))
    certificate_file = certificate_file_list[0]
    with open(certificate_file) as out:
      expected = self.customdomain_ca_certificate_pem + '\n' + \
        self.ca.certificate_pem + '\n' + self.customdomain_ca_key_pem
      self.assertEqual(
        expected,
        out.read()
      )

    ca = CertificateAuthority(
      'TestSlaveSlapOSMasterCertificateCompatibility')

    _, customdomain_ca_key_pem, csr, _ = createCSR(
      'customdomainsslcrtsslkeysslcacrt.example.com')
    _, customdomain_ca_certificate_pem = ca.signCSR(csr)

    slave_parameter_dict = self.getSlaveParameterDictDict()[
      'custom_domain_ssl_crt_ssl_key_ssl_ca_crt'].copy()
    slave_parameter_dict.update(
      ssl_crt=customdomain_ca_certificate_pem,
      ssl_key=customdomain_ca_key_pem,
      ssl_ca_crt=ca.certificate_pem,
    )

    self.slap.request(
        software_release=self.getSoftwareURL(),
        partition_reference='custom_domain_ssl_crt_ssl_key_ssl_ca_crt',
        partition_parameter_kw=slave_parameter_dict,
        shared=True
    )

    self.slap.waitForInstance()
    self.runKedifaUpdater()
    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      customdomain_ca_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    certificate_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'srv', 'bbb-ssl',
      '_custom_domain_ssl_crt_ssl_key_ssl_ca_crt.crt'))
    self.assertEqual(1, len(certificate_file_list))
    certificate_file = certificate_file_list[0]
    with open(certificate_file) as out:
      expected = customdomain_ca_certificate_pem + '\n' + ca.certificate_pem \
        + '\n' + customdomain_ca_key_pem
      self.assertEqual(
        expected,
        out.read()
      )

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
        'warning-list': [
          'ssl_key is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_ca_crt is obsolete, please use key-upload-url']
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
        parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.sslcacrtgarbage_ca_certificate_pem,
      der2pem(result.peercert)
    )

    self.assertEqualResultJson(result, 'Path', '/test-path')

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
        'warning-list': [
          'ssl_key is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_ca_crt is obsolete, please use key-upload-url'
        ]
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    certificate_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'srv', 'bbb-ssl',
      '_ssl_ca_crt_does_not_match.crt'))
    self.assertEqual(1, len(certificate_file_list))
    certificate_file = certificate_file_list[0]
    with open(certificate_file) as out:
      expected = self.certificate_pem + '\n' + self.ca.certificate_pem + \
        '\n' + self.key_pem
      self.assertEqual(
        expected,
        out.read()
      )


class TestSlaveSlapOSMasterCertificateCompatibilityUpdate(
  SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def setUpMaster(cls):
    # run partition until AIKC finishes
    cls.runComputerPartitionUntil(
      cls.untilNotReadyYetNotInMasterKeyGenerateAuthUrl)

    parameter_dict = cls.requestDefaultInstance().getConnectionParameterDict()
    ca_certificate = requests.get(
      parameter_dict['kedifa-caucase-url'] + '/cas/crt/ca.crt.pem')
    assert ca_certificate.status_code == httplib.OK
    cls.ca_certificate_file = os.path.join(cls.working_directory, 'ca.crt.pem')
    open(cls.ca_certificate_file, 'w').write(ca_certificate.text)
    # Do not upload certificates for the master partition

  instance_parameter_dict = {
    'domain': 'example.com',
    'port': HTTPS_PORT,
    'plain_http_port': HTTP_PORT,
    'kedifa_port': KEDIFA_PORT,
    'caucase_port': CAUCASE_PORT,
    'mpm-graceful-shutdown-timeout': 2,
  }

  @classmethod
  def getInstanceParameterDict(cls):
    if 'apache-certificate' not in cls.instance_parameter_dict:
      cls.instance_parameter_dict.update(**{
        'apache-certificate': cls.certificate_pem,
        'apache-key': cls.key_pem,
      })
    cls.instance_parameter_dict['public-ipv4'] = cls._ipv4_address
    return cls.instance_parameter_dict

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'ssl_from_master': {
        'url': cls.backend_url,
        'enable_cache': True,
      },
    }

  def test_master_partition_state(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertRejectedSlavePromiseWithPop(parameter_dict)

    expected_parameter_dict = {
      'monitor-base-url': 'https://[%s]:8401' % self._ipv6_address,
      'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      'domain': 'example.com',
      'accepted-slave-amount': '1',
      'rejected-slave-amount': '0',
      'rejected-slave-dict': {},
      'slave-amount': '1',
      'warning-list': [
        u'apache-certificate is obsolete, please use master-key-upload-url',
        u'apache-key is obsolete, please use master-key-upload-url',
      ],
    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

  def test_apache_key_apache_certificate_update(self):
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    _, key_pem, _, certificate_pem = createSelfSignedCertificate(
      [
        '*.customdomain.example.com',
        '*.example.com',
        '*.alias1.example.com',
      ])

    self.instance_parameter_dict.update(**{
      'apache-certificate': certificate_pem,
      'apache-key': key_pem,

    })
    self.requestDefaultInstance()
    self.slap.waitForInstance()
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')


class TestSlaveCiphers(SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'public-ipv4': cls._ipv4_address,
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
      'mpm-graceful-shutdown-timeout': 2,
      'ciphers': 'ECDHE-ECDSA-AES256-GCM-SHA384 ECDHE-RSA-AES256-GCM-SHA384'
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'default_ciphers': {
        'url': cls.backend_url,
        'enable_cache': True,
      },
      'own_ciphers': {
        'ciphers': 'ECDHE-ECDSA-AES128-GCM-SHA256 ECDHE-RSA-AES128-GCM-SHA256',
        'url': cls.backend_url,
        'enable_cache': True,
      },
    }

  def test_master_partition_state(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertRejectedSlavePromiseWithPop(parameter_dict)

    expected_parameter_dict = {
      'monitor-base-url': 'https://[%s]:8401' % self._ipv6_address,
      'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      'domain': 'example.com',
      'accepted-slave-amount': '2',
      'rejected-slave-amount': '0',
      'slave-amount': '2',
      'rejected-slave-dict': {}
    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

  def test_default_ciphers(self):
    parameter_dict = self.assertSlaveBase('default_ciphers')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.OK, result.status_code)

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(httplib.FOUND, result_http.status_code)

    configuration_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'caddy-slave-conf.d',
        '_default_ciphers.conf'
      ))[0]
    self.assertTrue(
      'ciphers ECDHE-ECDSA-AES256-GCM-SHA384 ECDHE-RSA-AES256-GCM-SHA384'
      in open(configuration_file).read()
    )

  def test_own_ciphers(self):
    parameter_dict = self.assertSlaveBase('own_ciphers')

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.OK, result.status_code)

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(httplib.FOUND, result_http.status_code)

    configuration_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'caddy-slave-conf.d',
        '_own_ciphers.conf'
      ))[0]
    self.assertTrue(
      'ciphers ECDHE-ECDSA-AES128-GCM-SHA256 ECDHE-RSA-AES128-GCM-SHA256'
      in open(configuration_file).read()
    )


class TestSlaveRejectReportUnsafeDamaged(SlaveHttpFrontendTestCase):
  @classmethod
  def prepareCertificate(cls):
    cls.ca = CertificateAuthority('TestSlaveRejectReportUnsafeDamaged')
    super(TestSlaveRejectReportUnsafeDamaged, cls).prepareCertificate()

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'public-ipv4': cls._ipv4_address,
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
    }

  @classmethod
  def setUpClass(cls):
    super(TestSlaveRejectReportUnsafeDamaged, cls).setUpClass()
    cls.fillSlaveParameterDictDict()
    cls.requestSlaves()
    try:
      cls.slap.waitForInstance(
        max_retry=2  # two runs shall be enough
      )
    except Exception:
      # ignores exceptions, as problems are tested
      pass
    cls.updateSlaveConnectionParameterDictDict()

  slave_parameter_dict_dict = {}

  @classmethod
  def getSlaveParameterDictDict(cls):
    return cls.slave_parameter_dict_dict

  @classmethod
  def fillSlaveParameterDictDict(cls):
    cls.slave_parameter_dict_dict = {
      'url': {
        'url': "https://[fd46::c2ae]:!py!u'123123'",
      },
      'https-url': {
        'https-url': "https://[fd46::c2ae]:!py!u'123123'",
      },
      'ssl-proxy-verify_ssl_proxy_ca_crt_damaged': {
        'url': cls.backend_https_url,
        'ssl-proxy-verify': True,
        'ssl_proxy_ca_crt': 'damaged',
      },
      'ssl-proxy-verify_ssl_proxy_ca_crt_empty': {
        'url': cls.backend_https_url,
        'ssl-proxy-verify': True,
        'ssl_proxy_ca_crt': '',
      },
      'bad-backend': {
        'url': 'http://1:2:3:4',
        'https-url': 'http://host.domain:badport',
      },
      'empty-backend': {
        'url': '',
        'https-url': '',
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
      },
      'bad-ciphers': {
        'ciphers': 'bad ECDHE-ECDSA-AES256-GCM-SHA384 again',
      },
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
      'ssl_ca_crt_only': {
        'url': cls.backend_url,
        'ssl_ca_crt': cls.ca.certificate_pem,
      },
      'ssl_key-ssl_crt-unsafe': {
        'ssl_key': '${section:option}ssl_keyunsafe\nunsafe',
        'ssl_crt': '${section:option}ssl_crtunsafe\nunsafe',
      },
    }

  def test_master_partition_state(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertRejectedSlavePromiseWithPop(parameter_dict)

    expected_parameter_dict = {
      'monitor-base-url': 'https://[%s]:8401' % self._ipv6_address,
      'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      'domain': 'example.com',
      'accepted-slave-amount': '7',
      'rejected-slave-amount': '14',
      'slave-amount': '21',
      'rejected-slave-dict': {
        '_https-url': ['slave https-url "https://[fd46::c2ae]:!py!u\'123123\'"'
                       ' invalid'],
        '_url': [u'slave url "https://[fd46::c2ae]:!py!u\'123123\'" invalid'],
        '_ssl-proxy-verify_ssl_proxy_ca_crt_damaged': [
          'ssl_proxy_ca_crt is invalid'
        ],
        '_ssl-proxy-verify_ssl_proxy_ca_crt_empty': [
          'ssl_proxy_ca_crt is invalid'
        ],
        '_bad-ciphers': [
          "Cipher 'bad' is not supported.",
          "Cipher 'again' is not supported."
        ],
        '_custom_domain-unsafe': [
          "custom_domain '${section:option} afterspace\\nafternewline' invalid"
        ],
        '_server-alias-unsafe': [
          "server-alias '${section:option}' not valid",
          "server-alias 'afterspace' not valid"
        ],
        '_site_2': ["custom_domain 'duplicate.example.com' clashes"],
        '_site_3': ["server-alias 'duplicate.example.com' clashes"],
        '_site_4': ["custom_domain 'duplicate.example.com' clashes"],
        '_ssl_ca_crt_only': [
          "ssl_ca_crt is present, so ssl_crt and ssl_key are required"],
        '_ssl_key-ssl_crt-unsafe': [
          "slave ssl_key and ssl_crt does not match"],
        '_bad-backend': [
          "slave url 'http://1:2:3:4' invalid",
          "slave https-url 'http://host.domain:badport' invalid"],
        '_empty-backend': [
          "slave url '' invalid",
          "slave https-url '' invalid"],
      },
      'warning-slave-dict': {
        '_ssl_ca_crt_only': [
          'ssl_ca_crt is obsolete, please use key-upload-url'],
        '_ssl_key-ssl_crt-unsafe': [
          'ssl_key is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url']}
    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

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

  def test_ssl_proxy_verify_ssl_proxy_ca_crt_damaged(self):
    parameter_dict = self.parseSlaveParameterDict(
      'ssl-proxy-verify_ssl_proxy_ca_crt_damaged')
    self.assertEqual(
      {'request-error-list': ["ssl_proxy_ca_crt is invalid"]},
      parameter_dict
    )

  def test_ssl_proxy_verify_ssl_proxy_ca_crt_empty(self):
    parameter_dict = self.parseSlaveParameterDict(
      'ssl-proxy-verify_ssl_proxy_ca_crt_empty')
    self.assertEqual(
      {'request-error-list': ["ssl_proxy_ca_crt is invalid"]},
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

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

  def test_bad_ciphers(self):
    parameter_dict = self.parseSlaveParameterDict('bad-ciphers')
    self.assertEqual(
      {
        'request-error-list': [
          "Cipher 'bad' is not supported.",
          "Cipher 'again' is not supported."
        ]
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(httplib.FOUND, result.status_code)

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], '')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      httplib.MOVED_PERMANENTLY,
      result.status_code
    )

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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.SERVICE_UNAVAILABLE, result.status_code)

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(httplib.FOUND, result_http.status_code)

    monitor_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'plugin',
        'check-_monitor-ipv4-test-unsafe-ipv4-packet-list-test.py'))[0]
    # get promise module and check that parameters are ok

    self.assertEqual(
      getPluginParameterDict(self.software_path, monitor_file),
      {
        'frequency': '720',
        'ipv4': 'true',
        'address': '${section:option}\nafternewline ipv4',
      }
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
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(httplib.SERVICE_UNAVAILABLE, result.status_code)

    result_http = fakeHTTPResult(
      parameter_dict['domain'], parameter_dict['public-ipv4'], 'test-path')
    self.assertEqual(httplib.FOUND, result_http.status_code)

    monitor_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'plugin',
        'check-_monitor-ipv6-test-unsafe-ipv6-packet-list-test.py'))[0]
    # get promise module and check that parameters are ok
    self.assertEqual(
      getPluginParameterDict(self.software_path, monitor_file),
      {
        'frequency': '720',
        'address': '${section:option}\nafternewline ipv6'
      }
    )

  def test_site_1(self):
    parameter_dict = self.parseSlaveParameterDict('site_1')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'duplicate.example.com',
        'replication_number': '1',
        'url': 'http://duplicate.example.com',
        'site_url': 'http://duplicate.example.com',
        'secure_access': 'https://duplicate.example.com',
        'public-ipv4': self._ipv4_address,
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

  def test_site_2(self):
    parameter_dict = self.parseSlaveParameterDict('site_2')
    self.assertEqual(
      {
        'request-error-list': ["custom_domain 'duplicate.example.com' clashes"]
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

  def test_ssl_ca_crt_only(self):
    parameter_dict = self.parseSlaveParameterDict('ssl_ca_crt_only')

    self.assertEqual(
      parameter_dict,
      {
        'request-error-list': [
          "ssl_ca_crt is present, so ssl_crt and ssl_key are required"],
        'warning-list': [
          'ssl_ca_crt is obsolete, please use key-upload-url',
        ],
      }
    )

  def test_ssl_key_ssl_crt_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict('ssl_key-ssl_crt-unsafe')
    self.assertEqual(
      {
        'request-error-list': ["slave ssl_key and ssl_crt does not match"],
        'warning-list': [
          'ssl_key is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url']
      },
      parameter_dict
    )

  def test_bad_backend(self):
    parameter_dict = self.parseSlaveParameterDict('bad-backend')
    self.assertEqual(
      {
        'request-error-list': [
          "slave url 'http://1:2:3:4' invalid",
          "slave https-url 'http://host.domain:badport' invalid"],
      },
      parameter_dict
    )

  def test_empty_backend(self):
    parameter_dict = self.parseSlaveParameterDict('empty-backend')
    self.assertEqual(
      {
        'request-error-list': [
          "slave url '' invalid",
          "slave https-url '' invalid"],
      },
      parameter_dict
    )
