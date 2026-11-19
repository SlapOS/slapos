##############################################################################
#
# Copyright (c) 2025 Nexedi SA and Contributors. All Rights Reserved.
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
import json
import os
import pathlib
import subprocess
import tempfile
import urllib.parse

import requests
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../software-cpu.cfg')))


class TestLlamacpp(SlapOSInstanceTestCase):
  __partition_reference__ = 'G'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({})}

  def setUp(self):
    self.connection_parameters = self.computer_partition.getConnectionParameterDict()
    self.auth_headers = {
        'Authorization': 'Bearer ' + self.connection_parameters['api-key']}
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
        )
      ).text)
    self.addCleanup(os.unlink, ca_cert.name)
    return ca_cert.name

  def test_url_get(self):
    resp = requests.get(
        self.connection_parameters['backend-url'],
        headers=self.auth_headers,
        verify=self.ca_cert)
    self.assertEqual(requests.codes.ok, resp.status_code)

  def test_models(self):
    resp = requests.get(
        f'{self.connection_parameters["backend-url"]}/v1/models',
        verify=self.ca_cert)
    self.assertEqual(requests.codes.ok, resp.status_code)
    model_list = resp.json()
    self.assertEqual('list', model_list['object'])
    self.assertTrue(model_list['data'])
    self.assertIn(
        self.connection_parameters['filename'], model_list['data'][0]['id'])

  def test_tokenize_needs_token(self):
    endpoint = f'{self.connection_parameters["backend-url"]}/tokenize'
    payload = {'content': 'hello'}
    with self.subTest('no api key'):
      resp = requests.post(
          endpoint, json=payload, verify=self.ca_cert,
          headers={'Authorization': 'Bearer wrong'})
      self.assertEqual(requests.codes.unauthorized, resp.status_code)
    with self.subTest('wrong api key'):
      resp = requests.post(endpoint, json=payload, verify=self.ca_cert)
      self.assertEqual(requests.codes.unauthorized, resp.status_code)
    with self.subTest('good api key'):
      resp = requests.post(
          endpoint, json=payload, headers=self.auth_headers, verify=self.ca_cert)
      self.assertEqual(requests.codes.ok, resp.status_code)
      self.assertTrue(resp.json()['tokens'])

  def test_embeddings(self):
    resp = requests.post(
        f'{self.connection_parameters["backend-url"]}/v1/embeddings',
        json={'input': 'hello'},
        verify=self.ca_cert,
        headers=self.auth_headers,
    )
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertTrue(resp.json()['data'])

  def test_renew_certificate(self):
    def _getpeercert():
      # XXX low level way to get the server certificate
      with requests.Session() as session:
        pool = session.get(
          self.connection_parameters['backend-url'],
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
          'etc/service/nginx-certificate-updater',
        ),
      ),
      capture_output=not self._debug,
    )
    # reprocess instance to get the new certificate, after removing the timestamp
    # to force execution
    (pathlib.Path(self.computer_partition_root_path) / '.timestamp').unlink()
    self.waitForInstance()

    cert_after = _getpeercert()
    self.assertNotEqual(cert_before['notAfter'], cert_after['notAfter'])
