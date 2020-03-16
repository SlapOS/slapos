##############################################################################
#
# Copyright (c) 2018 Nexedi SA and Contributors. All Rights Reserved.
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
import json
import glob
import urlparse
import socket
import time

import psutil
import requests

from . import ERP5InstanceTestCase
from . import setUpModule
setUpModule  # pyflakes


class MariaDBTestCase(ERP5InstanceTestCase):
  """Base test case for mariadb tests.
  """
  __partition_reference__ = 'm'

  @classmethod
  def getInstanceSoftwareType(cls):
    return "mariadb"

  @classmethod
  def _getInstanceParameterDict(cls):
    return {
        'tcpv4-port': 3306,
        'max-slowqueries-threshold': 5,
        'slowest-query-threshold': 10,
        'max-connection-count': 5,
        'computer-memory-percent-threshold': 100, # XXX should not be needed here
        'name': 'name ?', # XXX what is this ? should not be needed here
    }

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(cls._getInstanceParameterDict())}


class TestMroonga(MariaDBTestCase):
  instance_max_retry = 2
  def test_mroonga(self):
    import pdb
    pdb.set_trace()
    pass

  def test_groonga_normalizer(self):
    pass
