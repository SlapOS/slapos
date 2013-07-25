import socket
try:
  import readline
except ImportError:
  pass

def haproxyctl(conf):
  while True:
    try:
      l = raw_input('> ')
    except EOFError:
      print
      break
    if l == 'quit':
      break
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(conf['socket_path'])
    s.send('%s\n' % l)
    while True:
      r = s.recv(1024)
      if not r:
        break
      print r
    s.close()
