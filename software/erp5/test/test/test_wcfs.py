# Copyright (C) 2021  Nexedi SA and Contributors.
#
# This program is free software: you can Use, Study, Modify and Redistribute
# it under the terms of the GNU General Public License version 3, or (at your
# option) any later version, as published by the Free Software Foundation.
#
# You can also Link and Combine this program with other software covered by
# the terms of any of the Free Software licenses or any of the Open Source
# Initiative approved licenses and Convey the resulting work. Corresponding
# source of such a combination shall include the source code for all other
# software used.
#
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See COPYING file for full licensing terms.
# See https://www.nexedi.com/licensing for rationale and options.

import json
import os.path
import subprocess
import unittest

from slapos.grid.utils import md5digest

from . import ERP5InstanceTestCase, setUpModule as _setUpModule
from .test_erp5 import TestPublishedURLIsReachableMixin

# skip tests when software release is built with wendelin.core 1.
def setUpModule():
  _setUpModule()

  cls = ERP5InstanceTestCase
  if not os.path.exists(
    os.path.join(
      cls.slap.software_directory,
      md5digest(cls.getSoftwareURL()),
      'bin', 'wcfs')):
    raise unittest.SkipTest("built with wendelin.core 1")


class TestWCFS(ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test Wendelin Core File System
  """
  __partition_reference__ = 'wcfs'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({'wcfs': {'enable': True}})}

  def getZUrl(self):
    return json.loads(
      self.getComputerPartition('wcfs').getConnectionParameter('_')
    )['serving-zurl']

  def test_wcfs_accessible(self):
    """Verify that wcfs filesystem is basically accessible.

       - we can read .wcfs/zurl
       - its content is equal to published `serving-zurl`
    """
    zurl = self.getZUrl()
    mntpt = lookupMount(zurl)
    zurl_ = readfile("%s/.wcfs/zurl" % mntpt)
    self.assertEqual(zurl_, zurl)

  def test_workload(self):
    """Verify simple workload (reading/writing operation) on WCFS is successful"""
    wcfs_test_bin = self.getRootPartitionConnectionParameterDict()['erp5_wcfs_test_bin']
    # If exit code = 0, all subtests were successful
    self.assertEqual(0, subprocess.call([wcfs_test_bin, self.getZUrl()]))


# lookupMount returns /proc/mount entry for wcfs mounted to serve zurl.
def lookupMount(zurl):
  for line in readfile('/proc/mounts').splitlines():
    # <zurl> <mountpoint> fuse.wcfs ...
    zurl_, mntpt, typ, _ = line.split(None, 3)
    if typ != 'fuse.wcfs':
      continue
    if zurl_ == zurl:
      return mntpt
  raise KeyError("lookup mount %s: no /proc/mounts entry" % zurl)

# readfile returns content of file @path.
def readfile(path):
  with open(path) as f:
    return f.read()
