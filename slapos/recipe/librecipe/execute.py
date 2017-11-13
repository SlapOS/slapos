import sys
import os
import signal
import subprocess
import time
from collections import defaultdict
from inotify_simple import INotify, flags

def _wait_files_creation(file_list):
  # Establish a list of directory and subfiles.
  # and test existence before watching, so that we don't miss an event.
  directories = defaultdict(dict)
  for f in file_list:
    dirname, filename = os.path.split(f)
    directories[dirname][filename] = os.path.lexists(f)

  def all_files_exists():
    return all(all(files.itervalues()) for files in directories.itervalues())

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

def execute(args):
  """Portable execution with process replacement"""
  # XXX: Kept for backward compatibility
  generic_exec([args, None, None])

def execute_wait(args):
  """Execution but after all files in args[1] exists"""
  # XXX: Kept for backward compatibility
  generic_exec([args[0], args[1], None])


child_pg = None


def executee(args):
  """Portable execution with process replacement and environment manipulation"""
  # XXX: Kept for backward compatibility
  generic_exec([args[0], None, args[1]])

def executee_wait(args):
  """Portable execution with process replacement and environment manipulation"""
  # XXX: Kept for backward compatibility
  generic_exec(args)

def generic_exec(args):
  exec_list = list(args[0])
  file_list = args[1]
  environment_overriding = args[2]

  exec_env = os.environ.copy()
  if environment_overriding is not None:
      exec_env.update(environment_overriding)

  if file_list is not None:
      _wait_files_creation(file_list)

  os.execve(exec_list[0], exec_list + sys.argv[1:], exec_env)

def sig_handler(sig, frame):
  print 'Received signal %r, killing children and exiting' % sig
  if child_pg is not None:
    os.killpg(child_pg, signal.SIGHUP)
    os.killpg(child_pg, signal.SIGTERM)
  sys.exit(0)

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGQUIT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)


def execute_with_signal_translation(args):
  """Run process as children and translate from SIGTERM to another signal"""
  global child_pg
  child = subprocess.Popen(args, close_fds=True, preexec_fn=os.setsid)
  child_pg = child.pid
  try:
    print 'Process %r started' % args
    while True:
      time.sleep(10)
  finally:
    os.killpg(child_pg, signal.SIGHUP)
    os.killpg(child_pg, signal.SIGTERM)
