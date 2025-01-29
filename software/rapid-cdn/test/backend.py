##############################################################################
#
# Copyright (c) 2025 Nexedi SA and Contributors. All Rights Reserved.
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

from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from socketserver import ThreadingMixIn
import base64
import gzip
import io
import json
import logging
import os
import random
import ssl
import string
import sys
import time


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  pass


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


def server_https_weak_method(ip, port):
  server_https_weak = ThreadedHTTPServer(
    (ip, port),
    TestHandler)
  context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
  context.load_cert_chain(
    os.path.join(
      os.path.dirname(
        os.path.realpath(__file__)), 'test_data', 'sha1-2048.pem'))
  server_https_weak.socket = context.wrap_socket(
    server_https_weak.socket, server_side=True)
  server_https_weak.serve_forever()


if __name__ == '__main__':
  server_https_weak_method(sys.argv[1], int(sys.argv[2]))
