##############################################################################
#
# Copyright (c) 2021 Nexedi SA and Contributors. All Rights Reserved.
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


class TestResticRestServer(SlapOSInstanceTestCase):

  def setUp(self):
    self.connection_parameters = \
        self.computer_partition.getConnectionParameterDict()
    parsed_url = urllib.parse.urlparse(self.connection_parameters['url'])
    self.url_with_credentials = parsed_url._replace(
        netloc='{}:{}@[{}]:{}'.format(
            self.connection_parameters['rest-server-user'],
            self.connection_parameters['rest-server-password'],
            parsed_url.hostname,
            parsed_url.port,
        )).geturl()

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

  def test_http_get(self):
    resp = requests.get(self.connection_parameters['url'], verify=self.ca_cert)
    self.assertEqual(resp.status_code, requests.codes.unauthorized)

    resp = requests.get(
        urllib.parse.urljoin(
            self.url_with_credentials,
            '/metrics',
        ),
        verify=self.ca_cert,
    )
    # a random metric
    self.assertIn('process_cpu_seconds_total', resp.text)
    resp.raise_for_status()

  def test_backup_scenario(self):
    restic_bin = os.path.join(
        self.computer_partition_root_path,
        'software_release',
        'go.work',
        'bin',
        'restic',
    )

    def get_restic_output(*args, **kw):
      return subprocess.check_output(
          (
              restic_bin,
              '--cacert',
              self.ca_cert,
              '--password-file',
              password_file.name,
              '--repo',
              'rest:' + self.url_with_credentials,
          ) + args,
          universal_newlines=True,
          **kw,
      )

    with tempfile.TemporaryDirectory() as work_directory,\
        tempfile.NamedTemporaryFile(mode='w') as password_file:
      password_file.write('secret')
      password_file.flush()

      with open(os.path.join(work_directory, 'data'), 'w') as f:
        f.write('data to backup')
      with self.assertRaises(subprocess.CalledProcessError) as exc_context:
        get_restic_output('snapshots', stderr=subprocess.PIPE)
      self.assertIn('Is there a repository at the following location?',
                    exc_context.exception.stderr)

      out = get_restic_output('init')
      self.assertIn('created restic repository', out)

      out = get_restic_output('backup', work_directory)
      self.assertIn('Added to the repo', out)

      out = get_restic_output('snapshots')
      self.assertEqual(out.splitlines()[-1], '1 snapshots')
      snapshot_id = out.splitlines()[2].split()[0]
      backup_path = out.splitlines()[2].split()[-1]
      restore_directory = os.path.join(work_directory, 'restore')

      out = get_restic_output(
          'restore',
          snapshot_id,
          '--target',
          restore_directory,
      )
      self.assertIn('restoring <Snapshot', out)
      with open(os.path.join(restore_directory, backup_path, 'data')) as f:
        self.assertEqual(f.read(), 'data to backup')

  def test_renew_certificate(self):
    def _getpeercert():
      # XXX low level way to get get the server certificate
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
          'etc/service/rest-server-certificate-updater'),
      ),
      capture_output=not self._debug,
    )

    # reprocess instance to get the new certificate, after removing the timestamp
    # to force execution
    (pathlib.Path(self.computer_partition_root_path) / '.timestamp').unlink()
    self.waitForInstance()

    cert_after = _getpeercert()
    self.assertNotEqual(cert_before['notAfter'], cert_after['notAfter'])
