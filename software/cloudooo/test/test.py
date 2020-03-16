##############################################################################
# coding: utf-8
#
# Copyright (c) 2020 Nexedi SA and Contributors. All Rights Reserved.
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
import textwrap
import hashlib
from io import BytesIO

from PIL import Image
import requests

from slapos.recipe.librecipe import generateHashFromFiles
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, CloudOOoTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestCloudOOo(CloudOOoTestCase):
  def setUp(self):
    self.url = self.computer_partition.getConnectionParameterDict()["url"]

  def assertImagesSimilar(self, i1, i2, tolerance=5):
    """Assert images difference between images is less than `tolerance` %.
   taken from https://rosettacode.org/wiki/Percentage_difference_between_images
    """
    pairs = zip(i1.getdata(), i2.getdata())
    if len(i1.getbands()) == 1:
      # for gray-scale jpegs
      dif = sum(abs(p1-p2) for p1,p2 in pairs)
    else:
      dif = sum(abs(c1-c2) for p1,p2 in pairs for c1,c2 in zip(p1,p2))

    ncomponents = i1.size[0] * i1.size[1] * 3
    self.assertLessEqual((dif / 255.0 * 100) / ncomponents, tolerance)

  def assertImagesSame(self, i1, i2):
    """Assert images are exactly same."""
    self.assertImagesSimilar(i1, i2, 0)

  def test_XXX(self):
    import pdb; pdb.set_trace()