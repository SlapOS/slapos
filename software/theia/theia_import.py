import argparse
import glob
import itertools
import os
import sys
import subprocess as sp
import time
import traceback

import six
from six.moves import configparser

sys.path.append(os.path.dirname(__file__))
from theia_common import copytree, copydb, parse_installed


os.environ['LC_ALL'] = 'C'
os.umask(0o77)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--rsync', required=True)
  parser.add_argument('--sqlite3', required=True)
  parser.add_argument('--slapos', required=True)
  parser.add_argument('--srlog', required=True)
  parser.add_argument('--cplog', required=True)
  parser.add_argument('--supervisorctl', required=True)
  parser.add_argument('--supervisordconf', required=True)
  parser.add_argument('--root', required=True)
  parser.add_argument('--backup', required=True)
  parser.add_argument('--cfg', required=True)
  parser.add_argument('--dirs', nargs='*')
  parser.add_argument('--exitfile', required=True)
  parser.add_argument('--errorfile', required=True)
  args = parser.parse_args()

  TheiaImport(args)()


class TheiaImport(object):

  def __init__(self, args):
    self.rsync_bin = args.rsync
    self.sqlite3_bin = args.sqlite3
    self.slapos_bin = args.slapos
    self.sr_log = args.srlog
    self.cp_log = args.cplog
    self.supervisorctl_bin = args.supervisorctl
    self.supervisord_conf = args.supervisordconf
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
    self.logs = []

  def mirrorpath(self, dst):
    return os.path.abspath(os.path.join(
      self.backup_dir, os.path.relpath(dst, start=self.root_dir)))

  def restoretree(self, dst, exclude=[], extrargs=[], verbosity='-v'):
    src = self.mirrorpath(dst)
    return copytree(self.rsync_bin, src, dst, exclude, extrargs, verbosity)

  def restoredb(self):
    copydb(self.sqlite3_bin, self.mirrorpath(self.proxy_db), self.proxy_db)

  def restorepartition(self, partition):
    installed = parse_installed(partition)
    self.restoretree(partition, exclude=installed)

  def supervisorctl(self, *args):
    supervisor_command = (self.supervisorctl_bin, '-c', self.supervisord_conf)
    command = supervisor_command + args
    print(' '.join(command))
    sp.check_call(command)

  def slapos(self, *args):
    command = (self.slapos_bin,) + args + ('--cfg', self.slapos_cfg)
    print(' '.join(command))
    sp.check_call(command)

  def remove(self, path):
    try:
      os.remove(path)
    except OSError:
      if os.path.exists(path):
        raise

  def loginfo(self, msg):
    print(msg)
    self.logs.append(msg)

  def __call__(self):
    self.remove(self.error_file)
    exitcode = 0
    try:
      self.restore()
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

  def restore(self):
    self.loginfo('Stop slapproxy')
    self.supervisorctl('stop', 'slapos-proxy')

    self.loginfo('Restore partitions')
    for p in self.partition_dirs:
      self.restorepartition(p)
  
    for d in self.dirs:
      self.loginfo('Restore directory ' + d)
      self.restoretree(d)

    self.loginfo('Restore slapproxy database')
    self.restoredb()

    etc_dir = os.path.join(self.root_dir, 'etc')
    self.loginfo('Restore directory ' + etc_dir)
    self.restoretree(etc_dir, extrargs=('--filter=- */', '--filter=-! .*'))

    custom_script = os.path.join(self.root_dir, 'srv', 'runner-import-restore')
    if os.path.exists(custom_script):
      self.loginfo('Run custom restore script %s' % custom_script)
      sp.check_call(custom_script)

    self.loginfo('Start slapproxy again')
    self.supervisorctl('start', 'slapos-proxy')

    self.loginfo('Reformat partitions')
    self.slapos('node', 'format', '--now')

    self.loginfo('Remove old supervisord configuration files')
    conf_dir = os.path.join(self.instance_dir, 'etc', 'supervisor.conf.d')
    for f in glob.glob(os.path.join(conf_dir, '*')):
      os.remove(f)

    self.loginfo('Build Software Releases')
    for i in range(3):
      try:
        self.slapos('node', 'software', '--all', '--logfile', self.sr_log)
      except sp.CalledProcessError:
        if i == 2:
          raise
      else:
        break

    self.loginfo('Remove old custom instance scripts')
    partitions_glob = os.path.join(self.instance_dir, 'slappart*')
    scripts = os.path.join(partitions_glob, 'srv', 'runner-import-restore')
    for f in glob.glob(scripts):
      self.remove(f)

    self.loginfo('Remove partition timestamps')
    timestamps = os.path.join(partitions_glob, '.timestamp')
    for f in glob.glob(timestamps):
      self.remove(f)

    self.loginfo('Build Instances')
    cp_log = self.cp_log
    for i in range(3):
      try:
        self.slapos('node', 'instance', '--force-stop', '--logfile', cp_log)
      except sp.CalledProcessError:
        if i == 2:
          raise
      else:
        break

    for custom_script in glob.glob(scripts):
      self.loginfo('Running custom instance script %s' % custom_script)
      sp.check_call(custom_script)

    self.loginfo('Done')


if __name__ == '__main__':
  main()
