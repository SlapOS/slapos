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
import urllib.parse
import tempfile

import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestResticRestServer(SlapOSInstanceTestCase):
  # XXX WIP
  instance_max_retry = 3
  def setUp(self):
    self.connection_parameters = self.computer_partition.getConnectionParameterDict()

  def _getCaucaseServiceCACertificate(self):
    ca_cert = tempfile.NamedTemporaryFile(
        prefix="ca.crt.pem",
        mode="w",
        delete=False,
    )
    ca_cert.write(
        requests.get(
            urllib.parse.urljoin(
                self.connection_parameters['caucase-url'],
                '/cas/crt/ca.crt.pem',
            )).text)
    self.addCleanup(os.unlink, ca_cert.name)
    return ca_cert.name


  def test_http_get(self):
    import pdb; pdb.set_trace()
    ca = self._getCaucaseServiceCACertificate()
    resp = requests.get(
        self.connection_parameters['url'],
        verify=ca)

    # example usage:
    # zcat mysqldump.sql.gz | ../inst/TestResticRestServer-0/software_release/go.work/bin/restic --cacert={ca} --password-file password --repo rest:https://backup:password@[::1]:19080 --stdin --stdin-filename=mysqldump.sql backup
