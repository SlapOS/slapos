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
import json
import smtplib

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "software.cfg"))
)


class PostfixTestCase(SlapOSInstanceTestCase):
  @classmethod
  def getInstanceSoftwareType(cls):
    return 'cluster'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      "_": json.dumps(
        {
          "default-relay-config": {
            "relay-host": "example.com",
            "relay-port": 2525,
            "relay-user": "user",
            "relay-password": "pass",
          },
          "outbound-domain-whitelist": [
            "mail1.domain.lan",
            "mail2.domain.lan"
          ],
          "relay-domain": "foobaz.lan",
          "topology": {
              "relay-foo": {
                  "state": "started"
              },
              "relay-bar": {
                  "state": "started",
                  "config": {
                    "relay-host": "bar.example.com"
                  }
              }
          }
        }
      )
    }

  @classmethod
  def setUpClass(cls):
    super(PostfixTestCase, cls).setUpClass()
    for domain in [
      "mail1.domain.lan",
      "mail2.domain.lan",
      "mail3.domain.lan",
    ]:
      cls.requestSlaveInstanceForDomain(domain)

  @classmethod
  def requestSlaveInstanceForDomain(cls, domain):
    software_url = cls.getSoftwareURL()
    param_dict = {
      "name": domain,
      "mail-server-host": "2001:db8::%d" % (hash(domain) % 100),
      "mail-server-port": 10025
    }
    return cls.slap.request(
      software_release=software_url,
      partition_reference="SLAVE-%s" % domain.replace('.', '-'),
      partition_parameter_kw={'_': json.dumps(param_dict)},
      shared=True,
      software_type='slave',
    )

  def test_dns_entries(self):
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    expected_entries = set([
      "mail1.domain.lan MX 10 foobaz.lan",
      "mail2.domain.lan MX 10 foobaz.lan"
    ])
    actual_entries = set(
      filter(None, (line.strip() for line in parameter_dict["dns-entries"].splitlines()))
    )
    self.assertEqual(actual_entries, expected_entries)
