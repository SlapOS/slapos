##############################################################################
#
# Copyright (c) 2022 Nexedi SA and Contributors. All Rights Reserved.
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


import contextlib
import datetime
import glob
import http.client
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest

import psutil
import requests
import urllib.parse
import xmlrpc.client
import urllib3
from slapos.testing.utils import CrontabMixin

from . import ERP5InstanceTestCase, setUpModule, matrix, default

setUpModule # pyflakes


class TestPublishedURLIsReachableMixin:
  """Mixin that checks that default page of ERP5 is reachable.
  """

  def _checkERP5IsReachable(self, base_url, site_id, verify):
    # We access ERP5 trough a "virtual host", which should make
    # ERP5 produce URLs using https://virtual-host-name:1234/virtual_host_root
    # as base.
    virtual_host_url = urllib.parse.urljoin(
        base_url,
        '/VirtualHostBase/https/virtual-host-name:1234/{}/VirtualHostRoot/_vh_virtual_host_root/'
        .format(site_id))

    # What happens is that instantiation just create the services, but does not
    # wait for ERP5 to be initialized. When this test run ERP5 instance is
    # instantiated, but zope is still busy creating the site and haproxy replies
    # with 503 Service Unavailable when zope is not started yet, with 404 when
    # erp5 site is not created, with 500 when mysql is not yet reachable, so we
    # configure this requests session to retry.
    # XXX we should probably add a promise instead
    with requests.Session() as session:
      session.mount(
          base_url,
          requests.adapters.HTTPAdapter(
              max_retries=urllib3.util.retry.Retry(
                  total=20,
                  backoff_factor=.5,
                  status_forcelist=(404, 500, 503))))

      r = session.get(virtual_host_url, verify=verify, allow_redirects=False)
      self.assertEqual(r.status_code, requests.codes.found)
      # access on / are redirected to login form, with virtual host preserved
      self.assertEqual(r.headers.get('location'), 'https://virtual-host-name:1234/virtual_host_root/login_form')

      # login page can be rendered and contain the text "ERP5"
      r = session.get(
          urllib.parse.urljoin(base_url, f'{site_id}/login_form'),
          verify=verify,
          allow_redirects=False,
      )
      self.assertEqual(r.status_code, requests.codes.ok)
      self.assertIn("ERP5", r.text)

  def test_published_family_default_v6_is_reachable(self):
    """Tests the IPv6 URL published by the root partition is reachable.
    """
    param_dict = self.getRootPartitionConnectionParameterDict()
    self._checkERP5IsReachable(
      param_dict['family-default-v6'],
      param_dict['site-id'],
      verify=False,
    )

  def test_published_family_default_v4_is_reachable(self):
    """Tests the IPv4 URL published by the root partition is reachable.
    """
    param_dict = self.getRootPartitionConnectionParameterDict()
    self._checkERP5IsReachable(
      param_dict['family-default'],
      param_dict['site-id'],
      verify=False,
    )


class TestDefaultParameters(ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 can be instantiated with no parameters
  """
  __partition_reference__ = 'defp'
  __test_matrix__ = matrix((default,))


class TestMedusa(ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 Medusa server
  """
  __partition_reference__ = 'medusa'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({'wsgi': False})}


class TestJupyter(ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 Jupyter notebook
  """
  __partition_reference__ = 'jupyter'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({'jupyter': {'enable': True}})}

  def test_jupyter_notebook_is_reachable(self):
    param_dict = self.getRootPartitionConnectionParameterDict()

    self.assertEqual(
      'https://[%s]:8888/tree' % self.computer_partition_ipv6_address,
      param_dict['jupyter-url']
    )

    result = requests.get(
      param_dict['jupyter-url'], verify=False, allow_redirects=False)
    self.assertEqual(
      [requests.codes.found, True, '/login?next=%2Ftree'],
      [result.status_code, result.is_redirect, result.headers['Location']]
    )


class TestBalancerPorts(ERP5InstanceTestCase):
  """Instantiate with two zope families, this should create for each family:
   - a balancer entry point with corresponding haproxy
   - a balancer entry point for test runner
  """
  __partition_reference__ = 'ap'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
        '_':
            json.dumps({
                "zope-partition-dict": {
                    "family1": {
                        "instance-count": 3,
                        "family": "family1"
                    },
                    "family2": {
                        "instance-count": 5,
                        "family": "family2"
                    },
                },
            })
    }

  def checkValidHTTPSURL(self, url):
    parsed = urllib.parse.urlparse(url)
    self.assertEqual(parsed.scheme, 'https')
    self.assertTrue(parsed.hostname)
    self.assertTrue(parsed.port)

  def test_published_family_parameters(self):
    # when we request two families, we have two published family-{family_name} URLs
    param_dict = self.getRootPartitionConnectionParameterDict()
    for family_name in ('family1', 'family2'):
      self.checkValidHTTPSURL(
          param_dict[f'family-{family_name}'])
      self.checkValidHTTPSURL(
          param_dict[f'family-{family_name}-v6'])

  def test_published_test_runner_url(self):
    # each family's also a list of test test runner URLs, by default 3 per family
    param_dict = self.getRootPartitionConnectionParameterDict()
    for family_name in ('family1', 'family2'):
      family_test_runner_url_list = param_dict[
          f'{family_name}-test-runner-url-list']
      self.assertEqual(3, len(family_test_runner_url_list))
      for url in family_test_runner_url_list:
        self.checkValidHTTPSURL(url)

  def test_zope_listen(self):
    # we requested 3 zope in family1 and 5 zopes in family2, we should have 8 zope running.
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
    self.assertEqual(
        3 + 5,
        len([p for p in all_process_info if p['name'].startswith('zope-')]))

  def test_haproxy_listen(self):
    # We have 2 families, haproxy should listen to a total of 3 ports per family
    # normal access on ipv4 and ipv6 and test runner access on ipv4 only
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
    process_info, = (p for p in all_process_info if p['name'].startswith('haproxy-'))
    haproxy_master_process = psutil.Process(process_info['pid'])
    haproxy_worker_process, = haproxy_master_process.children()
    self.assertEqual(
        sorted([socket.AF_INET] * 4 + [socket.AF_INET6] * 2),
        sorted(
            c.family
            for c in haproxy_worker_process.connections()
            if c.status == 'LISTEN'
        ))


class TestSeleniumTestRunner(ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 can be instantiated with selenium server for test runner.
  """
  __partition_reference__ = 'sel'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
        '_':
        json.dumps({
            'test-runner': {
                'selenium': {
                    "target": "selenium-server",
                    "server-url": "https://example.com",
                    "verify-server-certificate": False,
                    "desired-capabilities": {
                        "browserName": "firefox",
                        "version": "68.0.2esr",
                    }
                }
            }
        })
    }

  def test_test_runner_configuration_json_file(self):
    runUnitTest_script, = glob.glob(
        self.computer_partition_root_path + "/../*/bin/runUnitTest.real")
    config_file = None
    with open(runUnitTest_script) as f:
      for line in f:
        if 'ERP5_TEST_RUNNER_CONFIGURATION' in line:
          _, config_file = line.split('=')
    assert config_file
    with open(config_file.strip()) as f:
      self.assertEqual(
          f.read(),
          json.dumps(json.loads(self.getInstanceParameterDict()['_'])['test-runner'], sort_keys=True))


class TestDisableTestRunner(ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 can be instantiated without test runner.
  """
  __partition_reference__ = 'distr'
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({'test-runner': {'enabled': False}})}

  def test_no_runUnitTestScript(self):
    """No runUnitTest script should be generated in any partition.
    """
    # self.computer_partition_root_path is the path of root partition.
    # we want to assert that no scripts exist in any partition.
    bin_programs = list(map(os.path.basename,
      glob.glob(self.computer_partition_root_path + "/../*/bin/*")))

    self.assertTrue(bin_programs) # just to check the glob was correct.
    self.assertNotIn('runUnitTest', bin_programs)
    self.assertNotIn('runTestSuite', bin_programs)

  def test_no_haproxy_testrunner_port(self):
    # Haproxy only listen on two ports, there is no haproxy ports allocated for test runner
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
    process_info, = (p for p in all_process_info if p['name'].startswith('haproxy'))
    haproxy_master_process = psutil.Process(process_info['pid'])
    haproxy_worker_process, = haproxy_master_process.children()
    self.assertEqual(
        sorted([socket.AF_INET, socket.AF_INET6]),
        sorted(
            c.family
            for c in haproxy_worker_process.connections()
            if c.status == 'LISTEN'
        ))


class TestZopeNodeParameterOverride(ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test override zope node parameters
  """
  __partition_reference__ = 'override'
  __test_matrix__ = matrix((default,))

  @classmethod
  def getInstanceParameterDict(cls):
    # The following example includes the most commonly used options,
    # but not necessarily in a meaningful way.
    return {'_': json.dumps({
      "zodb": [{
        "type": "zeo",
        "server": {},
        "cache-size-bytes": "20MB",
        "cache-size-bytes!": [
          ("bb-0", 1<<20),
          ("bb-.*", "500MB"),
        ],
        "pool-timeout": "10m",
        "storage-dict": {
          "cache-size!": [
            ("a-.*", "50MB"),
          ],
        },
      }],
      "zope-partition-dict": {
          "a": {
              "instance-count": 3,
          },
          "bb": {
              "instance-count": 5,
              "port-base": 2300,
          },
      },
    })}

  def test_zope_conf(self):
    zeo_addr = json.loads(
        self.getComputerPartition('zodb').getConnectionParameter('_')
      )["storage-dict"]["root"]["server"]

    def checkParameter(line, kw):
      k, v = line.split()
      self.assertFalse(k.endswith('!'), k)
      try:
        expected = kw.pop(k)
      except KeyError:
        if k == 'server':
          return
      self.assertIsNotNone(expected)
      self.assertEqual(str(expected), v)

    def checkConf(zodb, storage):
      zodb["mount-point"] = "/"
      zodb["pool-size"] = 4
      zodb["pool-timeout"] = "10m"
      storage["storage"] = "root"
      storage["server"] = zeo_addr
      with open(f'{partition}/etc/zope-{zope}.conf') as f:
        conf = list(map(str.strip, f.readlines()))
      i = conf.index("<zodb_db root>") + 1
      conf = iter(conf[i:conf.index("</zodb_db>", i)])
      for line in conf:
        if line == '<zeoclient>':
          for line in conf:
            if line == '</zeoclient>':
              break
            checkParameter(line, storage)
          for k, v in storage.items():
            self.assertIsNone(v, k)
          del storage
        else:
          checkParameter(line, zodb)
      for k, v in zodb.items():
        self.assertIsNone(v, k)

    partition = self.getComputerPartitionPath('zope-a')
    for zope in range(3):
      checkConf({
          "cache-size-bytes": "20MB",
        }, {
          "cache-size": "50MB",
        })
    partition = self.getComputerPartitionPath('zope-bb')
    for zope in range(5):
      checkConf({
          "cache-size-bytes": "500MB" if zope else 1<<20,
        }, {
          "cache-size": None,
        })


class TestWatchActivities(ERP5InstanceTestCase):
  """Tests for bin/watch_activities scripts in zope partitions.
  """
  __partition_reference__ = 'wa'

  def test(self):
    # "watch_activities" scripts use watch command. We'll fake a watch command
    # that executes the actual command only once to check the output.
    tmpdir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, tmpdir)
    with open(os.path.join(tmpdir, 'watch'), 'w') as f:
      f.write("""#!/bin/sh

      if [ "$1" != "-n" ] || [ "$2" != "5" ]
      then
        echo unexpected arguments: "$1" "$2"
        exit 1
      fi
      shift
      shift

      exec bash -c "$@"
      """)
      os.fchmod(f.fileno(), 0o700)
    try:
      output = subprocess.check_output(
          [
              os.path.join(
                  self.getComputerPartitionPath('zope-1'),
                  'bin',
                  'watch_activities',
              )
          ],
          env=dict(os.environ,
                   PATH=os.pathsep.join([tmpdir, os.environ['PATH']])),
          stderr=subprocess.STDOUT,
          text=True,
      )
    except subprocess.CalledProcessError as e:
      self.fail(e.output)
    self.assertIn(' dict ', output)


class ZopeSkinsMixin:
  """Mixins with utility methods to test zope behaviors.
  """
  @classmethod
  def _setUpClass(cls):
    super()._setUpClass()
    cls._waitForActivities()

  @classmethod
  def _waitForActivities(cls, timeout=datetime.timedelta(minutes=10).total_seconds()):
    """Wait for ERP5 to be ready and have processed all activities.
    """
    for _ in range(int(timeout / 5)):
      with cls.getXMLRPCClient() as erp5_xmlrpc_client:
        try:
          if erp5_xmlrpc_client.portal_activities.countMessage() == 0:
            break
        except (xmlrpc.client.ProtocolError,
                xmlrpc.client.Fault,
                http.client.HTTPException):
          pass
      time.sleep(5)
    else:
      raise AssertionError("Timeout waiting for activities")

  @classmethod
  def _getAuthenticatedZopeUrl(cls, path, family_name='default'):
    """Returns a URL to access a zope family through balancer,
    with credentials in the URL.

    path is joined with urllib.parse.urljoin to the URL of the portal.
    """
    param_dict = cls.getRootPartitionConnectionParameterDict()
    parsed = urllib.parse.urlparse(param_dict['family-' + family_name])
    base_url = parsed._replace(
        netloc='{}:{}@{}:{}'.format(
            param_dict['inituser-login'],
            param_dict['inituser-password'],
            parsed.hostname,
            parsed.port,
        ),
        path=param_dict['site-id'] + '/',
    ).geturl()
    return urllib.parse.urljoin(base_url, path)

  @classmethod
  @contextlib.contextmanager
  def getXMLRPCClient(cls):
    # don't verify certificate
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    erp5_xmlrpc_client = xmlrpc.client.ServerProxy(
        cls._getAuthenticatedZopeUrl(''),
        context=ssl_context,
    )
    with erp5_xmlrpc_client:
      yield erp5_xmlrpc_client

  @classmethod
  def _addPythonScript(cls, script_id, params, body):
    with cls.getXMLRPCClient() as erp5_xmlrpc_client:
      custom = erp5_xmlrpc_client.portal_skins.custom
      try:
        custom.manage_addProduct.PythonScripts.manage_addPythonScript(
            script_id)
      except xmlrpc.client.ProtocolError as e:
        if e.errcode != 302:
          raise
      getattr(custom, script_id).ZPythonScriptHTML_editAction(
          '',
          '',
          params,
          body,
      )


class ZopeTestMixin(ZopeSkinsMixin, CrontabMixin):
  """Mixin class for zope features.
  """
  wsgi = NotImplemented # type: bool

  __partition_reference__ = 'z'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
        '_':
        json.dumps({
            "zope-partition-dict": {
                "default": {
                    "longrequest-logger-interval": 1,
                    "longrequest-logger-timeout": 1,
                },
                "multiple": {
                    "family": "multiple",
                    "instance-count": 3,
                    "port-base":  2210,
                },
            },
            "wsgi": cls.wsgi,
        })
    }

  @classmethod
  def _setUpClass(cls):
    super()._setUpClass()
    cls.zope_base_url = cls._getAuthenticatedZopeUrl('')
    param_dict = cls.getRootPartitionConnectionParameterDict()
    cls.zope_deadlock_debugger_url = cls._getAuthenticatedZopeUrl(
        '/manage_debug_threads?{deadlock-debugger-password}'.format(
        **param_dict))

    # a python script to verify activity processing
    cls._addPythonScript(
        script_id='ERP5Site_verifyActivityProcessing',
        params='mode',
        body='''if 1:
          import json
          portal = context.getPortalObject()
          if mode == "count":
            return json.dumps(dict(count=len(portal.portal_activities.getMessageList())))
          if mode == "activate":
            for _ in range(10):
              portal.portal_templates.activate(activity="SQLQueue").getTitle()
            return "activated"
          raise ValueError("Unknown mode: %s" % mode)
        ''',
    )
    cls.zope_verify_activity_processing_url = urllib.parse.urljoin(
        cls.zope_base_url,
        'ERP5Site_verifyActivityProcessing',
    )
    # a python script logging to event log
    cls._addPythonScript(
        script_id='ERP5Site_logMessage',
        params='name',
        body='''if 1:
            from erp5.component.module.Log import log
            return log("hello %s" % name)
        ''',
    )
    cls.zope_log_message_url = urllib.parse.urljoin(
        cls.zope_base_url,
        'ERP5Site_logMessage',
    )
    # a python script issuing a long request
    cls._addPythonScript(
        script_id='ERP5Site_executeLongRequest',
        params='',
        body='''if 1:
          import time
          for _ in range(5):
            time.sleep(1)
          return "done"
        ''',
    )
    cls.zope_long_request_url = urllib.parse.urljoin(
        cls.zope_base_url,
        'ERP5Site_executeLongRequest',
    )

  def setUp(self):
    super().setUp()
    # run logrotate a first time so that it create state files
    self._executeCrontabAtDate('logrotate', '2000-01-01')

  def tearDown(self):
    super().tearDown()
    # reset logrotate status
    logrotate_status = os.path.join(
        self.getComputerPartitionPath('zope-default'),
        'srv',
        'logrotate.status',
    )
    if os.path.exists(logrotate_status):
      os.unlink(logrotate_status)
    for logfile in glob.glob(
        os.path.join(
            self.getComputerPartitionPath('zope-default'),
            'srv',
            'backup',
            'logrotate',
            '*',
        )):
      os.unlink(logfile)
    for logfile in glob.glob(
        os.path.join(
            self.getComputerPartitionPath('zope-default'),
            'srv',
            'monitor',
            'private',
            'documents',
            '*',
        )):
      os.unlink(logfile)

  def _getCrontabCommand(self, crontab_name):
    # type: (str) -> str
    """Read a crontab and return the command that is executed.

    overloaded to use crontab from zope partition
    """
    with open(
        os.path.join(
            self.getComputerPartitionPath('zope-default'),
            'etc',
            'cron.d',
            crontab_name,
        )) as f:
      crontab_spec, = f.readlines()
    self.assertNotEqual(crontab_spec[0], '@', crontab_spec)
    return crontab_spec.split(None, 5)[-1]

  def test_event_log_rotation(self):
    requests.get(
        self.zope_log_message_url,
        params={
            "name": "world"
        },
        verify=False,
    ).raise_for_status()

    zope_event_log_path = os.path.join(
        self.getComputerPartitionPath('zope-default'),
        'var',
        'log',
        'zope-0-event.log',
    )
    with open(zope_event_log_path) as f:
      self.assertIn('hello world', f.read())

    self._executeCrontabAtDate('logrotate', '2050-01-01')
    # this logrotate leaves the log for the day as non compressed
    rotated_log_file = os.path.join(
        self.getComputerPartitionPath('zope-default'),
        'srv',
        'backup',
        'logrotate',
        'zope-0-event.log-20500101',
    )
    with open(rotated_log_file) as f:
      self.assertIn('hello world', f.read())

    requests.get(
        self.zope_log_message_url,
        params={
            "name": "le monde"
        },
        verify=False,
    ).raise_for_status()
    with open(zope_event_log_path) as f:
      self.assertNotIn('hello world', f.read())
    with open(zope_event_log_path) as f:
      self.assertIn('hello le monde', f.read())

    # on next day execution of logrotate, log files are compressed
    self._executeCrontabAtDate('logrotate', '2050-01-02')
    self.assertTrue(os.path.exists(rotated_log_file + '.xz'))
    self.assertFalse(os.path.exists(rotated_log_file))

  def test_access_log_rotation(self):
    requests.get(
        self.zope_base_url,
        verify=False,
        headers={
            'User-Agent': 'before rotation'
        },
    ).raise_for_status()

    zope_access_log_path = os.path.join(
        self.getComputerPartitionPath('zope-default'),
        'var',
        'log',
        'zope-0-Z2.log',
    )
    with open(zope_access_log_path) as f:
      self.assertIn('before rotation', f.read())

    self._executeCrontabAtDate('logrotate', '2050-01-01')
    # this logrotate leaves the log for the day as non compressed
    rotated_log_file = os.path.join(
        self.getComputerPartitionPath('zope-default'),
        'srv',
        'backup',
        'logrotate',
        'zope-0-Z2.log-20500101',
    )
    with open(rotated_log_file) as f:
      self.assertIn('before rotation', f.read())

    requests.get(
        self.zope_base_url,
        verify=False,
        headers={
            'User-Agent': 'after rotation'
        },
    ).raise_for_status()
    with open(zope_access_log_path) as f:
      self.assertNotIn('before rotation', f.read())
    with open(zope_access_log_path) as f:
      self.assertIn('after rotation', f.read())

    # on next day execution of logrotate, log files are compressed
    self._executeCrontabAtDate('logrotate', '2050-01-02')
    self.assertTrue(os.path.exists(rotated_log_file + '.xz'))
    self.assertFalse(os.path.exists(rotated_log_file))

  def test_long_request_log_rotation(self):
    requests.get(self.zope_long_request_url,
                 verify=False,
                 params={
                     'when': 'before rotation'
                 }).raise_for_status()

    zope_long_request_log_path = os.path.join(
        self.getComputerPartitionPath('zope-default'),
        'var',
        'log',
        'longrequest_logger_zope-0.log',
    )
    with open(zope_long_request_log_path) as f:
      self.assertIn('before rotation', f.read())

    self._executeCrontabAtDate('logrotate', '2050-01-01')
    # this logrotate leaves the log for the day as non compressed
    rotated_log_file = os.path.join(
        self.getComputerPartitionPath('zope-default'),
        'srv',
        'backup',
        'logrotate',
        'longrequest_logger_zope-0.log-20500101',
    )
    with open(rotated_log_file) as f:
      self.assertIn('before rotation', f.read())

    requests.get(
        self.zope_long_request_url,
        verify=False,
        params={
            'when': 'after rotation'
        },
    ).raise_for_status()
    with open(zope_long_request_log_path) as f:
      self.assertNotIn('before rotation', f.read())
    with open(zope_long_request_log_path) as f:
      self.assertIn('after rotation', f.read())

    # on next day execution of logrotate, log files are compressed
    self._executeCrontabAtDate('logrotate', '2050-01-02')
    self.assertTrue(os.path.exists(rotated_log_file + '.xz'))
    self.assertFalse(os.path.exists(rotated_log_file))

  def test_basic_authentication_user_in_access_log(self):
    param_dict = self.getRootPartitionConnectionParameterDict()
    requests.get(self.zope_base_url,
                 verify=False,
                 auth=requests.auth.HTTPBasicAuth(
                     param_dict['inituser-login'],
                     param_dict['inituser-password'],
                 )).raise_for_status()

    zope_access_log_path = os.path.join(
        self.getComputerPartitionPath('zope-default'),
        'var',
        'log',
        'zope-0-Z2.log',
    )
    with open(zope_access_log_path) as f:
      self.assertIn(param_dict['inituser-login'], f.read())

  def test_deadlock_debugger(self):
    dump_response = requests.get(
        self.zope_deadlock_debugger_url,
        verify=False,
    )
    dump_response.raise_for_status()
    self.assertIn('Thread ', dump_response.text)

  def test_activity_processing(self):
    def wait_for_activities(max_retries):
      for retry in range(max_retries):
        time.sleep(10)
        resp = requests.get(
            self.zope_verify_activity_processing_url,
            params={
                'mode': 'count',
                'retry': retry,
            },
            verify=False,
        )
        if not resp.ok:
          # XXX we start by flushing existing activities from site creation
          # and initial upgrader run. During this time it may happen that
          # ERP5 replies with site errors, we tolerate these errors and only
          # check the final state.
          continue
        count = resp.json()['count']
        if not count:
          break
      else:
        self.assertEqual(count, 0)

    wait_for_activities(60)
    requests.get(
        self.zope_verify_activity_processing_url,
        params={
            'mode': 'activate'
        },
        verify=False,
    ).raise_for_status()
    wait_for_activities(10)

  def test_multiple_zope_family_log_files(self):
    logfiles = [
      os.path.basename(p) for p in glob.glob(
        os.path.join(
          self.getComputerPartitionPath('zope-multiple'), 'var', 'log', '*'))
    ]
    self.assertEqual(
      sorted([l for l in logfiles if l.startswith('zope')]), [
        'zope-0-Z2.log',
        'zope-0-event.log',
        'zope-0-neo-root.log',
        'zope-1-Z2.log',
        'zope-1-event.log',
        'zope-1-neo-root.log',
        'zope-2-Z2.log',
        'zope-2-event.log',
        'zope-2-neo-root.log',
      ] if '_neo' in self.__class__.__name__ else [
        'zope-0-Z2.log',
        'zope-0-event.log',
        'zope-1-Z2.log',
        'zope-1-event.log',
        'zope-2-Z2.log',
        'zope-2-event.log',
      ])

class TestZopeMedusa(ZopeTestMixin, ERP5InstanceTestCase):
  wsgi = False


class TestZopeWSGI(ZopeTestMixin, ERP5InstanceTestCase):
  wsgi = True

  @unittest.expectedFailure
  def test_long_request_log_rotation(self):
    super().test_long_request_log_rotation()

  @unittest.expectedFailure
  def test_basic_authentication_user_in_access_log(self):
    super().test_basic_authentication_user_in_access_log()


class TestZopePublisherTimeout(ZopeSkinsMixin, ERP5InstanceTestCase):
  __partition_reference__ = 't'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
        '_':
        json.dumps({
            # a default timeout of 3
            "publisher-timeout": 3,
            # and a family without timeout
            "family-override": {
                "no-timeout": {
                    "publisher-timeout": None,
                },
            },
            "zope-partition-dict": {
                # a family to process activities, so that our test
                # does not hit a zope node processing activities
                "activity": {
                    "family": "activity",
                },
                "default": {
                    "family": "default",
                    "port-base": 2210,
                },
                "no-timeout": {
                    "family": "no-timeout",
                    "port-base": 22220,
                },
            },
        })
    }

  @classmethod
  def _setUpClass(cls):
    super()._setUpClass()
    cls._addPythonScript(
      'ERP5Site_doSlowRequest',
      '',
      '''if 1:
        import time
        def recurse(o):
          time.sleep(0.1)
          for sub in o.objectValues():
            recurse(sub)
        recurse(context.getPortalObject())
      '''
    )

  def test_long_request_interupted_on_default_family(self):
    ret = requests.get(self._getAuthenticatedZopeUrl(
      'ERP5Site_doSlowRequest', family_name='default'), verify=False)
    self.assertIn('TimeoutReachedError', ret.text)
    self.assertEqual(ret.status_code, requests.codes.server_error)

  def test_long_request_not_interupted_on_no_timeout_family(self):
    with self.assertRaises(requests.exceptions.Timeout):
      requests.get(
        self._getAuthenticatedZopeUrl('ERP5Site_doSlowRequest', family_name='no-timeout'),
        verify=False,
        timeout=6)


class TestCloudooo(ZopeSkinsMixin, ERP5InstanceTestCase):
  """Test ERP5 can be instantiated with cloudooo parameters
  """
  __partition_reference__ = 'c'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
        '_':
        json.dumps({
            'cloudooo-url-list': [
              'https://cloudooo1.example.com/',
              'https://cloudooo2.example.com/',
            ],
            'cloudooo-retry-count': 123,
        })
    }

  def test_cloudooo_url_list_preference(self):
    self.assertEqual(
      requests.get(
          self._getAuthenticatedZopeUrl(
            'portal_preferences/getPreferredDocumentConversionServerUrlList'),
          verify=False).text,
      "['https://cloudooo1.example.com/', 'https://cloudooo2.example.com/']")

  @unittest.expectedFailure # setting "retry" is not implemented
  def test_cloudooo_retry_count_preference(self):
    self.assertEqual(
      requests.get(
          self._getAuthenticatedZopeUrl(
            'portal_preferences/getPreferredDocumentConversionServerRetry'),
          verify=False).text,
      "123")


class TestCloudoooDefaultParameter(ZopeSkinsMixin, ERP5InstanceTestCase):
  """Test default ERP5 cloudooo parameters
  """
  __partition_reference__ = 'cd'

  def test_cloudooo_url_list_preference(self):
    self.assertIn(
      requests.get(
          self._getAuthenticatedZopeUrl(
            'portal_preferences/getPreferredDocumentConversionServerUrlList'),
          verify=False).text,
      [
        "['https://cloudooo1.erp5.net/', 'https://cloudooo.erp5.net/']",
        "['https://cloudooo.erp5.net/', 'https://cloudooo1.erp5.net/']",
      ])

  @unittest.expectedFailure # default value of "retry" does not match schema
  def test_cloudooo_retry_count_preference(self):
    self.assertEqual(
      requests.get(
          self._getAuthenticatedZopeUrl(
            'portal_preferences/getPreferredDocumentConversionServerRetry'),
          verify=False).text,
      "2")
