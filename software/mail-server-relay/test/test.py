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
            "proxy-map": {
              "example-proxy": {
                "host": "example.com",
                "port": 2525,
                "user": "user",
                "password": "pass",
                "domains": ["mail1.domain.lan", "mail2.domain.lan"]
              }
            }
          },
          "relay-domain": "foobaz.lan",
          "topology": {
            "relay-foo": {
              "fqdn": "relay.foo.lan"
            },
            "relay-bar": {
              "fqdn": "relay.bar.lan",
              "config": {
                "proxy-map": {
                  "bar-proxy": {
                    "host": "bar.example.com",
                    "port": 2525,
                    "user": "user",
                    "password": "pass",
                    "domains": ["mail1.domain.lan", "mail2.domain.lan"]
                  }
                }
              }
            }
          }
        }
      )
    }

  @classmethod
  def requestDefaultInstance(cls, state: str = "started"):
    default_instance = super(PostfixTestCase, cls).requestDefaultInstance(state)
    for domain in [
      "mail1.domain.lan",
      "mail2.domain.lan",
      "mail3.domain.lan",
    ]:
      cls.requestSlaveInstanceForDomain(domain, state=state)
      cls.requestSlaveInstanceForDomain(domain, suffix="-test", state=state)
    return default_instance

  @classmethod
  def createParametersForDomain(cls, domain):
    return {
      "name": domain,
      "mail-server-host": "2001:db8::%d" % (hash(domain) % 100),
      "mail-server-port": 10025
    }

  @classmethod
  def requestSlaveInstanceForDomain(cls, domain, suffix="", state: str = "started"):
    software_url = cls.getSoftwareURL()
    param_dict = cls.createParametersForDomain(domain)
    return cls.slap.request(
      software_release=software_url,
      partition_reference="SLAVE-%s%s" % (domain, suffix),
      partition_parameter_kw={'_': json.dumps(param_dict)},
      shared=True,
      software_type='cluster',
      state=state,
    )

  def test_returned_backend_domains(self):
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    expected_entries = set([
      "mail1.domain.lan",
      "mail2.domain.lan",
      "mail3.domain.lan",
    ])
    actual_entries = set(
      filter(None, (line.strip() for line in parameter_dict["backend-domains"].splitlines()))
    )
    self.assertEqual(actual_entries, expected_entries)

  def test_shared_output_schema_and_dns(self):
    for domain in ["mail1.domain.lan", "mail2.domain.lan"]:
      shared_instance = self.requestSlaveInstanceForDomain(domain)
      connection_dict = json.loads(shared_instance.getConnectionParameterDict().get("_", "{}"))
      self.assertEqual(connection_dict.get("outbound-host", "<missing>"), "foobaz.lan")
      self.assertEqual(connection_dict.get("outbound-smtp-port", "<missing>"), "10587")
      self.assertEqual(
        connection_dict.get("dns-entries", "<missing>"),
        # entries are sorted lexicographically as a side-effect of buildout's
        # object to string serialization.
        f"{domain}. MX 10 relay.bar.lan.\n"
        f"{domain}. MX 10 relay.foo.lan."
      )
      shared_dup_instance = self.requestSlaveInstanceForDomain(domain, suffix="-test")
      connection_dict = json.loads(shared_dup_instance.getConnectionParameterDict().get("_", "{}"))
      error = connection_dict.get("error", "<missing>")
      self.assertIn("address_already_used", error, f"Expected duplicate error for {domain}, got {error}")


class ProxyMapDuplicateDomainTestCase(SlapOSInstanceTestCase):
  """Test case for proxy-map with duplicate domains across proxies.
  
  This verifies that when the same domain appears in multiple proxies,
  the validation error is published in the cluster's connection parameters.
  """
  __partition_reference__ = 'P'
  
  @classmethod
  def getInstanceSoftwareType(cls):
    return 'cluster'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      "_": json.dumps(
        {
          "default-relay-config": {
            "proxy-map": {
              "smtp2go-proxy": {
                "host": "smtp2go.example.com",
                "port": 2525,
                "user": "user1",
                "password": "pass1",
                "domains": ["duplicate.domain.lan", "unique1.domain.lan"]
              },
              "sendgrid-proxy": {
                "host": "sendgrid.example.com",
                "port": 587,
                "user": "user2",
                "password": "pass2",
                "domains": ["duplicate.domain.lan", "unique2.domain.lan"]
              }
            }
          },
          "outbound-domain-whitelist": [
            "duplicate.domain.lan",
            "unique1.domain.lan",
            "unique2.domain.lan"
          ],
          "relay-domain": "relay.test.lan",
          "topology": {
              "relay-test": {
                  "state": "started"
              }
          }
        }
      )
    }

  def test_duplicate_domain_error_published(self):
    """Verify that duplicate domain errors are published in connection parameters."""
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    errors = parameter_dict.get("errors", [])
    
    # Should have at least one error about duplicate domains
    self.assertIsInstance(errors, list, "Errors should be a list")
    self.assertTrue(len(errors) > 0, "Should have at least one error for duplicate domains")
    
    # Check that the error mentions the duplicate domain
    error_text = " ".join(errors)
    self.assertIn("duplicate.domain.lan", error_text.lower(), 
                  "Error should mention the duplicate domain")
    self.assertIn("appears in multiple proxies", error_text.lower(),
                  "Error should indicate domain appears in multiple proxies")

