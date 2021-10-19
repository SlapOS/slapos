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

import os
import json
# import multiprocessing
# import ssl
from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import time
# import tempfile
import StringIO
import gzip
import base64
import socket
import sys
import random
import string
import datetime

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def createKey():
  key = rsa.generate_private_key(
    public_exponent=65537, key_size=2048, backend=default_backend())
  key_pem = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
  )
  return key, key_pem


# comes from https://stackoverflow.com/a/21788372/9256748
def patch_broken_pipe_error():
    """Monkey Patch BaseServer.handle_error to not write
    a stacktrace to stderr on broken pipe.
    https://stackoverflow.com/a/7913160"""
    from SocketServer import BaseServer

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


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  pass


class TestHandler(BaseHTTPRequestHandler):
  identification = None
  configuration = {}

  def log_message(self, *args):
    if os.environ.get('SLAPOS_TEST_DEBUG'):
      return BaseHTTPRequestHandler.log_message(self, *args)
    else:
      return

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
    config = {
      'status_code': self.headers.dict.get('x-reply-status-code', '200')
    }
    prefix = 'x-reply-header-'
    length = len(prefix)
    for key, value in self.headers.dict.items():
      if key.startswith(prefix):
        header = '-'.join([q.capitalize() for q in key[length:].split('-')])
        config[header] = value.strip()

    if 'x-reply-body' in self.headers.dict:
      config['Body'] = base64.b64decode(self.headers.dict['x-reply-body'])

    config['X-Drop-Header'] = self.headers.dict.get('x-drop-header')
    self.configuration[self.path] = config

    self.send_response(201)
    self.send_header("Content-Type", "application/json")
    self.end_headers()
    self.wfile.write(json.dumps({self.path: config}, indent=2))

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
      for header in (self.headers.dict.get('x-drop-header') or '').split():
        drop_header_list.append(header)
      response = None
      status_code = 200
      timeout = int(self.headers.dict.get('timeout', '0'))
      if 'x-maximum-timeout' in self.headers.dict:
        maximum_timeout = int(self.headers.dict['x-maximum-timeout'])
        timeout = random.randrange(maximum_timeout)
      if 'x-response-size' in self.headers.dict:
        min_response, max_response = [
          int(q) for q in self.headers.dict['x-response-size'].split(' ')]
        reponse_size = random.randrange(min_response, max_response)
        response = ''.join(
          random.choice(string.lowercase) for x in range(reponse_size))
      compress = int(self.headers.dict.get('compress', '0'))
      header_dict = {}
      prefix = 'x-reply-header-'
      length = len(prefix)
      for key, value in self.headers.dict.items():
        if key.startswith(prefix):
          header = '-'.join([q.capitalize() for q in key[length:].split('-')])
          header_dict[header] = value.strip()
    if response is None:
      if 'x-reply-body' not in self.headers.dict:
        response = {
          'Path': self.path,
          'Incoming Headers': self.headers.dict
        }
        response = json.dumps(response, indent=2)
      else:
        response = base64.b64decode(self.headers.dict['x-reply-body'])

    time.sleep(timeout)
    self.send_response(status_code)

    for key, value in header_dict.items():
      self.send_header(key, value)

    if self.identification is not None:
      self.send_header('X-Backend-Identification', self.identification)

    if 'Content-Type' not in drop_header_list:
      self.send_header("Content-Type", "application/json")
    if 'Set-Cookie' not in drop_header_list:
      self.send_header('Set-Cookie', 'secured=value;secure')
      self.send_header('Set-Cookie', 'nonsecured=value')

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

# class HttpFrontendTestCase(SlapOSInstanceTestCase):
#  @classmethod
#  def prepareCertificate(cls):
#    cls.another_server_ca = CertificateAuthority("Another Server Root CA")
#    cls.test_server_ca = CertificateAuthority("Test Server Root CA")
#    key, key_pem, csr, csr_pem = createCSR(
#      "testserver.example.com", cls._ipv4_address)
#    _, cls.test_server_certificate_pem = cls.test_server_ca.signCSR(csr)
#
#    cls.test_server_certificate_file = tempfile.NamedTemporaryFile(
#      delete=False
#    )
#
#    cls.test_server_certificate_file.write(
#        cls.test_server_certificate_pem + key_pem
#      )
#    cls.test_server_certificate_file.close()
#
#  def startServerProcess(cls):
#    server = ThreadedHTTPServer(
#      (cls._ipv4_address, cls._server_http_port),
#      TestHandler)
#
#    server_https = ThreadedHTTPServer(
#      (cls._ipv4_address, cls._server_https_port),
#      TestHandler)
#
#    server_https.socket = ssl.wrap_socket(
#      server_https.socket,
#      certfile=cls.test_server_certificate_file.name,
#      server_side=True)
#
#    cls.backend_url = 'http://%s:%s/' % server.server_address
#    cls.server_process = multiprocessing.Process(
#      target=server.serve_forever, name='HTTPServer')
#    cls.server_process.start()
#    cls.logger.debug('Started process %s' % (cls.server_process,))
#
#    cls.backend_https_url = 'https://%s:%s/' % server_https.server_address
#    cls.server_https_process = multiprocessing.Process(
#      target=server_https.serve_forever, name='HTTPSServer')
#    cls.server_https_process.start()
#    cls.logger.debug('Started process %s' % (cls.server_https_process,))
#
#  @classmethod
#  def cleanUpCertificate(cls):
#    if getattr(cls, 'test_server_certificate_file', None) is not None:
#      os.unlink(cls.test_server_certificate_file.name)
#
#  @classmethod
#  def stopServerProcess(cls):
#    for server in ['server_process', 'server_https_process']:
#      process = getattr(cls, server, None)
#      if process is not None:
#        cls.logger.debug('Stopping process %s' % (process,))
#        process.join(10)
#        process.terminate()
#        time.sleep(0.1)
#        if process.is_alive():
#          cls.logger.warning(
#            'Process %s still alive' % (process, ))
#
#  def startAuthenticatedServerProcess(self):
#    master_parameter_dict = self.parseConnectionParameterDict()
#    caucase_url = master_parameter_dict['backend-client-caucase-url']
#    ca_certificate = requests.get(caucase_url + '/cas/crt/ca.crt.pem')
#    assert ca_certificate.status_code == httplib.OK
#    ca_certificate_file = os.path.join(
#      self.working_directory, 'ca-backend-client.crt.pem')
#    with open(ca_certificate_file, 'w') as fh:
#      fh.write(ca_certificate.text)
#
#    class OwnTestHandler(TestHandler):
#      identification = 'Auth Backend'
#
#    server_https_auth = ThreadedHTTPServer(
#      (self._ipv4_address, self._server_https_auth_port),
#      OwnTestHandler)
#
#    server_https_auth.socket = ssl.wrap_socket(
#      server_https_auth.socket,
#      certfile=self.test_server_certificate_file.name,
#      cert_reqs=ssl.CERT_REQUIRED,
#      ca_certs=ca_certificate_file,
#      server_side=True)
#
#    self.backend_https_auth_url = 'https://%s:%s/' \
#        % server_https_auth.server_address
#
#    self.server_https_auth_process = multiprocessing.Process(
#      target=server_https_auth.serve_forever, name='HTTPSServerAuth')
#    self.server_https_auth_process.start()
#    self.logger.debug('Started process %s' % (self.server_https_auth_process,))
#
#  def stopAuthenticatedServerProcess(self):
#    self.logger.debug('Stopping process %s' % (
#      self.server_https_auth_process,))
#    self.server_https_auth_process.join(10)
#    self.server_https_auth_process.terminate()
#    time.sleep(0.1)
#    if self.server_https_auth_process.is_alive():
#      self.logger.warning(
#        'Process %s still alive' % (self.server_https_auth_process, ))
#
#
#  @classmethod
#  def _cleanup(cls, snapshot_name):
#    cls.cleanUpCertificate()
#    cls.stopServerProcess()
#    super(HttpFrontendTestCase, cls)._cleanup(snapshot_name)
#
#  @classmethod
#  def setUpClass(cls):
#    try:
#      cls.createWildcardExampleComCertificate()
#      cls.prepareCertificate()
#      # find ports once to be able startServerProcess many times
#      cls._server_http_port = findFreeTCPPort(cls._ipv4_address)
#      cls._server_https_port = findFreeTCPPort(cls._ipv4_address)
#      cls._server_https_auth_port = findFreeTCPPort(cls._ipv4_address)
#      cls.startServerProcess()
#    except BaseException:
#      cls.logger.exception("Error during setUpClass")
#      cls._cleanup("{}.{}.setUpClass".format(cls.__module__, cls.__name__))
#      cls.setUp = lambda self: self.fail('Setup Class failed.')
#      raise
#
#    super(HttpFrontendTestCase, cls).setUpClass()
#
#    try:
#      # expose instance directory
#      cls.instance_path = cls.slap.instance_directory
#      # expose software directory, extract from found computer partition
#      cls.software_path = os.path.realpath(os.path.join(
#          cls.computer_partition_root_path, 'software_release'))
#      # do working directory
#      cls.working_directory = os.path.join(os.path.realpath(
#          os.environ.get(
#              'SLAPOS_TEST_WORKING_DIR',
#              os.path.join(os.getcwd(), '.slapos'))),
#          'caddy-frontend-test')
#      if not os.path.isdir(cls.working_directory):
#        os.mkdir(cls.working_directory)
#      cls.setUpMaster()
#      cls.waitForCaddy()
#    except BaseException:
#      cls.logger.exception("Error during setUpClass")
#      # "{}.{}.setUpClass".format(cls.__module__, cls.__name__) is already used
#      # by SlapOSInstanceTestCase.setUpClass so we use another name for
#      # snapshot, to make sure we don't store another snapshot in same
#      # directory.
#      cls._cleanup("{}.SlaveHttpFrontendTestCase.{}.setUpClass".format(
#        cls.__module__, cls.__name__))
#      cls.setUp = lambda self: self.fail('Setup Class failed.')
#      raise


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
  print url_template % server.server_address[:2]
  server.serve_forever()
