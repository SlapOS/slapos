import os
import subprocess
import time
import signal
import sys

pid_file = None
def sig_handler(s, frame):
  print "Killing on signal %s:" % s,
  global pid_file
  if pid_file is not None:
    if os.path.exists(pid_file):
      pid = int(open(pid_file).read())
      print 'pid %s with SIGTERM...' % pid,
      os.kill(pid, signal.SIGTERM)
      if os.kill(pid, 0):
        time.sleep(5)
        if os.kill(pid, 0):
          print 'with SIGKILL...',
          os.kill(pid, signal.SIGKILL)
    else:
      print 'no pid file %r, nothing to do...' % pid_file,
  print 'done.'
  sys.exit(0)

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGQUIT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)


def svcdaemon(args):
  """Utility script to run daemons in supervisord"""
  real_binary = args[0]['real_binary']
  global pid_file
  pid_file = args[0]['pid_file']
  subprocess.check_call(real_binary)
  print 'Started %r' % real_binary
  while True:
    time.sleep(2)
