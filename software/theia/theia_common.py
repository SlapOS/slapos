import contextlib
import errno
import glob
import hashlib
import os
import re
import subprocess as sp
import sqlite3

import six
import zc.buildout.configparser

from slapos.util import bytes2str, str2bytes


RSYNC_FLAGS = ('-rlptgo', '--safe-links', '--stats', '--ignore-missing-args', '--delete', '--delete-excluded')
RSYNC_REGEX = '^(file has vanished: |rsync warning: some files vanished before they could be transferred)'
EXCLUDE_PATTERNS = ('*.sock', '*.socket', '*.pid', '.installed*.cfg')
EXCLUDE_FLAGS = ['--exclude={}'.format(x) for x in sorted(EXCLUDE_PATTERNS)]


def makedirs(path):
  try:
    os.makedirs(path if os.path.isdir(path) else os.path.dirname(path))
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise


def copytree(rsyncbin, src, dst, exclude=[], extrargs=[], verbosity='-v'):
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
  command.extend(('--filter=-/ {}'.format(x) for x in sorted(exclude)))
  command.extend(extrargs)
  command.append(verbosity)
  command.append(src)
  command.append(dst)
  try:
    return sp.check_output(command, universal_newlines=True)
  except sp.CalledProcessError as e:
    # Not all rsync errors are to be considered as errors
    if e.returncode != 24 or re.search(RSYNC_REGEX, e.output, re.M) is None:
      raise
    return e.output


def copydb(sqlite3bin, src_db, dst_db):
  makedirs(dst_db)
  sp.check_output((sqlite3bin, src_db, '.backup ' + dst_db))


def remove(path):
  try:
    os.remove(path)
  except OSError:
    if os.path.exists(path):
      raise


def parse_installed(partition):
  paths = []
  custom_script = os.path.join(partition, 'srv', '.backup_identity_script')
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
          if p and p != custom_script:
            paths.append(p)
  return paths


def sha256sum(file_path, chunk_size=1024 * 1024):
  sha256 = hashlib.sha256()
  with open(file_path, 'rb') as f:
    chunk = f.read(chunk_size)
    while chunk:
      sha256.update(chunk)
      chunk = f.read(chunk_size)
  return sha256.hexdigest()


def hashwalk(backup_dir, mirror_partitions):
  scripts = {}
  for p in mirror_partitions:
    script_path = os.path.join(p, 'srv', '.backup_identity_script')
    if os.path.exists(script_path):
      scripts[os.path.abspath(p)] = script_path
  for dirpath, dirnames, filenames in os.walk(backup_dir):
    filenames.sort()
    for f in filenames:
      filepath = os.path.join(dirpath, f)
      if os.path.isfile(filepath):
        displaypath = os.path.relpath(filepath, start=backup_dir)
        yield '%s %s' % (sha256sum(filepath), displaypath)
    remaining_dirnames = []
    for subdir in dirnames:
      subdirpath = os.path.abspath(os.path.join(dirpath, subdir))
      custom_hashscript = scripts.get(subdirpath)
      if custom_hashscript:
        print('Using custom signature script %s' % custom_hashscript)
        for s in hashcustom(subdirpath, backup_dir, custom_hashscript):
          yield s
      else:
        remaining_dirnames.append(subdir)
    remaining_dirnames.sort()
    dirnames[:] = remaining_dirnames


@contextlib.contextmanager
def cwd(path):
  old_path = os.getcwd()
  try:
    os.chdir(path)
    yield
  finally:
    os.chdir(old_path)


def hashcustom(mirrordir, backup_dir, custom_hashscript):
  workingdir = os.path.join(mirrordir, os.pardir, os.pardir, os.pardir)
  with cwd(os.path.abspath(workingdir)):
    for dirpath, _, filenames in os.walk(mirrordir):
      filepaths = []
      for f in filenames:
        path = os.path.join(dirpath, f)
        if os.path.isfile(path):
          filepaths.append('./' + os.path.relpath(path, start=workingdir))
      if not filepaths:
        continue
      hashprocess = sp.Popen(
        custom_hashscript, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
      out, err = hashprocess.communicate(str2bytes('\0'.join(filepaths)))
      if hashprocess.returncode != 0:
        template = "Custom signature script %s failed on inputs:\n%s"
        msg = template % (custom_hashscript, '\n'.join(filepaths))
        msg += "\nwith stdout:\n%s" % bytes2str(out)
        msg += "\nand stderr:\n%s" % bytes2str(err)
        raise Exception(msg)
      signatures = bytes2str(out).strip('\n').split('\n')
      signatures.sort()
      displaypath = os.path.relpath(dirpath, start=backup_dir)
      for s in signatures:
        yield '%s %s/ (custom)' % (s, displaypath)
