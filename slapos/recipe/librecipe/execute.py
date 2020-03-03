from __future__ import print_function

import errno
import sys
import os
import signal
import subprocess
from collections import defaultdict
from inotify_simple import INotify, flags

import six

def _wait_files_creation(file_list):
  # Establish a list of directory and subfiles.
  # and test existence before watching, so that we don't miss an event.
  directories = defaultdict(dict)
  for f in file_list:
    dirname, filename = os.path.split(f)
    directories[dirname][filename] = os.path.lexists(f)

  def all_files_exists():
    return all(all(six.itervalues(files)) for files in six.itervalues(directories))

  with INotify() as inotify:
    watchdescriptors = {inotify.add_watch(dirname,
        flags.CREATE | flags.DELETE | flags.MOVED_TO | flags.MOVED_FROM
        ): dirname
      for dirname in directories}

    while not all_files_exists():
      for event in inotify.read():
        directory = directories[watchdescriptors[event.wd]]
        if event.name in directory:
          directory[event.name] = event.mask & (flags.CREATE | flags.MOVED_TO)

def _libc():
  from ctypes import CDLL, get_errno, c_char_p, c_int, c_ulong, util
  libc = CDLL(util.find_library('c'), use_errno=True)
  libc_mount = libc.mount
  libc_mount.argtypes = c_char_p, c_char_p, c_char_p, c_ulong, c_char_p
  def mount(source, target, filesystemtype, mountflags, data):
    if libc_mount(source, target, filesystemtype, mountflags, data):
      e = get_errno()
      raise OSError(e, os.strerror(e))
  libc_unshare = libc.unshare
  libc_unshare.argtypes = c_int,
  def unshare(flags):
    if libc_unshare(flags):
      e = get_errno()
      raise OSError(e, os.strerror(e))
  return mount, unshare

def generic_exec(args, extra_environ=None, wait_list=None,
                 pidfile=None, reserve_cpu=False, private_tmpfs=(),
                 #shebang_workaround=False, # XXX: still needed ?
                 ):
  args = list(args)

  if pidfile:
    import psutil
    try:
      with open(pidfile) as f:
        pid = int(f.read())
      running = psutil.Process(pid).cmdline()
    except Exception:
      pass
    else:
      # With chained shebangs, several paths may be inserted at the beginning.
      n = len(args)
      for i in xrange(1+len(running)-n):
        if args == running[i:n+i]:
          sys.exit("Already running with pid %s." % pid)
    with open(pidfile, 'w') as f:
      f.write(str(os.getpid()))

  args += sys.argv[1:]

  if reserve_cpu:
    # If the CGROUPS cpuset is available (and prepared by slap format),
    # request an exclusive CPU core for this process.
    with open(os.path.expanduser('~/.slapos-cpu-exclusive'), 'a') as f:
      f.write('%s\n' % os.getpid())

  if wait_list:
    _wait_files_creation(wait_list)

  if private_tmpfs:
    mount, unshare = _libc()
    CLONE_NEWNS   = 0x00020000
    CLONE_NEWUSER = 0x10000000
    uid = os.getuid()
    gid = os.getgid()
    unshare(CLONE_NEWUSER |CLONE_NEWNS)
    with open('/proc/self/setgroups', 'wb') as f: f.write('deny')
    with open('/proc/self/uid_map',   'wb') as f: f.write('%s %s 1' % (uid, uid))
    with open('/proc/self/gid_map',   'wb') as f: f.write('%s %s 1' % (gid, gid))
    for size, path in private_tmpfs:
      try:
        os.mkdir(path)
      except OSError as e:
        if e.errno != errno.EEXIST:
          raise
      mount('tmpfs', path, 'tmpfs', 0, 'size=' + size)

  if extra_environ:
    env = os.environ.copy()
    env.update(extra_environ)
    os.execve(args[0], args, env)
  else:
    os.execv(args[0], args)

child_pg = None

def sig_handler(sig, frame):
  print('Received signal %r, killing children and exiting' % sig)
  if child_pg is not None:
    os.killpg(child_pg, signal.SIGHUP)
    os.killpg(child_pg, signal.SIGTERM)
  sys.exit()

def execute_with_signal_translation(args):
  """Run process as children and translate from SIGTERM to another signal"""
  global child_pg
  signal.signal(signal.SIGINT, sig_handler)
  signal.signal(signal.SIGQUIT, sig_handler)
  signal.signal(signal.SIGTERM, sig_handler)
  child = subprocess.Popen(args, close_fds=True, preexec_fn=os.setsid)
  child_pg = child.pid
  try:
    print('Process %r started' % (args, ))
    signal.pause()
  finally:
    os.killpg(child_pg, signal.SIGHUP)
    os.killpg(child_pg, signal.SIGTERM)
