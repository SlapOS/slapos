# -*- coding: utf-8 -*-
from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer
import ssl
import os
import logging
from netaddr import valid_ipv4, valid_ipv6
import socket
import cgi, errno

class ServerHandler(SimpleHTTPRequestHandler):

  document_path = ''
  restrict_root_folder = True

  def respond(self, code=200, type='text/html'):
    self.send_response(code)
    self.send_header("Content-type", type)
    self.end_headers()

  def restrictedRootAccess(self):
    if self.restrict_root_folder and self.path and self.path == '/':
      # no access to root path
      self.respond(403)
      self.wfile.write("Forbidden")
      return True
    return False

  def do_GET(self):
    logging.info('%s - GET: %s \n%s' % (self.client_address[0], self.path, self.headers))
    if self.restrictedRootAccess():
      return
    SimpleHTTPRequestHandler.do_GET(self)

  def do_POST(self):
    logging.info('%s - POST: %s \n%s' % (self.client_address[0], self.path, self.headers))
    if self.restrictedRootAccess():
      return

    form = cgi.FieldStorage(
      fp=self.rfile,
      headers=self.headers,
      environ={'REQUEST_METHOD':'POST',
                'CONTENT_TYPE':self.headers['Content-Type']}
    )
    name = form['path'].value
    content = form['content'].value
    method = 'a'
    if form.has_key('clear') and form['clear'].value == '1':
      method = 'w'
    self.writeFile(name, content, method)
    self.respond(200, type=self.headers['Content-Type'])
    self.wfile.write("Content written to %s" % name)

  def writeFile(self, filename, content, method='a'):
    file_path = os.path.join(self.document_path, filename)

    try:
      os.makedirs(os.path.dirname(file_path))
    except OSError as exception:
      if exception.errno != errno.EEXIST:
        logging.error('Failed to create file in %s. The error is \n%s' % (
          file_path, str(exception)))

    logging.info('Writing recieved content to file %s' % file_path)
    try:
      with open(file_path, method) as myfile:
        myfile.write(content)
        logging.info('Done.')
    except IOError as e:
      logging.error('Something happened while processing \'writeFile\'. The message is %s' %
                    str(e))

class HTTPServerV6(HTTPServer):
  address_family = socket.AF_INET6


def run(args):
  
  # minimal web server.  serves files relative to the
  # current directory.
  logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                            filename=args['log-file'] ,level=logging.INFO)
  
  port = args['port']
  host = args['host']
  os.chdir(args['cwd'])
  
  Handler = ServerHandler
  Handler.document_path = args['root-dir']
  Handler.restrict_root_folder = (args['root-dir'] != args['cwd'])
  
  if valid_ipv6(host):
    server = HTTPServerV6
  else:
    server = HTTPServer
  
  httpd = server((host, port), Handler)
  scheme = 'http'
  if args.has_key('cert-file') and args.has_key('key-file') and \
      os.path.exists(args['cert-file']) and os.path.exists(args['key-file']):
    scheme = 'https'
    httpd.socket = ssl.wrap_socket (httpd.socket, 
                                     server_side=True,
                                     certfile=args['cert-file'],
                                     keyfile=args['key-file'])

  logging.info("Starting simple http server at %s://%s:%s" % (scheme, host, port))
  httpd.serve_forever()
