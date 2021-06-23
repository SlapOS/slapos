import argparse
import glob
import itertools
import os
import sys
import time
import traceback

import six
from six.moves import configparser

sys.path.append(os.path.dirname(__file__))
from theia_common import copytree, copydb, hashwalk, parse_installed, remove


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
  parser.add_argument('--exitfile', required=True)
  parser.add_argument('--errorfile', required=True)
  args = parser.parse_args()

  TheiaExport(args)()


class TheiaExport(object):

  def __init__(self, args):
    self.rsync_bin = args.rsync
    self.sqlite3_bin = args.sqlite3
    self.root_dir = args.root
    self.backup_dir = args.backup
    self.slapos_cfg = cfg = args.cfg
    self.dirs = args.dirs
    self.exit_file = args.exitfile
    self.error_file = args.errorfile
    configp = configparser.SafeConfigParser()
    configp.read(cfg)
    self.proxy_db = configp.get('slapproxy', 'database_uri')
    self.instance_dir = configp.get('slapos', 'instance_root')
    partitions = glob.glob(os.path.join(self.instance_dir, 'slappart*'))
    self.partition_dirs = [p for p in partitions if os.path.isdir(p)]
    self.copytree_partitions_args = {}
    self.logs = []

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

  def sign(self, signaturefile):
    pardir = os.path.abspath(os.path.join(self.backup_dir, os.pardir))
    tmpfile = os.path.join(pardir, 'backup.signature.tmp')
    mirror_partitions = [self.mirrorpath(p) for p in self.partition_dirs]
    with open(tmpfile, 'w') as f:
      for s in hashwalk(self.backup_dir, mirror_partitions):
        f.write(s + '\n')
    os.rename(tmpfile, signaturefile)

  def checkpartition(self, partition, pattern='/srv/backup/'):
    installed, extrargs = self.copytree_partitions_args[partition]
    output = self.backuptree(
      partition,
      exclude=installed,
      extrargs=extrargs + ('--dry-run', '--update'),
      verbosity='--out-format=%n',
    )
    return [path for path in output.splitlines() if pattern in path]

  def loginfo(self, msg):
    print(msg)
    self.logs.append(msg)

  def __call__(self):
    remove(self.error_file)
    exitcode = 0
    try:
      self.export()
    except Exception:
      exitcode = 1
      exc = traceback.format_exc()
      with open(self.error_file, 'w') as f:
        f.write('\n ... OK\n'.join(self.logs))
        f.write('\n\n ... ERROR !\n\n')
        f.write(exc)
      print('\n\nERROR\n\n' + exc)
    finally:
      with open(self.exit_file, 'w') as f:
        f.write(str(exitcode))
      sys.exit(exitcode)

  def export(self):
    export_start_date = int(time.time())

    etc_dir = os.path.join(self.root_dir, 'etc')
    with open(os.path.join(etc_dir, '.resilient_timestamp'), 'w') as f:
      f.write(str(export_start_date))

    self.loginfo('Backup directory ' + etc_dir)
    self.backuptree(etc_dir, extrargs=('--filter=- */', '--filter=-! .*'))

    for d in self.dirs:
      self.loginfo('Backup directory ' + d)
      self.backuptree(d)

    self.loginfo('Backup slapproxy database')
    self.backupdb()

    self.loginfo('Backup partitions')
    for p in self.partition_dirs:
      self.backuppartition(p)

    self.loginfo('Compute backup signature')
    self.sign(os.path.join(self.backup_dir, 'backup.signature'))

    time.sleep(10)
    self.loginfo('Check partitions')
    modified = list(itertools.chain.from_iterable(
      self.checkpartition(p) for p in self.partition_dirs))
    if modified:
      msg = 'Some files have been modified since the backup started'
      self.loginfo(msg + ':')
      self.loginfo('\n'.join(modified))
      self.loginfo("Let's wait %d minutes and try again" % BACKUP_WAIT)
      time.sleep(BACKUP_WAIT * 60)
      raise Exception(msg)

    self.loginfo('Done')


if __name__ == '__main__':
  main()
