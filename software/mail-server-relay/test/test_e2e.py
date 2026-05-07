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

import base64
import os
import json
import imaplib
import smtplib
import socket
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
    value = condition()
    if value:
      return value
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


class E2ETestCase(SlapOSInstanceTestCase):
  __partition_reference__ = 'e2e'
  instance_max_retry = 4

  relay_inbound_port = 10025
  relay_outbound_port = 10587
  smtp_timeout = 60

  testmail_password = 'password123'

  @classmethod
  def getConnectionDict(cls, instance):
    return unwrap(instance.getConnectionParameterDict())

  @classmethod
  def requestRelayCluster(cls, topology, proxy_map, extra, state):
    parameters = serialize({
      "default-relay-config": {
        "proxy-map": proxy_map,
      } | extra,
      "topology": topology
    })
    requester = lambda: cls.slap.request(
      software_release=RELAY_SR,
      partition_reference='mail-relay-cluster',
      partition_parameter_kw=parameters,
      software_type='cluster',
      state=state,
    )
    relay_cluster = requester()
    relay_cluster.rerequest = requester
    return relay_cluster

  @classmethod
  def requestMailServer(cls, domain, state, extra=None):
    param_dict = {
      "mail-domains": [domain],
      "inbound-relay": {"relay-sr-url": RELAY_SR},
      "test-account": True,
    }
    if extra:
      for k, v in extra.items():
        w = param_dict.setdefault(k, v)
        if w is not v and all(isinstance(x, dict) for x in (w, v)):
          w.update(v)
    requester = lambda: cls.slap.request(
      software_release=EMAIL_SR,
      partition_reference=domain,
      partition_parameter_kw=serialize(param_dict),
      software_type='default',
      state=state,
    )
    mailserver = requester()
    mailserver.rerequest = requester
    mailserver.domain = domain
    mailserver.testmail = 'testmail@' + domain
    return mailserver

  @classmethod
  def requestExternalMailServer(cls, domain, state):
    return cls.requestMailServer(
      domain,
      state,
      {'inbound-relay': {'enable': False}},
  )

  @classmethod
  def requestRelayShared(cls, domain, address, extra_parameters, state):
    ipv6, port = address
    parameters = {
      "name": domain,
      "mail-server-host": ipv6,
      "mail-server-port": port,
    }
    parameters.update(extra_parameters)
    def requester():
      relay_shared = cls.slap.request(
        software_release=RELAY_SR,
        partition_reference=domain,
        partition_parameter_kw=serialize(parameters),
        shared=True,
        software_type='cluster',
        state=state,
      )
      relay_shared.domain = domain
      relay_shared.examplemail = 'example@' + domain
      relay_shared.backend_address = address
      return relay_shared
    relay_shared = requester()
    relay_shared.rerequest = requester
    return relay_shared

  @classmethod
  def getRelayHost(cls, relay_cluster):
    cluster_params = cls.getConnectionDict(relay_cluster)
    return cluster_params.get('relay-hosts')[0]

  @classmethod
  def getRelaySharedLogin(cls, password_shared):
    params = cls.getConnectionDict(password_shared)
    return params['outbound-user'], params['outbound-password']

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

  @classmethod
  def client_ssl_context(cls, client_cert_bundle):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # do not verify the relay's certificate
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    ssl_context.load_cert_chain(client_cert_bundle)
    return ssl_context

  @staticmethod
  def _get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

  def send_email(self, mailserver, mail_recipient, body, send_as=None):
    sender = send_as or mailserver.testmail
    with smtplib.SMTP(*mailserver.smtp_addr, timeout=self.smtp_timeout) as smtp:
      smtp.starttls()
      smtp.login(mailserver.testmail, self.testmail_password)
      smtp.sendmail(
        from_addr=sender,
        to_addrs=[mail_recipient.testmail],
        msg=f"Subject: Test email from {sender}\n\n{body}",
      )

  def check_inbox(self, mailserver, expected):
    def check_email():
      with imaplib.IMAP4(*mailserver.imap_addr, timeout=self.smtp_timeout) as imap:
        imap.starttls(ssl_context=self._get_ssl_context())
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
        if expected not in email_body:
          return False
        return email_body
    return try_until(
      wrap_exception(check_email),
      timeout=60,
      interval=2,
      err_msg=f"Email with '{expected}' not received by {mailserver.testmail}"
    )

  def check_mail_e2e(self, mailserver, mail_recipient, body, send_as=None):
    self.send_email(mailserver, mail_recipient, body, send_as)
    self.check_inbox(mail_recipient, body)

  def check_not_in_inbox(self, mailserver, unexpected_content, wait_time=30):
    time.sleep(wait_time)
    imap_params = self.getConnectionDict(mailserver)
    host, port = imap_params['imap-smtp-ipv6'], imap_params['imap-port']
    with imaplib.IMAP4(*mailserver.imap_addr, timeout=self.smtp_timeout) as imap:
      imap.starttls(ssl_context=self._get_ssl_context())
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


class Relay(E2ETestCase):
  # Use IPv6 of extra free partitions
  partition_count = 15

  mail_server_domains = ["mail%d.domain.lan" % i for i in range(1, 3)]
  password_relay_domain = "mail.relay.password.domain.lan"
  ip_auth_relay_domain = "mail.relay.ip-auth.domain.lan"
  fingerprint_relay_domain = "mail.relay.fingerprint.domain.lan"
  unknown_domain = "unknown.domain.lan"
  well_known_domain = "rapid.space"
  owned_mx_domain = "mx-ipv6.messwithdns.test.rapid.space"

  @classmethod
  def requestDefaultInstance(cls, state="started"):
    cls.relay_cluster = relay_cluster = cls.requestRelayCluster(
      # Request two relays nodes to cover corner cases
      # such as multiple relay TLS fingerprints
      topology = {
        "relay-one": {"fqdn": "ipv6.messwithdns.test.rapid.space"},
        "relay-two": {"fqdn": "ipv4.messwithdns.test.rapid.space"},
      },
      proxy_map = {},
      extra = {
        "greylisting-enabled": True,
        "greylisting-delay": 5,
        "greylisting-whitelist-recipients": [cls.mail_server_domains[1]],
      },
      state = state
    )
    # Request two backend mail servers with relays
    cls.mail_servers = [
      cls.requestMailServer(domain, state) for domain in cls.mail_server_domains
    ]
    # Request one unrelated mail server unknown to the relay cluster
    # (mostly to reuse its TLS certificates directly)
    cls.unknown_mailserver = cls.requestExternalMailServer(
      cls.unknown_domain,
      state,
    )
    # Ensure every sub-instance is allocated into a partition
    # so that the remaining partition's IPv6 can be used.
    if not relay_cluster.getConnectionParameterDict():
      # requestDefaultInstance is called twice by the framework:
      # the first time to make the initial requests, and the second
      # time after the framework ran waitForInstance, to obtain the
      # connection dict (a first request always returns an empty dict).
      # We don't need to reprocess the partitions the second time, when
      # the relay cluster already returns a non-empty connection dict.
      cls.waitForInstance()
    available_ipv6 = (
      cls.getPartitionIPv6(cp.getId())
      for cp in cls.slap.computer.getComputerPartitionList()
      if cp.getState() != 'started'
    )
    cls.free_ipv6 = next(available_ipv6)
    # password auth relay
    extra = {"authentication": "password"}
    cls.password_relay_shared, cls.well_known_shared, cls.owned_mx_shared = (
      cls.requestRelayShared(d, (next(available_ipv6), 10025), extra, state)
      for d in (
        cls.password_relay_domain, cls.well_known_domain, cls.owned_mx_domain
      )
    )
    cls.password_relays = (
      cls.password_relay_shared, cls.well_known_shared, cls.owned_mx_shared
    )
    # (obsolete) ip auth relay
    cls.ip_auth_relay_shared = cls.requestRelayShared(
      cls.ip_auth_relay_domain,
      (next(available_ipv6), 10025),
      {
        "authentication": "none",
      },
      state,
    )
    # (recommended) TLS fingerprint auth relay
    fingerprint_path = cls.partitionPath(
      cls.unknown_mailserver,
      'etc', 'postfix', 'ssl', 'postfix-backend.digest'
    )
    with open(fingerprint_path) as f:
      fingerprint = f.read().split('=', 1)[1].strip()
    cls.fingerprint_relay_shared = cls.requestRelayShared(
      cls.fingerprint_relay_domain,
      (next(available_ipv6), 10025),
      {
        "authentication": "fingerprint",
        "fingerprints": [fingerprint],
      },
      state,
    )
    cls.fingerprint_relay_shared.cert_bundle = cls.partitionPath(
      cls.unknown_mailserver,
      'etc', 'postfix', 'ssl', 'postfix-backend.bundle.pem'
    )
    # We need to return an instance here because the framework expects it.
    return relay_cluster

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    # Process the partitions again to propagate all shared relay
    # requests to the cluster's relay nodes sub-instances.
    cls.waitForInstance()
    # Fetch instance information for use in tests
    relay_host = cls.getRelayHost(cls.relay_cluster)
    cls.relay_inbound = {
      'host': relay_host,
      'port': cls.relay_inbound_port,
      'timeout': cls.smtp_timeout,
    }
    cls.relay_outbound = {
      'host': relay_host,
      'port': cls.relay_outbound_port,
      'timeout': cls.smtp_timeout,
    }
    for relay in cls.password_relays:
      relay.login = cls.getRelaySharedLogin(relay)
    cls.relay_servers = [
      cp for cp in cls.slap.computer.getComputerPartitionList()
      if cp.getState() == 'started' and cp.getType() == 'relay'
    ]
    for server in cls.mail_servers:
      server.smtp_addr = cls.smtpAddrOf(server)
      server.imap_addr = cls.imapAddrOf(server)
    cls.free_port = 10011

  def test_relay_inbound_fqdn(self):
    with smtplib.SMTP(**self.relay_inbound) as smtp:
      _, resp = smtp.helo()
      self.assertEqual(resp, b'ipv6.messwithdns.test.rapid.space')

  def test_relay_outbound_fqdn(self):
    with smtplib.SMTP(**self.relay_outbound) as smtp:
      _, resp = smtp.helo()
      self.assertEqual(resp, b'ipv6.messwithdns.test.rapid.space')

  def test_relay_unknown_sender_rejected(self):
    mail1 = self.mail_servers[0]
    body = "Send to relay from unknown sender address"
    source = (self.free_ipv6, self.free_port)
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(source_address=source, **self.relay_outbound) as smtp:
        smtp.starttls()
        smtp.sendmail(
          from_addr='unknown@' + self.unknown_domain,
          to_addrs=[mail1.testmail],
          msg="Subject: Unknown sender should be rejected\n\n" + body,
       )

  def test_relay_usurped_well_known_domain_rejected(self):
    mail1 = self.mail_servers[0]
    msg = "Subject: Send to relay from usurped well-known sender address"
    with smtplib.SMTP(**self.relay_outbound) as smtp:
      smtp.starttls()
      smtp.login(*self.well_known_shared.login)
      # login works fine but sending is rejected
      with self.assertRaises(smtplib.SMTPRecipientsRefused):
        smtp.sendmail(
          from_addr=self.well_known_shared.examplemail,
          to_addrs=[mail1.testmail],
          msg=msg,
        )

  def test_relay_owned_mx_domain_accepted(self):
    mail1 = self.mail_servers[0]
    msg = "Subject: Send to relay from domain with cluster MX"
    with smtplib.SMTP(**self.relay_outbound) as smtp:
      smtp.starttls()
      smtp.login(*self.owned_mx_shared.login)
      smtp.sendmail(
        from_addr=self.owned_mx_shared.examplemail,
        to_addrs=[mail1.testmail],
        msg=msg,
      )
    self.check_inbox(mail1, msg)

  def test_relay_password_shared_output_stable(self):
    params = self.getConnectionDict(self.password_relay_shared)
    password = params.get('outbound-password')
    user = params.get('outbound-user')
    self.assertTrue(password, "Password must be published")
    self.assertTrue(user, "User must be published")
    self.assertEqual(
      params.get('outbound-smtp-port'), str(self.relay_outbound_port))
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
    with smtplib.SMTP(**self.relay_outbound) as smtp:
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
    mail1 = self.mail_servers[0]
    spoofed_sender = self.ip_auth_relay_shared.examplemail
    msg = "Subject: Password Auth Impersonation\n\nThis should be rejected."
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(**self.relay_outbound) as smtp:
        smtp.starttls()
        smtp.login(*self.password_relay_shared.login)
        smtp.sendmail(
          from_addr=spoofed_sender,
          to_addrs=[mail1.testmail],
          msg=msg,
        )

  def test_relay_password_auth_login_required(self):
    """Attempting to authenticate on the submission port with the backend IP
    but no password login must be rejected"""
    mail1 = self.mail_servers[0]
    body = "Password auth login required test."
    source = self.password_relay_shared.backend_address
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(source_address=source, **self.relay_outbound) as smtp:
        smtp.starttls()
        smtp.sendmail(
          from_addr=self.password_relay_shared.examplemail,
          to_addrs=[mail1.testmail],
          msg="Subject: Password auth login required\n\n" + body,
        )

  def test_relay_password_auth_rejected_without_tls(self):
    """Attempting to authenticate on the submission port without STARTTLS
    must be rejected — credentials must never be sent in cleartext."""
    with self.assertRaises(smtplib.SMTPNotSupportedError):
      with smtplib.SMTP(**self.relay_outbound) as smtp:
        # Attempt login without starttls — server must refuse
        smtp.login(*self.password_relay_shared.login)

  def test_relay_ip_auth_legitimate(self):
    mail1 = self.mail_servers[0]
    body = "IP auth legitimate test."
    source = self.ip_auth_relay_shared.backend_address
    with smtplib.SMTP(source_address=source, **self.relay_outbound) as smtp:
      smtp.starttls()
      smtp.sendmail(
        from_addr=self.ip_auth_relay_shared.examplemail,
        to_addrs=[mail1.testmail],
        msg="Subject: IP Auth Legit\n\n" + body,
      )
    self.check_inbox(mail1, body)

  def test_relay_ip_auth_impersonation_blocked(self):
    mail1 = self.mail_servers[0]
    body = "IP auth impersonation test."
    source = self.ip_auth_relay_shared.backend_address
    spoofed_sender = self.password_relay_shared.examplemail
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(source_address=source, **self.relay_outbound) as smtp:
        smtp.starttls()
        smtp.sendmail(
          from_addr=spoofed_sender,
          to_addrs=[mail1.testmail],
          msg="Subject: IP Auth Impersonation\n\n" + body,
        )

  def test_relay_ip_auth_unknown_ip_blocked(self):
    mail1 = self.mail_servers[0]
    body = "IP auth impersonation test."
    source = (self.free_ipv6, self.free_port)
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(source_address=source, **self.relay_outbound) as smtp:
        smtp.starttls()
        smtp.sendmail(
          from_addr=self.ip_auth_relay_shared.examplemail,
          to_addrs=[mail1.testmail],
          msg="Subject: IP Auth Impersonation\n\n" + body,
        )

  def test_relay_fingerprint_auth_legitimate(self):
    mail1 = self.mail_servers[0]
    body = "Authenticate to relay with backend client certificate"
    ssl_context = self.client_ssl_context(
      self.fingerprint_relay_shared.cert_bundle
    )
    source = self.fingerprint_relay_shared.backend_address
    with smtplib.SMTP(source_address=source, **self.relay_outbound) as smtp:
      smtp.starttls(context=ssl_context)
      smtp.sendmail(
        from_addr=self.fingerprint_relay_shared.examplemail,
        to_addrs=[mail1.testmail],
        msg="Subject: TLS fingerprint auth to relay\n\n" + body,
      )
    self.check_inbox(mail1, body)

  def test_relay_fingerprint_auth_impersonation_blocked(self):
    mail1 = self.mail_servers[0]
    body = "Impersonate to relay with backend client certificate"
    ssl_context = self.client_ssl_context(
      self.fingerprint_relay_shared.cert_bundle
    )
    source = self.fingerprint_relay_shared.backend_address
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(source_address=source, **self.relay_outbound) as smtp:
        smtp.starttls(context=ssl_context)
        smtp.sendmail(
          from_addr=self.password_relay_shared.examplemail,
          to_addrs=[mail1.testmail],
          msg="Subject: TLS fingerprint impersonate to relay\n\n" + body,
       )

  def test_relay_fingerprint_auth_required(self):
    mail1 = self.mail_servers[0]
    body = "Send to relay without backend client certificate"
    source = self.fingerprint_relay_shared.backend_address
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(source_address=source, **self.relay_outbound) as smtp:
        smtp.starttls()
        smtp.sendmail(
          from_addr=self.password_relay_shared.examplemail,
          to_addrs=[mail1.testmail],
          msg="Subject: Send to relay without client certificate\n\n" + body,
        )

  def test_relay_auth_sender_to_untransportable_recipient_rejected(self):
    """Mail from an authentified backend domain that does not have a proxy
    to an external address must be rejected directly by the relay."""
    msg = "Subject: No Proxy Test\n\nThis should be rejected - untransportable"
    # Connect directly to the relay with authentification
    # The relay should reject because this sender has no proxy configured
    ssl_context = self.client_ssl_context(
      self.fingerprint_relay_shared.cert_bundle
    )
    source = self.fingerprint_relay_shared.backend_address
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(source_address=source, **self.relay_outbound) as smtp:
        smtp.starttls(context=ssl_context)
        smtp.sendmail(
          from_addr=self.fingerprint_relay_shared.examplemail,
          to_addrs=['unknown@' + self.unknown_domain],
          msg=msg,
        )

  def test_server_authenticated_relay_with_client_tls(self):
    mailserver = self.mail_servers[0]
    for i, relay_server in enumerate(self.relay_servers):
      body = "Authenticate to backend with relay %d's client certificates" % i
      cert_bundle = self.partitionPath(
        relay_server, 'etc', 'postfix', 'ssl', 'postfix.bundle.pem'
      )
      ssl_context = self.client_ssl_context(cert_bundle)
      addr = mailserver.smtp_addr
      timeout = self.smtp_timeout
      source = (self.free_ipv6, self.free_port)
      with smtplib.SMTP(*addr, timeout=timeout, source_address=source) as smtp:
        smtp.starttls(context=ssl_context)
        smtp.sendmail(
          from_addr=self.password_relay_shared.examplemail,
          to_addrs=[mailserver.testmail],
          msg="Subject: TLS fingerprint auth as relay\n\n" + body,
        )
      self.check_inbox(mailserver, body)

  def test_server_non_authenticated_relay_rejected(self):
    msg = "Subject: Unauthenticated Connection\n\nThis should be rejected."
    mailserver = self.mail_servers[0]
    addr = mailserver.smtp_addr
    timeout = self.smtp_timeout
    source = (self.free_ipv6, self.free_port)
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(*addr, timeout=timeout, source_address=source) as smtp:
        smtp.starttls()
        smtp.sendmail(
          from_addr=self.password_relay_shared.examplemail,
          to_addrs=[mailserver.testmail],
          msg=msg,
        )

  def test_server_authenticated_sender_impersonation_blocked(self):
    msg = "Subject: Authenticated Connection with spoofed sender\n\nReject it."
    mailserver = self.mail_servers[0]
    addr = mailserver.smtp_addr
    timeout = self.smtp_timeout
    source = (self.free_ipv6, self.free_port)
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(*addr, timeout=timeout, source_address=source) as smtp:
        smtp.starttls()
        smtp.login(mailserver.testmail, self.testmail_password)
        smtp.sendmail(
          from_addr='unknown@' + mailserver.domain,
          to_addrs=[mailserver.testmail],
          msg=msg,
        )

  def test_server_authenticated_sender_unknown_domain_blocked(self):
    msg = "Subject: Authenticated Connection with spoofed sender\n\nReject it."
    mailserver = self.mail_servers[0]
    addr = mailserver.smtp_addr
    timeout = self.smtp_timeout
    source = (self.free_ipv6, self.free_port)
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(*addr, timeout=timeout, source_address=source) as smtp:
        smtp.starttls()
        smtp.login(mailserver.testmail, self.testmail_password)
        smtp.sendmail(
          from_addr='unknown@' + self.unknown_domain,
          to_addrs=[mailserver.testmail],
          msg=msg,
        )

  def test_spf_impersonation_rejected(self):
    mail1 = self.mail_servers[0]
    msg_body = "This inbound impersonation should be rejected by SPF."
    with self.assertRaises(smtplib.SMTPRecipientsRefused):
      with smtplib.SMTP(**self.relay_inbound) as smtp:
        smtp.sendmail(
          from_addr="testmail@spf-always-fail.messwithdns.test.rapid.space",
          to_addrs=[mail1.testmail],
          msg=f"Subject: SPF Impersonation\n\n{msg_body}",
        )
    self.check_not_in_inbox(mail1, msg_body, wait_time=5)

  def test_spf_pass(self):
    mail1 = self.mail_servers[0]
    msg_body = "This inbound email should bypass greylisting on first delivery."
    with smtplib.SMTP(**self.relay_inbound) as smtp:
      smtp.sendmail(
        from_addr="testmail@spf-always-pass.messwithdns.test.rapid.space",
        to_addrs=[mail1.testmail],
        msg=f"Subject: SPF Pass\n\n{msg_body}",
      )
    self.check_inbox(mail1, msg_body)

  def test_greylist_whitelist_recipient(self):
    mail2 = self.mail_servers[1]
    msg_body = "This inbound email should bypass greylisting on first delivery."
    with smtplib.SMTP(**self.relay_inbound) as smtp:
      smtp.sendmail(
        from_addr='unknown@' + self.unknown_domain,
        to_addrs=[mail2.testmail],
        msg=f"Subject: Mock SPF Pass\n\n{msg_body}",
      )
    self.check_inbox(mail2, msg_body)


class E2E(E2ETestCase):
  instance_max_retry = 4

  mail_server_domains = ["mail%d.domain.lan" % i for i in range(1, 4)]
  external_domains = ["external%d.domain.lan" % i for i in range(1, 3)]
  unknown_domain = "unknown.domain.lan"
  testmail_password = 'password123'

  @classmethod
  def requestDefaultInstance(cls, state="started"):
    external_mail_servers = [
      cls.requestExternalMailServer(external_domain, state)
      for external_domain in cls.external_domains
    ]
    if not all(e.getConnectionParameterDict() for e in external_mail_servers):
      # requestDefaultInstance is called twice by the framework:
      # the first time to make the initial requests, and the second
      # time after the framework ran waitForInstance, to obtain the
      # connection dict (a first request always returns an empty dict).
      # We need to run waitForInstance directly here to pass the connection
      # dict of the external mail servers to the cluster parameters. But we
      # don't need to do it the second time, when the external mail servers
      # already have an up to date non-empty connection dict.
      cls.waitForInstance()
      external_mail_servers = [e.rerequest() for e in external_mail_servers]
    cls.external_mail_servers = external_mail_servers
    external = [cls.getConnectionDict(e) for e in external_mail_servers]
    cls.relay_cluster = relay_cluster = cls.requestRelayCluster(
      topology = {
        "relay-one": {"fqdn": "relay.one.lan"},
      },
      proxy_map = {
        "external-proxy-1": {
          "host": external[0]['imap-smtp-ipv6'],
          "port": int(external[0]['smtp-port']),
          "domains": cls.mail_server_domains[:-1]
        },
        "external-proxy-2": {
          "host": external[1]['imap-smtp-ipv6'],
          "port": int(external[1]['smtp-port']),
          "domains": cls.mail_server_domains[-1:]
        },
      },
      extra = {
        "greylisting-enabled": True,
        "greylisting-delay": 5,
      },
      state = state
    )
    cls.mail_servers = [
      cls.requestMailServer(domain, state) for domain in cls.mail_server_domains
    ]
    # We need to return an instance here because the framework expects it.
    return relay_cluster

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    # Fetch instance information for use in tests
    cls.external_mail_server = cls.external_mail_servers[0]
    relay_host = cls.getRelayHost(cls.relay_cluster)
    cls.relay_inbound = {
      'host': relay_host,
      'port': cls.relay_inbound_port,
      'timeout': cls.smtp_timeout,
    }
    for server in cls.mail_servers + cls.external_mail_servers:
      server.smtp_addr = cls.smtpAddrOf(server)
      server.imap_addr = cls.imapAddrOf(server)

  def _managesieve(self, mailserver, script_name, script_content):
    """Upload and activate (or deactivate) a sieve script via ManageSieve,
    the same protocol SnappyMail uses."""
    host = self.getConnectionDict(mailserver)['imap-smtp-ipv6']
    sock = socket.create_connection((host, 4190), timeout=30)

    def recv_response():
      lines = []
      while True:
        line = b''
        while not line.endswith(b'\r\n'):
          c = sock.recv(1)
          if not c:
            raise ConnectionError("ManageSieve: connection closed")
          line += c
        line = line.decode('utf-8').strip()
        lines.append(line)
        if line.startswith(('OK', 'NO', 'BYE')):
          return lines

    def send(cmd):
      sock.sendall((cmd + '\r\n').encode('utf-8'))

    recv_response()  # greeting

    send('STARTTLS')
    resp = recv_response()
    self.assertTrue(resp[-1].startswith('OK'), f"STARTTLS: {resp}")

    sock = self._get_ssl_context().wrap_socket(sock)
    recv_response()  # post-TLS capabilities

    creds = base64.b64encode(
      b'\0' + mailserver.testmail.encode()
      + b'\0' + self.testmail_password.encode()
    ).decode()
    send(f'AUTHENTICATE "PLAIN" "{creds}"')
    resp = recv_response()
    self.assertTrue(resp[-1].startswith('OK'), f"AUTH: {resp}")

    if script_content is not None:
      data = script_content.encode('utf-8')
      send(f'PUTSCRIPT "{script_name}" {{{len(data)}+}}')
      sock.sendall(data + b'\r\n')
      resp = recv_response()
      self.assertTrue(resp[-1].startswith('OK'), f"PUTSCRIPT: {resp}")
      send(f'SETACTIVE "{script_name}"')
    else:
      send('SETACTIVE ""')
    resp = recv_response()
    self.assertTrue(resp[-1].startswith('OK'), f"SETACTIVE: {resp}")

    send('LOGOUT')
    sock.close()

  def test_servers(self):
    for server in self.mail_servers:
      params = self.getConnectionDict(server)
      self.assertIn('imap-port', params, "Vibe check")

  def test_send_email(self):
    # each mail server has testmail@{{domain}}:password123::
    from_mail, to_mail = self.mail_servers[:2]
    self.check_mail_e2e(from_mail, to_mail, "This is a test email.")

  def test_send_email_to_external(self):
    self.check_mail_e2e(
      self.mail_servers[0], self.external_mail_server,
      "This is a test email to external server."
    )

  def test_send_email_via_proxy2(self):
    """Mail from a domain whitelisted in the second proxy entry is routed
    through the second external relay and arrives at the second external
    mail server."""
    self.check_mail_e2e(
      self.mail_servers[-1], self.external_mail_servers[1],
      "This is a test email routed via the second proxy."
    )

  def test_send_email_from_external_via_relay(self):
    # try sending a mail from external to mail1 via the relay
    mail1 = self.mail_servers[0]
    msg_body = "This is a test email from external via relay."
    # first try, greylisted
    with self.assertRaises(smtplib.SMTPRecipientsRefused) as exc:
      with smtplib.SMTP(**self.relay_inbound) as smtp:
        smtp.sendmail(
          from_addr=self.external_mail_server.testmail,
          to_addrs=[mail1.testmail],
          msg=f"Subject: Test Email from External\n\n{msg_body}"
        )

    for _addr, (code, _msg) in exc.exception.recipients.items():
      self.assertEqual(code, 450, f"Expected 450 greylisting, got {code}: {_msg}")

    time.sleep(10)

    with smtplib.SMTP(**self.relay_inbound) as smtp:
      smtp.sendmail(
        from_addr=self.external_mail_server.testmail,
        to_addrs=[mail1.testmail],
        msg=f"Subject: Test Email from External\n\n{msg_body}"
      )
    # Verify email was received at mail1
    self.check_inbox(mail1, msg_body)

  def test_sender_restriction_legitimate(self):
    """mail1 (whitelisted) sends as @mail1.domain.lan through the relay to
    mail2 — this is a legitimate sender domain and must be accepted."""
    mail1, mail2 = self.mail_servers[:2]
    self.check_mail_e2e(
      mail1, mail2,
      "This is a legitimate sender domain test."
    )

  def test_sieve_redirect(self):
    """Upload a sieve redirect script via ManageSieve on mail2,
    send from mail1, and verify the mail arrives at mail3."""
    mail1, mail2, mail3 = self.mail_servers

    sieve_script = (
      'require ["editheader", "variables", "envelope"];\n'
      '\n'
      '# Capture original sender and envelope recipient (forwarder)\n'
      'if header :matches "From" "*" { set "original_from" "${1}"; }\n'
      'if envelope :matches "to" "*" { set "forward_from" "${1}"; }\n'
      '\n'
      '# Add forwarding trace headers\n'
      'addheader "X-Forwarded-For" "${forward_from} %(u)s";\n'
      'addheader "X-Forwarded-To" "%(u)s";\n'
      '\n'
      '# If no Reply-To, set it to the original sender\n'
      'if not header :matches "Reply-To" "*" {\n'
      '  addheader "Reply-To" "${original_from}";\n'
      '}\n'
      '\n'
      '# Remove spam classification header\n'
      'deleteheader "X-Bogosity";\n'
      '\n'
      '# Rewrite From to the forwarding user\n'
      'deleteheader "From";\n'
      'addheader "From" "${forward_from}";\n'
      '\n'
      'redirect "%(u)s";\n'
    ) % {'u': mail3.testmail}
    self._managesieve(mail2, 'redirect', sieve_script)
    self.addCleanup(self._managesieve, mail2, None, None)

    body = "Sieve redirect via ManageSieve test"
    self.send_email(mail1, mail2, body)
    mailmsg = self.check_inbox(mail3, body)
    self.assertIn("Reply-To: " + mail1.testmail, mailmsg)
    self.assertIn("From: " + mail2.testmail, mailmsg)
    self.assertIn("Return-Path: <%s>" % mail2.testmail, mailmsg)
    self.assertIn(
      "X-Forwarded-For: %s %s" % (mail2.testmail, mail3.testmail),
      mailmsg,
    )
    self.assertIn("X-Forwarded-To: " + mail3.testmail, mailmsg)


class CustomOutbound(E2ETestCase):
  instance_max_retry = 4

  custom_domain = 'custom-outbound.domain.lan'

  @classmethod
  def requestDefaultInstance(cls, state="started"):
    relay_cluster = cls.requestRelayCluster(
      topology = {
        "relay-one": {"fqdn": "relay.one.lan"},
      },
      proxy_map = {},
      extra = {},
      state = state
    )
    password_relay_shared = cls.requestRelayShared(
      cls.custom_domain,
      # Use whatever IPv6, this test will not send to it
      (cls.getPartitionIPv6(relay_cluster.getId()), 10025),
      {"authentication": "password"},
      state,
    )
    if not password_relay_shared.getConnectionParameterDict():
      # Process partitions to obtain the connection dict of the password relay
      cls.waitForInstance()
      relay_cluster = relay_cluster.rerequest()
      password_relay_shared = password_relay_shared.rerequest()
    cls.relay_cluster = relay_cluster
    cls.password_relay_shared = password_relay_shared
    relay_host = cls.getRelayHost(relay_cluster)
    relay_user, password = cls.getRelaySharedLogin(password_relay_shared)
    cls.custom_mailserver = custom_mailserver = cls.requestMailServer(
      cls.custom_domain,
      state,
      extra={
        "inbound-relay": {"enable": False},
        "outbound-relay": {
          "host": relay_host,
          "port": cls.relay_outbound_port,
          "user": relay_user,
          "password": password,
        }
      },
    )
    cls.mailserver = mailserver = cls.requestMailServer(
      'mail.domain.lan',
      state,
    )
    return custom_mailserver

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    # Fetch instance information for use in tests
    for server in (cls.custom_mailserver, cls.mailserver):
      server.smtp_addr = cls.smtpAddrOf(server)
      server.imap_addr = cls.imapAddrOf(server)

  def test_send_via_custom_outbound_relay(self):
    self.check_mail_e2e(
      self.custom_mailserver,
      self.mailserver,
      "This is a test email.",
    )

