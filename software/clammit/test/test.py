##############################################################################
#
# Copyright (c) 2024 Nexedi SA and Contributors. All Rights Reserved.
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

import contextlib
import io
import os
import pathlib
import subprocess
import tempfile
import urllib.parse

import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class ClammitTestCase(SlapOSInstanceTestCase):
  def setUp(self):
    self.connection_parameters = \
        self.computer_partition.getConnectionParameterDict()
    self.ca_cert = self._getCaucaseServiceCACertificate()

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

  def test_upload_of_files_to_clammit_for_scan(self):
    resp = requests.get(
      self.connection_parameters['scan-url'],
      verify=self.ca_cert,
    )

    r = requests.post(
      self.connection_parameters['scan-url'],
      files={'file': 'Hello world'},
      verify=self.ca_cert,
    )
    self.assertEqual(r.status_code, 200)

    r = requests.post(
      self.connection_parameters['scan-url'],
      files={'file': b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'},
      verify=self.ca_cert,
    )
    self.assertEqual(r.status_code, 418)

  def test_renew_certificate(self):
    def _getpeercert():
      # XXX low level way to get the server certificate
      with requests.Session() as session:
        pool = session.get(
          self.connection_parameters['url'],
          verify=self.ca_cert,
        ).raw._pool.pool
        with contextlib.closing(pool.get()) as cnx:
          return cnx.sock._sslobj.getpeercert()

    cert_before = _getpeercert()
    # execute certificate updater when it's time to renew certificate.
    # use a timeout, because this service runs forever
    subprocess.run(
      (
        'timeout',
        '5',
        'faketime',
        '+63 days',
        os.path.join(
          self.computer_partition_root_path,
          'etc/service/frontend-certificate-updater'),
      ),
      capture_output=not self._debug,
    )

    # reprocess instance to get the new certificate, after removing the timestamp
    # to force execution
    (pathlib.Path(self.computer_partition_root_path) / '.timestamp').unlink()
    self.waitForInstance()

    cert_after = _getpeercert()
    self.assertNotEqual(cert_before['notAfter'], cert_after['notAfter'])
