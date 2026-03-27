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


def wait_for_condition(condition_func, timeout=60, interval=2, error_message="Condition not met within timeout"):
  """
  Retry a condition function until it returns True or timeout is reached.
  
  Args:
    condition_func: A callable that returns True when the condition is met
    timeout: Maximum time to wait in seconds (default: 60)
    interval: Time between retries in seconds (default: 2)
    error_message: Message to include in the exception if timeout is reached
  
  Raises:
    AssertionError: If the condition is not met within the timeout period
  """
  start_time = time.time()
  last_error = None
  
  while time.time() - start_time < timeout:
    try:
      if condition_func():
        return True
    except Exception as e:
      last_error = e
    time.sleep(interval)
  
  elapsed = time.time() - start_time
  error_msg = f"{error_message} (waited {elapsed:.1f}s)"
  if last_error:
    error_msg += f". Last error: {last_error}"
  raise AssertionError(error_msg)

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
  smtp_timeout = 60
  @classmethod
  def getInstanceSoftwareType(cls):
    return 'cluster'

  @classmethod
  def getInstanceParameterDict(cls, ext=False, state: str = "started"):
    if ext:
      external = json.loads(cls.requestExternalServerInstance(state=state).getConnectionParameterDict()['_'])
      rhost = external['imap-smtp-ipv6']
      rport = int(external['smtp-port'])
      ruser = "testmail@external.domain.lan"  # we're using the test account's credentials to log in
      rpass = "password123"
    else:
      rhost, rport, ruser, rpass = "external.domain.lan", 2525, "user", "pass"
    return {
      "_": json.dumps(
        {
          "default-relay-config": {
            "proxy-map": {
              "external-proxy": {
                "host": rhost,
                "port": rport,
                "user": ruser,
                "password": rpass,
                "domains": [
                  "mail1.domain.lan",
                  "mail2.domain.lan",
                  "mail3.domain.lan",
                  "mail4.domain.lan"
                ]
              }
            },
            "greylisting-enable": True,
            "greylisting-delay": 5,
            "greylisting-whitelist-recipients": [
              "testmail@mail2.domain.lan"
            ],
          },
          "outbound-domain-whitelist": [
            "mail1.domain.lan",
            "mail2.domain.lan",
            "mail3.domain.lan",
            "mail4.domain.lan"
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
    cls.ext_mail_server = cls.requestExternalServerInstance(state)
    cls.waitForInstance()
    cls._instance_parameter_dict = cls.getInstanceParameterDict(ext=True, state=state)
    default_instance = super(E2E, cls).requestDefaultInstance(state)
    cls.mail_server_instances = [
      cls.requestMailServerForDomain(domain, state) for domain in cls.domain_list
    ]
    # Request a direct relay slave for mail4 with password authentication.
    # Uses a different domain than mail1-3 (which are IP-based via mail-server)
    # to avoid the cluster's duplicate-domain-name rejection.
    cls.mail4_password_slave = cls.slap.request(
      software_release=software_urls[0],
      partition_reference="password-auth-mail4",
      partition_parameter_kw={'_': json.dumps({
        "name": "mail4.domain.lan",
        "mail-server-host": "::1",
        "mail-server-port": 10025,
        "authentication": "password",
      })},
      shared=True,
      software_type='cluster',
      state=state,
    )
    cls.waitForInstance()
    return default_instance

  @classmethod
  def requestMailServerForDomain(cls, domain, state: str = "started"):
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
      state=state,
    )
    
  @classmethod
  def requestExternalServerInstance(cls, state: str = "started"):
    param_dict = {
      "mail-domains": [
        "external.domain.lan"
      ],
      "no-relay": True,
      "test-account": True,
    }
    return cls.slap.request(
      software_release=software_urls[1],
      partition_reference="external-mail-server",
      partition_parameter_kw={'_': json.dumps(param_dict)},
      software_type='default',
      state=state,
    )
    
  def test_servers(self):
    for server in self.mail_server_instances:
      params = json.loads(server.getConnectionParameterDict()['_'])
      self.assertIn('imap-port', params, "Vibe check")

  def _send_email_via_smtp(self, smtp_server_instance, sender, recipient, subject, body, login_as=None):
    """Helper method to send email via SMTP.
    
    Args:
      login_as: If set, authenticate as this address instead of sender.
                Useful for testing sender domain restrictions (impersonation).
    """
    smtp_params = json.loads(smtp_server_instance.getConnectionParameterDict()['_'])
    msg = f"Subject: {subject}\n\n{body}"
    login_user = login_as or sender
    
    with smtplib.SMTP(smtp_params['imap-smtp-ipv6'], smtp_params['smtp-port'], timeout=self.smtp_timeout) as smtp:
      smtp.login(login_user, "password123")
      smtp.sendmail(
        from_addr=sender,
        to_addrs=[recipient],
        msg=msg
      )

  def _verify_email_received(self, imap_server_instance, recipient, expected_content):
    """Helper method to verify email was received via IMAP"""
    imap_params = json.loads(imap_server_instance.getConnectionParameterDict()['_'])
    
    def check_email():
      """Check if email with expected content is in the inbox"""
      try:
        with imaplib.IMAP4(imap_params['imap-smtp-ipv6'], imap_params['imap-port'], timeout=self.smtp_timeout) as imap:
          imap.login(recipient, "password123")
          imap.select("INBOX")
          result, data = imap.search(None, 'ALL')
          if result != 'OK':
            return False
          
          email_ids = data[0].split()
          if len(email_ids) == 0:
            return False
          
          # Check if the last email contains the expected content
          latest_email_id = email_ids[-1]
          result, data = imap.fetch(latest_email_id, '(RFC822)')
          if result != 'OK':
            return False
          
          email_body = data[0][1].decode('utf-8')
          return expected_content in email_body
      except Exception:
        return False
    
    wait_for_condition(
      check_email,
      timeout=60,
      interval=2,
      error_message=f"Email with content '{expected_content}' not received by {recipient}"
    )

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
    recipient = "testmail@external.domain.lan"
    
    self._send_email_via_smtp(mail1, sender, recipient, "Test Email", "This is a test email to external server.")
    self._verify_email_received(ext, recipient, "This is a test email to external server.")

  def _get_relay_smtp_info(self, mail_domain):
    """Return (relay_host, smtp_port) for the inbound relay MX of ``mail_domain``."""
    cluster_params = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    dns_entries = cluster_params.get('dns-entries', '')
    relay_host = None

    for line in dns_entries.strip().split('\n'):
      if f'{mail_domain} MX' in line:
        parts = line.strip().split()
        if len(parts) >= 4:
          relay_host = parts[3]
          if relay_host.startswith('[') and relay_host.endswith(']'):
            relay_host = relay_host[1:-1]
          break

    return relay_host, 10025

  def test_send_email_from_external_via_relay(self):
    # try sending a mail from external to mail1 via the relay
    mail1 = self.mail_server_instances[0]
    sender = "testmail@external.domain.lan"
    recipient = "testmail@mail1.domain.lan"
    relay_host, relay_port = self._get_relay_smtp_info('mail1.domain.lan')
    self.assertIsNotNone(relay_host, "Could not find relay host")
    
    msg = "Subject: Test Email from External\n\nThis is a test email from external via relay."
    with self.assertRaises(smtplib.SMTPRecipientsRefused) as exc:
      with smtplib.SMTP(relay_host, relay_port, timeout=self.smtp_timeout) as smtp:
        smtp.sendmail(
          from_addr=sender,
          to_addrs=[recipient],
          msg=msg
        )

    for _addr, (code, _msg) in exc.exception.recipients.items():
      self.assertEqual(code, 450, f"Expected 450 greylisting, got {code}: {_msg}")

    time.sleep(10)

    with smtplib.SMTP(relay_host, relay_port, timeout=self.smtp_timeout) as smtp:
      smtp.sendmail(
        from_addr=sender,
        to_addrs=[recipient],
        msg=msg
      )
    
    # Verify email was received at mail1
    self._verify_email_received(mail1, recipient, "This is a test email from external via relay.")

  def test_spf_impersonation_rejected(self):
    """Inbound mail claiming to be from spf-always-fail.messwithdns.test.rapid.space must be rejected by SPF."""
    mail1 = self.mail_server_instances[0]
    relay_host, relay_port = self._get_relay_smtp_info('mail1.domain.lan')
    self.assertIsNotNone(relay_host, "Could not find relay host")

    sender = "testmail@spf-always-fail.messwithdns.test.rapid.space"
    recipient = "testmail@mail1.domain.lan"
    body = "This inbound impersonation should be rejected by SPF."
    msg = f"Subject: SPF Impersonation\n\n{body}"

    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(relay_host, relay_port, timeout=self.smtp_timeout) as smtp:
        smtp.sendmail(
          from_addr=sender,
          to_addrs=[recipient],
          msg=msg,
        )

    self._verify_email_not_received(
      mail1,
      recipient,
      body,
      wait_time=5,
    )

  def test_spf_whitelist_recipient(self):
    """Inbound mail to a whitelisted recipient bypasses greylisting and is
    accepted on the first attempt,."""
    mail2 = self.mail_server_instances[1]
    relay_host, relay_port = self._get_relay_smtp_info('mail2.domain.lan')
    self.assertIsNotNone(relay_host, "Could not find relay host")

    sender = "testmail@external.domain.lan"
    recipient = "testmail@mail2.domain.lan"
    body = "This inbound email should bypass greylisting on first delivery."
    msg = f"Subject: Mock SPF Pass\n\n{body}"

    with smtplib.SMTP(relay_host, relay_port, timeout=self.smtp_timeout) as smtp:
      smtp.sendmail(
        from_addr=sender,
        to_addrs=[recipient],
        msg=msg,
      )

    self._verify_email_received(mail2, recipient, body)
    
  def test_spf_pass(self):
    """Inbound mail from an SPF-passing domain bypasses greylisting and is
    accepted on the first attempt,."""
    mail1 = self.mail_server_instances[0]
    relay_host, relay_port = self._get_relay_smtp_info('mail1.domain.lan')
    self.assertIsNotNone(relay_host, "Could not find relay host")

    sender = "testmail@spf-always-pass.messwithdns.test.rapid.space"
    recipient = "testmail@mail1.domain.lan"
    body = "This inbound email should bypass greylisting on first delivery."
    msg = f"Subject: SPF Pass\n\n{body}"

    with smtplib.SMTP(relay_host, relay_port, timeout=self.smtp_timeout) as smtp:
      smtp.sendmail(
        from_addr=sender,
        to_addrs=[recipient],
        msg=msg,
      )

    self._verify_email_received(mail1, recipient, body)

  def _verify_email_not_received(self, imap_server_instance, recipient, unexpected_content, wait_time=30):
    """Helper method to verify an email was NOT received.

    Waits ``wait_time`` seconds (giving time for potential delivery),
    then asserts no email in the inbox contains ``unexpected_content``.
    """
    # Give the mail system time to potentially (incorrectly) deliver
    time.sleep(wait_time)

    imap_params = json.loads(imap_server_instance.getConnectionParameterDict()['_'])
    with imaplib.IMAP4(imap_params['imap-smtp-ipv6'], imap_params['imap-port'], timeout=self.smtp_timeout) as imap:
      imap.login(recipient, "password123")
      imap.select("INBOX")
      result, data = imap.search(None, 'ALL')
      if result != 'OK' or not data[0]:
        return  # no emails at all — pass

      for email_id in data[0].split():
        result, email_data = imap.fetch(email_id, '(RFC822)')
        if result == 'OK':
          body = email_data[0][1].decode('utf-8')
          self.assertNotIn(
            unexpected_content, body,
            f"Email with unexpected content '{unexpected_content}' was found in {recipient}'s inbox"
          )

  def test_sender_restriction_legitimate(self):
    """mail1 (whitelisted) sends as @mail1.domain.lan through the relay to
    mail2 — this is a legitimate sender domain and must be accepted."""
    mail1, mail2 = self.mail_server_instances[:2]
    sender = "testmail@mail1.domain.lan"
    recipient = "testmail@mail2.domain.lan"

    self._send_email_via_smtp(
      mail1, sender, recipient,
      "Legit Sender Test",
      "This is a legitimate sender domain test."
    )
    self._verify_email_received(mail2, recipient, "This is a legitimate sender domain test.")

  def test_sender_restriction_impersonation_blocked(self):
    """mail1 backend tries to send with From: @mail2.domain.lan (a domain
    belonging to another backend). The relay must reject this."""
    mail1 = self.mail_server_instances[0]
    ext = self.ext_mail_server

    legitimate_user = "testmail@mail1.domain.lan"
    spoofed_sender = "testmail@mail2.domain.lan"
    recipient = "testmail@external.domain.lan"

    # Authenticate on mail1 as the real user but set MAIL FROM to mail2's domain
    self._send_email_via_smtp(
      mail1, spoofed_sender, recipient,
      "Impersonation Test",
      "This impersonated email should be blocked by the relay.",
      login_as=legitimate_user,
    )

    # The backend accepted the mail (user is authenticated locally), but
    # the relay should reject it when the backend tries to forward it.
    # Verify the email never arrives at the external server.
    self._verify_email_not_received(
      ext, recipient,
      "This impersonated email should be blocked by the relay.",
      wait_time=30,
    )

  def _get_relay_submission_info(self):
    """Return (relay_host, submission_port) from the cluster's DNS entries."""
    cluster_params = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    dns_entries = cluster_params.get('dns-entries', '')
    relay_host = None
    for line in dns_entries.strip().split('\n'):
      if 'MX' in line:
        parts = line.strip().split()
        if len(parts) >= 4:
          relay_host = parts[3]
          if relay_host.startswith('[') and relay_host.endswith(']'):
            relay_host = relay_host[1:-1]
          break
    return relay_host, 10587

  def _get_mail4_password_credentials(self):
    """Return (user, password) for the mail4 SASL password-auth slave."""
    slave_params = json.loads(
      self.mail4_password_slave.getConnectionParameterDict().get('_', '{}')
    )
    user = slave_params.get('outbound-user', '')
    password = slave_params.get('outbound-password', '')
    return user, password

  def test_password_auth_slave_output(self):
    """The password-auth slave (mail4) receives outbound-password,
    outbound-user and outbound-submission-port in its connection params."""
    params = json.loads(
      self.mail4_password_slave.getConnectionParameterDict().get('_', '{}')
    )
    self.assertTrue(params.get('outbound-password'), "Password must be published")
    self.assertTrue(params.get('outbound-user'), "User must be published")
    self.assertEqual(params.get('outbound-submission-port'), '10587')

  def test_password_auth_legitimate(self):
    """Authenticate as mail4.domain.lan on the relay's submission port
    and send as @mail4.domain.lan — must be accepted."""
    mail1 = self.mail_server_instances[0]
    relay_host, submission_port = self._get_relay_submission_info()
    self.assertIsNotNone(relay_host, "Could not find relay host")

    user, password = self._get_mail4_password_credentials()
    self.assertTrue(password, "Could not retrieve mail4 SASL password")

    sender = "testmail@mail4.domain.lan"
    recipient = "testmail@mail1.domain.lan"

    msg = "Subject: Password Auth Legit\n\nPassword auth legitimate test."
    with smtplib.SMTP(relay_host, submission_port, timeout=self.smtp_timeout) as smtp:
      smtp.starttls()
      smtp.login(user, password)
      smtp.sendmail(
        from_addr=sender,
        to_addrs=[recipient],
        msg=msg,
      )

    self._verify_email_received(mail1, recipient, "Password auth legitimate test.")

  def test_password_auth_impersonation_blocked(self):
    """Authenticate as mail4.domain.lan on the submission port but try
    to send as @mail1.domain.lan — relay must reject."""
    relay_host, submission_port = self._get_relay_submission_info()
    self.assertIsNotNone(relay_host, "Could not find relay host")

    user, password = self._get_mail4_password_credentials()
    self.assertTrue(password, "Could not retrieve mail4 SASL password")

    spoofed_sender = "testmail@mail1.domain.lan"
    recipient = "testmail@external.domain.lan"

    msg = "Subject: Password Auth Impersonation\n\nThis should be rejected."
    with self.assertRaises((smtplib.SMTPSenderRefused, smtplib.SMTPRecipientsRefused)):
      with smtplib.SMTP(relay_host, submission_port, timeout=self.smtp_timeout) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.sendmail(
          from_addr=spoofed_sender,
          to_addrs=[recipient],
          msg=msg,
        )

  def test_password_auth_rejected_without_tls(self):
    """Attempting to authenticate on the submission port without STARTTLS
    must be rejected — credentials must never be sent in cleartext."""
    relay_host, submission_port = self._get_relay_submission_info()
    self.assertIsNotNone(relay_host, "Could not find relay host")

    user, password = self._get_mail4_password_credentials()
    self.assertTrue(password, "Could not retrieve mail4 SASL password")

    with self.assertRaises(smtplib.SMTPNotSupportedError):
      with smtplib.SMTP(relay_host, submission_port, timeout=self.smtp_timeout) as smtp:
        # Attempt login without starttls — server must refuse
        smtp.login(user, password)
