##############################################################################
#
# Copyright (c) 2018 Nexedi SA and Contributors. All Rights Reserved.
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

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, MailServerTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))

param_dict = {
    "mail_domain": "mail.local",
}

class TestDefaultInstance(MailServerTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(param_dict)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "default"
    def test_enb_conf(self):
      self.slap.waitForInstance()
      connection_parameters = self.computer_partition.getConnectionParameterDict()

      imap_smtp_ipv6 = connection_parameters['imap-smtp-ipv6']
      imap_port = connection_parameters['imap-port']
      smtp_port = connection_parameters['smtp-port']

      # Check connection parameters are not empty
      self.assertTrue(imap_smtp_ipv6)
      self.assertTrue(imap_port)
      self.assertTrue(smtp_port)

      # Check conf contains correct domain
      conf_file = glob.glob(os.path.join(
        self.slap.instance_directory, '*', 'etc', 'postfix', 'main.cf'))[0]

      with open(conf_file, 'r') as f:
        domain_configured = False
        for line in f:
          if line.startswith("virtual_mailbox_domains"):
            self.assertEqual(line, "virtual_mailbox_domains = {}\n".format(param_dict['mail_domain']))
            domain_configured = True
        self.assertTrue(domain_configured)
