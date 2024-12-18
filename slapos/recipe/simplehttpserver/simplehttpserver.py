# -*- coding: utf-8 -*-
from six.moves.SimpleHTTPServer import SimpleHTTPRequestHandler
from six.moves.socketserver import TCPServer

import cgi
import contextlib
import errno
import logging
import os
import ssl
import socket

from slapos.util import str2bytes

from . import issubpathof


class ServerHandler(SimpleHTTPRequestHandler):
  base_path = None # set by run
  restrict_write = True # set by run
  _additional_logs = None

  @contextlib.contextmanager
  def _log_extra(self, msg):
    self._additional_logs = msg
    try:
      yield
    finally:
      self._additional_logs = None

  def _log(self, level, msg, *args):
    if self._additional_logs:
      msg += self._additional_logs
    logging.log(level, '%s - - ' + msg, self.client_address[0], *args)

  def log_message(self, msg, *args):
    self._log(logging.INFO, msg, *args)

  def log_error(self, msg, *args):
    self._log(logging.ERROR, msg, *args)

  def log_request(self, *args):
    with self._log_extra('\n' + str(self.headers)):
      SimpleHTTPRequestHandler.log_request(self, *args)

  def respond(self, code=200, type='text/html'):
    self.send_response(code)
    self.send_header("Content-type", type)
    self.end_headers()

  def restrictedWriteAccess(self):
    if self.restrict_write and self.command not in ('GET', 'HEAD'):
      # no write access
      self.respond(403)
      self.wfile.write(b"Forbidden")
      return True
    return False

  def do_POST(self):
    """Write to a file on the server.

    request keys:
      path: the path of the file
      content: content of the file
      clear: (0|1 default 1) overwrite the file if 1

    request can be encoded as application/x-www-form-urlencoded or multipart/form-data
    """
    if self.restrictedWriteAccess():
      return

    form = cgi.FieldStorage(
      fp=self.rfile,
      headers=self.headers,
      environ={'REQUEST_METHOD': 'POST',
               'CONTENT_TYPE': self.headers['Content-Type']}
    )

    file_content = form['content'].value
    file_path = form['path'].value
    if form['content'].file:
      # post data as multipart/form-data , values are bytes
      file_path = file_path.decode('utf-8')
    else:
      # application/x-www-form-urlencoded , values are str
      file_content = file_content.encode('utf-8')
    file_open_mode = 'wb' if ('clear' in form and form['clear'].value in ('1', b'1')) else 'ab'

    self.writeFile(file_path, file_content, file_open_mode)

  def writeFile(self, filename, content, method='ab'):
    file_path = os.path.abspath(os.path.join(self.base_path, filename))
    # Check writing there is allowed
    if not issubpathof(file_path, self.base_path):
      self.respond(403, 'text/plain')
      self.wfile.write(b"Forbidden")
      return
    # Create missing directories if needed
    try:
      os.makedirs(os.path.dirname(file_path))
    except OSError as exception:
      if exception.errno != errno.EEXIST:
        self.log_error('Failed to create file in %s. The error is \n%s',
          file_path, exception)
    # Write content to file
    self.log_message('Writing received content to file %s', file_path)
    try:
      with open(file_path, method) as myfile:
        myfile.write(content)
        self.log_message('Done.')
    except IOError as e:
      self.log_error(
        'Something happened while processing \'writeFile\'. The message is %s',
        e)
    self.respond(200, type=self.headers['Content-Type'])
    self.wfile.write(b"Content written to %s" % str2bytes(filename))


def run(args):
  # minimal web server. serves files relative to the current directory.
  logging.basicConfig(
      format="%(asctime)s %(levelname)s - %(message)s",
      filename=args['log-file'],
      level=logging.INFO)

  address = args['address']
  cwd = args['cwd']

  os.chdir(cwd)

  Handler = ServerHandler
  Handler.base_path = cwd
  Handler.restrict_write = not args['allow-write']

  try:
    host, port = address
    family, _, _, _, _ = socket.getaddrinfo(host, port)[0]
  except ValueError:
    family = socket.AF_UNIX

  class Server(TCPServer):
    allow_reuse_address = 1 # for tests, HTTPServer in stdlib sets it too
    address_family = family

  httpd = Server(address, Handler)

  certfile = args['cert-file']
  if certfile: # keyfile == None signifies key is in certfile
    PROTOCOL_TLS_SERVER = getattr(ssl, 'PROTOCOL_TLS_SERVER', None)
    if PROTOCOL_TLS_SERVER:
      sslcontext = ssl.SSLContext(PROTOCOL_TLS_SERVER)
      sslcontext.load_cert_chain(certfile, args['key-file'])
      httpd.socket = sslcontext.wrap_socket(httpd.socket, server_side=True)
    else: # BBB Py2, Py<3.6
      httpd.socket = ssl.wrap_socket(
          httpd.socket,
          server_side=True,
          certfile=certfile,
          keyfile=args['key-file'])

  logging.info("Starting simple http server at %s", address)
  httpd.serve_forever()
