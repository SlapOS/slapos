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
from __future__ import unicode_literals

import json
import os
import requests
import httplib

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestCaucase(SlapOSInstanceTestCase):
  def deserializeConnectionParameter(self):
    return json.loads(
      self.computer_partition.getConnectionParameter('_'))

  def test(self):
    connection_parameter_dict = self.deserializeConnectionParameter()
    self.assertEqual(
      connection_parameter_dict,
      {'url': 'http://[%s]:8009' % (self._ipv6_address,)}
    )
    result = requests.get(connection_parameter_dict['url'])

    self.assertEqual(result.status_code, httplib.OK)
    self.assertEqual(
      result.json(),
      {
        '_links': {
          'self': {
            'href': 'http://[%s]:8009' % (self._ipv6_address,)
          },
          'getCAUHAL': {
            'href': 'http://[%s]:8009//cau' % (self._ipv6_address,),
            'title': 'cau'
          },
          'getCASHAL': {
            'href': 'http://[%s]:8009//cas' % (self._ipv6_address,),
            'title': 'cas'
          }
        }
      }
    )
