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
import subprocess
import tempfile
import time
import re
from six.moves.urllib.parse import urlparse, urljoin

import pexpect
import psutil
import requests
import sqlite3

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.grid.svcbackend import getSupervisorRPC
from slapos.grid.svcbackend import _getSupervisordSocketPath


# Base classes
# ------------

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TheiaTestCase(SlapOSInstanceTestCase):
    # Theia uses unix sockets, so it needs short paths.
  __partition_reference__ = 'T'


# Utils
# -----

class SQLiteDB(object):
  def __init__(self, sqlitedb_file):
    self.sqlitedb_file = sqlitedb_file

  def select(self, fields, table, where={}):
    connection = sqlite3.connect(self.sqlitedb_file)

    def dict_factory(cursor, row):
      d = {}
      for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
      return d
    connection.row_factory = dict_factory
    cursor = connection.cursor()

    condition = " AND ".join("%s='%s'" % (k, v) for k, v in where.items())
    cursor.execute(
      "SELECT %s FROM %s%s"
      % (
        ", ".join(fields),
        table,
        " WHERE %s" % condition if where else "",
      )
    )
    return cursor.fetchall()


# Tests
# -----

class TestTheiaInterface(TheiaTestCase):
  def setUp(self):
    self.connection_parameters = self.computer_partition.getConnectionParameterDict()

  def test_http_get(self):
    resp = requests.get(self.connection_parameters['url'], verify=False)
    self.assertEqual(requests.codes.unauthorized, resp.status_code)

    # with login/password, this is allowed
    parsed_url = urlparse(self.connection_parameters['url'])
    authenticated_url = parsed_url._replace(
        netloc='{}:{}@[{}]:{}'.format(
            self.connection_parameters['username'],
            self.connection_parameters['password'],
            parsed_url.hostname,
            parsed_url.port,
        )).geturl()
    resp = requests.get(authenticated_url, verify=False)
    self.assertEqual(requests.codes.ok, resp.status_code)

    # there's a public folder to serve file
    with open('{}/srv/frontend-static/public/test_file'.format(
        self.computer_partition_root_path), 'w') as f:
      f.write("hello")
    resp = requests.get(urljoin(authenticated_url, '/public/'), verify=False)
    self.assertIn('test_file', resp.text)
    resp = requests.get(
        urljoin(authenticated_url, '/public/test_file'), verify=False)
    self.assertEqual('hello', resp.text)

    # there's a (not empty) favicon
    resp = requests.get(
        urljoin(authenticated_url, '/favicon.ico'), verify=False)
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertTrue(resp.raw)

    # there is a CSS referencing fonts
    css_text = requests.get(urljoin(authenticated_url, '/css/slapos.css'), verify=False).text
    css_urls = re.findall(r'url\([\'"]+([^\)]+)[\'"]+\)', css_text)
    self.assertTrue(css_urls)
    # and fonts are served
    for url in css_urls:
      resp = requests.get(urljoin(authenticated_url, url), verify=False)
      self.assertEqual(requests.codes.ok, resp.status_code)
      self.assertTrue(resp.raw)

  def test_theia_slapos(self):
    # Make sure we can use the shell and the integrated slapos command
    process = pexpect.spawnu(
        '{}/bin/theia-shell'.format(self.computer_partition_root_path),
        env={'HOME': self.computer_partition_root_path})

    # use a large enough terminal so that slapos proxy show table fit in the screen
    process.setwinsize(5000, 5000)

    # log process output for debugging
    logger = logging.getLogger('theia-shell')
    class DebugLogFile:
      def write(self, msg):
        logger.info("output from theia-shell: %s", msg)
      def flush(self):
        pass
    process.logfile = DebugLogFile()

    process.expect_exact('Standalone SlapOS for computer `slaprunner` activated')

    # try to supply and install a software to check that this slapos is usable
    process.sendline(
        'slapos supply https://lab.nexedi.com/nexedi/slapos/raw/1.0.144/software/helloworld/software.cfg slaprunner'
    )
    process.expect(
        'Requesting software installation of https://lab.nexedi.com/nexedi/slapos/raw/1.0.144/software/helloworld/software.cfg...'
    )

    # we pipe through cat to disable pager and prevent warnings like
    # WARNING: terminal is not fully functional
    process.sendline('slapos proxy show | cat')
    process.expect(
        'https://lab.nexedi.com/nexedi/slapos/raw/1.0.144/software/helloworld/software.cfg'
    )

    process.sendline('slapos node software')
    process.expect(
        'Installing software release https://lab.nexedi.com/nexedi/slapos/raw/1.0.144/software/helloworld/software.cfg'
    )
    # interrupt this, we don't want to actually wait for software installation
    process.sendcontrol('c')

    process.terminate()
    process.wait()

  def test_theia_shell_execute_tasks(self):
    # shell needs to understand -c "command" arguments for theia tasks feature
    test_file = '{}/test file'.format(self.computer_partition_root_path)
    subprocess.check_call([
        '{}/bin/theia-shell'.format(self.computer_partition_root_path),
        '-c',
        'touch "{}"'.format(test_file)
    ])
    self.assertTrue(os.path.exists(test_file))


class TestTheiaEmbeddedSlapOSShutdown(TheiaTestCase):
  def test_stopping_instance_stops_embedded_slapos(self):
    embedded_slapos_supervisord_socket = _getSupervisordSocketPath(
        os.path.join(
            self.computer_partition_root_path,
            'srv',
            'runner',
            'instance',
        ), self.logger)

    # Wait a bit for this supervisor to be started.
    for _ in range(20):
      if os.path.exists(embedded_slapos_supervisord_socket):
        break
      time.sleep(1)

    # get the pid of the supervisor used to manage instances
    with getSupervisorRPC(embedded_slapos_supervisord_socket) as embedded_slapos_supervisor:
      embedded_slapos_process = psutil.Process(embedded_slapos_supervisor.getPID())

    # Stop theia's services
    with self.slap.instance_supervisor_rpc as instance_supervisor:
      process_info, = [
          p for p in instance_supervisor.getAllProcessInfo()
          if p['name'].startswith('slapos-standalone-instance-')
      ]
      instance_supervisor.stopProcessGroup(process_info['group'])

    # the supervisor controlling instances is also stopped
    self.assertFalse(embedded_slapos_process.is_running())


class TestTheiaWithSR(TheiaTestCase):
  srurl = 'bogus/software.cfg'
  srtype = 'bogus'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'embedded-sr': cls.srurl,
      'embedded-sr-type': cls.srtype,
    }

  def test(self):
    db = SQLiteDB(os.path.join(self.computer_partition_root_path, 'srv', 'runner', 'var', 'proxy.db'))
    supplied = db.select(
      fields=["*"],
      table = "software14",
      where={'url': self.srurl}
    )
    self.assertEqual(len(supplied), 1)
    requested = db.select(
      fields=["*"],
      table = "partition14",
      where={'software_release': self.srurl, 'software_type': self.srtype}
    )
    self.assertEqual(len(requested), 1)


class TestTheiaResilientInterface(TestTheiaInterface):
  instance_max_retry = 30

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'resilient'

  @classmethod
  def setUpClass(cls):
    super(TestTheiaResilientInterface, cls).setUpClass()
    # Patch the computer root path to that of the export theia instance
    cls.computer_partition_root_path = os.path.join(cls.slap._instance_root, "T2")


class TestTheiaResilientWithSR(TestTheiaWithSR):
  instance_max_retry = 30

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'resilient'

  @classmethod
  def setUpClass(cls):
    super(TestTheiaResilientWithSR, cls).setUpClass()
    # Patch the computer root path to that of the export theia instance
    cls.computer_partition_root_path = os.path.join(cls.slap._instance_root, "T2")
