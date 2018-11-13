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
import unittest

import requests

from utils import SlapOSInstanceTestCase

debug_mode = os.environ.get('DEBUG')
# for development: debugging logs and install Ctrl+C handler
if debug_mode:
  import logging
  logging.basicConfig(level=logging.DEBUG)
  unittest.installHandler()


class ERP5TestCase(SlapOSInstanceTestCase):
  """Test the remote driver on a minimal web server.
  """
  @classmethod
  def getSoftwareURLList(cls):
    return (os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'software.cfg')), )


class TestPublishedURLIsReachableMixin(object):
  def test_published_url_is_reachable(self):
    """Tests the URL published by the root partition is reacheable.
    """
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    admin_url = parameter_dict['admin-url']

    r = requests.get(parameter_dict['url'])
    self.assertEqual(r.status_code, requests.codes.ok)
    self.assertIn("ERP5", r.text)


class TestDefaultParameters(ERP5TestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 can be instanciated with no parameters
  """


class TestDisableTestRunner(ERP5TestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 can be instanciated without test runner.
  """
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({'test-runner': {'enable': False}})}

  def test_no_runUnitTestScript(self):
    """No runUnitTest script should be generated.
    """
    bin_programs = [os.path.basename(path) for path in
      glob.glob("{}/*/bin/*".format(computer_partition_root_path))]

    self.assertTrue(bin_programs) # just to check the glob was correct.
    self.assertNotIn('runUnitTest', bin_programs)
    self.assertNotIn('runTestSuite', bin_programs)