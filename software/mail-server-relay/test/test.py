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
  def makeParameterDict(cls, inbound_ca=None):
    relay_config = {
      "fqdn": cls.relay_fqdn,
    }
    if inbound_ca is not None:
      relay_config['config'] = {'inbound-ca-certificate': inbound_ca}
    return {
      "_": json.dumps({
        "topology": {
          cls.relay_name: relay_config,
        },
      })
    }

  @classmethod
  def requestDefaultInstance(cls, state='started', inbound_ca=None):
    cls.cluster = cluster = cls.slap.request(
      software_release=cls.getSoftwareURL(),
      partition_reference=cls.relay_name,
      partition_parameter_kw=cls.makeParameterDict(inbound_ca),
      software_type='cluster',
      state=state,
    )
    return cluster

  @classmethod
  def partitionPath(cls, cp, *paths):
    return os.path.join(cls.slap.instance_directory, cp.getId(), *paths)

  @classmethod
  def slapos(cls, *args):
    return subprocess.call((
      cls.slap._slapos_bin, *args,  '--cfg', cls.slap._slapos_config))

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

  def getRelayCertPaths(self, relay):
    prefix = self.partitionPath(relay, 'etc', 'postfix')
    return (
      os.path.join(prefix, 'ssl', 'postfix.bundle.pem'),
      os.path.join(prefix, 'inbound', 'ssl', 'postfix-inbound.bundle.pem'),
    )

  @staticmethod
  def readFile(path, mode='rb'):
    with open(path, mode) as f:
      return f.read()

  @staticmethod
  def pemToDer(pem):
    PEM_HEADER = "-----BEGIN CERTIFICATE-----"
    certificate_pem = pem[pem.find(PEM_HEADER):]
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

  def assertServedInboundCertificate(self, pempath, cluster=None):
    expected_certificate_der = self.pemToDer(self.readFile(pempath, 'r'))
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

  def assertCertFileContentEqual(self, *paths):
    self.assertEqual(*(self.readFile(p).strip() for p in paths))

  @classmethod
  def generateCACertificate(cls, fqdn, ca, ca_key):
    openssl = shutil.which('openssl') or '/usr/bin/openssl'
    subprocess.check_call(
      [
        openssl,
        'req', '-x509',
        '-newkey', 'rsa:2048', '-noenc',
        '-days', '30',
        '-sha256',
        '-extensions', 'v3_ca', 
        '-subj', '/CN=Root CA for %s' % fqdn,
        '-addext', 'keyUsage=critical,digitalSignature,keyCertSign',
        '-keyout', ca_key, '-out', ca,
      ],
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
    )

  @classmethod
  def generateLeafCertificate(cls, fqdn, ca, ca_key, leaf_bundle):
    openssl = shutil.which('openssl') or '/usr/bin/openssl'
    with tempfile.TemporaryDirectory() as tempdir:
      csr = os.path.join(tempdir, 'csr')
      x = subprocess.call(
        [
          openssl,
          'req',
          '-newkey', 'rsa:2048', '-noenc',
          '-sha256',
          '-subj', '/CN=%s' % fqdn,
          '-addext', 'subjectAltName=DNS:%s' % fqdn,
          '-keyout', leaf_bundle, '-out', csr,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
      )
      leaf = os.path.join(tempdir, 'leaf')
      subprocess.check_call(
        [
          openssl,
          'x509', '-req',
          '-days', '30',
          '-sha256',
          '-copy_extensions', 'copyall',
          '-CA', ca,
          '-CAkey', ca_key,
          '-in', csr,
          '-out', leaf,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
      )
      with open(leaf) as f:
        leaf = f.read()
      with open(leaf_bundle, 'a') as f:
        f.write(leaf)

  def pushCertificate(self, url, leaf, pinnedpubkey):
    curl = shutil.which('curl') or '/usr/bin/curl'
    return subprocess.call(
      [
        curl,
        '-T', leaf,
        '-E', leaf,
        '-k', '--pinnedpubkey', pinnedpubkey,
        url,
      ],
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
    )

  def test_custom_inbound_certificate_lifecycle(self):
    with tempfile.TemporaryDirectory() as tempdir:
      ca = os.path.join(tempdir, 'ca.pem')
      ca_key = os.path.join(tempdir, 'ca_key.pem')
      leaf_bundle = os.path.join(tempdir, 'leaf.bundle.pem')
      badname_bundle = os.path.join(tempdir, 'badname.bundle.pem')
      badca = os.path.join(tempdir, 'badca.pem')
      badca_key = os.path.join(tempdir, 'badca_key.pem')
      bad_bundle = os.path.join(tempdir, 'bad.bundle.pem')

      relay = self.getRelayPartition()
      conn = json.loads(relay.getConnectionParameterDict()['_'])
      url = conn['keystore-url']
      pinnedpubkey = conn['pinnedpubkey']

      self.generateCACertificate(self.relay_fqdn, ca, ca_key)
      self.generateLeafCertificate(self.relay_fqdn, ca, ca_key, leaf_bundle)
      self.generateLeafCertificate('bad.domain', ca, ca_key, badname_bundle)
      self.generateCACertificate('bad.ca', badca, badca_key)
      self.generateLeafCertificate(self.relay_fqdn, badca, badca_key, bad_bundle)

      # Check initial state
      default_bundle, inbound_bundle = self.getRelayCertPaths(relay)
      self.assertCertFileContentEqual(default_bundle, inbound_bundle)
      self.assertServedInboundCertificate(default_bundle)

      # Try pushing certificate not signed by default CAs
      retcode = self.pushCertificate(url, leaf_bundle, pinnedpubkey)
      self.assertIn(retcode, (55, 56)) # haproxy resets connection due to bad CA
      self.assertCertFileContentEqual(default_bundle, inbound_bundle)

      # Customize CA
      ca_pem = self.readFile(ca, 'r')
      self.requestDefaultInstance(inbound_ca=ca_pem)
      for _ in range(2):
       self.waitForInstance()

      # Try pushing certificate not signed by custom CA
      retcode = self.pushCertificate(url, bad_bundle, pinnedpubkey)
      self.assertIn(retcode, (55, 56)) # haproxy resets connection due to bad CA
      self.assertCertFileContentEqual(default_bundle, inbound_bundle)

      # Try pushing certificate signed by custom CA but with wrong name
      retcode = self.pushCertificate(url, badname_bundle, pinnedpubkey)
      self.assertEqual(retcode, 92) # haproxy resets connection due to bad name
      self.assertCertFileContentEqual(default_bundle, inbound_bundle)

      # Push valid certificate
      retcode = self.pushCertificate(url, leaf_bundle, pinnedpubkey)
      self.assertEqual(retcode, 0) # ok
      self.assertCertFileContentEqual(leaf_bundle, inbound_bundle)
      self.assertServedInboundCertificate(leaf_bundle)
      self.assertEqual(
        self.slapos('node', 'promise'),
        0,
      )


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
