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
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
##############################################################################

import hashlib
import os
import shutil
import subprocess
import tempfile

from slapos.testing.testcase import installSoftwareUrlList, makeModuleSetUpAndTestCaseClass

software_release_url = os.path.abspath(
  os.path.join(os.path.dirname(__file__), '..', 'test.cfg'))

setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(software_release_url))

class TestMariaDB(InstanceTestCase):
  request_instance = False

  def test(self):
    mariadb_path = os.path.join(
      self.slap.software_directory,
      hashlib.md5(self.getSoftwareURL().encode()).hexdigest(),
      'parts',
      'mariadb',
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
      shutil.copytree(
        mariadb_path,
        tmp_dir,
        symlinks=True,
        dirs_exist_ok=True,
      )
      test_dir = os.path.join(tmp_dir, 'mariadb-test')
      if not os.path.isdir(test_dir): # BBB MariaDB < 11
        test_dir = os.path.join(tmp_dir, 'mysql-test')
      os.chdir(test_dir)
      skip_test_list = [
        'spider',            # fail if 'failed to retrieve the MAC address'.
        'mysqld--help-aria', # fail if 'failed to retrieve the MAC address'.
        'mysqldump-header',  # fail with our -DDEFAULT_CHARSET=utf8 build.
        'ssl_autoverify',    # fail without Net/SSLeay.pm.
      ]
      result = subprocess.run(
        ['./mtr', '--parallel=10', '--force', '--max-test-fail=40', '--mem',
         '--skip-test=(%s)' % ('|'.join(skip_test_list))],
        capture_output=True,
      )
      self.assertEqual(result.returncode, 0, result.stdout)
