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
import signal
from contextlib import contextmanager

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "software.cfg"))
)

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutError
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

class PostfixTestCase(SlapOSInstanceTestCase):
  def check_imap(self, address, password):
    """Test IMAP login with given address and password"""
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    host = parameter_dict["imap-smtp-ipv6"]
    imap = None
    try:
      imap = imaplib.IMAP4(host, int(parameter_dict["imap-port"]), timeout=10)
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
            "example.com"
          ],
          "no-relay": True,
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

  def test_webmail(self):
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    webmail_url = parameter_dict.get("webmail-url", "<missing>")
    self.assertTrue(webmail_url.startswith("http"), "Webmail URL should start with http")

    import urllib.request
    import ssl

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

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
