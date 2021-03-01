import argparse
import glob
import itertools
import os
import sys
import subprocess as sp
import time

import six
from six.moves import configparser

from slapos.util import bytes2str, str2bytes

sys.path.append(os.path.dirname(__file__))
from theia_common import copytree, copydb, makedirs, sha256sum, parse_installed


os.environ['LC_ALL'] = 'C'
os.umask(0o77)


BACKUP_WAIT = 10


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--rsync', required=True)
  parser.add_argument('--sqlite3', required=True)
  parser.add_argument('--root', required=True)
  parser.add_argument('--backup', required=True)
  parser.add_argument('--cfg', required=True)
  parser.add_argument('--dirs', nargs='*')
  args = parser.parse_args()

  TheiaExport(args).export()


class TheiaExport(object):

  def __init__(self, args):
    self.rsync_bin = args.rsync
    self.sqlite3_bin = args.sqlite3
    self.root_dir = args.root
    self.backup_dir = args.backup
    self.slapos_cfg = cfg = args.cfg
    self.dirs = args.dirs
    configp = configparser.SafeConfigParser()
    configp.read(cfg)
    self.proxy_db = configp.get('slapproxy', 'database_uri')
    self.instance_dir = configp.get('slapos', 'instance_root')
    partitions = glob.glob(os.path.join(self.instance_dir, 'slappart*'))
    self.partition_dirs = [p for p in partitions if os.path.isdir(p)]
    self.copytree_partitions_args = {}

  def mirrorpath(self, src):
    return os.path.abspath(os.path.join(
      self.backup_dir, os.path.relpath(src, start=self.root_dir)))

  def backuptree(self, src, exclude=[], extrargs=[], verbosity='-v'):
    dst = self.mirrorpath(src)
    return copytree(self.rsync_bin, src, dst, exclude, extrargs, verbosity)

  def backupdb(self):
    copydb(self.sqlite3_bin, self.proxy_db, self.mirrorpath(self.proxy_db))

  def backuppartition(self, partition):
    installed = parse_installed(partition)
    rules = os.path.join(partition, 'srv', 'exporter.exclude')
    extrargs = ('--filter=.-/ ' + rules,) if os.path.exists(rules) else ()
    self.backuptree(partition, exclude=installed, extrargs=extrargs)
    self.copytree_partitions_args[partition] = (installed, extrargs)

  def hashscript(self, partition):
    script_path = os.path.join(partition, 'srv', '.backup_identity_script')
    if os.path.exists(script_path):
      return script_path

  def hashtree(self):
    d = {self.mirrorpath(p): self.hashscript(p) for p in self.partition_dirs}
    for dirpath, dirnames, filenames in os.walk(self.backup_dir):
      try:
        hashscript = d[os.path.abspath(dirpath)]
      except KeyError:
        paths = (os.path.join(dirpath, f) for f in filenames)
        filepaths = [p for p in paths if os.path.isfile(p)]
        for filepath in filepaths:
          yield sha256sum(filepath)
      else:
        self.hashcustom(dirpath, hashscript)
        dirnames.clear()
        continue

  def hashcustom(self, mirrordir, hashscript):
    for dirpath, _, filenames in os.walk(mirrordir):
      paths = (os.path.join(dirpath, f) for f in filenames)
      filepaths = [p for p in paths if os.path.isfile(p)]
      hashprocess = sp.Popen(hashscript, stdin=sp.PIPE, stdout=sp.PIPE)
      out, err = hashprocess.communicate(str2bytes('\0'.join(filepaths)))
      if hashprocess.returncode != 0:
        print("Custom signature script %s failed on inputs %r with:\n%s\n%s"
              % (hashscript, filepaths, out, err))
        sys.exit(1)
      for signature in bytes2str(out).strip('\n').split('\n'):
        yield signature

  def checkpartition(self, partition, pattern='/srv/backup/'):
    installed, extrargs = self.copytree_partitions_args[partition]
    output = self.backuptree(
      partition,
      exclude=installed,
      extrargs=extrargs + ('--dry-run', '--update'),
      verbosity='--out-format=%n',
    )
    return [path for path in output.splitlines() if pattern in path]

  def export(self):
    export_start_date = int(time.time())

    etc_dir = os.path.join(self.root_dir, 'etc')
    with open(os.path.join(etc_dir, '.resilient_timestamp'), 'w') as f:
      f.write(str(export_start_date))

    self.backuptree(etc_dir, extrargs=('--filter=- */', '--filter=-! .*'))

    for d in self.dirs:
      self.backuptree(d)

    self.backupdb()

    self.backuptree(self.instance_dir, exclude=self.partition_dirs)

    for p in self.partition_dirs:
      self.backuppartition(p)

    time.sleep(10)
    modified = list(itertools.chain.from_iterable(self.checkpartition(p) for p in self.partition_dirs))
    if modified:
      print(
        "ERROR: The following files in srv/backup were modified since the"
        "exporter started. Since they must be backup, exporter should be"
        "re-run. Let's sleep %s minutes, to let the backup end.\n%s" % (
        BACKUP_WAIT, '\n'.join(modified)))
      time.sleep(BACKUP_WAIT * 60)


if __name__ == '__main__':
  main()
