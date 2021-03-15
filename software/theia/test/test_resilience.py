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


def getPartitionIdWhere(cls, software_url, software_type):
  for computer_partition in cls.slap.computer.getComputerPartitionList():
    _software = computer_partition.getSoftwareRelease()._software_release
    _type = computer_partition.getType()
    if _software == software_url and _type == software_type:
      return computer_partition.getId()
  return None

def getPartitionPathWhere(cls, software_url, software_type):
  Id = getPartitionIdWhere(cls, software_url, software_type)
  if Id:
    return os.path.join(cls.slap._instance_root, Id)
  return None


class ResilientTheiaTestCase(test.TheiaTestCase):
  instance_max_retry = 20

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'resilient'

  @classmethod
  def setUpClass(cls):
    super(ResilientTheiaTestCase, cls).setUpClass()
    # Patch the computer root path to that of the export theia instance
    path = getPartitionPathWhere(cls, cls.getSoftwareURL(), 'export')
    cls.computer_partition_root_path = path


class TheiaResiliencyTestCase(ResilientTheiaTestCase):
  @classmethod
  def _getLocalPath(cls, relative_path):
    partition_root = getPartitionPathWhere(cls, cls.getSoftwareURL(), 'export')
    absolute_path = os.path.join(partition_root, relative_path)
    return absolute_path

  @classmethod
  def _doSlaposCommand(cls, command):
    partition_root = getPartitionPathWhere(cls, cls.getSoftwareURL(), 'export')
    slapos_bin = os.path.join(partition_root, 'srv', 'runner', 'bin', 'slapos')
    output = subprocess.check_output((slapos_bin, ) + command)
    return output

  def _supplySoftwareRelease(self, software_url):
    self._doSlaposCommand(('supply', software_url, 'slaprunner'))

  def _waitForSoftwareBuild(self):
    self._doSlaposCommand(('node', 'software'))

  def _requestInstance(self, instance_name, software_url):
    self._doSlaposCommand(('request', instance_name, software_url))

  def _waitForInstanceDeploy(self):
    self._doSlaposCommand(('node', 'instance'))

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


class TestTheiaBasicResilience(TheiaResiliencyTestCase):
  def test_basic_dummy_resilience(self):
    export_partition_id = getPartitionIdWhere(self, self.getSoftwareURL(), 'export')
    import_partition_id = getPartitionIdWhere(self, self.getSoftwareURL(), 'import')

    # Copy ./dummy SR in export theia ~/srv/project/dummy
    dummy_target_path = self._getLocalPath('srv/project/dummy')
    shutil.copytree('dummy', dummy_target_path)

    dummy_software_url = os.path.join(dummy_target_path, 'software.cfg')

    # Deploy dummy instance
    self._supplySoftwareRelease(dummy_software_url)
    self._waitForSoftwareBuild()
    self._requestInstance("dummy_instance", dummy_software_url)
    self._waitForInstanceDeploy()

    # Check that dummy instance was properly deployed
    relative_dummy_log_path = 'srv/runner/instance/slappart0/log.log'
    with open(self._getLocalPath(relative_dummy_log_path), 'r') as f:
      content = f.read()
    self.assertTrue(content.startswith("Hello"), content)

    # Call exporter script instead of waiting for cron job
    # XXX Accelerate cron frequency instead ?
    exporter_script = self._getLocalPath('bin/exporter')
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
    new_export_partition_id = getPartitionIdWhere(self, self.getSoftwareURL(), 'export')
    self.assertNotEqual(export_partition_id, import_partition_id)
    self.assertEqual(import_partition_id, new_export_partition_id)

    # Check that there is a new import instance
    new_import_partition_id = getPartitionIdWhere(self, self.getSoftwareURL(), 'import')
    self.assertNotEqual(export_partition_id, new_import_partition_id)
    self.assertNotEqual(new_export_partition_id, new_import_partition_id)

    # Check that the data was transfered over
    with open(self._getLocalPath(relative_dummy_log_path), 'r') as f:
      content_after = f.read()

    self.assertTrue(content.startswith("Hello"), content)
    self.assertTrue(content_after.startswith("Hello"), content_after)
    self.assertIn(content, content_after, "%s not in %s" % (content, content_after))
