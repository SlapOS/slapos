##############################################################################
#
# Copyright (c) 2021 Nexedi SA and Contributors. All Rights Reserved.
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
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class HTML5ASBaseTestCase(SlapOSInstanceTestCase):
  """
  Common class for testing html5as base.
  It inherit from SlapOSInstanceTestCase which:
    * Install the software release.
    * Checks it compile without issue.
    * Deploy the instance
    * Check deployement works and promise pass
  For testing the deployement a different testing class will need to be set up
  per each variation of parameters the instance needs to be given.
  """

  def checkUrlAndGetResponse(self, url):
    """
    Common class to check an url and return the response
    """
    response = requests.get(url)
    self.assertEqual(requests.codes['OK'], response.status_code)
    return response


class TestEmptyDeploy(HTML5ASBaseTestCase):
  """
  This class test the instance with no parameters.
  """

  def test_deploy_with_no_paramater(self):
    """
    Get the connection URL and check it is accessible
    """
    url = self.requestDefaultInstance().getConnectionParameterDict()['server_url']
    response = self.checkUrlAndGetResponse(url)
    result = response.text
    self.assertEqual("Hello World!\n", result)