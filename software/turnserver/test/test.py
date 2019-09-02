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
import ConfigParser

import utils
from slapos.recipe.librecipe import generateHashFromFiles

# for development: debugging logs and install Ctrl+C handler
if os.environ.get('SLAPOS_TEST_DEBUG'):
  import logging
  logging.basicConfig(level=logging.DEBUG)
  import unittest
  unittest.installHandler()

def subprocess_status_output(*args, **kwargs):
  prc = subprocess.Popen(
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    *args,
    **kwargs)
  out, err = prc.communicate()
  return prc.returncode, out

class InstanceTestCase(utils.SlapOSInstanceTestCase):
  @classmethod
  def getSoftwareURLList(cls):
    return (os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'software.cfg')), )



class ServicesTestCase(InstanceTestCase):

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

    supervisor = self.getSupervisorRPCServer().supervisor
    process_name_list = [process['name']
                     for process in supervisor.getAllProcessInfo()]

    hash_file_list = [os.path.join(self.computer_partition_root_path, path)
                      for path in hash_list]

    for name in expected_process_names:
      h = generateHashFromFiles(hash_file_list)
      expected_process_name = name.format(hash=h)

      self.assertIn(expected_process_name, process_name_list)

  def test_default_deployment(self):
    partition_path_list = glob.glob(os.path.join(self.instance_path, '*'))
    instance_folder = None
    for partition_path in partition_path_list:
      if os.path.exists(os.path.join(partition_path, 'etc/turnserver.conf')):
        instance_folder = partition_path
        break

    secret_file = os.path.join(instance_folder, 'etc/.turnsecret')
    self.assertTrue(os.path.exists(instance_folder))
    self.assertTrue(os.path.exists(secret_file))
    config = ConfigParser.ConfigParser()
    config.readfp(open(secret_file))
    secret = config.get('turnserver', 'secret')

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
log-file=%(instance_path)s/var/log/turnserver.log
userdb=%(instance_path)s/srv/turndb
pidfile=%(instance_path)s/var/run/turnserver.pid
verbose""" % {'instance_path': instance_folder, 'secret': secret, 'ipv4': self.config['ipv4_address']}

    with open(os.path.join(instance_folder, 'etc/turnserver.conf')) as f:
      current_config = f.read().strip()

    self.assertEqual(current_config, expected_config)

  def test_turnserver_promises(self):
    partition_path_list = glob.glob(os.path.join(self.instance_path, '*'))
    instance_folder = None
    for partition_path in partition_path_list:
      if os.path.exists(os.path.join(partition_path, 'etc/turnserver.conf')):
        instance_folder = partition_path
        break
    self.assertTrue(os.path.exists(instance_folder))

    promise_path_list = glob.glob(os.path.join(instance_folder, 'etc/plugin/*.py'))
    promise_name_list = [x for x in
                         os.listdir(os.path.join(instance_folder, 'etc/plugin'))
                         if not x.endswith('.pyc')]
    partition_name = os.path.basename(instance_folder.rstrip('/'))
    self.assertEqual(sorted(promise_name_list),
                    sorted([
                      "__init__.py",
                      "check-free-disk-space.py",
                      "monitor-http-frontend.py",
                      "buildout-%s-status.py" % partition_name,
                      "monitor-bootstrap-status.py",
                      "monitor-httpd-listening-on-tcp.py",
                      "turnserver-port-listening.py",
                      "turnserver-tls-port-listening.py",
                    ]))

    ignored_plugin_list = [
      '__init__.py',
      'monitor-http-frontend.py',
    ]
    runpromise_bin = os.path.join(
      self.software_path, 'bin', 'monitor.runpromise')
    monitor_conf = os.path.join(instance_folder, 'etc', 'monitor.conf')
    msg = []
    status = 0
    for plugin_path in promise_path_list:
      plugin_name = os.path.basename(plugin_path)
      if plugin_name in ignored_plugin_list:
        continue
      plugin_status, plugin_result = subprocess_status_output([
        runpromise_bin,
        '-c', monitor_conf,
        '--run-only', plugin_name,
        '--force',
        '--check-anomaly'
      ])
      status += plugin_status
      if plugin_status == 1:
        msg.append(plugin_result)
      # sanity check
      if 'Checking promise %s' % plugin_name not in plugin_result:
        plugin_status = 1
        msg.append(plugin_result)
    msg = ''.join(msg).strip()
    self.assertEqual(status, 0, msg)

class ParametersTestCase(InstanceTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'server-name': "turn.site.com",
      'port': 3488,
      'tls-port': 5369,
      'external-ip': '127.0.0.1',
      'listening-ip': '127.0.0.1'
    }

  def test_turnserver_with_parameters(self):
    partition_path_list = glob.glob(os.path.join(self.instance_path, '*'))
    instance_folder = None
    for partition_path in partition_path_list:
      if os.path.exists(os.path.join(partition_path, 'etc/turnserver.conf')):
        instance_folder = partition_path
        break

    secret_file = os.path.join(instance_folder, 'etc/.turnsecret')
    self.assertTrue(os.path.exists(instance_folder))
    self.assertTrue(os.path.exists(secret_file))
    config = ConfigParser.ConfigParser()
    config.readfp(open(secret_file))
    secret = config.get('turnserver', 'secret')

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
log-file=%(instance_path)s/var/log/turnserver.log
userdb=%(instance_path)s/srv/turndb
pidfile=%(instance_path)s/var/run/turnserver.pid
verbose""" % {'instance_path': instance_folder,
              'secret': secret,
              'ipv4': '127.0.0.1',
              'name': 'turn.site.com',
              'external_ip': '127.0.0.1',
              'port': 3488,
              'tls_port': 5369,}

    with open(os.path.join(instance_folder, 'etc/turnserver.conf')) as f:
      current_config = f.read().strip()

    self.assertEqual(current_config, expected_config)


