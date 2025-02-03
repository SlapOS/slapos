from __future__ import print_function

import atexit
import errno
import sys
import os
import select
import signal
import subprocess
import time
from collections import defaultdict
from inotify_simple import INotify, flags

import six

def _wait_files_creation(file_list):
  # Establish a list of directory and subfiles.
  # and test existence before watching, so that we don't miss an event.
  directories = defaultdict(dict)
  def check_if_files_exists():
    for f in file_list:
      dirname, filename = os.path.split(f)
      directories[dirname][filename] = os.path.lexists(f)
  check_if_files_exists()

  def all_files_exists():
    return all(all(six.itervalues(files)) for files in six.itervalues(directories))

  with INotify() as inotify:
    try:
      watchdescriptors = {inotify.add_watch(dirname,
          flags.CREATE | flags.DELETE | flags.MOVED_TO | flags.MOVED_FROM
          ): dirname
        for dirname in directories}
    except OSError as e:
      if e.errno not in (errno.ENOSPC, errno.EMFILE):
        raise
      print('Error using inotify, falling back to polling')
      while not all_files_exists():
        time.sleep(0.1)
        check_if_files_exists()
    else:
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

def parse_signal(sig):
  try:
    try:
      a, b = sig.split('+', 1)
    except ValueError:
      a = sig
      b = 0
    else:
      b = int(b)
    if a[0] != '_':
      return getattr(signal, 'SIG' + a) + b
  except Exception:
    raise ValueError("invalid signal value: %s" % sig)

def generic_exec(args, extra_environ=None, wait_list=None,
                 pidfile=None, reserve_cpu=False, private_tmpfs=(),
                 # signal name (e.g. "RTMIN+1") that should be specified
                 # if pidfile (defaults to "USR1" if redirect)
                 sig_ign=None,
                 # redirect stdout and/or stderr to files; upon USR1,
                 # these files are reopened (suitable for log rotation)
                 # and an optional signal is sent to the spawned process
                 redirect=None, # (signal, stdout, stderr)
                 ):
  """
  All the SIG_IGN stuff is to avoid being killed between:
  - the moment some external software (like a logrotate configuration
    snippet) can know the PID via pidfile;
  - and when the process being starting sets up its signal handler.
  """
  args = list(args)

  if redirect and not sig_ign:
    sig_ign = "USR1"
  if sig_ign:
    sig_ign = parse_signal(sig_ign)
    signal.signal(sig_ign, signal.SIG_IGN)
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
      for i in six.moves.xrange(1+len(running)-n):
        if args == running[i:n+i]:
          return "Already running with pid %s." % pid
    @atexit.register # some best effort clean-up, and it is
    def _():         # expected that it does nothing upon execv.
      try:
        os.unlink(pidfile)
      except OSError as e:
        if e.errno != errno.ENOENT:
          raise
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

  def preexec_fn():
    if private_tmpfs:
      mount, unshare = _libc()
      CLONE_NEWNS   = 0x00020000
      CLONE_NEWUSER = 0x10000000
      uid = os.getuid()
      gid = os.getgid()
      unshare(CLONE_NEWUSER |CLONE_NEWNS)
      with open('/proc/self/setgroups', 'w') as f:
        f.write('deny')
      with open('/proc/self/uid_map', 'w') as f:
        f.write('%s %s 1' % (uid, uid))
      with open('/proc/self/gid_map', 'w') as f:
        f.write('%s %s 1' % (gid, gid))
      for size, path in private_tmpfs:
        try:
          os.mkdir(path)
        except OSError as e:
          if e.errno != errno.EEXIST:
            raise
        mount(b'tmpfs', path.encode(), b'tmpfs', 0, ('size=' + size).encode())
    if redirect:
      if sig != sig_ign:
        signal.signal(sig_ign, signal.SIG_DFL)
        signal.signal(sig, signal.SIG_IGN)
      for fds in dup2:
        os.dup2(*fds)

  if redirect:
    if extra_environ:
      env = os.environ.copy()
      env.update(extra_environ)
    else:
      env = None
    sig, stdout, stderr = redirect
    sig = parse_signal(sig)
    r, trigger = os.pipe()
    rfds = [r]
    logs = []
    dup2 = []
    def reopen():
      new = []
      for path, fd in logs:
        os.close(fd)
        new.append((path,
            os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o666)))
      logs[:] = new
    def setup(fd, path):
      r, w = os.pipe()
      if w != fd:
        dup2.append((w, fd))
      logs.append((path, w))
      rfds.append(r)
    if stdout:
      setup(1, stdout)
    if stderr:
      if stderr == stdout:
        dup2.append((1, 2))
      else:
        setup(2, stderr)
    # First, preexec_fn is called, then close_fds is processed,
    # and at last, Popen returns.
    process = subprocess.Popen(args, preexec_fn=preexec_fn, env=env,
                               close_fds=True) # PY3: this is the default
    def sighandler(*_):
      if sig:
        process.send_signal(sig)
      os.write(trigger, b'\0')
    signal.signal(sig_ign, sighandler)
    reopen()
    while True:
      try: # PY3: select internally retries on EINTR
        r = select.select(rfds, (), ())[0]
      except select.error as e:
        if e.args[0] != errno.EINTR:
          raise
        assert six.PY2
        continue
      for r in r:
        d = os.read(r, 1024)
        i = rfds.index(r) - 1
        if i < 0:
          reopen()
        elif d:
          os.write(logs[i][1], d)
        else:
          os.close(logs.pop(i)[1])
          os.close(rfds.pop(i+1))
          if not logs:
            signal.signal(sig_ign, signal.SIG_IGN)
            return process.wait()

  preexec_fn()
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
