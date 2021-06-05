##############################################################################
#
# Copyright (c) 2018 Nexedi SA and Contributors. All Rights Reserved.
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

import os
import json
import glob
import urlparse
import socket
import time

import psutil
import requests

from . import ERP5InstanceTestCase
from . import setUpModule
setUpModule # pyflakes


class TestPublishedURLIsReachableMixin(object):
  """Mixin that checks that default page of ERP5 is reachable.
  """

  def _checkERP5IsReachable(self, base_url, site_id, verify):
    # We access ERP5 trough a "virtual host", which should make
    # ERP5 produce URLs using https://virtual-host-name:1234/virtual_host_root
    # as base.
    virtual_host_url = urlparse.urljoin(
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
    session = requests.Session()
    session.mount(
        base_url,
        requests.adapters.HTTPAdapter(
            max_retries=requests.packages.urllib3.util.retry.Retry(
                total=60,
                backoff_factor=.5,
                status_forcelist=(404, 500, 503))))

    r = session.get(virtual_host_url, verify=verify, allow_redirects=False)
    self.assertEqual(r.status_code, requests.codes.found)
    # access on / are redirected to login form, with virtual host preserved
    self.assertEqual(r.headers.get('location'), 'https://virtual-host-name:1234/virtual_host_root/login_form')

    # login page can be rendered and contain the text "ERP5"
    r = session.get(
        urlparse.urljoin(base_url, '{}/login_form'.format(site_id)),
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
      'https://[%s]:8888/tree' % self._ipv6_address,
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
    parsed = urlparse.urlparse(url)
    self.assertEqual(parsed.scheme, 'https')
    self.assertTrue(parsed.hostname)
    self.assertTrue(parsed.port)

  def test_published_family_parameters(self):
    # when we request two families, we have two published family-{family_name} URLs
    param_dict = self.getRootPartitionConnectionParameterDict()
    for family_name in ('family1', 'family2'):
      self.checkValidHTTPSURL(
          param_dict['family-{family_name}'.format(family_name=family_name)])
      self.checkValidHTTPSURL(
          param_dict['family-{family_name}-v6'.format(family_name=family_name)])

  def test_published_test_runner_url(self):
    # each family's also a list of test test runner URLs, by default 3 per family
    param_dict = self.getRootPartitionConnectionParameterDict()
    for family_name in ('family1', 'family2'):
      family_test_runner_url_list = param_dict[
          '{family_name}-test-runner-url-list'.format(family_name=family_name)]
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
    process_info, = [p for p in all_process_info if p['name'].startswith('haproxy-')]
    haproxy_master_process = psutil.Process(process_info['pid'])
    haproxy_worker_process, = haproxy_master_process.children()
    self.assertEqual(
        sorted([socket.AF_INET] * 4 + [socket.AF_INET6] * 2),
        sorted([
            c.family
            for c in haproxy_worker_process.connections()
            if c.status == 'LISTEN'
        ]))


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
          json.dumps(json.loads(self.getInstanceParameterDict()['_'])['test-runner']))


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
    bin_programs = map(os.path.basename,
      glob.glob(self.computer_partition_root_path + "/../*/bin/*"))

    self.assertTrue(bin_programs) # just to check the glob was correct.
    self.assertNotIn('runUnitTest', bin_programs)
    self.assertNotIn('runTestSuite', bin_programs)

  def test_no_haproxy_testrunner_port(self):
    # Haproxy only listen on two ports, there is no haproxy ports allocated for test runner
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
    process_info, = [p for p in all_process_info if p['name'].startswith('haproxy')]
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
      with open('%s/etc/zope-%s.conf' % (partition, zope)) as f:
        conf = map(str.strip, f.readlines())
      i = conf.index("<zodb_db root>") + 1
      conf = iter(conf[i:conf.index("</zodb_db>", i)])
      for line in conf:
        if line == '<zeoclient>':
          for line in conf:
            if line == '</zeoclient>':
              break
            checkParameter(line, storage)
          for k, v in storage.iteritems():
            self.assertIsNone(v, k)
          del storage
        else:
          checkParameter(line, zodb)
      for k, v in zodb.iteritems():
        self.assertIsNone(v, k)

    partition = self.getComputerPartitionPath('zope-a')
    for zope in xrange(3):
      checkConf({
          "cache-size-bytes": "20MB",
        }, {
          "cache-size": "50MB",
        })
    partition = self.getComputerPartitionPath('zope-bb')
    for zope in xrange(5):
      checkConf({
          "cache-size-bytes": "500MB" if zope else 1<<20,
        }, {
          "cache-size": None,
        })
