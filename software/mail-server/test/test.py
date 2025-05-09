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
import socket
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
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
      with time_limit(20):
        sock.connect((host, int(parameter_dict["smtp-port"])))
        self.assertIn(b"ESMTP Postfix", sock.recv(1024))
        sock.send(b"EHLO localhost\r\n")
        self.assertIn(b"250", sock.recv(1024))
    finally:
      sock.close()

  def test_dovecot(self):
    parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()["_"])
    host = parameter_dict["imap-smtp-ipv6"]
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
      with time_limit(20):
        sock.connect((host, int(parameter_dict["imap-port"])))
        self.assertIn(b"Dovecot ready.", sock.recv(1024))
        sock.send(b"1 LOGIN invalid foobar\r\n")
        self.assertIn(b"1 NO [AUTHENTICATIONFAILED]", sock.recv(1024))
        # sock.send(b"1 LOGIN testmail@example.com MotDePasseEmail\r\n")
        # self.assertIn(b"Logged in", sock.recv(1024))
        # sock.send(b"2 SELECT INBOX\r\n")
        # self.assertIn(b"2 OK [READ-WRITE]", sock.recv(1024))
    finally:
      sock.close()
