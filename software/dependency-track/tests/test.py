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

import os
import subprocess
import tarfile
import urllib.parse

import lxml.html
import requests
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.testing.utils import CrontabMixin

setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "software.cfg"))
)


class TestDependencyTrack(CrontabMixin, InstanceTestCase):
  __partition_reference__ = "DT"  # postgresql use a socket in data dir

  def setUp(self):
    self.url = self.computer_partition.getConnectionParameterDict()["url"]

  def test_http_single_page_app(self):
    resp = requests.get(self.url, verify=False)
    home_page_text = resp.text
    self.assertTrue(resp.ok)
    resp = requests.get(urllib.parse.urljoin(self.url, "/projects"), verify=False)
    self.assertTrue(resp.ok)
    self.assertEqual(resp.text, home_page_text)

  def test_http_api(self):
    resp = requests.get(urllib.parse.urljoin(self.url, "/api/version"), verify=False)
    resp.raise_for_status()
    self.assertEqual(resp.json()["application"], "Dependency-Track")

  def test_http_caching_and_compression(self):
    resp = requests.get(self.url, verify=False)
    tree = lxml.html.fromstring(resp.text)
    for path in (
      tree.xpath("//link[@rel='stylesheet']/@href")[0],
      tree.xpath("//script[@src]/@src")[0],
    ):
      with self.subTest(path=path):
        resp = requests.get(
          urllib.parse.urljoin(self.url, path),
          headers={"Accept-Encoding": "gzip"},
          verify=False,
        )
        resp.raise_for_status()
        self.assertEqual(resp.headers["Cache-Control"], "public, max-age=31536000, immutable")
        self.assertEqual(resp.headers["Content-Encoding"], "gzip")

  def test_logs(self):
    var_log = self.computer_partition_root_path / "var" / "log"
    srv_backup_logrotate = self.computer_partition_root_path / "srv" / "backup" / "logrotate"

    def _make_request():
      requests.post(urllib.parse.urljoin(self.url, '/api/v1/user/login'), verify=False,)

    _make_request()
    self.assertTrue((var_log / "dependency-track-api-sever.log").read_text())
    self.assertTrue((var_log / "nginx_access.log").read_text())
    self.assertTrue((var_log / "nginx_error.log").read_text())

    self._executeCrontabAtDate('logrotate', '2000-01-01')
    self._executeCrontabAtDate('logrotate', '2001-02-03')
    self.assertTrue((srv_backup_logrotate / "dependency-track-api-sever.log-20010203").read_text())
    self.assertTrue((srv_backup_logrotate / "nginx_access.log-20010203").read_text())
    self.assertTrue((srv_backup_logrotate / "nginx_error.log-20010203").read_text())

    _make_request()
    self.assertTrue((var_log / "dependency-track-api-sever.log").read_text())
    self.assertTrue((var_log / "nginx_access.log").read_text())
    self._executeCrontabAtDate('logrotate', '2001-02-04')
    self.assertTrue((srv_backup_logrotate / "dependency-track-api-sever.log-20010203.xz").exists())
    self.assertTrue((srv_backup_logrotate / "nginx_access.log-20010203.xz").exists())
    self.assertTrue((srv_backup_logrotate / "dependency-track-api-sever.log-20010204").read_text())
    self.assertTrue((srv_backup_logrotate / "nginx_access.log-20010204").read_text())


class TestBackup(InstanceTestCase, CrontabMixin):
  __partition_reference__ = "b"  # postgresql use a socket in data dir

  def test(self):
    partition_root = self.computer_partition_root_path
    psql = partition_root / 'bin' / 'postgresql-psql'
    marker = (
      partition_root / 'srv' / 'dependency-track' / '.dependency-track'
      / 'backup-test-marker')

    marker.write_text('before backup')
    subprocess.check_call([psql, '-c', 'CREATE TABLE backup_test (value text)'])
    subprocess.check_call(
      [psql, '-c', "INSERT INTO backup_test VALUES ('before backup')"])

    self._executeCrontabAtDate('backup-crontab-entry', '2000-01-01')

    with tarfile.open(
      partition_root / 'srv' / 'backup' / 'dependency-track.tar.gz') as tar:
      self.assertIn('./backup-test-marker', tar.getnames())

    with self.slap.instance_supervisor_rpc as supervisor:
      process_info, = [
        process_info
        for process_info in supervisor.getAllProcessInfo()
        if 'dependency-track-api-server-instance' in process_info['name']
      ]
      supervisor.stopProcess(
        f"{process_info['group']}:{process_info['name']}")
    marker.unlink()
    subprocess.check_call([psql, '-c', 'DROP TABLE backup_test'])
    subprocess.check_call(partition_root / 'bin' / 'postgresql-restore-backup')

    self.assertEqual(marker.read_text(), 'before backup')
    self.assertEqual(
      subprocess.check_output(
        [psql, '-tAc', 'SELECT value FROM backup_test']).strip(),
      b'before backup')

    (partition_root / '.timestamp').unlink()
    self.waitForInstance()
