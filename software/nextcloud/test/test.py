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
import re

from six.moves.urllib.parse import urlparse

from slapos.recipe.librecipe import generateHashFromFiles
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class NextCloudTestCase(InstanceTestCase):

  # calculated in setUp
  partition_dir = None
  nextcloud_path = None

  def setUp(self):
    # we want full diff when assertions fail
    self.maxDiff = None

    # lookup the partition in which nextcloud was installed
    partition_path_list = glob.glob(os.path.join(
        self.slap.instance_directory, '*'))
    for partition_path in partition_path_list:
      path = os.path.join(partition_path, 'srv/www')
      if os.path.exists(path):
        self.nextcloud_path = path
        self.partition_dir = partition_path
        break
    self.assertTrue(
        self.nextcloud_path,
        "Nextcloud path not found in %r" % (partition_path_list,))

    # lookup nextcloud partition ipv6
    partition_id = os.path.basename(self.partition_dir)
    self.nextcloud_ipv6 = self.getPartitionIPv6(partition_id)

    # parse database info from mariadb url
    d = self.computer_partition.getConnectionParameterDict()
    db_url = d['mariadb-url-list'][2:-2] # parse <url> out of "['<url>']"
    self._db_info = urlparse(db_url)

  def getNextcloudConfig(self, config_dict={}):
    data_dict = dict(
      datadirectory=self.partition_dir + "/srv/data",
      dbhost="%s:2099" % self._ipv4_address,
      dbname="nextcloud",
      dbpassword=self._db_info.password,
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
      cli_url="https://[%s]:9988/" % self.nextcloud_ipv6,
      partition_dir=self.partition_dir,
      trusted_domain_list=json.dumps(["[%s]:9988" % self.nextcloud_ipv6]),
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


class TestServices(NextCloudTestCase):
  __partition_reference__ = 'ncs'

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

    with self.slap.instance_supervisor_rpc as supervisor:
      process_name_list = [process['name']
                     for process in supervisor.getAllProcessInfo()]

    hash_file_list = [os.path.join(self.computer_partition_root_path, path)
                      for path in hash_list]

    for name in expected_process_names:
      h = generateHashFromFiles(hash_file_list)
      expected_process_name = name.format(hash=h)

      self.assertIn(expected_process_name, process_name_list)

  def test_nextcloud_installation(self):
    can_install_path = os.path.join(self.nextcloud_path, 'config/CAN_INSTALL')

    self.assertTrue(os.path.exists(self.nextcloud_path))
    self.assertFalse(os.path.exists(can_install_path))
    self.assertTrue(os.path.exists(os.path.join(self.nextcloud_path, 'config/config.php')))

    php_bin = os.path.join(self.partition_dir, 'bin/php')
    nextcloud_status = subprocess.check_output([
      php_bin,
      os.path.join(self.nextcloud_path, 'occ'),
      'status',
      '--output',
      'json'])
    json_status = json.loads(nextcloud_status)
    self.assertTrue(json_status['installed'], True)

  def test_nextcloud_config(self):
    config_file = os.path.join(self.nextcloud_path, 'config/config.php')
    php_script = os.path.join(self.partition_dir, 'test.php')
    with open(php_script, 'w') as f:
      f.write("<?php include('%s'); echo json_encode($CONFIG); ?>" % config_file)

    php_bin = os.path.join(self.partition_dir, 'bin/php')
    occ = os.path.join(self.nextcloud_path, 'occ')
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
    self.assertEqual(collabora_config.strip(), b'https://collabora.host.vifib.net/')
    stun_config = subprocess.check_output([
      php_bin,
      occ,
      "config:app:get",
      "spreed",
      "stun_servers"
    ])
    self.assertEqual(stun_config.strip(), b'["turn.vifib.com:5349"]')
    turn_config = subprocess.check_output([
      php_bin,
      occ,
      "config:app:get",
      "spreed",
      "turn_servers"
    ])
    self.assertEqual(turn_config.strip(), b'[{"server":"","secret":"","protocols":"udp,tcp"}]')
    news_config_file = os.path.join(self.partition_dir, 'srv/data/news/config/config.ini')
    with open(news_config_file) as f:
      config = f.read()
    self.assertRegex(config, r"(useCronUpdates\s+=\s+false)")


class TestNextCloudParameters(NextCloudTestCase):
  __partition_reference__ = 'ncp'

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
    config_file = os.path.join(self.nextcloud_path, 'config/config.php')
    php_script = os.path.join(self.partition_dir, 'test.php')
    with open(php_script, 'w') as f:
      f.write("<?php include('%s'); echo json_encode($CONFIG); ?>" % config_file)

    php_bin = os.path.join(self.partition_dir, 'bin/php')
    occ = os.path.join(self.nextcloud_path, 'occ')
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
        "[%s]:9988" % self.nextcloud_ipv6,
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
    self.assertEqual(collabora_config.strip(), b'https://my-custom.collabora.net')
    stun_config = subprocess.check_output([
      php_bin,
      occ,
      "config:app:get",
      "spreed",
      "stun_servers"
    ])
    self.assertEqual(stun_config.strip(), b'["stun.example.net:5439"]')
    turn_config = subprocess.check_output([
      php_bin,
      occ,
      "config:app:get",
      "spreed",
      "turn_servers"
    ])
    self.assertEqual(
        turn_config.strip(),
        b'[{"server":"turn.example.net:5439","secret":"c4f0ead40a49bbbac3c58f7b9b43990f78ebd96900757ae67e10190a3a6b6053","protocols":"udp,tcp"}]')
