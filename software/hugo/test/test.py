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


class HugoTestCase(SlapOSInstanceTestCase):

  def checkUrlAndGetResponse(self, url):
    response = requests.get(url)
    self.assertEqual(requests.codes['OK'], response.status_code)
    return response


class TestHugo(HugoTestCase):
  def test_default_deploy(self):
    url = self.requestDefaultInstance().getConnectionParameterDict()['nginx-server-cdn-url']
    response = self.checkUrlAndGetResponse(url)
    result = response.text
    self.assertTrue("<strong>Now you can access your published website powered by Hugo</strong>" in result)

  def test_published_parameter(self):
    data_url = self.requestDefaultInstance().getConnectionParameterDict()['data']
    go_environment = self.requestDefaultInstance().getConnectionParameterDict()['go_environment']
    self.assertTrue("/srv/hugo" in data_url)
    self.assertTrue("/go.work/env.sh" in go_environment)