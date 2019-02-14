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
import time
import subprocess

import requests

from utils import SlapOSInstanceTestCase


def subprocess_output(*args, **kwargs):
  prc = subprocess.Popen(
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    *args,
    **kwargs
  )

  out, err = prc.communicate()
  return out


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

  def getTrimmedProcessInfo(self):
    return '\n'.join(sorted([
      '%(group)s:%(name)s %(statename)s' % q for q
      in self.getSupervisorRPCServer().supervisor.getAllProcessInfo()]))

  def assertTestData(self, runtime_data, hash_value=None):
    filename = '%s.txt' % (self.id(),)
    test_data_file = os.path.join(
      os.path.dirname(os.path.realpath(__file__)), 'test_data', filename)
    try:
      test_data = open(test_data_file).read().strip()
    except IOError:
      test_data = ''

    if hash_value is not None:
      runtime_data = runtime_data.replace(hash_value, '{hash}')

    maxDiff = self.maxDiff
    self.maxDiff = None
    try:
      self.assertMultiLineEqual(
        test_data,
        runtime_data
      )
    except AssertionError:
      if os.environ.get('SAVE_TEST_DATA', '0') == '1':
        open(test_data_file, 'w').write(runtime_data.strip())
      raise
    finally:
      self.maxDiff = maxDiff

  def test_plugin_list(self):
    runtime_data = '\n'.join(sorted([
      q[len(self.instance_path) + 1:]
      for q in glob.glob(os.path.join(
        self.instance_path, '*', 'etc', 'plugin', '*'))
      if not q.endswith('pyc')  # ignore compiled python
    ]))

    self.assertTestData(runtime_data)

  def test_promise_list(self):
    runtime_data = '\n'.join(sorted([
      q[len(self.instance_path) + 1:]
      for q in glob.glob(os.path.join(
        self.instance_path, '*', 'etc', 'promise', '*'))]))

    self.assertTestData(runtime_data)

  def _test_file_list(self, slave_dir, IGNORE_PATH_LIST):
    runtime_data = []
    for slave_var in glob.glob(os.path.join(self.instance_path, '*', 'var')):
      for entry in os.walk(os.path.join(slave_var, slave_dir)):
        for filename in entry[2]:
          path = os.path.join(
            entry[0][len(self.instance_path) + 1:], filename)
          if not any([path.endswith(q) for q in IGNORE_PATH_LIST]):
            runtime_data.append(path)
    runtime_data = '\n'.join(sorted(runtime_data))
    self.assertTestData(runtime_data)

  def test_file_list_log(self):
    self._test_file_list('log', [
      # no control at all when cron would kick in, ignore it
      'cron.log',
    ])

  def test_file_list_run(self):
    self._test_file_list('run', [
      # run by cron from time to time
      'monitor/monitor-collect.pid',
    ])

  def test_supervisor_state(self):
    # give a chance for etc/run scripts to finish
    time.sleep(1)

    hash_files = [
      'software_release/buildout.cfg',
    ]
    hash_files = [os.path.join(self.computer_partition_root_path, path)
                  for path in hash_files]
    h = self.generateHashFromFiles(hash_files)

    runtime_data = self.getTrimmedProcessInfo()
    self.assertTestData(runtime_data, hash_value=h)


class ERP5TestCase(SlapOSInstanceTestCase):
  """Test the remote driver on a minimal web server.
  """
  logger = logging.getLogger(__name__)

  @classmethod
  def exposeInstanceInfo(cls):
    logger = cls.logger
    ipv4 = os.environ['SLAPOS_TEST_IPV4']
    ipv6 = os.environ['SLAPOS_TEST_IPV6']
    logger.warning('IPv4 ports on %s' % (ipv4,))
    logger.warning(
      subprocess_output(('lsof -Pni@%s -a -sTCP:LISTEN' % (ipv4,)).split()))
    logger.warning('IPv6 ports on %s' % (ipv6,))
    logger.warning(
      subprocess_output(('lsof -Pni@[%s] -a -sTCP:LISTEN' % (ipv6,)).split()))

  @classmethod
  def setUpClass(cls):
    cls.exposeInstanceInfo()
    super(ERP5TestCase, cls).setUpClass()
    # expose instance directory
    cls.instance_path = os.path.join(
        cls.config['working_directory'],
        'inst')

  @classmethod
  def getSoftwareURLList(cls):
    return (os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'software.cfg')), )

  def getRootPartitionConnectionParameterDict(self):
    """Return the output paramters from the root partition"""
    return json.loads(
        self.computer_partition.getConnectionParameterDict()['_'])


class TestPublishedURLIsReachableMixin(object):
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


class TestDefaultParameters(ERP5TestCase, TestPublishedURLIsReachableMixin,
                            TestDataMixin):
  """Test ERP5 can be instanciated with no parameters
  """
  __partition_reference__ = 'defp'


class TestDisableTestRunner(ERP5TestCase, TestPublishedURLIsReachableMixin,
                            TestDataMixin):
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
