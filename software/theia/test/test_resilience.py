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
import unittest
import subprocess
import tempfile
import time
import re
import shutil
from six.moves.urllib.parse import urlparse, urljoin

import pexpect
import psutil
import requests
import sqlite3

from slapos.grid.svcbackend import getSupervisorRPC
from slapos.grid.svcbackend import _getSupervisordSocketPath

import test


class ResilientTheiaTestCase(test.TheiaTestCase):
  @classmethod
  def _getTypePartition(cls, software_type):
    software_url = cls.getSoftwareURL()
    for computer_partition in cls.slap.computer.getComputerPartitionList():
      partition_url = computer_partition.getSoftwareRelease()._software_release
      partition_type = computer_partition.getType()
      if partition_url == software_url and partition_type == software_type:
        return computer_partition
    raise "Theia %s partition not found" % software_type

  @classmethod
  def _getTypePartitionId(cls, software_type):
    return cls._getTypePartition(software_type).getId()

  @classmethod
  def _getTypePartitionPath(cls, software_type, *paths):
    return os.path.join(cls.slap._instance_root, cls._getTypePartitionId(software_type), *paths)

  @classmethod
  def _getSlapos(cls, software_type='export'):
    return cls._getTypePartitionPath(software_type, 'srv', 'runner', 'bin', 'slapos')

  @classmethod
  def _deployEmbeddedSoftware(cls, software_url, instance_name):
    slapos = cls._getSlapos()
    subprocess.check_call((slapos, 'supply', software_url, 'slaprunner'))
    subprocess.check_call((slapos, 'node', 'software'))
    subprocess.check_call((slapos, 'request', instance_name, software_url))
    subprocess.check_call((slapos, 'node', 'instance'))

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'resilient'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'autorun': 'stopped'}

  @classmethod
  def setUpClass(cls):
    super(ResilientTheiaTestCase, cls).setUpClass()
    # Patch the computer root path to that of the export theia instance
    cls.computer_partition_root_path = cls._getTypePartitionPath('export')


class TestTheiaResilientInterface(test.TestTheia, ResilientTheiaTestCase):
  pass

class TestTheiaResilientWithSR(test.TestTheiaWithSR, ResilientTheiaTestCase):
  pass


class TestTheiaExportImport(ResilientTheiaTestCase):
  def _getTestSoftwareUrl(self):
    try:
      return self._test_software_url
    except AttributeError:
      # Copy ./resilience_dummy SR in export theia ~/srv/project/dummy
      dummy_target_path = self._getTypePartitionPath('export', 'srv', 'project', 'dummy')
      shutil.copytree('resilience_dummy', dummy_target_path)
      self._test_software_url = os.path.join(dummy_target_path, 'software.cfg')
      return self._test_software_url

  def _getAdaptedTestSoftwareUrl(self):
    return self._getTypePartitionPath('import', 'srv', 'project', 'dummy', 'software.cfg')

  def test_export_import(self):
    # Deploy dummy instance in export partition
    test_software_url = self._getTestSoftwareUrl()
    self._deployEmbeddedSoftware(test_software_url, 'dummy_instance')

    # Check that dummy instance was properly deployed
    log_path = self._getTypePartitionPath('export', 'srv', 'runner', 'instance', 'slappart0', 'log.log')
    with open(log_path) as f:
      initial_log = f.readlines()
    self.assertEqual(len(initial_log), 1)
    self.assertTrue(initial_log[0].startswith("Hello"), initial_log[0])

    # Call export script manually
    theia_export_script = self._getTypePartitionPath('export', 'bin', 'theia-export-script')
    subprocess.check_call((theia_export_script,))

    # Copy <export>/srv/backup/theia to <import>/srv/backup/theia manually
    export_backup_path = self._getTypePartitionPath('export', 'srv', 'backup', 'theia')
    import_backup_path = self._getTypePartitionPath('import', 'srv', 'backup', 'theia')
    shutil.rmtree(import_backup_path)
    shutil.copytree(export_backup_path, import_backup_path)

    # Call the import script manually
    theia_import_script = self._getTypePartitionPath('import', 'bin', 'theia-import-script')
    subprocess.check_call((theia_import_script,))

    # Check that the software url is correct
    test_adapted_url = self._getAdaptedTestSoftwareUrl()
    proxy_content = subprocess.check_output((self._getSlapos('import'), 'proxy', 'show'))
    self.assertIn(test_adapted_url, proxy_content)
    if test_adapted_url != test_software_url:
      self.assertNotIn(test_software_url, proxy_content)

    # Check that the dummy instance is not yet started
    log_path = self._getTypePartitionPath('import', 'srv', 'runner', 'instance', 'slappart0', 'log.log')
    with open(log_path) as f:
      copied_log = f.readlines()
    self.assertEqual(copied_log, initial_log)

    # Start the dummy instance
    subprocess.check_call((self._getSlapos('import'), 'node', 'instance'))

    # Check that dummy instance was properly re-deployed
    with open(log_path) as f:
      new_log = f.readlines()
    self.assertEqual(len(new_log), 2)
    self.assertEqual(new_log[0], initial_log[0])
    self.assertTrue(new_log[1].startswith("Hello"), new_log[1])


class TestTheiaExportImportWebURL(TestTheiaExportImport):
  def _getTestSoftwareUrl(self):
    return "https://lab.nexedi.com/xavier_thompson/slapos/raw/a0f0ac90/software/theia/test/dummy/software.cfg"

  _getAdaptedTestSoftwareUrl = _getTestSoftwareUrl
