import sys
import os
import signal
import subprocess
import time

import inotifyx

def _wait_files_creation(file_list):
  # Etablish a list of directory and subfiles
  directories = dict()
  for dirname, filename in [os.path.split(f) for f in file_list]:
    directories.setdefault(dirname, dict())
    directories[dirname][filename] = False

  def all_files_exists():
    return all([all(files.values()) for files in directories.values()])

  fd = inotifyx.init()
  try:
    # Watch every directories where the file are
    watchdescriptors = dict()
    for dirname in directories.keys():
      wd = inotifyx.add_watch(fd,
                              dirname,
                              inotifyx.IN_CREATE | inotifyx.IN_DELETE)
      watchdescriptors[wd] = dirname

    # Set to True the file wich exists
    for dirname, filename in [os.path.split(f) for f in file_list]:
      directories[dirname][filename] = os.path.exists(os.path.join(dirname,
                                                                   filename))
    # Let's wait for every file creation
    while not all_files_exists():
      events_list = inotifyx.get_events(fd)
      for event in events_list:
        dirname = watchdescriptors[event.wd]
        if event.name in directories[dirname]:
          # One of watched file was created or deleted
          if event.mask & inotifyx.IN_DELETE:
            directories[dirname][event.name] = False
          else:
            directories[dirname][event.name] = True

  finally:
    os.close(fd)

def execute(args):
  """Portable execution with process replacement"""
  # Note: Candidate for slapos.lib.recipe
  os.execv(args[0], args + sys.argv[1:])

def execute_wait(args):
  """Execution but after all files in args[1] exists"""
  exec_list = list(args[0])
  file_list = list(args[1])
  _wait_files_creation(file_list)
  os.execv(exec_list[0], exec_list + sys.argv[1:])


child_pg = None


def executee(args):
  """Portable execution with process replacement and environment manipulation"""
  exec_list = list(args[0])
  environment = args[1]
  env = os.environ.copy()
  for k,v in environment.iteritems():
    env[k] = v
  os.execve(exec_list[0], exec_list + sys.argv[1:], env)

def executee_wait(args):
  """Portable execution with process replacement and environment manipulation"""
  exec_list = list(args[0])
  file_list = list(args[1])
  environment = args[2]
  env = os.environ.copy()
  for k,v in environment.iteritems():
    env[k] = v
  _wait_files_creation(file_list)
  os.execve(exec_list[0], exec_list + sys.argv[1:], env)

def sig_handler(signal, frame):
  print 'Received signal %r, killing children and exiting' % signal
  if child_pg is not None:
    os.killpg(child_pg, signal.SIGHUP)
    os.killpg(child_pg, signal.SIGTERM)
  sys.exit(0)

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGQUIT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)


def execute_with_signal_translation(args):
  """Run process as children and translate from SIGTERM to another signal"""
  child = subprocess.Popen(args, close_fds=True, preexec_fn=os.setsid)
  child_pg = child.pid
  try:
    print 'Process %r started' % args
    while True:
      time.sleep(10)
  finally:
    os.killpg(child_pg, signal.SIGHUP)
    os.killpg(child_pg, signal.SIGTERM)
