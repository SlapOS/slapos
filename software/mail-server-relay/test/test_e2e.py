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
import imaplib
import smtplib
import time

from slapos.testing.testcase import (
  makeModuleSetUpAndTestCaseClass,
  installSoftwareUrlList,
)

software_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

software_urls = [
  os.path.join(software_folder, 'mail-server-relay', 'software.cfg'),
  os.path.join(software_folder, 'mail-server', 'software.cfg'),
]

_, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "software.cfg"))
)

def setUpModule():
  # Supply every version of the software.
  installSoftwareUrlList(
    SlapOSInstanceTestCase,
    software_urls,
    debug=bool(int(os.environ.get('SLAPOS_TEST_DEBUG', 0))),
  )


class E2E(SlapOSInstanceTestCase):
  instance_max_retry = 4
  domain_list = [
    "mail1.domain.lan",
    "mail2.domain.lan",
    "mail3.domain.lan",
  ]
  @classmethod
  def getInstanceSoftwareType(cls):
    return 'cluster'

  @classmethod
  def getInstanceParameterDict(cls, ext=False):
    if ext:
      external = json.loads(cls.requestExternalServerInstance().getConnectionParameterDict()['_'])
      rhost = external['imap-smtp-ipv6']
      rport = int(external['smtp-port'])
      ruser = "testmail@example.com"  # we're using the test account's credentials to log in
      rpass = "password123"
    else:
      rhost, rport, ruser, rpass = "example.com", 2525, "user", "pass"
    return {
      "_": json.dumps(
        {
          "default-relay-config": {
            "relay-host": rhost,
            "relay-port": rport,
            "relay-user": ruser,
            "relay-password": rpass,
          },
          "outbound-domain-whitelist": [
            "mail1.domain.lan",
            "mail2.domain.lan"
          ],
          "topology": {
              "relay-foo": {
                  "state": "started"
              },
              "relay-bar": {
                  "state": "started",
              }
          }
        }
      )
    }

  @classmethod
  def requestDefaultInstance(cls, state: str = "started"):
    cls.ext_mail_server = cls.requestExternalServerInstance()
    cls.waitForInstance()
    cls._instance_parameter_dict = cls.getInstanceParameterDict(ext=True)
    default_instance = super(E2E, cls).requestDefaultInstance(state)
    cls.mail_server_instances = [
      cls.requestMailServerForDomain(domain) for domain in cls.domain_list
    ]
    cls.waitForInstance()
    return default_instance

  @classmethod
  def requestMailServerForDomain(cls, domain):
    param_dict = {
      "mail-domains": [domain],
      "relay-sr-url": cls.getSoftwareURL(),
      "test-account": True,
    }
    return cls.slap.request(
      software_release=software_urls[1],
      partition_reference=domain,
      partition_parameter_kw={'_': json.dumps(param_dict)},
      software_type='default',
    )
    
  @classmethod
  def requestExternalServerInstance(cls):
    param_dict = {
      "mail-domains": [
        "example.com"
      ],
      "relay-host": "::1",
      "relay-port": 1234,
      "test-account": True,
    }
    return cls.slap.request(
      software_release=software_urls[1],
      partition_reference="external-mail-server",
      partition_parameter_kw={'_': json.dumps(param_dict)},
      software_type='default',
    )
    
  def test_servers(self):
    for server in self.mail_server_instances:
      params = json.loads(server.getConnectionParameterDict()['_'])
      self.assertIn('imap-port', params, "Vibe check")

  def _send_email_via_smtp(self, smtp_server_instance, sender, recipient, subject, body):
    """Helper method to send email via SMTP"""
    smtp_params = json.loads(smtp_server_instance.getConnectionParameterDict()['_'])
    msg = f"Subject: {subject}\n\n{body}"
    
    with smtplib.SMTP(smtp_params['imap-smtp-ipv6'], smtp_params['smtp-port'], timeout=10) as smtp:
      smtp.login(sender, "password123")
      smtp.sendmail(
        from_addr=sender,
        to_addrs=[recipient],
        msg=msg
      )

  def _verify_email_received(self, imap_server_instance, recipient, expected_content):
    """Helper method to verify email was received via IMAP"""
    imap_params = json.loads(imap_server_instance.getConnectionParameterDict()['_'])
    
    time.sleep(10)  # Wait for email delivery
    with imaplib.IMAP4(imap_params['imap-smtp-ipv6'], imap_params['imap-port'], timeout=10) as imap:
      imap.login(recipient, "password123")
      imap.select("INBOX")
      result, data = imap.search(None, 'ALL')
      self.assertEqual(result, 'OK', "Failed to search emails")
      email_ids = data[0].split()
      self.assertGreater(len(email_ids), 0, "No emails found in inbox")
      
      # Check if the last email is the one we sent
      latest_email_id = email_ids[-1]
      result, data = imap.fetch(latest_email_id, '(RFC822)')
      self.assertEqual(result, 'OK', "Failed to fetch email")
      email_body = data[0][1].decode('utf-8')
      self.assertIn(expected_content, email_body, "Email content does not match")

  def test_send_email(self):
    # each mail server has testmail@{{domain}}:password123::
    # try sending a mail from mail1 to mail2 using smtp
    mail1, mail2 = self.mail_server_instances[:2]
    sender = "testmail@mail1.domain.lan"
    recipient = "testmail@mail2.domain.lan"
    
    self._send_email_via_smtp(mail1, sender, recipient, "Test Email", "This is a test email.")
    self._verify_email_received(mail2, recipient, "This is a test email.")
      
  def test_send_email_to_external(self):
    # try sending a mail from external mail server to mail1 using smtp
    mail1, ext = self.mail_server_instances[0], self.ext_mail_server
    sender = "testmail@mail1.domain.lan"
    recipient = "testmail@example.com"
    
    self._send_email_via_smtp(mail1, sender, recipient, "Test Email", "This is a test email to external server.")
    self._verify_email_received(ext, recipient, "This is a test email to external server.")

  def test_send_email_from_external_via_relay(self):
    # try sending a mail from external to mail1 via the relay
    mail1 = self.mail_server_instances[0]
    sender = "testmail@example.com"
    recipient = "testmail@mail1.domain.lan"
    
    # Get relay connection info from cluster's DNS entries
    cluster_params = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    dns_entries = cluster_params.get('dns-entries', '')
    
    # Parse DNS entries to find the MX record for mail1.domain.lan
    # Format should be: "mail1.domain.lan MX 10 [relay_host]"
    relay_host = None
    relay_port = 10025  # Default SMTP port
    
    for line in dns_entries.strip().split('\n'):
      if 'mail1.domain.lan MX' in line:
        parts = line.strip().split()
        if len(parts) >= 4:
          relay_host = parts[3]
          if relay_host.startswith('[') and relay_host.endswith(']'):
            relay_host = relay_host[1:-1]
          break
    
    self.assertIsNotNone(relay_host, f"Could not find relay host in DNS entries: {dns_entries}")
    
    msg = "Subject: Test Email from External\n\nThis is a test email from external via relay."
    with smtplib.SMTP(relay_host, relay_port, timeout=10) as smtp:
      # No authentication needed for incoming mail to relay
      smtp.sendmail(
        from_addr=sender,
        to_addrs=[recipient],
        msg=msg
      )
    
    # Verify email was received at mail1
    self._verify_email_received(mail1, recipient, "This is a test email from external via relay.")
