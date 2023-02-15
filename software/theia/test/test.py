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

import configparser
import json
import logging
import os
import re
import subprocess
import sqlite3
import time

import netaddr
import pexpect
import psutil
import requests
import six

from six.moves.urllib.parse import urlparse, urljoin

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass, SlapOSNodeCommandError
from slapos.grid.svcbackend import getSupervisorRPC, _getSupervisordSocketPath
from slapos.proxy.db_version import DB_VERSION
from slapos.slap.standalone import SlapOSConfigWriter


theia_software_release_url = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'software.cfg'))

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(theia_software_release_url)


class TheiaTestCase(SlapOSInstanceTestCase):
  __partition_reference__ = 'T' # for supervisord sockets in included slapos

  @classmethod
  def getPath(cls, *components):
    return os.path.join(cls.computer_partition_root_path, *components)

  @classmethod
  def _getSlapos(cls):
    try:
      return cls._theia_slapos
    except AttributeError:
      cls._theia_slapos = slapos = cls.getPath('srv', 'runner', 'bin', 'slapos')
      return slapos

  @classmethod
  def callSlapos(cls, *command, **kwargs):
    return subprocess.call((cls._getSlapos(),) + command, **kwargs)

  @classmethod
  def checkSlapos(cls, *command, **kwargs):
    return subprocess.check_call((cls._getSlapos(),) + command, **kwargs)

  @classmethod
  def captureSlapos(cls, *command, **kwargs):
    kwargs.setdefault('universal_newlines', kwargs.pop('text', None))
    return subprocess.check_output((cls._getSlapos(),) + command, **kwargs)

  @classmethod
  def requestInstance(cls, parameter_dict=None, state='started'):
    cls.slap.request(
      software_release=cls.getSoftwareURL(),
      software_type=cls.getInstanceSoftwareType(),
      partition_reference=cls.default_partition_reference,
      partition_parameter_kw=parameter_dict,
      state=state
    )

  @classmethod
  def restartService(cls, service):
    with cls.slap.instance_supervisor_rpc as supervisor:
      for process_info in supervisor.getAllProcessInfo():
        service_name = process_info['name']
        if service in service_name:
          service_id = '%s:%s' % (process_info['group'], service_name)
          supervisor.stopProcess(service_id)
          supervisor.startProcess(service_id)
          break
      else:
        raise Exception("Service %s not found" % service)


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

    # there's a public folder to serve file (no need for authentication)
    with open(self.getPath() + '/srv/frontend-static/public/test_file',
              'w') as f:
      f.write("hello")
    def get(path_info):
      resp = self.get(urljoin(url, path_info))
      self.assertIn('Content-Security-Policy', resp.headers)
      return resp.text
    self.assertIn('test_file', get('/public/'))
    self.assertEqual('hello', get('/public/test_file'))

    # there's a (not empty) favicon (no need for authentication)
    resp = self.get(urljoin(url, '/favicon.ico'))
    self.assertTrue(resp.raw)

    # there is a CSS referencing fonts
    css_text = self.get(urljoin(authenticated_url, '/css/slapos.css')).text
    css_urls = re.findall(r'url\([\'"]+([^\)]+)[\'"]+\)', css_text)
    self.assertTrue(css_urls)
    # and fonts are served
    for url in css_urls:
      resp = self.get(urljoin(authenticated_url, url))
      self.assertTrue(resp.raw)

  def test_ipv6_parameter_published(self):
    self.assertIn('ipv6', self.connection_parameters)

  def test_theia_slapos(self):
    home = self.getPath()
    # Make sure we can use the shell and the integrated slapos command
    process = pexpect.spawnu(home + '/bin/theia-shell', env={'HOME': home})

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
    home = self.getPath()
    # shell needs to understand -c "command" arguments for theia tasks feature
    test_file = home + '/test file'
    subprocess.check_call([
        home + '/bin/theia-shell',
        '-c',
        'touch "{}"'.format(test_file)
    ])
    self.assertTrue(os.path.exists(test_file))

  def test_theia_request_script(self):
    script_path = os.path.join(
      self.getPath(),
      'srv',
      'project',
      'request-script-example.sh',
    )
    self.assertTrue(os.path.exists(script_path))

  def test_slapos_cli(self):
    self.assertIn(b'slaprunner', self.captureSlapos('proxy', 'show'))
    self.assertIn(b'slaprunner', self.captureSlapos('computer', 'list'))

  def test_ipv6_range(self):
    proxy_path = self.getPath('srv', 'runner', 'var', 'proxy.db')
    query = "SELECT partition_reference, address FROM partition_network%s" % DB_VERSION

    with sqlite3.connect(proxy_path) as db:
      rows = db.execute(query).fetchall()
      partitions = set(p for p, _ in rows)
      ipv6 = set(addr for _, addr in rows if netaddr.valid_ipv6(addr))
      # Check that each partition has a different IPv6
      self.assertEqual(len(partitions), len(ipv6))
      # Check that no partition has the same IPv6 as theia
      self.assertNotIn(self.connection_parameters['ipv6'], ipv6)


class TestTheiaWithNonAsciiInstanceName(TestTheia):
  default_partition_reference = '💥'


class TestTheiaEmbeddedSlapOSShutdown(TheiaTestCase):
  def test_stopping_instance_stops_embedded_slapos(self):
    embedded_slapos_supervisord_socket = _getSupervisordSocketPath(
        os.path.join(
            self.getPath(),
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


class TestTheiaWithEmbeddedInstance(TheiaTestCase):
  sr_url = os.path.abspath('dummy/software.cfg')
  sr_type = 'dummy-type'
  sr_config = {"dummy": "yes"}
  regexpr = re.compile(r"([\w/\-\.]+)\s+slaprunner\s+available")

  @classmethod
  def getInstanceParameterDict(cls, sr_url=None, sr_type=None, sr_config=None):
    return {
      'initial-embedded-instance': json.dumps({
        'software-url': sr_url or cls.sr_url,
        'software-type': sr_type or cls.sr_type,
        'instance-parameters': sr_config or cls.sr_config,
      }),
    }

  def expandUrl(self, url):
    if url.startswith('~/'):
      url = os.path.join(self.getPath(), url[2:])
    return url

  def assertSupplied(self, sr_url, info=None):
    info = info or self.captureSlapos('proxy', 'show', text=True)
    self.assertIn(sr_url, info)
    self.assertIn(sr_url, self.regexpr.findall(info))

  def assertNotSupplied(self, sr_url, info=None):
    info = info or self.captureSlapos('proxy', 'show', text=True)
    self.assertNotIn(sr_url, info)

  def assertEmbedded(self, sr_url, sr_type, config):
    proxy_info = self.captureSlapos('proxy', 'show', text=True)
    self.assertSupplied(sr_url, info=proxy_info)
    name = 'embedded_instance'
    self.assertIn(name, self.captureSlapos('service', 'list', text=True))
    info = json.loads(self.captureSlapos('service', 'info', name, text=True))
    self.assertEqual(info['software-url'], sr_url)
    # XXX: slapos service info does not show the software type, so we check in
    # slapos proxy show output
    self.assertIn(sr_type, proxy_info)
    self.assertEqual(info['instance-parameters'], config)

  def assertNotEmbedded(self, sr_url, sr_type, config):
    sr_url = self.expandUrl(sr_url)
    proxy_info = self.captureSlapos('proxy', 'show', text=True)
    self.assertNotSupplied(sr_url, info=proxy_info)
    self.assertNotIn(sr_type, proxy_info)

  def test(self):
    # Check that embedded instance is supplied and requested
    initial_sr_url = self.expandUrl(self.sr_url)
    self.assertEmbedded(initial_sr_url, self.sr_type, self.sr_config)

    # Change parameters for embedded instance
    sr_url = os.path.abspath('bogus/software.cfg')
    sr_type = 'bogus-type'
    sr_config = {"bogus": "true"}
    self.requestInstance(
      self.getInstanceParameterDict(sr_url, sr_type, sr_config))
    self.waitForInstance()

    # Check that parameters have not been taken into account
    self.assertNotEmbedded(sr_url, sr_type, sr_config)

    # Check that previous instance has not been changed
    self.assertEmbedded(initial_sr_url, self.sr_type, self.sr_config)


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


class TestTheiaForwardFrontendRequestsEnabled(TheiaTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    return {"autorun": "user-controlled"} # we interact with slapos in this test

  def _getRequestedInstanceList(self, query):
    with sqlite3.connect(os.path.join(
        self.computer_partition_root_path,
        'srv/runner/var/proxy.db',
    )) as db:
      return [row[0] for row in db.execute(query).fetchall()]

  def getRequestedInstanceList(self):
    return self._getRequestedInstanceList(
      f"SELECT partition_reference FROM partition{DB_VERSION} where slap_state='busy'"
    )

  def getForwardedInstanceList(self):
    return self._getRequestedInstanceList(
      f"SELECT partition_reference FROM forwarded_partition_request{DB_VERSION}"
    )

  def requestEmbeddedFrontendInstance(self, state='available'):
    self.checkSlapos(
      'request',
      '--state',
      state,
      'frontend',
      'http://git.erp5.org/gitweb/slapos.git/blob_plain/HEAD:/software/apache-frontend/software.cfg',
    )

  def test(self):
    self.requestEmbeddedFrontendInstance()
    # partition requested directly by user are forwarded with user_ prefix
    self.assertEqual(self.getForwardedInstanceList(), ['user_frontend'])
    self.assertEqual(self.getRequestedInstanceList(), [])
    self.requestEmbeddedFrontendInstance(state='destroyed')

    self.requestInstance({'forward-slapos-frontend-requests': 'disabled'})
    self.waitForInstance()
    self.requestEmbeddedFrontendInstance()
    self.assertEqual(self.getForwardedInstanceList(), [])
    self.assertEqual(self.getRequestedInstanceList(), ['frontend'])
    self.requestEmbeddedFrontendInstance(state='destroyed')
    self.checkSlapos('node', 'report')

    self.requestInstance({'forward-slapos-frontend-requests': 'enabled'})
    self.waitForInstance()
    self.requestEmbeddedFrontendInstance()
    self.assertEqual(self.getForwardedInstanceList(), ['user_frontend'])
    self.assertEqual(self.getRequestedInstanceList(), [])


class TestTheiaEnv(TheiaTestCase):
  dummy_software_path = os.path.abspath('dummy/software.cfg')

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'initial-embedded-instance': json.dumps({
        'software-url': cls.dummy_software_path,
      }),
      'autorun': 'stopped',
    }

  def test_theia_env(self):
    """Make sure environment variables are the same whether we use shell or supervisor services.
    """
    # The path of the env.json file expected to be generated by building the dummy software release
    env_json_path = self.getPath('srv', 'runner', 'software', 'env.json')

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
    theia_shell_process = pexpect.spawnu('{}/bin/theia-shell'.format(self.getPath()), env=theia_env)
    self.addCleanup(theia_shell_process.wait)
    self.addCleanup(theia_shell_process.terminate)

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

    # Launch slapos node software service from the embedded supervisord.
    # Note that we have two services, slapos-node-software and slapos-node-software-all
    # The later uses --all which is what we want to use here, because the software
    # is already installed and we want to install it again, this time from supervisor
    embedded_run_path = self.getPath('srv', 'runner', 'var', 'run')
    embedded_supervisord_socket_path = _getSupervisordSocketPath(embedded_run_path, self.logger)
    with getSupervisorRPC(embedded_supervisord_socket_path) as embedded_supervisor:
      previous_stop_time = embedded_supervisor.getProcessInfo('slapos-node-software-all')['stop']
      embedded_supervisor.startProcess('slapos-node-software-all')
      for _retries in range(20):
        time.sleep(1)
        if embedded_supervisor.getProcessInfo('slapos-node-software-all')['stop'] != previous_stop_time:
          break
      else:
        self.fail("the supervisord service 'slapos-node-software-all' takes too long to finish")

    # Get the supervisord environment
    with open(env_json_path) as f:
      supervisord_env = json.load(f)

    # Compare relevant variables from both environments
    self.maxDiff = None
    self.assertEqual(theia_shell_env['PATH'].split(':'), supervisord_env['PATH'].split(':'))
    self.assertEqual(theia_shell_env['SLAPOS_CONFIGURATION'], supervisord_env['SLAPOS_CONFIGURATION'])
    self.assertEqual(theia_shell_env['SLAPOS_CLIENT_CONFIGURATION'], supervisord_env['SLAPOS_CLIENT_CONFIGURATION'])
    self.assertEqual(theia_shell_env['HOME'], supervisord_env['HOME'])


class TestTheiaSharedPath(TheiaTestCase):
  bogus_path = 'bogus'

  @classmethod
  def setUpClass(cls):
    super(TestTheiaSharedPath, cls).setUpClass()
    # Change shared part list to include bogus paths
    cls.slap._shared_part_list.append(cls.bogus_path)
    SlapOSConfigWriter(cls.slap).writeConfig(cls.slap._slapos_config)
    # Re-instanciate
    cls.slap._force_slapos_node_instance_all = True
    try:
      cls.waitForInstance()
    finally:
      cls.slap._force_slapos_node_instance_all = False

  def test(self):
    theia_cfg_path = self.getPath('srv', 'runner', 'etc', 'slapos.cfg')
    cfg = configparser.ConfigParser()
    cfg.read(theia_cfg_path)
    self.assertTrue(cfg.has_option('slapos', 'shared_part_list'))
    shared_parts_string = cfg.get('slapos', 'shared_part_list')
    shared_parts_list = [s.strip() for s in shared_parts_string.splitlines()]
    self.assertIn(self.bogus_path, shared_parts_list)


class ResilientTheiaMixin(object):
  @classmethod
  def setUpClass(cls):
    super(ResilientTheiaMixin, cls).setUpClass()
    # Patch the computer root path to that of the export theia instance
    cls.computer_partition_root_path = cls.getPartitionPath('export')
    # Add resiliency files to snapshot patterns
    cls._save_instance_file_pattern_list += (
      '*/srv/export-exitcode-file',
      '*/srv/export-errormessage-file',
      '*/srv/import-exitcode-file',
      '*/srv/import-errormessage-file',
    )

  @classmethod
  def getPartitionId(cls, instance_type):
    software_url = cls.getSoftwareURL()
    for computer_partition in cls.slap.computer.getComputerPartitionList():
      partition_url = computer_partition.getSoftwareRelease()._software_release
      partition_type = computer_partition.getType()
      if partition_url == software_url and partition_type == instance_type:
        return computer_partition.getId()
    raise Exception("Theia %s partition not found" % instance_type)

  @classmethod
  def getPartitionPath(cls, instance_type='export', *paths):
    return os.path.join(cls.slap._instance_root, cls.getPartitionId(instance_type), *paths)

  @classmethod
  def _getSlapos(cls, instance_type='export'):
    return cls.getPartitionPath(instance_type, 'srv', 'runner', 'bin', 'slapos')

  @classmethod
  def callSlapos(cls, *command, **kwargs):
    instance_type = kwargs.pop('instance_type', 'export')
    return subprocess.call((cls._getSlapos(instance_type),) + command, **kwargs)

  @classmethod
  def checkSlapos(cls, *command, **kwargs):
    instance_type = kwargs.pop('instance_type', 'export')
    return subprocess.check_call((cls._getSlapos(instance_type),) + command, **kwargs)

  @classmethod
  def captureSlapos(cls, *command, **kwargs):
    kwargs.setdefault('universal_newlines', kwargs.pop('text', None))
    instance_type = kwargs.pop('instance_type', 'export')
    return subprocess.check_output((cls._getSlapos(instance_type),) + command, **kwargs)

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'resilient'

  @classmethod
  def waitForInstance(cls):
    # process twice to propagate to all instances
    for _ in range(2):
      super(ResilientTheiaMixin, cls).waitForInstance()


class TestTheiaResilientInterface(ResilientTheiaMixin, TestTheia):
  pass


class TestTheiaResilientWithEmbeddedInstance(ResilientTheiaMixin, TestTheiaWithEmbeddedInstance):
  pass
