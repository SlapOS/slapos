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
import paramiko
import contextlib
import base64
import hashlib
import subprocess
from six.moves.urllib.parse import urlparse
from six.moves.urllib.parse import quote
from six.moves.configparser import ConfigParser

from slapos.recipe.librecipe import generateHashFromFiles
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class SlaprunnerTestCase(SlapOSInstanceTestCase):
  # Slaprunner uses unix sockets, so it needs short paths.
  __partition_reference__ = 's'


class TestSSH(SlaprunnerTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    cls.ssh_key = paramiko.RSAKey.generate(1024)
    return {
        'user-authorized-key': 'ssh-rsa {}'.format(cls.ssh_key.get_base64())
    }

  def test_connect(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    ssh_url = parameter_dict['ssh-url']
    parsed = urlparse(ssh_url)
    self.assertEqual('ssh', parsed.scheme)

    # username contain a fingerprint (only, so we simplify the parsing)
    #
    # relevant parts of the grammar defined in
    # https://tools.ietf.org/id/draft-salowey-secsh-uri-00.html
    #
    #   ssh-info      =  [ userinfo ] [";" c-param *("," c-param)]
    #   c-param       =  paramname "=" paramvalue
    ssh_info = parsed.username
    username, fingerprint_from_url = ssh_info.split(';fingerprint=')
    client = paramiko.SSHClient()

    self.assertTrue(fingerprint_from_url.startswith('ssh-rsa-'), '')
    fingerprint_from_url = fingerprint_from_url[len('ssh-rsa-'):]

    class KeyPolicy(object):
      """Accept server key and keep it in self.key for inspection
      """
      def missing_host_key(self, client, hostname, key):
        self.key = key

    key_policy = KeyPolicy()
    client.set_missing_host_key_policy(key_policy)

    with contextlib.closing(client):
      client.connect(
          username=username,
          hostname=parsed.hostname,
          port=parsed.port,
          pkey=self.ssh_key,
      )
      # Check fingerprint from server matches the published one.
      # Paramiko does not allow to get the fingerprint as SHA256 easily yet
      # https://github.com/paramiko/paramiko/pull/1103
      self.assertEqual(
          fingerprint_from_url,
          quote(
              # base64 encoded fingerprint adds an extra = at the end
              base64.b64encode(
                  hashlib.sha256(key_policy.key.asbytes()).digest())[:-1],
              # also encode /
              safe=''))

      # Check shell is usable
      channel = client.invoke_shell()
      channel.settimeout(30)
      received = ''
      while True:
        r = channel.recv(1024)
        self.logger.debug("received >%s<", r)
        if not r:
          break
        received += r
        if 'slaprunner shell' in received:
          break
      self.assertIn("Welcome to SlapOS slaprunner shell", received)

      # simple commands can also be executed ( this would be like `ssh bash -c 'pwd'` )
      self.assertEqual(
          self.computer_partition_root_path,
          client.exec_command("pwd")[1].read(1000).strip())


class TestSlapOS(SlaprunnerTestCase):
  def test_slapos_command(self):
    # in ~/bin/slapos there is a wrapper setting configuration to use slapos from
    # the web runner.
    proxy_show_output = subprocess.check_output(
        (
            os.path.join(self.computer_partition_root_path, 'bin', 'slapos'),
            'proxy',
            'show',
        ),
        env={})
    self.assertIn('slaprunner', proxy_show_output)

  def test_shared_part_list(self):
    # this slapos used shared_part_list
    cfg_parser = ConfigParser()
    with open(os.path.join(self.computer_partition_root_path,
                           'etc',
                           'slapos.cfg')) as f:
      cfg_parser.readfp(f)
    shared_part_list = cfg_parser.get('slapos', 'shared_part_list').splitlines()

    # web runner own shared parts. Note that there is intentionnaly a double
    # slash in this path, because slaprunner has double slash in paths since
    # early releases, including for the path of slapos repository that will be
    # used to develop and install software. If we fix this duplication, then
    # the URL of installed software will be different and it will get a different
    # hash and be reinstalled. To prevent this, we keep that // between srv and runner.
    self.assertEqual(
        '{}/srv//runner//shared'.format(self.computer_partition_root_path.rstrip('/')),
        shared_part_list[-1])

    # shared parts from outer slapos
    outer_shared_part_list = os.getenv('SLAPOS_TEST_SHARED_PART_LIST',
                                       '').split(os.pathsep)
    for outer_shared_part in outer_shared_part_list:
      self.assertIn(outer_shared_part, shared_part_list)


class ServicesTestCase(SlaprunnerTestCase):
  def test_hashes(self):
    hash_files = [
      'software_release/buildout.cfg',
    ]
    expected_process_names = [
      'slaprunner-supervisord-{hash}-on-watch',
      'runner-sshkeys-authority-{hash}-on-watch',
      'runner-sshd-{hash}-on-watch',
      'slaprunner-httpd-{hash}-on-watch',
      'gunicorn-{hash}-on-watch',
      'nginx-frontend-{hash}-on-watch',
      'certificate_authority-{hash}-on-watch',
      'shellinaboxd-{hash}-on-watch',
      'supervisord-{hash}-on-watch',
    ]

    with self.slap.instance_supervisor_rpc as supervisor:
      process_names = [
          process['name'] for process in supervisor.getAllProcessInfo()
      ]

    hash_files = [os.path.join(self.computer_partition_root_path, path)
                  for path in hash_files]

    for name in expected_process_names:
      h = generateHashFromFiles(hash_files)
      expected_process_name = name.format(hash=h)

      self.assertIn(expected_process_name, process_names)
