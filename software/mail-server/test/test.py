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
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      "_": json.dumps(
        {
          "mail-domains": [
            "example.com"
          ],
          "relay-host": "::1",
          "relay-port": 1234
        }
      )
    }

  def test_postfix(self):
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    host = parameter_dict["imap-smtp-ipv6"]

    try:
      server = smtplib.SMTP(host, int(parameter_dict["smtp-port"]), timeout=10)
      server.quit()
    except Exception as e:
      self.fail(f"SMTP connection failed: {e}")

  def test_dovecot(self):
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    host = parameter_dict["imap-smtp-ipv6"]
    imap = None
    try:
      imap = imaplib.IMAP4(host, int(parameter_dict["imap-port"]), timeout=10)
      imap.login("testmail@example.com", "MotDePasseEmail")
      imap.select("INBOX")
      result, data = imap.search(None, "ALL")
      self.assertEqual(result, "OK")
    except Exception as e:
      self.fail(f"IMAP connection failed: {e}")
    finally:
      if imap:
        imap.logout()
