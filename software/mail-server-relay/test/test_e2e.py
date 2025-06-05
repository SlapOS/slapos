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
  def getInstanceParameterDict(cls):
    return {
      "_": json.dumps(
        {
          "default-relay-config": {
            "relay-host": "example.com",
            "relay-port": 2525,
            "relay-user": "user",
            "relay-password": "pass",
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
    default_instance = super(E2E, cls).requestDefaultInstance(state)
    cls.waitForInstance()
    cls.mail_server_instances = [
      cls.requestMailServerForDomain(domain) for domain in cls.domain_list
    ]
    return default_instance

  @classmethod
  def requestMailServerForDomain(cls, domain):
    param_dict = {
      "mail-domains": [domain],
      "relay-sr-url": cls.getSoftwareURL()
    }
    return cls.slap.request(
      software_release=software_urls[1],
      partition_reference=domain,
      partition_parameter_kw={'_': json.dumps(param_dict)},
      software_type='default',
    )

  def test_servers(self):
    for server in self.mail_server_instances:
      params = json.loads(server.getConnectionParameterDict()['_'])
      self.assertIn('imap-port', params, "Vibe check")

  def test_send_email(self):
    # each mail server has testmail@{{domain}}:MotDePasseEmail::
    # try sending a mail from mail1 to mail2 using smtp
    mail1, mail2 = self.mail_server_instances[:2]
    mail1_params = json.loads(mail1.getConnectionParameterDict()['_'])
    sender = "testmail@mail1.domain.lan"
    recipient = "testmail@mail2.domain.lan"
    mail2_params = json.loads(mail2.getConnectionParameterDict()['_'])
    msg = "Subject: Test Email\n\nThis is a test email."
    with smtplib.SMTP(mail1_params['imap-smtp-ipv6'], mail1_params['smtp-port'], timeout=10) as smtp:
      smtp.login(sender, "MotDePasseEmail")
      smtp.sendmail(
        from_addr=sender,
        to_addrs=[recipient],
        msg=msg
      )
    import time
    time.sleep(10)
    with imaplib.IMAP4(mail2_params['imap-smtp-ipv6'], mail2_params['imap-port'], timeout=10) as imap:
      imap.login(recipient, "MotDePasseEmail")
      imap.select("INBOX")
      result, data = imap.search(None, 'ALL')
      self.assertEqual(result, 'OK', "Failed to search emails")
      email_ids = data[0].split()
      if len(email_ids) == 0:
        breakpoint()
      self.assertGreater(len(email_ids), 0, "No emails found in inbox")
      # Check if the last email is the one we sent
      latest_email_id = email_ids[-1]
      result, data = imap.fetch(latest_email_id, '(RFC822)')
      self.assertEqual(result, 'OK', "Failed to fetch email")
      email_body = data[0][1].decode('utf-8')
      self.assertIn("This is a test email.", email_body, "Email content does not match")