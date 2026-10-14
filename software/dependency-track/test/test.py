##############################################################################
#
# Copyright (c) 2024 Nexedi SA and Contributors. All Rights Reserved.
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
import urllib.parse

import lxml.html
import requests
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "software.cfg"))
)


class TestDependencyTrack(InstanceTestCase):
  __partition_reference__ = "DT"  # postgresql use a socket in data dir

  def setUp(self):
    self.url = self.computer_partition.getConnectionParameterDict()["url"]

  def test_http_single_page_app(self):
    resp = requests.get(self.url, verify=False)
    home_page_text = resp.text
    self.assertTrue(resp.ok)
    resp = requests.get(urllib.parse.urljoin(self.url, "/projects"), verify=False)
    self.assertTrue(resp.ok)
    self.assertEqual(resp.text, home_page_text)

  def test_http_api(self):
    resp = requests.get(urllib.parse.urljoin(self.url, "/api/version"), verify=False)
    resp.raise_for_status()
    self.assertEqual(resp.json()["application"], "Dependency-Track")

  def test_http_caching_and_compression(self):
    resp = requests.get(self.url, verify=False)
    tree = lxml.html.fromstring(resp.text)
    for path in (
      tree.xpath("//link[@rel='stylesheet']/@href")[0],
      tree.xpath("//script[@src]/@src")[0],
    ):
      with self.subTest(path=path):
        resp = requests.get(
          urllib.parse.urljoin(self.url, path),
          headers={"Accept-Encoding": "gzip"},
          verify=False,
        )
        resp.raise_for_status()
        self.assertEqual(resp.headers["Cache-Control"], "public, max-age=31536000, immutable")
        self.assertEqual(resp.headers["Content-Encoding"], "gzip")
