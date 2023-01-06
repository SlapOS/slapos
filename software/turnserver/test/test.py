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
import subprocess
import json
import glob
import configparser

from slapos.recipe.librecipe import generateHashFromFiles
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TurnServerTestCase(InstanceTestCase):

  partition_path = None

  def setUp(self):
    # Lookup the partition in which turnserver was installed.
    partition_path_list = glob.glob(os.path.join(
      self.slap.instance_directory, '*'))
    for partition_path in partition_path_list:
      if os.path.exists(os.path.join(partition_path, 'etc/turnserver.conf')):
        self.partition_path = partition_path
        break

    self.assertTrue(
        self.partition_path,
        "Turnserver path not found in %r" % (partition_path_list,))


class TestServices(TurnServerTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'listening-ip': cls._ipv4_address
    }

  def test_process_list(self):
    hash_list = [
      'software_release/buildout.cfg',
    ]
    expected_process_names = [
      'bootstrap-monitor',
      'turnserver-{hash}-on-watch',
      'certificate_authority-{hash}-on-watch',
      'crond-{hash}-on-watch',
      'monitor-httpd-{hash}-on-watch',
      'monitor-httpd-graceful',
    ]

    with self.slap.instance_supervisor_rpc as supervisor:
      process_name_list = [process['name']
                     for process in supervisor.getAllProcessInfo()]

    hash_file_list = [os.path.join(self.computer_partition_root_path, path)
                      for path in hash_list]

    for name in expected_process_names:
      h = generateHashFromFiles(hash_file_list)
      expected_process_name = name.format(hash=h)

      self.assertIn(expected_process_name, process_name_list)

  def test_default_deployment(self):
    secret_file = os.path.join(self.partition_path, 'etc/.turnsecret')
    self.assertTrue(os.path.exists(self.partition_path))
    self.assertTrue(os.path.exists(secret_file))
    config = configparser.ConfigParser()
    with open(secret_file) as f:
      config.readfp(f)
    secret = config.get('turnserver', 'secret')
    self.assertTrue(secret)

    expected_config = """listening-port=3478
tls-listening-port=5349
fingerprint
lt-cred-mech
use-auth-secret
static-auth-secret=%(secret)s
listening-ip=%(ipv4)s
server-name=turn.example.com
realm=turn.example.com
total-quota=100
bps-capacity=0
stale-nonce=600
cert=%(instance_path)s/etc/ssl/cert.pem
pkey=%(instance_path)s/etc/ssl/key.pem
dh-file=%(instance_path)s/etc/ssl/dhparam.pem
cipher-list="ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+3DES:DH+3DES:RSA+AES:RSA+3DES:!ADH:!AECDH:!MD5"
no-loopback-peers
no-multicast-peers
mobility
no-tlsv1
no-tlsv1_1
no-stdout-log
simple-log
log-file=%(instance_path)s/var/log/turnserver.log
userdb=%(instance_path)s/srv/turndb
pidfile=%(instance_path)s/var/run/turnserver.pid
verbose""" % {'instance_path': self.partition_path, 'secret': secret, 'ipv4': self._ipv4_address}

    with open(os.path.join(self.partition_path, 'etc/turnserver.conf')) as f:
      current_config = f.read().strip()

    self.assertEqual(current_config.splitlines(), expected_config.splitlines())


class TestParameters(TurnServerTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'server-name': "turn.site.com",
      'port': 3488,
      'tls-port': 5369,
      'external-ip': '127.0.0.1',
      'listening-ip': cls._ipv4_address
    }

  def test_turnserver_with_parameters(self):
    secret_file = os.path.join(self.partition_path, 'etc/.turnsecret')
    self.assertTrue(os.path.exists(self.partition_path))
    self.assertTrue(os.path.exists(secret_file))
    config = configparser.ConfigParser()
    with open(secret_file) as f:
      config.readfp(f)
    secret = config.get('turnserver', 'secret')
    self.assertTrue(secret)

    expected_config = """listening-port=%(port)s
tls-listening-port=%(tls_port)s
fingerprint
lt-cred-mech
use-auth-secret
static-auth-secret=%(secret)s
listening-ip=%(ipv4)s
external-ip=%(external_ip)s
server-name=%(name)s
realm=%(name)s
total-quota=100
bps-capacity=0
stale-nonce=600
cert=%(instance_path)s/etc/ssl/cert.pem
pkey=%(instance_path)s/etc/ssl/key.pem
dh-file=%(instance_path)s/etc/ssl/dhparam.pem
cipher-list="ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+3DES:DH+3DES:RSA+AES:RSA+3DES:!ADH:!AECDH:!MD5"
no-loopback-peers
no-multicast-peers
mobility
no-tlsv1
no-tlsv1_1
no-stdout-log
simple-log
log-file=%(instance_path)s/var/log/turnserver.log
userdb=%(instance_path)s/srv/turndb
pidfile=%(instance_path)s/var/run/turnserver.pid
verbose""" % {'instance_path': self.partition_path,
              'secret': secret,
              'ipv4': self._ipv4_address,
              'name': 'turn.site.com',
              'external_ip': '127.0.0.1',
              'port': 3488,
              'tls_port': 5369,}

    with open(os.path.join(self.partition_path, 'etc/turnserver.conf')) as f:
      current_config = f.read().strip()

    self.assertEqual(current_config.splitlines(), expected_config.splitlines())

class TestInsecureServices(TurnServerTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'listening-ip': cls._ipv4_address
    }

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'insecure'

  def test_process_list(self):
    hash_list = [
      'software_release/buildout.cfg',
    ]
    expected_process_names = [
      'bootstrap-monitor',
      'turnserver-{hash}-on-watch',
      'certificate_authority-{hash}-on-watch',
      'crond-{hash}-on-watch',
      'monitor-httpd-{hash}-on-watch',
      'monitor-httpd-graceful',
    ]

    with self.slap.instance_supervisor_rpc as supervisor:
      process_name_list = [process['name']
                     for process in supervisor.getAllProcessInfo()]

    hash_file_list = [os.path.join(self.computer_partition_root_path, path)
                      for path in hash_list]

    for name in expected_process_names:
      h = generateHashFromFiles(hash_file_list)
      expected_process_name = name.format(hash=h)

      self.assertIn(expected_process_name, process_name_list)

  def test_default_deployment(self):
    self.assertTrue(os.path.exists(self.partition_path))
    connection_parameter_dict = self.computer_partition\
      .getConnectionParameterDict()
    password = connection_parameter_dict['password']


    expected_config = """listening-port=3478
lt-cred-mech
realm=turn.example.com
fingerprint
listening-ip=%(ipv4)s
server-name=turn.example.com
no-stdout-log
simple-log
log-file=%(instance_path)s/var/log/turnserver.log
pidfile=%(instance_path)s/var/run/turnserver.pid
verbose
user=nxdturn:%(password)s""" % {'instance_path': self.partition_path, 'password': password, 'ipv4': self._ipv4_address}

    with open(os.path.join(self.partition_path, 'etc/turnserver.conf')) as f:
      current_config = f.read().strip()

    self.assertEqual(current_config.splitlines(), expected_config.splitlines())

