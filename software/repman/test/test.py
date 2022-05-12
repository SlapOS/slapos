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

import os
import time
from six.moves.urllib.parse import urljoin

import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestRepman(SlapOSInstanceTestCase):
  __partition_reference__ = 'R'
  # Repman need more deployments and a bit more time to be able to bootstrap correctly
  instance_max_retry = 20

  def setUp(self):
    self.url = self.computer_partition.getConnectionParameterDict()['url']

  def test_http_get(self):
    connection_parameter_dict = \
        self.computer_partition.getConnectionParameterDict()
    resp = requests.get(self.url, verify=False)
    self.assertEqual(resp.status_code, requests.codes.ok)

    resp = requests.post(
        urljoin(self.url, '/api/login'),
        json={
            'username': connection_parameter_dict['username'],
            'password': connection_parameter_dict['repman-password'],
        },
        verify=False,
    )
    self.assertEqual(resp.status_code, requests.codes.ok)

    token = resp.json()['token']
    headers = {"authorization": "Bearer " + token}

    for i in range(20):
      resp = requests.get(
          urljoin(self.url, '/api/clusters'),
          params={
              'query': '{"method":"GET","isArray":false}',
          },
          headers=headers,
          verify=False,
      )
      self.assertEqual(resp.status_code, requests.codes.ok)
      cluster, = resp.json()
      if cluster['isProvision'] and cluster['isFailable'] and not cluster['isDown']:
        break
      time.sleep(i)

    self.assertTrue(cluster['isProvision'])
    self.assertTrue(cluster['isFailable'])
    self.assertFalse(cluster['isDown'])

    resp = requests.get(
        urljoin(self.url, '/api/clusters/cluster1/status'),
        headers=headers,
        verify=False,
    )
    self.assertEqual(resp.status_code, requests.codes.ok)
    self.assertEqual(resp.json(), {"alive": "running"})
