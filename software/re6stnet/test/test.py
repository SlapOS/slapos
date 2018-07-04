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
import shutil
import urlparse
import tempfile
import requests
import socket
import StringIO
import subprocess
import json

import psutil

import utils

LOCAL_IPV4 = os.environ['LOCAL_IPV4']
GLOBAL_IPV6 = os.environ['GLOBAL_IPV6']


# for development: debugging logs and install Ctrl+C handler
if os.environ.get('DEBUG'):
  import logging
  logging.basicConfig(level=logging.DEBUG)
  import unittest
  unittest.installHandler()


class Re6stnetTestCase(utils.SlapOSInstanceTestCase):
  def setUp(self):
    import logging

    utils.SlapOSInstanceTestCase.setUp(self)
    self.logger = logging.getLogger(__name__)

  @classmethod
  def getSoftwareURLList(cls):
    return (os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'software.cfg')), )

class TestRe6stnetRegistry(Re6stnetTestCase):

  def test_listen(self):
    connection_parameters = self.computer_partition.getConnectionParameterDict()
    registry_url = connection_parameters['re6stry-local-url']

    _ = requests.get(registry_url)

class TestPortRedirection(Re6stnetTestCase):

  def test_portredir_config(self):
    portredir_config_path = os.path.join(self.computer_partition_root_path, '.slapos-port-redirect')
    with open(portredir_config_path) as f:
      portredir_config = json.load(f)

    self.assertDictContainsSubset({
      'srcPort': 9201,
      'destPort': 9201,
    }, portredir_config[0])
