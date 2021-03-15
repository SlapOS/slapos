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
  instance_max_retry = 20

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
  def getInstanceSoftwareType(cls):
    return 'resilient'

  @classmethod
  def setUpClass(cls):
    super(ResilientTheiaTestCase, cls).setUpClass()
    # Patch the computer root path to that of the export theia instance
    cls.computer_partition_root_path = cls._getTypePartitionPath('export')


class TheiaResiliencyTestCase(ResilientTheiaTestCase):
  def _getTakeoverUrlAndPassword(self, scope="theia-1"):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    takeover_url = parameter_dict["takeover-%s-url" % scope]
    takeover_password = parameter_dict["takeover-%s-password" % scope]
    return takeover_url, takeover_password

  def _getTakeoverState(self, takeover_url):
    def getTakeoverPageContent():
      resp = requests.get(takeover_url, verify=True)
      self.assertEqual(requests.codes.ok, resp.status_code)
      return resp.text

    takeover_page_content = getTakeoverPageContent()
    if "<b>Last valid backup:</b> No backup downloaded yet, takeover should not happen now." in takeover_page_content:
      return "nothing"
    elif "<b>Importer script(s) of backup in progress:</b> True" in takeover_page_content:
      return "ongoing"
    return "ready"

  def _doTakeover(self, takeover_url, takeover_password):
    resp = requests.get(
      "%s?password=%s" % (takeover_url, takeover_password),
      verify=True
    )
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertNotIn("Error", resp.text, "An Error occured: %s" % resp.text)
    self.assertIn("Success", resp.text, "'Success' not in '%s'" % resp.text)
    return resp.text


class TestTheiaResilientInterface(test.TestTheia, ResilientTheiaTestCase):
  pass


class TestTheiaResilientWithSR(test.TestTheiaWithSR, ResilientTheiaTestCase):
  pass


class TestTheiaExportImport(TheiaResiliencyTestCase):
  def test_export_import(self):
    # Copy ./dummy SR in export theia ~/srv/project/dummy
    dummy_target_path = self._getTypePartitionPath('export', 'srv' 'project', 'dummy')
    shutil.copytree('dummy', dummy_target_path)
    dummy_software_url = os.path.join(dummy_target_path, 'software.cfg')

    # Deploy dummy instance
    slapos = self._getSlapos()
    subprocess.check_output((slapos, 'supply', dummy_software_url, 'slaprunner'))
    subprocess.check_output((slapos, 'node', 'software'))
    subprocess.check_output((slapos, 'request', 'dummy_instance', dummy_software_url))
    subprocess.check_output((slapos, 'node', 'instance'))

    # Check that dummy instance was properly deployed
    log_path = self._getTypePartitionPath('export', 'srv', 'runner', 'instance', 'slappart0', 'log.log')
    with open(log_path) as f:
      content = f.read()
    self.assertTrue(content.startswith("Hello"), content)

    # Call export script manually
    theia_export_script = self._getTypePartitionPath('export', 'bin', 'theia-export-script')
    subprocess.check_output((theia_export_script, ))

    # Copy <export>/srv/backup/theia to <import>/srv/backup/theia manually
    export_backup_path = self._getTypePartitionPath('export', 'srv', 'backup', 'theia')
    import_backup_path = self._getTypePartitionPath('import', 'srv', 'backup', 'theia')
    shutil.rmtree(import_backup_path)
    shutil.copytree(export_backup_path, import_backup_path)

    # Call the import script manually
    theia_import_script = self._getTypePartitionPath('import', 'bin', 'theia-import-script')
    subprocess.check_output((theia_import_script, ))

    # Check that dummy instance was properly re-deployed
    log_path = self._getTypePartitionPath('import', 'srv', 'runner', 'instance', 'slappart0', 'log.log')
    with open(log_path) as f:
      content = f.read()
    self.assertTrue(content.startswith("Hello"), content)


class TestTheiaBasicResilience(TheiaResiliencyTestCase):
  def test_basic_dummy_resilience(self):
    export_partition_id = self._getTypePartitionId('export')
    import_partition_id = self._getTypePartitionId('import')

    # Copy ./dummy SR in export theia ~/srv/project/dummy
    dummy_target_path = self._getTypePartitionPath('export', 'srv', 'project', 'dummy')
    shutil.copytree('dummy', dummy_target_path)

    dummy_software_url = os.path.join(dummy_target_path, 'software.cfg')

    # Deploy dummy instance
    slapos = self._getSlapos()
    subprocess.check_output((slapos, 'supply', dummy_software_url, 'slaprunner'))
    subprocess.check_output((slapos, 'node', 'software'))
    subprocess.check_output((slapos, 'request', 'dummy_instance', dummy_software_url))
    subprocess.check_output((slapos, 'node', 'instance'))

    # Check that dummy instance was properly deployed
    dummy_log_path = self._getTypePartitionPath('export', 'srv', 'runner', 'instance', 'slappart0', 'log.log')
    with open(dummy_log_path) as f:
      content = f.read()
    self.assertTrue(content.startswith("Hello"), content)

    # Call exporter script instead of waiting for cron job
    # XXX Accelerate cron frequency instead ?
    exporter_script = self._getTypePartitionPath('export', 'bin', 'exporter')
    transaction_id = str(int(time.time()))
    subprocess.check_output((exporter_script, '--transaction-id', transaction_id))

    # Get equeue.log file in import instance
    import_partition_root = getPartitionPathWhere(self, self.getSoftwareURL(), 'import')
    importer_log = os.path.join(import_partition_root, 'var', 'log', 'equeue.log')

    def getFileContent(file_path):
      with open(file_path) as f:
        return f.read()

    # Wait for importer to start
    # XXX remove this
    time.sleep(60)
    takeover_url, takeover_password = self._getTakeoverUrlAndPassword()

    for _ in range(100):
      takeover_state = self._getTakeoverState(takeover_url)
      if takeover_state == "ready":
        break
      elif takeover_state == "nothing":
          importer_log_content = getFileContent(importer_log)
          self.fail("Backup is not even started: %s" % importer_log_content)
      else:
        self.logger.info("Backup is ongoing, waiting some more")
      time.sleep(20)
    else:
      importer_log_content = getFileContent(importer_log)
      self.fail("Timeout before backup is finished, see importer log:\n%s" % importer_log_content)

    # Takeover
    self._doTakeover(takeover_url, takeover_password)

    # Wait for import instance to become export instance and new import to be allocated
    self.slap.waitForInstance(1)

    previous_computer_partition = self.computer_partition
    self.computer_partition = self.requestDefaultInstance()

    # Check that the import instance became the export instance
    new_export_partition_id = self._getTypePartitionId('export')
    self.assertNotEqual(export_partition_id, import_partition_id)
    self.assertEqual(import_partition_id, new_export_partition_id)

    # Check that there is a new import instance
    new_import_partition_id = self._getTypePartitionId('import')
    self.assertNotEqual(export_partition_id, new_import_partition_id)
    self.assertNotEqual(new_export_partition_id, new_import_partition_id)

    # Check that the data was transfered over
    with open(self._getLocalPath(relative_dummy_log_path), 'r') as f:
      content_after = f.read()

    self.assertTrue(content.startswith("Hello"), content)
    self.assertTrue(content_after.startswith("Hello"), content_after)
    self.assertIn(content, content_after, "%s not in %s" % (content, content_after))
