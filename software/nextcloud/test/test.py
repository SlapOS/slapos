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
import glob
import re

import psutil

import utils

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

  def getNextcloudConfig(self, config_dict={}):
    self.maxDiff = None
    data_dict = dict(
      datadirectory=self.partition_dir + "/srv/data",
      dbhost="%s:2099" % self.config['ipv4_address'],
      dbname="nextcloud", 
      dbpassword="insecure", 
      dbport="",
      dbuser="nextcloud",
      mail_domain="nextcloud@example.com",
      mail_from_address="Nextcloud",
      mail_smtpauth=1,
      mail_smtpauthtype="LOGIN",
      mail_smtphost="",
      mail_smtpport="587",
      mail_smtppassword="",
      mail_smtpname="",
      cli_url="https://[%s]:9988/" % self.config['ipv6_address'],
      partition_dir=self.partition_dir,
      trusted_domain_list=json.dumps(["[%s]:9988" % self.config['ipv6_address']]),
      trusted_proxy_list=[],
    )
    data_dict.update(config_dict)

    template = """{
  "activity_expire_days": 14, 
  "auth.bruteforce.protection.enabled": true, 
  "blacklisted_files": [
    ".htaccess", 
    "Thumbs.db", 
    "thumbs.db"
  ], 
  "cron_log": true, 
  "csrf.optout": [
	  "/^WebDAVFS/",
	  "/^Microsoft-WebDAV-MiniRedir/",
	  "/^\\\\.jio_documents/"
	],
  "datadirectory": "%(datadirectory)s", 
  "dbhost": "%(dbhost)s", 
  "dbname": "%(dbname)s", 
  "dbpassword": "%(dbpassword)s", 
  "dbport": "", 
  "dbtableprefix": "oc_", 
  "dbtype": "mysql", 
  "dbuser": "%(dbuser)s", 
  "enable_previews": true, 
  "enabledPreviewProviders": [
	  "OC\\\\Preview\\\\PNG",
	  "OC\\\\Preview\\\\JPEG",
	  "OC\\\\Preview\\\\GIF",
	  "OC\\\\Preview\\\\BMP",
	  "OC\\\\Preview\\\\XBitmap",
	  "OC\\\\Preview\\\\Movie",
	  "OC\\\\Preview\\\\PDF",
	  "OC\\\\Preview\\\\MP3",
	  "OC\\\\Preview\\\\TXT",
	  "OC\\\\Preview\\\\MarkDown"
	],
  "filelocking.enabled": "true", 
  "filesystem_check_changes": 0, 
  "forwarded_for_headers": [
    "HTTP_X_FORWARDED"
  ], 
  "htaccess.RewriteBase": "/", 
  "installed": true, 
  "integrity.check.disabled": false, 
  "knowledgebaseenabled": false, 
  "log_rotate_size": 104857600, 
  "logfile": "%(datadirectory)s/nextcloud.log", 
  "loglevel": 2, 
  "mail_domain": "%(mail_domain)s", 
  "mail_from_address": "%(mail_from_address)s", 
  "mail_sendmailmode": "smtp", 
  "mail_smtpauth": %(mail_smtpauth)s, 
  "mail_smtpauthtype": "%(mail_smtpauthtype)s", 
  "mail_smtphost": "%(mail_smtphost)s", 
  "mail_smtpmode": "smtp", 
  "mail_smtpname": "%(mail_smtpname)s", 
  "mail_smtppassword": "%(mail_smtppassword)s", 
  "mail_smtpport": "%(mail_smtpport)s", 
  "mail_smtpsecure": "tls", 
  "maintenance": false, 
  "memcache.locking": "\\\\OC\\\\Memcache\\\\Redis",
  "memcache.local": "\\\\OC\\\\Memcache\\\\APCu",
  "memcache.distributed": "\\\\OC\\\\Memcache\\\\Redis",
  "mysql.utf8mb4": true, 
  "overwrite.cli.url": "%(cli_url)s", 
  "overwriteprotocol": "https", 
  "preview_max_scale_factor": 1, 
  "preview_max_x": 1024, 
  "preview_max_y": 768, 
  "quota_include_external_storage": false, 
  "redis": {
    "host": "%(partition_dir)s/srv/redis/redis.socket", 
    "port": 0, 
    "timeout": 0
  }, 
  "share_folder": "/Shares", 
  "skeletondirectory": "", 
  "theme": "", 
  "trashbin_retention_obligation": "auto, 7", 
  "trusted_domains": %(trusted_domain_list)s, 
  "trusted_proxies": %(trusted_proxy_list)s, 
  "updater.release.channel": "stable"
}"""

    return json.loads(template % data_dict)


class ServicesTestCase(InstanceTestCase):

  @staticmethod
  def generateHash(file_list):
    import hashlib
    hasher = hashlib.md5()
    for path in file_list:
      with open(path, 'r') as afile:
        buf = afile.read()
      hasher.update("%s\n" % len(buf))
      hasher.update(buf)
    hash = hasher.hexdigest()
    return hash

  def test_process_list(self):
    hash_list = [
      'software_release/buildout.cfg',
    ]
    expected_process_names = [
      'bootstrap-monitor',
      'mariadb',
      'mariadb_update',
      'apache-php-{hash}-on-watch',
      'certificate_authority-{hash}-on-watch',
      'crond-{hash}-on-watch',
      'monitor-httpd-{hash}-on-watch',
      'monitor-httpd-graceful',
      'nextcloud-install',
      'nextcloud-news-updater',
      'redis-on-watch',
    ]

    supervisor = self.getSupervisorRPCServer().supervisor
    process_name_list = [process['name']
                     for process in supervisor.getAllProcessInfo()]

    hash_file_list = [os.path.join(self.computer_partition_root_path, path)
                      for path in hash_list]

    for name in expected_process_names:
      h = ServicesTestCase.generateHash(hash_file_list)
      expected_process_name = name.format(hash=h)

      self.assertIn(expected_process_name, process_name_list)

  def test_nextcloud_installation(self):
    partition_path_list = glob.glob(os.path.join(self.instance_path, '*'))
    nextcloud_path = None
    for partition_path in partition_path_list:
      path = os.path.join(partition_path, 'srv/www')
      if os.path.exists(path):
        nextcloud_path = path
        instance_folder = partition_path
        break
    can_install_path = os.path.join(nextcloud_path, 'config/CAN_INSTALL')

    self.assertTrue(os.path.exists(nextcloud_path))
    self.assertFalse(os.path.exists(can_install_path))
    self.assertTrue(os.path.exists(os.path.join(nextcloud_path, 'config/config.php')))

    php_bin = os.path.join(instance_folder, 'bin/php')
    nextcloud_status = subprocess.check_output([
      php_bin,
      os.path.join(nextcloud_path, 'occ'),
      'status',
      '--output',
      'json'])
    json_status = json.loads(nextcloud_status)
    self.assertTrue(json_status['installed'], True)

  def test_nextcloud_config(self):
    partition_path_list = glob.glob(os.path.join(self.instance_path, '*'))
    nextcloud_path = None
    for partition_path in partition_path_list:
      path = os.path.join(partition_path, 'srv/www')
      if os.path.exists(path):
        nextcloud_path = path
        instance_folder = partition_path
        break
    config_file = os.path.join(nextcloud_path, 'config/config.php')
    php_script = os.path.join(instance_folder, 'test.php')
    with open(php_script, 'w') as f:
      f.write("<?php include('%s'); echo json_encode($CONFIG); ?>" % config_file)

    self.partition_dir = instance_folder
    php_bin = os.path.join(instance_folder, 'bin/php')
    occ = os.path.join(nextcloud_path, 'occ')
    config_result =  subprocess.check_output([
      php_bin,
      '-f',
      php_script
    ])
    config_dict = json.loads(config_result)
    #remove generated values
    config_dict.pop('instanceid')
    config_dict.pop('passwordsalt')
    config_dict.pop('secret')
    config_dict.pop('version')
    expected_dict = self.getNextcloudConfig()
    self.assertEqual(config_dict, expected_dict)
    collabora_config = subprocess.check_output([
      php_bin,
      occ,
      "config:app:get",
      "richdocuments",
      "wopi_url"
    ])
    self.assertEqual(collabora_config.strip(), 'https://collabora.host.vifib.net/')
    stun_config = subprocess.check_output([
      php_bin,
      occ,
      "config:app:get",
      "spreed",
      "stun_servers"
    ])
    self.assertEqual(stun_config.strip(), '["turn.vifib.com:5349"]')
    turn_config = subprocess.check_output([
      php_bin,
      occ,
      "config:app:get",
      "spreed",
      "turn_servers"
    ])
    self.assertEqual(turn_config.strip(), '[{"server":"","secret":"","protocols":"udp,tcp"}]')
    news_config_file = os.path.join(instance_folder, 'srv/data/news/config/config.ini')
    with open(news_config_file) as f:
      config = f.read()
      regex = r"(useCronUpdates\s+=\s+false)"
      result = re.search(regex, config)
      self.assertNotEqual(result, None)


  def test_nextcloud_promises(self):
    partition_path_list = glob.glob(os.path.join(self.instance_path, '*'))
    nextcloud_path = None
    for partition_path in partition_path_list:
      path = os.path.join(partition_path, 'srv/www')
      if os.path.exists(path):
        nextcloud_path = path
        instance_folder = partition_path
        break

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
                      "apache-httpd-port-listening.py",           
                      "buildout-%s-status.py" % partition_name,
                      "monitor-bootstrap-status.py",
                      "monitor-httpd-listening-on-tcp.py"
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


class TestConfigWithParameters(InstanceTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'instance.mail-from': "Nextcloud-Test",
      'instance.mail-domain': "test@example.com",
      'instance.mail-smtpauthtype': "LOGIN",
      'instance.mail-smtpauth': 1,
      'instance.mail-smtpport': 4588,
      'instance.mail-smtphost': '127.0.0.1',
      'instance.mail-smtpname': 'mail.example.net',
      'instance.mail-smtppassword': 'dwsofjsd',
      'instance.collabora-url': 'https://my-custom.collabora.net',
      'instance.stun-server': 'stun.example.net:5439',
      'instance.turn-server': 'turn.example.net:5439',
      'instance.turn-secret': 'c4f0ead40a49bbbac3c58f7b9b43990f78ebd96900757ae67e10190a3a6b6053',
      'instance.cli-url': 'nextcloud.example.com',
      'instance.trusted-domain-1': 'nextcloud.example.com',
      'instance.trusted-domain-2': 'nextcloud.proxy.com',
      'instance.trusted-proxy-list': '2001:67c:1254:e:89::5df3 127.0.0.1 10.23.1.3',
    }

  def test_nextcloud_config_with_parameters(self):
    partition_path_list = glob.glob(os.path.join(self.instance_path, '*'))
    nextcloud_path = None
    for partition_path in partition_path_list:
      path = os.path.join(partition_path, 'srv/www')
      if os.path.exists(path):
        nextcloud_path = path
        instance_folder = partition_path
        break
    config_file = os.path.join(nextcloud_path, 'config/config.php')
    php_script = os.path.join(instance_folder, 'test.php')
    with open(php_script, 'w') as f:
      f.write("<?php include('%s'); echo json_encode($CONFIG); ?>" % config_file)

    self.partition_dir = instance_folder
    php_bin = os.path.join(instance_folder, 'bin/php')
    occ = os.path.join(nextcloud_path, 'occ')
    config_result =  subprocess.check_output([
      php_bin,
      '-f',
      php_script
    ])
    # XXX - debug logs
    with open(config_file) as f:
      log_string = f.read()
      log_string += "\n\n\n=========NEXTCLOUD LOGS=============\n\n\n"
    with open(os.path.join(instance_folder, 'srv/data/nextcloud.log')) as f:
      log_string += f.read()
      log_string += "\n\n\n=========APACHE ERROR LOGS=============\n\n\n"
    with open(os.path.join(instance_folder, 'var/log/apache/error.log')) as f:
      log_string += f.read()
    raise ValueError(log_string)
    config_dict = json.loads(config_result)
    #remove generated values
    config_dict.pop('instanceid')
    config_dict.pop('passwordsalt')
    config_dict.pop('secret')
    config_dict.pop('version')
    instance_parameter_dict = dict(
      mail_domain="test@example.com",
      mail_from_address="Nextcloud-Test",
      mail_smtpauth=1,
      mail_smtpauthtype="LOGIN",
      mail_smtphost="127.0.0.1",
      mail_smtpport="4588",
      mail_smtppassword="dwsofjsd",
      mail_smtpname="mail.example.net",
      cli_url="nextcloud.example.com",
      partition_dir=self.partition_dir,
      trusted_domain_list=json.dumps([
        "[%s]:9988" % self.config['ipv6_address'],
        "nextcloud.example.com",
        "nextcloud.proxy.com"
      ]),
      trusted_proxy_list=json.dumps([
        "2001:67c:1254:e:89::5df3",
        "127.0.0.1",
        "10.23.1.3"
      ])
    )
    expected_dict = self.getNextcloudConfig(instance_parameter_dict)
    self.assertEqual(config_dict, expected_dict)
    collabora_config = subprocess.check_output([
      php_bin,
      occ,
      "config:app:get",
      "richdocuments",
      "wopi_url"
    ])
    self.assertEqual(collabora_config.strip(), 'https://my-custom.collabora.net')
    stun_config = subprocess.check_output([
      php_bin,
      occ,
      "config:app:get",
      "spreed",
      "stun_servers"
    ])
    self.assertEqual(stun_config.strip(), '["stun.example.net:5439"]')
    turn_config = subprocess.check_output([
      php_bin,
      occ,
      "config:app:get",
      "spreed",
      "turn_servers"
    ])
    self.assertEqual(turn_config.strip(),
                     '[{"server":"turn.example.net:5439","secret":"c4f0ead40a49bbbac3c58f7b9b43990f78ebd96900757ae67e10190a3a6b6053","protocols":"udp,tcp"}]')
