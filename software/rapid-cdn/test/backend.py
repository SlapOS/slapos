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
import http.client
import json
import logging
import os
import ssl
import sys
import time


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  pass


class ConfigurationReplyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return '<%i>' % (len(obj))
        elif isinstance(obj, http.client.HTTPMessage):
            reply = ''
            for k, v in obj.items():
              reply += '%r: %r' % (k, v)
            return reply
        return json.JSONEncoder.default(self, obj)


class TestHandler(BaseHTTPRequestHandler):
  configuration = {}
  DEFAULT_CONFIGURATION = {
   'Status-Code': '200',
   'Protocol-Version': 'HTTP/1.0',
   'Response-Timeout': '0',
   'Header-Timeout': '0',
   'Body-Timeout': '0',
  }

  log_message = logging.getLogger(__name__ + '.TestHandler').info

  def wfile_write(self, *args, **kwargs):
    try:
      self.wfile.write(*args, **kwargs)
    except ConnectionResetError:
      # clients can drop connection during sending data, ignore it
      pass

  # Special verb for internal usage
  def do_REMOVE(self):
    config = self.configuration.pop(self.path, None)
    # also drop any variant configs registered for this path, so a test that
    # registered several Vary variants is fully cleaned with a single REMOVE
    for k in [
        k for k in list(self.configuration)
        if isinstance(k, tuple) and len(k) == 2 and k[0] == self.path]:
      self.configuration.pop(k, None)
    if config is None:
      self.send_response(204)
      self.end_headers()
    else:
      self.send_response(200)
      self.send_header("Content-Type", "application/json")
      self.end_headers()
      self.wfile_write(json.dumps({self.path: config}, indent=2))

  # Special verb for internal usage
  def do_CONFIG(self):
    config = self.DEFAULT_CONFIGURATION.copy()
    incoming_headers = http.client.HTTPMessage()
    config_header = 'X-Config-'
    config_header_header = 'X-Config-Reply-Header-'
    config_header_vary_key = 'X-Config-Vary-Key'
    config_header_vary_value = 'X-Config-Vary-Value'
    vary_key = self.headers.get(config_header_vary_key)
    vary_value = self.headers.get(config_header_vary_value)
    for header_name, header_value in self.headers.items():
      if header_name.startswith(config_header_header):
        incoming_headers.add_header(
          header_name[len(config_header_header):], header_value)
      elif header_name in (config_header_vary_key, config_header_vary_value):
        # variant selector — stored as the configuration's dict key, not as
        # part of the response config itself
        continue
      elif header_name.startswith(config_header):
        config[header_name[len(config_header):]] = header_value
    if 'X-Config-Body' not in self.headers:
      config['Body'] = self.rfile.read(int(self.headers.get(
        'Content-Length', '0')))
    if self.headers.get('X-Config-Global', '0') == '1':
      base_path = '*'
    else:
      base_path = self.path
    if vary_key is not None and vary_value is not None:
      # For multi-header variants (e.g. Vary: Accept-Encoding, Accept-Language)
      # both headers carry comma-separated lists of equal length:
      #   X-Config-Vary-Key:   Accept-Encoding, Accept-Language
      #   X-Config-Vary-Value: gzip, en
      # For a single-header variant the value may itself contain commas
      # (e.g. an expected request header `Accept-Encoding: br, gzip, deflate`),
      # so we only split when the key contains a comma.
      if ',' in vary_key:
        vary_key_list = [k.strip() for k in vary_key.split(',')]
        vary_value_list = [v.strip() for v in vary_value.split(',')]
        assert len(vary_key_list) == len(vary_value_list), \
          'X-Config-Vary-Key / X-Config-Vary-Value length mismatch'
      else:
        vary_key_list = [vary_key]
        vary_value_list = [vary_value]
      variant = tuple(sorted(zip(vary_key_list, vary_value_list)))
      key = (base_path, variant)
    else:
      key = base_path
    self.send_response(201)
    self.send_header("Content-Type", "application/json")
    self.configuration[key] = {
      'headers': incoming_headers,
      'configuration': config
    }
    reply = {str(key): dict(self.configuration[key])}
    response = json.dumps(
      reply, indent=2, cls=ConfigurationReplyEncoder).encode()
    self.send_header('Content-Length', len(response))
    self.end_headers()
    self.wfile_write(response)

  def do_POST(self):
    return self.do_GET()

  def do_PUT(self):
    return self.do_GET()

  def do_DELETE(self):
    return self.do_GET()

  def do_PATCH(self):
    return self.do_GET()

  def do_HEAD(self):
    return self.do_GET()

  def do_OPTIONS(self):
    return self.do_GET()

  def do_TRACE(self):
    return self.do_GET()

  def do_CONNECT(self):
    return self.do_GET()

  def do_GET(self):
    def generateDefaultResponse():
      header_dict = {}
      for header in list(self.headers.keys()):
        content = self.headers.get_all(header)
        if len(content) == 0:
          header_dict[header] = None
        elif len(content) == 1:
          header_dict[header] = content[0]
        else:
          header_dict[header] = content

      return json.dumps(
        {
          'Path': self.path,
          'Incoming Headers': header_dict,
          'Verb': self.command
        },
        indent=2).encode()

    # Variant lookup: any (path, ((k1, v1), (k2, v2), ...)) entry whose every
    # (k, v) pair matches the corresponding request header is a candidate;
    # the most-specific candidate (largest variant tuple) wins over the
    # path's plain (and the '*' global) config.
    candidates = [
      k for k in list(self.configuration)
      if isinstance(k, tuple) and len(k) == 2 and k[0] == self.path
      and all(self.headers.get(kk) == vv for kk, vv in k[1])
    ]
    if candidates:
      candidates.sort(key=lambda k: len(k[1]), reverse=True)
      config = self.configuration[candidates[0]]
    else:
      config = self.configuration.get(
        self.path, self.configuration.get('*', None))
    if config is None:
      self.send_response(404)
      response = generateDefaultResponse()
      self.send_header('Content-Length', len(response))
      self.send_header('Content-Type', 'application/json')
      self.end_headers()
      self.wfile_write(response)
      return

    self.protocol_version = config['configuration']['Protocol-Version']
    time.sleep(int(config['configuration']['Response-Timeout']))
    self.send_response_only(int(config['configuration']['Status-Code']))
    if isinstance(config['configuration']['Body'], str):
      if config['configuration']['Body'] == 'calculate':
        body = generateDefaultResponse()
        if 'Content-Type' not in config['headers']:
          config['headers']['Content-Type'] = 'application/json'
      else:
        body = config['configuration']['Body'].encode()
    else:
      body = config['configuration']['Body']
    time.sleep(int(config['configuration']['Header-Timeout']))
    for header, value in config['headers'].items():
      for header_type in ['Date', 'Last-Modified']:
        if header == header_type:
          if value == 'now':
            value = self.date_time_string()
      if header == 'Expires':
        if value.startswith('delta:'):
          value = self.date_time_string(
            time.time() + float(value.split(':')[1])
          )
      if header == 'Content-Length':
        if value == 'calculate':
          value = '%s' % (len(body),)
      self.send_header(header, value)
    self.end_headers()
    time.sleep(int(config['configuration']['Body-Timeout']))
    self.wfile_write(body)


def server_https_weak_method(ip, port):
  try:
    server_https_weak = ThreadedHTTPServer(
      (ip, port),
      TestHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1
    context.maximum_version = ssl.TLSVersion.TLSv1
    context.load_cert_chain(
      os.path.join(
        os.path.dirname(
          os.path.realpath(__file__)), 'test_data', 'sha1-2048.pem'))
    server_https_weak.socket = context.wrap_socket(
      server_https_weak.socket, server_side=True)
    if not isinstance(server_https_weak.socket, ssl.SSLSocket):
      raise RuntimeError(
        'server_https_weak: wrap_socket did not return an SSLSocket on '
        '%s:%s; refusing to serve plain HTTP on a weak-SSL port' % (ip, port))
    sys.stderr.write(
      'server_https_weak READY tls=on ip=%s port=%s\n' % (ip, port))
    sys.stderr.flush()
    server_https_weak.serve_forever()
  except BaseException as e:
    sys.stderr.write(
      'server_https_weak FAILED ip=%s port=%s: %r\n' % (ip, port, e))
    sys.stderr.flush()
    raise


if __name__ == '__main__':
  server_https_weak_method(sys.argv[1], int(sys.argv[2]))
