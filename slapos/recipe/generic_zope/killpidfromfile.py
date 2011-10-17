import sys
import os
import signal
def killpidfromfile(*args):
  if len(args):
    file = args[1]
    sig = getattr(signal, args[2], None)
  else:
    file = sys.argv[1]
    sig = getattr(signal, sys.argv[2], None)
  if sig is None:
    raise ValueError('Unknwon signal name %s' % sig)
  if os.path.exists(file):
    pid = int(open(file).read())
    print 'Killing pid %s with signal %s' % (pid, sig)
    os.kill(pid, sig)
