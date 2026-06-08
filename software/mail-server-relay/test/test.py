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
import ssl
import subprocess
import tempfile
import time

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
  __partition_reference__ = 'C'

  relay_name = "relay-custom-cert"
  relay_fqdn = "custom-inbound.relay.lan"
  relay_inbound_port = 10025
  smtp_timeout = 60

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'cluster'

  @classmethod
  def makeParameterDict(
      cls,
      custom_inbound_certificate=None,
      relay_name=None,
      relay_fqdn=None,
  ):
    relay_config = {
      "fqdn": relay_fqdn or cls.relay_fqdn,
    }
    if custom_inbound_certificate is not None:
      relay_config["custom-inbound-certificate"] = custom_inbound_certificate
    return {
      "_": json.dumps({
        "topology": {
          relay_name or cls.relay_name: relay_config,
        },
      })
    }

  @classmethod
  def getInstanceParameterDict(cls):
    return cls.makeParameterDict()

  def requestCluster(self, custom_inbound_certificate=None):
    return self.slap.request(
      software_release=self.getSoftwareURL(),
      partition_reference=self.__partition_reference__,
      partition_parameter_kw=self.makeParameterDict(custom_inbound_certificate),
      software_type='cluster',
      state='started',
    )

  def requestClusterAndWait(self, custom_inbound_certificate=None):
    self.requestCluster(custom_inbound_certificate)
    for _ in range(2):
      self.waitForInstance()
    return self.requestCluster(custom_inbound_certificate)

  def requestStandaloneClusterAndWait(
      self,
      partition_reference,
      relay_name,
      relay_fqdn,
      custom_inbound_certificate,
  ):
    def requester():
      return self.slap.request(
        software_release=self.getSoftwareURL(),
        partition_reference=partition_reference,
        partition_parameter_kw=self.makeParameterDict(
          custom_inbound_certificate,
          relay_name=relay_name,
          relay_fqdn=relay_fqdn,
        ),
        software_type='cluster',
        state='started',
      )
    requester()
    self.waitForInstance()
    self.waitForInstance()
    return requester()

  @classmethod
  def partitionPath(cls, cp, *paths):
    return os.path.join(cls.slap.instance_directory, cp.getId(), *paths)

  def getRelayPartition(self, relay_fqdn=None):
    expected_fqdn_line = "myhostname = %s" % (relay_fqdn or self.relay_fqdn)
    relay_list = []
    for cp in self.slap.computer.getComputerPartitionList():
      main_cf_path = self.partitionPath(cp, 'etc', 'postfix', 'inbound', 'main.cf')
      if os.path.exists(main_cf_path):
        with open(main_cf_path) as f:
          if expected_fqdn_line in f.read():
            relay_list.append((os.path.getmtime(main_cf_path), cp))
    if relay_list:
      return max(relay_list, key=lambda x: x[0])[1]
    raise AssertionError(
      "Could not find relay partition for %s" % (relay_fqdn or self.relay_fqdn)
    )

  def getRelayCertificatePathDict(self, relay):
    return {
      "default-cert": self.partitionPath(relay, 'etc', 'postfix', 'ssl', 'postfix.crt'),
      "default-key": self.partitionPath(relay, 'etc', 'postfix', 'ssl', 'postfix.key'),
      "inbound-bundle": self.partitionPath(
        relay, 'etc', 'postfix', 'inbound', 'ssl', 'postfix-inbound.bundle.pem'
      ),
    }

  @staticmethod
  def readFile(path):
    with open(path, "rb") as f:
      return f.read()

  @staticmethod
  def pemToDer(certificate_pem):
    return ssl.PEM_cert_to_DER_cert(certificate_pem.strip())

  def getRelayHost(self, cluster=None):
    connection_dict = json.loads(
      (cluster or self.computer_partition).getConnectionParameterDict().get("_", "{}")
    )
    self.assertIn("relay-hosts", connection_dict)
    return connection_dict["relay-hosts"][0]

  def getServedInboundCertificateDer(self, cluster=None):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    with smtplib.SMTP(
      self.getRelayHost(cluster),
      self.relay_inbound_port,
      timeout=self.smtp_timeout,
    ) as smtp:
      smtp.ehlo()
      smtp.starttls(context=ssl_context)
      return smtp.sock.getpeercert(binary_form=True)

  def assertServedInboundCertificate(self, expected_certificate_pem, cluster=None):
    expected_certificate_der = self.pemToDer(expected_certificate_pem)
    deadline = time.time() + self.smtp_timeout
    last_certificate_der = None
    last_error = None
    while True:
      try:
        last_certificate_der = self.getServedInboundCertificateDer(cluster)
        last_error = None
        if expected_certificate_der == last_certificate_der:
          return
      except Exception as e:
        last_error = e

      if time.time() >= deadline:
        if last_error is not None:
          raise AssertionError(
            "Postfix did not serve the expected inbound certificate: %r"
            % last_error
          )
        self.assertEqual(expected_certificate_der, last_certificate_der)
      time.sleep(2)

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
        cert_pem = cert_file.read()
        key_pem = key_file.read()
        return {
          "cert": cert_pem,
          "key": key_pem,
          "bundle": key_pem + cert_pem,
        }

  def assertCustomCertificateWritten(self, path_dict, certificate):
    self.assertEqual(
      certificate["bundle"].encode().strip(),
      self.readFile(path_dict["inbound-bundle"]).strip(),
    )

  def test_custom_inbound_certificate_lifecycle(self):
    relay = self.getRelayPartition()
    path_dict = self.getRelayCertificatePathDict(relay)

    self.assertServedInboundCertificate(
      self.readFile(path_dict["default-cert"]).decode()
    )

    valid_certificate = self.generateCertificate(self.relay_fqdn)
    cluster = self.requestClusterAndWait(valid_certificate["bundle"])
    relay = self.getRelayPartition()
    path_dict = self.getRelayCertificatePathDict(relay)

    self.assertCustomCertificateWritten(path_dict, valid_certificate)
    self.assertServedInboundCertificate(valid_certificate["cert"], cluster)

  def test_custom_inbound_certificate_on_initial_request(self):
    relay_name = "relay-custom-cert-initial"
    relay_fqdn = "custom-inbound-initial.relay.lan"
    valid_certificate = self.generateCertificate(relay_fqdn)
    cluster = self.requestStandaloneClusterAndWait(
      "custom-inbound-certificate-initial",
      relay_name,
      relay_fqdn,
      valid_certificate["bundle"],
    )
    relay = self.getRelayPartition(relay_fqdn)
    path_dict = self.getRelayCertificatePathDict(relay)

    self.assertCustomCertificateWritten(path_dict, valid_certificate)
    self.assertServedInboundCertificate(valid_certificate["cert"], cluster)


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

class DMARCRelayConfigMixin:
  def getRelayPartitionPathList(self):
    partition_prefix = self.computer_partition.getId().rsplit('-', 1)[0] + '-'
    return sorted(
      os.path.join(self.slap.instance_directory, cp.getId())
      for cp in self.slap.computer.getComputerPartitionList()
      if (
        cp.getState() == 'started' and
        cp.getType() == 'relay' and
        cp.getId().startswith(partition_prefix)
      )
    )

  def getRelayInfoList(self):
    relay_info_list = []
    for partition_path in self.getRelayPartitionPathList():
      with open(os.path.join(partition_path, 'etc', 'postfix', 'inbound', 'main.cf')) as fh:
        main_cf = fh.read()
      relay_info_list.append({
        'main_cf': main_cf,
        'opendmarc_conf': os.path.join(
          partition_path, 'etc', 'postfix', 'inbound', 'opendmarc.conf'),
        'opendmarc_service': os.path.join(
          partition_path, 'etc', 'service', 'opendmarc'),
      })
    self.assertTrue(relay_info_list, 'Expected at least one started relay partition')
    return relay_info_list


class DMARCEnabledRelayConfigTestCase(DMARCRelayConfigMixin, PostfixTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    parameter_dict = json.loads(super().getInstanceParameterDict()['_'])
    parameter_dict['default-relay-config']['dmarc'] = {'enable': True}
    return {'_': json.dumps(parameter_dict)}

  def test_opendmarc_is_enabled_in_postfix(self):
    for relay_info in self.getRelayInfoList():
      self.assertIn('smtpd_milters = inet:127.0.0.1:10024', relay_info['main_cf'])
      self.assertIn('milter_default_action = accept', relay_info['main_cf'])
      self.assertIn('milter_protocol = 6', relay_info['main_cf'])

  def test_opendmarc_wrapper_and_config_are_created(self):
    for relay_info in self.getRelayInfoList():
      self.assertTrue(os.path.exists(relay_info['opendmarc_service']))
      with open(relay_info['opendmarc_conf']) as fh:
        config = fh.read()
      self.assertIn('RejectFailures true', config)
      self.assertIn('SPFSelfValidate true', config)


class DMARCDisabledRelayConfigTestCase(DMARCRelayConfigMixin, PostfixTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    parameter_dict = json.loads(super().getInstanceParameterDict()['_'])
    parameter_dict['default-relay-config']['dmarc'] = {'enable': False}
    return {'_': json.dumps(parameter_dict)}

  def test_opendmarc_is_not_enabled_in_postfix(self):
    for relay_info in self.getRelayInfoList():
      self.assertNotIn('smtpd_milters = inet:127.0.0.1:10024', relay_info['main_cf'])
      self.assertNotIn('milter_default_action = accept', relay_info['main_cf'])

  def test_opendmarc_wrapper_is_not_created(self):
    for relay_info in self.getRelayInfoList():
      self.assertFalse(os.path.exists(relay_info['opendmarc_service']))


class DMARCPerRelayOverrideTestCase(DMARCRelayConfigMixin, PostfixTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    parameter_dict = json.loads(super().getInstanceParameterDict()['_'])
    parameter_dict['default-relay-config']['dmarc'] = {'enable': True}
    parameter_dict['topology']['relay-bar']['config']['dmarc'] = {'enable': False}
    return {'_': json.dumps(parameter_dict)}

  def test_dmarc_can_be_disabled_on_one_relay(self):
    relay_info_list = self.getRelayInfoList()
    enabled_relay_count = 0
    disabled_relay_count = 0
    for relay_info in relay_info_list:
      if 'smtpd_milters = inet:127.0.0.1:10024' in relay_info['main_cf']:
        enabled_relay_count += 1
        self.assertTrue(os.path.exists(relay_info['opendmarc_service']))
        self.assertTrue(os.path.exists(relay_info['opendmarc_conf']))
      else:
        disabled_relay_count += 1
        self.assertFalse(os.path.exists(relay_info['opendmarc_service']))
        self.assertFalse(os.path.exists(relay_info['opendmarc_conf']))
    self.assertEqual(enabled_relay_count, 1)
    self.assertEqual(disabled_relay_count, 1)
