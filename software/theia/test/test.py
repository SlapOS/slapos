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
import difflib
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


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TheiaTestCase(SlapOSInstanceTestCase):
    # Theia uses unix sockets, so it needs short paths.
  __partition_reference__ = 'T'

  instance_max_retry = 1

  @classmethod
  def _getSlapos(cls):
    partition_root = cls.computer_partition_root_path
    slapos = os.path.join(partition_root, 'srv', 'runner', 'bin', 'slapos')
    return slapos


class TestTheia(TheiaTestCase):
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
  sr_url = 'bogus/software.cfg'
  sr_type = 'bogus_type'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'embedded-sr': cls.sr_url,
      'embedded-sr-type': cls.sr_type,
    }

  def test(self):
    slapos = self._getSlapos()
    info = subprocess.check_output((slapos, 'proxy', 'show'))
    instance_name = "Embedded Instance"

    self.assertIsNotNone(re.search(r"%s\s+slaprunner\s+available" % (self.sr_url,), info), info)
    self.assertIsNotNone(re.search(r"%s\s+%s\s+%s" % (self.sr_url, self.sr_type, instance_name), info), info)


class TestTheiaEnv(TheiaTestCase):
  def test_theia_env(self):
    script = os.path.join(self.computer_partition_root_path, 'print_env.sh')
    shell_env = os.path.join(self.computer_partition_root_path, 'shell_env.log')
    supervisord_env = os.path.join(self.computer_partition_root_path, 'supervisord_env.log')
    supervisord_conf = os.path.join(self.computer_partition_root_path, 'srv', 'runner', 'etc', 'supervisord.conf')

    # Write a script to print the information we want to inspect
    with open(script, 'w') as f:
      f.write(
        textwrap.dedent(
          """
          function printpath() {
            echo "$1: $(readlink -f $(which $1) 2> /dev/null)"
          }
          printpath slapos
          printpath gcc
          echo "HOME: $HOME"
          echo "SLAPOS_CONFIGURATION: $SLAPOS_CONFIGURATION"
          echo "SLAPOS_CLIENT_CONFIGURATION: $SLAPOS_CLIENT_CONFIGURATION"
          echo "PATH:"
          echo $PATH | tr ':' '\n'
          """
        )
      )

    # Append a program to the supervisord configuration to call the script from supervisord
    with open(supervisord_conf, 'a') as f:
      f.write(
        textwrap.dedent(
          """
          [program:supervisord-env]
          command = bash %s
          autostart = true
          autorestart = false
          startretries = 0
          startsecs = 0
          redirect_stderr = true
          stdout_logfile = %s
          stdout_logfile_maxbytes = 5MB
          stdout_logfile_backups = 0
          """
        ) % (script, supervisord_env)
      )

    # Get the environment of the running theia process
    theia_project = os.path.join(self.computer_partition_root_path, 'srv', 'project')
    ps_x = subprocess.Popen(('ps', 'x'), stdout=subprocess.PIPE)
    grep_yarn = subprocess.Popen(('grep', 'yarn'), stdin=ps_x.stdout, stdout=subprocess.PIPE)
    grep_output = subprocess.check_output(('grep', theia_project), stdin=grep_yarn.stdout)
    pid = int(grep_output.strip().split(' ')[0])
    theia_env = psutil.Process(pid).environ()

    # Start a theia shell process within the environment of the running theia process
    # This should give us a shell with an environment be very close to that of the browser shell
    process = pexpect.spawnu('{}/bin/theia-shell'.format(self.computer_partition_root_path), env=theia_env)

    # Get the environment when called from the shell
    process.sendline("bash %s > %s" % (script, shell_env))

    # Reload supervisord, this will start the new program and get the environment from supervisord
    process.sendline("supervisorctl -c %s reload" % supervisord_conf)

    # Wait for supervisord to reload and the program to run
    time.sleep(10)

    process.terminate()
    process.wait()

    # Compare the collected data
    with open(os.path.join(shell_env), 'r') as f:
      shell_env_log = f.readlines()

    with open(os.path.join(supervisord_env), 'r') as f:
      supervisord_env_log = f.readlines()

    if shell_env_log != supervisord_env_log:
      diff = difflib.ndiff(shell_env_log, supervisord_env_log)
      self.fail(
        textwrap.dedent(
          """
          The theia shell and supervisord have different environments

          shell:
          %s

          supervisord:
          %s

          diff:
          %s
          """
        ) % (''.join(shell_env_log), ''.join(supervisord_env_log), ''.join(diff))
      )
