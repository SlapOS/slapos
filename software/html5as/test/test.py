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
from urlparse import urlparse

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class HTML5ASTestCase(SlapOSInstanceTestCase):
  """
  Common class for testing html5as.
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


class TestEmptyDeploy(HTML5ASTestCase):
  """
  This class test the instance with no parameters.
  """

  def test_deploy_with_no_paramater(self):
    url = self.requestDefaultInstance().getConnectionParameterDict()['server_url']
    response = self.checkUrlAndGetResponse(url)
    result = response.text
    self.assertFalse("<h1>" in result)
    self.assertTrue("<p>Hello World</p>" in result)

class TestDeployWithTitle(HTML5ASTestCase):
  """
  This class test an instance with the parameter "title"
  """

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'title': 'Test1',
    }

  def test_deploy_with_title_parameter(self):
    connection_parameter_dict = self.computer_partition.getConnectionParameterDict()
    self.assertEqual(connection_parameter_dict["title"], "Title Test1!")
    url = connection_parameter_dict['server_url']
    response = self.checkUrlAndGetResponse(url)
    result = response.text
    self.assertTrue("<h1>Test1</h1>" in result)
    self.assertTrue("<p>Hello World</p>" in result)

class TestGracefulWithPortChange(HTML5ASTestCase):
  """
  This class test the instance with the parameter "port"
  """

  instance_parameter_dict = {
    'port': 8087
  }

  @classmethod
  def getInstanceParameterDict(cls):
    return cls.instance_parameter_dict

  def test_change_port_parameter(self):
    """
    This test test port change and its application with graceful restart
    """
    # Check initial connection parameter match expected port
    url = self.computer_partition.getConnectionParameterDict()['server_url']
    self.assertEqual(urlparse(url).port, 8087)
    # Check port is listening even thought it is duplicated with the promise:
    # "port-listening-promise"
    self.checkUrlAndGetResponse(url)

    # Update port parameter
    self.instance_parameter_dict.update({
      'port': 8086,

    })
    # Request instance with the new port parameter
    self.requestDefaultInstance()
    # Reprocess the instance to apply new port and run promises
    self.slap.waitForInstance(self.instance_max_retry)
    # Rerequest instance to get update connection parameter
    url = self.requestDefaultInstance().getConnectionParameterDict()['server_url']
    # Make sure the new port is the one being used
    self.assertEqual(urlparse(url).port, 8086)

    # Check port is listening even thought it is duplicated with the promise:
    # "port-listening-promise"
    self.checkUrlAndGetResponse(url)


class TestReplicateHTML5AS(HTML5ASTestCase):
  """
  This class test the instance with the parameter "port"
  """

  instance_parameter_dict = {
    "port-1": 8088,
    "title-1": "Title 1",
  }

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'replicate'

  @classmethod
  def getInstanceParameterDict(cls):
    return cls.instance_parameter_dict

  def test_replicate_instance(self):
   # Check First instance is deployed with proper parameters
    connection_parameter_dict = self.computer_partition.getConnectionParameterDict()
    url = connection_parameter_dict['instance-1-server_url']
    self.assertEqual(urlparse(url).port, 8088)
    response = self.checkUrlAndGetResponse(url)
    result = response.text
    self.assertTrue("<h1>Title 1</h1>" in result)

    # Check only one instance is deployed by default
    self.assertTrue("instance-2-server_url" not in connection_parameter_dict)

    # Update replicate quantity parameter
    self.instance_parameter_dict.update({
      'replicate-quantity': 2,
      'port-2': 8089,
      'sla-2-computer_guid': self.slap._computer_id,
    })
    # Request instance with the one more replicate
    self.requestDefaultInstance()
    self.slap.waitForInstance(self.instance_max_retry)

    # Check the second replicate
    connection_parameter_dict = self.requestDefaultInstance().getConnectionParameterDict()
    url = connection_parameter_dict['instance-2-server_url']
    self.assertEqual(urlparse(url).port, 8089)
    response = self.checkUrlAndGetResponse(url)
    result = response.text
    self.assertTrue("<h1>Title 2</h1>" in result)
