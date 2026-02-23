import argparse
import glob
import itertools
import os
import shutil
import subprocess
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
    configp = configparser.ConfigParser()
    configp.read(cfg)
    self.proxy_db = configp.get('slapproxy', 'database_uri')
    self.instance_dir = configp.get('slapos', 'instance_root')
    partitions = glob.glob(os.path.join(self.instance_dir, 'slappart*'))
    self.partition_dirs = [p for p in partitions if os.path.isdir(p)]
    self.copytree_partitions_args = {}
    self.logs = []
    self.outsidedir = os.path.abspath(os.path.join(self.backup_dir, os.pardir))
    self.signaturedir = os.path.join(self.backup_dir, 'backup.signatures')

  def mirror_path(self, src):
    return os.path.abspath(os.path.join(
      self.backup_dir, os.path.relpath(src, start=self.root_dir)))

  def backup_tree(self, src):
    return copytree(self.rsync_bin, src, self.mirror_path(src))

  def backup_file(self, src, fail_if_missing=False):
    if os.path.exists(src):
      self.log('Backup file ' + src)
      copyfile(src, self.mirror_path(src))
    elif fail_if_missing:
      raise Exception('File %s is missing' % src)
    else:
      self.log('Delete file from backup ' + src)
      remove(self.mirror_path(src))

  def backup_db(self):
    copydb(self.sqlite3_bin, self.proxy_db, self.mirror_path(self.proxy_db))

  def backup_partition(self, partition):
    dst = self.mirror_path(partition)
    ignore_relpath = os.path.join('srv', 'exporter.exclude')
    ignore = parse_ignored(partition, ignore_relpath)
    if ignore:
      ignore.append(ignore_relpath) # ignore exporter.exclude itself
    delete = parse_installed(partition)
    copytree(self.rsync_bin, partition, dst, ignore, delete)
    self.copytree_partitions_args[partition] = (dst, ignore, delete)
    # Transfer parsed ignorefile so that theia1 can preserve matching files
    if ignore:
      mkdir(os.path.join(dst, 'srv'))
      with open(os.path.join(dst, ignore_relpath), 'w') as f:
        f.write('\n'.join(ignore))

  def sign(self, signaturefile, signatures):
    sign(self.outsidedir, signaturefile, signatures)

  def sign_root(self):
    signaturefile = os.path.join(self.signaturedir, 'backup.signature')
    exclude = [self.mirror_path(p) for p in self.partition_dirs]
    exclude.append(self.signaturedir)
    signatures = hashwalk(self.backup_dir, *exclude)
    self.sign(signaturefile, signatures)

  def sign_partition(self, partition):
    dst = self.mirror_path(partition)
    filename = os.path.basename(partition) + '.backup.signature'
    signaturefile = os.path.join(self.signaturedir, filename)
    script = hashscript(partition)
    if script:
      signaturefile += '.custom'
      self.sign(signaturefile, hashcustom(dst, script))
    else:
      self.sign(signaturefile, hashwalk(dst))

  def check_partition(self, partition, pattern='/srv/backup/'):
    dst, ignore, delete = self.copytree_partitions_args[partition]
    output = copytree(
      self.rsync_bin,
      partition,
      dst,
      ignore=ignore,
      delete=delete,
      extrargs=('--dry-run', '--update'),
      verbosity='--out-format=%n',
    )
    return [path for path in output.splitlines() if pattern in path]

  def log(self, msg):
    print(msg)
    self.logs.append(msg)

  def __call__(self):
    exitcode = 0
    try:
      self.export()
    except Exception as e:
      exitcode = 1
      exc = traceback.format_exc()
      if isinstance(e, subprocess.CalledProcessError) and e.output:
        exc = "%s\n\n%s" % (exc, e.output)
      with open(self.error_file, 'w') as f:
        f.write('\n ... OK\n\n'.join(self.logs))
        f.write('\n ... ERROR !\n\n')
        f.write(exc)
      print('\n\nERROR\n\n' + exc)
    else:
      with open(self.error_file, 'w') as f:
        f.write('\n ... OK\n\n'.join(self.logs))
        f.write('\n ... OK !\n\n')
        f.write('SUCCESS')
    finally:
      with open(self.exit_file, 'w') as f:
        f.write(str(exitcode))
      sys.exit(exitcode)

  def export(self):
    export_start_date = int(time.time())

    timestamp = os.path.join(self.root_dir, 'etc', '.resilient_timestamp')
    with open(timestamp, 'w') as f:
      f.write(str(export_start_date))

    rmtree(self.signaturedir)
    mkdir(self.signaturedir)

    self.backup_file(timestamp, fail_if_missing=True)

    for d in self.dirs:
      self.log('Backup directory ' + d)
      self.backup_tree(d)

    for f in self.files:
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
