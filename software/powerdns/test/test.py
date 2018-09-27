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

# for development: debugging logs and install Ctrl+C handler
if os.environ.get('DEBUG'):
  import logging
  logging.basicConfig(level=logging.DEBUG)
  import unittest
  unittest.installHandler()


class InstanceTestCase(utils.SlapOSInstanceTestCase):
  @classmethod
  def getSoftwareURLList(cls):
    return (os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'software.cfg')), )


class ServicesTestCase(InstanceTestCase):
  @staticmethod
  def generateHashFromFiles(file_list):
    import hashlib
    hasher = hashlib.md5()
    for path in file_list:
      with open(path, 'r') as afile:
        buf = afile.read()
      hasher.update("%s\n" % len(buf))
      hasher.update(buf)
    hash = hasher.hexdigest()
    return hash

  def test_hashes(self):
    hash_files = [
      'software_release/buildout.cfg',
    ]
    service_names = [
      'pdns',
    ]

    supervisor = self.getSupervisorRPCServer().supervisor
    process_names = [process['name']
                     for process in supervisor.getAllProcessInfo()]

    hash_files = ['{}/{}'.format(self.computer_partition_root_path, path)
                  for path in hash_files]

    for service_name in service_names:
      h = ServicesTestCase.generateHashFromFiles(hash_files)
      expected_process_name = '{}-{}-on-watch'.format(service_name, h)

      self.assertIn(expected_process_name, process_names)
