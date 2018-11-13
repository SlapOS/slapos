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

import requests

from utils import SlapOSInstanceTestCase


class ERP5TestCase(SlapOSInstanceTestCase):
  """Test the remote driver on a minimal web server.
  """
  @classmethod
  def getSoftwareURLList(cls):
    return (os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'software.cfg')), )

  def getRootPartitionConnectionParameterDict(self):
    """Return the output paramters from the root partition"""
    return json.loads(
        self.computer_partition.getConnectionParameterDict()['_'])


class TestPublishedURLIsReachableMixin(object):
  def _checkERP5IsReachable(self, url):
    r = requests.get(url, verify=False) # XXX can we get CA from caucase already ?
    self.assertEqual(r.status_code, requests.codes.ok)
    self.assertIn("ERP5", r.text)

  def test_published_family_default_v6_is_reachable(self):
    """Tests the IPv6 URL published by the root partition is reacheable.
    """
    param_dict = self.getRootPartitionConnectionParameterDict()
    self._checkERP5IsReachable(
      urlparse.urljoin(param_dict['family-default-v6'], param_dict['site-id']))

  def test_published_family_default_v4_is_reachable(self):
    """Tests the IPv4 URL published by the root partition is reacheable.
    """
    param_dict = self.getRootPartitionConnectionParameterDict()
    self._checkERP5IsReachable(
      urlparse.urljoin(param_dict['family-default'], param_dict['site-id']))


class TestDefaultParameters(ERP5TestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 can be instanciated with no parameters
  """


class TestDisableTestRunner(ERP5TestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 can be instanciated without test runner.
  """
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
