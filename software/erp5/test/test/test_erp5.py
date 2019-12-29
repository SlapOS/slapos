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
from six.moves.urllib.parse import urljoin, urlparse
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
  def _checkERP5IsReachable(self, url):
    # What happens is that instanciation just create the services, but does not
    # wait for ERP5 to be initialized. When this test run ERP5 instance is
    # instanciated, but zope is still busy creating the site and haproxy replies
    # with 503 Service Unavailable, sometimes the first request is 404, so we
    # retry in a loop.
    # If we can move the "create site" in slapos node instance, then this retry loop
    # would not be necessary.
    for i in range(1, 60):
      r = requests.get(url, verify=False)  # XXX can we get CA from caucase already ?
      if r.status_code in (requests.codes.service_unavailable,
                           requests.codes.not_found):
        delay = i * 2
        self.logger.warn("ERP5 was not available, sleeping for %ds and retrying", delay)
        time.sleep(delay)
        continue
      if r.status_code != requests.codes.ok:
        r.raise_for_status()
      break

    self.assertIn("ERP5", r.text)

  def test_published_family_default_v6_is_reachable(self):
    """Tests the IPv6 URL published by the root partition is reachable.
    """
    param_dict = self.getRootPartitionConnectionParameterDict()
    self._checkERP5IsReachable(
      urljoin(param_dict['family-default-v6'], param_dict['site-id']))

  def test_published_family_default_v4_is_reachable(self):
    """Tests the IPv4 URL published by the root partition is reachable.
    """
    param_dict = self.getRootPartitionConnectionParameterDict()
    self._checkERP5IsReachable(
      urljoin(param_dict['family-default'], param_dict['site-id']))


class TestDefaultParameters(ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 can be instanciated with no parameters
  """
  __partition_reference__ = 'defp'


class TestMedusa(ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 Medusa server
  """
  __partition_reference__ = 'medusa'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({'wsgi': False})}


class TestApacheBalancerPorts(ERP5InstanceTestCase):
  """Instanciate with two zope families, this should create for each family:
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
    parsed = urlparse(url)
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

  def test_apache_listen(self):
    # We have 2 families, apache should listen to a total of 3 ports per family
    # normal access on ipv4 and ipv6 and test runner access on ipv4 only
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
    process_info, = [p for p in all_process_info if p['name'] == 'apache']
    apache_process = psutil.Process(process_info['pid'])
    self.assertEqual(
        sorted([socket.AF_INET] * 4 + [socket.AF_INET6] * 2),
        sorted([
            c.family
            for c in apache_process.connections()
            if c.status == 'LISTEN'
        ]))

  def test_haproxy_listen(self):
    # There is one haproxy per family
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
    process_info, = [
        p for p in all_process_info if p['name'].startswith('haproxy-')
    ]
    haproxy_process = psutil.Process(process_info['pid'])
    self.assertEqual([socket.AF_INET, socket.AF_INET], [
        c.family for c in haproxy_process.connections() if c.status == 'LISTEN'
    ])


class TestDisableTestRunner(ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 can be instanciated without test runner.
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

  def test_no_apache_testrunner_port(self):
    # Apache only listen on two ports, there is no apache ports allocated for test runner
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
    process_info, = [p for p in all_process_info if p['name'] == 'apache']
    apache_process = psutil.Process(process_info['pid'])
    self.assertEqual(
        sorted([socket.AF_INET, socket.AF_INET6]),
        sorted(
            c.family
            for c in apache_process.connections()
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
