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
import functools
import urllib.parse
import subprocess
import time
from typing import Optional, Tuple

import bs4
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.testing.caucase import CaucaseCertificate, CaucaseService


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "software.cfg"))
)


class TestGitlab(SlapOSInstanceTestCase):
  __partition_reference__ = "G"  # solve path too long for postgresql and unicorn
  instance_max_retry = 50  # puma takes time to be ready

  @classmethod
  def getInstanceSoftwareType(cls):
    return "gitlab"

  @classmethod
  def getInstanceParameterDict(cls):
    frontend_caucase = cls.getManagedResource("frontend_caucase", CaucaseService)
    certificate = cls.getManagedResource("client_certificate", CaucaseCertificate)
    certificate.request("shared frontend", frontend_caucase)
    return {
      "root-password": "admin1234",
      "frontend-caucase-url-list": frontend_caucase.url,
    }

  def setUp(self):
    self.backend_url = self.computer_partition.getConnectionParameterDict()[
      "backend_url"
    ]

  def test_http_get(self):
    resp = requests.get(self.backend_url, verify=False)
    self.assertTrue(resp.status_code in [requests.codes.ok, requests.codes.found])

  def test_rack_attack_sign_in_rate_limiting(self):
    client_certificate = self.getManagedResource(
      "client_certificate", CaucaseCertificate
    )
    session = requests.Session()
    session.cert = (client_certificate.cert_file, client_certificate.key_file)

    # Load the login page to get a CSRF token.
    response = session.get(
      urllib.parse.urljoin(self.backend_url, "users/sign_in"), verify=False
    )
    self.assertEqual(response.status_code, 200)

    # Extract the CSRF token and param.
    bsoup = bs4.BeautifulSoup(response.text, "html.parser")
    csrf_param = bsoup.find("meta", dict(name="csrf-param"))["content"]
    csrf_token = bsoup.find("meta", dict(name="csrf-token"))["content"]

    request_data = {
      "user[login]": "test",
      "user[password]": "random",
      csrf_param: csrf_token,
    }

    sign_in = functools.partial(
      session.post, response.url, data=request_data, verify=False
    )

    for _ in range(10):
      sign_in(headers={"X-Forwarded-For": "1.2.3.4"}).raise_for_status()
    # after 10 authentication failures, this client is rate limited
    self.assertEqual(sign_in(headers={"X-Forwarded-For": "1.2.3.4"}).status_code, 429)
    # but other clients are not
    self.assertNotEqual(
      sign_in(headers={"X-Forwarded-For": "5.6.7.8"}).status_code, 429
    )

  def _get_client_ip_address_from_nginx_log(
    self, cert: Optional[Tuple[str, str]]
  ) -> str:
    requests.get(
      urllib.parse.urljoin(
        self.backend_url,
        f"/users/sign_in?request_id={self.id()}",
      ),
      verify=False,
      cert=cert,
      headers={"X-Forwarded-For": "1.2.3.4"},
    ).raise_for_status()
    nginx_log_file = (
      self.computer_partition_root_path / "var" / "log" / "nginx" / "gitlab_access.log"
    )
    for _ in range(100):
      last_log_line = nginx_log_file.read_text().splitlines()[-1]
      if self.id() in last_log_line:
        return last_log_line.split("-")[0].strip()
      time.sleep(1)
    raise RuntimeError(f"Could not find {self.id()} in {last_log_line=}")

  def test_client_ip_in_nginx_log_with_certificate(self):
    client_certificate = self.getManagedResource(
      "client_certificate", CaucaseCertificate
    )
    self.assertEqual(
      self._get_client_ip_address_from_nginx_log(
        cert=(client_certificate.cert_file, client_certificate.key_file)
      ),
      "1.2.3.4",
    )

  def test_client_ip_in_nginx_log_without_certificate(self):
    self.assertNotEqual(
      self._get_client_ip_address_from_nginx_log(cert=None),
      "1.2.3.4",
    )

  def test_client_ip_in_nginx_log_with_not_verified_certificate(self):
    another_unrelated_caucase = self.getManagedResource(
      "another_unrelated_caucase", CaucaseService
    )
    unknown_client_certificate = self.getManagedResource(
      "unknown_client_certificate", CaucaseCertificate
    )
    unknown_client_certificate.request(
      "unknown client certificate", another_unrelated_caucase
    )
    self.assertNotEqual(
      self._get_client_ip_address_from_nginx_log(
        cert=(unknown_client_certificate.cert_file, unknown_client_certificate.key_file)
      ),
      "1.2.3.4",
    )

  def test_download_archive_rate_limiting(self):
    gitlab_rails_bin = self.computer_partition_root_path / 'bin' / 'gitlab-rails'

    subprocess.check_call(
      (gitlab_rails_bin,
      'runner',
      "user = User.find(1);" \
      "token = user.personal_access_tokens.create(scopes: [:api], name: 'Root token');" \
      "token.set_token('SLurtnxPscPsU-SDm4oN');" \
      "token.save!"),
    )

    client_certificate = self.getManagedResource('client_certificate', CaucaseCertificate)
    with requests.Session() as session:
      session.cert = (client_certificate.cert_file, client_certificate.key_file)
      session.verify = False

      ret = session.post(
        urllib.parse.urljoin(self.backend_url, '/api/v4/projects'),
        data={
          'name': 'sample-test',
          'visibility': 'public',
        },
        headers={"PRIVATE-TOKEN" : 'SLurtnxPscPsU-SDm4oN'},
      )
      ret.raise_for_status()
      project_id = ret.json()['id']

      session.post(
        urllib.parse.urljoin(
          self.backend_url, f"/api/v4/projects/{project_id}/repository/commits"
        ),
        json={
          "branch": "main",
          "commit_message": "Add a file to test download archive",
          "actions": [
            {"action": "create", "file_path": "README.md", "content": "file content"}
          ],
        },
        headers={"PRIVATE-TOKEN": "SLurtnxPscPsU-SDm4oN"},
      ).raise_for_status()

      for i, ext in enumerate(("zip", "tar.gz", "tar.bz2", "tar")):
        headers = {"X-Forwarded-For": f"{i}.{i}.{i}.{i}"}
        get = functools.partial(
          session.get,
          urllib.parse.urljoin(
            self.backend_url,
            f"/root/sample-test/-/archive/main/sample-test-main.{ext}",
          ),
          headers=headers,
        )
        with self.subTest(ext):
          get().raise_for_status()
          self.assertEqual(get().status_code, 429)

      self.assertEqual(
        session.get(
          urllib.parse.urljoin(
            self.backend_url,
            f"/root/sample-test/-/archive/invalidref/sample-test-invalidref.zip",
          ),
        ).status_code,
        404,
      )
