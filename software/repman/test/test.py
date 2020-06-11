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
from __future__ import unicode_literals

import os
import textwrap
import logging
import tempfile
import time
from six.moves.urllib.parse import urlparse, urljoin

import pexpect
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestRepman(SlapOSInstanceTestCase):
  __partition_reference__ = 'R'  # solve path too long for postgresql and unicorn

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'default'

  def setUp(self):
    self.backend_url = self.computer_partition.getConnectionParameterDict(
    )['backend-url']

  def test_http_get(self):
    resp = requests.get(self.backend_url, verify=False)
    self.assertTrue(
      resp.status_code in [requests.codes.ok, requests.codes.found])
