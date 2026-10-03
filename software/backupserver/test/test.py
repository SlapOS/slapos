##############################################################################
#
# Copyright (c) 2019 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################


import importlib.util
import json
import os
import pwd
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestBackupServer(InstanceTestCase):

  def test(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()

    # Check that there is a RSS feed
    self.assertTrue('rss' in parameter_dict)
    self.assertTrue(parameter_dict['rss'].startswith(
      f'https://[{self.computer_partition_ipv6_address}]:9443/'
    ))

    result = requests.get(
      parameter_dict['rss'], verify=False, allow_redirects=False)

    # XXX crontab not triggered yet
    self.assertEqual(
      [requests.codes.not_found, False],
      [result.status_code, result.is_redirect]
    )

    # Check monitor
    self.assertTrue('monitor-base-url' in parameter_dict)
    self.assertTrue('monitor-setup-url' in parameter_dict)

    result = requests.get(
      parameter_dict['monitor-base-url'], verify=False, allow_redirects=False)
    self.assertEqual(
      [requests.codes.unauthorized, False],
      [result.status_code, result.is_redirect]
    )


def _getFreePort():
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.bind(('127.0.0.1', 0))
  port = s.getsockname()[1]
  s.close()
  return port


class TestBackupServerRdiffBackupVersions(InstanceTestCase):
  """
  software/backupserver must keep working when pulling from remote ends that
  run either rdiff-backup 1.x or 2.x: the two major versions do not share a
  network protocol (see https://rdiff-backup.net/migration.html), so this
  software release builds both (component/rdiff-backup's rdiff-backup-1.3.4 and
  rdiff-backup-script parts) and each slave picks the one matching its own
  remote end through the rdiff-backup-version parameter.

  This test acts as both ends of one pull: a local sshd plays "the remote
  end" being backed up, and two slaves - one configured for rdiff-backup
  version 1, one for version 2 - each pull a small known file from it.

  It also covers the opposite: two more slaves are deliberately configured
  with a rdiff-backup-version that does NOT match what their "remote" end
  actually runs. The pull itself is then expected to fail (the local and
  remote rdiff-backup CLIs disagree on syntax), and the
  backupserver_check_backup promise is expected to catch and report that
  failure, instead of silently passing.
  """

  # rdiff-backup-version each slave is configured with.
  CONFIGURED_VERSION = {
    'rdiffv1': 1,
    'rdiffv2': 2,
    'rdiffwrong21': 2,
    'rdiffwrong12': 1,
  }
  # rdiff-backup major version the "remote" end (the sshd fixture, through
  # remote_rdiff_path) actually runs for each slave. For the rdiffwrong*
  # slaves this is deliberately the other version than CONFIGURED_VERSION,
  # to simulate a slave misconfigured against its real remote end.
  REMOTE_ACTUAL_VERSION = {
    'rdiffv1': 1,
    'rdiffv2': 2,
    'rdiffwrong21': 1,
    'rdiffwrong12': 2,
  }

  # rdiffwrong12 (configured for version 1, remote actually runs version 2)
  # does not fail quickly: rdiff-backup 2.x's CLI keeps a backward-compatible
  # reading of the 1.x "--server --restrict-read-only" flags (see
  # https://rdiff-backup.net/migration.html), so its "server" side starts up
  # instead of rejecting them outright, but the two versions still do not
  # share a wire protocol, so both ends then block reading forever (verified
  # empirically: zero bytes exchanged, indefinitely). This never reaches a
  # "backup failed" status line, so it is caught through the periodicity
  # check instead (see template-backup-script.sh.in's comment about the
  # promise detecting a backup that took too long). _runPromise() overrides
  # this slave's isolated promise copy to use a frequent cron pattern for
  # that check alone - the slave's own "frequency" parameter stays the rare
  # one used by every other slave, since it also drives the instance's real
  # dcron, and a frequent real cron would otherwise fire its own automatic
  # backup attempt (with no sshd fixture listening yet) before the test
  # gets a chance to run and observe this slave's backup script itself.
  HANGING_SLAVE_REFERENCE_TUPLE = ('rdiffwrong12',)

  @classmethod
  def getSlaveReferenceList(cls):
    return list(cls.CONFIGURED_VERSION)

  @classmethod
  def getSlaveRdiffBackupVersion(cls, slave_reference):
    return cls.CONFIGURED_VERSION[slave_reference]

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      slave_reference: {
        'hostname': '%s.example.com' % slave_reference,
        'connection': '%s@127.0.0.1' % cls._ssh_user,
        'connection_port': str(cls._ssh_port),
        'exclude': '',
        'include': cls._source_dir[slave_reference],
        'frequency': '47 5 1 1 *',  # never triggered by cron in this test
        'sudo': False,
        'rdiff-backup-version': cls.getSlaveRdiffBackupVersion(slave_reference),
      }
      for slave_reference in cls.getSlaveReferenceList()
    }

  @classmethod
  def requestDefaultInstance(cls, state='started'):
    cls._ssh_user = pwd.getpwuid(os.getuid()).pw_name
    cls._ssh_port = _getFreePort()
    cls._work_dir = tempfile.mkdtemp(prefix='backupserver-rdiffversion-')
    cls._source_dir = {}
    cls._source_content = {}
    for slave_reference in cls.getSlaveReferenceList():
      source_dir = os.path.realpath(
        os.path.join(cls._work_dir, 'source-%s' % slave_reference))
      os.makedirs(source_dir)
      content = 'hello from %s\n' % slave_reference
      with open(os.path.join(source_dir, 'greeting.txt'), 'w') as f:
        f.write(content)
      cls._source_dir[slave_reference] = source_dir
      cls._source_content[slave_reference] = content

    instance = super().requestDefaultInstance(state=state)
    cls.requestSlaves()
    return instance

  @classmethod
  def requestSlaves(cls, extra_parameter_dict_dict=None):
    software_url = cls.getSoftwareURL()
    software_type = cls.getInstanceSoftwareType()
    for slave_reference, partition_parameter_kw in \
            cls.getSlaveParameterDictDict().items():
      if extra_parameter_dict_dict:
        partition_parameter_kw = dict(
          partition_parameter_kw,
          **extra_parameter_dict_dict.get(slave_reference, {}))
      cls.slap.request(
        software_release=software_url,
        software_type=software_type,
        partition_reference=slave_reference,
        partition_parameter_kw=partition_parameter_kw,
        shared=True,
      )

  @classmethod
  def getSlaveConnectionParameterDict(cls, slave_reference):
    return cls.slap.request(
      software_release=cls.getSoftwareURL(),
      software_type=cls.getInstanceSoftwareType(),
      partition_reference=slave_reference,
      partition_parameter_kw=cls.getSlaveParameterDictDict()[slave_reference],
      shared=True,
    ).getConnectionParameterDict()

  @staticmethod
  def _getRenderedSlaveReference(slave_reference):
    # instance-pullrdiffbackup.cfg.in names every generated section after
    # slave_instance['slave_reference'], which SlapOS populates as the
    # requested partition_reference prefixed with "_".
    return '_' + slave_reference

  def _getBackupScriptPath(self, slave_reference):
    return os.path.join(
      self.computer_partition_root_path, 'etc', 'backup',
      '%s-backup-script' % self._getRenderedSlaveReference(slave_reference))

  def _getRdiffBackupBinary(self, slave_reference, version):
    # template-backup-script.sh.in sets RDIFF_BACKUP= once in the "if" branch
    # (version 1) and once in the "else" branch (version 2 and up) of a
    # shell conditional; both lines are always present in the rendered
    # script regardless of which one actually runs, so pick the occurrence
    # matching the requested version rather than just the first match in
    # the file.
    with open(self._getBackupScriptPath(slave_reference)) as f:
      content = f.read()
    match_list = re.findall(r'^\s*RDIFF_BACKUP=(\S+)$', content, re.MULTILINE)
    self.assertEqual(
      2, len(match_list),
      "expected 2 RDIFF_BACKUP= lines (if/else) in %s, found %r" % (
        slave_reference, match_list))
    index = 0 if version == 1 else 1
    return match_list[index]

  @staticmethod
  def _getRunPromisesScriptPath():
    return importlib.util.find_spec('slapos.grid.promise.runpromises').origin

  def _runPromise(self, slave_reference):
    # Run this slave's backupserver_check_backup promise in full isolation:
    # its own promise-folder (containing only a copy of that one generated
    # promise script) and its own, empty partition-folder, with no
    # --log-folder. With no --log-folder, GenericPromise logs sense() to an
    # in-memory buffer that test() reads back within that same process, so
    # one subprocess run is enough to get a result for this run alone,
    # uninfluenced by any other promise or by a previous run's history.
    promise_name = '%s_check_backup.py' % self._getRenderedSlaveReference(
      slave_reference)
    promise_src = os.path.join(
      self.computer_partition_root_path, 'etc', 'plugin', promise_name)
    promise_dir = tempfile.mkdtemp(prefix='backupserver-rdiffversion-promise-')
    self.addCleanup(shutil.rmtree, promise_dir, ignore_errors=True)
    promise_dst = os.path.join(promise_dir, promise_name)
    shutil.copy(promise_src, promise_dst)
    if slave_reference in self.HANGING_SLAVE_REFERENCE_TUPLE:
      # Make this isolated copy's periodicity check use a frequent cron
      # pattern, without touching the slave's own "frequency" parameter
      # (which also drives the instance's real dcron, and must stay rare -
      # see HANGING_SLAVE_REFERENCE_TUPLE).
      with open(promise_dst) as f:
        promise_content = f.read()
      promise_content, count = re.subn(
        r"('cron_frequency': ')[^']*(')", r'\g<1>* * * * *\g<2>',
        promise_content)
      self.assertEqual(
        1, count, "could not find cron_frequency in %s" % promise_dst)
      with open(promise_dst, 'w') as f:
        f.write(promise_content)
    partition_dir = tempfile.mkdtemp(prefix='backupserver-rdiffversion-partition-')
    self.addCleanup(shutil.rmtree, partition_dir, ignore_errors=True)
    # PromiseLauncher.run() unconditionally lists legacy_promise_folder with
    # no None-guard, so this must be a real, empty directory rather than the
    # unset default - otherwise os.listdir(None) falls back to the current
    # directory and os.path.join() on its entries raises a TypeError.
    legacy_promise_dir = tempfile.mkdtemp(
      prefix='backupserver-rdiffversion-legacy-promise-')
    self.addCleanup(shutil.rmtree, legacy_promise_dir, ignore_errors=True)
    return subprocess.run(
      [
        sys.executable, self._getRunPromisesScriptPath(),
        '--promise-folder', promise_dir,
        '--legacy-promise-folder', legacy_promise_dir,
        '--partition-folder', partition_dir,
        '--force',
      ],
      capture_output=True, text=True)

  def _startSshdFixture(self, authorized_key_list):
    ssh_keygen = shutil.which('ssh-keygen')
    sshd = shutil.which('sshd') or '/usr/sbin/sshd'
    self.assertTrue(os.path.exists(sshd), "no sshd binary found for the test fixture")

    ssh_dir = tempfile.mkdtemp(prefix='backupserver-rdiffversion-sshd-')
    self.addCleanup(shutil.rmtree, ssh_dir, ignore_errors=True)

    host_key = os.path.join(ssh_dir, 'host_key')
    subprocess.check_call(
      [ssh_keygen, '-q', '-N', '', '-t', 'ed25519', '-f', host_key])

    authorized_keys = os.path.join(ssh_dir, 'authorized_keys')
    with open(authorized_keys, 'w') as f:
      f.write('\n'.join(authorized_key_list) + '\n')

    sshd_config = os.path.join(ssh_dir, 'sshd_config')
    with open(sshd_config, 'w') as f:
      f.write(
        'Port %s\n'
        'ListenAddress 127.0.0.1\n'
        'HostKey %s\n'
        'AuthorizedKeysFile %s\n'
        'PubkeyAuthentication yes\n'
        'PasswordAuthentication no\n'
        'UsePAM no\n'
        'StrictModes no\n'
        'PidFile %s\n'
        'LogLevel ERROR\n' % (
          self._ssh_port, host_key, authorized_keys,
          os.path.join(ssh_dir, 'sshd.pid')))

    def stopSshdFixture(process, log_file):
      process.terminate()
      process.wait()
      log_file.close()

    sshd_log = open(os.path.join(ssh_dir, 'sshd.log'), 'w')
    process = subprocess.Popen(
      [sshd, '-D', '-e', '-f', sshd_config],
      stdout=sshd_log, stderr=subprocess.STDOUT)
    self.addCleanup(stopSshdFixture, process, sshd_log)

    for _ in range(100):
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', self._ssh_port)) == 0:
          break
      time.sleep(0.1)
    else:
      self.fail("sshd fixture did not start listening on port %s" % self._ssh_port)

  def test(self):
    # Phase 1: the slaves were first requested without knowing which exact
    # rdiff-backup binary path each one's generated script resolved to
    # (bare "rdiff-backup" only resolves correctly through a PATH lookup,
    # which this test's sshd fixture - a single login shared by all
    # slaves - cannot provide different answers for). Discover each binary
    # now, then re-request the slaves with remote_rdiff_path set so the
    # "remote" side invokes whatever version it is supposed to actually run
    # (REMOTE_ACTUAL_VERSION) - which for the rdiffwrong* slaves is, on
    # purpose, not the version they are themselves configured with
    # (CONFIGURED_VERSION).
    remote_rdiff_path = {
      slave_reference: self._getRdiffBackupBinary(
        slave_reference, self.REMOTE_ACTUAL_VERSION[slave_reference])
      for slave_reference in self.getSlaveReferenceList()
    }
    self.requestSlaves({
      slave_reference: {'remote_rdiff_path': path}
      for slave_reference, path in remote_rdiff_path.items()
    })
    self.waitForInstance()

    authorized_key_list = [
      self.getSlaveConnectionParameterDict(slave_reference)['authorized_key']
      for slave_reference in self.getSlaveReferenceList()
    ]
    self._startSshdFixture(authorized_key_list)

    for slave_reference in self.getSlaveReferenceList():
      script = self._getBackupScriptPath(slave_reference)
      if slave_reference in self.HANGING_SLAVE_REFERENCE_TUPLE:
        # This backup never completes (see HANGING_SLAVE_REFERENCE_TUPLE),
        # so run it in the background, give it a moment to reach the
        # "backup running" status line, then move on without waiting for it
        # to exit - it has to be killed explicitly during cleanup instead.
        process = subprocess.Popen(
          [script], start_new_session=True,
          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def killHangingBackup(process=process):
          try:
            os.killpg(process.pid, signal.SIGKILL)
          except ProcessLookupError:
            pass
          process.wait()
        self.addCleanup(killHangingBackup)
        # Make sure at least one whole minute of the "* * * * *" schedule
        # passes strictly after this backup started, so the promise's
        # periodicity check (prev_cron) has something to compare against.
        time.sleep(65)
      else:
        result = subprocess.run(
          [script], capture_output=True, text=True)
        # template-backup-script.sh.in never exits non-zero itself (its last
        # command is always one of the "backup success"/"backup failed"
        # echoes), so a rdiff-backup version mismatch is visible only in the
        # status log it writes, not in this returncode - check that first.
        self.assertEqual(
          0, result.returncode,
          "%s: backup-script itself errored out:\nstdout: %s\nstderr: %s" % (
            slave_reference, result.stdout, result.stderr))

      status_log = os.path.join(
        self.computer_partition_root_path, 'srv', 'status',
        '%s_status.txt' % self._getRenderedSlaveReference(slave_reference))
      with open(status_log) as f:
        status_content = f.read()

      restored_path = os.path.join(
        self.computer_partition_root_path,
        'srv', 'backup',
        '%s-backup-directory' % self._getRenderedSlaveReference(slave_reference),
        self._source_dir[slave_reference].lstrip('/'),
        'greeting.txt')

      promise_result = self._runPromise(slave_reference)

      if slave_reference in self.HANGING_SLAVE_REFERENCE_TUPLE:
        self.assertIn(
          'backup running', status_content,
          "%s: status log does not report the backup as running:\n%s" % (
            slave_reference, status_content))
        self.assertNotIn('backup failed', status_content)
        self.assertNotIn('backup success', status_content)
        self.assertFalse(
          os.path.exists(restored_path),
          "%s: %s was created despite the rdiff-backup version mismatch" % (
            slave_reference, restored_path))
        self.assertEqual(
          2, promise_result.returncode,
          "%s: backupserver_check_backup promise did not report the "
          "expected failure for a backup that never finished:\n"
          "stdout: %s\nstderr: %s" % (
            slave_reference, promise_result.stdout, promise_result.stderr))
      elif self.CONFIGURED_VERSION[slave_reference] == \
          self.REMOTE_ACTUAL_VERSION[slave_reference]:
        self.assertIn(
          'backup success', status_content,
          "%s: status log does not report success:\n%s" % (
            slave_reference, status_content))
        self.assertTrue(
          os.path.exists(restored_path),
          "%s: %s was not created, backup-script output:\nstdout: %s\n"
          "stderr: %s" % (
            slave_reference, restored_path, result.stdout, result.stderr))
        with open(restored_path) as f:
          self.assertEqual(self._source_content[slave_reference], f.read())
        self.assertEqual(
          0, promise_result.returncode,
          "%s: backupserver_check_backup promise unexpectedly reported a "
          "problem:\nstdout: %s\nstderr: %s" % (
            slave_reference, promise_result.stdout, promise_result.stderr))
      else:
        self.assertIn(
          'backup failed', status_content,
          "%s: status log does not report the expected failure "
          "(configured for rdiff-backup version %s, remote actually runs "
          "version %s):\n%s" % (
            slave_reference, self.CONFIGURED_VERSION[slave_reference],
            self.REMOTE_ACTUAL_VERSION[slave_reference], status_content))
        self.assertFalse(
          os.path.exists(restored_path),
          "%s: %s was created despite the rdiff-backup version mismatch" % (
            slave_reference, restored_path))
        self.assertEqual(
          2, promise_result.returncode,
          "%s: backupserver_check_backup promise did not report the "
          "expected failure for a rdiff-backup version mismatch:\n"
          "stdout: %s\nstderr: %s" % (
            slave_reference, promise_result.stdout, promise_result.stderr))
