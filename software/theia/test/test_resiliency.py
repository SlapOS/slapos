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
from __future__ import unicode_literals

import errno
import os
import re
import shutil
import subprocess
import time

import requests

from slapos.testing.testcase import SlapOSNodeCommandError, installSoftwareUrlList

from test import TheiaTestCase, ResilientTheiaMixin, theia_software_release_url


class WorkaroundSnapshotConflict(TheiaTestCase):
  @classmethod
  def _copySnapshot(cls, source_file_name, name):
    # Workaround setUpModule snapshots name conflicts
    if not name.startswith(cls.__module__):
      name = '%s.%s' % (cls.__module__, name)
    super(WorkaroundSnapshotConflict, cls)._copySnapshot(source_file_name, name)


def setUpModule():
  installSoftwareUrlList(
    WorkaroundSnapshotConflict,
    [theia_software_release_url],
    debug=bool(int(os.environ.get('SLAPOS_TEST_DEBUG', 0))),
  )


class ResilientTheiaTestCase(ResilientTheiaMixin, TheiaTestCase):
  @classmethod
  def _processEmbeddedInstance(cls, retries=0, software_type='export'):
    slapos = cls._getSlapos(software_type)
    for _ in range(retries):
      try:
        output = subprocess.check_output((slapos, 'node', 'instance'), stderr=subprocess.STDOUT)
      except subprocess.CalledProcessError:
        continue
      print(output)
      break
    else:
      # Sleep a bit as an attempt to workaround monitoring boostrap not being ready
      print("Wait before running slapos node instance one last time")
      time.sleep(120)
      subprocess.check_call((slapos, 'node', 'instance'))

  @classmethod
  def _deployEmbeddedSoftware(cls, software_url, instance_name, retries=0, software_type='export'):
    slapos = cls._getSlapos(software_type)
    subprocess.check_call((slapos, 'supply', software_url, 'slaprunner'))
    try:
      subprocess.check_output((slapos, 'node', 'software'), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      print(e.output)
      raise
    subprocess.check_call((slapos, 'request', instance_name, software_url))
    cls._processEmbeddedInstance(retries, software_type)

  @classmethod
  def getInstanceParameterDict(cls):
    return {'autorun': 'stopped'}


class ResilienceMixin(object):
  def _prepareExport(self):
    pass

  def _doSync(self):
    raise NotImplementedError

  def _checkSync(self):
    pass

  def _doTakeover(self):
    raise NotImplementedError

  def _checkTakeover(self):
    pass

  def test(self):
    # Do stuff on the main instance
    # e.g. deploy an embedded software instance
    self._prepareExport()

    # Backup the main instance to a clone
    # i.e. call export and import scripts
    self._doSync()

    # Check that the export-backup-import process went well
    # e.g. look at logs and compare data
    self._checkSync()

    # Let the clone become a main instance
    # i.e. start embedded services
    self._doTakeover()

    # Check that the takeover went well
    # e.g. check services
    self._checkTakeover()


class ExportAndImportMixin(object):
  promise_period = 120

  def export_exitfile(self):
    return self._getPartitionPath('export', 'srv', 'export-exitcode-file')

  def export_errorfile(self):
    return self._getPartitionPath('export', 'srv', 'export-errormessage-file')

  def export_promise_script(self):
    return self._getPartitionPath('export', 'srv', 'export-promise-script')

  def import_exitfile(self):
    return self._getPartitionPath('import', 'srv', 'import-exitcode-file')

  def import_errorfile(self):
    return self._getPartitionPath('import', 'srv', 'import-errormessage-file')

  def import_promise_script(self):
    return self._getPartitionPath('import', 'srv', 'import-promise-script')

  def makedirs(self, path):
    try:
      os.makedirs(path if os.path.isdir(path) else os.path.dirname(path))
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise

  def writeFile(self, path, content, mode='w'):
    self.makedirs(path)
    executable = mode == 'exec'
    mode = 'w' if executable else mode
    with open(path, mode) as f:
      if executable:
        f.write('#!/bin/sh\n')
      f.write(content)
    if executable:
      os.chmod(path, 0o700)

  def assertPromiseSucess(self, t=120):
    # Wait until promise expires
    if t > 0:
      time.sleep(t)
    try:
      self.slap.waitForInstance(error_lines=0)
    except SlapOSNodeCommandError as e:
      s = str(e)
      self.assertNotIn("Promise 'resiliency-export-promise.py' failed", s)
      self.assertNotIn('ERROR export script', s)
      self.assertNotIn("Promise 'resiliency-import-promise.py' failed", s)
      self.assertNotIn('ERROR import script', s)
    else:
      pass

  def _doExport(self):
    t = time.time() + self.promise_period

    # Compute last modification of the export exitcode file
    exitfile = self.export_exitfile()
    initial_exitdate = os.path.getmtime(exitfile)

    # Call export script manually
    theia_export_script = self._getPartitionPath('export', 'bin', 'theia-export-script')
    subprocess.check_call((theia_export_script,), stderr=subprocess.STDOUT)

    # Check that the export exitcode file was modified
    self.assertGreater(os.path.getmtime(exitfile), initial_exitdate)
    with open(exitfile) as f:
      self.assertEquals('0', f.read())

    # Check promises
    self.assertPromiseSucess(t - time.time())

  def _doTransfer(self):
    # Copy <export>/srv/backup/theia to <import>/srv/backup/theia manually
    export_backup_path = self._getPartitionPath('export', 'srv', 'backup', 'theia')
    import_backup_path = self._getPartitionPath('import', 'srv', 'backup', 'theia')
    shutil.rmtree(import_backup_path)
    shutil.copytree(export_backup_path, import_backup_path)

  def _doImport(self):
    t = time.time() + self.promise_period

    # Compute last modification of the import exitcode file
    exitfile = self.import_exitfile()
    initial_exitdate = os.path.getmtime(exitfile)

    # Call the import script manually
    theia_import_script = self._getPartitionPath('import', 'bin', 'theia-import-script')
    subprocess.check_call((theia_import_script,), stderr=subprocess.STDOUT)

    # Check that the import exitcode file was updated
    self.assertGreater(os.path.getmtime(exitfile), initial_exitdate)
    with open(exitfile) as f:
      self.assertEquals('0', f.read())

    # Check promises
    self.assertPromiseSucess(t - time.time())


class TestTheiaExportAndImportFailures(ExportAndImportMixin, ResilientTheiaTestCase):
  script_relpath = os.path.join(
    'srv', 'runner', 'instance', 'slappart0',
    'srv', '.backup_identity_script')

  def assertPromiseFailure(self, *msg):
    # Wait until promise expires
    time.sleep(self.promise_period)
    try:
      self.slap.waitForInstance(error_lines=0)
    except SlapOSNodeCommandError as e:
      s = str(e).replace('\\n', '\n')
      for m in msg:
        self.assertIn(m, s)
    else:
      self.fail('No promise failed')

  def assertScriptFailure(self, func, errorfile, exitfile, *msg):
    self.assertRaises(
      subprocess.CalledProcessError,
      func,
    )
    if msg:
      with open(errorfile) as f:
        error = f.read()
      for m in msg:
        self.assertIn(m, error)
    with open(exitfile) as f:
      self.assertNotEqual('0', f.read())

  def assertExportFailure(self, *msg):
    self.assertScriptFailure(
      self._doExport,
      self.export_errorfile(),
      self.export_exitfile(),
      *msg)
    self.assertPromiseFailure('ERROR export script failed', *msg)

  def assertImportFailure(self, *msg):
    self.assertScriptFailure(
      self._doImport,
      self.import_errorfile(),
      self.import_exitfile(),
      *msg)
    self.assertPromiseFailure('ERROR import script failed', *msg)

  def customScript(self, path, content=None):
    if content:
      self.writeFile(path, content, mode='exec')
    else:
      if os.path.exists(path):
        os.remove(path)

  def customSignatureScript(self, content=None):
    custom_script = self._getPartitionPath('export', self.script_relpath)
    self.customScript(custom_script, content)

  def customRestoreScript(self, content=None):
    restore_script = self._getPartitionPath('import', 'srv', 'runner-import-restore')
    self.customScript(restore_script, content)
    return restore_script

  def cleanup_exitfiles(self):
    self.writeFile(self.export_exitfile(), '0')
    self.writeFile(self.import_exitfile(), '0')

  def setUp(self):
    self.customSignatureScript(content=None)
    self.customRestoreScript(content=None)
    self.cleanup_exitfiles()

  def test_export_promise(self):
    self.writeFile(self.export_exitfile(), '1')
    self.assertPromiseFailure('ERROR export script failed')

  def test_import_promise(self):
    self.writeFile(self.import_exitfile(), '1')
    self.assertPromiseFailure('ERROR import script failed')

  def test_custom_hash_script(self):
    self.customSignatureScript(content='exit 1')
    backup_script = self._getPartitionPath(
      'export', 'srv', 'backup', 'theia', self.script_relpath)
    self.assertExportFailure('Compute backup signature\n ... ERROR !',
      'Custom signature script %s failed' % os.path.abspath(backup_script))

  def test_signature_mismatch(self):
    signature_file = self._getPartitionPath('import', 'srv', 'backup', 'theia', 'backup.signature')
    moved_file = self._getPartitionPath('import', 'srv', 'backup', 'backup.signature.moved')
    self.writeFile(moved_file, 'Bogus Hash\n', mode='a')
    os.rename(moved_file, signature_file)
    self.assertImportFailure('ERROR the backup signatures do not match')

  def test_restore_script_error(self):
    self._doExport()
    self._doTransfer()
    restore_script = self.customRestoreScript('exit 1')
    self.assertImportFailure('Run custom restore script %s\n ... ERROR !' % restore_script)


class TestTheiaExportAndImport(ResilienceMixin, ExportAndImportMixin, ResilientTheiaTestCase):
  def checkLog(self, log_path, initial=[], newline="Hello"):
    with open(log_path) as f:
      log = f.readlines()
    self.assertEqual(len(log), len(initial) + int(bool(newline)))
    for line, initial_line in zip(log, initial):
      self.assertEqual(line, initial_line)
    if newline:
      self.assertTrue(log[-1].startswith(newline), log[-1])
    return log

  def _prepareExport(self):
    # Copy ./resilience_dummy SR in export theia ~/srv/project/dummy
    dummy_target_path = self._getPartitionPath('export', 'srv', 'project', 'dummy')
    shutil.copytree('resilience_dummy', dummy_target_path)
    self._test_software_url = os.path.join(dummy_target_path, 'software.cfg')

    # Deploy dummy instance in export partition
    self._deployEmbeddedSoftware(self._test_software_url, 'dummy_instance')

    relpath_dummy = os.path.join('srv', 'runner', 'instance', 'slappart0')
    self.export_dummy_root = dummy_root = self._getPartitionPath('export', relpath_dummy)
    self.import_dummy_root = self._getPartitionPath('import', relpath_dummy)

    # Check that dummy instance was properly deployed
    self.initial_log = self.checkLog(os.path.join(dummy_root, 'log.log'))

    # Create ~/include and ~/include/included
    self.writeFile(os.path.join(dummy_root, 'include', 'included'),
      'This file should be included in resilient backup')

    # Create ~/exclude and ~/exclude/excluded
    self.writeFile(os.path.join(dummy_root, 'exclude', 'excluded'),
      'This file should be excluded from resilient backup')

    # Check that ~/srv/exporter.exclude and ~/srv/runner-import-restore
    # As well as ~/srv/.backup_identity_script
    self.assertTrue(os.path.exists(os.path.join(dummy_root, 'srv', 'exporter.exclude')))
    self.assertTrue(os.path.exists(os.path.join(dummy_root, 'srv', 'runner-import-restore')))
    self.assertTrue(os.path.exists(os.path.join(dummy_root, 'srv', '.backup_identity_script')))

  def _doSync(self):
    self._doExport()
    self._doTransfer()
    self._doImport()

  def _checkSync(self):
    dummy_root = self.import_dummy_root

    # Check that the software url is correct
    adapted_test_url = self._getPartitionPath('import', 'srv', 'project', 'dummy', 'software.cfg')
    proxy_content = subprocess.check_output(
      (self._getSlapos('import'), 'proxy', 'show'), universal_newlines=True)
    self.assertIn(adapted_test_url, proxy_content)
    self.assertNotIn(self._test_software_url, proxy_content)

    # Check that the dummy instance is not yet started
    self.checkLog(os.path.join(dummy_root, 'log.log'), self.initial_log, newline=None)

    # Check that ~/srv/.backup_identity_script was called
    signature = self._getPartitionPath('import', 'srv', 'backup', 'backup.signature.proof')
    with open(signature) as f:
      self.assertIn('Custom script', f.read())

    # Check that ~/include and ~/include/included were included
    self.assertTrue(os.path.exists(os.path.join(dummy_root, 'include', 'included')))

    # Check that ~/exclude was excluded
    self.assertFalse(os.path.exists(os.path.join(dummy_root, 'exclude')))

    # Check that ~/srv/runner-import-restore was called
    self.checkLog(os.path.join(dummy_root, 'runner-import-restore.log'))

  def _doTakeover(self):
    # Start the dummy instance as a sort of fake takeover
    subprocess.check_call((self._getSlapos('import'), 'node', 'instance'))

  def _checkTakeover(self):
    # Check that dummy instance was properly re-deployed
    log_path = os.path.join(self.import_dummy_root, 'log.log')
    self.checkLog(log_path, self.initial_log)


class TakeoverMixin(ExportAndImportMixin):
  def _getTakeoverUrlAndPassword(self, scope="theia-1"):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    takeover_url = parameter_dict["takeover-%s-url" % scope]
    takeover_password = parameter_dict["takeover-%s-password" % scope]
    return takeover_url, takeover_password

  def _getTakeoverPage(self, takeover_url):
    resp = requests.get(takeover_url, verify=True)
    self.assertEqual(requests.codes.ok, resp.status_code)
    return resp.text

  def _waitScriptDone(self, name, start, exitfile, errorfile, maxtries, interval):
    print('Wait until %s script has run' % name.lower())
    for t in range(maxtries):
      if os.path.getmtime(exitfile) < start:
        time.sleep(interval)
        continue
      with open(exitfile) as f:
        if f.read() == '0':
          print(name + 'script ran successfully')
          return maxtries - t
      print(name + ' script failed:\n')
      with open(errorfile):
        print(f.read())
      self.fail(name + ' script failed')
    self.fail(name + ' script did not finish before timeout')

  def _waitTakeoverReady(self, takeover_url, start, maxtries, interval):
    export_exitfile = self.export_exitfile()
    export_errorfile =  self.export_errorfile()
    tries = self._waitScriptDone(
      'Export', start, export_exitfile, export_errorfile, maxtries, interval)
    import_exitfile = self.import_exitfile()
    import_errorfile =  self.import_errorfile()
    tries = self._waitScriptDone(
      'Import', start, import_exitfile, import_errorfile, tries, interval)
    for _ in range(tries):
      info = self._getTakeoverPage(takeover_url)
      if "No backup downloaded yet, takeover should not happen now." in info:
        print('Takeover page still reports export script in progress')
      elif "<b>Importer script(s) of backup in progress:</b> True" in info:
        print('Takeover page still reports import script in progress')
      else:
        return
      time.sleep(interval)
    self.fail('Takeover page failed to report readiness')

  def _requestTakeover(self, takeover_url, takeover_password):
    resp = requests.get("%s?password=%s" % (takeover_url, takeover_password), verify=True)
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertNotIn("Error", resp.text, "An Error occured: %s" % resp.text)
    self.assertIn("Success", resp.text, "An Error occured: %s" % resp.text)
    return resp.text


class TestTheiaResilience(ResilienceMixin, TakeoverMixin, ResilientTheiaTestCase):
  test_instance_max_retries = 0
  backup_max_tries = 70
  backup_wait_interval = 10

  _test_software_url = "https://lab.nexedi.com/xavier_thompson/slapos/raw/theia_resilience/software/theia/test/resilience_dummy/software.cfg"

  def _prepareExport(self):
    # Deploy test instance
    self._deployEmbeddedSoftware(self._test_software_url, 'test_instance', self.test_instance_max_retries)

    # Check that there is an export and import instance and get their partition IDs
    self.export_id = self._getPartitionId('export')
    self.import_id = self._getPartitionId('import')

  def _doSync(self):
    start = time.time()

    # Call exporter script instead of waiting for cron job
    # XXX Accelerate cron frequency instead ?
    exporter_script = self._getPartitionPath('export', 'bin', 'exporter')
    transaction_id = str(int(time.time()))
    subprocess.check_call((exporter_script, '--transaction-id', transaction_id))

    takeover_url, _ = self._getTakeoverUrlAndPassword()

    # Wait for takoever to be ready
    self._waitTakeoverReady(takeover_url, start, self.backup_max_tries, self.backup_wait_interval)

  def _doTakeover(self):
    # Takeover
    takeover_url, takeover_password = self._getTakeoverUrlAndPassword()
    self._requestTakeover(takeover_url, takeover_password)

    # Wait for import instance to become export instance and new import to be allocated
    # This also checks that all promises of theia instances succeed
    self.slap.waitForInstance(self.instance_max_retry)
    self.computer_partition = self.requestDefaultInstance()

  def _checkTakeover(self):
    # Check that there is an export, import and frozen instance and get their new partition IDs
    import_id = self.import_id
    export_id = self.export_id
    new_export_id = self._getPartitionId('export')
    new_import_id = self._getPartitionId('import')
    new_frozen_id = self._getPartitionId('frozen')

    # Check that old export instance is now frozen
    self.assertEqual(export_id, new_frozen_id)

    # Check that old import instance is now the new export instance
    self.assertEqual(import_id, new_export_id)

    # Check that there is a new import instance
    self.assertNotIn(new_import_id, (export_id, new_export_id))

    # Check that the test instance is properly redeployed
    # This checks the promises of the test instance
    self._processEmbeddedInstance(self.test_instance_max_retries)
