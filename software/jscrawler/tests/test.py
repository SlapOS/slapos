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
from urllib.parse import urlparse

import requests
import time

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.testing.utils import ManagedHTTPServer


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestJSCrawler(SlapOSInstanceTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    class TestServer(ManagedHTTPServer):
      def do_GET(self):
        # type: () -> None
        self.send_response(200)
        self.send_header("Content-Type", "application/html")
        self.end_headers()
        self.wfile.write(f'<title>Hello {self._name}</title>'.encode())

    return {
      'urls': '\n'.join([
          cls.getManagedResource('website1', TestServer).url,
          cls.getManagedResource('website2', TestServer).url,
      ])
    }

  def setUp(self):
    self.url = self.computer_partition.getConnectionParameterDict(
    )['url']

  def test_http_get(self):
    resp = requests.get(self.url, verify=False)
    self.assertTrue(
      resp.status_code in [requests.codes.ok, requests.codes.found])

  def test_crawled_sitemap(self):
    url_list = self.computer_partition.getInstanceParameterDict()['urls'].split('\n')
    time.sleep(70) # wait until cron runs
    website1 = urlparse(url_list[0]).netloc
    sitemap1 = requests.get(self.url + '/%s.xml' % website1, verify=False)
    self.assertEqual(sitemap1.status_code, requests.codes.ok)

    website2 = urlparse(url_list[1]).netloc
    sitemap2 = requests.get(self.url + '/%s.xml' % website2, verify=False)
    self.assertEqual(sitemap2.status_code, requests.codes.ok)
