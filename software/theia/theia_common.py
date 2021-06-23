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


def sha256sum(file_path, chunk_size=1024 * 1024):
  sha256 = hashlib.sha256()
  with open(file_path, 'rb') as f:
    chunk = f.read(chunk_size)
    while chunk:
      sha256.update(chunk)
      chunk = f.read(chunk_size)
  return sha256.hexdigest()


def hashscript(partition):
  script_path = os.path.join(partition, 'srv', '.backup_identity_script')
  if os.path.exists(script_path):
    return script_path


def hashwalk(backup_dir, mirror_partitions):
  d = {p: hashscript(p) for p in mirror_partitions if hashscript(p)}
  for dirpath, dirnames, filenames in os.walk(backup_dir):
    custom_hashscript = d.get(os.path.abspath(dirpath))
    if custom_hashscript:
      hashcustom(dirpath, custom_hashscript)
      dirnames.clear()
    else:
      paths = (os.path.join(dirpath, f) for f in filenames)
      filepaths = [p for p in paths if os.path.isfile(p)]
      for filepath in filepaths:
        yield sha256sum(filepath)
      dirnames.sort()


def hashcustom(mirrordir, custom_hashscript):
  for dirpath, _, filenames in os.walk(mirrordir):
    paths = (os.path.join(dirpath, f) for f in filenames)
    filepaths = [p for p in paths if os.path.isfile(p)]
    hashprocess = sp.Popen(custom_hashscript, stdin=sp.PIPE, stdout=sp.PIPE)
    out, err = hashprocess.communicate(str2bytes('\0'.join(filepaths)))
    if hashprocess.returncode != 0:
      template = "Custom signature script %s failed on inputs %r with:\n%s\n%s"
      msg = template % (custom_hashscript, filepaths, out, err)
      print(msg)
      raise Exception(msg)
    signatures = bytes2str(out).strip('\n').split('\n')
    signatures.sort()
    for s in signatures:
      yield s
