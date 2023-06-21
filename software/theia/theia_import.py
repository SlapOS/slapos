import argparse
import glob
import itertools
import os
import sys
import subprocess as sp
import time
import traceback

import requests
from requests.exceptions import RequestException

import six
from six.moves import configparser

sys.path.append(os.path.dirname(__file__))
from theia_common import *


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
  parser.add_argument('--dirs', action='append')
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
    self.proxy_rest_url = configp.get('slapos', 'master_rest_url') # 200 OK
    self.instance_dir = configp.get('slapos', 'instance_root')
    mirror_dir = self.mirror_path(self.instance_dir)
    partitions = glob.glob(os.path.join(mirror_dir, 'slappart*'))
    self.mirror_partition_dirs = [p for p in partitions if os.path.isdir(p)]
    self.logs = []

  def mirror_path(self, dst):
    return os.path.abspath(os.path.join(
      self.backup_dir, os.path.relpath(dst, start=self.root_dir)))

  def dst_path(self, src):
    return os.path.abspath(os.path.join(
      self.root_dir, os.path.relpath(src, start=self.backup_dir)))

  def restore_tree(self, dst, exclude=(), extrargs=(), verbosity='-v'):
    src = self.mirror_path(dst)
    return copytree(self.rsync_bin, src, dst, exclude, extrargs, verbosity)

  def restore_file(self, dst):
    src = self.mirror_path(dst)
    return copyfile(src, dst)

  def restore_db(self):
    copydb(self.sqlite3_bin, self.mirror_path(self.proxy_db), self.proxy_db)

  def restore_partition(self, mirror_partition):
    p = self.dst_path(mirror_partition)
    installed = parse_installed(p) if os.path.exists(p) else []
    copytree(self.rsync_bin, mirror_partition, p, exclude=installed)

  def supervisorctl(self, *args):
    supervisor_command = (self.supervisorctl_bin, '-c', self.supervisord_conf)
    command = supervisor_command + args
    print(' '.join(command))
    print(sp.check_output(command, stderr=sp.STDOUT, universal_newlines=True))

  def slapos(self, *args):
    command = (self.slapos_bin,) + args + ('--cfg', self.slapos_cfg)
    print(' '.join(command))
    print(sp.check_output(command, stderr=sp.STDOUT, universal_newlines=True))

  def sign(self, signaturefile, root_dir):
    with open(signaturefile, 'r') as f:
      for line in f:
        try:
          _, relpath = line.strip().split(None, 1)
        except ValueError:
          yield 'Could not parse: %s' % line
          continue
        filepath = os.path.join(root_dir, relpath)
        try:
          signature = sha256sum(filepath)
        except IOError:
          yield 'Could not read: %s' % filepath
          continue
        yield '%s %s' % (signature, relpath)

  def sign_custom(self, root_dir):
    partition = self.dst_path(root_dir)
    script = hashscript(partition)
    if not script:
      msg = 'ERROR: missing custom signature script for partition ' + partition
      raise Exception(msg)
    return hashcustom(root_dir, script)

  def find_signature_file(self, partition):
    filename = os.path.basename(partition) + '.backup.signature'
    signaturefile = os.path.join(self.backup_dir, filename)
    if os.path.exists(signaturefile):
      return signaturefile, False
    signaturefile += '.custom'
    if os.path.exists(signaturefile):
      return signaturefile, True
    raise Exception('ERROR: missing signature file for partition ' + partition)

  def verify(self, signaturefile, root_dir, custom=False):
    proof = signaturefile + '.proof'
    if custom:
      signatures = self.sign_custom(root_dir)
    else:
      signatures = self.sign(signaturefile, root_dir)
    with open(proof, 'w') as f:
      for s in signatures:
        f.write(s + '\n')
    diffcommand = ('diff', signaturefile, proof)
    try:
      sp.check_output(
        diffcommand, stderr=sp.STDOUT, universal_newlines=True)
    except sp.CalledProcessError as e:
      template = 'ERROR the backup signatures do not match\n\n%s\n%s'
      msg = template % (' '.join(diffcommand), e.output)
      print(msg)
      raise Exception(msg)

  def wait_for_proxy(self):
    timeout = 10
    sleep = 20
    url = self.proxy_rest_url
    for i in range(10):
      try:
        self.log(
          '- GET proxy %s with timeout %d (attempt %d)' % (url, timeout, i))
        response = requests.get(url, verify=True, timeout=timeout)
      except RequestException:
        if i == 9:
          raise
        else:
          self.log('- Sleep %ds before retrying' % sleep)
          time.sleep(sleep)
      else:
        response.raise_for_status()
        break

  def log(self, msg):
    msg = time.strftime("%Y-%B-%d %H:%M:%S - ") + msg
    print(msg)
    self.logs.append(msg)

  def __call__(self):
    remove(self.error_file)
    exitcode = 0
    try:
      self.restore()
    except Exception as e:
      exitcode = 1
      exc = traceback.format_exc()
      if isinstance(e, sp.CalledProcessError) and e.output:
        exc = "%s\n\n%s" % (exc, e.output)
      with open(self.error_file, 'w') as f:
        f.write('\n ... OK\n\n'.join(self.logs))
        f.write('\n ... ERROR !\n\n')
        f.write(exc)
      print('\n\nERROR\n\n' + exc)
    finally:
      with open(self.exit_file, 'w') as f:
        f.write(str(exitcode))
      sys.exit(exitcode)

  def restore(self):
    self.log('Verify main backup signature')
    signaturefile = os.path.join(self.backup_dir, 'backup.signature')
    self.verify(signaturefile, self.backup_dir)

    custom_partition_signatures = []
    for m in self.mirror_partition_dirs:
      signaturefile, custom = self.find_signature_file(m)
      if custom:
        custom_partition_signatures.append((signaturefile, m))
      else:
        self.log('Verify backup signature for ' + m)
        self.verify(signaturefile, m)

    self.log('Stop slapproxy')
    self.supervisorctl('stop', 'slapos-proxy')

    self.log('Restore partitions')
    for m in self.mirror_partition_dirs:
      self.restore_partition(m)

    for d in self.dirs:
      self.log('Restore directory ' + d)
      self.restore_tree(d)

    self.log('Restore slapproxy database')
    self.restore_db()

    timestamp = os.path.join(self.root_dir, 'etc', '.resilient_timestamp')
    self.log('Restore resilient timestamp ' + timestamp)
    self.restore_file(timestamp)

    custom_script = os.path.join(self.root_dir, 'srv', 'runner-import-restore')
    if os.path.exists(custom_script):
      self.log('Run custom restore script %s' % custom_script)
      print(sp.check_output(custom_script))

    self.log('Start slapproxy again')
    self.supervisorctl('start', 'slapos-proxy')

    self.log('Wait until slapproxy is available')
    self.wait_for_proxy()

    self.log('Reformat partitions')
    self.slapos('node', 'format', '--now')

    self.log('Remove old supervisord configuration files')
    conf_dir = os.path.join(self.instance_dir, 'etc', 'supervisor.conf.d')
    for f in glob.glob(os.path.join(conf_dir, '*')):
      os.remove(f)

    self.log('Build Software Releases')
    for i in range(3):
      try:
        self.slapos('node', 'software', '--all', '--logfile', self.sr_log)
      except sp.CalledProcessError:
        if i == 2:
          raise
      else:
        break

    self.log('Remove old custom instance scripts')
    partitions_glob = os.path.join(self.instance_dir, 'slappart*')
    scripts = os.path.join(partitions_glob, 'srv', 'runner-import-restore')
    for f in glob.glob(scripts):
      remove(f)

    self.log('Remove partition timestamps')
    timestamps = os.path.join(partitions_glob, '.timestamp')
    for f in glob.glob(timestamps):
      remove(f)

    self.log('Build Instances')
    cp_log = self.cp_log
    for i in range(3):
      try:
        self.slapos('node', 'instance', '--force-stop', '--logfile', cp_log)
      except sp.CalledProcessError:
        if i == 2:
          raise
      else:
        break

    self.log('Verify custom backup signatures')
    for signaturefile, m in custom_partition_signatures:
      self.verify(signaturefile, m, True)

    for custom_script in glob.glob(scripts):
      self.log('Running custom instance script %s' % custom_script)
      print(sp.check_output(custom_script))

    self.log('Done')


if __name__ == '__main__':
  main()
