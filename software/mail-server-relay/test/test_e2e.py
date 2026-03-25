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
import ssl
import time

from slapos.testing.testcase import (
  makeModuleSetUpAndTestCaseClass,
  installSoftwareUrlList,
)


def try_until(condition, *, timeout=60, interval=2, err_msg=None):
  deadline = time.time() + timeout
  last_error = None
  while True:
    if condition():
      return
    if time.time() >= deadline:
      raise AssertionError(err_msg)
    time.sleep(interval)

def wrap_exception(f):
  def wrapper():
    try:
      return f()
    except Exception as e:
      return False
  return wrapper

def raise_unless(value):
  if not value:
    raise AssertionError(value)

def serialize(d):
  return {'_': json.dumps(d)}

def unwrap(d):
  return json.loads(d['_'])


SR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SR_PARDIR = os.path.abspath(os.path.join(SR_DIR, os.pardir))
RELAY_SR = os.path.join(SR_DIR, 'software.cfg')
EMAIL_SR = os.path.join(SR_PARDIR, 'mail-server', 'software.cfg')

_, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(RELAY_SR)

DEBUG = bool(int(os.environ.get('SLAPOS_TEST_DEBUG', 0)))
def setUpModule():
  installSoftwareUrlList(
    SlapOSInstanceTestCase,
    [RELAY_SR, EMAIL_SR],
    debug=DEBUG,
  )


class E2E(SlapOSInstanceTestCase):
  instance_max_retry = 4
  mail_server_domains = ["mail%d.domain.lan" % i for i in range(1, 4)]
  password_relay_domain = "mail.relay.password.domain.lan"
  external_domain = 'example.com'
  testmail_password = 'password123'
  relay_inbound_port = 10025
  relay_outbound_port = 10587

  @classmethod
  def getConnectionDict(cls, instance):
    return unwrap(instance.getConnectionParameterDict())

  @classmethod
  def requestRelayCluster(cls, external_server, state="started"):
    def make_proxy_config(*values):
      keys = ('proxy-' + o for o in ('host', 'port', 'user', 'password'))
      return dict(zip(keys, values))
    external = cls.getConnectionDict(external_server)
    proxy_config = make_proxy_config(
      external['imap-smtp-ipv6'],
      int(external['smtp-port']),
      'testmail@' + cls.external_domain,
      'password123',
    )
    parameters = serialize({
     "default-proxy-config": proxy_config,
      "outbound-domain-whitelist": cls.mail_server_domains + [
        cls.password_relay_domain,
      ],
      "topology": {
          "relay-foo": {
            "state": "started"
          }
      }
    })
    return cls.slap.request(
      software_release=RELAY_SR,
      partition_reference='mail-relay-cluster',
      partition_parameter_kw=parameters,
      software_type='cluster',
      state=state,
    )

  @classmethod
  def requestMailServer(cls, domain, state, extra=None):
    param_dict = {
      "mail-domains": [domain],
      "relay-sr-url": RELAY_SR,
      "test-account": True,
    }
    if extra:
      param_dict.update(extra)
    mailserver = cls.slap.request(
      software_release=EMAIL_SR,
      partition_reference=domain,
      partition_parameter_kw=serialize(param_dict),
      software_type='default',
      state=state,
    )
    mailserver.testmail = 'testmail@' + domain
    return mailserver

  @classmethod
  def requestExternalMailServer(cls, state):
    return cls.requestMailServer(cls.external_domain, state, {'no-relay': True})

  @classmethod
  def requestRelayShared(cls, domain, address, extra_parameters, state):
    ipv6, port = address
    parameters = {
      "name": domain,
      "mail-server-host": ipv6,
      "mail-server-port": port,
    }
    parameters.update(extra_parameters)
    requester = lambda: cls.slap.request(
      software_release=RELAY_SR,
      partition_reference=domain,
      partition_parameter_kw=serialize(parameters),
      shared=True,
      software_type='cluster',
      state=state,
    )
    relay_shared = requester()
    relay_shared.rerequest = requester
    relay_shared.domain = domain
    relay_shared.examplemail = 'example@' + domain
    relay_shared.backend_address = address
    return relay_shared

  @classmethod
  def requestDefaultInstance(cls, state="started"):
    external = cls.requestExternalMailServer(state)
    if not external.getConnectionParameterDict():
      # requestDefaultInstance is called twice by the framework:
      # the first time to make the initial requests, and the second
      # time after the framework ran waitForInstance, to obtain the
      # connection dict (a first request always returns an empty dict).
      # We need to run waitForInstance directly here to pass the connection
      # dict of the external mail server to the cluster parameters. But we
      # don't need to do it the second time, when the external mail server
      # already has an up to date non-empty connection dict.
      cls.waitForInstance()
      external = cls.requestExternalMailServer(state)
    cls.external_mail_server = external
    cls.relay_cluster = relay_cluster = cls.requestRelayCluster(external, state)
    if DEBUG and not relay_cluster.getConnectionParameterDict():
      # debug: run waitForInstance right after requesting the cluster
      # to fail fast in case of error in the cluster instance buildout
      # without having requested and needing to process more mail servers.
      # This is purely a convenience for developping.
      cls.waitForInstance()
    cls.mail_servers = [
      cls.requestMailServer(domain, state) for domain in cls.mail_server_domains
    ]
    # Ensure every instance & sub-instance is allocated into a partition
    # so that the remaining partition's IPv6 can be used.
    cls.waitForInstance()
    available_ipv6 = (
      cls.getPartitionIPv6(cp.getId())
      for cp in cls.slap.computer.getComputerPartitionList()
      if cp.getState() != 'started'
    )
    cls.free_ipv6 = next(available_ipv6)
    cls.password_relay_shared = cls.requestRelayShared(
      cls.password_relay_domain,
      (next(available_ipv6), 10025),
      {"authentication": "password"},
      state,
    )
    # We need to return an instance here because the framework expects it.
    return relay_cluster

  @classmethod
  def setUpClass(cls):
    super(E2E, cls).setUpClass()
    # Fetch instance information for use in tests
    relay_host = cls.getRelayHost()
    cls.relay_inbound_addr = (relay_host, cls.relay_inbound_port)
    cls.relay_outbound_addr = (relay_host, cls.relay_outbound_port)
    cls.password_relay_shared.login = cls.getRelaySharedLogin()
    cls.relay_server = next((
      cp for cp in cls.slap.computer.getComputerPartitionList()
      if cp.getState() == 'started' and cp.getType() == 'relay'
    ))
    cls.free_port = 10011

  @classmethod
  def getRelaySharedLogin(cls):
    params = cls.getConnectionDict(cls.password_relay_shared)
    return params['outbound-user'], params['outbound-password']

  @classmethod
  def getRelayHost(cls):
    # TODO: the cluster should really publish this cleanly
    cluster_params = cls.getConnectionDict(cls.relay_cluster)
    dns_entries = cluster_params.get('dns-entries', '')
    for line in dns_entries.strip().split('\n'):
      if 'MX' in line:
        parts = line.strip().split()
        if len(parts) >= 4:
          relay_host = parts[3]
          if relay_host.startswith('[') and relay_host.endswith(']'):
            relay_host = relay_host[1:-1]
          return relay_host
    raise Exception("Could not find relay host")

  @classmethod
  def smtpAddrOf(self, server):
    smtp_params = self.getConnectionDict(server)
    return smtp_params['imap-smtp-ipv6'], int(smtp_params['smtp-port'])

  @classmethod
  def imapAddrOf(self, server):
    smtp_params = self.getConnectionDict(server)
    return smtp_params['imap-smtp-ipv6'], int(smtp_params['imap-port'])

  @classmethod
  def partitionPath(cls, cp, *paths):
    return os.path.join(cls.slap.instance_directory, cp.getId(), *paths)

  def test_servers(self):
    for server in self.mail_servers:
      params = self.getConnectionDict(server)
      self.assertIn('imap-port', params, "Vibe check")

  def send_email(self, mailserver, mail_recipient, body, send_as=None):
    sender = send_as or mailserver.testmail
    with smtplib.SMTP(*self.smtpAddrOf(mailserver), timeout=10) as smtp:
      smtp.starttls()
      smtp.login(mailserver.testmail, self.testmail_password)
      smtp.sendmail(
        from_addr=sender,
        to_addrs=[mail_recipient.testmail],
        msg=f"Subject: Test email from {sender}\n\n{body}",
      )

  def check_inbox(self, mailserver, expected):
    def check_email():
      with imaplib.IMAP4(*self.imapAddrOf(mailserver), timeout=10) as imap:
        imap.login(mailserver.testmail, self.testmail_password)
        imap.select("INBOX")
        result, data = imap.search(None, 'ALL')
        if result != 'OK':
          return False
        email_ids = data[0].split()
        if len(email_ids) == 0:
          return False
        # Check if the last email contains the expected content
        result, data = imap.fetch(email_ids[-1], '(RFC822)')
        if result != 'OK':
          return False
        email_body = data[0][1].decode('utf-8')
        return expected in data[0][1].decode('utf-8')
    try_until(
      wrap_exception(check_email),
      timeout=60,
      interval=2,
      err_msg=f"Email with '{expected}' not received by {mailserver.testmail}"
    )

  def check_mail_e2e(self, mailserver, mail_recipient, body, send_as=None):
    self.send_email(mailserver, mail_recipient, body, send_as)
    self.check_inbox(mail_recipient, body)

  def test_send_email(self):
    # each mail server has testmail@{{domain}}:password123::
    from_mail, to_mail = self.mail_servers[:2]
    self.check_mail_e2e(from_mail, to_mail, "This is a test email.")
      
  def test_send_email_to_external(self):
    self.check_mail_e2e(
      self.mail_servers[0], self.external_mail_server,
      "This is a test email to external server."
    )

  def test_send_email_from_external_via_relay(self):
    # try sending a mail from external to mail1 via the relay
    mail1 = self.mail_servers[0]
    sender = "testmail@example.com"
    msg_body = "This is a test email from external via relay."
    with smtplib.SMTP(*self.relay_inbound_addr, timeout=10) as smtp:
      # No authentication needed for incoming mail to relay
      smtp.sendmail(
        from_addr=sender,
        to_addrs=[mail1.testmail],
        msg="Subject: Test Email from External\n\n" + msg_body
      )
    # Verify email was received at mail1
    self.check_inbox(mail1, msg_body)

  def check_not_in_inbox(self, mailserver, unexpected_content, wait_time=30):
    time.sleep(wait_time)
    imap_params = self.getConnectionDict(mailserver)
    host, port = imap_params['imap-smtp-ipv6'], imap_params['imap-port']
    with imaplib.IMAP4(*self.imapAddrOf(mailserver), timeout=10) as imap:
      imap.login(mailserver.testmail, self.testmail_password)
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
            f"Email with unexpected content '{unexpected_content}'"
            f"was found in {mailserver.testmail}'s inbox",
          )

  def test_sender_restriction_legitimate(self):
    """mail1 (whitelisted) sends as @mail1.domain.lan through the relay to
    mail2 — this is a legitimate sender domain and must be accepted."""
    mail1, mail2 = self.mail_servers[:2]
    self.check_mail_e2e(
      mail1, mail2,
      "This is a legitimate sender domain test."
    )

  def test_sender_restriction_impersonation_blocked(self):
    """mail1 backend tries to send with From: @mail2.domain.lan (a domain
    belonging to another backend). The relay must reject this."""
    spoofed_sender = "testmail@mail2.domain.lan"
    msg = "This impersonated email should be blocked by the relay."
    # Authenticate on mail1 as the real user but set MAIL FROM to mail2's domain
    self.send_email(
      self.mail_servers[0], self.external_mail_server, msg,
      send_as=spoofed_sender,
    )
    # The backend accepted the mail (user is authenticated locally), but
    # the relay should reject it when the backend tries to forward it.
    # Verify the email never arrives at the external server.
    self.check_not_in_inbox(self.external_mail_server, msg, wait_time=30)

  def test_relay_password_shared_output_stable(self):
    params = self.getConnectionDict(self.password_relay_shared)
    password = params.get('outbound-password')
    user = params.get('outbound-user')
    self.assertTrue(password, "Password must be published")
    self.assertTrue(user, "User must be published")
    self.assertEqual(
      params.get('outbound-submission-port'), str(self.relay_outbound_port))
    self.assertTrue(
      params.get('tls-fingerprints'), "TLS fingerprints must be published")
    self.assertIsInstance(
      params['tls-fingerprints'], list, "TLS fingerprints should be a list")
    # Reprocess the cluster
    self.relay_cluster.bang("Reprocess to check password stability")
    self.waitForInstance()
    # Assert password remain stable
    params = self.getConnectionDict(self.password_relay_shared.rerequest())
    self.assertEqual(password, params.get('outbound-password'))
    self.assertEqual(user, params.get('outbound-user'))

  def test_relay_password_auth_legitimate(self):
    """Authenticate as <domain> on the relay's submission port
    and send as @<domain> — must be accepted."""
    mail1 = self.mail_servers[0]
    body = "Password auth legitimate test."
    with smtplib.SMTP(*self.relay_outbound_addr, timeout=10) as smtp:
      smtp.starttls()
      smtp.login(*self.password_relay_shared.login)
      smtp.sendmail(
        from_addr=self.password_relay_shared.examplemail,
        to_addrs=[mail1.testmail],
        msg="Subject: Password Auth Legit\n\n" + body,
      )
    self.check_inbox(mail1, body)

  def test_relay_password_auth_impersonation_blocked(self):
    """Authenticate as <domain> on the submission port but try
    to send as @<other-domain> — relay must reject."""
    spoofed_sender = self.mail_servers[0].testmail
    msg = "Subject: Password Auth Impersonation\n\nThis should be rejected."
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(*self.relay_outbound_addr, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(*self.password_relay_shared.login)
        smtp.sendmail(
          from_addr=spoofed_sender,
          to_addrs=[self.external_mail_server.testmail],
          msg=msg,
        )

  def test_relay_password_auth_rejected_without_tls(self):
    """Attempting to authenticate on the submission port without STARTTLS
    must be rejected — credentials must never be sent in cleartext."""
    with self.assertRaises(smtplib.SMTPNotSupportedError):
      with smtplib.SMTP(*self.relay_outbound_addr, timeout=10) as smtp:
        # Attempt login without starttls — server must refuse
        smtp.login(*self.password_relay_shared.login)

  def test_server_auth_as_relay_with_client_tls(self):
    body = "Authenticate to relay using TLS client certiticates"
    mailserver = self.mail_servers[0]
    cert_bundle = self.partitionPath(
      self.relay_server,
      'etc', 'postfix', 'ssl', 'postfix.bundle.pem'
    )
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # do not verify the backend's certificate
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    ssl_context.load_cert_chain(cert_bundle)
    host, port = self.smtpAddrOf(mailserver)
    source = (self.free_ipv6, self.free_port)
    with smtplib.SMTP(host, port, timeout=10, source_address=source) as smtp:
      smtp.starttls(context=ssl_context)
      smtp.sendmail(
        from_addr=self.password_relay_shared.examplemail,
        to_addrs=[mailserver.testmail],
        msg="Subject: auth as relay\n\n" + body,
      )
    self.check_inbox(mailserver, body)

  def test_server_non_authenticated_rejected(self):
    msg = "Subject: Unauthenticated Connection\n\nThis should be rejected."
    mailserver = self.mail_servers[0]
    host, port = self.smtpAddrOf(mailserver)
    source = (self.free_ipv6, self.free_port)
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(host, port, timeout=10, source_address=source) as smtp:
        smtp.starttls()
        smtp.sendmail(
          from_addr=self.password_relay_shared.examplemail,
          to_addrs=[mailserver.testmail],
          msg=msg,
        )

