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
from requests.structures import CaseInsensitiveDict
import http.client
from requests_toolbelt.adapters import source
import json
import multiprocessing
import subprocess
from unittest import skip
import ssl
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import time
import tempfile
import ipaddress
import io
import gzip
import base64
import re
from slapos.recipe.librecipe import generateHashFromFiles
import xml.etree.ElementTree as ET
import urllib.parse
import socket
import sys
import logging
import lzma
import random
import string
from slapos.slap.standalone import SlapOSNodeInstanceError
import caucase.client
import caucase.utils

import datetime

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.testing.utils import findFreeTCPPort
from slapos.testing.utils import getPromisePluginParameterDict
if __name__ == '__main__':
  SlapOSInstanceTestCase = object
else:
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

# IP on which test run, in order to mimic HTTP[s] access
TEST_IP = os.environ['SLAPOS_TEST_IPV4']

# "--resolve" inspired from https://stackoverflow.com/a/44378047/9256748
DNS_CACHE = {}


def unicode_escape(s):
  return s.encode('unicode_escape').decode()


def add_custom_dns(domain, port, ip):
  port = int(port)
  key = (domain, port)
  value = (socket.AF_INET, 1, 6, '', (ip, port))
  DNS_CACHE[key] = [value]


def new_getaddrinfo(*args):
  return DNS_CACHE[args[:2]]


def der2pem(der):
  certificate = x509.load_der_x509_certificate(der, default_backend())
  return certificate.public_bytes(serialization.Encoding.PEM)


# comes from https://stackoverflow.com/a/21788372/9256748
def patch_broken_pipe_error():
    """Monkey Patch BaseServer.handle_error to not write
    a stacktrace to stderr on broken pipe.
    https://stackoverflow.com/a/7913160"""
    from socketserver import BaseServer

    handle_error = BaseServer.handle_error

    def my_handle_error(self, request, client_address):
        type, err, tb = sys.exc_info()
        # there might be better ways to detect the specific erro
        if repr(err) == "error(32, 'Broken pipe')":
            pass
        else:
            handle_error(self, request, client_address)

    BaseServer.handle_error = my_handle_error


patch_broken_pipe_error()


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
    [x509.DNSName(str(q)) for q in name_list]
  )
  subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, 'Test Self Signed Certificate'),
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
      x509.IPAddress(ipaddress.ip_address(str(ip)))
    )
  csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
     x509.NameAttribute(NameOID.COMMON_NAME, str(common_name)),
  ]))

  if len(subject_alternative_name_list):
    csr = csr.add_extension(
      x509.SubjectAlternativeName(subject_alternative_name_list),
      critical=False
    )

  csr = csr.sign(key, hashes.SHA256(), default_backend())
  csr_pem = csr.public_bytes(serialization.Encoding.PEM)
  return key, key_pem, csr, csr_pem


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  pass


class CertificateAuthority(object):
  def __init__(self, common_name):
    self.key, self.key_pem = createKey()
    public_key = self.key.public_key()
    builder = x509.CertificateBuilder()
    builder = builder.subject_name(x509.Name([
      x509.NameAttribute(NameOID.COMMON_NAME, str(common_name)),
    ]))
    builder = builder.issuer_name(x509.Name([
      x509.NameAttribute(NameOID.COMMON_NAME, str(common_name)),
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


class RecurlestsResponse(object):
  # properties:
  #   content Content of the response, in bytes.
  #   cookies A CookieJar of Cookies the server sent back.
  #   history A list of Response objects from the history of the Request. Any
  #           redirect responses will end up here. The list is sorted from the
  #           oldest to the most recent request.
  #   is_permanent_redirect True if this Response one of the permanent versions
  #                         of redirect.
  #   is_redirect True if this Response is a well-formed HTTP redirect that
  #               could have been processed automatically (by
  #               Session.resolve_redirects).
  #   links Returns the parsed header links of the response, if any.
  #   next Returns a PreparedRequest for the next request in a redirect chain,
  #        if there is one.
  #   reason Textual reason of responded HTTP Status, e.g. “Not Found” or “OK”.
  def json(self, *args, **kwargs):
    return json.loads(self.text, *args, **kwargs)


class Recurlests(object):
  """curl command wrapper, mimicing requests"""
  def __init__(self, curl='curl'):
    self.curl = curl

  def get(self, url, **kwargs):
    return self.request('GET', url, **kwargs)

  def put(self, url, **kwargs):
    return self.request('PUT', url, **kwargs)

  def request(
    self,
    method,
    url,
    http3=True,
    http3_only=False,
    resolve_all=None,
    verify=True,
    allow_redirects=True,
    headers=None,
    auth=None,
    timeout=None,
    source_ip=None,
    data=None
  ):
    try:
      alt_svc = tempfile.NamedTemporaryFile(delete=False).name
      response_header_file = tempfile.NamedTemporaryFile(delete=False).name
      response_file = tempfile.NamedTemporaryFile(delete=False).name
      hsts_file = tempfile.NamedTemporaryFile(delete=False).name
      command_list = [
        self.curl,
        '--disable',
        '--globoff',
        '--path-as-is',
        '--no-progress-meter',
        '--dump-header', response_header_file,
        '--hsts', hsts_file,
        '--output', response_file,
        '--alt-svc', alt_svc,
        '--request', method,
        '--write-out', '%{json}'
      ]
      if data is not None:
        command_list.extend(['--data-binary', data])
      if allow_redirects:
        command_list.append('--location')
        command_list.extend(['--max-redirs', '100'])
      if source_ip is not None:
        command_list.extend(['--interface', source_ip])
      if not verify:
        command_list.append('--insecure')
      elif isinstance(verify, str):
        command_list.extend(['--cacert', verify])
      if headers is None:
        headers = {}
      for header, value in headers.items():
        command_list.extend(['--header', '%s: %s' % (header, value)])
      if auth is not None:
        command_list.extend(['--user', '%s:%s' % auth])
      if resolve_all is not None:
        for port, ip in resolve_all.items():
          command_list.extend(['--resolve', '*:%s:%s' % (port, ip)])
      if http3_only:
        command_list.append('--http3-only')
        if timeout is None:
          # forcibly set timeout to some nice value to detect 2nd case of HTTP3
          # unavailable
          timeout = 2
      elif http3 and url.startswith('https://'):
        command_list.append('--http3')
      if timeout is not None:
        if isinstance(timeout, int) or isinstance(timeout, float):
          command_list.extend(['--max-time', str(timeout)])
        else:
          command_list.exetend([
            '--connect-timeout', str(timeout[0]),
            '--max-time', str(timeout[1])])
      command_list.append(url)
      prc = subprocess.Popen(
        command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE
      )
      response = RecurlestsResponse()
      response.command_output, response.command_error = [
        q.decode() for q in prc.communicate()]
      response.command_returncode = prc.returncode
      try:
        response.write_out_json = json.loads(response.command_output)
      except Exception:
        raise
      with open(response_header_file) as fh:
        response.header_text = fh.read()
      response.headers = CaseInsensitiveDict()
      for line in response.header_text.splitlines()[1:]:
        if line.strip():
         header, value = line.split(':', 1)
         value = value.strip()
         response.headers.setdefault(header, [])
         response.headers[header].append(value)
      for header in response.headers.keys():
        response.headers[header] = ', '.join(response.headers[header])
      if response.headers.get('content-encoding') == 'gzip':
        with gzip.GzipFile(response_file) as fh:
          response.text = fh.read().decode()
      else:
        with open(response_file) as fh:
          response.text = fh.read()
      response.certificate_list = []
      response.certificate = None
      if 'certs' in response.write_out_json:
        in_cert = False
        cert_list = []
        for line in response.write_out_json['certs'].splitlines():
          if line == '-----END CERTIFICATE-----':
            in_cert = False
            cert_list.append(line)
            cert_list.append('')  # add the newline as it is expected
            response.certificate_list.append('\n'.join(cert_list).encode())
            cert_list = []
          elif line == '-----BEGIN CERTIFICATE-----':
            in_cert = True
          if in_cert:
            cert_list.append(line)
        if len(response.certificate_list):
          response.certificate = response.certificate_list[0]
      response.protocol = response.write_out_json['http_version']
      response.status_code = int(response.write_out_json['http_code'])
      if response.status_code < 400 and response.status_code != 0:
        response.ok = True
      else:
        response.ok = False
      response.content_type = response.write_out_json['content_type']
      response.method = response.write_out_json['method']
      response.response_code = response.write_out_json['response_code']
      response.speed_download = response.write_out_json['speed_download']
      response.speed_upload = response.write_out_json['speed_upload']
      response.time_appconnect = response.write_out_json['time_appconnect']
      response.time_connect = response.write_out_json['time_connect']
      response.time_namelookup = response.write_out_json['time_namelookup']
      response.time_pretransfer = response.write_out_json['time_pretransfer']
      response.time_redirect = response.write_out_json['time_redirect']
      response.time_starttransfer = response.write_out_json[
        'time_starttransfer']
      response.time_total = response.write_out_json['time_total']
      response.elapsed = float(response.time_total)
      response.url = response.write_out_json['url']
      response.url_effective = response.write_out_json['url_effective']
      response.urlnum = response.write_out_json['urlnum']
      response.curl_version = response.write_out_json['curl_version']
      response.command_list = command_list
      return response
    finally:
      os.unlink(alt_svc)
      os.unlink(response_header_file)
      os.unlink(response_file)
      os.unlink(hsts_file)
    # kwargs:
    #  params - Dictionary, list of tuples or bytes to send in the query
    #           string for the Request.
    #  data - Dictionary, list of tuples, bytes, or file-like object to send
    #         in the body of the Request.
    #  json - A JSON serializable Python object to send in the body of the
    #         Request.
    #  cookies - Dict or CookieJar object to send with the Request.
    #  files - Dictionary of 'name': file-like-objects (or {'name':
    #  proxies - Dictionary mapping protocol to the URL of the proxy.
    #  stream - if False, the response content will be immediately downloaded.
    #  cert - if String, path to ssl client cert file (.pem). If Tuple,
    #         ('cert', 'key') pair.


mimikra = Recurlests()


class AtsMixin(object):
  def _hack_ats(self, max_stale_age):
    records_config = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'trafficserver', 'records.config'
      ))
    self.assertEqual(1, len(records_config))
    self._hack_ats_records_config_path = records_config[0]
    original_max_stale_age = \
        'CONFIG proxy.config.http.cache.max_stale_age INT 604800\n'
    new_max_stale_age = \
        'CONFIG proxy.config.http.cache.max_stale_age INT %s\n' % (
          max_stale_age,)
    with open(self._hack_ats_records_config_path) as fh:
      self._hack_ats_original_records_config = fh.readlines()
    # sanity check - are we really do it?
    self.assertIn(
      original_max_stale_age,
      self._hack_ats_original_records_config)
    new_records_config = []
    max_stale_age_changed = False
    for line in self._hack_ats_original_records_config:
      if line == original_max_stale_age:
        line = new_max_stale_age
        max_stale_age_changed = True
      new_records_config.append(line)
    self.assertTrue(max_stale_age_changed)
    with open(self._hack_ats_records_config_path, 'w') as fh:
      fh.write(''.join(new_records_config))
    self._hack_ats_restart()

  def _unhack_ats(self):
    with open(self._hack_ats_records_config_path, 'w') as fh:
      fh.write(''.join(self._hack_ats_original_records_config))
    self._hack_ats_restart()

  def _hack_ats_restart(self):
    for process_info in self.callSupervisorMethod('getAllProcessInfo'):
      if process_info['name'].startswith(
        'trafficserver') and process_info['name'].endswith('-on-watch'):
        self.callSupervisorMethod(
          'stopProcess', '%(group)s:%(name)s' % process_info)
        self.callSupervisorMethod(
          'startProcess', '%(group)s:%(name)s' % process_info)
    # give short time for the ATS to start back
    time.sleep(5)
    for process_info in self.callSupervisorMethod('getAllProcessInfo'):
      if process_info['name'].startswith(
        'trafficserver') and process_info['name'].endswith('-on-watch'):
        self.assertEqual(process_info['statename'], 'RUNNING')


class TestDataMixin(object):
  def getTrimmedProcessInfo(self):
    return '\n'.join(sorted([
      '%(group)s:%(name)s %(statename)s' % q for q
      in self.callSupervisorMethod('getAllProcessInfo')
      if q['name'] != 'watchdog' and q['group'] != 'watchdog']))

  def assertTestData(self, runtime_data, data_replacement_dict=None, msg=None):
    if data_replacement_dict is None:
      data_replacement_dict = {}
    filename = '%s.txt' % (self.id(),)
    test_data_file = os.path.join(
      os.path.dirname(os.path.realpath(__file__)), 'test_data', filename)

    try:
      with open(test_data_file) as fh:
        test_data = fh.read().strip()
    except IOError:
      test_data = ''

    for replacement in sorted(data_replacement_dict.keys()):
      value = data_replacement_dict[replacement]
      runtime_data = runtime_data.replace(value, replacement)

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
        with open(test_data_file, 'w') as fh:
          fh.write(runtime_data.strip() + '\n')
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

  def test00file_list_log(self):
    # test00 name chosen to be run just after setup
    self._test_file_list(['var', 'log'], [
      # no control at all when cron would kick in, ignore it
      'cron.log',
      # appears late and is quite unstable, no need to assert
      'trafficserver/.diags.log.meta',
      'trafficserver/.manager.log.meta',
      'trafficserver/.squid.log.meta',
      'trafficserver/diags.log',
      'trafficserver/squid.log',
      # not important, appears sometimes
      'trafficserver/.error.log.meta',
      'trafficserver/error.log',
      'trafficserver/.traffic.out.meta',
      'trafficserver/traffic.out',
    ])

  def test00file_list_run(self):
    # test00 name chosen to be run just after setup
    self._test_file_list(['var', 'run'], [
      # can't be sure regarding its presence
      'frontend_haproxy_configuration_last_state',
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

  def test00supervisor_state(self):
    # test00 name chosen to be run just after setup
    # give a chance for etc/run scripts to finish
    time.sleep(1)

    hash_file_list = [os.path.join(
        self.computer_partition_root_path, 'software_release/buildout.cfg')]
    data_replacement_dict = {
      '{hash-generic}': generateHashFromFiles(hash_file_list)
    }
    for backend_haproxy_wrapper_path in glob.glob(os.path.join(
      self.instance_path, '*', 'bin', 'backend-haproxy-wrapper')):
      partition_id = backend_haproxy_wrapper_path.split('/')[-3]
      data_replacement_dict['{hash-backend-haproxy-%s}' % (partition_id)] =  \
          generateHashFromFiles([
            backend_haproxy_wrapper_path] + hash_file_list)
    for rejected_slave_publish_path in glob.glob(os.path.join(
      self.instance_path, '*', 'etc', 'nginx-master-introspection.conf')):
      partition_id = rejected_slave_publish_path.split('/')[-3]
      rejected_slave_pem_path = os.path.join(
        self.instance_path, partition_id, 'etc', 'master-introspection.pem')
      data_replacement_dict[
        '{hash-master-introspection}'
      ] = generateHashFromFiles(
        [rejected_slave_publish_path, rejected_slave_pem_path] + hash_file_list
      )

    runtime_data = self.getTrimmedProcessInfo()
    self.assertTestData(
      runtime_data, data_replacement_dict=data_replacement_dict)

  def _updateDataReplacementDict(self, data_replacement_dict):
    pass

  def test00cluster_request_instance_parameter_dict(self):
    # test00 name chosen to be run just after setup
    cluster_request_parameter_list = []
    data_replacement_dict = {}
    computer = self.slap._slap.registerComputer('local')
    # state of parameters of all instances
    for partition in computer.getComputerPartitionList():
      if partition.getState() == 'destroyed':
        continue
      parameter_dict = partition.getInstanceParameterDict()
      if '_' in parameter_dict:
        # deserialize for pretty printing only, and keep in mind
        # that slave-kedifa-information content is string, so exactly it's
        # sent like this to the real master
        parameter_dict['_'] = json.loads(parameter_dict['_'])
      parameter_dict['timestamp'] = '@@TIMESTAMP@@'
      cluster_request_parameter_list.append(parameter_dict)

    # XXX: Dirty decode/encode/decode...?
    data_replacement_dict = {
      '@@_ipv4_address@@': self._ipv4_address,
      '@@_ipv6_address@@': self._ipv6_address,
      '@@_server_http_port@@': str(self._server_http_port),
      '@@_server_https_auth_port@@': str(self._server_https_auth_port),
      '@@_server_https_port@@': str(self._server_https_port),
      '@@_server_netloc_a_http_port@@': str(self._server_netloc_a_http_port),
      '@@_server_netloc_b_http_port@@': str(self._server_netloc_b_http_port),
      '@@another_server_ca.certificate_pem@@': unicode_escape(
        self.another_server_ca.certificate_pem.decode()),
      '@@another_server_ca.certificate_pem_double@@': unicode_escape(
        unicode_escape(self.another_server_ca.certificate_pem.decode())),
      # self.getSoftwareURL can contain other replacements so do it first
      '@@00getSoftwareURL@@': self.getSoftwareURL(),
      '@@test_server_ca.certificate_pem@@': unicode_escape(
        self.test_server_ca.certificate_pem.decode()),
      '@@test_server_ca.certificate_pem_double@@': unicode_escape(
        unicode_escape(self.test_server_ca.certificate_pem.decode())),
    }

    # support slave-less test cases
    if getattr(self, 'getSlaveConnectionParameterDictDict', None) is not None:
      for reference, value in self.getSlaveConnectionParameterDictDict(
        ).items():
        data_replacement_dict[
          '@@%s_key-generate-auth-url@@' % reference] = value[
          'key-generate-auth-url'].split('/')[-2]
        data_replacement_dict[
          '@@%s_key-upload-url@@' % reference] = value[
          'key-generate-auth-url'].split('/')[-1]

    connection_parameter_dict = self.requestDefaultInstance(
      ).getConnectionParameterDict()
    data_replacement_dict[
      '@@master-key-download-url_endpoint@@'] = connection_parameter_dict[
      'master-key-generate-auth-url'].split('/')[-2]
    data_replacement_dict['@@monitor-password@@'] = connection_parameter_dict[
      'monitor-setup-url'].split('=')[-1]
    json_data = json.dumps(
      cluster_request_parameter_list, indent=2,
      # keys are sorted, even after deserializing, in order to have
      # stable information about the sent parameters between runs
      sort_keys=True
    )
    # again some mangling -- allow subclasses to update on need
    self._updateDataReplacementDict(data_replacement_dict)
    self.assertTestData(json_data, data_replacement_dict=data_replacement_dict)


def fakeHTTPSResult(domain, path, port=HTTPS_PORT,
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
  # Expose some Via to show how nicely it arrives to the backend
  headers.setdefault('Via', 'http/1.1 clientvia')

  session = requests.Session()
  with session:
    if source_ip is not None:
      new_source = source.SourceAddressAdapter(source_ip)
      session.mount('http://', new_source)
      session.mount('https://', new_source)
    socket_getaddrinfo = socket.getaddrinfo
    try:
      add_custom_dns(domain, port, TEST_IP)
      socket.getaddrinfo = new_getaddrinfo
      # Use a prepared request, to disable path normalization.
      # We need this because some test checks requests with paths like
      # /test-path/deep/.././deeper but we don't want the client to send
      # /test-path/deeper
      # See also https://github.com/psf/requests/issues/5289
      url = 'https://%s:%s/%s' % (domain, port, path)
      req = requests.Request(
          method='GET',
          url=url,
          headers=headers,
          cookies=cookies,
      )
      prepped = req.prepare()
      prepped.url = url
      return session.send(prepped, verify=False, allow_redirects=False)
    finally:
      socket.getaddrinfo = socket_getaddrinfo


def fakeHTTPResult(domain, path, port=HTTP_PORT,
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
  # Expose some Via to show how nicely it arrives to the backend
  headers.setdefault('Via', 'http/1.1 clientvia')
  headers['Host'] = '%s:%s' % (domain, port)
  session = requests.Session()
  with session:
    if source_ip is not None:
      new_source = source.SourceAddressAdapter(source_ip)
      session.mount('http://', new_source)
      session.mount('https://', new_source)

    # Use a prepared request, to disable path normalization.
    url = 'http://%s:%s/%s' % (TEST_IP, port, path)
    req = requests.Request(method='GET', url=url, headers=headers)
    prepped = req.prepare()
    prepped.url = url
    return session.send(prepped, allow_redirects=False)


class TestHandler(BaseHTTPRequestHandler):
  identification = None
  configuration = {}
  # override Server header response
  server_version = "TestBackend"
  sys_version = ""

  log_message = logging.getLogger(__name__ + '.TestHandler').info

  def do_DELETE(self):
    config = self.configuration.pop(self.path, None)
    if config is None:
      self.send_response(204)
      self.end_headers()
    else:
      self.send_response(200)
      self.send_header("Content-Type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps({self.path: config}, indent=2))

  def do_PUT(self):
    incoming_config = {}
    for key, value in list(self.headers.items()):
      if key.startswith('X-'):
        incoming_config[key] = value
    config = {
      'status_code': incoming_config.pop('X-Reply-Status-Code', '200')
    }
    prefix = 'X-Reply-Header-'
    length = len(prefix)
    for key in list(incoming_config.keys()):
      if key.startswith(prefix):
        header = '-'.join([q.capitalize() for q in key[length:].split('-')])
        config[header] = incoming_config.pop(key)

    if 'X-Reply-Body' in incoming_config:
      config['Body'] = base64.b64decode(
        incoming_config.pop('X-Reply-Body')).decode()

    config['X-Drop-Header'] = incoming_config.pop('X-Drop-Header', None)
    self.configuration[self.path] = config

    self.send_response(201)
    self.send_header("Content-Type", "application/json")
    self.end_headers()
    reply = {self.path: config}
    if incoming_config:
      reply['unknown_config'] = incoming_config
    self.wfile.write(json.dumps(reply, indent=2).encode())

  def do_POST(self):
    return self.do_GET()

  def do_GET(self):
    config = self.configuration.get(self.path, None)
    if config is not None:
      config = config.copy()
      response = config.pop('Body', None)
      status_code = int(config.pop('status_code'))
      timeout = int(config.pop('Timeout', '0'))
      compress = int(config.pop('Compress', '0'))
      drop_header_list = []
      for header in (config.pop('X-Drop-Header') or '').split():
        drop_header_list.append(header)
      header_dict = config
    else:
      drop_header_list = []
      for header in (self.headers.get('x-drop-header') or '').split():
        drop_header_list.append(header)
      response = None
      status_code = 200
      timeout = int(self.headers.get('timeout', '0'))
      if 'x-maximum-timeout' in self.headers:
        maximum_timeout = int(self.headers['x-maximum-timeout'])
        timeout = random.randrange(maximum_timeout)
      if 'x-response-size' in self.headers:
        min_response, max_response = [
          int(q) for q in self.headers['x-response-size'].split(' ')]
        reponse_size = random.randrange(min_response, max_response)
        response = ''.join(
          random.choice(string.lowercase) for x in range(reponse_size))
      compress = int(self.headers.get('compress', '0'))
      header_dict = {}
      prefix = 'x-reply-header-'
      length = len(prefix)
      for key, value in list(self.headers.items()):
        if key.startswith(prefix):
          header = '-'.join([q.capitalize() for q in key[length:].split('-')])
          header_dict[header] = value.strip()
    if response is None:
      if 'x-reply-body' not in self.headers:
        headers_dict = dict()
        for header in list(self.headers.keys()):
          content = self.headers.get_all(header)
          if len(content) == 0:
            headers_dict[header] = None
          elif len(content) == 1:
            headers_dict[header] = content[0]
          else:
            headers_dict[header] = content
        response = {
          'Path': self.path,
          'Incoming Headers': headers_dict
        }
        response = json.dumps(response, indent=2)
      else:
        response = base64.b64decode(self.headers['x-reply-body'])

    time.sleep(timeout)
    self.send_response_only(status_code)
    self.send_header('Server', self.server_version)

    for key, value in list(header_dict.items()):
      self.send_header(key, value)

    if self.identification is not None:
      self.send_header('X-Backend-Identification', self.identification)

    if 'Content-Type' not in drop_header_list:
      self.send_header("Content-Type", "application/json")
    if 'Set-Cookie' not in drop_header_list:
      self.send_header('Set-Cookie', 'secured=value;secure')
      self.send_header('Set-Cookie', 'nonsecured=value')

    if 'Via' not in drop_header_list:
      self.send_header('Via', 'http/1.1 backendvia')
    if compress:
      self.send_header('Content-Encoding', 'gzip')
      out = io.BytesIO()
      # compress with level 0, to find out if in the middle someting would
      # like to alter the compression
      with gzip.GzipFile(fileobj=out, mode="wb", compresslevel=0) as f:
        f.write(response.encode())
      response = out.getvalue()
      self.send_header('Backend-Content-Length', len(response))
    if 'Content-Length' not in drop_header_list:
      self.send_header('Content-Length', len(response))
    self.end_headers()
    if getattr(response, 'encode', None) is not None:
      response = response.encode()
    self.wfile.write(response)


class HttpFrontendTestCase(SlapOSInstanceTestCase):
  # show full diffs, as it is required for proper analysis of problems
  maxDiff = None

  # minimise partition path
  __partition_reference__ = 'T-'

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
    server = ThreadedHTTPServer(
      (cls._ipv4_address, cls._server_http_port),
      TestHandler)

    server_https = ThreadedHTTPServer(
      (cls._ipv4_address, cls._server_https_port),
      TestHandler)

    server_https.socket = ssl.wrap_socket(
      server_https.socket,
      certfile=cls.test_server_certificate_file.name,
      server_side=True)

    cls.backend_url = 'http://%s:%s/' % server.server_address
    server_process = multiprocessing.Process(
      target=server.serve_forever, name='HTTPServer')
    server_process.start()
    # from now on, socket is used by server subprocess, we can close it
    server.socket.close()
    cls.logger.debug('Started process %s' % (server_process,))

    cls.backend_https_url = 'https://%s:%s/' % server_https.server_address
    server_https_process = multiprocessing.Process(
      target=server_https.serve_forever, name='HTTPSServer')
    server_https_process.start()
    server_https.socket.close()
    cls.logger.debug('Started process %s' % (server_https_process,))

    class NetlocHandler(TestHandler):
      identification = 'netloc'

    netloc_a_http = ThreadedHTTPServer(
      (cls._ipv4_address, cls._server_netloc_a_http_port),
      NetlocHandler)
    netloc_a_http_process = multiprocessing.Process(
      target=netloc_a_http.serve_forever, name='netloc-a-http')
    netloc_a_http_process.start()
    netloc_a_http.socket.close()

    netloc_b_http = ThreadedHTTPServer(
      (cls._ipv4_address, cls._server_netloc_b_http_port),
      NetlocHandler)
    netloc_b_http_process = multiprocessing.Process(
      target=netloc_b_http.serve_forever, name='netloc-b-http')
    netloc_b_http_process.start()
    netloc_b_http.socket.close()

    cls.server_process_list = [
      server_process,
      server_https_process,
      netloc_a_http_process,
      netloc_b_http_process,
    ]

  @classmethod
  def cleanUpCertificate(cls):
    if getattr(cls, 'test_server_certificate_file', None) is not None:
      os.unlink(cls.test_server_certificate_file.name)

  @classmethod
  def stopServerProcess(cls):
    for process in cls.server_process_list:
      if process is not None:
        cls.logger.debug('Stopping process %s' % (process,))
        process.join(10)
        process.terminate()
        time.sleep(0.1)
        if process.is_alive():
          cls.logger.warning(
            'Process %s still alive' % (process, ))

  def startAuthenticatedServerProcess(self):
    master_parameter_dict = self.parseConnectionParameterDict()
    caucase_url = master_parameter_dict['backend-client-caucase-url']
    ca_certificate = requests.get(caucase_url + '/cas/crt/ca.crt.pem')
    assert ca_certificate.status_code == http.client.OK
    ca_certificate_file = os.path.join(
      self.working_directory, 'ca-backend-client.crt.pem')
    with open(ca_certificate_file, 'w') as fh:
      fh.write(ca_certificate.text)

    class OwnTestHandler(TestHandler):
      identification = 'Auth Backend'

    server_https_auth = ThreadedHTTPServer(
      (self._ipv4_address, self._server_https_auth_port),
      OwnTestHandler)

    server_https_auth.socket = ssl.wrap_socket(
      server_https_auth.socket,
      certfile=self.test_server_certificate_file.name,
      cert_reqs=ssl.CERT_REQUIRED,
      ca_certs=ca_certificate_file,
      server_side=True)

    self.backend_https_auth_url = 'https://%s:%s/' \
        % server_https_auth.server_address

    self.server_https_auth_process = multiprocessing.Process(
      target=server_https_auth.serve_forever, name='HTTPSServerAuth')
    self.server_https_auth_process.start()
    server_https_auth.socket.close()
    self.logger.debug('Started process %s' % (self.server_https_auth_process,))

  def stopAuthenticatedServerProcess(self):
    self.logger.debug('Stopping process %s' % (
      self.server_https_auth_process,))
    self.server_https_auth_process.join(10)
    self.server_https_auth_process.terminate()
    time.sleep(0.1)
    if self.server_https_auth_process.is_alive():
      self.logger.warning(
        'Process %s still alive' % (self.server_https_auth_process, ))

  @classmethod
  def _fetchKedifaCaucaseCaCertificateFile(cls, parameter_dict):
    ca_certificate = requests.get(
      parameter_dict['kedifa-caucase-url'] + '/cas/crt/ca.crt.pem')
    assert ca_certificate.status_code == http.client.OK
    cls.kedifa_caucase_ca_certificate_file = os.path.join(
      cls.working_directory, 'kedifa-caucase.ca.crt.pem')
    with open(cls.kedifa_caucase_ca_certificate_file, 'w') as fh:
      fh.write(ca_certificate.text)

  @classmethod
  def _fetchBackendClientCaCertificateFile(cls, parameter_dict):
    ca_certificate = requests.get(
      parameter_dict['backend-client-caucase-url'] + '/cas/crt/ca.crt.pem')
    assert ca_certificate.status_code == http.client.OK
    cls.backend_client_caucase_ca_certificate_file = os.path.join(
      cls.working_directory, 'backend-client-caucase.ca.crt.pem')
    with open(cls.backend_client_caucase_ca_certificate_file, 'w') as fh:
      fh.write(ca_certificate.text)

  @classmethod
  def setUpMaster(cls):
    parameter_dict = cls.requestDefaultInstance().getConnectionParameterDict()
    cls._fetchKedifaCaucaseCaCertificateFile(parameter_dict)
    auth = requests.get(
      parameter_dict['master-key-generate-auth-url'],
      verify=cls.kedifa_caucase_ca_certificate_file)
    assert auth.status_code == http.client.CREATED
    upload = requests.put(
      parameter_dict['master-key-upload-url'] + auth.text,
      data=cls.key_pem + cls.certificate_pem,
      verify=cls.kedifa_caucase_ca_certificate_file)
    assert upload.status_code == http.client.CREATED
    cls.runKedifaUpdater()

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
      # give haproxy a moment to refresh its config, as sending signal does not
      # block until haproxy is refreshed
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
  def callSupervisorMethod(cls, method, *args, **kwargs):
    with cls.slap.instance_supervisor_rpc as instance_supervisor:
      return getattr(instance_supervisor, method)(*args, **kwargs)

  def assertPublishFailsafeErrorPromiseEmptyWithPop(self, parameter_dict):
    promise_url = parameter_dict.pop(
      'publish-failsafe-error-promise-url')

    try:
      result = requests.get(promise_url, verify=False)
      self.assertEqual("", result.text)
    except AssertionError:
      raise
    except Exception as e:
      self.fail(e)

  def assertRejectedSlavePromiseEmptyWithPop(self, parameter_dict):
    rejected_slave_promise_url = parameter_dict.pop(
      'rejected-slave-promise-url')

    try:
      result = requests.get(rejected_slave_promise_url, verify=False)
      if result.text == '':
        result_json = {}
      else:
        result_json = result.json()
      self.assertEqual(
        {},
        result_json
      )
    except AssertionError:
      raise
    except Exception as e:
      self.fail(e)

  def assertHttp2(self, domain):
    result = mimikra.get(
      'https://%(domain)s:%(https_port)s/' % dict(
        domain=domain, https_port=HTTPS_PORT),
      resolve_all={HTTPS_PORT: TEST_IP},
      verify=False
    )
    self.assertEqual('2', result.protocol)

  def assertHttp11(self, domain):
    result = mimikra.get(
      'https://%(domain)s:%(https_port)s/' % dict(
        domain=domain, https_port=HTTPS_PORT),
      resolve_all={HTTPS_PORT: TEST_IP},
      verify=False
    )
    self.assertEqual('1.1', result.protocol)

  def assertHttp1(self, domain):
    result = mimikra.get(
      'https://%(domain)s:%(https_port)s/' % dict(
        domain=domain, https_port=HTTPS_PORT),
      resolve_all={HTTPS_PORT: TEST_IP},
      verify=False
    )
    self.assertEqual('1', result.protocol)

  def assertResponseHeaders(
    self, result, cached=False, via=True, backend_reached=True):
    headers = result.headers.copy()
    self.assertKeyWithPop('Content-Length', headers)

    if backend_reached:
      self.assertEqual('TestBackend', headers.pop('Server', ''))
      self.assertKeyWithPop('Date', headers)

    via_id = '%s-%s' % (
      self.node_information_dict['node-id'],
      list(self.node_information_dict['version-hash-history'].keys())[0])
    if via:
      self.assertIn('Via', headers)
      if cached:
        self.assertEqual(
          'http/1.1 backendvia, '
          'HTTP/1.1 rapid-cdn-backend-%(via_id)s, '
          'http/1.0 rapid-cdn-cache-%(via_id)s, '
          'HTTP/1.1 rapid-cdn-frontend-%(via_id)s' % dict(via_id=via_id),
          headers.pop('Via')
        )
      else:
        self.assertEqual(
          'http/1.1 backendvia, '
          'HTTP/1.1 rapid-cdn-backend-%(via_id)s, '
          'HTTP/1.1 rapid-cdn-frontend-%(via_id)s' % dict(via_id=via_id),
          headers.pop('Via')
        )
    else:
      self.assertNotIn('Via', headers)
    return headers

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
      http.client.OK,
      result.status_code,
      'While accessing %r of %r the status code was %r' % (
        url, frontend, result.status_code))
    # check that the result is correct JSON, which allows to access
    # information about all logs
    self.assertEqual(
      'application/json',
      result.headers['Content-Type']
    )
    self.assertEqual(
      sorted([q['name'] for q in result.json()]),
      ['access.log', 'backend.log'])
    # assert only for few tests, as logs are available for sure only
    # for few of them
    for test_name in [
      'test_url', 'test_auth_to_backend', 'test_compressed_result']:
      if self.id().endswith(test_name):
        self.assertEqual(
          http.client.OK,
          requests.get(url + 'backend.log', verify=False).status_code
        )
        self.assertEqual(
          http.client.OK,
          requests.get(url + 'access.log', verify=False).status_code
        )

  def assertKedifaKeysWithPop(self, parameter_dict, prefix=''):
    generate_auth_url = parameter_dict.pop('%skey-generate-auth-url' % (
      prefix,))
    upload_url = parameter_dict.pop('%skey-upload-url' % (prefix,))
    kedifa_ipv6_base = 'https://[%s]:%s' % (self._ipv6_address, KEDIFA_PORT)
    base = '^' + kedifa_ipv6_base.replace(
      '[', r'\[').replace(']', r'\]') + '/.{32}'
    self.assertRegex(
      generate_auth_url,
      base + r'\/generateauth$'
    )
    self.assertRegex(
      upload_url,
      base + r'\?auth=$'
    )

    kedifa_caucase_url = parameter_dict.pop('kedifa-caucase-url')
    self.assertEqual(
      kedifa_caucase_url,
      'http://[%s]:%s' % (self._ipv6_address, CAUCASE_PORT),
    )

    return generate_auth_url, upload_url

  def assertNodeInformationWithPop(self, parameter_dict):
    key = 'frontend-node-1-node-information-json'
    node_information_json_dict = {}
    for k in list(parameter_dict.keys()):
      if k.startswith('frontend-node') and k.endswith(
        'node-information-json'):
        node_information_json_dict[k] = parameter_dict.pop(k)
    self.assertEqual(
      [key],
      list(node_information_json_dict.keys())
    )

    node_information_dict = json.loads(node_information_json_dict[key])
    self.assertIn("node-id", node_information_dict)
    self.assertIn("version-hash-history", node_information_dict)
    self.node_information_dict = node_information_dict

  def assertBackendHaproxyStatisticUrl(self, parameter_dict):
    url_key = 'frontend-node-1-backend-haproxy-statistic-url'
    backend_haproxy_statistic_url_dict = {}
    for key in list(parameter_dict.keys()):
      if key.startswith('frontend-node') and key.endswith(
        'backend-haproxy-statistic-url'):
        backend_haproxy_statistic_url_dict[key] = parameter_dict.pop(key)
    self.assertEqual(
      [url_key],
      list(backend_haproxy_statistic_url_dict.keys())
    )

    backend_haproxy_statistic_url = backend_haproxy_statistic_url_dict[url_key]
    result = requests.get(
      backend_haproxy_statistic_url,
      verify=False,
    )
    self.assertEqual(http.client.OK, result.status_code)
    self.assertIn('testing partition 0', result.text)
    self.assertIn('Statistics Report for HAProxy', result.text)

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
      del (HTTPResponse.orig__init__)

    HTTPAdapter = requests.adapters.HTTPAdapter
    if getattr(HTTPAdapter, 'orig_build_response', None) is not None:
      HTTPAdapter.build_response = HTTPAdapter.orig_build_response
      del (HTTPAdapter.orig_build_response)

  def setUp(self):
    # patch requests in order to being able to extract SSL certs
    self.patchRequests()

  def tearDown(self):
    self.unpatchRequests()
    super(HttpFrontendTestCase, self).tearDown()

  def parseParameterDict(self, parameter_dict):
    parsed_parameter_dict = {}
    for key, value in list(parameter_dict.items()):
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
    return [
      q for q in glob.glob(os.path.join(self.instance_path, '*',))
      if os.path.exists(
        os.path.join(q, 'etc', 'nginx-master-introspection.conf'))][0]

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
  def waitForFrontend(cls):
    def method():
      fakeHTTPSResult(
        cls._ipv4_address,
        '/',
      )
    cls.waitForMethod('waitForFrontend', method)

  @classmethod
  def _cleanup(cls, snapshot_name):
    cls.cleanUpCertificate()
    cls.stopServerProcess()
    super(HttpFrontendTestCase, cls)._cleanup(snapshot_name)

  @classmethod
  def _workingDirectorySetUp(cls):
      # do working directory
      cls.working_directory = os.path.join(os.path.realpath(
          os.environ.get(
              'SLAPOS_TEST_WORKING_DIR',
              os.path.join(os.getcwd(), '.slapos'))),
          'rapid-cdn-test')
      if not os.path.isdir(cls.working_directory):
        os.mkdir(cls.working_directory)

  @classmethod
  def setUpClass(cls):
    try:
      cls.createWildcardExampleComCertificate()
      cls.prepareCertificate()
      # find ports once to be able startServerProcess many times
      cls._server_http_port = findFreeTCPPort(cls._ipv4_address)
      cls._server_https_port = findFreeTCPPort(cls._ipv4_address)
      cls._server_https_auth_port = findFreeTCPPort(cls._ipv4_address)
      cls._server_netloc_a_http_port = findFreeTCPPort(cls._ipv4_address)
      cls._server_netloc_b_http_port = findFreeTCPPort(cls._ipv4_address)
      cls.startServerProcess()
    except BaseException:
      cls.logger.exception("Error during setUpClass")
      cls._cleanup("{}.{}.setUpClass".format(cls.__module__, cls.__name__))
      cls.setUp = lambda self: self.fail('Setup Class failed.')
      raise

    super(HttpFrontendTestCase, cls).setUpClass()

    try:
      cls._workingDirectorySetUp()
      # expose instance directory
      cls.instance_path = cls.slap.instance_directory
      # expose software directory, extract from found computer partition
      cls.software_path = os.path.realpath(os.path.join(
          cls.computer_partition_root_path, 'software_release'))
      cls.setUpMaster()
      cls.waitForFrontend()
    except BaseException:
      cls.logger.exception("Error during setUpClass")
      # "{}.{}.setUpClass".format(cls.__module__, cls.__name__) is already used
      # by SlapOSInstanceTestCase.setUpClass so we use another name for
      # snapshot, to make sure we don't store another snapshot in same
      # directory.
      cls._cleanup("{}.HttpFrontendTestCase.{}.setUpClass".format(
        cls.__module__, cls.__name__))
      cls.setUp = lambda self: self.fail('Setup Class failed.')
      raise


class SlaveHttpFrontendTestCase(HttpFrontendTestCase):
  def _get_backend_haproxy_configuration(self):
    backend_configuration_file = glob.glob(os.path.join(
      self.instance_path, '*', 'etc', 'backend-haproxy.cfg'))[0]
    with open(backend_configuration_file) as fh:
      return fh.read()

  @classmethod
  def requestDefaultInstance(cls, state='started'):
    default_instance = super(
      SlaveHttpFrontendTestCase, cls).requestDefaultInstance(state=state)
    if state != 'destroyed':
      cls.requestSlaves()
    return default_instance

  @classmethod
  def requestSlaveInstance(cls, partition_reference, partition_parameter_kw):
    software_url = cls.getSoftwareURL()
    software_type = cls.getInstanceSoftwareType()
    cls.logger.debug(
      'requesting slave "%s" type: %r software:%s parameters:%s',
      partition_reference, software_type, software_url, partition_parameter_kw)
    return cls.slap.request(
      software_release=software_url,
      software_type=software_type,
      partition_reference=partition_reference,
      partition_parameter_kw=partition_parameter_kw,
      shared=True
    )

  @classmethod
  def requestSlaves(cls):
    for slave_reference, partition_parameter_kw in list(
      cls.getSlaveParameterDictDict().items()):
      software_url = cls.getSoftwareURL()
      software_type = cls.getInstanceSoftwareType()
      cls.logger.debug(
        'requesting slave "%s" type: %r software:%s parameters:%s',
        slave_reference, software_type, software_url, partition_parameter_kw)
      cls.requestSlaveInstance(
        partition_reference=slave_reference,
        partition_parameter_kw=partition_parameter_kw,
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
        if 'domain' in parameter_dict:
          try:
            fakeHTTPSResult(
              parameter_dict['domain'], '/')
          except requests.exceptions.InvalidURL:
            # ignore slaves to which connection is impossible by default
            continue
    cls.waitForMethod('waitForSlave', method)

  @classmethod
  def getSlaveConnectionParameterDictList(cls):
    parameter_dict_list = []

    for slave_reference, partition_parameter_kw in list(
      cls.getSlaveParameterDictDict().items()):
      parameter_dict_list.append(cls.requestSlaveInstance(
        partition_reference=slave_reference,
        partition_parameter_kw=partition_parameter_kw,
      ).getConnectionParameterDict())
    return parameter_dict_list

  @classmethod
  def getSlaveConnectionParameterDictDict(cls):
    parameter_dict_dict = {}

    for slave_reference, partition_parameter_kw in list(
      cls.getSlaveParameterDictDict().items()):
      parameter_dict_dict[slave_reference] = cls.requestSlaveInstance(
        partition_reference=slave_reference,
        partition_parameter_kw=partition_parameter_kw,
      ).getConnectionParameterDict()
    return parameter_dict_dict

  @classmethod
  def setUpSlaves(cls):
    cls.updateSlaveConnectionParameterDictDict()

  @classmethod
  def updateSlaveConnectionParameterDictDict(cls):
    cls.slave_connection_parameter_dict_dict = {}
    # run partition for slaves to be setup
    for slave_reference, partition_parameter_kw in list(
      cls.getSlaveParameterDictDict().items()):
      slave_instance = cls.requestSlaveInstance(
        partition_reference=slave_reference,
        partition_parameter_kw=partition_parameter_kw,
      )
      cls.slave_connection_parameter_dict_dict[slave_reference] = \
          slave_instance.getConnectionParameterDict()

  def parseSlaveParameterDict(self, key):
    return self.parseParameterDict(
      self.slave_connection_parameter_dict_dict[
        key
      ]
    )

  def assertSlaveBase(
    self, reference, expected_parameter_dict=None, hostname=None):
    if expected_parameter_dict is None:
      expected_parameter_dict = {}
    parameter_dict = self.parseSlaveParameterDict(reference)
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.current_generate_auth, self.current_upload_url = \
        self.assertKedifaKeysWithPop(parameter_dict, '')
    self.assertNodeInformationWithPop(parameter_dict)
    if hostname is None:
      hostname = reference.replace('_', '').replace('-', '').lower()
    expected_parameter_dict.update(**{
      'domain': '%s.example.com' % (hostname,),
      'replication_number': '1',
      'url': 'http://%s.example.com' % (hostname, ),
      'site_url': 'http://%s.example.com' % (hostname, ),
      'secure_access': 'https://%s.example.com' % (hostname, ),
      'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
    })
    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

    return parameter_dict

  def assertLastLogLineRegexp(self, log_name, log_regexp):
    log_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'var', 'log', 'httpd', log_name
      ))[0]

    # sometimes logs appear with a bit of delay, so give it a chance
    for _ in range(5):
      with open(log_file, 'r') as fh:
        line = fh.readlines()[-1]
      if re.match(log_regexp, line):
        break
      time.sleep(0.5)
    self.assertRegex(
      line,
      log_regexp)


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
    self.assertBackendHaproxyStatisticUrl(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertPublishFailsafeErrorPromiseEmptyWithPop(parameter_dict)
    self.assertRejectedSlavePromiseEmptyWithPop(parameter_dict)
    self.assertNodeInformationWithPop(parameter_dict)

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
    self.assertBackendHaproxyStatisticUrl(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertPublishFailsafeErrorPromiseEmptyWithPop(parameter_dict)
    self.assertRejectedSlavePromiseEmptyWithPop(parameter_dict)
    self.assertNodeInformationWithPop(parameter_dict)
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


class TestMasterAIKCDisabledAIBCCDisabledRequest(
  HttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
      'automatic-internal-kedifa-caucase-csr': 'false',
      'automatic-internal-backend-client-caucase-csr': 'false',
    }

  @classmethod
  def _setUpClass(cls):
    instance_max_retry = cls.instance_max_retry
    try:
      cls.instance_max_retry = 3
      super(TestMasterAIKCDisabledAIBCCDisabledRequest, cls)._setUpClass()
    except SlapOSNodeInstanceError:  # Note: SLAPOS_TEST_DEBUG=1 will interrupt
      pass
    else:
      raise ValueError('_setUpClass unexpected success')
    # Cluster requested without automatic certificate handling will never
    # stabilize, as nodes can't join to the cluster, so the user is required
    # to first manually create key and certificate for himself, then manually
    # create certificates for services
    cls._workingDirectorySetUp()
    _, kedifa_key_pem, _, kedifa_csr_pem = createCSR('Kedifa User')
    _, backend_client_key_pem, _, backend_client_csr_pem = createCSR(
      'Backend Client User')
    parameter_dict = cls.requestDefaultInstance(
      ).getConnectionParameterDict()
    cls._fetchKedifaCaucaseCaCertificateFile(parameter_dict)
    cls._fetchBackendClientCaCertificateFile(parameter_dict)
    with open(cls.kedifa_caucase_ca_certificate_file) as fh:
      kedifa_ca_pem = fh.read()
    with open(cls.backend_client_caucase_ca_certificate_file) as fh:
      backend_client_ca_pem = fh.read()

    kedifa_caucase_url = parameter_dict['kedifa-caucase-url']
    backend_client_caucase_url = parameter_dict['backend-client-caucase-url']

    # Simulate human: create user keys
    def getCauCertificate(ca_url, ca_pem, csr_pem):
      cau_client = caucase.client.CaucaseClient(
        ca_url=ca_url + '/cau',
        ca_crt_pem_list=caucase.utils.getCertList(ca_pem),
      )
      csr_id = cau_client.createCertificateSigningRequest(csr_pem)
      return cau_client.getCertificate(csr_id)

    kedifa_crt_pem = getCauCertificate(
      kedifa_caucase_url, kedifa_ca_pem, kedifa_csr_pem)
    backend_client_crt_pem = getCauCertificate(
      backend_client_caucase_url, backend_client_ca_pem,
      backend_client_csr_pem)
    kedifa_key_file = os.path.join(cls.working_directory, 'kedifa-key.pem')
    with open(kedifa_key_file, 'wb') as fh:
      fh.write(kedifa_crt_pem + kedifa_key_pem)
    backend_client_key_file = os.path.join(
      cls.working_directory, 'backend-client-key.pem')
    with open(backend_client_key_file, 'wb') as fh:
      fh.write(backend_client_crt_pem + backend_client_key_pem)

    # Simulate human: create service keys
    def signAllCasCsr(ca_url, ca_pem, user_key, pending_csr_amount):
      client = caucase.client.CaucaseClient(
        ca_url=ca_url + '/cas',
        ca_crt_pem_list=caucase.utils.getCertList(ca_pem), user_key=user_key)
      pending_csr_list = client.getPendingCertificateRequestList()
      assert len(pending_csr_list) == pending_csr_amount
      for csr_entry in pending_csr_list:
        client.createCertificate(int(csr_entry['id']))

    signAllCasCsr(kedifa_caucase_url, kedifa_ca_pem, kedifa_key_file, 2)
    signAllCasCsr(
      backend_client_caucase_url, backend_client_ca_pem,
      backend_client_key_file, 1)
    # Continue instance processing, copy&paste from
    # slapos.testing.testcase.SlapOSInstanceTestCase._setUpClass
    # as we hack a lot
    cls.instance_max_retry = instance_max_retry
    cls.waitForInstance()
    cls.computer_partition = cls.requestDefaultInstance()
    cls.computer_partition_root_path = os.path.join(
      cls.slap._instance_root, cls.computer_partition.getId())

  def test(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertBackendHaproxyStatisticUrl(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertPublishFailsafeErrorPromiseEmptyWithPop(parameter_dict)
    self.assertRejectedSlavePromiseEmptyWithPop(parameter_dict)
    self.assertKeyWithPop('kedifa-csr-certificate', parameter_dict)
    self.assertKeyWithPop('kedifa-csr-url', parameter_dict)
    self.assertKeyWithPop('frontend-node-1-kedifa-csr-url', parameter_dict)
    self.assertKeyWithPop(
      'frontend-node-1-backend-client-csr-url', parameter_dict)
    self.assertKeyWithPop(
      'frontend-node-1-csr-certificate', parameter_dict)
    self.assertNodeInformationWithPop(parameter_dict)
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


class TestSlave(SlaveHttpFrontendTestCase, TestDataMixin, AtsMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
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
      'bad-backend': {
        'url': 'http://bad.backend/',
      },
      'Url': {
        # make URL "incorrect", with whitespace, nevertheless it shall be
        # correctly handled
        'url': ' ' + cls.backend_url + '/?a=b&c=' + ' ',
        # authenticating to http backend shall be no-op
        'authenticate-to-backend': True,
      },
      'url-netloc-list': {
        'url': cls.backend_url,
        'url-netloc-list': '%(ip)s:%(port_a)s %(ip)s:%(port_b)s' % {
          'ip': cls._ipv4_address,
          'port_a': cls._server_netloc_a_http_port,
          'port_b': cls._server_netloc_b_http_port},
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
        'strict-transport-security': '200',
        'strict-transport-security-sub-domains': True,
        'strict-transport-security-preload': True,
      },
      'https-url-netloc-list': {
        'url': cls.backend_url + 'http',
        'https-url': cls.backend_url + 'https',
        'https-url-netloc-list': '%(ip)s:%(port_a)s %(ip)s:%(port_b)s' % {
          'ip': cls._ipv4_address,
          'port_a': cls._server_netloc_a_http_port,
          'port_b': cls._server_netloc_b_http_port},
      },
      'server-alias': {
        'url': cls.backend_url,
        'server-alias': 'alias1.example.com alias2.example.com',
        'strict-transport-security': '200',
      },
      'server-alias-empty': {
        'url': cls.backend_url,
        'server-alias': '',
        'strict-transport-security': '200',
        'strict-transport-security-sub-domains': True,
      },
      'server-alias-wildcard': {
        'url': cls.backend_url,
        'server-alias': '*.alias1.example.com',
        'strict-transport-security': '200',
        'strict-transport-security-preload': True,
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
      'type-redirect': {
        'url': cls.backend_url,
        'https-url': cls.backend_https_url,
        'type': 'redirect',
        'https-only': False,
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
      'enable_cache-https-only-false': {
        'url': cls.backend_url,
        'https-only': False,
        'enable_cache': True,
      },
      'enable-http2-false': {
        'url': cls.backend_url,
        'enable-http2': False,
      },
      'enable-http2-default': {
        'url': cls.backend_url,
      },
      'enable-http3-true': {
        'url': cls.backend_url,
        'enable-http3': True,
      },
      'enable-http3-default': {
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
        # Note: Do not reorder the entires below, see comments in
        #       test_disabled_cookie_list
        'disabled-cookie-list': 'Coconut Chocolate Vanilia',
      },
      'disabled-cookie-list-simple': {
        'url': cls.backend_url,
        'disabled-cookie-list': 'Chocolate',
      },
      'ciphers': {
        'ciphers': 'RSA-3DES-EDE-CBC-SHA RSA-AES128-CBC-SHA',
      },
      'ciphers-translation-all': {
        # all ciphers from instance-master.cfg.in found in GOOD_CIPHER_LIST
        # and keys of CIPHER_TRANSLATION_DICT in order to check translations
        'ciphers':
        'ECDHE-ECDSA-AES256-GCM-SHA384 ECDHE-RSA-AES256-GCM-SHA384 '
        'ECDHE-ECDSA-AES128-GCM-SHA256 ECDHE-RSA-AES128-GCM-SHA256 '
        'ECDHE-ECDSA-WITH-CHACHA20-POLY1305 ECDHE-RSA-WITH-CHACHA20-POLY1305 '
        'ECDHE-RSA-AES256-CBC-SHA ECDHE-RSA-AES128-CBC-SHA '
        'ECDHE-ECDSA-AES256-CBC-SHA ECDHE-ECDSA-AES128-CBC-SHA '
        'RSA-AES256-CBC-SHA RSA-AES128-CBC-SHA ECDHE-RSA-3DES-EDE-CBC-SHA '
        'RSA-3DES-EDE-CBC-SHA',
      },
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
        'old'.encode(),
        fh.read()
      )
    with lzma.open(
      os.path.join(ats_logrotate_dir, older_file_name + '.xz')) as fh:
      self.assertEqual(
        'older'.encode(),
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
    self.assertBackendHaproxyStatisticUrl(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertPublishFailsafeErrorPromiseEmptyWithPop(parameter_dict)
    self.assertRejectedSlavePromiseEmptyWithPop(parameter_dict)
    self.assertNodeInformationWithPop(parameter_dict)

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
          "slave url ' %(backend)s/?a=b&c= ' has been converted to "
          "'%(backend)s/?a=b&c='" % {'backend': self.backend_url}],
        '_ciphers': [
          "Cipher 'RSA-3DES-EDE-CBC-SHA' translated to 'DES-CBC3-SHA'",
          "Cipher 'RSA-AES128-CBC-SHA' translated to 'AES128-SHA'"],
        '_ciphers-translation-all': [
          "Cipher 'ECDHE-ECDSA-AES128-CBC-SHA' translated to "
          "'ECDHE-ECDSA-AES128-SHA'",
          "Cipher 'ECDHE-ECDSA-AES256-CBC-SHA' translated to "
          "'ECDHE-ECDSA-AES256-SHA'",
          "Cipher 'ECDHE-ECDSA-WITH-CHACHA20-POLY1305' translated to "
          "'ECDHE-ECDSA-CHACHA20-POLY1305'",
          "Cipher 'ECDHE-RSA-3DES-EDE-CBC-SHA' translated to "
          "'ECDHE-RSA-DES-CBC3-SHA'",
          "Cipher 'ECDHE-RSA-AES128-CBC-SHA' translated to "
          "'ECDHE-RSA-AES128-SHA'",
          "Cipher 'ECDHE-RSA-AES256-CBC-SHA' translated to "
          "'ECDHE-RSA-AES256-SHA'",
          "Cipher 'ECDHE-RSA-WITH-CHACHA20-POLY1305' translated to "
          "'ECDHE-RSA-CHACHA20-POLY1305'",
          "Cipher 'RSA-3DES-EDE-CBC-SHA' translated to 'DES-CBC3-SHA'",
          "Cipher 'RSA-AES128-CBC-SHA' translated to 'AES128-SHA'",
          "Cipher 'RSA-AES256-CBC-SHA' translated to 'AES256-SHA'"]
      }

    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

    partition_path = self.getMasterPartitionPath()

    # check that monitor cors domains are correctly setup by file presence, as
    # we trust monitor stack being tested in proper place and it is too hard
    # to have working monitor with local proxy
    with open(os.path.join(
      partition_path, 'etc', 'httpd-cors.cfg')) as fh:
      self.assertTestData(fh.read().strip())

  def test_node_information_json(self):
    node_information_file_path = glob.glob(os.path.join(
      self.instance_path, '*', '.frontend-node-information.json'))[0]
    with open(node_information_file_path, 'r') as fh:
      current_node_information = json.load(fh)
    modified_node_information = current_node_information.copy()
    modified_node_information['version-hash-history'] = {'testhash': 'testurl'}

    def writeNodeInformation(node_information, path):
      with open(path, 'w') as fh:
        json.dump(node_information, fh, sort_keys=True)
      # full processing is needed as this is just simulation which does
      # not bang the instance tree
      slap_force_slapos_node_instance_all = \
          self.slap._force_slapos_node_instance_all
      self.slap._force_slapos_node_instance_all = True
      try:
        self.waitForInstance()
        self.waitForInstance()
        self.waitForInstance()
      finally:
        self.slap._force_slapos_node_instance_all = \
          slap_force_slapos_node_instance_all

    self.addCleanup(
      writeNodeInformation, current_node_information,
      node_information_file_path)

    # simulate that upgrade happened
    writeNodeInformation(
      modified_node_information,
      node_information_file_path)
    parameter_dict = self.parseConnectionParameterDict()
    expected_node_information = {
      'node-id': current_node_information['node-id'],
      'version-hash-history': current_node_information['version-hash-history']
    }
    expected_node_information['version-hash-history']['testhash'] = 'testurl'
    self.assertEqual(
      json.loads(parameter_dict['frontend-node-1-node-information-json']),
      expected_node_information
    )

  def test_monitor_conf(self):
    monitor_conf_list = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'monitor.conf'
      ))
    self.assertEqual(3, len(monitor_conf_list))
    expected = [(False, q) for q in monitor_conf_list]
    got = []
    for q in monitor_conf_list:
      with open(q) as fh:
        got.append(('!py!' in fh.read(), q))
    # check that no monitor.conf in generated configuration has magic !py!
    self.assertEqual(
      expected,
      got
    )

  def test_empty(self):
    parameter_dict = self.assertSlaveBase('empty')
    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')
    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(http.client.SERVICE_UNAVAILABLE, result.status_code)

    result_http = fakeHTTPResult(
      parameter_dict['domain'], 'test-path')
    self.assertEqual(
      http.client.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://empty.example.com:%s/test-path' % (HTTP_PORT,),
      result_http.headers['Location']
    )

    # check that 404 is as configured
    result_missing = fakeHTTPSResult(
      'forsuredoesnotexists.example.com', '')
    self.assertEqual(http.client.NOT_FOUND, result_missing.status_code)
    self.assertEqual(
      """<html>
<head>
  <title>Instance not found</title>
</head>
<body>
<h1>The instance has not been found</h1>
<p>The reasons of this could be:</p>
<ul>
<li>the instance does not exists or the URL is incorrect
<ul>
<li>in this case please check the URL
</ul>
<li>the instance has been stopped
<ul>
<li>in this case please check in the SlapOS Master if the instance is """
      """started or wait a bit for it to start
</ul>
</ul>
</body>
</html>
""",
      result_missing.text
    )

  def test_server_polluted_keys_removed(self):
    buildout_file = os.path.join(
      self.getMasterPartitionPath(), 'instance-master.cfg')
    with open(buildout_file) as fh:
      for line in [
        q for q in fh.readlines()
        if q.startswith('config-slave-list') or q.startswith(
            'config-extra_slave_instance_list')]:
        self.assertFalse('slave_title' in line)
        self.assertFalse('slap_software_type' in line)
        self.assertFalse('connection-parameter-hash' in line)
        self.assertFalse('timestamp' in line)

  def assertRequestHeaders(
    self, header_dict, domain=None, source_ip=SOURCE_IP,
    port=HTTPS_PORT, proto='https', cached=False):
    if domain is not None:
      self.assertEqual(
        header_dict['host'],
        '%s:%s' % (domain, port))
    self.assertEqual(
      header_dict['x-forwarded-for'],
      source_ip
    )
    self.assertEqual(
      header_dict['x-forwarded-port'],
      port
    )
    self.assertEqual(
      header_dict['x-forwarded-proto'],
      proto
    )
    via_id = '%s-%s' % (
      self.node_information_dict['node-id'],
      list(self.node_information_dict['version-hash-history'].keys())[0])
    if cached:
      self.assertEqual(
        [
          'http/1.1 clientvia',
          'HTTP/1.1 rapid-cdn-frontend-%(via_id)s, '
          'http/1.1 rapid-cdn-cache-%(via_id)s' % dict(via_id=via_id),
          'HTTP/1.1 rapid-cdn-backend-%(via_id)s' % dict(via_id=via_id)
        ],
        header_dict['via']
      )
    else:
      self.assertEqual(
        [
          'http/1.1 clientvia',
          'HTTP/1.1 rapid-cdn-frontend-%(via_id)s' % dict(via_id=via_id),
          'HTTP/1.1 rapid-cdn-backend-%(via_id)s' % dict(via_id=via_id)
        ],
        header_dict['via']
      )

  def test_url(self):
    parameter_dict = self.assertSlaveBase(
      'Url',
      {
        'warning-list': [
          "slave url ' %s/?a=b&c= ' has been converted to '%s/?a=b&c='" % (
            self.backend_url, self.backend_url)],
      }
    )
    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={
        'Timeout': '10',  # more than default backend-connect-timeout == 5
        'Accept-Encoding': 'gzip',
        'User-Agent': 'TEST USER AGENT',
      }
    )

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    headers = self.assertResponseHeaders(result)
    self.assertNotIn('Strict-Transport-Security', headers)
    self.assertEqualResultJson(result, 'Path', '?a=b&c=/test-path/deeper')

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))

    self.assertEqual(j['Incoming Headers']['timeout'], '10')
    self.assertFalse('Content-Encoding' in headers)
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      headers['Set-Cookie']
    )

    self.assertLastLogLineRegexp(
      '_Url_access_log',
      r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3} - - '
      r'\[\d{2}\/.{3}\/\d{4}\:\d{2}\:\d{2}\:\d{2} \+\d{4}\] '
      r'"GET \/test-path\/deep\/..\/.\/deeper HTTP\/1.1" \d{3} '
      r'\d+ "-" "TEST USER AGENT" \d+'
    )

    self.assertLastLogLineRegexp(
      '_Url_backend_log',
      r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+ '
      r'\[\d{2}\/.{3}\/\d{4}\:\d{2}\:\d{2}\:\d{2}.\d{3}\] '
      r'http-backend _Url-http\/_Url-backend-http '
      r'\d+/\d+\/\d+\/\d+\/\d+ '
      r'200 \d+ - - ---- '
      r'\d+\/\d+\/\d+\/\d+\/\d+ \d+\/\d+ '
      r'"GET /test-path/deeper HTTP/1.1"'
    )

    result_http = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      http.client.FOUND,
      result_http.status_code
    )

    headers = self.assertResponseHeaders(
      result_http, via=False, backend_reached=False)

    self.assertEqual(
      'https://url.example.com:%s/test-path/deeper' % (HTTP_PORT,),
      headers['Location']
    )

    # check that timeouts are correctly set in the haproxy configuration
    backend_configuration_file = glob.glob(os.path.join(
      self.instance_path, '*', 'etc', 'backend-haproxy.cfg'))[0]
    with open(backend_configuration_file) as fh:
      content = fh.read()
    self.assertIn("""backend _Url-http
  timeout server 12s
  timeout connect 5s
  retries 3""", content)
    self.assertIn("""  timeout queue 60s
  timeout server 12s
  timeout client 12s
  timeout connect 5s
  retries 3""", content)
    # check that no needless entries are generated
    self.assertIn("backend _Url-http\n", content)
    self.assertNotIn("backend _Url-https\n", content)

    # check out access via IPv6
    out_ipv6, err_ipv6 = self._curl(
      parameter_dict['domain'], self._ipv6_address, HTTPS_PORT)

    try:
      j = json.loads(out_ipv6.decode())
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (out_ipv6.decode(),))
    self.assertEqual(
       self._ipv6_address,
       j['Incoming Headers']['x-forwarded-for']
    )

  def test_url_netloc_list(self):
    parameter_dict = self.assertSlaveBase('url-netloc-list')
    result = fakeHTTPSResult(parameter_dict['domain'], 'path')
    # assure that the request went to backend specified in the netloc
    self.assertEqual(
      result.headers['X-Backend-Identification'],
      'netloc'
    )

  def test_auth_to_backend(self):
    parameter_dict = self.assertSlaveBase('auth-to-backend')

    self.startAuthenticatedServerProcess()
    try:
      # assert that you can't fetch nothing without key
      try:
        requests.get(self.backend_https_auth_url, verify=False)
      except Exception:
        pass
      else:
        self.fail(
          'Access to %r shall be not possible without certificate' % (
            self.backend_https_auth_url,))
      # check that you can access this backend via frontend
      # (so it means that auth to backend worked)
      result = fakeHTTPSResult(
        parameter_dict['domain'],
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
      self.assertRequestHeaders(
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
      self.stopAuthenticatedServerProcess()

  def test_auth_to_backend_not_configured(self):
    parameter_dict = self.assertSlaveBase('auth-to-backend-not-configured')
    self.startAuthenticatedServerProcess()
    try:
      # assert that you can't fetch nothing without key
      try:
        requests.get(self.backend_https_auth_url, verify=False)
      except Exception:
        pass
      else:
        self.fail(
          'Access to %r shall be not possible without certificate' % (
            self.backend_https_auth_url,))
      # check that you can access this backend via frontend
      # (so it means that auth to backend worked)
      result = fakeHTTPSResult(
        parameter_dict['domain'],
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
        http.client.BAD_GATEWAY
      )
    finally:
      self.stopAuthenticatedServerProcess()

  def test_auth_to_backend_backend_ignore(self):
    parameter_dict = self.assertSlaveBase('auth-to-backend-backend-ignore')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
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
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result.headers['Set-Cookie']
    )

    result_http = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      http.client.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://authtobackendbackendignore.example.com:%s/test-path/deeper' % (
        HTTP_PORT,),
      result_http.headers['Location']
    )

  def test_compressed_result(self):
    parameter_dict = self.assertSlaveBase(
      'Url',
      {
        'warning-list': [
          "slave url ' %s/?a=b&c= ' has been converted to '%s/?a=b&c='" % (
            self.backend_url, self.backend_url)],
      }
    )

    result_compressed = fakeHTTPSResult(
      parameter_dict['domain'],
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
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={
        'Accept-Encoding': 'gzip',
      }
    )
    self.assertFalse('Content-Encoding' in result_not_compressed.headers)

  def test_no_content_type_alter(self):
    parameter_dict = self.assertSlaveBase(
      'Url',
      {
        'warning-list': [
          "slave url ' %s/?a=b&c= ' has been converted to '%s/?a=b&c='" % (
            self.backend_url, self.backend_url)],
      }
    )
    result = fakeHTTPSResult(
      parameter_dict['domain'],
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
</note>""").decode(),
        'X-Drop-Header': 'Content-Type'
      }
    )

    self.assertNotIn('Content-Type', result.headers)

  def test_type_zope_path(self):
    parameter_dict = self.assertSlaveBase('type-zope-path')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/'
      'https/typezopepath.example.com:443/path/to/some/resource'
      '/VirtualHostRoot/'
      'test-path/deeper'
    )

  def test_type_zope_default_path(self):
    parameter_dict = self.assertSlaveBase('type-zope-default-path')

    result = fakeHTTPSResult(
      parameter_dict['domain'], '')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      http.client.MOVED_PERMANENTLY,
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
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      'max-age=200', result.headers['Strict-Transport-Security'])
    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPSResult(
      'alias1.example.com',
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      'max-age=200', result.headers['Strict-Transport-Security'])
    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPSResult(
      'alias2.example.com',
      'test-path/deep/.././deeper')

    self.assertEqual(
      'max-age=200', result.headers['Strict-Transport-Security'])
    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

  def test_server_alias_empty(self):
    parameter_dict = self.assertSlaveBase('server-alias-empty')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
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
      'max-age=200; includeSubDomains',
      result.headers['Strict-Transport-Security'])
    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))

    self.assertEqual(j['Incoming Headers']['timeout'], '10')
    self.assertFalse('Content-Encoding' in result.headers)
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result.headers['Set-Cookie']
    )

  def test_server_alias_wildcard(self):
    parameter_dict = self.assertSlaveBase('server-alias-wildcard')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      'max-age=200; preload',
      result.headers['Strict-Transport-Security'])
    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = fakeHTTPSResult(
      'wild.alias1.example.com', 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      'max-age=200; preload',
      result.headers['Strict-Transport-Security'])
    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_server_alias_duplicated(self):
    parameter_dict = self.assertSlaveBase('server-alias-duplicated')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = fakeHTTPSResult(
      'alias3.example.com', 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_server_alias_custom_domain_duplicated(self):
    parameter_dict = self.assertSlaveBase(
      'server-alias_custom_domain-duplicated', hostname='alias4')
    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_ssl_ca_crt(self):
    parameter_dict = self.assertSlaveBase(
      'custom_domain_ssl_crt_ssl_key_ssl_ca_crt')

    # as now the place to put the key is known put the key there
    auth = requests.get(
      self.current_generate_auth,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, auth.status_code)

    data = self.customdomain_ca_certificate_pem + \
        self.customdomain_ca_key_pem + \
        self.ca.certificate_pem

    upload = requests.put(
      self.current_upload_url + auth.text,
      data=data,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, upload.status_code)
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.customdomain_ca_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    certificate_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'srv', 'autocert',
      '_custom_domain_ssl_crt_ssl_key_ssl_ca_crt.pem'))
    self.assertEqual(1, len(certificate_file_list))
    certificate_file = certificate_file_list[0]
    with open(certificate_file, 'rb') as out:
      self.assertEqual(data, out.read())

  def test_ssl_ca_crt_only(self):
    self.assertSlaveBase('ssl_ca_crt_only')
    # as now the place to put the key is known put the key there
    auth = requests.get(
      self.current_generate_auth,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, auth.status_code)

    data = self.ca.certificate_pem

    upload = requests.put(
      self.current_upload_url + auth.text,
      data=data,
      verify=self.kedifa_caucase_ca_certificate_file)

    self.assertEqual(http.client.UNPROCESSABLE_ENTITY, upload.status_code)
    self.assertEqual('Key incorrect', upload.text)

  def test_ssl_ca_crt_garbage(self):
    parameter_dict = self.assertSlaveBase('ssl_ca_crt_garbage')

    # as now the place to put the key is known put the key there
    auth = requests.get(
      self.current_generate_auth,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, auth.status_code)

    _, ca_key_pem, csr, _ = createCSR(
      parameter_dict['domain'])
    _, ca_certificate_pem = self.ca.signCSR(csr)

    data = ca_certificate_pem + ca_key_pem + 'some garbage'.encode()
    upload = requests.put(
      self.current_upload_url + auth.text,
      data=data,
      verify=self.kedifa_caucase_ca_certificate_file)

    self.assertEqual(http.client.CREATED, upload.status_code)
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
        parameter_dict['domain'], 'test-path')

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
    with open(certificate_file, 'rb') as out:
      self.assertEqual(data, out.read())

  def test_ssl_ca_crt_does_not_match(self):
    parameter_dict = self.assertSlaveBase('ssl_ca_crt_does_not_match')
    # as now the place to put the key is known put the key there
    auth = requests.get(
      self.current_generate_auth,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, auth.status_code)

    data = self.certificate_pem + self.key_pem + self.ca.certificate_pem

    upload = requests.put(
      self.current_upload_url + auth.text,
      data=data,
      verify=self.kedifa_caucase_ca_certificate_file)

    self.assertEqual(http.client.CREATED, upload.status_code)
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    certificate_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'srv', 'autocert',
      '_ssl_ca_crt_does_not_match.pem'))
    self.assertEqual(1, len(certificate_file_list))
    certificate_file = certificate_file_list[0]
    with open(certificate_file, 'rb') as out:
      self.assertEqual(data, out.read())

  def test_https_only(self):
    parameter_dict = self.assertSlaveBase('https-only')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result_http = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqualResultJson(result_http, 'Path', '/test-path/deeper')

  def test_custom_domain(self):
    parameter_dict = self.assertSlaveBase(
      'custom_domain', hostname='mycustomdomain')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_custom_domain_server_alias(self):
    parameter_dict = self.assertSlaveBase(
      'custom_domain_server_alias', hostname='mycustomdomainserveralias')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result = fakeHTTPSResult(
      'mycustomdomainserveralias1.example.com',
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

  def test_custom_domain_wildcard(self):
    self.assertSlaveBase(
      'custom_domain_wildcard', hostname='*.customdomain')

    result = fakeHTTPSResult(
      'wild.customdomain.example.com',
      'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_custom_domain_ssl_crt_ssl_key(self):
    parameter_dict = self.assertSlaveBase('custom_domain_ssl_crt_ssl_key')

    # as now the place to put the key is known put the key there
    auth = requests.get(
      self.current_generate_auth,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, auth.status_code)
    data = self.customdomain_certificate_pem + \
        self.customdomain_key_pem
    upload = requests.put(
      self.current_upload_url + auth.text,
      data=data,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, upload.status_code)
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.customdomain_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_type_zope(self):
    parameter_dict = self.assertSlaveBase('type-zope')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https/typezope.example.com:443'
      '/VirtualHostRoot/test-path/deeper'
    )

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      http.client.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://typezope.example.com:%s/test-path/deeper' % (
        HTTP_PORT,),
      result.headers['Location']
    )

  def test_type_zope_prefer_gzip_encoding_to_backend_https_only(self):
    parameter_dict = self.assertSlaveBase(
      'type-zope-prefer-gzip-encoding-to-backend-https-only')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https/'
      'typezopeprefergzipencodingtobackendhttpsonly.example.com:443'
      '/VirtualHostRoot/test-path/deeper'
    )

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/http/'
      'typezopeprefergzipencodingtobackendhttpsonly.example.com:80'
      '/VirtualHostRoot/test-path/deeper'
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https/'
      'typezopeprefergzipencodingtobackendhttpsonly.example.com:443'
      '/VirtualHostRoot/test-path/deeper'
    )
    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/http/'
      'typezopeprefergzipencodingtobackendhttpsonly.example.com:80'
      '/VirtualHostRoot/test-path/deeper'
    )
    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

  def test_type_zope_prefer_gzip_encoding_to_backend(self):
    parameter_dict = self.assertSlaveBase(
      'type-zope-prefer-gzip-encoding-to-backend')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https/'
      'typezopeprefergzipencodingtobackend.example.com:443'
      '/VirtualHostRoot/test-path/deeper'
    )

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      http.client.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://%s:%s/test-path/deeper' % (
        parameter_dict['domain'], HTTP_PORT),
      result.headers['Location']
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https/'
      'typezopeprefergzipencodingtobackend.example.com:443'
      '/VirtualHostRoot/test-path/deeper'
    )
    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      http.client.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://%s:%s/test-path/deeper' % (
        parameter_dict['domain'], HTTP_PORT),
      result.headers['Location']
    )

  def test_type_zope_virtualhostroot_http_port(self):
    parameter_dict = self.assertSlaveBase(
      'type-zope-virtualhostroot-http-port')

    result = fakeHTTPResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/http/typezopevirtualhostroothttpport'
      '.example.com:12345/VirtualHostRoot/test-path'
    )

  def test_type_zope_virtualhostroot_https_port(self):
    parameter_dict = self.assertSlaveBase(
      'type-zope-virtualhostroot-https-port')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(
      result,
      'Path',
      '/VirtualHostBase/https/typezopevirtualhostroothttpsport'
      '.example.com:12345/VirtualHostRoot/test-path'
    )

  def test_type_notebook(self):
    # CDN's type:notebook in haproxy world is simply like type:websocket on
    # default parameters, so test has been adapted
    # generally, websocket is possible to be served on any path, which is
    # haproxy default
    parameter_dict = self.assertSlaveBase('type-notebook')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path',
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
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'Upgrade',
      j['Incoming Headers']['connection']
    )
    self.assertTrue('x-real-ip' in j['Incoming Headers'])
    self.assertHttp11(parameter_dict['domain'])

  def test_type_websocket(self):
    parameter_dict = self.assertSlaveBase(
      'type-websocket')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path',
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
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'Upgrade',
      j['Incoming Headers']['connection']
    )
    self.assertTrue('x-real-ip' in j['Incoming Headers'])
    self.assertHttp11(parameter_dict['domain'])

  def test_type_websocket_websocket_transparent_false(self):
    parameter_dict = self.assertSlaveBase(
      'type-websocket-websocket-transparent-false')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path',
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
    self.assertRequestHeaders(
      j['Incoming Headers'], port='17', proto='irc')
    self.assertEqual(
      'Upgrade',
      j['Incoming Headers']['connection']
    )
    self.assertFalse('x-real-ip' in j['Incoming Headers'])
    self.assertHttp11(parameter_dict['domain'])

  def test_type_websocket_websocket_path_list(self):
    parameter_dict = self.assertSlaveBase(
      'type-websocket-websocket-path-list')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path',
      headers={'Connection': 'Upgrade'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(
      result,
      'Path',
      '/test-path'
    )
    self.assertHttp1(parameter_dict['domain'])
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])
    self.assertFalse('x-real-ip' in j['Incoming Headers'])

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'ws/test-path',
      headers={'Connection': 'Upgrade'})

    self.assertEqualResultJson(
      result,
      'Path',
      '/ws/test-path'
    )
    self.assertHttp1(parameter_dict['domain'])
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'Upgrade',
      j['Incoming Headers']['connection']
    )
    self.assertTrue('x-real-ip' in j['Incoming Headers'])

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'with%20space/test-path', headers={'Connection': 'Upgrade'})

    self.assertEqualResultJson(
      result,
      'Path',
      '/with%20space/test-path'
    )
    self.assertHttp1(parameter_dict['domain'])
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])
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
      parameter_dict['domain'], 'test-path',
      headers={'Connection': 'Upgrade'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(
      result,
      'Path',
      '/test-path'
    )
    self.assertHttp1(parameter_dict['domain'])
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])
    self.assertFalse('x-real-ip' in j['Incoming Headers'])

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'ws/test-path',
      headers={'Connection': 'Upgrade'})

    self.assertEqualResultJson(
      result,
      'Path',
      '/ws/test-path'
    )
    self.assertHttp1(parameter_dict['domain'])
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertRequestHeaders(
      j['Incoming Headers'], port='17', proto='irc')
    self.assertEqual(
      'Upgrade',
      j['Incoming Headers']['connection']
    )
    self.assertFalse('x-real-ip' in j['Incoming Headers'])

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'with%20space/test-path', headers={'Connection': 'Upgrade'})

    self.assertEqualResultJson(
      result,
      'Path',
      '/with%20space/test-path'
    )
    self.assertHttp1(parameter_dict['domain'])
    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertRequestHeaders(
      j['Incoming Headers'], port='17', proto='irc')
    self.assertEqual(
      'Upgrade',
      j['Incoming Headers']['connection']
    )
    self.assertFalse('x-real-ip' in j['Incoming Headers'])

  def test_type_redirect(self):
    parameter_dict = self.assertSlaveBase('type-redirect')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      http.client.FOUND,
      result.status_code
    )

    self.assertEqual(
      '%stest-path/deeper' % (self.backend_https_url,),
      result.headers['Location']
    )

    self.assertResponseHeaders(
      result, via=False, backend_reached=False)

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      http.client.FOUND,
      result.status_code
    )

    self.assertEqual(
      '%stest-path/deeper' % (self.backend_url,),
      result.headers['Location']
    )

    self.assertResponseHeaders(
      result, via=False, backend_reached=False)

  def test_type_redirect_custom_domain(self):
    parameter_dict = self.assertSlaveBase(
      'type-redirect-custom_domain', hostname='customdomaintyperedirect')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      http.client.FOUND,
      result.status_code
    )

    self.assertEqual(
      '%stest-path/deeper' % (self.backend_url,),
      result.headers['Location']
    )

    self.assertResponseHeaders(
      result, via=False, backend_reached=False)

  def test_ssl_proxy_verify_ssl_proxy_ca_crt_unverified(self):
    parameter_dict = self.assertSlaveBase(
      'ssl-proxy-verify_ssl_proxy_ca_crt-unverified')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      http.client.SERVICE_UNAVAILABLE,
      result.status_code
    )

    result_http = fakeHTTPResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      http.client.FOUND,
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
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertRequestHeaders(j['Incoming Headers'], parameter_dict['domain'])

    self.assertFalse('Content-Encoding' in result.headers)

    self.assertEqual(
      'secured=value;secure, nonsecured=value',
      result.headers['Set-Cookie']
    )

    result_http = fakeHTTPResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      http.client.FOUND,
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
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      http.client.SERVICE_UNAVAILABLE,
      result.status_code
    )

  def test_ciphers(self):
    parameter_dict = self.assertSlaveBase(
     'ciphers', expected_parameter_dict={
       'warning-list': [
         "Cipher 'RSA-3DES-EDE-CBC-SHA' translated to 'DES-CBC3-SHA'",
         "Cipher 'RSA-AES128-CBC-SHA' translated to 'AES128-SHA'"]})

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(http.client.SERVICE_UNAVAILABLE, result.status_code)

    result_http = fakeHTTPResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      http.client.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://ciphers.example.com:%s/test-path' % (HTTP_PORT,),
      result_http.headers['Location']
    )

    configuration_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'frontend-haproxy-crt-list.txt'
      ))[0]
    with open(configuration_file) as fh:
      self.assertTrue(
        '/_ciphers.pem [ciphers DES-CBC3-SHA:AES128-SHA '
        in fh.read()
      )

  def test_ciphers_translation_all(self):
    parameter_dict = self.assertSlaveBase(
     'ciphers-translation-all', expected_parameter_dict={
       'warning-list': [
         "Cipher 'ECDHE-ECDSA-AES128-CBC-SHA' translated to "
         "'ECDHE-ECDSA-AES128-SHA'",
         "Cipher 'ECDHE-ECDSA-AES256-CBC-SHA' translated to "
         "'ECDHE-ECDSA-AES256-SHA'",
         "Cipher 'ECDHE-ECDSA-WITH-CHACHA20-POLY1305' translated to "
         "'ECDHE-ECDSA-CHACHA20-POLY1305'",
         "Cipher 'ECDHE-RSA-3DES-EDE-CBC-SHA' translated to "
         "'ECDHE-RSA-DES-CBC3-SHA'",
         "Cipher 'ECDHE-RSA-AES128-CBC-SHA' translated to "
         "'ECDHE-RSA-AES128-SHA'",
         "Cipher 'ECDHE-RSA-AES256-CBC-SHA' translated to "
         "'ECDHE-RSA-AES256-SHA'",
         "Cipher 'ECDHE-RSA-WITH-CHACHA20-POLY1305' translated to "
         "'ECDHE-RSA-CHACHA20-POLY1305'",
         "Cipher 'RSA-3DES-EDE-CBC-SHA' translated to 'DES-CBC3-SHA'",
         "Cipher 'RSA-AES128-CBC-SHA' translated to 'AES128-SHA'",
         "Cipher 'RSA-AES256-CBC-SHA' translated to 'AES256-SHA'"]})

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(http.client.SERVICE_UNAVAILABLE, result.status_code)

    result_http = fakeHTTPResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      http.client.FOUND,
      result_http.status_code
    )

    self.assertEqual(
      'https://cipherstranslationall.example.com:%s/test-path' % (HTTP_PORT,),
      result_http.headers['Location']
    )

    configuration_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'frontend-haproxy-crt-list.txt'
      ))[0]
    with open(configuration_file) as fh:
      self.assertTrue(
        '/_ciphers.translation.all.pem [ciphers '
        'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:'
        'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:'
        'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:'
        'ECDHE-RSA-AES256-SHA:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA:'
        'ECDHE-ECDSA-AES128-SHA:AES256-SHA:AES128-SHA:ECDHE-RSA-DES-CBC3-SHA:'
        'DES-CBC3-SHA'
        in fh.read()
      )

  def test_enable_cache_custom_domain(self):
    parameter_dict = self.assertSlaveBase(
      'enable_cache_custom_domain',
      hostname='customdomainenablecache')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    headers = self.assertResponseHeaders(result, True)
    self.assertKeyWithPop('Age', headers)

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
    self.assertRequestHeaders(
      backend_headers, parameter_dict['domain'], cached=True)

  def test_enable_cache_server_alias(self):
    parameter_dict = self.assertSlaveBase('enable_cache_server_alias')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    headers = self.assertResponseHeaders(result, cached=True)

    self.assertKeyWithPop('Age', headers)
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
    self.assertRequestHeaders(
      backend_headers, parameter_dict['domain'], cached=True)

    result = fakeHTTPResult(
      'enablecacheserveralias1.example.com',
      'test-path/deep/.././deeper', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600'})
    self.assertEqual(
      http.client.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://enablecacheserveralias1.example.com:%s/test-path/deeper' % (
        HTTP_PORT,),
      result.headers['Location']
    )

  def test_enable_cache_https_only_false(self):
    parameter_dict = self.assertSlaveBase('enable_cache-https-only-false')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    headers = self.assertResponseHeaders(result, cached=True)
    self.assertKeyWithPop('Age', headers)
    self.assertEqual(
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
        'Cache-Control': 'max-age=1, stale-while-revalidate=3600, '
                         'stale-if-error=3600'
      },
      headers
    )

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'HTTPS/test', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600'})

    self.assertEqual(http.client.OK, result.status_code)
    self.assertEqualResultJson(result, 'Path', '/HTTPS/test')

    self.assertResponseHeaders(result, cached=True)

  def test_enable_cache(self):
    parameter_dict = self.assertSlaveBase('enable_cache')

    source_ip = '127.0.0.1'
    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600',
      },
      source_ip=source_ip
    )

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    headers = self.assertResponseHeaders(result, cached=True)

    self.assertKeyWithPop('Age', headers)

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
    self.assertRequestHeaders(
      backend_headers, parameter_dict['domain'], cached=True)

    # BEGIN: Check that squid.log is correctly filled in
    ats_log_file_list = glob.glob(
      os.path.join(
        self.instance_path, '*', 'var', 'log', 'trafficserver', 'squid.log'
      ))
    self.assertEqual(1, len(ats_log_file_list))
    ats_log_file = ats_log_file_list[0]
    direct_pattern = re.compile(
      r'.*TCP_MISS/200 .*test-path/deeper.*enablecache.example.com'
      '.* - DIRECT*')
    # ATS needs some time to flush logs
    timeout = 10
    b = time.time()
    while True:
      direct_pattern_match = 0
      if (time.time() - b) > timeout:
        break
      with open(ats_log_file) as fh:
        for line in fh.readlines():
          if direct_pattern.match(line):
            direct_pattern_match += 1
      if direct_pattern_match > 0:
        break
      time.sleep(0.1)

    with open(ats_log_file) as fh:
      ats_log = fh.read()
    self.assertRegex(ats_log, direct_pattern)
    # END: Check that squid.log is correctly filled in

  def test_enable_cache_negative_revalidate(self):
    parameter_dict = self.assertSlaveBase('enable_cache')

    source_ip = '127.0.0.1'
    # have unique path for this test
    path = self.id()

    max_stale_age = 30
    max_age = int(max_stale_age / 2.)
    # body_200 is big enough to trigger
    # https://github.com/apache/trafficserver/issues/7880
    body_200 = 'Body 200' * 500
    body_502 = 'Body 502'
    body_502_new = 'Body 502 new'
    body_200_new = 'Body 200 new'

    self.addCleanup(self._unhack_ats)
    self._hack_ats(max_stale_age)

    def configureResult(status_code, body):
      backend_url = self.getSlaveParameterDictDict()['enable_cache']['url']
      result = requests.put(backend_url + path, headers={
          'X-Reply-Header-Cache-Control': 'max-age=%s, public' % (max_age,),
          'X-Reply-Status-Code': status_code,
          'X-Reply-Body': base64.b64encode(body.encode()),
          # drop Content-Length header to ensure
          # https://github.com/apache/trafficserver/issues/7880
          'X-Drop-Header': 'Content-Length',
        })
      self.assertEqual(result.status_code, http.client.CREATED)

    def checkResult(status_code, body):
      result = fakeHTTPSResult(
        parameter_dict['domain'], path,
        source_ip=source_ip
      )
      self.assertEqual(result.status_code, status_code)
      self.assertEqual(result.text, body)

    # backend returns something correctly
    configureResult('200', body_200)
    checkResult(http.client.OK, body_200)

    configureResult('502', body_502)
    time.sleep(1)
    # even if backend returns 502, ATS gives cached result
    checkResult(http.client.OK, body_200)

    # interesting moment, time is between max_age and max_stale_age, triggers
    # https://github.com/apache/trafficserver/issues/7880
    time.sleep(max_age + 1)
    checkResult(http.client.OK, body_200)

    # max_stale_age passed, time to return 502 from the backend
    time.sleep(max_stale_age + 2)
    checkResult(http.client.BAD_GATEWAY, body_502)

    configureResult('502', body_502_new)
    time.sleep(1)
    # even if there is new negative response on the backend, the old one is
    # served from the cache
    checkResult(http.client.BAD_GATEWAY, body_502)

    time.sleep(max_age + 2)
    # now as max-age of negative response passed, the new one is served
    checkResult(http.client.BAD_GATEWAY, body_502_new)

    configureResult('200', body_200_new)
    time.sleep(1)
    checkResult(http.client.BAD_GATEWAY, body_502_new)
    time.sleep(max_age + 2)
    # backend is back to normal, as soon as negative response max-age passed
    # the new response is served
    checkResult(http.client.OK, body_200_new)

  @skip('Feature postponed')
  def test_enable_cache_stale_if_error_respected(self):
    parameter_dict = self.assertSlaveBase('enable_cache')

    source_ip = '127.0.0.1'
    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600',
      },
      source_ip=source_ip
    )

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    headers = self.assertResponseHeaders(result)

    self.assertKeyWithPop('Age', headers)

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
    self.assertRequestHeaders(
      backend_headers, parameter_dict['domain'], cached=True)

    # check stale-if-error support is really respected if not present in the
    # request
    # wait a bit for max-age to expire
    time.sleep(2)
    # real check: cache access does not provide old data with stopped backend
    try:
      # stop the backend, to have error on while connecting to it
      self.stopServerProcess()

      result = fakeHTTPSResult(
        parameter_dict['domain'],
        'test-path/deep/.././deeper', headers={
          'X-Reply-Header-Cache-Control': 'max-age=1',
        },
        source_ip=source_ip
      )
      self.assertEqual(result.status_code, http.client.BAD_GATEWAY)
    finally:
      self.startServerProcess()
    # END: check stale-if-error support

  def test_enable_cache_ats_timeout(self):
    parameter_dict = self.assertSlaveBase('enable_cache')
    # check that timeout seen by ATS does not result in many queries done
    # to the backend and that next request works like a charm
    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test_enable_cache_ats_timeout', headers={
        'Timeout': '15',
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600'})

    # ATS timed out
    self.assertEqual(
      http.client.GATEWAY_TIMEOUT,
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
    timeout = 10
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
      parameter_dict['domain'],
      'test-path/deep/.././deeper', headers={
        'X-Reply-Header-Cache-Control': 'max-age=1, stale-while-'
        'revalidate=3600, stale-if-error=3600'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

  def test_enable_cache_disable_no_cache_request(self):
    parameter_dict = self.assertSlaveBase(
      'enable_cache-disable-no-cache-request')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path',
      headers={'Pragma': 'no-cache', 'Cache-Control': 'something'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = self.assertResponseHeaders(result, cached=True)

    self.assertKeyWithPop('Age', headers)

    self.assertEqual(
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value'
      },
      headers
    )

    backend_headers = result.json()['Incoming Headers']
    self.assertRequestHeaders(
      backend_headers, parameter_dict['domain'], cached=True)

    try:
      j = result.json()
    except Exception:
      raise ValueError('JSON decode problem in:\n%s' % (result.text,))
    self.assertFalse('pragma' in list(j['Incoming Headers'].keys()))

  def test_enable_cache_disable_via_header(self):
    parameter_dict = self.assertSlaveBase('enable_cache-disable-via-header')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = self.assertResponseHeaders(result, via=False)

    self.assertKeyWithPop('Age', headers)

    self.assertEqual(
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
      },
      headers
    )

    backend_headers = result.json()['Incoming Headers']
    self.assertRequestHeaders(
      backend_headers, parameter_dict['domain'], cached=True)

  def test_enable_http2_false(self):
    parameter_dict = self.assertSlaveBase('enable-http2-false')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = self.assertResponseHeaders(result)

    self.assertEqual(
      {
        'Content-Type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
      },
      headers
    )

    self.assertHttp11(parameter_dict['domain'])

  def test_enable_http2_default(self):
    parameter_dict = self.assertSlaveBase('enable-http2-default')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = self.assertResponseHeaders(result)
    self.assertEqual(
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
      },
      headers
    )

    self.assertHttp2(parameter_dict['domain'])

  def test_enable_http3_true(self):
    parameter_dict = self.assertSlaveBase('enable-http3-true')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = self.assertResponseHeaders(result)

    self.assertEqual(
      {
        'Content-Type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
      },
      headers
    )

    self.assertHttp2(parameter_dict['domain'])

  def test_enable_http3_default(self):
    parameter_dict = self.assertSlaveBase('enable-http3-default')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    headers = self.assertResponseHeaders(result)
    self.assertEqual(
      {
        'Content-type': 'application/json',
        'Set-Cookie': 'secured=value;secure, nonsecured=value',
      },
      headers
    )

    self.assertHttp2(parameter_dict['domain'])

  def test_prefer_gzip_encoding_to_backend_https_only(self):
    parameter_dict = self.assertSlaveBase(
      'prefer-gzip-encoding-to-backend-https-only')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    self.assertRequestHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'deflate'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    self.assertRequestHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'deflate', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    self.assertRequestHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'],
      port=HTTP_PORT, proto='http')
    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'deflate'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    self.assertRequestHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'],
      port=HTTP_PORT, proto='http')
    self.assertEqual(
      'deflate', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

  def test_prefer_gzip_encoding_to_backend(self):
    parameter_dict = self.assertSlaveBase(
      'prefer-gzip-encoding-to-backend')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    self.assertRequestHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'gzip', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'deflate'})

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    self.assertRequestHeaders(
      result.json()['Incoming Headers'], parameter_dict['domain'])
    self.assertEqual(
      'deflate', result.json()['Incoming Headers']['accept-encoding'])

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqualResultJson(result, 'Path', '/test-path/deeper')

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'gzip, deflate'})

    self.assertEqual(
      http.client.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://%s:%s/test-path/deeper' % (parameter_dict['domain'], HTTP_PORT),
      result.headers['Location']
    )

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper',
      headers={'Accept-Encoding': 'deflate'})

    self.assertEqual(
      http.client.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://%s:%s/test-path/deeper' % (parameter_dict['domain'], HTTP_PORT),
      result.headers['Location']
    )

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      http.client.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://%s:%s/test-path/deeper' % (parameter_dict['domain'], HTTP_PORT),
      result.headers['Location']
    )

    result = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      http.client.FOUND,
      result.status_code
    )

    self.assertEqual(
      'https://%s:%s/test-path/deeper' % (parameter_dict['domain'], HTTP_PORT),
      result.headers['Location']
    )

  def _curl(self, domain, ip, port, cookie=None):
    replacement_dict = dict(
      domain=domain, ip=ip, port=port)
    curl_command = [
        'curl', '-v', '-k',
        '-H', 'Host: %(domain)s' % replacement_dict,
        '--resolve', '%(domain)s:%(port)s:%(ip)s' % replacement_dict,
    ]
    if cookie is not None:
      curl_command.extend(['--cookie', cookie])
    curl_command.extend([
      'https://%(domain)s:%(port)s/' % replacement_dict])
    prc = subprocess.Popen(
      curl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = prc.communicate()
    self.assertEqual(
      prc.returncode, 0,
      "Problem running %r. Output:\n%s\nError:\n%s" % (
        curl_command, out, err))
    return out, err

  def test_disabled_cookie_list(self):
    parameter_dict = self.assertSlaveBase('disabled-cookie-list')
    out, err = self._curl(
      parameter_dict['domain'], TEST_IP, HTTPS_PORT,
      # Note: Cookie order is extremely important here, do not change
      # or test will start to pass incorrectly
      'Tea=present; Coconut=absent; DarkChocolate=present; Chocolate=absent; '
      'Coffee=present; Vanilia=absent; Water=present',
    )
    # self check - were the cookies sent in required order?
    self.assertIn(
      'ookie: Tea=present; Coconut=absent; DarkChocolate=present; '
      'Chocolate=absent; Coffee=present; Vanilia=absent; Water=present',
      err.decode())
    # real test - all configured cookies are dropped
    self.assertEqual(
      'Tea=present; DarkChocolate=present; Coffee=present; Water=present',
      json.loads(out)['Incoming Headers']['cookie'])

  def test_disabled_cookie_list_simple(self):
    parameter_dict = self.assertSlaveBase('disabled-cookie-list-simple')
    out, err = self._curl(
      parameter_dict['domain'], TEST_IP, HTTPS_PORT,
      'Chocolate=absent; Coffee=present',
    )
    # self check - were the cookies sent in required order?
    self.assertIn(
      'ookie: Chocolate=absent; Coffee=present',
      err.decode())
    # real test - all configured cookies are dropped
    self.assertEqual(
      'Coffee=present',
      json.loads(out)['Incoming Headers']['cookie'])

  def test_https_url(self):
    parameter_dict = self.assertSlaveBase('url_https-url')

    result = fakeHTTPSResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      'max-age=200; includeSubDomains; preload',
      result.headers['Strict-Transport-Security'])

    self.assertEqualResultJson(result, 'Path', '/https/test-path/deeper')
    self.assertRequestHeaders(
      result.json()['Incoming Headers'],
      parameter_dict['domain'])

    result_http = fakeHTTPResult(
      parameter_dict['domain'],
      'test-path/deep/.././deeper')

    self.assertEqual(
      http.client.FOUND,
      result_http.status_code
    )

    self.assertNotIn('Strict-Transport-Security', result_http.headers)

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

  def test_header_date(self):
    # Precisely check out Date header behaviour
    frontend = 'url_https-url'
    parameter_dict = self.assertSlaveBase(frontend)
    backend_url = self.getSlaveParameterDictDict()[
      frontend]['https-url'].strip()
    normal_path = 'normal'
    with_date_path = 'with_date'
    specific_date = 'Fri, 07 Dec 2001 00:00:00 GMT'
    result_configure = requests.put(
      backend_url + '/' + with_date_path, headers={
        'X-Reply-Header-Date': specific_date
      })
    self.assertEqual(result_configure.status_code, http.client.CREATED)

    result_normal = fakeHTTPSResult(parameter_dict['domain'], normal_path)
    result_with_date = fakeHTTPSResult(
      parameter_dict['domain'], with_date_path)

    # Prove that Date header with value specific_date send by backend is NOT
    # modified by the CDN, but some Date header is added, if backend sends non
    self.assertEqual(result_with_date.headers['Date'], specific_date)
    self.assertNotEqual(result_normal.headers['Date'], specific_date)

  def test_https_url_netloc_list(self):
    parameter_dict = self.assertSlaveBase('https-url-netloc-list')
    result = fakeHTTPSResult(parameter_dict['domain'], 'path')
    # assure that the request went to backend specified in the netloc
    self.assertEqual(
      result.headers['X-Backend-Identification'],
      'netloc'
    )

    result = fakeHTTPResult(parameter_dict['domain'], 'path')
    # assure that the request went to backend NOT specified in the netloc
    self.assertNotIn('X-Backend-Identification', result.headers)


class TestReplicateSlave(SlaveHttpFrontendTestCase, TestDataMixin, AtsMixin):
  instance_parameter_dict = {
      'domain': 'example.com',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
    }

  @classmethod
  def getInstanceParameterDict(cls):
    return cls.instance_parameter_dict

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'replicate': {
        'url': cls.backend_url,
        'enable_cache': True,
      },
    }

  def test(self):
    # now instantiate 2nd partition in started state
    # and due to port collision, stop the first one...
    self.instance_parameter_dict.update({
      '-frontend-quantity': 2,
      '-sla-2-computer_guid': self.slap._computer_id,
      '-frontend-1-state': 'stopped',
      '-frontend-2-state': 'started',
    })
    self.requestDefaultInstance()
    self.requestSlaves()
    self.slap.waitForInstance(self.instance_max_retry)
    # ...and be nice, put back the first one online
    self.instance_parameter_dict.update({
      '-frontend-1-state': 'started',
      '-frontend-2-state': 'stopped',
    })
    self.requestDefaultInstance()
    self.slap.waitForInstance(self.instance_max_retry)
    self.slap.waitForInstance(self.instance_max_retry)
    self.slap.waitForInstance(self.instance_max_retry)

    self.updateSlaveConnectionParameterDictDict()
    # the real assertions follow...
    parameter_dict = self.parseSlaveParameterDict('replicate')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict)
    key_list = [
      'frontend-node-1-node-information-json',
      'frontend-node-2-node-information-json'
    ]
    node_information_json_dict = {}
    for k in list(parameter_dict.keys()):
      if k.startswith('frontend-node') and k.endswith(
        'node-information-json'):
        node_information_json_dict[k] = parameter_dict.pop(k)
    self.assertEqual(
      key_list,
      list(node_information_json_dict.keys())
    )

    node_information_dict = json.loads(node_information_json_dict[key_list[0]])
    self.assertIn("node-id", node_information_dict)
    self.assertIn("version-hash-history", node_information_dict)
    self.node_information_dict = node_information_dict
    self.assertEqual(
      {
        'domain': 'replicate.example.com',
        'replication_number': '2',
        'url': 'http://replicate.example.com',
        'site_url': 'http://replicate.example.com',
        'secure_access': 'https://replicate.example.com',
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    result_http = fakeHTTPResult(
      parameter_dict['domain'], 'test-path')
    self.assertEqual(http.client.FOUND, result_http.status_code)

    # prove replication by asserting that slave ended up in both nodes
    frontend_haproxy_cfg_list = glob.glob(
      os.path.join(self.instance_path, '*', 'etc', 'frontend-haproxy.cfg'))
    self.assertEqual(2, len(frontend_haproxy_cfg_list))
    for frontend_haproxy_cfg in frontend_haproxy_cfg_list:
      with open(frontend_haproxy_cfg) as fh:
        self.assertIn('backend _replicate-http', fh.read())
    self.assertEqual(
      2,
      len(
        glob.glob(
          os.path.join(
            self.instance_path, '*', 'etc', 'frontend-haproxy.d',
            '._replicate.htpasswd')))
    )


class TestReplicateSlaveOtherDestroyed(SlaveHttpFrontendTestCase):
  instance_parameter_dict = {
      'domain': 'example.com',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
    }

  @classmethod
  def getInstanceParameterDict(cls):
    return cls.instance_parameter_dict

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'empty': {
        'url': cls.backend_url,
        'enable_cache': True,
      }
    }

  def test_extra_slave_instance_list_not_present_destroyed_request(self):
    # now instantiate 2nd partition in started state
    # and due to port collision, stop the first one
    self.instance_parameter_dict.update({
      '-frontend-quantity': 2,
      '-sla-2-computer_guid': self.slap._computer_id,
      '-frontend-1-state': 'stopped',
      '-frontend-2-state': 'started',

    })
    self.requestDefaultInstance()
    self.slap.waitForInstance(self.instance_max_retry)

    # now start back first instance, and destroy 2nd one
    self.instance_parameter_dict.update({
      '-frontend-1-state': 'started',
      '-frontend-2-state': 'destroyed',
    })
    self.requestDefaultInstance()
    self.slap.waitForInstance(self.instance_max_retry)
    self.slap.waitForInstance(self.instance_max_retry)
    self.slap.waitForInstance(self.instance_max_retry)

    buildout_file = os.path.join(
      self.getMasterPartitionPath(), 'instance-master.cfg')
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
    parameter_dict = self.assertSlaveBase('enable-http2-default')

    self.assertHttp11(parameter_dict['domain'])

  def test_enable_http2_false(self):
    parameter_dict = self.assertSlaveBase('enable-http2-false')

    self.assertHttp11(parameter_dict['domain'])

  def test_enable_http2_true(self):
    parameter_dict = self.assertSlaveBase('enable-http2-true')

    self.assertHttp2(parameter_dict['domain'])


class TestEnableHttp2ByDefaultDefaultSlave(SlaveHttpFrontendTestCase,
                                           TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
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
    parameter_dict = self.assertSlaveBase('enable-http2-default')

    self.assertHttp2(parameter_dict['domain'])

  def test_enable_http2_false(self):
    parameter_dict = self.assertSlaveBase('enable-http2-false')

    self.assertHttp11(parameter_dict['domain'])

  def test_enable_http2_true(self):
    parameter_dict = self.assertSlaveBase('enable-http2-true')

    self.assertHttp2(parameter_dict['domain'])


class TestRe6stVerificationUrlDefaultSlave(SlaveHttpFrontendTestCase,
                                           TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
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
    self.assertSlaveBase('default')

    re6st_connectivity_promise_list = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'plugin',
        're6st-connectivity.py'))

    self.assertEqual(1, len(re6st_connectivity_promise_list))
    re6st_connectivity_promise_file = re6st_connectivity_promise_list[0]

    self.assertEqual(
      getPromisePluginParameterDict(re6st_connectivity_promise_file),
      {
        'url': 'http://[2001:67c:1254:4::1]/index.html',
      }
    )


class TestRe6stVerificationUrlSlave(SlaveHttpFrontendTestCase,
                                    TestDataMixin):
  instance_parameter_dict = {
      'port': HTTPS_PORT,
      'domain': 'example.com',
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
    }

  @classmethod
  def getInstanceParameterDict(cls):
    return cls.instance_parameter_dict

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'default': {
        'url': cls.backend_url,
        'enable_cache': True,
      },
    }

  def test_default(self):
    self.instance_parameter_dict[
      're6st-verification-url'] = 'some-re6st-verification-url'
    # re-request instance with updated parameters
    self.requestDefaultInstance()

    # run once instance, it's only needed for later checks
    try:
      self.slap.waitForInstance()
    except Exception:
      pass

    self.assertSlaveBase('default')

    re6st_connectivity_promise_list = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'plugin',
        're6st-connectivity.py'))

    self.assertEqual(1, len(re6st_connectivity_promise_list))
    re6st_connectivity_promise_file = re6st_connectivity_promise_list[0]

    self.assertEqual(
      getPromisePluginParameterDict(re6st_connectivity_promise_file),
      {
        'url': 'some-re6st-verification-url',
      }
    )


class TestSlaveSlapOSMasterCertificateCompatibilityOverrideMaster(
  SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def setUpMaster(cls):
    parameter_dict = cls.requestDefaultInstance().getConnectionParameterDict()
    cls._fetchKedifaCaucaseCaCertificateFile(parameter_dict)
    # Do not upload certificates for the master partition

  def _updateDataReplacementDict(self, data_replacement_dict):
    local_replacement_dict = {
      '@@certificate_pem@@': unicode_escape(self.certificate_pem.decode()),
      '@@key_pem@@': unicode_escape(self.key_pem.decode()),
    }
    for key in list(local_replacement_dict.keys()):
      new_key = ''.join([key[:-2], '_double', '@@'])
      local_replacement_dict[new_key] = unicode_escape(
        local_replacement_dict[key])
    data_replacement_dict.update(**local_replacement_dict)

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'apache-certificate': cls.certificate_pem,
      'apache-key': cls.key_pem,
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
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
    parameter_dict = self.assertSlaveBase(
      'ssl_from_master_kedifa_overrides_master_certificate')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

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
      verify=self.kedifa_caucase_ca_certificate_file)
    requests.put(
      master_parameter_dict['master-key-upload-url'] + auth.text,
      data=key_pem + certificate_pem,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')


class TestSlaveSlapOSMasterCertificateCompatibility(
  SlaveHttpFrontendTestCase, TestDataMixin):

  def _updateDataReplacementDict(self, data_replacement_dict):
    local_replacement_dict = {
      '@@certificate_pem@@': unicode_escape(self.certificate_pem.decode()),
      '@@key_pem@@': unicode_escape(self.key_pem.decode()),
      '@@ssl_from_slave_certificate_pem@@': unicode_escape(
        self.ssl_from_slave_certificate_pem.decode()),
      '@@ssl_from_slave_key_pem@@': unicode_escape(
        self.ssl_from_slave_key_pem.decode()),
      '@@customdomain_certificate_pem@@': unicode_escape(
        self.customdomain_certificate_pem.decode()),
      '@@customdomain_key_pem@@': unicode_escape(
        self.customdomain_key_pem.decode()),
      '@@ssl_from_slave_kedifa_overrides_key_pem@@': unicode_escape(
        self.ssl_from_slave_kedifa_overrides_key_pem.decode()),
      '@@ssl_from_slave_kedifa_overrides_certificate_pem@@': unicode_escape(
        self.ssl_from_slave_kedifa_overrides_certificate_pem.decode()),
      '@@customdomain_ca_certificate_pem@@': unicode_escape(
        self.customdomain_ca_certificate_pem.decode()),
      '@@customdomain_ca_key_pem@@': unicode_escape(
        self.customdomain_ca_key_pem.decode()),
      '@@ca.certificate_pem@@': unicode_escape(
        self.ca.certificate_pem.decode()),
      '@@sslcacrtgarbage_ca_certificate_pem@@': unicode_escape(
        self.sslcacrtgarbage_ca_certificate_pem.decode()),
      '@@sslcacrtgarbage_ca_key_pem@@': unicode_escape(
        self.sslcacrtgarbage_ca_key_pem.decode()),
      '@@type_notebook_ssl_from_slave_certificate_pem@@': unicode_escape(
        self.type_notebook_ssl_from_slave_certificate_pem.decode()),
      '@@type_notebook_ssl_from_slave_key_pem@@': unicode_escape(
        self.type_notebook_ssl_from_slave_key_pem.decode()),
      '@@type_notebook_ssl_from_slave_kedifa_overrides_certificate_pem@@':
      unicode_escape(
        self.type_notebook_ssl_from_slave_kedifa_overrides_certificate_pem
        .decode()),
      '@@type_notebook_ssl_from_slave_kedifa_overrides_key_pem@@':
      unicode_escape(
        self.type_notebook_ssl_from_slave_kedifa_overrides_key_pem.decode()),
    }
    for key in list(local_replacement_dict.keys()):
      new_key = ''.join([key[:-2], '_double', '@@'])
      local_replacement_dict[new_key] = unicode_escape(
        local_replacement_dict[key])
    data_replacement_dict.update(**local_replacement_dict)

  @classmethod
  def setUpMaster(cls):
    parameter_dict = cls.requestDefaultInstance().getConnectionParameterDict()
    cls._fetchKedifaCaucaseCaCertificateFile(parameter_dict)
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
      'apache-certificate': cls.certificate_pem,
      'apache-key': cls.key_pem,
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
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
    self.assertBackendHaproxyStatisticUrl(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertPublishFailsafeErrorPromiseEmptyWithPop(parameter_dict)
    self.assertRejectedSlavePromiseEmptyWithPop(parameter_dict)

    expected_parameter_dict = {
      'monitor-base-url': 'https://[%s]:8401' % self._ipv6_address,
      'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      'domain': 'example.com',
      'accepted-slave-amount': '12',
      'rejected-slave-amount': '0',
      'slave-amount': '12',
      'rejected-slave-dict': {
      },
      'warning-list': [
        'apache-certificate is obsolete, please use master-key-upload-url',
        'apache-key is obsolete, please use master-key-upload-url',
      ],
      'warning-slave-dict': {
        '_custom_domain_ssl_crt_ssl_key': [
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url'
        ],
        '_custom_domain_ssl_crt_ssl_key_ssl_ca_crt': [
          'ssl_ca_crt is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url'
        ],
        '_ssl_ca_crt_does_not_match': [
          'ssl_ca_crt is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url',
        ],
        '_ssl_ca_crt_garbage': [
          'ssl_ca_crt is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url',
        ],
        # u'_ssl_ca_crt_only': [
        #   u'ssl_ca_crt is obsolete, please use key-upload-url',
        # ],
        '_ssl_from_slave': [
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url',
        ],
        '_ssl_from_slave_kedifa_overrides': [
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url',
        ],
        # u'_ssl_key-ssl_crt-unsafe': [
        #   u'ssl_key is obsolete, please use key-upload-url',
        #   u'ssl_crt is obsolete, please use key-upload-url',
        # ],
        '_type-notebook-ssl_from_slave': [
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url',
        ],
        '_type-notebook-ssl_from_slave_kedifa_overrides': [
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url',
        ],
      }
    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

  def test_ssl_from_master(self):
    parameter_dict = self.assertSlaveBase('ssl_from_master')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_ssl_from_master_kedifa_overrides(self):
    parameter_dict = self.assertSlaveBase('ssl_from_master_kedifa_overrides')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    _, key_pem, _, certificate_pem = \
        createSelfSignedCertificate([parameter_dict['domain']])

    # as now the place to put the key is known put the key there
    auth = requests.get(
      self.current_generate_auth,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, auth.status_code)

    data = certificate_pem + key_pem

    upload = requests.put(
      self.current_upload_url + auth.text,
      data=data,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, upload.status_code)
    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_ssl_from_slave(self):
    parameter_dict = self.assertSlaveBase(
      'ssl_from_slave',
      expected_parameter_dict={
        'warning-list': [
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url',
         ]
      })

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.ssl_from_slave_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_ssl_from_slave_kedifa_overrides(self):
    parameter_dict = self.assertSlaveBase(
      'ssl_from_slave_kedifa_overrides',
      expected_parameter_dict={
        'warning-list': ['ssl_crt is obsolete, please use key-upload-url',
                         'ssl_key is obsolete, please use key-upload-url']
      })

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.ssl_from_slave_kedifa_overrides_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    _, key_pem, _, certificate_pem = \
        createSelfSignedCertificate([parameter_dict['domain']])

    # as now the place to put the key is known put the key there
    auth = requests.get(
      self.current_generate_auth,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, auth.status_code)

    data = certificate_pem + key_pem

    upload = requests.put(
      self.current_upload_url + auth.text,
      data=data,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, upload.status_code)

    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_type_notebook_ssl_from_master(self):
    parameter_dict = self.assertSlaveBase('type-notebook-ssl_from_master')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path',
      HTTPS_PORT)

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_type_notebook_ssl_from_master_kedifa_overrides(self):
    parameter_dict = self.assertSlaveBase(
      'type-notebook-ssl_from_master_kedifa_overrides')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path',
      HTTPS_PORT)

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    _, key_pem, _, certificate_pem = \
        createSelfSignedCertificate([parameter_dict['domain']])

    # as now the place to put the key is known put the key there
    auth = requests.get(
      self.current_generate_auth,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, auth.status_code)

    data = certificate_pem + key_pem

    upload = requests.put(
      self.current_upload_url + auth.text,
      data=data,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, upload.status_code)

    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path',
      HTTPS_PORT)

    self.assertEqual(
      certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_type_notebook_ssl_from_slave(self):
    parameter_dict = self.assertSlaveBase(
      'type-notebook-ssl_from_slave',
      expected_parameter_dict={
        'warning-list': [
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url',
         ]
      })

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path',
      HTTPS_PORT)

    self.assertEqual(
      self.type_notebook_ssl_from_slave_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_type_notebook_ssl_from_slave_kedifa_overrides(self):
    parameter_dict = self.assertSlaveBase(
      'type-notebook-ssl_from_slave_kedifa_overrides',
      expected_parameter_dict={
        'warning-list': ['ssl_crt is obsolete, please use key-upload-url',
                         'ssl_key is obsolete, please use key-upload-url']
      })

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path',
      HTTPS_PORT)

    self.assertEqual(
      self.type_notebook_ssl_from_slave_kedifa_overrides_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

    _, key_pem, _, certificate_pem = \
        createSelfSignedCertificate([parameter_dict['domain']])

    # as now the place to put the key is known put the key there
    auth = requests.get(
      self.current_generate_auth,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, auth.status_code)

    data = certificate_pem + key_pem

    upload = requests.put(
      self.current_upload_url + auth.text,
      data=data,
      verify=self.kedifa_caucase_ca_certificate_file)
    self.assertEqual(http.client.CREATED, upload.status_code)

    self.runKedifaUpdater()

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path',
      HTTPS_PORT)

    self.assertEqual(
      certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  @skip('Not implemented in new test system')
  def test_custom_domain_ssl_crt_ssl_key(self):
    parameter_dict = self.assertSlaveBase(
      'custom_domain_ssl_crt_ssl_key',
      expected_parameter_dict={
        'warning-list': ['ssl_key is obsolete, please use key-upload-url',
                         'ssl_crt is obsolete, please use key-upload-url']
      })

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.customdomain_certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_ssl_ca_crt(self):
    parameter_dict = self.assertSlaveBase(
      'custom_domain_ssl_crt_ssl_key_ssl_ca_crt',
      expected_parameter_dict={
        'warning-list': [
          'ssl_ca_crt is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url'
        ]
      })

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

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
      expected = \
        self.customdomain_ca_certificate_pem.decode() + '\n' + \
        self.ca.certificate_pem.decode() + '\n' + \
        self.customdomain_ca_key_pem.decode()
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

    self.requestSlaveInstance(
        partition_reference='custom_domain_ssl_crt_ssl_key_ssl_ca_crt',
        partition_parameter_kw=slave_parameter_dict,
    )

    self.slap.waitForInstance()
    self.runKedifaUpdater()
    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

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
      expected = customdomain_ca_certificate_pem.decode() + '\n' + \
        ca.certificate_pem.decode() + '\n' + \
        customdomain_ca_key_pem.decode()
      self.assertEqual(
        expected,
        out.read()
      )

  def test_ssl_ca_crt_garbage(self):
    parameter_dict = self.assertSlaveBase(
      'ssl_ca_crt_garbage',
      expected_parameter_dict={
        'warning-list': [
          'ssl_ca_crt is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url']
      })

    result = fakeHTTPSResult(
        parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.sslcacrtgarbage_ca_certificate_pem,
      der2pem(result.peercert)
    )

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_ssl_ca_crt_does_not_match(self):
    parameter_dict = self.assertSlaveBase(
      'ssl_ca_crt_does_not_match',
      expected_parameter_dict={
        'warning-list': [
          'ssl_ca_crt is obsolete, please use key-upload-url',
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url'
        ]
      })

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    certificate_file_list = glob.glob(os.path.join(
      self.instance_path, '*', 'srv', 'bbb-ssl',
      '_ssl_ca_crt_does_not_match.crt'))
    self.assertEqual(1, len(certificate_file_list))
    certificate_file = certificate_file_list[0]
    with open(certificate_file) as out:
      expected = self.certificate_pem.decode() + '\n' + \
        self.ca.certificate_pem.decode() + '\n' + \
        self.key_pem.decode()
      self.assertEqual(
        expected,
        out.read()
      )


class TestSlaveSlapOSMasterCertificateCompatibilityUpdate(
  SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def setUpMaster(cls):
    parameter_dict = cls.requestDefaultInstance().getConnectionParameterDict()
    cls._fetchKedifaCaucaseCaCertificateFile(parameter_dict)
    # Do not upload certificates for the master partition

  def _updateDataReplacementDict(self, data_replacement_dict):
    local_replacement_dict = {
      '@@certificate_pem@@': unicode_escape(self.certificate_pem.decode()),
      '@@key_pem@@': unicode_escape(self.key_pem.decode()),
    }
    for key in list(local_replacement_dict.keys()):
      new_key = ''.join([key[:-2], '_double', '@@'])
      local_replacement_dict[new_key] = unicode_escape(
        local_replacement_dict[key])
    data_replacement_dict.update(**local_replacement_dict)

  instance_parameter_dict = {
    'domain': 'example.com',
    'port': HTTPS_PORT,
    'plain_http_port': HTTP_PORT,
    'kedifa_port': KEDIFA_PORT,
    'caucase_port': CAUCASE_PORT,
  }

  @classmethod
  def getInstanceParameterDict(cls):
    if 'apache-certificate' not in cls.instance_parameter_dict:
      cls.instance_parameter_dict.update(**{
        'apache-certificate': cls.certificate_pem,
        'apache-key': cls.key_pem,
      })
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
    self.assertBackendHaproxyStatisticUrl(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertPublishFailsafeErrorPromiseEmptyWithPop(parameter_dict)
    self.assertRejectedSlavePromiseEmptyWithPop(parameter_dict)

    expected_parameter_dict = {
      'monitor-base-url': 'https://[%s]:8401' % self._ipv6_address,
      'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      'domain': 'example.com',
      'accepted-slave-amount': '1',
      'rejected-slave-amount': '0',
      'rejected-slave-dict': {},
      'slave-amount': '1',
      'warning-list': [
        'apache-certificate is obsolete, please use master-key-upload-url',
        'apache-key is obsolete, please use master-key-upload-url',
      ],
    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

  def test_apache_key_apache_certificate_update(self):
    parameter_dict = self.assertSlaveBase('ssl_from_master')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

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
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')


class TestSlaveCiphers(SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
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
    self.assertBackendHaproxyStatisticUrl(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertPublishFailsafeErrorPromiseEmptyWithPop(parameter_dict)
    self.assertRejectedSlavePromiseEmptyWithPop(parameter_dict)

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
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(http.client.OK, result.status_code)

    result_http = fakeHTTPResult(
      parameter_dict['domain'], 'test-path')
    self.assertEqual(http.client.FOUND, result_http.status_code)

    configuration_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'frontend-haproxy-crt-list.txt'
      ))[0]
    with open(configuration_file) as fh:
      self.assertIn(
        '_default_ciphers.pem [ciphers '
        'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384 ',
        fh.read())

  def test_own_ciphers(self):
    parameter_dict = self.assertSlaveBase('own_ciphers')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(http.client.OK, result.status_code)

    result_http = fakeHTTPResult(
      parameter_dict['domain'], 'test-path')
    self.assertEqual(http.client.FOUND, result_http.status_code)

    configuration_file = glob.glob(
      os.path.join(
        self.instance_path, '*', 'etc', 'frontend-haproxy-crt-list.txt'
      ))[0]
    with open(configuration_file) as fh:
      self.assertIn(
        '_own_ciphers.pem [ciphers '
        'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256 ',
        fh.read())


class TestSlaveRejectReportUnsafeDamaged(SlaveHttpFrontendTestCase):
  @classmethod
  def prepareCertificate(cls):
    cls.ca = CertificateAuthority('TestSlaveRejectReportUnsafeDamaged')
    super(TestSlaveRejectReportUnsafeDamaged, cls).prepareCertificate()

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
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
      cls.slap.waitForInstance(max_retry=10)
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
      'URL': {
        'url': "https://[fd46::c2ae]:!py!u'123123'",
      },
      'HTTPS-URL': {
        'https-url': "https://[fd46::c2ae]:!py!u'123123'",
      },
      'SSL-PROXY-VERIFY_SSL_PROXY_CA_CRT_DAMAGED': {
        'url': cls.backend_https_url,
        'ssl-proxy-verify': True,
        'ssl_proxy_ca_crt': 'damaged',
      },
      'SSL-PROXY-VERIFY_SSL_PROXY_CA_CRT_EMPTY': {
        'url': cls.backend_https_url,
        'ssl-proxy-verify': True,
        'ssl_proxy_ca_crt': '',
      },
      'health-check-failover-SSL-PROXY-VERIFY_SSL_PROXY_CA_CRT_DAMAGED': {
        'url': cls.backend_https_url,
        'health-check-failover-ssl-proxy-verify': True,
        'health-check-failover-ssl-proxy-ca-crt': 'damaged',
      },
      'health-check-failover-SSL-PROXY-VERIFY_SSL_PROXY_CA_CRT_EMPTY': {
        'url': cls.backend_https_url,
        'health-check-failover-ssl-proxy-verify': True,
        'health-check-failover-ssl-proxy-ca-crt': '',
      },
      'BAD-BACKEND': {
        'url': 'http://1:2:3:4',
        'https-url': 'http://host.domain:badport',
      },
      'EMPTY-BACKEND': {
        'url': '',
        'https-url': '',
      },
      'CUSTOM_DOMAIN-UNSAFE': {
        'custom_domain': '${section:option} afterspace\nafternewline',
      },
      'SERVER-ALIAS-UNSAFE': {
        'server-alias': '${section:option} afterspace',
      },
      'SERVER-ALIAS-SAME': {
        'url': cls.backend_url,
        'server-alias': 'serveraliassame.example.com',
      },
      'VIRTUALHOSTROOT-HTTP-PORT-UNSAFE': {
        'type': 'zope',
        'url': cls.backend_url,
        'virtualhostroot-http-port': '${section:option}',
      },
      'VIRTUALHOSTROOT-HTTPS-PORT-UNSAFE': {
        'type': 'zope',
        'url': cls.backend_url,
        'virtualhostroot-https-port': '${section:option}',
      },
      'DEFAULT-PATH-UNSAFE': {
        'type': 'zope',
        'url': cls.backend_url,
        'default-path': '${section:option}\nn"\newline\n}\n}proxy\n/slashed',
      },
      'BAD-CIPHERS': {
        'ciphers': 'bad ECDHE-ECDSA-AES256-GCM-SHA384 again',
      },
      'SITE_1': {
        'custom_domain': 'duplicate.example.com',
      },
      'SITE_2': {
        'custom_domain': 'duplicate.example.com',
      },
      'SITE_3': {
        'server-alias': 'duplicate.example.com',
      },
      'SITE_4': {
        'custom_domain': 'duplicate.example.com',
        'server-alias': 'duplicate.example.com',
      },
      'SSL_CA_CRT_ONLY': {
        'url': cls.backend_url,
        'ssl_ca_crt': cls.ca.certificate_pem,
      },
      'SSL_KEY-SSL_CRT-UNSAFE': {
        'ssl_key': '${section:option}ssl_keyunsafe\nunsafe',
        'ssl_crt': '${section:option}ssl_crtunsafe\nunsafe',
      },
      'health-check-http-method': {
        'health-check': True,
        'health-check-http-method': 'WRONG',
      },
      'health-check-http-version': {
        'health-check': True,
        'health-check-http-version': 'WRONG/1.1',
      },
      'health-check-timeout': {
        'health-check': True,
        'health-check-timeout': 'WRONG',
      },
      'health-check-timeout-negative': {
        'health-check': True,
        'health-check-timeout': '-2',
      },
      'health-check-interval': {
        'health-check': True,
        'health-check-interval': 'WRONG',
      },
      'health-check-interval-negative': {
        'health-check': True,
        'health-check-interval': '-2',
      },
      'health-check-rise': {
        'health-check': True,
        'health-check-rise': 'WRONG',
      },
      'health-check-rise-negative': {
        'health-check': True,
        'health-check-rise': '-2',
      },
      'health-check-fall': {
        'health-check': True,
        'health-check-fall': 'WRONG',
      },
      'health-check-fall-negative': {
        'health-check': True,
        'health-check-fall': '-2',
      }
    }

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
        {
          '_SITE_4': ["custom_domain 'duplicate.example.com' clashes"],
          '_SITE_2': ["custom_domain 'duplicate.example.com' clashes"],
          '_SITE_3': ["server-alias 'duplicate.example.com' clashes"]
        },
        result_json
      )
    except AssertionError:
      raise
    except Exception as e:
      self.fail(e)

  def test_master_partition_state(self):
    parameter_dict = self.parseConnectionParameterDict()
    self.assertKeyWithPop('monitor-setup-url', parameter_dict)
    self.assertBackendHaproxyStatisticUrl(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertPublishFailsafeErrorPromiseEmptyWithPop(parameter_dict)
    self.assertRejectedSlavePromiseWithPop(parameter_dict)

    expected_parameter_dict = {
      'monitor-base-url': 'https://[%s]:8401' % self._ipv6_address,
      'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      'domain': 'example.com',
      'accepted-slave-amount': '3',
      'rejected-slave-amount': '28',
      'slave-amount': '31',
      'rejected-slave-dict': {
        '_HTTPS-URL': ['slave https-url "https://[fd46::c2ae]:!py!u\'123123\'"'
                       ' invalid'],
        '_URL': ['slave url "https://[fd46::c2ae]:!py!u\'123123\'" invalid'],
        '_SSL-PROXY-VERIFY_SSL_PROXY_CA_CRT_DAMAGED': [
          'ssl_proxy_ca_crt is invalid'
        ],
        '_SSL-PROXY-VERIFY_SSL_PROXY_CA_CRT_EMPTY': [
          'ssl_proxy_ca_crt is invalid'
        ],
        '_BAD-CIPHERS': [
          "Cipher 'again' is not supported.",
          "Cipher 'bad' is not supported."
        ],
        '_CUSTOM_DOMAIN-UNSAFE': [
          "custom_domain '${section:option} afterspace\\nafternewline' invalid"
        ],
        '_SERVER-ALIAS-UNSAFE': [
          "server-alias '${section:option}' not valid",
          "server-alias 'afterspace' not valid"
        ],
        '_SITE_2': ["custom_domain 'duplicate.example.com' clashes"],
        '_SITE_3': ["server-alias 'duplicate.example.com' clashes"],
        '_SITE_4': ["custom_domain 'duplicate.example.com' clashes"],
        '_SSL_CA_CRT_ONLY': [
          "ssl_ca_crt is present, so ssl_crt and ssl_key are required"],
        '_SSL_KEY-SSL_CRT-UNSAFE': [
          "slave ssl_key and ssl_crt does not match"],
        '_BAD-BACKEND': [
          "slave https-url 'http://host.domain:badport' invalid",
          "slave url 'http://1:2:3:4' invalid"],
        '_VIRTUALHOSTROOT-HTTP-PORT-UNSAFE': [
          "Wrong virtualhostroot-http-port '${section:option}'"],
        '_VIRTUALHOSTROOT-HTTPS-PORT-UNSAFE': [
          "Wrong virtualhostroot-https-port '${section:option}'"],
        '_EMPTY-BACKEND': [
          "slave https-url '' invalid",
          "slave url '' invalid"],
        '_health-check-failover-SSL-PROXY-VERIFY_SSL_PROXY_CA_CRT_DAMAGED': [
          'health-check-failover-ssl-proxy-ca-crt is invalid'
        ],
        '_health-check-failover-SSL-PROXY-VERIFY_SSL_PROXY_CA_CRT_EMPTY': [
          'health-check-failover-ssl-proxy-ca-crt is invalid'
        ],
        '_health-check-fall': [
          'Wrong health-check-fall WRONG'],
        '_health-check-fall-negative': [
          'Wrong health-check-fall -2'],
        '_health-check-http-method': [
          'Wrong health-check-http-method WRONG'],
        '_health-check-http-version': [
          'Wrong health-check-http-version WRONG/1.1'],
        '_health-check-interval': [
          'Wrong health-check-interval WRONG'],
        '_health-check-interval-negative': [
          'Wrong health-check-interval -2'],
        '_health-check-rise': [
          'Wrong health-check-rise WRONG'],
        '_health-check-rise-negative': [
          'Wrong health-check-rise -2'],
        '_health-check-timeout': [
          'Wrong health-check-timeout WRONG'],
        '_health-check-timeout-negative': [
          'Wrong health-check-timeout -2'],
      },
      'warning-slave-dict': {
        '_SSL_CA_CRT_ONLY': [
          'ssl_ca_crt is obsolete, please use key-upload-url'],
        '_SSL_KEY-SSL_CRT-UNSAFE': [
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url']}
    }

    self.assertEqual(
      expected_parameter_dict,
      parameter_dict
    )

  def test_url(self):
    parameter_dict = self.parseSlaveParameterDict('URL')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': [
          "slave url \"https://[fd46::c2ae]:!py!u'123123'\" invalid"]
      },
      parameter_dict
    )

  def test_https_url(self):
    parameter_dict = self.parseSlaveParameterDict('HTTPS-URL')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': [
          "slave https-url \"https://[fd46::c2ae]:!py!u'123123'\" invalid"]
      },
      parameter_dict
    )

  def test_ssl_proxy_verify_ssl_proxy_ca_crt_damaged(self):
    parameter_dict = self.parseSlaveParameterDict(
      'SSL-PROXY-VERIFY_SSL_PROXY_CA_CRT_DAMAGED')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {'request-error-list': ["ssl_proxy_ca_crt is invalid"]},
      parameter_dict
    )

  def test_ssl_proxy_verify_ssl_proxy_ca_crt_empty(self):
    parameter_dict = self.parseSlaveParameterDict(
      'SSL-PROXY-VERIFY_SSL_PROXY_CA_CRT_EMPTY')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {'request-error-list': ["ssl_proxy_ca_crt is invalid"]},
      parameter_dict
    )

  def test_health_check_failover_ssl_proxy_ca_crt_damaged(self):
    parameter_dict = self.parseSlaveParameterDict(
      'health-check-failover-SSL-PROXY-VERIFY_SSL_PROXY_CA_CRT_DAMAGED')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': [
          "health-check-failover-ssl-proxy-ca-crt is invalid"]
      },
      parameter_dict
    )

  def test_health_check_failover_ssl_proxy_ca_crt_empty(self):
    parameter_dict = self.parseSlaveParameterDict(
      'health-check-failover-SSL-PROXY-VERIFY_SSL_PROXY_CA_CRT_EMPTY')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': [
          "health-check-failover-ssl-proxy-ca-crt is invalid"]
      },
      parameter_dict
    )

  def test_server_alias_same(self):
    parameter_dict = self.assertSlaveBase(
      'SERVER-ALIAS-SAME')

    result = fakeHTTPSResult(
      parameter_dict['domain'], 'test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_custom_domain_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict('CUSTOM_DOMAIN-UNSAFE')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': [
          "custom_domain '${section:option} afterspace\\nafternewline' invalid"
        ]
      },
      parameter_dict
    )

  def test_server_alias_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict('SERVER-ALIAS-UNSAFE')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': [
          "server-alias '${section:option}' not valid", "server-alias "
          "'afterspace' not valid"]
      },
      parameter_dict
    )

  def test_bad_ciphers(self):
    parameter_dict = self.parseSlaveParameterDict('BAD-CIPHERS')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': [
          "Cipher 'again' is not supported.",
          "Cipher 'bad' is not supported."
        ]
      },
      parameter_dict
    )

  def test_virtualhostroot_http_port_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict(
      'VIRTUALHOSTROOT-HTTP-PORT-UNSAFE')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': [
          "Wrong virtualhostroot-http-port '${section:option}'"
        ]
      },
      parameter_dict
    )

  def test_virtualhostroot_https_port_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict(
      'VIRTUALHOSTROOT-HTTPS-PORT-UNSAFE')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': [
          "Wrong virtualhostroot-https-port '${section:option}'"
        ]
      },
      parameter_dict
    )

  def default_path_unsafe(self):
    parameter_dict = self.parseSlaveParameterDict('DEFAULT-PATH-UNSAFE')
    self.assertLogAccessUrlWithPop(parameter_dict)
    self.assertKedifaKeysWithPop(parameter_dict, 'master-')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'domain': 'defaultpathunsafe.example.com',
        'replication_number': '1',
        'url': 'http://defaultpathunsafe.example.com',
        'site_url': 'http://defaultpathunsafe.example.com',
        'secure_access': 'https://defaultpathunsafe.example.com',
        'backend-client-caucase-url': 'http://[%s]:8990' % self._ipv6_address,
      },
      parameter_dict
    )

    result = fakeHTTPSResult(
      parameter_dict['domain'], '')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqual(
      http.client.MOVED_PERMANENTLY,
      result.status_code
    )

    self.assertEqual(
      'https://defaultpathunsafe.example.com:%s/%%24%%7Bsection%%3Aoption%%7D'
      '%%0An%%22%%0Aewline%%0A%%7D%%0A%%7Dproxy%%0A/slashed' % (HTTPS_PORT,),
      result.headers['Location']
    )

  def test_site_1(self):
    self.assertSlaveBase('SITE_1', hostname='duplicate')

  def test_site_2(self):
    parameter_dict = self.parseSlaveParameterDict('SITE_2')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': ["custom_domain 'duplicate.example.com' clashes"]
      },
      parameter_dict
    )

  def test_site_3(self):
    parameter_dict = self.parseSlaveParameterDict('SITE_3')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': ["server-alias 'duplicate.example.com' clashes"]
      },
      parameter_dict,
    )

  def test_site_4(self):
    parameter_dict = self.parseSlaveParameterDict('SITE_4')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': ["custom_domain 'duplicate.example.com' clashes"]
      },
      parameter_dict
    )

  def test_ssl_ca_crt_only(self):
    parameter_dict = self.parseSlaveParameterDict('SSL_CA_CRT_ONLY')
    self.assertNodeInformationWithPop(parameter_dict)
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
    parameter_dict = self.parseSlaveParameterDict('SSL_KEY-SSL_CRT-UNSAFE')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': ["slave ssl_key and ssl_crt does not match"],
        'warning-list': [
          'ssl_crt is obsolete, please use key-upload-url',
          'ssl_key is obsolete, please use key-upload-url']
      },
      parameter_dict
    )

  def test_bad_backend(self):
    parameter_dict = self.parseSlaveParameterDict('BAD-BACKEND')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': [
          "slave https-url 'http://host.domain:badport' invalid",
          "slave url 'http://1:2:3:4' invalid"],
      },
      parameter_dict
    )

  def test_empty_backend(self):
    parameter_dict = self.parseSlaveParameterDict('EMPTY-BACKEND')
    self.assertNodeInformationWithPop(parameter_dict)
    self.assertEqual(
      {
        'request-error-list': [
          "slave https-url '' invalid",
          "slave url '' invalid"]
      },
      parameter_dict
    )


class TestSlaveHostHaproxyClash(SlaveHttpFrontendTestCase, TestDataMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
      'request-timeout': '12',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    # Note: The slaves are specifically constructed to have an order which
    #       is triggering the problem. Slave list is sorted in many places,
    #       and such slave configuration will result with them begin seen
    #       by backend haproxy configuration in exactly the way seen below
    #       Ordering it here will not help at all.
    return {
      'wildcard': {
        'url': cls.backend_url + 'wildcard',
        'custom_domain': '*.alias1.example.com',
      },
      'zspecific': {
        'url': cls.backend_url + 'zspecific',
        'custom_domain': 'zspecific.alias1.example.com',
      },
    }

  def test(self):
    self.assertSlaveBase(
      'wildcard', hostname='*.alias1')
    self.assertSlaveBase(
      'zspecific', hostname='zspecific.alias1')

    result_wildcard = fakeHTTPSResult(
      'other.alias1.example.com',
      'test-path',
      headers={
        'Timeout': '10',  # more than default backend-connect-timeout == 5
        'Accept-Encoding': 'gzip',
      }
    )
    self.assertEqual(self.certificate_pem, der2pem(result_wildcard.peercert))
    self.assertEqualResultJson(result_wildcard, 'Path', '/wildcard/test-path')

    result_specific = fakeHTTPSResult(
      'zspecific.alias1.example.com',
      'test-path',
      headers={
        'Timeout': '10',  # more than default backend-connect-timeout == 5
        'Accept-Encoding': 'gzip',
      }
    )
    self.assertEqual(self.certificate_pem, der2pem(result_specific.peercert))
    self.assertEqualResultJson(result_specific, 'Path', '/zspecific/test-path')


class TestPassedRequestParameter(HttpFrontendTestCase):
  # special SRs to check out
  frontend_2_sr = 'special_sr_for_2'
  frontend_3_sr = 'special_sr_for_3'
  kedifa_sr = 'special_sr_for_kedifa'

  @classmethod
  def setUpClass(cls):
    super(TestPassedRequestParameter, cls).setUpClass()
    cls.slap.supply(cls.frontend_2_sr, cls.slap._computer_id)
    cls.slap.supply(cls.frontend_3_sr, cls.slap._computer_id)
    cls.slap.supply(cls.kedifa_sr, cls.slap._computer_id)

  @classmethod
  def tearDownClass(cls):
    cls.slap.supply(
      cls.frontend_2_sr, cls.slap._computer_id, state="destroyed")
    cls.slap.supply(
      cls.frontend_3_sr, cls.slap._computer_id, state="destroyed")
    cls.slap.supply(
      cls.kedifa_sr, cls.slap._computer_id, state="destroyed")
    super(TestPassedRequestParameter, cls).tearDownClass()

  instance_parameter_dict = {
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
  }

  @classmethod
  def getInstanceParameterDict(cls):
    return cls.instance_parameter_dict

  def test(self):
    self.instance_parameter_dict.update({
      # master partition parameters
      '-frontend-quantity': 3,
      '-sla-2-computer_guid': self.slap._computer_id,
      '-sla-3-computer_guid': self.slap._computer_id,
      '-frontend-2-state': 'stopped',
      '-frontend-2-software-release-url': self.frontend_2_sr,
      '-frontend-3-state': 'stopped',
      '-frontend-3-software-release-url': self.frontend_3_sr,
      '-kedifa-software-release-url': self.kedifa_sr,
      'automatic-internal-kedifa-caucase-csr': False,
      'automatic-internal-backend-client-caucase-csr': False,
      # all nodes partition parameters
      'apache-certificate': self.certificate_pem,
      'apache-key': self.key_pem,
      'domain': 'example.com',
      'enable-http2-by-default': True,
      're6st-verification-url': 're6st-verification-url',
      'backend-connect-timeout': 2,
      'backend-connect-retries': 1,
      'ciphers': 'ciphers',
      'request-timeout': 100,
      'authenticate-to-backend': True,
      # specific parameters
      '-frontend-config-1-ram-cache-size': '512K',
      '-frontend-config-2-ram-cache-size': '256K',
    })

    # re-request instance with updated parameters
    self.requestDefaultInstance()

    # run once instance, it's only needed for later checks
    try:
      self.slap.waitForInstance()
    except Exception:
      pass

    computer = self.slap._slap.registerComputer('local')
    # state of parameters of all instances
    partition_parameter_dict_dict = {}
    for partition in computer.getComputerPartitionList():
      if partition.getState() == 'destroyed':
        continue
      parameter_dict = partition.getInstanceParameterDict()
      instance_title = parameter_dict['instance_title']
      if '_' in parameter_dict:
        # "flatten" the instance parameter
        parameter_dict = json.loads(parameter_dict['_'])
      partition_parameter_dict_dict[instance_title] = parameter_dict
      parameter_dict[
        'X-software_release_url'] = partition.getSoftwareRelease().getURI()

    base_software_url = self.getSoftwareURL()

    # drop some very varying parameters
    def assertKeyWithPop(d, k):
      self.assertIn(k, d)
      d.pop(k)
    assertKeyWithPop(
      partition_parameter_dict_dict['caddy-frontend-1'],
      'master-key-download-url')
    assertKeyWithPop(
      partition_parameter_dict_dict['caddy-frontend-2'],
      'master-key-download-url')
    assertKeyWithPop(
      partition_parameter_dict_dict['caddy-frontend-3'],
      'master-key-download-url')
    assertKeyWithPop(
      partition_parameter_dict_dict['testing partition 0'],
      'timestamp')
    assertKeyWithPop(
      partition_parameter_dict_dict['testing partition 0'],
      'ip_list')

    monitor_password = partition_parameter_dict_dict[
      'caddy-frontend-1'].pop('monitor-password')
    self.assertEqual(
      monitor_password,
      partition_parameter_dict_dict[
        'caddy-frontend-2'].pop('monitor-password')
    )
    self.assertEqual(
      monitor_password,
      partition_parameter_dict_dict[
        'caddy-frontend-3'].pop('monitor-password')
    )
    self.assertEqual(
      monitor_password,
      partition_parameter_dict_dict[
        'kedifa'].pop('monitor-password')
    )

    backend_client_caucase_url = 'http://[%s]:8990' % (self._ipv6_address,)
    kedifa_caucase_url = 'http://[%s]:15090' % (self._ipv6_address,)
    expected_partition_parameter_dict_dict = {
      'caddy-frontend-1': {
        'X-software_release_url': base_software_url,
        'apache-certificate': self.certificate_pem.decode(),
        'apache-key': self.key_pem.decode(),
        'authenticate-to-backend': 'True',
        'backend-client-caucase-url': backend_client_caucase_url,
        'backend-connect-retries': '1',
        'backend-connect-timeout': '2',
        'ciphers': 'ciphers',
        'cluster-identification': 'testing partition 0',
        'domain': 'example.com',
        'enable-http2-by-default': 'True',
        'enable-http3': 'false',
        'extra_slave_instance_list': '[]',
        'frontend-name': 'caddy-frontend-1',
        'http3-port': '443',
        'kedifa-caucase-url': kedifa_caucase_url,
        'monitor-cors-domains': 'monitor.app.officejs.com',
        'monitor-httpd-port': 8411,
        'monitor-username': 'admin',
        'plain_http_port': '11080',
        'port': '11443',
        'ram-cache-size': '512K',
        're6st-verification-url': 're6st-verification-url',
        'request-timeout': '100',
        'slave-kedifa-information': '{}'
      },
      'caddy-frontend-2': {
        'X-software_release_url': self.frontend_2_sr,
        'apache-certificate': self.certificate_pem.decode(),
        'apache-key': self.key_pem.decode(),
        'authenticate-to-backend': 'True',
        'backend-client-caucase-url': backend_client_caucase_url,
        'backend-connect-retries': '1',
        'backend-connect-timeout': '2',
        'ciphers': 'ciphers',
        'cluster-identification': 'testing partition 0',
        'domain': 'example.com',
        'enable-http2-by-default': 'True',
        'enable-http3': 'false',
        'extra_slave_instance_list': '[]',
        'frontend-name': 'caddy-frontend-2',
        'http3-port': '443',
        'kedifa-caucase-url': kedifa_caucase_url,
        'monitor-cors-domains': 'monitor.app.officejs.com',
        'monitor-httpd-port': 8412,
        'monitor-username': 'admin',
        'plain_http_port': '11080',
        'port': '11443',
        'ram-cache-size': '256K',
        're6st-verification-url': 're6st-verification-url',
        'request-timeout': '100',
        'slave-kedifa-information': '{}'
      },
      'caddy-frontend-3': {
        'X-software_release_url': self.frontend_3_sr,
        'apache-certificate': self.certificate_pem.decode(),
        'apache-key': self.key_pem.decode(),
        'authenticate-to-backend': 'True',
        'backend-client-caucase-url': backend_client_caucase_url,
        'backend-connect-retries': '1',
        'backend-connect-timeout': '2',
        'ciphers': 'ciphers',
        'cluster-identification': 'testing partition 0',
        'domain': 'example.com',
        'enable-http2-by-default': 'True',
        'enable-http3': 'false',
        'extra_slave_instance_list': '[]',
        'frontend-name': 'caddy-frontend-3',
        'http3-port': '443',
        'kedifa-caucase-url': kedifa_caucase_url,
        'monitor-cors-domains': 'monitor.app.officejs.com',
        'monitor-httpd-port': 8413,
        'monitor-username': 'admin',
        'plain_http_port': '11080',
        'port': '11443',
        're6st-verification-url': 're6st-verification-url',
        'request-timeout': '100',
        'slave-kedifa-information': '{}'
      },
      'kedifa': {
        'X-software_release_url': self.kedifa_sr,
        'caucase_port': '15090',
        'cluster-identification': 'testing partition 0',
        'kedifa_port': '15080',
        'monitor-cors-domains': 'monitor.app.officejs.com',
        'monitor-httpd-port': '8402',
        'monitor-username': 'admin',
        'slave-list': []
      },
      'testing partition 0': {
        '-frontend-2-software-release-url': self.frontend_2_sr,
        '-frontend-2-state': 'stopped',
        '-frontend-3-software-release-url': self.frontend_3_sr,
        '-frontend-3-state': 'stopped',
        '-frontend-config-1-ram-cache-size': '512K',
        '-frontend-config-2-ram-cache-size': '256K',
        '-frontend-quantity': '3',
        '-kedifa-software-release-url': self.kedifa_sr,
        '-sla-2-computer_guid': 'local',
        '-sla-3-computer_guid': 'local',
        'X-software_release_url': base_software_url,
        'apache-certificate': self.certificate_pem.decode(),
        'apache-key': self.key_pem.decode(),
        'authenticate-to-backend': 'True',
        'automatic-internal-backend-client-caucase-csr': 'False',
        'automatic-internal-kedifa-caucase-csr': 'False',
        'backend-connect-retries': '1',
        'backend-connect-timeout': '2',
        'caucase_port': '15090',
        'ciphers': 'ciphers',
        'domain': 'example.com',
        'enable-http2-by-default': 'True',
        'full_address_list': [],
        'instance_title': 'testing partition 0',
        'kedifa_port': '15080',
        'plain_http_port': '11080',
        'port': '11443',
        're6st-verification-url': 're6st-verification-url',
        'request-timeout': '100',
        'root_instance_title': 'testing partition 0',
        'slap_computer_id': 'local',
        'slap_computer_partition_id': 'T-0',
        'slap_software_release_url': base_software_url,
        'slap_software_type': 'RootSoftwareInstance',
        'slave_instance_list': []
      }
    }
    self.assertEqual(
      expected_partition_parameter_dict_dict,
      partition_parameter_dict_dict
    )


class TestSlaveHealthCheck(SlaveHttpFrontendTestCase, TestDataMixin, AtsMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
      'request-timeout': '12',
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    cls.setUpAssertionDict()
    return {
      'health-check-disabled': {
        'url': cls.backend_url,
      },
      'health-check-default': {
        'url': cls.backend_url,
        'health-check': True,
      },
      'health-check-connect': {
        'url': cls.backend_url,
        'health-check': True,
        'health-check-http-method': 'CONNECT',
      },
      'health-check-custom': {
        'url': cls.backend_url,
        'health-check': True,
        'health-check-http-method': 'POST',
        'health-check-http-path': '/POST-path to be encoded',
        'health-check-http-version': 'HTTP/1.0',
        'health-check-timeout': '7',
        'health-check-interval': '15',
        'health-check-rise': '3',
        'health-check-fall': '7',
      },
      'health-check-failover-url': {
        'https-only': False,  # http and https access to check
        'enable_cache': True,
        'health-check-timeout': 1,  # fail fast for test
        'health-check-interval': 1,  # fail fast for test
        'url': cls.backend_url + 'url',
        'https-url': cls.backend_url + 'https-url',
        'health-check': True,
        'health-check-http-path': '/health-check-failover-url',
        'health-check-failover-url': cls.backend_url + 'failover-url?a=b&c=',
        'health-check-failover-https-url':
        cls.backend_url + 'failover-https-url?a=b&c=',
      },
      'health-check-failover-url-netloc-list': {
        'https-only': False,  # http and https access to check
        'health-check-timeout': 1,  # fail fast for test
        'health-check-interval': 1,  # fail fast for test
        'url': cls.backend_url + 'url',
        'https-url': cls.backend_url + 'https-url',
        'health-check': True,
        'health-check-http-path': '/health-check-failover-url',
        'health-check-failover-url': cls.backend_url + 'failover-url?a=b&c=',
        'health-check-failover-https-url':
        cls.backend_url + 'failover-https-url?a=b&c=',
        'health-check-failover-url-netloc-list':
        '%(ip)s:%(port_a)s %(ip)s:%(port_b)s' % {
          'ip': cls._ipv4_address,
          'port_a': cls._server_netloc_a_http_port,
          'port_b': cls._server_netloc_b_http_port},
      },
      'health-check-failover-url-auth-to-backend': {
        'https-only': False,  # http and https access to check
        'health-check-timeout': 1,  # fail fast for test
        'health-check-interval': 1,  # fail fast for test
        'url': cls.backend_url + 'url',
        'https-url': cls.backend_url + 'https-url',
        'health-check': True,
        'health-check-http-path': '/health-check-failover-url-auth-to-backend',
        'health-check-authenticate-to-failover-backend': True,
        'health-check-failover-url': 'https://%s:%s/failover-url?a=b&c=' % (
          cls._ipv4_address, cls._server_https_auth_port),
        'health-check-failover-https-url':
        'https://%s:%s/failover-https-url?a=b&c=' % (
          cls._ipv4_address, cls._server_https_auth_port),
      },
      'health-check-failover-url-ssl-proxy-verified': {
        'url': cls.backend_url,
        'health-check-timeout': 1,  # fail fast for test
        'health-check-interval': 1,  # fail fast for test
        'health-check': True,
        'health-check-http-path': '/health-check-failover-url-ssl-proxy'
        '-verified',
        'health-check-failover-url': cls.backend_https_url,
        'health-check-failover-ssl-proxy-verify': True,
        'health-check-failover-ssl-proxy-ca-crt':
        cls.test_server_ca.certificate_pem,
      },
      'health-check-failover-url-ssl-proxy-verify-unverified': {
        'url': cls.backend_url,
        'health-check-timeout': 1,  # fail fast for test
        'health-check-interval': 1,  # fail fast for test
        'health-check': True,
        'health-check-http-path': '/health-check-failover-url-ssl-proxy-verify'
        '-unverified',
        'health-check-failover-url': cls.backend_https_url,
        'health-check-failover-ssl-proxy-verify': True,
        'health-check-failover-ssl-proxy-ca-crt':
        cls.another_server_ca.certificate_pem,
      },
      'health-check-failover-url-ssl-proxy-verify-missing': {
        'url': cls.backend_url,
        'health-check-timeout': 1,  # fail fast for test
        'health-check-interval': 1,  # fail fast for test
        'health-check': True,
        'health-check-http-path': '/health-check-failover-url-ssl-proxy-verify'
        '-missing',
        'health-check-failover-url': cls.backend_https_url,
        'health-check-failover-ssl-proxy-verify': True,
      },
    }

  @classmethod
  def setUpAssertionDict(cls):
    backend = urllib.parse.urlparse(cls.backend_url).netloc
    cls.assertion_dict = {
      'health-check-disabled': """\
backend _health-check-disabled-http
  timeout server 12s
  timeout connect 5s
  retries 3
  server _health-check-disabled-backend-http %s""" % (backend,),
      'health-check-connect': """\
backend _health-check-connect-http
  timeout server 12s
  timeout connect 5s
  retries 3
  server _health-check-connect-backend-http %s   check inter 5s"""
      """ rise 1 fall 2
  timeout check 2s""" % (backend,),
      'health-check-custom': """\
backend _health-check-custom-http
  timeout server 12s
  timeout connect 5s
  retries 3
  server _health-check-custom-backend-http %s   check inter 15s"""
      """ rise 3 fall 7
  option httpchk POST /POST-path%%%%20to%%%%20be%%%%20encoded HTTP/1.0
  timeout check 7s""" % (backend,),
      'health-check-default': """\
backend _health-check-default-http
  timeout server 12s
  timeout connect 5s
  retries 3
  server _health-check-default-backend-http %s   check inter 5s"""
      """ rise 1 fall 2
  option httpchk GET / HTTP/1.1
  timeout check 2s""" % (backend, )
    }

  def _test(self, key):
    parameter_dict = self.assertSlaveBase(key)
    self.assertIn(
      self.assertion_dict[key],
      self._get_backend_haproxy_configuration()
    )
    result = fakeHTTPSResult(
      parameter_dict['domain'],
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

  def test_health_check_disabled(self):
    self._test('health-check-disabled')

  def test_health_check_default(self):
    self._test('health-check-default')

  def test_health_check_connect(self):
    self._test('health-check-connect')

  def test_health_check_custom(self):
    self._test('health-check-custom')

  def test_health_check_failover_url(self):
    parameter_dict = self.assertSlaveBase('health-check-failover-url')
    slave_parameter_dict = self.getSlaveParameterDictDict()[
      'health-check-failover-url']

    source_ip = '127.0.0.1'
    max_stale_age = 30
    max_age = int(max_stale_age / 2.)
    body_200 = 'Body 200' * 500
    body_failover = 'Failover response'
    cached_path = self.id()
    self.addCleanup(self._unhack_ats)
    self._hack_ats(max_stale_age)

    # Prerequisite for cache: setup failover backend with proper code
    # for normal access (not cached, typical scenario) and cached access
    # in order to check ATS behaviour
    for path in ['/failoverpath', '/' + cached_path]:
      for url in [
        'failover-url?a=b&c=',
        'failover-https-url?a=b&c='
      ]:
        result = requests.put(
          self.backend_url + url + path,
          headers={
            'X-Reply-Status-Code': '503',
            'X-Reply-Body': base64.b64encode(body_failover.encode()),
          })
        self.assertEqual(result.status_code, http.client.CREATED)

    def configureResult(status_code, body):
      backend_url = self.getSlaveParameterDictDict()[
        'health-check-failover-url']['https-url']
      result = requests.put(
        '/'.join([backend_url, cached_path]),
        headers={
          'X-Reply-Header-Cache-Control': 'max-age=%s, public' % (max_age,),
          'X-Reply-Status-Code': status_code,
          'X-Reply-Body': base64.b64encode(body.encode()),
          # drop Content-Length header to ensure
          # https://github.com/apache/trafficserver/issues/7880
          'X-Drop-Header': 'Content-Length',
        })
      self.assertEqual(result.status_code, http.client.CREATED)

    def checkResult(status_code, body):
      result = fakeHTTPSResult(
        parameter_dict['domain'], cached_path,
        source_ip=source_ip
      )
      self.assertEqual(result.status_code, status_code)
      self.assertEqual(result.text, body)

    # check normal access...
    result = fakeHTTPResult(parameter_dict['domain'], '/path')
    self.assertEqualResultJson(result, 'Path', '/url/path')
    result = fakeHTTPSResult(parameter_dict['domain'], '/path')
    self.assertEqual(self.certificate_pem, der2pem(result.peercert))
    self.assertEqualResultJson(result, 'Path', '/https-url/path')
    # ...and cached result, also in order to store it in the cache
    configureResult('200', body_200)
    checkResult(http.client.OK, body_200)

    # start replying with bad status code
    result = requests.put(
      self.backend_url + slave_parameter_dict[
        'health-check-http-path'].strip('/'),
      headers={'X-Reply-Status-Code': '502'})
    self.assertEqual(result.status_code, http.client.CREATED)

    def restoreBackend():
      result = requests.put(
        self.backend_url + slave_parameter_dict[
          'health-check-http-path'].strip('/'),
        headers={})
      self.assertEqual(result.status_code, http.client.CREATED)
    self.addCleanup(restoreBackend)

    time.sleep(3)  # > health-check-timeout + health-check-interval

    # check simple failover
    result = fakeHTTPSResult(parameter_dict['domain'], '/failoverpath')
    self.assertEqual(self.certificate_pem, der2pem(result.peercert))
    self.assertEqual(result.status_code, http.client.SERVICE_UNAVAILABLE)
    self.assertEqual(result.text, body_failover)

    self.assertLastLogLineRegexp(
      '_health-check-failover-url_backend_log',
      r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+ '
      r'\[\d{2}\/.{3}\/\d{4}\:\d{2}\:\d{2}\:\d{2}.\d{3}\] '
      r'https-backend _health-check-failover-url-https-failover'
      r'\/_health-check-failover-url-backend-https '
      r'\d+/\d+\/\d+\/\d+\/\d+ '
      r'503 \d+ - - ---- '
      r'\d+\/\d+\/\d+\/\d+\/\d+ \d+\/\d+ '
      r'"GET /failoverpath HTTP/1.1"'
    )

    result = fakeHTTPResult(parameter_dict['domain'], '/failoverpath')
    self.assertEqual(result.status_code, http.client.SERVICE_UNAVAILABLE)
    self.assertEqual(result.text, body_failover)
    self.assertLastLogLineRegexp(
      '_health-check-failover-url_backend_log',
      r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+ '
      r'\[\d{2}\/.{3}\/\d{4}\:\d{2}\:\d{2}\:\d{2}.\d{3}\] '
      r'http-backend _health-check-failover-url-http-failover'
      r'\/_health-check-failover-url-backend-http '
      r'\d+/\d+\/\d+\/\d+\/\d+ '
      r'503 \d+ - - ---- '
      r'\d+\/\d+\/\d+\/\d+\/\d+ \d+\/\d+ '
      r'"GET /failoverpath HTTP/1.1"'
    )

    # It's time to check that ATS gives cached result, even if failover
    # backend is used
    checkResult(http.client.OK, body_200)
    # interesting moment, time is between max_age and max_stale_age, triggers
    # https://github.com/apache/trafficserver/issues/7880
    # which is stale-if-error simulated by ATS while using failover backend
    time.sleep(max_age + 1 - 3)
    checkResult(http.client.OK, body_200)
    # max_stale_age passed, time to return 502 with failover url
    time.sleep(max_stale_age + 2 - 3)
    checkResult(http.client.SERVICE_UNAVAILABLE, body_failover)

  def test_health_check_failover_url_netloc_list(self):
    parameter_dict = self.assertSlaveBase(
      'health-check-failover-url-netloc-list')
    slave_parameter_dict = self.getSlaveParameterDictDict()[
      'health-check-failover-url-netloc-list']
    # check normal access
    result = fakeHTTPSResult(parameter_dict['domain'], '/path')
    self.assertNotIn('X-Backend-Identification', result.headers)
    # start replying with bad status code
    result = requests.put(
      self.backend_url + slave_parameter_dict[
        'health-check-http-path'].strip('/'),
      headers={'X-Reply-Status-Code': '502'})
    self.assertEqual(result.status_code, http.client.CREATED)
    self.assertEqual(result.status_code, http.client.CREATED)

    def restoreBackend():
      result = requests.put(
        self.backend_url + slave_parameter_dict[
          'health-check-http-path'].strip('/'),
        headers={})
      self.assertEqual(result.status_code, http.client.CREATED)
    self.addCleanup(restoreBackend)

    time.sleep(3)  # > health-check-timeout + health-check-interval
    # check failover, uses netloc
    result = fakeHTTPSResult(parameter_dict['domain'], '/path')
    self.assertEqual(
      result.headers['X-Backend-Identification'],
      'netloc'
    )

  def test_health_check_failover_url_auth_to_backend(self):
    parameter_dict = self.assertSlaveBase(
      'health-check-failover-url-auth-to-backend')
    slave_parameter_dict = self.getSlaveParameterDictDict()[
      'health-check-failover-url-auth-to-backend']

    self.startAuthenticatedServerProcess()
    self.addCleanup(self.stopAuthenticatedServerProcess)
    # assert that you can't fetch nothing without key
    try:
      requests.get(self.backend_https_auth_url, verify=False)
    except Exception:
      pass
    else:
      self.fail(
        'Access to %r shall be not possible without certificate' % (
          self.backend_https_auth_url,))
    # check normal access
    result = fakeHTTPResult(parameter_dict['domain'], '/path')
    self.assertEqualResultJson(result, 'Path', '/url/path')
    self.assertNotIn('X-Backend-Identification', result.headers)
    result = fakeHTTPSResult(parameter_dict['domain'], '/path')
    self.assertEqual(self.certificate_pem, der2pem(result.peercert))
    self.assertEqualResultJson(result, 'Path', '/https-url/path')
    self.assertNotIn('X-Backend-Identification', result.headers)

    # start replying with bad status code
    result = requests.put(
      self.backend_url + slave_parameter_dict[
        'health-check-http-path'].strip('/'),
      headers={'X-Reply-Status-Code': '502'})
    self.assertEqual(result.status_code, http.client.CREATED)

    time.sleep(3)  # > health-check-timeout + health-check-interval

    result = fakeHTTPSResult(parameter_dict['domain'], '/failoverpath')
    self.assertEqual(self.certificate_pem, der2pem(result.peercert))
    self.assertEqualResultJson(
      result, 'Path', '/failover-https-url?a=b&c=/failoverpath')
    self.assertEqual(
      'Auth Backend', result.headers['X-Backend-Identification'])

    result = fakeHTTPResult(parameter_dict['domain'], '/failoverpath')
    self.assertEqualResultJson(
      result, 'Path', '/failover-url?a=b&c=/failoverpath')
    self.assertEqual(
      'Auth Backend', result.headers['X-Backend-Identification'])

  def test_health_check_failover_url_ssl_proxy_verified(self):
    parameter_dict = self.assertSlaveBase(
      'health-check-failover-url-ssl-proxy-verified')
    slave_parameter_dict = self.getSlaveParameterDictDict()[
      'health-check-failover-url-ssl-proxy-verified']

    # check normal access
    result = fakeHTTPSResult(parameter_dict['domain'], '/path')
    self.assertEqual(self.certificate_pem, der2pem(result.peercert))
    self.assertEqualResultJson(result, 'Path', '/path')

    # start replying with bad status code
    result = requests.put(
      self.backend_url + slave_parameter_dict[
        'health-check-http-path'].strip('/'),
      headers={'X-Reply-Status-Code': '502'})
    self.assertEqual(result.status_code, http.client.CREATED)

    time.sleep(3)  # > health-check-timeout + health-check-interval

    result = fakeHTTPSResult(
      parameter_dict['domain'], '/test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    self.assertEqualResultJson(result, 'Path', '/test-path')

  def test_health_check_failover_url_ssl_proxy_unverified(self):
    parameter_dict = self.assertSlaveBase(
      'health-check-failover-url-ssl-proxy-verify-unverified')
    slave_parameter_dict = self.getSlaveParameterDictDict()[
      'health-check-failover-url-ssl-proxy-verify-unverified']

    # check normal access
    result = fakeHTTPSResult(parameter_dict['domain'], '/path')
    self.assertEqual(self.certificate_pem, der2pem(result.peercert))
    self.assertEqualResultJson(result, 'Path', '/path')

    # start replying with bad status code
    result = requests.put(
      self.backend_url + slave_parameter_dict[
        'health-check-http-path'].strip('/'),
      headers={'X-Reply-Status-Code': '502'})
    self.assertEqual(result.status_code, http.client.CREATED)

    time.sleep(3)  # > health-check-timeout + health-check-interval

    result = fakeHTTPSResult(
      parameter_dict['domain'], '/test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    # as ssl proxy verification failed, service is unavailable
    self.assertEqual(result.status_code, http.client.SERVICE_UNAVAILABLE)

  def test_health_check_failover_url_ssl_proxy_missing(self):
    parameter_dict = self.assertSlaveBase(
      'health-check-failover-url-ssl-proxy-verify-missing')
    slave_parameter_dict = self.getSlaveParameterDictDict()[
      'health-check-failover-url-ssl-proxy-verify-missing']

    # check normal access
    result = fakeHTTPSResult(parameter_dict['domain'], '/path')
    self.assertEqual(self.certificate_pem, der2pem(result.peercert))
    self.assertEqualResultJson(result, 'Path', '/path')

    # start replying with bad status code
    result = requests.put(
      self.backend_url + slave_parameter_dict[
        'health-check-http-path'].strip('/'),
      headers={'X-Reply-Status-Code': '502'})
    self.assertEqual(result.status_code, http.client.CREATED)

    time.sleep(3)  # > health-check-timeout + health-check-interval

    result = fakeHTTPSResult(
      parameter_dict['domain'], '/test-path')

    self.assertEqual(
      self.certificate_pem,
      der2pem(result.peercert))

    # as ssl proxy verification failed, service is unavailable
    self.assertEqual(result.status_code, http.client.SERVICE_UNAVAILABLE)


class TestSlaveHttp3(SlaveHttpFrontendTestCase, TestDataMixin, AtsMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'domain': 'example.com',
      'port': HTTPS_PORT,
      'plain_http_port': HTTP_PORT,
      'kedifa_port': KEDIFA_PORT,
      'caucase_port': CAUCASE_PORT,
      'request-timeout': '12',
      'enable-http3': 'True',
      'http3-port': HTTPS_PORT,
    }

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'url': {
        'url': cls.backend_url,
      },
      'http2-false': {
        'url': cls.backend_url,
        'enable-http2': False
      },
      'http3-false': {
        'url': cls.backend_url,
        'enable-http3': False
      },
      'http3-true-http2-false': {
        'url': cls.backend_url,
        'enable-http2': False,
        'enable-http3': True,
      },
    }

  def test_url(self):
    parameter_dict = self.assertSlaveBase('url')
    result = mimikra.get(
      'https://%(domain)s:%(https_port)s/' % dict(
        domain=parameter_dict['domain'], https_port=HTTPS_PORT),
      resolve_all={HTTPS_PORT: TEST_IP},
      verify=False,
      http3_only=True
    )
    self.assertTrue(result.ok)
    self.assertEqual(result.protocol, '3')
    result = mimikra.get(
      'https://%(domain)s:%(https_port)s/' % dict(
        domain=parameter_dict['domain'], https_port=HTTPS_PORT),
      resolve_all={HTTPS_PORT: TEST_IP},
      verify=False,
    )
    self.assertTrue(result.ok)
    self.assertEqual(result.protocol, '3')
    self.assertEqual(
      result.headers['alt-svc'],
      'h3=":%s"; ma=3600' % (HTTPS_PORT,)
    )
    self.assertEqual(
      result.headers['alternate-protocol'],
      '%s:quic' % (HTTPS_PORT,)
    )

  def test_http2_false(self):
    parameter_dict = self.assertSlaveBase('http2-false')
    self.assertEqual(
      '0',
      mimikra.get(
        'https://%(domain)s:%(https_port)s/' % dict(
          domain=parameter_dict['domain'], https_port=HTTPS_PORT),
        resolve_all={HTTPS_PORT: TEST_IP},
        verify=False,
        http3_only=True
      ).protocol)
    result = mimikra.get(
      'https://%(domain)s:%(https_port)s/' % dict(
        domain=parameter_dict['domain'], https_port=HTTPS_PORT),
      resolve_all={HTTPS_PORT: TEST_IP},
      verify=False,
    )
    self.assertEqual('1', result.protocol)
    self.assertNotIn('alt-svc', result.headers)
    self.assertNotIn('alternate-protocol', result.headers)

  def test_http3_false(self):
    parameter_dict = self.assertSlaveBase('http3-false')
    self.assertEqual(
      '0',
      mimikra.get(
        'https://%(domain)s:%(https_port)s/' % dict(
          domain=parameter_dict['domain'], https_port=HTTPS_PORT),
        resolve_all={HTTPS_PORT: TEST_IP},
        verify=False,
        http3_only=True
      ).protocol)
    result = mimikra.get(
      'https://%(domain)s:%(https_port)s/' % dict(
        domain=parameter_dict['domain'], https_port=HTTPS_PORT),
      resolve_all={HTTPS_PORT: TEST_IP},
      verify=False,
      http3=True,
    )
    self.assertEqual('2', result.protocol)
    self.assertNotIn('alt-svc', result.headers)
    self.assertNotIn('alternate-protocol', result.headers)

  def test_http3_true_http2_false(self):
    parameter_dict = self.assertSlaveBase('http3-true-http2-false')
    self.assertEqual(
      '0',
      mimikra.get(
        'https://%(domain)s:%(https_port)s/' % dict(
          domain=parameter_dict['domain'], https_port=HTTPS_PORT),
        resolve_all={HTTPS_PORT: TEST_IP},
        verify=False,
        http3_only=True
      ).protocol)
    result = mimikra.get(
      'https://%(domain)s:%(https_port)s/' % dict(
        domain=parameter_dict['domain'], https_port=HTTPS_PORT),
      resolve_all={HTTPS_PORT: TEST_IP},
      verify=False,
      http3=True,
    )
    self.assertEqual('1', result.protocol)
    self.assertNotIn('alt-svc', result.headers)
    self.assertNotIn('alternate-protocol', result.headers)


if __name__ == '__main__':
  class HTTP6Server(ThreadedHTTPServer):
    address_family = socket.AF_INET6
  ip, port = sys.argv[1], int(sys.argv[2])
  if ':' in ip:
    klass = HTTP6Server
    url_template = 'http://[%s]:%s/'
  else:
    klass = ThreadedHTTPServer
    url_template = 'http://%s:%s/'

  server = klass((ip, port), TestHandler)
  print((url_template % server.server_address[:2]))
  server.serve_forever()
