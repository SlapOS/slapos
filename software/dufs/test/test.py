##############################################################################
#
# Copyright (c) 2022 Nexedi SA and Contributors. All Rights Reserved.
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
import contextlib
import json
import io
import os
import pathlib
import subprocess
import tempfile
import urllib.parse


import requests
import lxml.html

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  pathlib.Path(__file__).parent.parent / 'software.cfg')


class TestFileServer(SlapOSInstanceTestCase):
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

  def _decode_index_content(self, response_text:str) -> dict:
    index_data, = lxml.html.fromstring(
      response_text).xpath('.//template[@id="index-data"]/text()')
    return json.loads(base64.b64decode(index_data))

  def test_anonymous_can_only_access_public(self):
    resp = requests.get(
      self.connection_parameters['public-url'],
      verify=self.ca_cert,
    )
    self.assertEqual(resp.status_code, requests.codes.ok)

    with open(os.path.join(self.computer_partition_root_path, 'srv', 'www', 'secret.txt'), 'w'):
      resp = requests.get(
        urllib.parse.urljoin(self.connection_parameters['public-url'], '../secret.txt'),
        verify=self.ca_cert,
      )
      self.assertEqual(resp.status_code, requests.codes.unauthorized)
      resp = requests.get(
        urllib.parse.urljoin(self.connection_parameters['public-url'], '../not-exist.txt'),
        verify=self.ca_cert,
      )
      self.assertEqual(resp.status_code, requests.codes.unauthorized)

      # index is allowed on / but it only shows /pub/
      resp = requests.get(
        urllib.parse.urljoin(self.connection_parameters['public-url'], '..'),
        verify=self.ca_cert,
      )
      self.assertEqual(
        [path['name'] for path in self._decode_index_content(resp.text)['paths']],
        ['pub'])
      self.assertEqual(resp.status_code, requests.codes.ok)

  def test_index(self):
    pub = self.computer_partition_root_path / 'srv' / 'www' / 'pub'
    (pub / 'with-index').mkdir()
    (pub / 'with-index' / 'index.html').write_text('<html>Hello !</html>')
    self.assertEqual(
      requests.get(
        urllib.parse.urljoin(self.connection_parameters['public-url'], 'with-index/'),
        verify=self.ca_cert,
      ).text,
      '<html>Hello !</html>')

    (pub / 'without-index').mkdir()
    (pub / 'without-index' / 'file.txt').write_text('Hello !')
    self.assertIn(
      'file.txt',
      [path['name'] for path in
        self._decode_index_content(
          requests.get(
          urllib.parse.urljoin(self.connection_parameters['public-url'], 'without-index/'),
          verify=self.ca_cert,
        ).text)['paths']
      ]
    )

  def test_upload_file_refused_without_auth(self):
    parsed_upload_url = urllib.parse.urlparse(self.connection_parameters['upload-url'])
    # upload-url has username:password, remove it
    self.assertTrue(parsed_upload_url.password)
    upload_url = parsed_upload_url._replace(
      netloc=f'[{parsed_upload_url.hostname}]:{parsed_upload_url.port}').geturl()
    resp = requests.put(
      urllib.parse.urljoin(upload_url, 'hello.txt'),
      data=io.BytesIO(b'hello'),
      verify=self.ca_cert,
    )
    self.assertEqual(resp.status_code, requests.codes.unauthorized)

  def test_upload_file(self):
    for path in 'hello.txt', 'pub/hello.txt', 'create/intermediate/paths':
      with self.subTest(path):
        resp = requests.put(
          urllib.parse.urljoin(self.connection_parameters['upload-url'], path),
          data=io.BytesIO(b'hello'),
          verify=self.ca_cert,
        )
        self.assertEqual(resp.status_code, requests.codes.created)

        resp = requests.get(
          urllib.parse.urljoin(self.connection_parameters['upload-url'], path),
          verify=self.ca_cert,
        )
        self.assertEqual(resp.text, 'hello')
        self.assertEqual(resp.status_code, requests.codes.ok)

  def test_renew_certificate(self):
    def _getpeercert():
      # XXX low level way to get get the server certificate
      with requests.Session() as session:
        pool = session.get(
          self.connection_parameters['public-url'],
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
          'etc/service/dufs-certificate-updater'),
      ),
      capture_output=not self._debug,
    )

    # reprocess instance to get the new certificate, after removing the timestamp
    # to force execution
    (self.computer_partition_root_path / '.timestamp').unlink()
    self.waitForInstance()

    cert_after = _getpeercert()
    self.assertNotEqual(cert_before['notAfter'], cert_after['notAfter'])
