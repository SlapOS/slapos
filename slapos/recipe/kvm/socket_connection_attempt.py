import socket
import sys

def connection_attempt():

  try:
    hostname, port = sys.argv[1:3]
  except ValueError:
    print >> sys.stderr, """Bad command line.
  Usage: %s hostname|ip port""" % sys.argv[0]
    sys.exit(1)

  connection_okay = False

  try:
    s = socket.create_connection((hostname, port))
    connection_okay = True
    s.close()
  except (socket.error, socket.timeout):
    connection_okay = False

  if not connection_okay:
    print >> sys.stderr, "%(port)s on %(ip)s isn't listening" % {
      'port': port, 'ip': hostname
    }
    sys.exit(127)
