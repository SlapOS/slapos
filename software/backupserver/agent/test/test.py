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
  os.path.join(os.path.dirname(__file__), '..', 'software.cfg'))

setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(software_release_url))

class TestBackupServerAgent(InstanceTestCase):
  request_instance = False

  def test(self):
    rdiff_backup_path = os.path.join(
      self.slap.software_directory,
      hashlib.md5(self.getSoftwareURL().encode()).hexdigest(),
      'parts',
      'rdiff-backup',
      'bin',
      'rdiff-backup',
    )
    result = subprocess.run(
      [rdiff_backup_path, '--version'],
      capture_output=True,
    )
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertEqual(result.stdout, b'rdiff-backup 1.0.5\n')
