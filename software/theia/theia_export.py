import argparse
import glob
import itertools
import os
import sys
import time
import traceback

import six
from six.moves import configparser

sys.path.insert(0, os.path.dirname(__file__))
from theia_common import *


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
  parser.add_argument('--dirs', action='append')
  parser.add_argument('--files', action='append')
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
    self.files = args.files
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

  def mirror_path(self, src):
    return os.path.abspath(os.path.join(
      self.backup_dir, os.path.relpath(src, start=self.root_dir)))

  def backup_tree(self, src):
    return copytree(self.rsync_bin, src, self.mirror_path(src))

  def backup_file(self, src, fail_if_missing=False):
    if os.path.exists(src):
      copyfile(src, self.mirror_path(src))
    elif fail_if_missing:
      raise Exception('File %s is missing' % src)
    else:
      remove(self.mirror_path(src))

  def backup_db(self):
    copydb(self.sqlite3_bin, self.proxy_db, self.mirror_path(self.proxy_db))

  def backup_partition(self, partition):
    installed = parse_installed(partition)
    rules = os.path.join(partition, 'srv', 'exporter.exclude')
    extrargs = ('--filter=.-/ ' + rules,) if os.path.exists(rules) else ()
    dst = self.mirror_path(partition)
    copytree(self.rsync_bin, partition, dst, installed, extrargs)
    self.copytree_partitions_args[partition] = (dst, installed, extrargs)

  def sign(self, signaturefile, signatures):
    remove(signaturefile)
    pardir = os.path.abspath(os.path.join(self.backup_dir, os.pardir))
    tmpfile = os.path.join(pardir, os.path.basename(signaturefile) + '.tmp')
    with open(tmpfile, 'w') as f:
      for s in signatures:
        f.write(s + '\n')
    os.rename(tmpfile, signaturefile)

  def sign_root(self):
    signaturefile = os.path.join(self.backup_dir, 'backup.signature')
    signatures = hashwalk(self.backup_dir, self.mirror_path(self.instance_dir))
    self.sign(signaturefile, signatures)

  def sign_partition(self, partition):
    dst = self.mirror_path(partition)
    filename = os.path.basename(partition) + '.backup.signature'
    signaturefile = os.path.join(self.backup_dir, filename)
    script = hashscript(partition)
    if script:
      signaturefile += '.custom'
      self.sign(signaturefile, hashcustom(dst, script))
    else:
      self.sign(signaturefile, hashwalk(dst))

  def remove_signatures(self):
    pattern = os.path.join(self.backup_dir, '*backup.signature*')
    signature_files = glob.glob(pattern)
    for f in signature_files:
      try:
        os.remove(f)
      except OSError:
        pass

  def check_partition(self, partition, pattern='/srv/backup/'):
    dst, installed, extrargs = self.copytree_partitions_args[partition]
    output = copytree(
      self.rsync_bin,
      partition,
      dst,
      exclude=installed,
      extrargs=extrargs + ('--dry-run', '--update'),
      verbosity='--out-format=%n',
    )
    return [path for path in output.splitlines() if pattern in path]

  def log(self, msg):
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
        f.write('\n ... OK\n\n'.join(self.logs))
        f.write('\n ... ERROR !\n\n')
        f.write(exc)
      print('\n\nERROR\n\n' + exc)
    finally:
      with open(self.exit_file, 'w') as f:
        f.write(str(exitcode))
      sys.exit(exitcode)

  def export(self):
    export_start_date = int(time.time())

    timestamp = os.path.join(self.root_dir, 'etc', '.resilient_timestamp')
    with open(timestamp, 'w') as f:
      f.write(str(export_start_date))

    self.remove_signatures()

    self.log('Backup resilient timestamp ' + timestamp)
    self.backup_file(timestamp, fail_if_missing=True)

    for d in self.dirs:
      self.log('Backup directory ' + d)
      self.backup_tree(d)

    for f in self.files:
      self.log('Backup (or delete backup of) file ' + f)
      self.backup_file(f)

    self.log('Backup slapproxy database')
    self.backup_db()

    self.log('Backup partitions')
    for p in self.partition_dirs:
      self.backup_partition(p)

    self.log('Compute root backup signature')
    self.sign_root()

    self.log('Compute partitions backup signatures')
    for p in self.partition_dirs:
      self.sign_partition(p)

    time.sleep(10)
    self.log('Check partitions')
    modified = list(itertools.chain.from_iterable(
      self.check_partition(p) for p in self.partition_dirs))
    if modified:
      msg = 'Some files have been modified since the backup started'
      self.log(msg + ':')
      self.log('\n'.join(modified))
      self.log("Let's wait %d minutes and try again" % BACKUP_WAIT)
      time.sleep(BACKUP_WAIT * 60)
      raise Exception(msg)

    self.log('Done')


if __name__ == '__main__':
  main()
