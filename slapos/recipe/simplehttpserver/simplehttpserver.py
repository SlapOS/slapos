from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer
import ssl
import os
import logging
from netaddr import valid_ipv4, valid_ipv6
import socket

class ServerHandler(SimpleHTTPRequestHandler):

  def respond(self, code=200, type='text/plain'):
    self.send_response(code)
    self.send_header("Content-type", type)
    self.end_headers()

  def do_GET(self):
    logging.info('%s - GET: %s \n%s' % (self.client_address[0], self.path, self.headers))
    if not self.path or self.path == '/':
      # no access to root path
      self.respond(403)
      self.wfile.write("Forbidden")
      return
    SimpleHTTPRequestHandler.do_GET(self)

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
  
  if valid_ipv6(host):
    server = HTTPServerV6
  else:
    server = HTTPServer
  
  httpd = server((host, port), Handler)
  if args.has_key('cert-file') and args.has_key('key-file'):
    httpd.socket = ssl.wrap_socket (httpd.socket, 
                                     server_side=True,
                                     certfile=args['cert-file'],
                                     keyfile=args['key-file'])

  logging.info("Starting simple http server at https://%s:%s" % (host, port))
  httpd.serve_forever()
