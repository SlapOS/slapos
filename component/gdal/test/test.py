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

# pyright: strict

from pathlib import Path
import subprocess

from slapos.grid.utils import md5digest
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    Path(__file__).parent.parent / "test.cfg"
)


class GDALTestCase(SlapOSInstanceTestCase):
    """Tests for the GDAL component."""

    request_instance = False

    def test_noinstance(self):
        """Test that no SlapOS instance is being created for this component."""
        self.assertFalse(hasattr(self, "computer_partition"))

    def test_import(self):
        """Test that the GDAL Python module is importable."""
        software_path = (
          Path(self.slap.software_directory)
          / md5digest(self.getSoftwareURL())
        )
        self.assertTrue(software_path.exists())
        self.assertTrue(software_path.is_dir())

        bin_path = software_path / "bin"
        self.assertTrue(bin_path.exists())
        self.assertTrue(bin_path.is_dir())

        python_exe = bin_path / "python-gdal"
        self.assertTrue(python_exe.exists())
        self.assertTrue(python_exe.is_file())

        subprocess.check_call([python_exe, "-c", "import osgeo.gdal"])
