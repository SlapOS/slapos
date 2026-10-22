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
import re
import subprocess
import imaplib
import json
import smtplib
import ssl
import time
import urllib.request

from contextlib import contextmanager
from email.mime.text import MIMEText

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.slap.standalone import SlapOSNodeCommandError

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "software.cfg"))
)

class PostfixTestCase(SlapOSInstanceTestCase):
  __partition_reference__ = 'p'

  def _get_ssl_context(self):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

  def check_imap(self, address, password):
    """Test IMAP login with STARTTLS and given address and password"""
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    host = parameter_dict["imap-smtp-ipv6"]
    imap = None
    try:
      imap = imaplib.IMAP4(host, int(parameter_dict["imap-port"]), timeout=10)
      imap.starttls(ssl_context=self._get_ssl_context())
      imap.login(address, password)
      imap.select("INBOX")
      result, data = imap.search(None, "ALL")
      self.assertEqual(result, "OK")
    except Exception as e:
      self.fail(f"IMAP login failed for {address}: {e}")
    finally:
      if imap:
        imap.logout()

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      "_": json.dumps(
        {
          "mail-domains": [
            "example.com",
            "bogofilter-test.example.com",
            "bogofilter-training.example.com",
          ],
          "inbound-relay": {"enable": False},
          "test-account": True,  # Enable test account creation
        }
      )
    }
  
  @classmethod
  def requestDefaultInstance(cls, state: str = "started"):
    default_instance = super(PostfixTestCase, cls).requestDefaultInstance(state)
    cls.waitForInstance()
    for address in [
      "alice@example.com",
      "bob@example.com"
    ]:
      cls.requestSlaveInstanceForAccount(address, state=state)
    cls.requestSlaveInstanceForAccount("alice@example.com", suffix="-test", state=state)
    return default_instance
  
  @classmethod
  def requestSlaveInstanceForAccount(cls, address, suffix="", state: str = "started", additional={}):
    software_url = cls.getSoftwareURL()
    param_dict = {"address": address, **additional}
    return cls.slap.request(
      software_release=software_url,
      partition_reference="SLAVE-%s%s" % (address.replace('@', '-'), suffix),
      partition_parameter_kw={'_': json.dumps(param_dict)},
      shared=True,
      software_type='default',
      state=state,
    )

  def test_postfix(self):
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    host = parameter_dict["imap-smtp-ipv6"]
    try:
      server = smtplib.SMTP(host, int(parameter_dict["smtp-port"]), timeout=10)
      server.quit()
    except Exception as e:
      self.fail(f"SMTP connection failed: {e}")

  def test_dovecot(self):
    self.check_imap("testmail@example.com", "password123")

  def test_imap_plaintext_rejected(self):
    """IMAP login without STARTTLS must be rejected."""
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    host = parameter_dict["imap-smtp-ipv6"]
    imap = None
    try:
      imap = imaplib.IMAP4(host, int(parameter_dict["imap-port"]), timeout=10)
      with self.assertRaises(imaplib.IMAP4.error):
        imap.login("testmail@example.com", "password123")
    finally:
      if imap:
        try:
          imap.logout()
        except Exception:
          pass

  def test_imaps(self):
    """IMAP over implicit TLS (port 10993) must work."""
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    host = parameter_dict["imap-smtp-ipv6"]
    imap = None
    try:
      imap = imaplib.IMAP4_SSL(host, int(parameter_dict["imaps-port"]), timeout=10,
                                ssl_context=self._get_ssl_context())
      imap.login("testmail@example.com", "password123")
      imap.select("INBOX")
      result, data = imap.search(None, "ALL")
      self.assertEqual(result, "OK")
    except Exception as e:
      self.fail(f"IMAPS login failed: {e}")
    finally:
      if imap:
        try:
          imap.logout()
        except Exception:
          pass

  def test_webmail(self):
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    webmail_url = parameter_dict.get("webmail-url", "<missing>")
    self.assertTrue(webmail_url.startswith("http"), "Webmail URL should start with http")

    import urllib.request
    import ssl

    ctx = self._get_ssl_context()

    try:
      with urllib.request.urlopen(webmail_url, timeout=10, context=ctx) as response:
        response_text = response.read().decode('utf-8')
        self.assertIn("SnappyMail", response_text)
    except Exception as e:
      self.fail(f"Webmail access failed: {e}")

  def test_slaves(self):
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    pw_url = parameter_dict.get("password-url", "<missing>")
    self.assertTrue(pw_url.startswith("http"), "Password URL should start with http")

    def reset_password(user, token, new_password):
      import urllib.request
      import urllib.parse
      import ssl

      ctx = ssl.create_default_context()
      ctx.check_hostname = False
      ctx.verify_mode = ssl.CERT_NONE
      
      data = urllib.parse.urlencode({
        'user': user,
        'token': token,
        'password': new_password
      }).encode('utf-8')
      
      try:
        req = urllib.request.Request(pw_url, data=data, method='POST')
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
          response_text = response.read().decode('utf-8')
          self.assertIn("Password updated successfully", response_text)
      except Exception as e:
        self.fail(f"Password change failed for {user}: {e}")
      
    import time
    address = "a1@mail.lan"
    
    # request a1@mail.lan for slave S1, then check it's there
    # then destroy it, and request a1@mail.lan for slave S2 and check that it works    
    slave_instance_1 = self.requestSlaveInstanceForAccount(address, suffix="-S1")
    self.waitForInstance()
    slave_instance_1 = self.requestSlaveInstanceForAccount(address, suffix="-S1")
    connection_dict_1 = json.loads(slave_instance_1.getConnectionParameterDict().get("_", "{}"))
    self.assertEqual(connection_dict_1.get("address", "<missing>"), address)
    # to make sure it exists and gets changed, we'll update the password
    pw_token_1 = connection_dict_1.get("token", "<missing>")
    new_password_1 = "firstpass"
    reset_password(address, pw_token_1, new_password_1)
    time.sleep(2)
    self.check_imap(address, new_password_1)
    self.requestSlaveInstanceForAccount(address, suffix="-S1", state="destroyed")
    slave_instance_2 = self.requestSlaveInstanceForAccount(address, suffix="-S2")
    self.waitForInstance()
    slave_instance_2 = self.requestSlaveInstanceForAccount(address, suffix="-S2")
    connection_dict_2 = json.loads(slave_instance_2.getConnectionParameterDict().get("_", "{}"))
    self.assertEqual(connection_dict_2.get("address", "<missing>"), address)
    pw_token_2 = connection_dict_2.get("token", "<missing>")
    new_password_2 = "secondpass"
    reset_password(address, pw_token_2, new_password_2)
    time.sleep(2)
    self.check_imap(address, new_password_2)

    for address in ["alice@example.com", "bob@example.com"]:
      slave_instance = self.requestSlaveInstanceForAccount(address)
      connection_dict = json.loads(slave_instance.getConnectionParameterDict().get("_", "{}"))
      self.assertEqual(connection_dict.get("address", "<missing>"), address)
      pw_token = connection_dict.get("token", "<missing>")
      
      new_password = f"testpass_{address.split('@')[0]}"
      reset_password(address, pw_token, new_password)
      time.sleep(2)

      self.check_imap(address, new_password)

    for address in ["alice@example.com"]:
      slave_instance = self.requestSlaveInstanceForAccount(address, suffix="-test")
      connection_dict = json.loads(slave_instance.getConnectionParameterDict().get("_", "{}"))
      self.assertEqual(connection_dict.get("address", "<missing>"), address)
      error = connection_dict.get("error", "<missing>")
      self.assertIn("address_already_used", error, f"Expected duplicate error for {address}, got {error}")
      self.requestSlaveInstanceForAccount(address, suffix="-test", state="destroyed")

    reset_tok = "unique-12345"
    self.requestSlaveInstanceForAccount("bob@example.com", additional={"reset-token": reset_tok})
    self.waitForInstance()
    reset_inst = self.requestSlaveInstanceForAccount("bob@example.com")
    reset_connection_dict = json.loads(reset_inst.getConnectionParameterDict().get("_", "{}"))
    self.assertEqual(reset_connection_dict.get("token", "<missing>"), reset_tok)
    new_password = "newpass_bob"
    reset_password("bob@example.com", reset_tok, new_password)
    time.sleep(2)
    self.check_imap("bob@example.com", new_password)

  def test_smtp_works_with_bogofilter(self):
    """SMTP service is still reachable when bogofilter is enabled."""
    parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()["_"]
    )
    host = parameter_dict["imap-smtp-ipv6"]
    try:
      server = smtplib.SMTP(host, int(parameter_dict["smtp-port"]), timeout=10)
      server.quit()
    except Exception as e:
      self.fail(f"SMTP connection failed with bogofilter enabled: {e}")

  def test_bogofilter_adds_bogosity_header(self):
    """Bogofilter adds an X-Bogosity header to incoming (unauthenticated) mail.

    Since smtpd_client_restrictions uses permit_sasl_authenticated first,
    authenticated users bypass bogofilter filtering. Only incoming mail from
    external sources (unauthenticated) is filtered. We simulate this by
    sending without SASL authentication.
    """
    parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()["_"]
    )
    host = parameter_dict["imap-smtp-ipv6"]
    smtp_port = int(parameter_dict["smtp-port"])
    imap_port = int(parameter_dict["imap-port"])
    to_addr = "TestMail@Example.Com"
    from_addr = "unknown@unknown.domain"
    password = "password123"

    msg = MIMEText("Bogofilter integration test")
    msg['Subject'] = "Bogofilter header test"
    msg['From'] = from_addr
    msg['To'] = to_addr

    try:
      server = smtplib.SMTP(host, smtp_port, timeout=10)
      server.starttls(context=self._get_ssl_context())
      # Send without authentication to trigger bogofilter filtering
      server.sendmail(from_addr, [to_addr], msg.as_string())
      server.quit()
    except Exception as e:
      self.fail(f"SMTP send failed: {e}")

    # Allow time for bogofilter processing and LMTP delivery
    time.sleep(10)

    imap = None
    try:
      imap = imaplib.IMAP4(host, imap_port, timeout=10)
      imap.starttls(ssl_context=self._get_ssl_context())
      imap.login(to_addr, password)
      imap.select("INBOX")
      result, msg_ids = imap.search(None, "ALL")
      self.assertEqual(result, "OK")
      ids = msg_ids[0].split()
      self.assertGreater(len(ids), 0, "No messages in INBOX after send")
      result, msg_data = imap.fetch(ids[-1], "(BODY.PEEK[HEADER])")
      self.assertEqual(result, "OK")
      headers = msg_data[0][1].decode("utf-8", errors="replace")
      self.assertIn(
        "X-Bogosity",
        headers,
        "X-Bogosity header missing, bogofilter did not process the message",
      )
      self.assertTrue(os.path.exists(
        os.path.join(
          self.computer_partition_root_path,
          "bogofilter",
          to_addr.lower(),
          "wordlist.db",
        )
      ))
      self.assertFalse(os.path.exists(
        os.path.join(
          self.computer_partition_root_path,
          "bogofilter",
          to_addr,
        )
      ))
    except AssertionError:
      raise
    except Exception as e:
      self.fail(f"IMAP header check failed: {e}")
    finally:
      if imap:
        try:
          imap.logout()
        except Exception:
          pass

  def test_bogofilter_trains_first_message_moved_to_junk(self):
    """Moving mail to Junk creates and trains a new per-user database."""
    parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()["_"]
    )
    host = parameter_dict["imap-smtp-ipv6"]
    imap_port = int(parameter_dict["imap-port"])
    address = "testmail@bogofilter-test.example.com"
    login_address = "TestMail@Bogofilter-Test.Example.Com"
    password = "password123"
    wordlist_path = os.path.join(
      self.computer_partition_root_path,
      "bogofilter",
      address,
      "wordlist.db",
    )
    self.assertFalse(
      os.path.exists(wordlist_path),
      "Test account unexpectedly already has a bogofilter database",
    )

    msg = MIMEText("A unique message to train as spam")
    msg["Subject"] = "Bogofilter spam training test"
    msg["From"] = "sender@example.net"
    msg["To"] = address

    imap = imaplib.IMAP4(host, imap_port, timeout=10)
    try:
      imap.starttls(ssl_context=self._get_ssl_context())
      imap.login(login_address, password)
      result, _ = imap.create("Junk")
      self.assertEqual(result, "OK")
      result, _ = imap.append("INBOX", None, None, msg.as_bytes())
      self.assertEqual(result, "OK")
      result, _ = imap.select("INBOX")
      self.assertEqual(result, "OK")
      result, msg_ids = imap.search(None, "ALL")
      self.assertEqual(result, "OK")
      message_id = msg_ids[0].split()[-1]
      result, _ = imap._simple_command("MOVE", message_id, "Junk")
      self.assertEqual(result, "OK")
    finally:
      try:
        imap.logout()
      except Exception:
        pass

    for _ in range(20):
      if os.path.exists(wordlist_path) and os.path.getsize(wordlist_path) > 0:
        break
      time.sleep(0.5)
    self.assertTrue(
      os.path.exists(wordlist_path),
      "Moving a message to Junk did not create a bogofilter database",
    )
    self.assertGreater(
      os.path.getsize(wordlist_path),
      0,
      "Moving a message to Junk did not train bogofilter",
    )
    self.assertFalse(os.path.exists(
      os.path.join(
        self.computer_partition_root_path,
        "bogofilter",
        login_address,
      )
    ))


  @contextmanager
  def _imap(self, address, password="password123"):
    parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()["_"]
    )
    imap = imaplib.IMAP4(
      parameter_dict["imap-smtp-ipv6"], int(parameter_dict["imap-port"]),
      timeout=10)
    try:
      imap.starttls(ssl_context=self._get_ssl_context())
      imap.login(address, password)
      yield imap
    finally:
      try:
        imap.logout()
      except Exception:
        pass

  def _find_message(self, imap, mailbox, subject, timeout=0):
    """Return the UID of the message with subject in mailbox, or None.

    Wait up to timeout seconds for the message to arrive.
    """
    deadline = time.time() + timeout
    while True:
      result, _ = imap.select(mailbox)
      self.assertEqual(result, "OK")
      result, data = imap.uid("SEARCH", None, '(HEADER Subject "%s")' % subject)
      self.assertEqual(result, "OK")
      uid_list = data[0].split()
      self.assertLessEqual(len(uid_list), 1)
      if uid_list or time.time() >= deadline:
        return uid_list[0] if uid_list else None
      time.sleep(1)

  def _get_flags(self, imap, mailbox, subject):
    uid = self._find_message(imap, mailbox, subject)
    self.assertIsNotNone(uid, "%r not found in %s" % (subject, mailbox))
    result, data = imap.uid("FETCH", uid, "(FLAGS)")
    self.assertEqual(result, "OK")
    return imaplib.ParseFlags(data[0]) if data[0] else ()

  def _move(self, imap, source, destination, subject):
    uid = self._find_message(imap, source, subject)
    self.assertIsNotNone(uid, "%r not found in %s" % (subject, source))
    result, _ = imap.uid("MOVE", uid, destination)
    self.assertEqual(result, "OK")

  def _dump_bogofilter_database(self, address):
    """Return the non-zero counts of the bogofilter database of address.

    The ".MSG_COUNT" key gives the number of registered spam and ham
    messages.
    """
    wordlist_path = os.path.join(
      self.computer_partition_root_path, "bogofilter", address, "wordlist.db")
    if not os.path.exists(wordlist_path):
      return {}
    with open(os.path.join(self.computer_partition_root_path,
        "etc", "sieve", "execute", "bogofilter-learn.sh")) as f:
      bogofilter = re.search(r"(\S+)/bin/bogofilter ", f.read()).group(1)
    output = subprocess.check_output(
      [bogofilter + "/bin/bogoutil", "-d", wordlist_path],
      universal_newlines=True)
    counts = {}
    for line in output.splitlines():
      token, spam, ham = line.split()[:3]
      if token not in (".WORDLIST_VERSION", ".ENCODING") and (spam, ham) != ("0", "0"):
        counts[token] = (int(spam), int(ham))
    return counts

  def _get_bogofilter_message_count(self, address):
    """Return the number of spam and ham messages registered for address."""
    return self._dump_bogofilter_database(address).get(".MSG_COUNT", (0, 0))

  def test_bogofilter_trains_from_junk_moves_and_spam_verdicts(self):
    """Moves to and from Junk train bogofilter, and so does a spam verdict.

    Each message is registered in one class at most. Moving a message from
    Junk to Trash does not train.
    """
    address = "testmail@bogofilter-training.example.com"
    spam_text = (
      "buy cheap pills now, limited offer, click here to order discount "
      "viagra casino lottery winner")
    ham_text = (
      "here are the notes from the project meeting, please review the "
      "budget and the schedule before friday")
    self.assertEqual(self._get_bogofilter_message_count(address), (0, 0))

    with self._imap(address) as imap:
      imap.create("Junk")
      imap.create("Trash")
      for subject, text in (("Cheap pills offer", spam_text),
                            ("Meeting notes", ham_text)):
        msg = MIMEText(text)
        msg["Subject"] = subject
        msg["From"] = "sender@example.net"
        msg["To"] = address
        result, _ = imap.append("INBOX", None, None, msg.as_bytes())
        self.assertEqual(result, "OK")

      # A move to Junk registers spam
      self._move(imap, "INBOX", "Junk", "Cheap pills offer")
      self.assertIn(b"$BogofilterSpam",
        self._get_flags(imap, "Junk", "Cheap pills offer"))
      self.assertEqual(self._get_bogofilter_message_count(address), (1, 0))

      # A move from Junk registers ham, also for a message that the user moved
      # to Junk
      self._move(imap, "INBOX", "Junk", "Meeting notes")
      self.assertEqual(self._get_bogofilter_message_count(address), (2, 0))
      self._move(imap, "Junk", "INBOX", "Meeting notes")
      flags = self._get_flags(imap, "INBOX", "Meeting notes")
      self.assertIn(b"$BogofilterHam", flags)
      self.assertNotIn(b"$BogofilterSpam", flags)
      self.assertEqual(self._get_bogofilter_message_count(address), (1, 1))
      trained_database = self._dump_bogofilter_database(address)

      # Moving a message back and forth does not register it again
      self._move(imap, "INBOX", "Junk", "Meeting notes")
      self._move(imap, "Junk", "INBOX", "Meeting notes")
      self.assertEqual(
        self._dump_bogofilter_database(address), trained_database)

      # A move from Junk to Trash does not train
      self._move(imap, "Junk", "Trash", "Cheap pills offer")
      self.assertIn(b"$BogofilterSpam",
        self._get_flags(imap, "Trash", "Cheap pills offer"))
      self.assertEqual(
        self._dump_bogofilter_database(address), trained_database)

    # Incoming mail classified as spam is registered as spam and filed into
    # Junk. Postfix removes the X-Bogosity header that the sender wrote.
    parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()["_"]
    )
    msg = MIMEText(spam_text)
    msg["Subject"] = "Cheap pills offer again"
    msg["From"] = "sender@example.net"
    msg["To"] = address
    msg["X-Bogosity"] = "Ham, tests=bogofilter, spamicity=0.000000"
    with smtplib.SMTP(parameter_dict["imap-smtp-ipv6"],
        int(parameter_dict["smtp-port"]), timeout=10) as smtp:
      smtp.starttls(context=self._get_ssl_context())
      smtp.sendmail("sender@example.net", [address], msg.as_string())

    with self._imap(address) as imap:
      uid = self._find_message(imap, "Junk", "Cheap pills offer again",
        timeout=30)
      self.assertIsNotNone(uid, "Incoming spam was not filed into Junk")
      result, data = imap.uid("FETCH", uid, "(FLAGS BODY.PEEK[HEADER])")
      self.assertEqual(result, "OK")
      flags = imaplib.ParseFlags(data[0][0])
      self.assertIn(b"$BogofilterSpam", flags)
      self.assertIn(b"\\Seen", flags)
      bogosity_list = re.findall(
        r"^X-Bogosity: (.*)$",
        data[0][1].decode("utf-8", errors="replace"),
        re.MULTILINE | re.IGNORECASE,
      )
      self.assertEqual(len(bogosity_list), 1, bogosity_list)
      self.assertTrue(bogosity_list[0].startswith("Spam,"), bogosity_list)
      self.assertEqual(self._get_bogofilter_message_count(address), (2, 1))
      delivered_database = self._dump_bogofilter_database(address)

      # Moving the message from Junk and back restores the database exactly
      self._move(imap, "Junk", "INBOX", "Cheap pills offer again")
      self.assertEqual(self._get_bogofilter_message_count(address), (1, 2))
      self._move(imap, "INBOX", "Junk", "Cheap pills offer again")
      self.assertEqual(
        self._dump_bogofilter_database(address), delivered_database)

  def test_bogofilter_header_removed_from_authenticated_mail(self):
    """A sender cannot give its own X-Bogosity header to a local user."""
    parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()["_"]
    )
    address = "testmail@example.com"
    subject = "Forged bogosity %s" % time.time()
    database = self._dump_bogofilter_database(address)
    msg = MIMEText("A message with a forged X-Bogosity header")
    msg["Subject"] = subject
    msg["From"] = address
    msg["To"] = address
    msg["X-Bogosity"] = "Spam, tests=bogofilter, spamicity=1.000000"
    with smtplib.SMTP(parameter_dict["imap-smtp-ipv6"],
        int(parameter_dict["smtp-port"]), timeout=10) as smtp:
      smtp.starttls(context=self._get_ssl_context())
      smtp.login(address, "password123")
      smtp.sendmail(address, [address], msg.as_string())

    with self._imap(address) as imap:
      uid = self._find_message(imap, "INBOX", subject, timeout=30)
      self.assertIsNotNone(uid, "Authenticated mail was not delivered to INBOX")
      result, data = imap.uid("FETCH", uid, "(BODY.PEEK[HEADER])")
      self.assertEqual(result, "OK")
      self.assertNotIn(b"x-bogosity", data[0][1].lower())
    self.assertEqual(self._dump_bogofilter_database(address), database)

class OrsTestCase(SlapOSInstanceTestCase):
  __partition_reference__ = 'ors'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'default-ors'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      "_": json.dumps(
        {
          "mail-domains": [
            "example.com"
          ],
          "inbound-relay": {"enable": False},
          "demo-disable-auth": True,
        }
      )
    }

  def _get_ssl_context(self):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

  def login_imap(self, address, password):
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    host = parameter_dict["imap-smtp-ipv6"]
    imap = None
    try:
      imap = imaplib.IMAP4(host, int(parameter_dict["imap-port"]), timeout=10)
      imap.starttls(ssl_context=self._get_ssl_context())
      imap.login(address, password)
    except Exception as e:
      self.fail(f"IMAP login failed for {address}: {e}")
    finally:
      if imap:
        try:
          imap.logout()
        except Exception:
          pass

  def test_demo_disable_auth_allows_any_credentials(self):
    self.login_imap("anonymous@example.com", "whatever-password")
    self.login_imap("another@example.com", "different-password")

  def test_demo_disable_auth_allows_smtp_sending(self):
    parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()["_"]
    )
    host = parameter_dict["imap-smtp-ipv6"]
    smtp_port = int(parameter_dict["smtp-port"])
    from_addr = "anonymous@example.com"
    to_addr = "another@example.com"
    with smtplib.SMTP(host, smtp_port, timeout=10) as smtp:
      smtp.starttls()
      smtp.login(from_addr, "whatever-password")
      smtp.sendmail(from_addr, [to_addr], "Subject: Hello")

  def test_demo_disable_auth_is_rejected_on_default_software_type(self):
    partition_reference = "default-demo-rejected"
    try:
      self.slap.request(
        software_release=self.getSoftwareURL(),
        partition_reference=partition_reference,
        partition_parameter_kw={
          "_": json.dumps(
            {
              "mail-domains": [
                "reject-demo.example.com"
              ],
              "inbound-relay": {"enable": False},
              "demo-disable-auth": True,
            }
          )
        },
        software_type='default',
        state='started',
      )
      with self.assertRaises(SlapOSNodeCommandError):
        self.slap.waitForInstance(max_retry=3)
    finally:
      self.slap.request(
        software_release=self.getSoftwareURL(),
        partition_reference=partition_reference,
        partition_parameter_kw={
          "_": json.dumps(
            {
              "mail-domains": [
                "reject-demo.example.com"
              ],
              "inbound-relay": {"enable": False},
            }
          )
        },
        software_type='default',
        state='destroyed',
      )
      self.slap.waitForInstance(max_retry=5)

