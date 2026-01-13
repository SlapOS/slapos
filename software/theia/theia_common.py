import contextlib
import errno
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sqlite3

import six
import zc.buildout.configparser

from slapos.util import bytes2str, str2bytes


RSYNC_FLAGS = ('-rlptgo', '--safe-links', '--stats', '--ignore-missing-args', '--delete')
RSYNC_REGEX = '^(file has vanished: |rsync warning: some files vanished before they could be transferred)'
EXCLUDE_PATTERNS = ('*.sock', '*.socket', '*.pid', '.installed*.cfg')
EXCLUDE_FLAGS = ['--filter=-s {}'.format(x) for x in sorted(EXCLUDE_PATTERNS)]


def run_process(command, **kwargs):
  kwargs['stderr'] = subprocess.STDOUT # capture stderr too
  kwargs['universal_newlines'] = True
  return subprocess.check_output(command, **kwargs)


def mkdir(path):
  try:
    os.mkdir(path)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise


def makedirs(path):
  try:
    os.makedirs(path)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise


def copyfile(src, dst):
  dst = os.path.abspath(dst)
  makedirs(os.path.dirname(dst))
  shutil.copy2(src, dst)


def copytree(rsyncbin, src, dst, ignore=(), delete=(), extrargs=(), verbosity='-v'):
  # Ensure there is a trailing slash in the source directory
  # to avoid creating an additional directory level at the destination
  src = os.path.join(src, '')

  # Compute absolute path of destination
  dst = os.path.abspath(dst)

  # Create destination dir if it doesn't exist
  makedirs(dst)

  command = [rsyncbin]
  command.extend(RSYNC_FLAGS)

  # Exclude destination file from sources
  command.append('--filter=-/ {}'.format(dst))

  command.extend(EXCLUDE_FLAGS)
  # Put ignore patterns before delete patterns, so that ignoring takes precedence
  # Ignore patterns must always be relative to the root of the transfer, so that
  # they match the same on the sending and the receiving side. Delete patterns
  # may be absolute paths, as they need only match on the sending side.
  command.extend(('--filter=- {}'.format(x) for x in sorted(ignore)))
  command.extend(('--filter=-s/ {}'.format(x) for x in sorted(delete)))
  command.extend(extrargs)
  command.append(verbosity)
  command.append(src)
  command.append(dst)
  try:
    return run_process(command)
  except subprocess.CalledProcessError as e:
    # Not all rsync errors are to be considered as errors
    if e.returncode != 24 or re.search(RSYNC_REGEX, e.output, re.M) is None:
      raise
    return e.output


def copydb(sqlite3bin, src_db, dst_db):
  makedirs(os.path.dirname(dst_db))
  run_process((sqlite3bin, src_db, '.backup ' + dst_db))


def remove(path):
  try:
    os.remove(path)
  except OSError as e:
    if e.errno != errno.ENOENT:
      raise


def parse_installed(partition):
  paths = []
  for cfg in glob.glob(os.path.join(partition, '.installed*.cfg')):
    try:
      with open(cfg) as f:
        installed_cfg = zc.buildout.configparser.parse(f, cfg)
    except IOError as e:
      if e.errno != errno.ENOENT:
        raise
    else:
      for section in six.itervalues(installed_cfg):
        for p in section.get('__buildout_installed__', '').splitlines():
          p = p.strip()
          if p:
            paths.append(p)
  return paths


def parse_ignored(partition, *ignore_relpath):
  partition = os.path.normpath(os.path.abspath(partition))
  ignorefile = os.path.join(partition, *ignore_relpath)
  try:
    with open(ignorefile) as f:
      rules = f.read().splitlines()
  except OSError as e:
    if e.errno != errno.ENOENT:
      raise
    return ()
  parsed = []
  for rule in rules:
    rule = rule.strip()
    if rule:
      relpath = os.path.relpath(rule, start=partition)
      if not relpath.startswith(os.pardir):
        parsed.append(relpath)
      else:
        parsed.append(rule)
  return parsed


def sha256sum(file_path, chunk_size=1024 * 1024):
  sha256 = hashlib.sha256()
  with open(file_path, 'rb') as f:
    chunk = f.read(chunk_size)
    while chunk:
      sha256.update(chunk)
      chunk = f.read(chunk_size)
  return sha256.hexdigest()


def fast_hashwalk(root_dir):
  for dirpath, dirnames, filenames in os.walk(root_dir):
    for f in filenames:
      filepath = os.path.join(dirpath, f)
      if os.path.isfile(filepath):
        displaypath = os.path.relpath(filepath, start=root_dir)
        yield '%s %s' % (sha256sum(filepath), displaypath)


def exclude_hashwalk(root_dir, instance_dir):
  root_dir = os.path.abspath(root_dir)
  instance_dir = os.path.abspath(instance_dir)
  for dirpath, dirnames, filenames in os.walk(root_dir):
    for f in filenames:
      filepath = os.path.join(dirpath, f)
      if os.path.isfile(filepath):
        displaypath = os.path.relpath(filepath, start=root_dir)
        yield '%s %s' % (sha256sum(filepath), displaypath)
    if dirpath == instance_dir:
      remaining_dirs = []
      for d in dirnames:
        if not d.startswith('slappart'):
          remaining_dirs.append(d)
      dirnames[:] = remaining_dirs


def hashwalk(root_dir, instance_dir=None):
  if instance_dir and not os.path.relpath(
      instance_dir, start=root_dir).startswith(os.pardir):
    return exclude_hashwalk(root_dir, instance_dir)
  return fast_hashwalk(root_dir)


def hashscript(partition):
  script = os.path.join(partition, 'srv', '.backup_identity_script')
  if os.path.exists(script):
    return script
  return None


@contextlib.contextmanager
def cwd(path):
  old_path = os.getcwd()
  try:
    os.chdir(path)
    yield
  finally:
    os.chdir(old_path)


def hashcustom(partition, script):
  workingdir = os.path.join(partition, os.pardir, os.pardir, os.pardir)
  with cwd(os.path.abspath(workingdir)):
    for dirpath, dirnames, filenames in os.walk(partition):
      dirnames.sort()
      filepaths = []
      for f in filenames:
        path = os.path.join(dirpath, f)
        if os.path.isfile(path):
          filepaths.append('./' + os.path.relpath(path, start=workingdir))
      if not filepaths:
        continue
      hashprocess = subprocess.Popen(
        script,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
      )
      out, err = hashprocess.communicate(str2bytes('\0'.join(filepaths)))
      if hashprocess.returncode != 0:
        template = "Custom signature script %s failed on inputs:\n%s"
        msg = template % (script, '\n'.join(filepaths))
        msg += "\nwith stdout:\n%s" % bytes2str(out)
        msg += "\nand stderr:\n%s" % bytes2str(err)
        raise Exception(msg)
      signatures = bytes2str(out).strip('\n').split('\n')
      signatures.sort()
      displaypath = os.path.relpath(dirpath, start=partition)
      for s in signatures:
        yield '%s %s' % (s, displaypath)
