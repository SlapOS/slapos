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
import shutil
import subprocess
import tempfile

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
      self.assertIn(
        "this domain has already been claimed", error,
        f"Expected duplicate error for {domain}, got {error}"
      )


class CustomInboundCertificateTestCase(SlapOSInstanceTestCase):
  __partition_reference__ = 'custom-inbound-certificate'

  relay_name = "relay-custom-cert"
  relay_fqdn = "custom-inbound.relay.lan"

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'cluster'

  @classmethod
  def makeParameterDict(cls, custom_inbound_certificate=None):
    relay_config = {
      "fqdn": cls.relay_fqdn,
    }
    if custom_inbound_certificate is not None:
      relay_config["custom-inbound-certificate"] = custom_inbound_certificate
    return {
      "_": json.dumps({
        "topology": {
          cls.relay_name: relay_config,
        },
      })
    }

  @classmethod
  def getInstanceParameterDict(cls):
    return cls.makeParameterDict()

  def requestCluster(self, custom_inbound_certificate=None):
    return self.slap.request(
      software_release=self.getSoftwareURL(),
      partition_reference=self.computer_partition.getId(),
      partition_parameter_kw=self.makeParameterDict(custom_inbound_certificate),
      software_type='cluster',
      state='started',
    )

  def requestClusterAndWait(self, custom_inbound_certificate=None):
    self.requestCluster(custom_inbound_certificate)
    self.waitForInstance()
    self.waitForInstance()

  def runNodeInstanceExpectingPromiseFailure(self):
    last_stdout = ""
    for _ in range(3):
      result = subprocess.run(
        [
          self.slap._slapos_bin,
          "node",
          "instance",
          "--cfg",
          self.slap._slapos_config,
          "-v",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
      )
      last_stdout = result.stdout
      if result.returncode:
        self.assertIn("inbound_certificate_status.py", result.stdout)
        return
    self.fail("Expected inbound certificate status promise failure:\n%s" % last_stdout)

  @classmethod
  def partitionPath(cls, cp, *paths):
    return os.path.join(cls.slap.instance_directory, cp.getId(), *paths)

  def getRelayPartition(self):
    expected_fqdn_line = 'FQDN = "%s"' % self.relay_fqdn
    relay_list = []
    for cp in self.slap.computer.getComputerPartitionList():
      manager_path = self.partitionPath(cp, 'bin', 'inbound-certificate-manager')
      if os.path.exists(manager_path):
        with open(manager_path) as f:
          if expected_fqdn_line in f.read():
            relay_list.append((os.path.getmtime(manager_path), cp))
    if relay_list:
      return max(relay_list, key=lambda x: x[0])[1]
    raise AssertionError("Could not find relay partition for %s" % self.relay_fqdn)

  def getRelayCertificatePathDict(self, relay):
    return {
      "default-cert": self.partitionPath(relay, 'etc', 'postfix', 'ssl', 'postfix.crt'),
      "default-key": self.partitionPath(relay, 'etc', 'postfix', 'ssl', 'postfix.key'),
      "active-cert": self.partitionPath(relay, 'etc', 'postfix', 'ssl_inbound', 'postfix.crt'),
      "active-key": self.partitionPath(relay, 'etc', 'postfix', 'ssl_inbound', 'postfix.key'),
      "status": self.partitionPath(relay, 'etc', 'postfix', 'ssl_inbound', 'status'),
      "status-command": self.partitionPath(relay, 'bin', 'check-inbound-certificate-status'),
    }

  @staticmethod
  def readFile(path):
    with open(path, "rb") as f:
      return f.read()

  @classmethod
  def generateCertificate(cls, fqdn):
    openssl = shutil.which("openssl") or "/usr/bin/openssl"
    with tempfile.TemporaryDirectory() as tempdir:
      cert = os.path.join(tempdir, "cert.pem")
      key = os.path.join(tempdir, "key.pem")
      subprocess.check_call(
        [
          openssl,
          "req",
          "-x509",
          "-newkey",
          "rsa:2048",
          "-nodes",
          "-days",
          "30",
          "-sha256",
          "-subj",
          "/CN=%s" % fqdn,
          "-addext",
          "subjectAltName=DNS:%s" % fqdn,
          "-keyout",
          key,
          "-out",
          cert,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
      )
      with open(cert) as cert_file, open(key) as key_file:
        return {
          "cert": cert_file.read(),
          "key": key_file.read(),
        }

  def assertActiveCertificateIsGenerated(self, path_dict):
    self.assertEqual(
      self.readFile(path_dict["default-cert"]),
      self.readFile(path_dict["active-cert"]),
    )
    self.assertEqual(
      self.readFile(path_dict["default-key"]),
      self.readFile(path_dict["active-key"]),
    )

  def assertActiveCertificateIsCustom(self, path_dict, certificate):
    self.assertEqual(
      certificate["cert"].encode().strip(),
      self.readFile(path_dict["active-cert"]).strip(),
    )
    self.assertEqual(
      certificate["key"].encode().strip(),
      self.readFile(path_dict["active-key"]).strip(),
    )

  def test_custom_inbound_certificate_lifecycle(self):
    relay = self.getRelayPartition()
    path_dict = self.getRelayCertificatePathDict(relay)

    self.assertActiveCertificateIsGenerated(path_dict)
    self.assertIn(
      b"OK: using generated self-signed inbound certificate",
      self.readFile(path_dict["status"]),
    )

    valid_certificate = self.generateCertificate(self.relay_fqdn)
    self.requestClusterAndWait(valid_certificate)
    relay = self.getRelayPartition()
    path_dict = self.getRelayCertificatePathDict(relay)

    self.assertActiveCertificateIsCustom(path_dict, valid_certificate)
    self.assertIn(
      b"OK: using custom inbound certificate",
      self.readFile(path_dict["status"]),
    )

    invalid_certificate = self.generateCertificate("wrong." + self.relay_fqdn)
    self.requestCluster(invalid_certificate)
    self.runNodeInstanceExpectingPromiseFailure()

    relay = self.getRelayPartition()
    path_dict = self.getRelayCertificatePathDict(relay)
    self.assertActiveCertificateIsGenerated(path_dict)
    status = self.readFile(path_dict["status"])
    self.assertIn(b"ERROR: custom inbound certificate invalid", status)
    self.assertIn(b"using generated self-signed inbound certificate", status)

    promise = subprocess.run(
      [path_dict["status-command"]],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      universal_newlines=True,
    )
    self.assertNotEqual(0, promise.returncode)
    self.assertIn("ERROR: custom inbound certificate invalid", promise.stdout)


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
