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
import re

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))



ipv6_regexp =   '''(?:(?x)(?:(?:[0-9a-f]{1,4}:){1,1}(?::[0-9a-f]{1,4}){1,6})|
(?:(?:[0-9a-f]{1,4}:){1,2}(?::[0-9a-f]{1,4}){1,5})|
(?:(?:[0-9a-f]{1,4}:){1,3}(?::[0-9a-f]{1,4}){1,4})|
(?:(?:[0-9a-f]{1,4}:){1,4}(?::[0-9a-f]{1,4}){1,3})|
(?:(?:[0-9a-f]{1,4}:){1,5}(?::[0-9a-f]{1,4}){1,2})|
(?:(?:[0-9a-f]{1,4}:){1,6}(?::[0-9a-f]{1,4}){1,1})|
(?:(?:(?:[0-9a-f]{1,4}:){1,7}|:):)|
(?::(?::[0-9a-f]{1,4}){1,7})|
(?:(?:(?:(?:[0-9a-f]{1,4}:){6})(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}))|
(?:(?:(?:[0-9a-f]{1,4}:){5}[0-9a-f]{1,4}:(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}))|
(?:(?:[0-9a-f]{1,4}:){5}:[0-9a-f]{1,4}:(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})|
(?:(?:[0-9a-f]{1,4}:){1,1}(?::[0-9a-f]{1,4}){1,4}:(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})|
(?:(?:[0-9a-f]{1,4}:){1,2}(?::[0-9a-f]{1,4}){1,3}:(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})|
(?:(?:[0-9a-f]{1,4}:){1,3}(?::[0-9a-f]{1,4}){1,2}:(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})|
(?:(?:[0-9a-f]{1,4}:){1,4}(?::[0-9a-f]{1,4}){1,1}:(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})|
(?:(?:(?:[0-9a-f]{1,4}:){1,5}|:):(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})|
(?::(?::[0-9a-f]{1,4}){1,5}:(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}))
'''

class TestPeerTube(SlapOSInstanceTestCase):
  def setUp(self):
    self.connection_parameters = self.computer_partition.getConnectionParameterDict()

  """Test that the service url.${kind} responds Hello ${name}
  """
  def test_get(self):
    url = self.connection_parameters['frontend-url']
    response = requests.get(url, verify=False)
    self.assertEqual(requests.codes['OK'], response.status_code)
    self.assertIn('PeerTube', response.text)
    response =requests.get(url + "/feeds/videos.xml?sort=-trending", verify=False)
    self.assertEqual(requests.codes['OK'], response.status_code)
    self.assertIn('rss', response.text)
    self.assertFalse(bool(re.search(ipv6_regexp, response.text)))

