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
import requests
import functools
import bs4
from urllib.parse import urljoin

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestGitlab(SlapOSInstanceTestCase):
  __partition_reference__ = 'G'  # solve path too long for postgresql and unicorn

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'gitlab'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'root-password': 'admin1234'}

  def setUp(self):
    self.backend_url = self.computer_partition.getConnectionParameterDict(
    )['backend_url']

  def test_http_get(self):
    resp = requests.get(self.backend_url, verify=False)
    self.assertTrue(
      resp.status_code in [requests.codes.ok, requests.codes.found])

  def test_rack_attack_sign_in_rate_limiting(self):
    session = requests.session()

    # Load the login page to get a CSRF token.
    response = session.get(urljoin(self.backend_url, 'users/sign_in'), verify=False)
    self.assertEqual(response.status_code, 200)

    # Extract the CSRF token and param.
    bsoup = bs4.BeautifulSoup(response.text, 'html.parser')
    csrf_param = bsoup.find('meta', dict(name='csrf-param'))['content']
    csrf_token = bsoup.find('meta', dict(name='csrf-token'))['content']

    request_data = {
                    'user[login]': 'test',
                    'user[password]': 'random',
                    csrf_param: csrf_token}

    sign_in = functools.partial(
       session.post,
       response.url,
       data=request_data,
       verify=False)

    for _ in range(10):
      sign_in(headers={'X-Forwarded-For': '1.2.3.4'})
    # after 10 authentication failures, this client is rate limited
    self.assertEqual(sign_in(headers={'X-Forwarded-For': '1.2.3.4'}).status_code, 429)
    # but other clients are not
    self.assertNotEqual(sign_in(headers={'X-Forwarded-For': '5.6.7.8'}).status_code, 429)
