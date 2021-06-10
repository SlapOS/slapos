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

import json
import logging
import os
import re
import shutil
import subprocess
import textwrap
import time
import unittest

import pexpect
import psutil
import requests
import six

from six.moves.urllib.parse import urlparse, urljoin

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.grid.svcbackend import getSupervisorRPC, _getSupervisordSocketPath


software_cfg = 'software%s.cfg' % ('-py3' if six.PY3 else '')
theia_software_release_url = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', software_cfg))

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(theia_software_release_url)


class TheiaTestCase(SlapOSInstanceTestCase):
  __partition_reference__ = 'T' # for supervisord sockets in included slapos

  @classmethod
  def _getSlapos(cls):
    partition_root = cls.computer_partition_root_path
    slapos = os.path.join(partition_root, 'srv', 'runner', 'bin', 'slapos')
    return slapos


class TestTheia(TheiaTestCase):
  def setUp(self):
    self.connection_parameters = self.computer_partition.getConnectionParameterDict()

  def get(self, url, expect_code=requests.codes.ok):
    resp = requests.get(url, verify=False)
    self.assertEqual(
      expect_code,
      resp.status_code,
      '%s returned %d instead of %d' % (url, resp.status_code, expect_code),
    )
    return resp

  def test_backend_http_get(self):
    backend_url = self.connection_parameters['backend-url']
    self.get(backend_url, requests.codes.unauthorized)

    # with login/password, this is allowed
    parsed_url = urlparse(backend_url)
    authenticated_url = parsed_url._replace(
        netloc='{}:{}@[{}]:{}'.format(
            self.connection_parameters['username'],
            self.connection_parameters['password'],
            parsed_url.hostname,
            parsed_url.port,
        )).geturl()
    self.get(authenticated_url)

  def test_http_get(self):
    url = self.connection_parameters['url']
    self.get(url, requests.codes.unauthorized)

    # with login/password, this is allowed
    parsed_url = urlparse(self.connection_parameters['url'])
    authenticated_url = parsed_url._replace(
        netloc='{}:{}@[{}]:{}'.format(
            self.connection_parameters['username'],
            self.connection_parameters['password'],
            parsed_url.hostname,
            parsed_url.port,
        )).geturl()
    self.get(authenticated_url)

    # there's a public folder to serve file
    with open('{}/srv/frontend-static/public/test_file'.format(
        self.computer_partition_root_path), 'w') as f:
      f.write("hello")
    resp = self.get(urljoin(authenticated_url, '/public/'))
    self.assertIn('test_file', resp.text)
    resp = self.get(urljoin(authenticated_url, '/public/test_file'))
    self.assertEqual('hello', resp.text)

    # there's a (not empty) favicon
    resp = self.get(urljoin(authenticated_url, '/favicon.ico'))
    self.assertTrue(resp.raw)

    # there is a CSS referencing fonts
    css_text = self.get(urljoin(authenticated_url, '/css/slapos.css')).text
    css_urls = re.findall(r'url\([\'"]+([^\)]+)[\'"]+\)', css_text)
    self.assertTrue(css_urls)
    # and fonts are served
    for url in css_urls:
      resp = self.get(urljoin(authenticated_url, url))
      self.assertTrue(resp.raw)

  def test_theia_slapos(self):
    # Make sure we can use the shell and the integrated slapos command
    process = pexpect.spawnu(
        '{}/bin/theia-shell'.format(self.computer_partition_root_path),
        env={'HOME': self.computer_partition_root_path})

    # use a large enough terminal so that slapos proxy show table fit in the screen
    process.setwinsize(5000, 5000)

    # log process output for debugging
    logger = logging.getLogger('theia-shell')
    class DebugLogFile:
      def write(self, msg):
        logger.info("output from theia-shell: %s", msg)
      def flush(self):
        pass
    process.logfile = DebugLogFile()

    process.expect_exact('Standalone SlapOS for computer `slaprunner` activated')

    # try to supply and install a software to check that this slapos is usable
    process.sendline(
        'slapos supply https://lab.nexedi.com/nexedi/slapos/raw/1.0.144/software/helloworld/software.cfg slaprunner'
    )
    process.expect(
        'Requesting software installation of https://lab.nexedi.com/nexedi/slapos/raw/1.0.144/software/helloworld/software.cfg...'
    )

    # we pipe through cat to disable pager and prevent warnings like
    # WARNING: terminal is not fully functional
    process.sendline('slapos proxy show | cat')
    process.expect(
        'https://lab.nexedi.com/nexedi/slapos/raw/1.0.144/software/helloworld/software.cfg'
    )

    process.sendline('slapos node software')
    process.expect(
        'Installing software release https://lab.nexedi.com/nexedi/slapos/raw/1.0.144/software/helloworld/software.cfg'
    )
    # interrupt this, we don't want to actually wait for software installation
    process.sendcontrol('c')

    process.terminate()
    process.wait()

  def test_theia_shell_execute_tasks(self):
    # shell needs to understand -c "command" arguments for theia tasks feature
    test_file = '{}/test file'.format(self.computer_partition_root_path)
    subprocess.check_call([
        '{}/bin/theia-shell'.format(self.computer_partition_root_path),
        '-c',
        'touch "{}"'.format(test_file)
    ])
    self.assertTrue(os.path.exists(test_file))

  def test_theia_request_script(self):
    script_path = os.path.join(
      self.computer_partition_root_path,
      'srv',
      'project',
      'request-script-template.sh',
    )
    self.assertTrue(os.path.exists(script_path))

  def test_slapos_cli(self):
    slapos = self._getSlapos()
    proxy_show_output = subprocess.check_output((slapos, 'proxy', 'show'))
    self.assertIn(b'slaprunner', proxy_show_output)
    computer_list_output = subprocess.check_output((slapos, 'computer', 'list'))
    self.assertIn(b'slaprunner', computer_list_output)


class TestTheiaEmbeddedSlapOSShutdown(TheiaTestCase):
  def test_stopping_instance_stops_embedded_slapos(self):
    embedded_slapos_supervisord_socket = _getSupervisordSocketPath(
        os.path.join(
            self.computer_partition_root_path,
            'srv',
            'runner',
            'instance',
        ), self.logger)

    # Wait a bit for this supervisor to be started.
    for _ in range(20):
      if os.path.exists(embedded_slapos_supervisord_socket):
        break
      time.sleep(1)

    # get the pid of the supervisor used to manage instances
    with getSupervisorRPC(embedded_slapos_supervisord_socket) as embedded_slapos_supervisor:
      embedded_slapos_process = psutil.Process(embedded_slapos_supervisor.getPID())

    # Stop theia's services
    with self.slap.instance_supervisor_rpc as instance_supervisor:
      process_info, = [
          p for p in instance_supervisor.getAllProcessInfo()
          if p['name'].startswith('slapos-standalone-instance-')
      ]
      instance_supervisor.stopProcessGroup(process_info['group'])

    # the supervisor controlling instances is also stopped
    self.assertFalse(embedded_slapos_process.is_running())


class TestTheiaWithSR(TheiaTestCase):
  sr_url = 'bogus/software.cfg'
  sr_type = 'bogus_type'
  instance_parameters = '{\n"bogus_param": "bogus_value"\n}'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'embedded-sr': cls.sr_url,
      'embedded-sr-type': cls.sr_type,
      'embedded-instance-parameters': cls.instance_parameters
    }

  def test(self):
    slapos = self._getSlapos()
    info = subprocess.check_output((slapos, 'proxy', 'show'), universal_newlines=True)
    instance_name = "Embedded Instance"

    self.assertIsNotNone(re.search(r"%s\s+slaprunner\s+available" % (self.sr_url,), info), info)
    self.assertIsNotNone(re.search(r"%s\s+%s\s+%s" % (self.sr_url, self.sr_type, instance_name), info), info)

    service_info = subprocess.check_output((slapos, 'service', 'info', instance_name), universal_newlines=True)
    self.assertIn("{'bogus_param': 'bogus_value'}", service_info)


class TestTheiaFrontend(TheiaTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'additional-frontend-guid': 'SOMETHING'
    }

  def setUp(self):
    self.connection_parameters = self.computer_partition.getConnectionParameterDict()

  def test_http_get(self):
    for key in ('url', 'additional-url'):
      resp = requests.get(self.connection_parameters[key], verify=False)
      self.assertEqual(requests.codes.unauthorized, resp.status_code)


class TestTheiaEnv(TheiaTestCase):
  dummy_software_path = os.path.abspath('dummy/software.cfg')

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'embedded-sr': cls.dummy_software_path,
      'autorun': 'stopped',
    }

  def test_theia_env(self):
    # The path of the env.json file expected to be generated by building the dummy software release
    env_json_path = os.path.join(self.computer_partition_root_path, 'srv', 'runner', 'software', 'env.json')

    # Get the pid of the theia process from the test node's instance-supervisord
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
      for p in all_process_info:
        if p['name'].startswith('theia-instance'):
          theia_process = p
          break
      else:
        self.fail("Could not find theia process")
    theia_pid = theia_process['pid']

    # Get the environment of the theia process
    theia_env = psutil.Process(theia_pid).environ()

    # Start a theia shell that inherits the environment of the theia process
    # This simulates the environment of a shell launched from the browser application
    theia_shell_process = pexpect.spawnu('{}/bin/theia-shell'.format(self.computer_partition_root_path), env=theia_env)
    try:
      theia_shell_process.expect_exact('Standalone SlapOS for computer `slaprunner` activated')

      # Launch slapos node software from theia shell
      theia_shell_process.sendline('slapos node software')
      theia_shell_process.expect('Installing software release %s' % self.dummy_software_path)
      theia_shell_process.expect('Finished software releases.')

      # Get the theia shell environment
      with open(env_json_path) as f:
        theia_shell_env = json.load(f)

      # Remove the env.json file to later be sure that a new one has been generated
      os.remove(env_json_path)

      # Launch slapos-node-software from the embedded supervisord
      embedded_run_path = os.path.join(self.computer_partition_root_path, 'srv', 'runner', 'var', 'run')
      embedded_supervisord_socket_path = _getSupervisordSocketPath(embedded_run_path, self.logger)
      with getSupervisorRPC(embedded_supervisord_socket_path) as embedded_supervisor:
        previous_stop_time = embedded_supervisor.getProcessInfo('slapos-node-software')['stop']
        embedded_supervisor.startProcess('slapos-node-software')
        for _retries in range(20):
          time.sleep(1)
          if embedded_supervisor.getProcessInfo('slapos-node-software')['stop'] != previous_stop_time:
            break
        else:
          self.fail("the supervisord service 'slapos-node-software' takes too long to finish")

      # Get the supervisord environment
      with open(env_json_path) as f:
        supervisord_env = json.load(f)

      # Compare relevant variables from both environments
      self.maxDiff = None
      self.assertEqual(theia_shell_env['PATH'].split(':'), supervisord_env['PATH'].split(':'))
      self.assertEqual(theia_shell_env['SLAPOS_CONFIGURATION'], supervisord_env['SLAPOS_CONFIGURATION'])
      self.assertEqual(theia_shell_env['SLAPOS_CLIENT_CONFIGURATION'], supervisord_env['SLAPOS_CLIENT_CONFIGURATION'])
      self.assertEqual(theia_shell_env['HOME'], supervisord_env['HOME'])

    finally:
      # Cleanup the theia shell process
      theia_shell_process.terminate()
      theia_shell_process.wait()


class ResilientTheiaTestCase(TheiaTestCase):
  @classmethod
  def _getTypePartition(cls, software_type):
    software_url = cls.getSoftwareURL()
    for computer_partition in cls.slap.computer.getComputerPartitionList():
      partition_url = computer_partition.getSoftwareRelease()._software_release
      partition_type = computer_partition.getType()
      if partition_url == software_url and partition_type == software_type:
        return computer_partition
    raise "Theia %s partition not found" % software_type

  @classmethod
  def _getTypePartitionId(cls, software_type):
    return cls._getTypePartition(software_type).getId()

  @classmethod
  def _getTypePartitionPath(cls, software_type, *paths):
    return os.path.join(cls.slap._instance_root, cls._getTypePartitionId(software_type), *paths)

  @classmethod
  def _getSlapos(cls, software_type='export'):
    return cls._getTypePartitionPath(software_type, 'srv', 'runner', 'bin', 'slapos')

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
  def getInstanceSoftwareType(cls):
    return 'resilient'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'autorun': 'stopped'}


class TestTheiaResilientInterface(TestTheia, ResilientTheiaTestCase):
  @classmethod
  def setUpClass(cls):
    super(TestTheiaResilientInterface, cls).setUpClass()
    # Patch the computer root path to that of the export theia instance
    cls.computer_partition_root_path = cls._getTypePartitionPath('export')


class TestTheiaResilientWithSR(TestTheiaWithSR, ResilientTheiaTestCase):
  @classmethod
  def setUpClass(cls):
    super(TestTheiaResilientWithSR, cls).setUpClass()
    # Patch the computer root path to that of the export theia instance
    cls.computer_partition_root_path = cls._getTypePartitionPath('export')


class TheiaResilienceMixin(object):
  def _prepareExport(self):
    pass

  def _doBackup(self):
    raise NotImplementedError

  def _checkImport(self):
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
    self._doBackup()

    # Check that the export-backup-import process went well
    # e.g. look at logs and compare data
    self._checkImport()

    # Let the clone become a main instance
    # i.e. start embedded services
    self._doTakeover()

    # Check that the takeover went well
    # e.g. check services
    self._checkTakeover()


class TestTheiaExportImport(TheiaResilienceMixin, ResilientTheiaTestCase):
  _test_software_url = "https://lab.nexedi.com/xavier_thompson/slapos/raw/theia_resilience/software/theia/test/resilience_dummy/software.cfg"

  def _prepareExport(self):
    # Deploy dummy instance in export partition
    self._deployEmbeddedSoftware(self._test_software_url, 'dummy_instance')

    dummy_root = self._getTypePartitionPath('export', 'srv', 'runner', 'instance', 'slappart0')

    # Check that dummy instance was properly deployed
    log_path = os.path.join(dummy_root, 'log.log')
    with open(log_path) as f:
      initial_log = f.readlines()
    self.assertEqual(len(initial_log), 1)
    self.assertTrue(initial_log[0].startswith("Hello"), initial_log[0])
    self.initial_log = initial_log

    # Create ~/include and ~/include/included
    os.mkdir(os.path.join(dummy_root, 'include'))
    with open(os.path.join(dummy_root, 'include', 'included'), 'w') as f:
      f.write('This file should be included in resilient backup')
    self.assertTrue(os.path.exists(os.path.join(dummy_root, 'include', 'included')))

    # Create ~/exclude and ~/exclude/excluded
    os.mkdir(os.path.join(dummy_root, 'exclude'))
    with open(os.path.join(dummy_root, 'exclude', 'excluded'), 'w') as f:
      f.write('This file should be excluded from resilient backup')
    self.assertTrue(os.path.exists(os.path.join(dummy_root, 'exclude', 'excluded')))

    # Check that ~/srv/exporter.exclude and ~/srv/runner-import-restore exist
    self.assertTrue(os.path.exists(os.path.join(dummy_root, 'srv', 'exporter.exclude')))
    self.assertTrue(os.path.exists(os.path.join(dummy_root, 'srv', 'runner-import-restore')))

  def _doBackup(self):
    # Call export script manually
    theia_export_script = self._getTypePartitionPath('export', 'bin', 'theia-export-script')
    subprocess.check_call((theia_export_script,), stderr=subprocess.STDOUT)

    # Copy <export>/srv/backup/theia to <import>/srv/backup/theia manually
    export_backup_path = self._getTypePartitionPath('export', 'srv', 'backup', 'theia')
    import_backup_path = self._getTypePartitionPath('import', 'srv', 'backup', 'theia')
    shutil.rmtree(import_backup_path)
    shutil.copytree(export_backup_path, import_backup_path)

    # Call the import script manually
    theia_import_script = self._getTypePartitionPath('import', 'bin', 'theia-import-script')
    subprocess.check_call((theia_import_script,), stderr=subprocess.STDOUT)

  def _checkImport(self):
    dummy_root = self._getTypePartitionPath('import', 'srv', 'runner', 'instance', 'slappart0')

    # Check that the dummy instance is not yet started
    log_path = os.path.join(dummy_root, 'log.log')
    with open(log_path) as f:
      copied_log = f.readlines()
    self.assertEqual(copied_log, self.initial_log)

    # Check that ~/include and ~/include/included were included
    self.assertTrue(os.path.exists(os.path.join(dummy_root, 'include', 'included')))

    # Check that ~/exclude was excluded
    self.assertFalse(os.path.exists(os.path.join(dummy_root, 'exclude')))

    # Check that ~/srv/runner-import-restore was called
    restore_log_path = os.path.join(dummy_root, 'runner-import-restore.log')
    self.assertTrue(os.path.exists(restore_log_path))
    with open(restore_log_path) as f:
      restore_log = f.readlines()
    self.assertEqual(len(restore_log), 1)
    self.assertTrue(restore_log[0].startswith("Hello"), restore_log[0])

  def _doTakeover(self):
    # Start the dummy instance
    subprocess.check_call((self._getSlapos('import'), 'node', 'instance'))

  def _checkTakeover(self):
    # Check that dummy instance was properly re-deployed
    log_path = self._getTypePartitionPath('import', 'srv', 'runner', 'instance', 'slappart0', 'log.log')
    with open(log_path) as f:
      new_log = f.readlines()
    self.assertEqual(len(new_log), 2)
    self.assertEqual(new_log[0], self.initial_log[0])
    self.assertTrue(new_log[1].startswith("Hello"), new_log[1])


class TestTheiaExportImportLocalURL(TestTheiaExportImport):
  _test_software_url= None

  def _prepareExport(self):
    # Copy ./resilience_dummy SR in export theia ~/srv/project/dummy
    dummy_target_path = self._getTypePartitionPath('export', 'srv', 'project', 'dummy')
    shutil.copytree('resilience_dummy', dummy_target_path)
    self._test_software_url = os.path.join(dummy_target_path, 'software.cfg')

    super(TestTheiaExportImportLocalURL, self)._prepareExport()

  def _checkImport(self):
    # Check that the software url is correct
    test_adapted_url = self._getTypePartitionPath('import', 'srv', 'project', 'dummy', 'software.cfg')
    proxy_content = subprocess.check_output((self._getSlapos('import'), 'proxy', 'show'))
    self.assertIn(test_adapted_url, proxy_content)
    self.assertNotIn(self._test_software_url, proxy_content)

    super(TestTheiaExportImportLocalURL, self)._checkImport()


class TestTheiaBadRestoreScript(TestTheiaExportImportLocalURL):
  def _doBackup(self):
    # Call export script manually
    theia_export_script = self._getTypePartitionPath('export', 'bin', 'theia-export-script')
    subprocess.check_call((theia_export_script,), stderr=subprocess.STDOUT)

    # Copy <export>/srv/backup/theia to <import>/srv/backup/theia manually
    export_backup_path = self._getTypePartitionPath('export', 'srv', 'backup', 'theia')
    import_backup_path = self._getTypePartitionPath('import', 'srv', 'backup', 'theia')
    shutil.rmtree(import_backup_path)
    shutil.copytree(export_backup_path, import_backup_path)

    # Call the import script manually and check that it fails
    theia_import_script = self._getTypePartitionPath('import', 'bin', 'theia-import-script')
    self.assertRaises(
      subprocess.CalledProcessError,
      subprocess.check_call,
      (theia_import_script,),
      env={'TEST_RESTORE_STATUS': '1'},
      stderr=subprocess.STDOUT,
    )


class TakeoverMixin(object):
  def _getTakeoverUrlAndPassword(self, scope="theia-1"):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    takeover_url = parameter_dict["takeover-%s-url" % scope]
    takeover_password = parameter_dict["takeover-%s-password" % scope]
    return takeover_url, takeover_password

  def _getTakeoverPage(self, takeover_url):
    resp = requests.get(takeover_url, verify=True)
    self.assertEqual(requests.codes.ok, resp.status_code)
    return resp.text

  def _waitBackupStarted(self, takeover_url, wait=1, tries=1):
    for i in range(tries):
      if "No backup downloaded yet, takeover should not happen now." in self._getTakeoverPage(takeover_url):
        print("[attempt %d]: No backup downloaded yet, waiting a bit" % i)
        time.sleep(wait)
        continue
      print("[attempt %d]: Backup started, continuing" % i)
      break
    else:
      with open(self._getTypePartitionPath('import', 'var', 'log', 'equeue.log')) as f:
        log = f.read()
      self.fail("Backup did not start before timeout:\n%s" % log)

  def _waitBackupFinished(self, takeover_url, wait=1, tries=1):
    for i in range(tries):
      if "<b>Importer script(s) of backup in progress:</b> True" in self._getTakeoverPage(takeover_url):
        print("[attempt %d]: Backup in progress, waiting a bit" % i)
        time.sleep(wait)
        continue
      print("[attempt %d]: Backup finished, continuing" % i)
      break
    else:
      with open(self._getTypePartitionPath('import', 'var', 'log', 'equeue.log')) as f:
        log = f.read()
      self.fail("Backup did not finish before timeout:\n%s" % log)

  def _requestTakeover(self, takeover_url, takeover_password):
    resp = requests.get("%s?password=%s" % (takeover_url, takeover_password), verify=True)
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertNotIn("Error", resp.text, "An Error occured: %s" % resp.text)
    self.assertIn("Success", resp.text, "An Error occured: %s" % resp.text)
    return resp.text


class TestTheiaResilience(TheiaResilienceMixin, TakeoverMixin, ResilientTheiaTestCase):
  test_instance_max_retries = 0
  backup_started_tries = 50
  backup_finished_tries = 50
  backup_wait_interval = 10

  _test_software_url = "https://lab.nexedi.com/xavier_thompson/slapos/raw/theia_resilience/software/theia/test/resilience_dummy/software.cfg"

  def _prepareExport(self):
    # Deploy test instance
    self._deployEmbeddedSoftware(self._test_software_url, 'test_instance', self.test_instance_max_retries)

    # Check that there is an export and import instance and get their partition IDs
    self.export_id = self._getTypePartitionId('export')
    self.import_id = self._getTypePartitionId('import')

  def _doBackup(self):
    # Call exporter script instead of waiting for cron job
    # XXX Accelerate cron frequency instead ?
    exporter_script = self._getTypePartitionPath('export', 'bin', 'exporter')
    transaction_id = str(int(time.time()))
    subprocess.check_call((exporter_script, '--transaction-id', transaction_id))

    takeover_url, _ = self._getTakeoverUrlAndPassword()

    # Wait for importer to start and finish
    self._waitBackupStarted(takeover_url, self.backup_wait_interval, self.backup_started_tries)
    self._waitBackupFinished(takeover_url, self.backup_wait_interval, self.backup_finished_tries)

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
    new_export_id = self._getTypePartitionId('export')
    new_import_id = self._getTypePartitionId('import')
    new_frozen_id = self._getTypePartitionId('frozen')

    # Check that old export instance is now frozen
    self.assertEqual(export_id, new_frozen_id)

    # Check that old import instance is now the new export instance
    self.assertEqual(import_id, new_export_id)

    # Check that there is a new import instance
    self.assertNotIn(new_import_id, (export_id, new_export_id))

    # Check that the test instance is properly redeployed
    # This checks the promises of the test instance
    self._processEmbeddedInstance(self.test_instance_max_retries)
