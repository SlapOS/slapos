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
import logging
import socket
import subprocess
import time

import psutil
import requests

from utils import SlapOSInstanceTestCase


class ERP5TestCase(SlapOSInstanceTestCase):
  """Test the remote driver on a minimal web server.
  """
  logger = logging.getLogger(__name__)
  @classmethod
  def getSoftwareURLList(cls):
    return (os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'software.cfg')), )

  def getRootPartitionConnectionParameterDict(self):
    """Return the output paramters from the root partition"""
    return json.loads(
        self.computer_partition.getConnectionParameterDict()['_'])


def subprocess_status_output(*args, **kwargs):
  prc = subprocess.Popen(
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    *args,
    **kwargs)
  out, err = prc.communicate()
  return prc.returncode, out


class TestDataMixin(object):
  @staticmethod
  def generateHashFromFiles(file_list):
    import hashlib
    hasher = hashlib.md5()
    for path in file_list:
      with open(path, 'r') as afile:
        buf = afile.read()
      hasher.update("%s\n" % len(buf))
      hasher.update(buf)
    hash = hasher.hexdigest()
    return hash

  def assertTestData(self, runtime_data, hash_value_dict=None, msg=None):
    if hash_value_dict is None:
      hash_value_dict = {}
    filename = '%s.txt' % (self.id(),)
    test_data_file = os.path.join(
      os.path.dirname(os.path.realpath(__file__)), 'test_data', filename)

    try:
      test_data = open(test_data_file).read().strip()
    except IOError:
      test_data = ''

    for hash_type, hash_value in hash_value_dict.items():
      runtime_data = runtime_data.replace(hash_value, '{hash-%s}' % (
        hash_type),)

    maxDiff = self.maxDiff
    self.maxDiff = None
    longMessage = self.longMessage
    self.longMessage = True
    try:
      self.assertMultiLineEqual(
        test_data,
        runtime_data,
        msg=msg
      )
    except AssertionError:
      if os.environ.get('SAVE_TEST_DATA', '0') == '1':
        open(test_data_file, 'w').write(runtime_data.strip())
      raise
    finally:
      self.maxDiff = maxDiff
      self.longMessage = longMessage

  def test_promise_run_plugin(self):
    ignored_plugin_list = [
      '__init__.py',  # that's not a plugin
      'monitor-http-frontend.py',  # frontend not available, can't check
    ]
    runpromise_bin = glob.glob(os.path.join(
      self.working_directory, 'soft', '*', 'bin', 'monitor.runpromise'))[0]
    instance_path = os.path.join(self.working_directory, 'inst')
    partition_path_list = glob.glob(os.path.join(instance_path, '*'))
    promise_status_list = []
    msg = []
    for partition_path in sorted(partition_path_list):
      plugin_path_list = sorted(glob.glob(
          os.path.join(partition_path, 'etc', 'plugin', '*.py')
      ))
      strip = len(os.path.join(partition_path, 'etc', 'plugin')) + 1
      for plugin_path in plugin_path_list:
        monitor_conf = os.path.join(partition_path, 'etc', 'monitor.conf')
        plugin = plugin_path[strip:]
        if plugin in ignored_plugin_list:
          continue

        plugin_status, plugin_result = subprocess_status_output([
          runpromise_bin,
          '-c', monitor_conf,
          '--run-only', plugin,
          '--force',
          '--check-anomaly'
        ])
        if plugin_status == 1:
          msg.append(plugin_result)

        # sanity check
        if 'Checking promise %s' % plugin not in plugin_result:
          plugin_status = 1
          msg.append(plugin_result)
        promise_status_list.append(
          '%s: %s' % (
            plugin_path[len(instance_path) + 1:],
            plugin_status == 0 and 'OK' or 'ERROR'))

    if msg:
      msg = ''.join(msg).strip()
    self.assertTestData('\n'.join(promise_status_list), msg=(msg or None))

  def test_promise_run_promise(self):
    promise_path_list = glob.glob(
      os.path.join(self.working_directory, 'inst', '*', 'etc', 'promise'))
    self.assertEqual([], promise_path_list)


class TestPublishedURLIsReachableMixin(TestDataMixin):
  """Mixin that checks that default page of ERP5 is reachable.
  """
  def _checkERP5IsReachable(self, url):
    # What happens is that instanciation just create the services, but does not
    # wait for ERP5 to be initialized. When this test run ERP5 instance is
    # instanciated, but zope is still busy creating the site and haproxy replies
    # with 503 Service Unavailable.
    # If we can move the "create site" in slapos node instance, then this retry loop
    # would not be necessary.
    for i in range(1, 20):
      r = requests.get(url, verify=False) # XXX can we get CA from caucase already ?
      if r.status_code == requests.codes.service_unavailable:
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
      urlparse.urljoin(param_dict['family-default-v6'], param_dict['site-id']))

  def test_published_family_default_v4_is_reachable(self):
    """Tests the IPv4 URL published by the root partition is reachable.
    """
    param_dict = self.getRootPartitionConnectionParameterDict()
    self._checkERP5IsReachable(
      urlparse.urljoin(param_dict['family-default'], param_dict['site-id']))


class TestDefaultParameters(ERP5TestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 can be instanciated with no parameters
  """
  __partition_reference__ = 'defp'


class TestWSGI(ERP5TestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 WSGI server
  """
  __partition_reference__ = 'wsgi'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({'wsgi': True})}


class TestApacheBalancerPorts(ERP5TestCase):
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
    all_process_info = self.getSupervisorRPCServer(
    ).supervisor.getAllProcessInfo()
    self.assertEqual(
        3 + 5,
        len([p for p in all_process_info if p['name'].startswith('zope-')]))

  def test_apache_listen(self):
    # We have 2 families, apache should listen to a total of 3 ports per family
    # normal access on ipv4 and ipv6 and test runner access on ipv4 only
    all_process_info = self.getSupervisorRPCServer(
    ).supervisor.getAllProcessInfo()
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
    all_process_info = self.getSupervisorRPCServer(
    ).supervisor.getAllProcessInfo()
    process_info, = [
        p for p in all_process_info if p['name'].startswith('haproxy-')
    ]
    haproxy_process = psutil.Process(process_info['pid'])
    self.assertEqual([socket.AF_INET, socket.AF_INET], [
        c.family for c in haproxy_process.connections() if c.status == 'LISTEN'
    ])


class TestDisableTestRunner(ERP5TestCase, TestPublishedURLIsReachableMixin):
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
    bin_programs = [os.path.basename(path) for path in
      glob.glob("{}/../*/bin/*".format(self.computer_partition_root_path))]

    self.assertTrue(bin_programs) # just to check the glob was correct.
    self.assertNotIn('runUnitTest', bin_programs)
    self.assertNotIn('runTestSuite', bin_programs)

  def test_no_apache_testrunner_port(self):
    # Apache only listen on two ports, there is no apache ports allocated for test runner
    all_process_info = self.getSupervisorRPCServer(
    ).supervisor.getAllProcessInfo()
    process_info, = [p for p in all_process_info if p['name'] == 'apache']
    apache_process = psutil.Process(process_info['pid'])
    self.assertEqual(
        sorted([socket.AF_INET, socket.AF_INET6]),
        sorted([
            c.family
            for c in apache_process.connections()
            if c.status == 'LISTEN'
        ]))
