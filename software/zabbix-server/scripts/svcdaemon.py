import os
import subprocess
import time
import signal
import sys

def get_pid(filename):
  pid = None
  if os.path.exists(filename):
    data = open(pid_file).read()
    try:
      pid = int(data)
    except ValueError:
      pass
  return pid

pid_file = None
def sig_handler(s, frame):
  print "Killing on signal %s:" % s,
  global pid_file
  if pid_file is not None:
    pid = get_pid(pid_file)
    if pid is not None:
      os.kill(pid, signal.SIGTERM)
      try:
        os.kill(pid, 0)
      except Exception:
        pass
      else:
        time.sleep(5)
        try:
          os.kill(pid, 0)
        except Exception:
          pass
        else:
          print 'with SIGKILL...',
          os.kill(pid, signal.SIGKILL)
    else:
      raise ValueError('Pid is none.')
  print 'done.'
  sys.exit(0)

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGQUIT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)


def svcdaemon(args):
  """Utility script to run daemons in supervisord"""
  real_binary = args[0]
  global pid_file
  pid_file = args[1]
  subprocess.check_call(real_binary)
  print 'Started %r' % real_binary
  while True:
    time.sleep(5)
    pid = get_pid(pid_file)
    if pid is None:
      raise ValueError('Pid is none')
    os.kill(pid, 0)

if __name__ == '__main__':
  args = []
  args.append(sys.argv[1])
  args.append(sys.argv[2])
  if len(sys.argv) > 3:
    time.sleep(int(sys.argv[3]))
  svcdaemon(args)
  exit(0)
