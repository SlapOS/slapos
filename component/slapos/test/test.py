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

import os
import shutil
import subprocess
import sys

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.grid import utils

obs_cfg = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'obs.cfg'))

# TODO: can we do this not at import time ? probably using load_test ( https://docs.python.org/3/library/unittest.html#load-tests-protocol )
test_root_dir = os.path.join(os.environ['SLAPOS_TEST_WORKING_DIR'], 'obs')
target_directory = '/opt/slapos'
build_root_directory = os.path.join(test_root_dir, 'build_root_directory')
build_directory = build_root_directory + target_directory
bin_directory = os.path.join(build_directory, 'bin')
buildout_bin = os.path.join(bin_directory, 'buildout')
download_cache = os.path.join(build_directory, 'download_cache')
extends_cache = os.path.join(build_directory, 'extends_cache')
profile_cfg = os.path.join(build_directory, 'buildout.cfg')

for d in build_directory, download_cache, extends_cache, bin_directory:
  os.makedirs(d, exist_ok=True)

with open(profile_cfg, 'w') as f:
  f.write(f'''\
[buildout]
rootdir = {target_directory}
destdir = {build_root_directory}
builddir = {build_directory}
extends = {obs_cfg}
download-cache = {download_cache}
extends-cache = {extends_cache}
# TODO: disable shared parts ??? (maybe not needed now that we have shared=false)
''')

_, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    profile_cfg,
    shared_part_list=[])

def setUpModule():
  utils.launchBuildout(
    path=build_directory,
    # rebootstrap doesn't like a buildout not at the expected location
    buildout_binary=shutil.copy(os.path.join(os.path.dirname(sys.executable), 'buildout'), buildout_bin),
    logger=SlapOSInstanceTestCase.logger)

class TestSlapOSNodeBuild(SlapOSInstanceTestCase):
  request_instance = False

  def test(self):
    import pdb; pdb.set_trace()
