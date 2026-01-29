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

import http.client as httplib
import http.server
import json
import os
import glob
import gzip
import hashlib
import psutil
import re
import requests
import slapos.util
import sqlite3
from urllib.parse import parse_qs, urlparse
import unittest
import subprocess
import tempfile
import socketserver as SocketServer
import multiprocessing
import time
import shutil
import sys

from slapos.proxy.db_version import DB_VERSION
from slapos.recipe.librecipe import generateHashFromFiles
from slapos.test.monitoring_mixin import MonitoringPropagationTestMixin
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.slap.standalone import SlapOSNodeCommandError
from slapos.testing.utils import findFreeTCPPort

# To be in sync with component/vm-img/debian.cfg
DEFAULT_IMAGE_ISONAME = 'debian-13.3.0-amd64-netinst.iso'
DEFAULT_IMAGE_TITLE = 'Debian Trixie 13 netinst x86_64'
DEFAULT_IMAGE_MD5SUM = '10484b2d8e2780801dc7d354ba4ff238'
##

has_kvm = os.access('/dev/kvm', os.R_OK | os.W_OK)
skipUnlessKvm = unittest.skipUnless(has_kvm, 'kvm not loaded or not allowed')

if has_kvm:
  setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.join(
      os.path.dirname(__file__), 'test-software.cfg'), software_id='kvm')
else:
  setUpModule, InstanceTestCase = None, unittest.TestCase

  class SanityCheckTestCase(unittest.TestCase):
    def test_kvm_sanity_check(self):
      self.fail('This environment is not usable for kvm testing,'
                ' as it lacks kvm_intel kernel module')

bootstrap_common_param_dict = {
    # the bootstrap script is vm-bootstrap
    "bootstrap-script-url":
    "http://shacache.org/shacache/05105cd25d1ad798b71fd46a206c9b73da2c285a078"
    "af33d0e739525a595886785725a68811578bc21f75d0a97700a66d5e75bce5b2721ca455"
    "6a0734cb13e65#c98825aa1b6c8087914d2bfcafec3058",
    "authorized-keys": [
        "ssh-rsa %s key_one" % ("A" * 372),
        "ssh-rsa %s key_two" % ("B" * 372),
        "ssh-rsa %s key_three" % ("C" * 372)
    ]
}

bootstrap_machine_param_dict = {
    "disable-ansible-promise": True,
    "auto-ballooning": True,
    "ram-size": 4096,
    "cpu-count": 2,
    "disk-size": 50,
    "virtual-hard-drive-url":
    "http://shacache.org/shacache/a869d906fcd0af5091d5104451a2b86736485ae38e5"
    "c4388657bb957c25593b98378ed125f593683e7fda7e0dd485a376a0ce29dcbaa8d60766"
    "e1f67a7ef7b96",
    "virtual-hard-drive-md5sum": "9ffd690a5fcb4fa56702f2b99183e493",
    "virtual-hard-drive-gzipped": True,
    "use-tap": True,
    "use-nat": True,
    "nat-restrict-mode": True,
    "enable-vhost": True
}


class KVMTestCase(InstanceTestCase):
  @classmethod
  def findQemuTools(cls):
    with open(os.path.join(
        cls.slap.software_directory,
        hashlib.md5(cls.getSoftwareURL().encode()).hexdigest(),
        '.installed.cfg'
      )) as fh:
      location_cfg = fh.read()
    qemu_location = [
      q for q in location_cfg.splitlines()
      if q.startswith('location') and '/qemu/' in q]
    assert (len(qemu_location) == 1)
    qemu_location = qemu_location[0].split('=')[1].strip()
    cls.qemu_img = os.path.join(qemu_location, 'bin', 'qemu-img')
    assert (os.path.exists(cls.qemu_img))

  def getRunningImageList(
      self,
      _match_cdrom=re.compile('file=(.+),media=cdrom$').match,
      _sub_iso=re.compile(r'(/debian)(-[^-/]+)(-[^/]+-netinst\.iso)$').sub,
    ):
    kvm_instance_partition = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference)
    kvm_pid_file_list = glob.glob(os.path.join(
      self.slap._instance_root, '*', 'var', 'run', 'kvm.pid'))
    self.assertEqual(1, len(kvm_pid_file_list))
    with open(kvm_pid_file_list[0]) as fh:
      kvm_pid = int(fh.read().strip())
    sub_shared = re.compile(r'^%s/[^/]+/[0-9a-f]{32}/'
                            % re.escape(self.slap.shared_directory)).sub
    image_list = []
    for entry in psutil.Process(kvm_pid).cmdline():
      m = _match_cdrom(entry)
      if m:
        path = m.group(1)
        image_list.append(
          _sub_iso(
            r'\1-${ver}\3',
            sub_shared(
              r'${shared}/',
              path.replace(kvm_instance_partition, '${inst}')
            )))
    return image_list

  @classmethod
  def _findTopLevelPartitionPath(cls, path: str):
    index = 0
    while True:
      index = path.find(os.path.sep, index) + len(os.path.sep)
      top_path = path[:index]
      if os.path.exists(os.path.join(top_path, '.slapos-resource')):
        return top_path
      if index == -1:
        return None

  @classmethod
  def _updateSlaposResource(cls, partition_path, **kw):
    with open(os.path.join(partition_path, '.slapos-resource'), 'r+') as f:
      resource = json.load(f)
      resource.update(kw)
      f.seek(0)
      f.truncate()
      json.dump(resource, f, indent=2)

  @classmethod
  def formatPartitions(cls):
    super().formatPartitions()

    # steal tap from top level partition
    instance_directory = cls.slap.instance_directory
    top_partition_path = cls._findTopLevelPartitionPath(instance_directory)

    with open(os.path.join(top_partition_path, '.slapos-resource')) as f:
      top_resource = json.load(f)

    for partition in os.listdir(instance_directory):
      if not partition.startswith(cls.__partition_reference__):
        continue

      partition_path = os.path.join(instance_directory, partition)
      cls._updateSlaposResource(partition_path, tap=top_resource['tap'])


class KvmMixin:
  def assertPromiseFailsInDir(self, partition_directory, promise):
    monitor_run_promise = os.path.join(
      partition_directory, 'software_release', 'bin',
      'monitor.runpromise'
    )
    monitor_configuration = os.path.join(
      partition_directory, 'etc', 'monitor.conf')

    try:
      output = subprocess.check_output(
        [monitor_run_promise, '-c', monitor_configuration, '-a', '-f',
         '--run-only', promise],
        stderr=subprocess.STDOUT).decode('utf-8')
      self.fail('Promise did not failed with output %s' % (output,))
    except subprocess.CalledProcessError as e:
      return e.output.decode('utf-8')

  def assertPromiseFails(self, promise):
    partition_directory = os.path.join(
      self.slap.instance_directory,
      self.kvm_instance_partition_reference)
    return self.assertPromiseFailsInDir(partition_directory, promise)

  @classmethod
  def getPartitionIdByType(cls, instance_type):
    software_url = cls.getSoftwareURL()
    for computer_partition in cls.slap.computer.getComputerPartitionList():
      try:
        partition_url = computer_partition.\
          getSoftwareRelease()._software_release
        partition_type = computer_partition.getType()
      except (
        slapos.slap.exception.NotFoundError,
        slapos.slap.exception.ResourceNotReady
      ):
        partition_url = 'NA'
        partition_type = 'NA'
      if partition_url == software_url and partition_type == instance_type:
        return computer_partition.getId()
    raise Exception("Partition type %s not found" % instance_type)

  @classmethod
  def getPartitionPath(cls, instance_type='kvm-export', *paths):
    return os.path.join(
      cls.slap._instance_root, cls.getPartitionIdByType(instance_type), *paths)

  @classmethod
  def getKvmExportPartitionBackupPath(cls, *paths):
    return cls.getPartitionPath(
      'kvm-export', 'srv', 'backup', 'kvm', 'virtual1', *paths)

  @classmethod
  def getAuthenticatedUrl(cls, connection_parameter_dict, prefix='',
                          additional=False):
    parsed_url = urlparse(
      connection_parameter_dict['%surl%s' % (
        prefix, '-additional' if additional else '')])
    return parsed_url._replace(
      netloc='{}:{}@[{}]:{}'.format(
        connection_parameter_dict['%susername' % prefix],
        connection_parameter_dict['%spassword' % prefix],
        parsed_url.hostname,
        parsed_url.port,
      )).geturl()

  def getConnectionParameterDictJson(self):
    return json.loads(
      self.computer_partition.getConnectionParameterDict()['_'])

  def getProcessInfo(self, kvm_additional_hash_file_list=None):
    if kvm_additional_hash_file_list is None:
      kvm_additional_hash_file_list = []
    hash_value = generateHashFromFiles([
      os.path.join(self.computer_partition_root_path, hash_file)
      for hash_file in [
        'software_release/buildout.cfg',
      ]
    ])
    kvm_partition = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference)
    hash_file_list = [
       os.path.join(kvm_partition, 'etc', 'kvm_raw.json')
    ] + kvm_additional_hash_file_list + [
      'software_release/buildout.cfg']

    kvm_hash_value = generateHashFromFiles([
      os.path.join(kvm_partition, hash_file)
      for hash_file in hash_file_list
    ])
    with self.slap.instance_supervisor_rpc as supervisor:
      running_process_info = '\n'.join(sorted(
        '%(group)s:%(name)s %(statename)s' % q for q
        in supervisor.getAllProcessInfo()
        if q['name'] != 'watchdog' and q['group'] != 'watchdog'))
    return running_process_info.replace(
      hash_value, '{hash}').replace(kvm_hash_value, '{kvm-hash-value}')

  @classmethod
  def waitForInstanceWithPropagation(cls, first_retry=10, second_retry=10):
    # run slapos node instance twice
    # once to apply newly requested instance...
    try:
      cls.slap.waitForInstance(max_retry=first_retry)
    except SlapOSNodeCommandError:
      pass
    # ...and second time to re-read the parameters from master and propagate
    #    it to the instances
    cls.slap.waitForInstance(max_retry=second_retry)

  @classmethod
  def raising_waitForInstance(cls, max_retry=5):
    with cls.assertRaises(cls, SlapOSNodeCommandError):
      cls.slap.waitForInstance(max_retry=max_retry)

  @classmethod
  def raising_waitForInstanceWithForce(cls, max_retry=5):
    _current = cls.slap._force_slapos_node_instance_all
    try:
      cls.slap._force_slapos_node_instance_all = True
      cls.raising_waitForInstance(max_retry=max_retry)
    finally:
      cls.slap._force_slapos_node_instance_all = _current

  @classmethod
  def waitForInstanceWithForce(cls, max_retry=10):
    _current = cls.slap._force_slapos_node_instance_all
    try:
      cls.slap._force_slapos_node_instance_all = True
      cls.slap.waitForInstance(max_retry=max_retry)
    finally:
      cls.slap._force_slapos_node_instance_all = _current

  def rerequestInstance(self, parameter_dict=None, state='started'):
    if parameter_dict is None:
      parameter_dict = {}
    software_url = self.getSoftwareURL()
    software_type = self.getInstanceSoftwareType()
    return self.slap.request(
        software_release=software_url,
        software_type=software_type,
        partition_reference=self.default_partition_reference,
        partition_parameter_kw={'_': json.dumps(parameter_dict)},
        state=state)


@skipUnlessKvm
class TestInstance(KVMTestCase, KvmMixin):
  __partition_reference__ = 'i'
  kvm_instance_partition_reference = 'i0'

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    present_key_list = []
    assert_key_list = [
     'backend-url', 'url', 'username', 'password', 'monitor-setup-url',
     'ipv6-network-info', 'tap-ipv4', 'tap-ipv6']
    for k in assert_key_list:
      if k in connection_parameter_dict:
        present_key_list.append(k)
        connection_parameter_dict.pop(k)
    self.assertEqual(
      connection_parameter_dict,
      {
        'ipv6': self.computer_partition_ipv6_address,
        'monitor-base-url':
        f'https://[{self.computer_partition_ipv6_address}]:8026',
        'nat-rule-port-tcp-22':
        f'{self.computer_partition_ipv6_address} : 10022',
        'nat-rule-port-tcp-443':
        f'{self.computer_partition_ipv6_address} : 10443',
        'nat-rule-port-tcp-80':
        f'{self.computer_partition_ipv6_address} : 10080',
      }
    )
    self.assertEqual(set(present_key_list), set(assert_key_list))
    self.assertEqual(
      """i0:6tunnel-10022-{hash}-on-watch RUNNING
i0:6tunnel-10080-{hash}-on-watch RUNNING
i0:6tunnel-10443-{hash}-on-watch RUNNING
i0:boot-image-url-list-updater-{hash} EXITED
i0:boot-image-url-select-updater-{hash} EXITED
i0:bootstrap-monitor EXITED
i0:certificate_authority-{hash}-on-watch RUNNING
i0:crond-{hash}-on-watch RUNNING
i0:kvm-{kvm-hash-value}-on-watch RUNNING
i0:monitor-httpd-{hash}-on-watch RUNNING
i0:monitor-httpd-graceful EXITED
i0:nginx-graceful EXITED
i0:nginx-on-watch RUNNING
i0:whitelist-domains-download-{hash} RUNNING
i0:whitelist-firewall-{hash} RUNNING""",
      self.getProcessInfo([
        'var/boot-image-url-list/boot-image-url-list.json',
        'var/boot-image-url-select/boot-image-url-select.json'
      ])
    )

    # assure that the default image is used
    self.assertEqual(
      ['${inst}/srv/boot-image-url-select-repository/' + DEFAULT_IMAGE_MD5SUM],
      self.getRunningImageList()
    )


class MonitorAccessMixin(KvmMixin):
  def sqlite3_connect(self):
    sqlitedb_file = os.path.join(
      os.path.abspath(
        os.path.join(
          self.slap.instance_directory, os.pardir
        )
      ), 'var', 'proxy.db'
    )
    return sqlite3.connect(sqlitedb_file)

  def get_all_instantiated_partition_list(self):
    db = self.sqlite3_connect()
    try:
      db.row_factory = lambda cursor, row: {
        col[0]: row[idx]
        for idx, col in enumerate(cursor.description)
      }
      return db.execute(
        "SELECT reference, xml, connection_xml, partition_reference,"
        " software_release, requested_state, software_type"
        " FROM partition%s"
        " WHERE slap_state='busy'" % DB_VERSION).fetchall()
    finally:
      db.close()

  def test_access_monitor(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    monitor_setup_url = connection_parameter_dict['monitor-setup-url']
    monitor_url_with_auth = 'https' + monitor_setup_url.split('https')[2]

    auth = parse_qs(urlparse(monitor_url_with_auth).path)

    # check that monitor-base-url for all partitions in the tree are accessible
    # with published username and password
    partition_with_monitor_base_url_count = 0
    for partition_information in self.get_all_instantiated_partition_list():
      connection_xml = partition_information.get('connection_xml')
      if not connection_xml:
        continue
      connection_dict = slapos.util.xml2dict(connection_xml)
      if '_' in connection_dict:
        connection_dict = json.loads(connection_dict['_'])
      monitor_base_url = connection_dict.get('monitor-base-url')
      if not monitor_base_url:
        continue
      result = requests.get(
        monitor_base_url, verify=False, auth=(
          auth['username'][0],
          auth['password'][0])
      )

      self.assertEqual(
        httplib.OK,
        result.status_code
      )
      partition_with_monitor_base_url_count += 1
    self.assertEqual(
      self.expected_partition_with_monitor_base_url_count,
      partition_with_monitor_base_url_count
    )


@skipUnlessKvm
class TestAccessDefault(MonitorAccessMixin, KVMTestCase):
  __partition_reference__ = 'ad'
  kvm_instance_partition_reference = 'ad0'
  expected_partition_with_monitor_base_url_count = 1

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    authenticated_url = self.getAuthenticatedUrl(connection_parameter_dict)
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)
    self.assertNotIn('url-additional', connection_parameter_dict)


@skipUnlessKvm
class TestAccessDefaultAdditional(MonitorAccessMixin, KVMTestCase):
  __partition_reference__ = 'ada'
  kvm_instance_partition_reference = 'ada0'
  expected_partition_with_monitor_base_url_count = 1

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'frontend-additional-instance-guid': 'SOMETHING'
    })}

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    authenticated_url = self.getAuthenticatedUrl(connection_parameter_dict)
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)

    authenticated_url = self.getAuthenticatedUrl(
      connection_parameter_dict, additional=True)
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)


@skipUnlessKvm
class TestAccessDefaultBootstrap(MonitorAccessMixin, KVMTestCase):
  __partition_reference__ = 'adb'
  kvm_instance_partition_reference = 'adb0'
  expected_partition_with_monitor_base_url_count = 1

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(dict(
      bootstrap_common_param_dict, **bootstrap_machine_param_dict))}

  def test(self):
    # START: mock .slapos-resource with tap.ipv4_addr
    # needed for netconfig.sh
    partition_path = str(self.computer_partition_root_path)
    top_partition_path = self._findTopLevelPartitionPath(partition_path)

    with open(os.path.join(top_partition_path, '.slapos-resource')) as f:
      top_tap = json.load(f)['tap']

    if top_tap['ipv4_addr'] == '':
      top_tap.update({
        "ipv4_addr": "10.0.0.2",
        "ipv4_gateway": "10.0.0.1",
        "ipv4_netmask": "255.255.0.0",
        "ipv4_network": "10.0.0.0"
      })

    self._updateSlaposResource(partition_path, tap=top_tap)

    self.waitForInstanceWithForce()
    # END: mock .slapos-resource with tap.ipv4_addr

    connection_parameter_dict = self.getConnectionParameterDictJson()
    authenticated_url = self.getAuthenticatedUrl(connection_parameter_dict)
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)
    # check that expected files to configure the VM are exposed by the instance
    self.assertEqual(
      ['delDefaultIface', 'netconfig.sh'],
      sorted(os.listdir(os.path.join(
        self.computer_partition_root_path, 'srv', 'public')))
    )


@skipUnlessKvm
class TestAccessKvmCluster(MonitorAccessMixin, KVMTestCase):
  __partition_reference__ = 'akc'
  kvm_instance_partition_reference = 'akc0'
  expected_partition_with_monitor_base_url_count = 2

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      "kvm-partition-dict": {
        "KVM0": {
            "disable-ansible-promise": True
        }
      }
    })}

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    authenticated_url = self.getAuthenticatedUrl(
      connection_parameter_dict, prefix='KVM0-')
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)
    self.assertNotIn('KVM0-url-additional', connection_parameter_dict)

    disable_novnc_server_parameters = {
      "kvm-partition-dict": {
        "KVM0": {
            "disable-ansible-promise": True,
            "enable-novnc-server": False
        }
      }
    }
    self.rerequestInstance(disable_novnc_server_parameters)
    self.waitForInstanceWithPropagation()
    self.computer_partition = self.rerequestInstance(
      disable_novnc_server_parameters)

    connection_parameter_dict = self.getConnectionParameterDictJson()
    self.assertNotIn('KVM0-url', connection_parameter_dict)
    self.assertNotIn('KVM0-url-additional', connection_parameter_dict)
    # check also that old URL is not working anymore
    with self.assertRaises(requests.exceptions.ConnectionError):
      requests.get(authenticated_url, verify=False)

    enable_novnc_server_parameters = {
      "kvm-partition-dict": {
        "KVM0": {
            "disable-ansible-promise": True,
            "enable-novnc-server": True
        }
      }
    }
    self.rerequestInstance(enable_novnc_server_parameters)
    self.waitForInstanceWithPropagation()
    self.computer_partition = self.rerequestInstance(
      enable_novnc_server_parameters)

    connection_parameter_dict = self.getConnectionParameterDictJson()
    self.assertIn('KVM0-url', connection_parameter_dict)
    self.assertNotIn('KVM0-url-additional', connection_parameter_dict)
    self.assertEqual(authenticated_url, self.getAuthenticatedUrl(
      connection_parameter_dict, prefix='KVM0-'))
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )


@skipUnlessKvm
class TestAccessKvmClusterAdditional(MonitorAccessMixin, KVMTestCase):
  __partition_reference__ = 'akca'
  kvm_instance_partition_reference = 'akca0'
  expected_partition_with_monitor_base_url_count = 2

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      "frontend": {
        'frontend-additional-instance-guid': 'SOMETHING',
      },
      "kvm-partition-dict": {
        "KVM0": {
            "disable-ansible-promise": True,
        }
      }
    })}

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    authenticated_url = self.getAuthenticatedUrl(
      connection_parameter_dict, prefix='KVM0-')
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)

    authenticated_url = self.getAuthenticatedUrl(
      connection_parameter_dict, prefix='KVM0-', additional=True)
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)


@skipUnlessKvm
class TestAccessKvmClusterBootstrap(MonitorAccessMixin, KVMTestCase):
  __partition_reference__ = 'akcb'
  kvm_instance_partition_reference = 'akcb0'
  expected_partition_with_monitor_base_url_count = 3

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(dict(bootstrap_common_param_dict, **{
      "slave-frontend": {
        "slave-frontend-dict": {}
      },
      "fw-restricted-access": "off",
      "fw-authorized-sources": [],
      "fw-reject-sources": ["10.32.0.0/13"],
      "kvm-partition-dict": {
          "test-machine1": dict(bootstrap_machine_param_dict, **{
              "computer-guid": "local",
              "state": "started"
          })
      }
    }))}

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    authenticated_url = self.getAuthenticatedUrl(
      connection_parameter_dict, prefix='test-machine1-')
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)

  def test_2machines(self):
    parameters_2machines = dict(bootstrap_common_param_dict, **{
      "slave-frontend": {
        "slave-frontend-dict": {}
      },
      "fw-restricted-access": "off",
      "fw-authorized-sources": [],
      "fw-reject-sources": ["10.32.0.0/13"],
      "kvm-partition-dict": {
          "test-machine1": dict(bootstrap_machine_param_dict, **{
              "computer-guid": "local",
              "state": "started"
          }),
          "test-machine2": dict(bootstrap_machine_param_dict, **{
              "computer-guid": "local",
              "state": "started",
              "virtual-hard-drive-url":
              "http://shacache.org/shacache/5bdc95ea3f8ca40ff4fb8d086776e393"
              "87a68e91f76b1a5f883dfc33fa13cf1ee71c7d218a4e9401f56519a352791"
              "272ada4a5c334b3ca38a32c0bcacb6838e2",
              "virtual-hard-drive-md5sum": "deaf751a31dd6aec320d67c75c88c2e1",
              "virtual-hard-drive-gzipped": True,
          })
      }
    })
    self.rerequestInstance(parameters_2machines)
    # a configuration with 2 machines won't work because we can't have 2 VM
    # started in the same partition (because they would use the same tap). We
    # can still test that the parameters for the 2nd machine exist.
    self.raising_waitForInstance(4)
    self.computer_partition = self.rerequestInstance(parameters_2machines)

    connection_parameter_dict = self.getConnectionParameterDictJson()
    authenticated_url = self.getAuthenticatedUrl(
      connection_parameter_dict, prefix='test-machine1-')
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)
    authenticated_url = self.getAuthenticatedUrl(
      connection_parameter_dict, prefix='test-machine2-')
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)


class CronMixin(object):
  def setUp(self):
    super().setUp()
    # wait until all mocked partition have var/cron-environment.json
    for i in range(20):
      missing_list = []
      for mocked in glob.glob(os.path.join(
        self.slap._instance_root, '*', 'var', 'cron-d-mock')):
        cron_environment = os.path.join(
          '/', *mocked.split('/')[:-2], 'var', 'cron-environment.json')
        if not os.path.exists(cron_environment):
          missing_list.append(cron_environment)
      if len(missing_list) == 0:
        break
      time.sleep(1)
    else:
      raise ValueError('Missing cron environment', ' '.join(missing_list))

  @classmethod
  def executeCronDMockJob(cls, instance_type, cron):
    jobpath = cls.getPartitionPath(
      instance_type, 'var', 'cron-d-mock', cron)
    with open(
      cls.getPartitionPath(
          instance_type, 'var', 'cron-environment.json')) as fh:
      cron_environment = json.load(fh)
    job_list = []
    with open(jobpath, 'r') as fh:
      for job in fh.readlines():
        job = job.strip()
        job_list.append(job)
    job_list_output = []
    for job in job_list:
      job_list_output.append(subprocess.run(
        job, env=cron_environment, shell=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT))
    return job_list_output


class TestInstanceResilientBackupMixin(CronMixin, KvmMixin):
  __partition_reference__ = 'irb'
  instance_max_retry = 20

  disk_type = 'virtio'

  @classmethod
  def getInstanceParameterDict(cls):
    parameter_dict = {}
    if cls.disk_type != 'virtio':
      parameter_dict['disk-type'] = cls.disk_type
    return {'_': json.dumps(parameter_dict)}

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'

  def setUp(self):
    super().setUp()
    importer_partition = glob.glob(os.path.join(
      self.slap.instance_directory, '*', 'template-kvm-import.cfg'))
    self.assertEqual(1, len(importer_partition))
    self.importer_partition = os.path.dirname(importer_partition[0])

  def call_exporter(self):
    result = self.executeCronDMockJob('kvm-export', 'backup')
    self.assertEqual(len(result), 1)
    self.assertEqual(
      0,
      result[0].returncode,
      result[0].stdout.decode('utf-8'))
    return result[0].stdout.decode('utf-8')

  def assertExporterStatus(
    self, status_text,
    post_take_over=False,
    partial_recover=False,
    empty_backup_recover=False,
    migrated_old=False,
    recovered_not_ready=False
  ):
    take_over_text = 'Post take-over or post qmpbackup upgrade cleanup'
    if post_take_over:
      self.assertIn(take_over_text, status_text)
    else:
      self.assertNotIn(take_over_text, status_text)

    partial_recover_text = 'Recovered from partial backup by removing partial'
    if partial_recover:
      self.assertIn(partial_recover_text, status_text)
    else:
      self.assertNotIn(partial_recover_text, status_text)

    empty_backup_text = 'Recovered from empty backup'
    if empty_backup_recover:
      self.assertIn(empty_backup_text, status_text)
    else:
      self.assertNotIn(empty_backup_text, status_text)

    migrated_old_text = 'Migrated from old style backup by removing backup '\
                        'directory and bitmaps'
    if migrated_old:
      self.assertIn(migrated_old_text, status_text)
    else:
      self.assertNotIn(migrated_old_text, status_text)

    recovered_not_ready_text = 'Recovered from state not ready'
    if recovered_not_ready:
      self.assertIn(recovered_not_ready_text, status_text)
    else:
      self.assertNotIn(recovered_not_ready_text, status_text)


def awaitBackup(equeue_file):
  for f in range(30):
    with open(equeue_file, 'r') as fh:
      equeue_log = fh.read()
      if 'finished successfully' in equeue_log:
        break
    time.sleep(1)
  else:
    raise ValueError('Backup not finished: %s' % (equeue_log))
  return equeue_log


@skipUnlessKvm
class TestInstanceResilientBackupImporter(
  TestInstanceResilientBackupMixin, KVMTestCase):
  def test(self):
    equeue_file = os.path.join(
      self.importer_partition, 'var', 'log', 'equeue.log')
    destination_qcow2 = os.path.join(
      self.importer_partition, 'srv', 'virtual.qcow2')
    destination_backup = os.path.join(
      self.importer_partition, 'srv', 'backup', 'kvm', 'virtual1')
    # sanity check - no export/import happened yet
    self.assertFalse(os.path.exists(self.getKvmExportPartitionBackupPath()))
    self.call_exporter()

    equeue_log = awaitBackup(equeue_file)
    self.assertNotIn('qemu-img rebase', equeue_log)
    self.assertEqual(
      os.listdir(self.getKvmExportPartitionBackupPath()),
      os.listdir(destination_backup)
    )
    self.assertTrue(os.path.exists(destination_qcow2))
    # clean up equeue file for precise assertion
    with open(equeue_file, 'w') as fh:
      fh.write('')
    # drop backup destination to assert its recreation
    os.unlink(destination_qcow2)
    self.call_exporter()
    equeue_log = awaitBackup(equeue_file)
    self.assertIn('qemu-img rebase', equeue_log)
    self.assertEqual(
      os.listdir(self.getKvmExportPartitionBackupPath()),
      os.listdir(destination_backup)
    )
    self.assertTrue(os.path.exists(destination_qcow2))
    # takeover
    connection_parameter = self.getConnectionParameterDictJson()
    takeover_result = requests.post(
      connection_parameter['takeover-kvm-1-url'],
      data={
        'password': connection_parameter['takeover-kvm-1-password']})
    self.assertEqual(httplib.OK, takeover_result.status_code)
    self.assertTrue(takeover_result.text.startswith('Success.'))
    # the real assertions comes from re-stabilizing the instance tree
    self.slap.waitForInstance(max_retry=10)
    # check that all stabilizes after backup after takeover
    status_text = self.call_exporter()
    self.assertExporterStatus(status_text, post_take_over=True)
    self.slap.waitForInstance(max_retry=10)


@skipUnlessKvm
class TestInstanceResilientBackupImporterIde(
  TestInstanceResilientBackupImporter):
  disk_type = 'ide'


class TestInstanceResilientBackupExporterMixin(
  TestInstanceResilientBackupMixin):
  def assertImported(self):
    self.assertEqual(
      set(sorted(os.listdir(self.getPartitionPath('kvm-import', 'srv')))),
      set([
        'backup', 'proof.signature', 'virtual.qcow2', 'sshkeys',
        'backup.diff', 'monitor', 'cgi-bin', 'passwd', 'ssl', 'equeue.db'])
    )

  def initialBackup(self):
    equeue_file = self.getPartitionPath(
      'kvm-import', 'var', 'log', 'equeue.log')
    # clean up equeue file for precise assertion
    if os.path.exists(equeue_file):
      shutil.copy(equeue_file, '%s.%s' % (equeue_file, time.time()))
      with open(equeue_file, 'w') as fh:
        fh.write('')
    status_text = self.call_exporter()
    awaitBackup(equeue_file)
    self.assertEqual(
      len(glob.glob(self.getKvmExportPartitionBackupPath('FULL-*.qcow2'))),
      1)
    self.assertEqual(
      len(glob.glob(self.getKvmExportPartitionBackupPath('INC-*.qcow2'))),
      0)
    self.assertExporterStatus(status_text)
    self.assertImported()


@skipUnlessKvm
class TestInstanceResilientBackupExporter(
  TestInstanceResilientBackupExporterMixin, KVMTestCase):
  maxDiff = None

  def test(self):
    self.initialBackup()
    # assure that additional backup run does not leave temporary files
    equeue_file = self.getPartitionPath(
      'kvm-import', 'var', 'log', 'equeue.log')
    # clean up equeue file for precise assertion
    with open(equeue_file, 'w') as fh:
      fh.write('')
    self.call_exporter()
    awaitBackup(equeue_file)
    self.assertEqual(
      len(glob.glob(self.getKvmExportPartitionBackupPath('FULL-*.qcow2'))),
      1)
    self.assertEqual(
      len(glob.glob(self.getKvmExportPartitionBackupPath('INC-*.qcow2'))),
      1)
    self.assertImported()
    # restart the VM and prove that the backup worked
    self.requestDefaultInstance(state='stopped')
    self.waitForInstanceWithPropagation()
    self.requestDefaultInstance()
    self.waitForInstanceWithPropagation()
    # assure that gracefull stop kicked in
    kvm_log_file_list = glob.glob(
      self.getPartitionPath('kvm-export', '.*_kvm-*.log'))
    self.assertEqual(1, len(kvm_log_file_list))
    with open(kvm_log_file_list[0]) as fh:
      kvm_log_list = fh.readlines()
    stopping_str = 'Gracefully stopping qemu\n'
    stopped_str = 'Gracefully stopped qemu\n'
    stopping_list = [q for q in kvm_log_list if q == stopping_str]
    self.assertEqual(1, len(stopping_list))
    stopped_list = [q for q in kvm_log_list[kvm_log_list.index(stopping_str):]
                    if q == stopped_str]
    self.assertEqual(1, len(stopped_list))

    with open(equeue_file, 'w') as fh:
      fh.write('')
    self.call_exporter()
    awaitBackup(equeue_file)
    self.assertEqual(
      len(glob.glob(self.getKvmExportPartitionBackupPath('FULL-*.qcow2'))),
      1)
    self.assertEqual(
      len(glob.glob(self.getKvmExportPartitionBackupPath('INC-*.qcow2'))),
      2)
    self.assertImported()


@skipUnlessKvm
class TestInstanceResilientBackupExporterMigrateOld(
  TestInstanceResilientBackupExporterMixin, KVMTestCase):
  def test(self):
    backup_partition = self.getPartitionPath(
      'kvm-export', 'srv', 'backup', 'kvm')
    backup_file_list = ['virtual.qcow2', 'virtual.qcow2.gz']
    for backup_file in backup_file_list:
      with open(os.path.join(backup_partition, backup_file), 'w') as fh:
        fh.write('')
    self.initialBackup()
    post_backup_file_list = os.listdir(backup_partition)
    for backup_file in backup_file_list:
      self.assertNotIn(backup_file, post_backup_file_list)


@skipUnlessKvm
class TestInstanceResilientBackupExporterMigratePre047(
  TestInstanceResilientBackupExporterMixin, KVMTestCase):
  def test(self):
    # stop the VM to gain write access to the image
    self.requestDefaultInstance(state='stopped')
    self.waitForInstanceWithPropagation()
    image = self.getPartitionPath('kvm-export', 'srv', 'virtual.qcow2')
    with open(
      glob.glob(os.path.join(
          self.slap._instance_root, '*', 'etc', 'kvm_raw.json'))[0]) as fh:
      qemu_img = json.load(fh)['qemu-img-path']
    # added bitmap like old qmpbackup would do
    subprocess.check_call([
      qemu_img, "bitmap", "--add", image,
      "qmpbackup-virtual1-8a1050f7-cabd-4e29-a825-742e5eecdfea"])
    # Simply starting the KVM will do needed migration, so all else works
    self.requestDefaultInstance(state='started')
    self.waitForInstanceWithPropagation()
    self.initialBackup()


@skipUnlessKvm
class TestInstanceResilientBackupExporterPartialRecovery(
  TestInstanceResilientBackupExporterMixin, KVMTestCase):
  def test(self):
    def assertPromiseState(partition_directory, promise, state):
      monitor_run_promise = os.path.join(
        partition_directory, 'software_release', 'bin',
        'monitor.runpromise'
      )
      monitor_configuration = os.path.join(
        partition_directory, 'etc', 'monitor.conf')

      self.assertEqual(
        state,
        subprocess.call([
          monitor_run_promise, '-c', monitor_configuration, '-a', '-f',
          '--run-only', promise])
      )
    self.initialBackup()
    # cover .partial file in the backup directory with fallback to full
    current_backup = glob.glob(
      self.getKvmExportPartitionBackupPath('FULL-*'))[0]

    # assert check-backup-directory behaviour, typical...
    partition_path = self.getPartitionPath('kvm-export')
    assertPromiseState(partition_path, 'check-backup-directory.py', 0)
    with open(current_backup + '.partial', 'w') as fh:
      fh.write('')
    assertPromiseState(partition_path, 'check-backup-directory.py', 1)

    # ...when backup is in progress
    check_backup_directory = self.getPartitionPath(
      'kvm-export', 'bin', 'check-backup-directory')
    current_backup_lock_location = self.getPartitionPath(
      'kvm-export', 'var', 'backup-in-progress')
    # find used flock binary
    flock = None
    with open(check_backup_directory) as fh:
      for line in fh.readlines():
        line = line.strip()
        if 'flock' in line:
          flock = line.split()[1]
    self.assertIsNotNone(flock)

    current_backup_lock = subprocess.Popen([
      flock, '--nonblock', '--no-fork', current_backup_lock_location,
      'sleep', '3600'])
    assertPromiseState(partition_path, 'check-backup-directory.py', 0)
    current_backup_lock.terminate()
    current_backup_lock.wait()

    status_text = self.call_exporter()
    self.assertEqual(
      len(glob.glob(self.getKvmExportPartitionBackupPath('FULL-*.qcow2'))),
      1)
    self.assertEqual(
      len(glob.glob(self.getKvmExportPartitionBackupPath('INC-*.qcow2'))),
      1)
    self.assertExporterStatus(status_text, partial_recover=True)
    assertPromiseState(partition_path, 'check-backup-directory.py', 0)


@skipUnlessKvm
class TestInstanceResilientBackupExporterEmptyRecovery(
  TestInstanceResilientBackupExporterMixin, KVMTestCase):
  def test(self):
    self.initialBackup()
    # cover empty backup recovery
    current_backup_list = glob.glob(
      self.getKvmExportPartitionBackupPath('*.qcow2'))
    self.assertEqual(
      1,
      len(current_backup_list)
    )
    for file in current_backup_list:
      os.unlink(file)
    status_text = self.call_exporter()
    self.assertEqual(
      len(glob.glob(self.getKvmExportPartitionBackupPath('FULL-*.qcow2'))),
      1)
    self.assertEqual(
      len(glob.glob(self.getKvmExportPartitionBackupPath('INC-*.qcow2'))),
      0)
    self.assertExporterStatus(status_text, empty_backup_recover=True)


@skipUnlessKvm
class TestInstanceResilientBackupExporterOldStyleMigration(
  TestInstanceResilientBackupExporterMixin, KVMTestCase):
  old_backup_name = 'virtio0'

  def test(self):
    backup_path = self.getPartitionPath('kvm-export', 'srv', 'backup', 'kvm')
    os.mkdir(os.path.join(backup_path, self.old_backup_name))
    status_text = self.call_exporter()
    self.assertEqual(
      len(glob.glob(self.getKvmExportPartitionBackupPath('FULL-*.qcow2'))),
      1)
    self.assertEqual(
      len(glob.glob(self.getKvmExportPartitionBackupPath('INC-*.qcow2'))),
      0)
    self.assertExporterStatus(status_text, migrated_old=True)


@skipUnlessKvm
class TestInstanceResilientBackupExporterIde(
  TestInstanceResilientBackupExporter):
  maxDiff = None
  disk_type = 'ide'


@skipUnlessKvm
class TestInstanceResilientBackupExporterMigrateOldIde(
  TestInstanceResilientBackupExporterMigrateOld):
  disk_type = 'ide'


@skipUnlessKvm
class TestInstanceResilientBackupExporterPartialRecoveryIde(
  TestInstanceResilientBackupExporterPartialRecovery):
  disk_type = 'ide'


@skipUnlessKvm
class TestInstanceResilientBackupExporterEmptyRecoveryIde(
  TestInstanceResilientBackupExporterEmptyRecovery):
  disk_type = 'ide'


@skipUnlessKvm
class TestInstanceResilientBackupExporterOldStyleMigrationIde(
  TestInstanceResilientBackupExporterOldStyleMigration):
  disk_type = 'ide'
  old_backup_name = 'ide0-hd0'


@skipUnlessKvm
class TestInstanceResilient(KVMTestCase, KvmMixin):
  __partition_reference__ = 'ir'
  kvm_instance_partition_reference = 'ir0'
  instance_max_retry = 20

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      '-sla-0-computer_guid': 'local',
      '-sla-1-computer_guid': 'local',
      '-sla-2-computer_guid': 'local',
      '-sla-pbs1-computer_guid': 'local',
      '-sla-pbs2-computer_guid': 'local',
      'resilient-clone-number': 2,
      'resiliency-backup-periodicity': '#12 1 * * *'
    })}

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls.pbs1_ipv6 = cls.getPartitionIPv6(cls.getPartitionIdByType(
      'pull-backup'))
    # XXX order of partition is
    # ir0: main
    # ir1: PBS1
    # ir2: PBS2
    # ir3: kvm-export
    # ir4: kvm-import1
    # ir5: kvm-import2
    cls.pbs2_ipv6 = cls.getPartitionIPv6('ir2')
    cls.kvm_instance_partition_reference = cls.getPartitionIdByType(
      'kvm-export')
    cls.kvm0_ipv6 = cls.getPartitionIPv6(cls.kvm_instance_partition_reference)
    cls.kvm1_ipv6 = cls.getPartitionIPv6(cls.getPartitionIdByType(
      'kvm-import'))
    cls.kvm2_ipv6 = cls.getPartitionIPv6('ir5')

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    authenticated_url = self.getAuthenticatedUrl(connection_parameter_dict)
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    present_key_list = []
    assert_key_list = [
     'monitor-password', 'takeover-kvm-1-password', 'takeover-kvm-2-password',
     'backend-url', 'url', 'monitor-setup-url', 'ipv6-network-info',
     'username', 'password']
    for k in assert_key_list:
      if k in connection_parameter_dict:
        present_key_list.append(k)
        connection_parameter_dict.pop(k)
    self.maxDiff = None
    self.assertIn('feed-url-kvm-1-pull', connection_parameter_dict)
    feed_pull = connection_parameter_dict.pop('feed-url-kvm-1-pull')
    self.assertRegex(
      feed_pull,
      'http://\\[{}\\]:[0-9][0-9][0-9][0-9]/get/local-ir0-kvm-1-pull'.format(
        self.pbs1_ipv6))
    self.assertIn('feed-url-kvm-1-push', connection_parameter_dict)
    feed_push = connection_parameter_dict.pop('feed-url-kvm-1-push')
    self.assertRegex(
      feed_push,
      'http://\\[{}\\]:[0-9][0-9][0-9][0-9]/get/local-ir0-kvm-1-push'.format(
        self.pbs1_ipv6))
    self.assertIn('feed-url-kvm-2-pull', connection_parameter_dict)
    feed_pull2 = connection_parameter_dict.pop('feed-url-kvm-2-pull')
    self.assertRegex(
      feed_pull2,
      'http://\\[{}\\]:[0-9][0-9][0-9][0-9]/get/local-ir0-kvm-2-pull'.format(
        self.pbs2_ipv6))
    self.assertIn('feed-url-kvm-2-push', connection_parameter_dict)
    feed_push2 = connection_parameter_dict.pop('feed-url-kvm-2-push')
    self.assertRegex(
      feed_push2,
      'http://\\[{}\\]:[0-9][0-9][0-9][0-9]/get/local-ir0-kvm-2-push'.format(
        self.pbs2_ipv6))
    self.assertEqual(
      connection_parameter_dict,
      {
        'ipv6': self.kvm0_ipv6,
        'monitor-base-url':
        f'https://[{self.computer_partition_ipv6_address}]:8196',
        'monitor-user': 'admin',
        'takeover-kvm-1-url': f'http://[{self.kvm1_ipv6}]:9263/',
        'takeover-kvm-2-url': f'http://[{self.kvm2_ipv6}]:9263/',
      }
    )
    self.assertEqual(set(present_key_list), set(assert_key_list))

    self.assertEqual(
      """ir0:bootstrap-monitor EXITED
ir0:certificate_authority-{hash}-on-watch RUNNING
ir0:crond-{hash}-on-watch RUNNING
ir0:monitor-httpd-{hash}-on-watch RUNNING
ir0:monitor-httpd-graceful EXITED
ir1:bootstrap-monitor EXITED
ir1:certificate_authority-{hash}-on-watch RUNNING
ir1:crond-{hash}-on-watch RUNNING
ir1:equeue-on-watch RUNNING
ir1:monitor-httpd-{hash}-on-watch RUNNING
ir1:monitor-httpd-graceful EXITED
ir1:notifier-on-watch RUNNING
ir1:pbs_sshkeys_authority-on-watch RUNNING
ir2:bootstrap-monitor EXITED
ir2:certificate_authority-{hash}-on-watch RUNNING
ir2:crond-{hash}-on-watch RUNNING
ir2:equeue-on-watch RUNNING
ir2:monitor-httpd-{hash}-on-watch RUNNING
ir2:monitor-httpd-graceful EXITED
ir2:notifier-on-watch RUNNING
ir2:pbs_sshkeys_authority-on-watch RUNNING
ir3:6tunnel-10022-{hash}-on-watch RUNNING
ir3:6tunnel-10080-{hash}-on-watch RUNNING
ir3:6tunnel-10443-{hash}-on-watch RUNNING
ir3:boot-image-url-list-updater-{hash} EXITED
ir3:boot-image-url-select-updater-{hash} EXITED
ir3:bootstrap-monitor EXITED
ir3:certificate_authority-{hash}-on-watch RUNNING
ir3:crond-{hash}-on-watch RUNNING
ir3:equeue-on-watch RUNNING
ir3:kvm-{kvm-hash-value}-on-watch RUNNING
ir3:monitor-httpd-{hash}-on-watch RUNNING
ir3:monitor-httpd-graceful EXITED
ir3:nginx-graceful EXITED
ir3:nginx-on-watch RUNNING
ir3:notifier-on-watch RUNNING
ir3:resilient_sshkeys_authority-on-watch RUNNING
ir3:sshd-graceful EXITED
ir3:sshd-on-watch RUNNING
ir3:whitelist-domains-download-{hash} RUNNING
ir3:whitelist-firewall-{hash} RUNNING
ir4:bootstrap-monitor EXITED
ir4:certificate_authority-{hash}-on-watch RUNNING
ir4:crond-{hash}-on-watch RUNNING
ir4:equeue-on-watch RUNNING
ir4:monitor-httpd-{hash}-on-watch RUNNING
ir4:monitor-httpd-graceful EXITED
ir4:notifier-on-watch RUNNING
ir4:resilient-web-takeover-httpd-on-watch RUNNING
ir4:resilient_sshkeys_authority-on-watch RUNNING
ir4:sshd-graceful EXITED
ir4:sshd-on-watch RUNNING
ir5:bootstrap-monitor EXITED
ir5:certificate_authority-{hash}-on-watch RUNNING
ir5:crond-{hash}-on-watch RUNNING
ir5:equeue-on-watch RUNNING
ir5:monitor-httpd-{hash}-on-watch RUNNING
ir5:monitor-httpd-graceful EXITED
ir5:notifier-on-watch RUNNING
ir5:resilient-web-takeover-httpd-on-watch RUNNING
ir5:resilient_sshkeys_authority-on-watch RUNNING
ir5:sshd-graceful EXITED
ir5:sshd-on-watch RUNNING""",
      self.getProcessInfo([
        'var/boot-image-url-list/boot-image-url-list.json',
        'var/boot-image-url-select/boot-image-url-select.json'
      ])
    )

    self.rerequestInstance({"enable-novnc-server": False})
    self.waitForInstanceWithPropagation()
    self.computer_partition = self.rerequestInstance(
      {"enable-novnc-server": False})

    connection_parameter_dict = self.getConnectionParameterDictJson()
    self.assertNotIn('url', connection_parameter_dict)
    self.assertNotIn('url-additional', connection_parameter_dict)
    # check also that old URL is not working anymore
    with self.assertRaises(requests.exceptions.ConnectionError):
      requests.get(authenticated_url, verify=False)

    self.rerequestInstance({"enable-novnc-server": True})
    self.waitForInstanceWithPropagation()
    self.computer_partition = self.rerequestInstance(
      {"enable-novnc-server": True})

    connection_parameter_dict = self.getConnectionParameterDictJson()
    self.assertIn('url', connection_parameter_dict)
    self.assertNotIn('url-additional', connection_parameter_dict)
    self.assertEqual(
      authenticated_url, self.getAuthenticatedUrl(connection_parameter_dict))
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )


@skipUnlessKvm
class TestInstanceResilientDiskTypeIde(KVMTestCase, KvmMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'disk-type': 'ide'
    })}


@skipUnlessKvm
class TestAccessResilientAdditional(MonitorAccessMixin, KVMTestCase):
  __partition_reference__ = 'ara'
  kvm_instance_partition_reference = 'ara0'
  expected_partition_with_monitor_base_url_count = 4

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'frontend-additional-instance-guid': 'SOMETHING'
    })}

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    authenticated_url = self.getAuthenticatedUrl(connection_parameter_dict)
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)

    authenticated_url = self.getAuthenticatedUrl(
      connection_parameter_dict, additional=True)
    result = requests.get(authenticated_url, verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)


class HttpHandler(http.server.SimpleHTTPRequestHandler):
  def log_message(self, *args):
    if os.environ.get('SLAPOS_TEST_DEBUG'):
      return http.server.SimpleHTTPRequestHandler.log_message(self, *args)
    else:
      return


class FakeImageServerMixin(KvmMixin):
  @classmethod
  def setUpClass(cls):
    try:
      cls.findQemuTools()
      cls.startImageHttpServer()
      super().setUpClass()
    except BaseException:
      cls.stopImageHttpServer()
      raise

  @classmethod
  def tearDownClass(cls):
    super().tearDownClass()
    cls.stopImageHttpServer()

  @classmethod
  def startImageHttpServer(cls):
    cls.image_source_directory = tempfile.mkdtemp()
    server = SocketServer.TCPServer(
      (cls._ipv4_address, findFreeTCPPort(cls._ipv4_address)),
      HttpHandler)

    # c89f17758be13adeb06886ef935d5ff1
    fake_image_content = b'fake_image_content'
    cls.fake_image_md5sum = hashlib.md5(fake_image_content).hexdigest()
    with open(os.path.join(
      cls.image_source_directory, cls.fake_image_md5sum), 'wb') as fh:
      fh.write(fake_image_content)

    # bc81d2aee81e030c6cee210c802339c2
    fake_image2_content = b'fake_image2_content'
    cls.fake_image2_md5sum = hashlib.md5(fake_image2_content).hexdigest()
    with open(os.path.join(
      cls.image_source_directory, cls.fake_image2_md5sum), 'wb') as fh:
      fh.write(fake_image2_content)

    cls.fake_image_wrong_md5sum = cls.fake_image2_md5sum

    # c5ef5d70ad5a0dbfd890a734f588e344
    fake_image3_content = b'fake_image3_content'
    cls.fake_image3_md5sum = hashlib.md5(fake_image3_content).hexdigest()
    with open(os.path.join(
      cls.image_source_directory, cls.fake_image3_md5sum), 'wb') as fh:
      fh.write(fake_image3_content)

    # real fake image
    real_image_input = os.path.join(cls.image_source_directory, 'real.img')
    subprocess.check_call([
      cls.qemu_img, "create", "-f", "qcow2", real_image_input, "1M"])

    with open(real_image_input, 'rb') as fh:
      real_image_content = fh.read()
    cls.real_image_md5sum = hashlib.md5(real_image_content).hexdigest()
    with open(os.path.join(
      cls.image_source_directory, cls.real_image_md5sum), 'wb') as fh:
      fh.write(real_image_content)

    real_gzip_content = gzip.compress(real_image_content)
    cls.real_gzip_md5sum = hashlib.md5(real_gzip_content).hexdigest()
    with open(os.path.join(
      cls.image_source_directory, cls.real_gzip_md5sum), 'wb') as fh:
      fh.write(real_gzip_content)

    url = 'http://%s:%s' % server.server_address
    cls.fake_image = '/'.join([url, cls.fake_image_md5sum])
    cls.fake_image2 = '/'.join([url, cls.fake_image2_md5sum])
    cls.fake_image3 = '/'.join([url, cls.fake_image3_md5sum])
    cls.real_image = '/'.join([url, cls.real_image_md5sum])
    cls.real_gzip = '/'.join([url, cls.real_gzip_md5sum])

    old_dir = os.path.realpath(os.curdir)
    os.chdir(cls.image_source_directory)
    try:
      cls.server_process = multiprocessing.Process(
        target=server.serve_forever, name='FakeImageHttpServer', daemon=True)
      cls.server_process.start()
      server.socket.close()
    finally:
      os.chdir(old_dir)

  @classmethod
  def stopImageHttpServer(cls):
    cls.logger.debug('Stopping process %s', cls.server_process)
    cls.server_process.join(10)
    cls.server_process.terminate()
    time.sleep(0.1)
    if cls.server_process.is_alive():
      cls.logger.warning(
        'Process %s still alive', cls.server_process)

    shutil.rmtree(cls.image_source_directory)


@skipUnlessKvm
class TestVirtualHardDriveUrl(FakeImageServerMixin, KVMTestCase):
  __partition_reference__ = 'vhdu'
  kvm_instance_partition_reference = 'vhdu0'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      "virtual-hard-drive-url": cls.real_image,
      "virtual-hard-drive-md5sum": cls.real_image_md5sum
    })}

  def test(self):
    kvm_partition = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference)
    image_repository = os.path.join(
      kvm_partition,
      'srv', 'virtual-hard-drive-url-repository')
    self.assertEqual(
      [json.loads(self.getInstanceParameterDict()['_'])[
        'virtual-hard-drive-md5sum']],
      os.listdir(image_repository)
    )
    destination_image = os.path.join(kvm_partition, 'srv', 'virtual.qcow2')
    # compare result of qemu-img info of repository and the one
    qemu_img_list = [self.qemu_img, 'info', '-U', '--output', 'json']
    source_image_info_json = json.loads(subprocess.check_output(
      qemu_img_list + [
        os.path.join(self.image_source_directory, self.real_image_md5sum)]))
    destination_image_info_json = json.loads(subprocess.check_output(
      qemu_img_list + [destination_image]))
    source_image_info_json.pop('filename')
    destination_image_info_json.pop('filename')
    source_image_info_json['children'][0]['info'].pop('filename')
    destination_image_info_json['children'][0]['info'].pop('filename')
    # the best possible way to assure that provided image is used is by
    # comparing the result of qemu-img info for both
    self.assertEqual(
      source_image_info_json,
      destination_image_info_json
    )


@skipUnlessKvm
class TestVirtualHardDriveUrlGzipped(TestVirtualHardDriveUrl):
  __partition_reference__ = 'vhdug'
  kvm_instance_partition_reference = 'vhdug0'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      "virtual-hard-drive-url": cls.real_gzip,
      "virtual-hard-drive-md5sum": cls.real_gzip_md5sum,
      "virtual-hard-drive-gzipped": True
    })}


@skipUnlessKvm
class TestBootImageUrlList(FakeImageServerMixin, KVMTestCase):
  __partition_reference__ = 'biul'
  kvm_instance_partition_reference = 'biul0'

  # variations
  key = 'boot-image-url-list'
  test_input = "%s#%s\n%s#%s"
  image_directory = 'boot-image-url-list-repository'
  config_state_promise = 'boot-image-url-list-config-state-promise.py'
  download_md5sum_promise = 'boot-image-url-list-download-md5sum-promise.py'
  download_state_promise = 'boot-image-url-list-download-state-promise.py'

  bad_value = "jsutbad"
  incorrect_md5sum_value_image = "%s#"
  incorrect_md5sum_value = "url#asdasd"
  single_image_value = "%s#%s"
  unreachable_host_value = "evennotahost#%s"
  too_many_image_value = """
      image1#11111111111111111111111111111111
      image2#22222222222222222222222222222222
      image3#33333333333333333333333333333333
      image4#44444444444444444444444444444444
      image5#55555555555555555555555555555555
      image6#66666666666666666666666666666666
      """

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'default'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      cls.key: cls.test_input % (
        cls.fake_image, cls.fake_image_md5sum, cls.fake_image2,
        cls.fake_image2_md5sum)
    })}

  def tearDown(self):
    # clean up the instance for other tests
    # move instance to "default" state
    self.rerequestInstance()
    self.slap.waitForInstance(max_retry=20)
    super().tearDown()

  def test(self):
    # check that image is correctly downloaded
    kvm_instance_partition = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference)
    image_repository = os.path.join(
      kvm_instance_partition, 'srv', self.image_directory)
    image = os.path.join(image_repository, self.fake_image_md5sum)
    self.assertTrue(os.path.exists(image))
    with open(image, 'rb') as fh:
      image_md5sum = hashlib.md5(fh.read()).hexdigest()
    self.assertEqual(image_md5sum, self.fake_image_md5sum)

    image2 = os.path.join(image_repository, self.fake_image2_md5sum)
    self.assertTrue(os.path.exists(image2))
    with open(image2, 'rb') as fh:
      image2_md5sum = hashlib.md5(fh.read()).hexdigest()
    self.assertEqual(image2_md5sum, self.fake_image2_md5sum)

    self.assertEqual(
      [
        f'${{inst}}/srv/{self.image_directory}/{self.fake_image_md5sum}',
        f'${{inst}}/srv/{self.image_directory}/{self.fake_image2_md5sum}',
      ],
      self.getRunningImageList()
    )

    # Switch image
    self.rerequestInstance({
      self.key: self.test_input % (
        self.fake_image3, self.fake_image3_md5sum,
        self.fake_image2, self.fake_image2_md5sum)
    })
    self.waitForInstanceWithPropagation()
    self.assertTrue(os.path.exists(os.path.join(
      image_repository, self.fake_image3_md5sum)))
    self.assertTrue(os.path.exists(os.path.join(
      image_repository, self.fake_image2_md5sum)))

    self.assertEqual(
      [
        f'${{inst}}/srv/{self.image_directory}/{self.fake_image3_md5sum}',
        f'${{inst}}/srv/{self.image_directory}/{self.fake_image2_md5sum}',
      ],
      self.getRunningImageList()
    )

    # cleanup of images works, also asserts that configuration changes are
    # reflected
    self.rerequestInstance()
    self.waitForInstanceWithPropagation()
    self.assertEqual(
      os.listdir(image_repository),
      []
    )

    # again only default image is available in the running process
    self.assertEqual(
      ['${inst}/srv/boot-image-url-select-repository/' + DEFAULT_IMAGE_MD5SUM],
      self.getRunningImageList()
    )

  def test_bad_parameter(self):
    self.rerequestInstance({
      self.key: self.bad_value
    })
    if self.getInstanceSoftwareType() == 'kvm-resilient':
      self.waitForInstance()
    self.raising_waitForInstance(5)
    self.assertPromiseFails(self.config_state_promise)

  def test_incorrect_md5sum(self):
    self.rerequestInstance({
      self.key: self.incorrect_md5sum_value_image % (self.fake_image,)
    })
    if self.getInstanceSoftwareType() == 'kvm-resilient':
      self.waitForInstance()
    self.raising_waitForInstance(5)
    self.assertPromiseFails(self.config_state_promise)

  def test_incorrect_md5sum_value(self):
    self.rerequestInstance({
      self.key: self.incorrect_md5sum_value
    })
    if self.getInstanceSoftwareType() == 'kvm-resilient':
      self.waitForInstance()
    self.raising_waitForInstance(5)
    self.assertPromiseFails(self.config_state_promise)

  def test_not_matching_md5sum(self):
    self.rerequestInstance({
      self.key: self.single_image_value % (
        self.fake_image, self.fake_image_wrong_md5sum)
    })
    if self.getInstanceSoftwareType() == 'kvm-resilient':
      self.waitForInstance()
    self.raising_waitForInstance(5)
    self.assertPromiseFails(self.download_md5sum_promise)
    self.assertPromiseFails(self.download_state_promise)

  def test_unreachable_host(self):
    self.rerequestInstance({
      self.key: self.unreachable_host_value % (
        self.fake_image_md5sum,)
    })
    if self.getInstanceSoftwareType() == 'kvm-resilient':
      self.waitForInstance()
    self.raising_waitForInstance(5)
    self.assertPromiseFails(self.download_state_promise)

  def test_too_many_images(self):
    self.rerequestInstance({
      self.key: self.too_many_image_value
    })
    if self.getInstanceSoftwareType() == 'kvm-resilient':
      self.waitForInstance()
    self.raising_waitForInstance(5)
    self.assertPromiseFails(self.config_state_promise)


@skipUnlessKvm
class TestBootImageUrlListResilient(TestBootImageUrlList):
  kvm_instance_partition_reference = 'biul2'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'


@skipUnlessKvm
class TestBootImageUrlSelect(FakeImageServerMixin, KVMTestCase):
  __partition_reference__ = 'bius'
  kvm_instance_partition_reference = 'bius0'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'default'

  def test(self):
    # check the default image
    image_repository = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference,
      'srv', 'boot-image-url-select-repository')
    self.assertEqual(
      [DEFAULT_IMAGE_MD5SUM],
      os.listdir(image_repository)
    )
    with open(os.path.join(
      image_repository, DEFAULT_IMAGE_MD5SUM), 'rb') as fh:
      image_md5sum = hashlib.md5(fh.read()).hexdigest()
    self.assertEqual(image_md5sum, DEFAULT_IMAGE_MD5SUM)
    self.assertEqual(
      ['${inst}/srv/boot-image-url-select-repository/' + DEFAULT_IMAGE_MD5SUM],
      self.getRunningImageList()
    )
    # switch the image
    self.rerequestInstance({
      'boot-image-url-select': "Debian Bullseye 11 netinst x86_64"})
    self.waitForInstanceWithPropagation()
    image_repository = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference,
      'srv', 'boot-image-url-select-repository')
    self.assertEqual(
      ['b710c178eb434d79ce40ce703d30a5f0'],
      os.listdir(image_repository)
    )
    image = os.path.join(image_repository, 'b710c178eb434d79ce40ce703d30a5f0')
    self.assertTrue(os.path.exists(image))
    with open(image, 'rb') as fh:
      image_md5sum = hashlib.md5(fh.read()).hexdigest()
    self.assertEqual(image_md5sum, 'b710c178eb434d79ce40ce703d30a5f0')
    self.assertEqual(
      [
        '${inst}/srv/boot-image-url-select-repository/'
        'b710c178eb434d79ce40ce703d30a5f0'
      ],
      self.getRunningImageList()
    )

  def test_bad_image(self):
    self.rerequestInstance({
      'boot-image-url-select': 'DOESNOTEXISTS'
    })
    self.raising_waitForInstance(2)
    # we check that buildout fails in the top level partition (because it is
    # a problem of parameter)
    partition_id = self.getPartitionIdByType(self.getInstanceSoftwareType())
    partition_path = self.getPartitionPath(self.getInstanceSoftwareType())
    buildout_promise = 'buildout-%s-status.py' % partition_id
    self.assertPromiseFailsInDir(partition_path, buildout_promise)

  def test_together(self):
    partition_parameter_kw = {
      'boot-image-url-list': "{}#{}".format(
        self.fake_image, self.fake_image_md5sum),
      'boot-image-url-select': "Debian Bullseye 11 netinst x86_64"
    }
    self.rerequestInstance(partition_parameter_kw)
    self.waitForInstanceWithPropagation()
    # check that image is correctly downloaded
    image_repository = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference,
      'srv', 'boot-image-url-list-repository')
    self.assertEqual(
      [self.fake_image_md5sum],
      os.listdir(image_repository)
    )
    image = os.path.join(image_repository, self.fake_image_md5sum)
    self.assertTrue(os.path.exists(image))
    with open(image, 'rb') as fh:
      image_md5sum = hashlib.md5(fh.read()).hexdigest()
    self.assertEqual(image_md5sum, self.fake_image_md5sum)

    image_repository = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference,
      'srv', 'boot-image-url-select-repository')
    self.assertEqual(
      ['b710c178eb434d79ce40ce703d30a5f0'],
      os.listdir(image_repository)
    )
    image = os.path.join(image_repository, 'b710c178eb434d79ce40ce703d30a5f0')
    self.assertTrue(os.path.exists(image))
    with open(image, 'rb') as fh:
      image_md5sum = hashlib.md5(fh.read()).hexdigest()
    self.assertEqual(image_md5sum, 'b710c178eb434d79ce40ce703d30a5f0')

    kvm_instance_partition = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference)

    self.assertEqual(
      [
        '${{inst}}/srv/boot-image-url-list-repository/{}'.format(
          self.fake_image_md5sum),
        '${inst}/srv/boot-image-url-select-repository/'
        'b710c178eb434d79ce40ce703d30a5f0'
      ],
      self.getRunningImageList()
    )

    # check that using only boot-image-url-list results with not having
    # boot-image-url-select if nothing is provided
    partition_parameter_kw = {
      'boot-image-url-list': "{}#{}".format(
        self.fake_image, self.fake_image_md5sum),
    }
    self.rerequestInstance(partition_parameter_kw)
    self.waitForInstanceWithPropagation()
    # check that image is correctly downloaded
    image_repository = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference,
      'srv', 'boot-image-url-list-repository')
    self.assertEqual(
      [self.fake_image_md5sum],
      os.listdir(image_repository)
    )
    image = os.path.join(image_repository, self.fake_image_md5sum)
    self.assertTrue(os.path.exists(image))
    with open(image, 'rb') as fh:
      image_md5sum = hashlib.md5(fh.read()).hexdigest()
    self.assertEqual(image_md5sum, self.fake_image_md5sum)

    self.assertEqual(
      [],
      os.listdir(os.path.join(
        self.slap.instance_directory, self.kvm_instance_partition_reference,
        'srv', 'boot-image-url-select-repository'))
    )

    kvm_instance_partition = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference)

    self.assertEqual(
      [
        '${{inst}}/srv/boot-image-url-list-repository/{}'.format(
          self.fake_image_md5sum),
      ],
      self.getRunningImageList()
    )

    # cleanup of images works, also asserts that configuration changes are
    # reflected
    self.rerequestInstance()
    self.waitForInstanceWithPropagation()

    self.assertEqual(
      os.listdir(os.path.join(
        kvm_instance_partition, 'srv', 'boot-image-url-select-repository')),
      [DEFAULT_IMAGE_MD5SUM]
    )
    self.assertEqual(
      os.listdir(os.path.join(
        kvm_instance_partition, 'srv', 'boot-image-url-list-repository')),
      []
    )

    # again only default image is available in the running process
    self.assertEqual(
      ['${inst}/srv/boot-image-url-select-repository/' + DEFAULT_IMAGE_MD5SUM],
      self.getRunningImageList()
    )


@skipUnlessKvm
class TestBootImageUrlSelectResilient(TestBootImageUrlSelect):
  kvm_instance_partition_reference = 'bius2'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'


@skipUnlessKvm
class TestBootImageUrlListKvmCluster(FakeImageServerMixin, KVMTestCase):
  __partition_reference__ = 'biulkc'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'

  input_value = "%s#%s"
  key = 'boot-image-url-list'
  config_file_name = 'boot-image-url-list.conf'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      "kvm-partition-dict": {
        "KVM0": {
            "disable-ansible-promise": True,
        }
      }
    })}

  def test(self):
    # Note: As there is no way to introspect nicely where partition landed
    #       we assume ordering of the cluster requests
    self.rerequestInstance({
      "kvm-partition-dict": {
        "KVM0": {
            "disable-ansible-promise": True,
            self.key: self.input_value % (
              self.fake_image, self.fake_image_md5sum)
        },
        "KVM1": {
            "disable-ansible-promise": True,
            self.key: self.input_value % (
              self.fake_image2, self.fake_image2_md5sum)
        }
      }
    })
    # a configuration with 2 machines won't work because we can't have 2 VM
    # started in the same partition (because they would use the same tap). We
    # can still test that the config file for the 2nd machine is OK.
    self.raising_waitForInstance(4)
    KVM0_config = os.path.join(
      self.slap.instance_directory, self.__partition_reference__ + '1', 'etc',
      self.config_file_name)
    KVM1_config = os.path.join(
      self.slap.instance_directory, self.__partition_reference__ + '2', 'etc',
      self.config_file_name)
    with open(KVM0_config) as fh:
      self.assertEqual(
        self.input_value % (self.fake_image, self.fake_image_md5sum),
        fh.read().strip()
      )
    with open(KVM1_config) as fh:
      self.assertEqual(
        self.input_value % (self.fake_image2, self.fake_image2_md5sum),
        fh.read().strip()
      )


@skipUnlessKvm
class TestBootImageUrlSelectKvmCluster(KvmMixin, KVMTestCase):
  __partition_reference__ = 'biuskc'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      "kvm-partition-dict": {
        "KVM0": {
            "disable-ansible-promise": True,
        }
      }
    })}

  def test(self):
    # Note: As there is no way to introspect nicely where partition landed
    #       we assume ordering of the cluster requests
    self.rerequestInstance({
      "kvm-partition-dict": {
        "KVM0": {
            "disable-ansible-promise": True,
            "boot-image-url-select": "Debian Bullseye 11 netinst x86_64"
        },
        "KVM1": {
            "disable-ansible-promise": True,
            "boot-image-url-select": DEFAULT_IMAGE_TITLE,
        }
      }
    })
    # a configuration with 2 machines won't work because we can't have 2 VM
    # started in the same partition (because they would use the same tap). We
    # can still test that the config file for the 2nd machine is OK.
    self.raising_waitForInstance(4)
    KVM0_config = os.path.join(
      self.slap.instance_directory, self.__partition_reference__ + '1', 'etc',
      'boot-image-url-select.json')
    KVM1_config = os.path.join(
      self.slap.instance_directory, self.__partition_reference__ + '2', 'etc',
      'boot-image-url-select.json')
    with open(KVM0_config) as fh:
      self.assertEqual(
        '["https://shacache.nxdcdn.com/02257c3ec27e45d9f022c181a69b59da67e5c7'
        '2871cdb4f9a69db323a1fad58093f2e69702d29aa98f5f65e920e0b970d816475a5a'
        '936e1f3bf33832257b7e92#b710c178eb434d79ce40ce703d30a5f0"]',
        fh.read().strip()
      )
    with open(KVM1_config) as fh:
      config = fh.read().strip()
      # we don't know where the shared directly will be so just assert begin
      # and end of the path
      self.assertIn(
        '["file://',
        config
      )
      self.assertIn(
        '%s#%s"]' % (DEFAULT_IMAGE_ISONAME, DEFAULT_IMAGE_MD5SUM),
        config
      )


@skipUnlessKvm
class TestNatRules(KvmMixin, KVMTestCase):
  __partition_reference__ = 'nr'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'nat-rules': [100, 200],
    })}

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()

    self.assertIn('nat-rule-port-tcp-100', connection_parameter_dict)
    self.assertIn('nat-rule-port-tcp-200', connection_parameter_dict)

    self.assertEqual(
      f'{self.computer_partition_ipv6_address} : 10100',
      connection_parameter_dict['nat-rule-port-tcp-100']
    )
    self.assertEqual(
      f'{self.computer_partition_ipv6_address} : 10200',
      connection_parameter_dict['nat-rule-port-tcp-200']
    )


@skipUnlessKvm
class TestNatRulesKvmCluster(KVMTestCase):
  __partition_reference__ = 'nrkc'

  nat_rules = [100, 200, 300]

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      "kvm-partition-dict": {
        "KVM0": {
            "nat-rules": cls.nat_rules,
            "disable-ansible-promise": True,
        }
      }
    })}

  def getRunningHostFwd(self):
    kvm_pid_file_list = glob.glob(os.path.join(
      self.slap._instance_root, '*', 'var', 'run', 'kvm.pid'))
    self.assertEqual(1, len(kvm_pid_file_list))
    with open(kvm_pid_file_list[0]) as fh:
      kvm_pid = int(fh.read().strip())
    kvm_process = psutil.Process(kvm_pid)
    for entry in kvm_process.cmdline():
      if 'hostfwd' in entry:
        return entry

  def test(self):
    host_fwd_entry = self.getRunningHostFwd()
    self.assertIn(
      f'hostfwd=tcp:{self._ipv4_address}:10100-:100',
      host_fwd_entry)
    self.assertIn(
      f'hostfwd=tcp:{self._ipv4_address}:10200-:200',
      host_fwd_entry)
    self.assertIn(
      f'hostfwd=tcp:{self._ipv4_address}:10300-:300',
      host_fwd_entry)

@skipUnlessKvm
class TestWhitelistFirewall(KVMTestCase):
  __partition_reference__ = 'wf'
  kvm_instance_partition_reference = 'wf0'

  def test(self):
    slapos_whitelist_firewall = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference,
      '.slapos-whitelist-firewall')
    self.assertTrue(os.path.exists(slapos_whitelist_firewall))
    with open(slapos_whitelist_firewall, 'rb') as fh:
      content = fh.read()
    try:
      self.content_json = json.loads(content)
    except ValueError:
      self.fail(f'Failed to parse json of {content!r}')
    self.assertTrue(isinstance(self.content_json, list))
    # check /etc/resolv.conf
    with open('/etc/resolv.conf') as f:
      resolv_conf_ip_list = []
      for line in f.readlines():
        if line.startswith('nameserver'):
          resolv_conf_ip_list.append(line.split()[1])
    resolv_conf_ip_list = list(set(resolv_conf_ip_list))
    self.assertFalse(len(resolv_conf_ip_list) == 0)
    self.assertTrue(all([q in self.content_json for q in resolv_conf_ip_list]))
    # there is something more
    self.assertGreater(len(self.content_json), len(resolv_conf_ip_list))


@skipUnlessKvm
class TestWhitelistFirewallRequest(TestWhitelistFirewall):
  whitelist_domains = '2.2.2.2 3.3.3.3\n4.4.4.4'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'whitelist-domains': cls.whitelist_domains,
    })}

  def test(self):
    super().test()
    self.assertIn('2.2.2.2', self.content_json)
    self.assertIn('3.3.3.3', self.content_json)
    self.assertIn('4.4.4.4', self.content_json)


@skipUnlessKvm
class TestWhitelistFirewallResilient(TestWhitelistFirewall):
  kvm_instance_partition_reference = 'wf2'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'


@skipUnlessKvm
class TestWhitelistFirewallRequestResilient(TestWhitelistFirewallRequest):
  kvm_instance_partition_reference = 'wf2'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'


@skipUnlessKvm
class TestWhitelistFirewallCluster(TestWhitelistFirewall):
  kvm_instance_partition_reference = 'wf1'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      "kvm-partition-dict": {
        "KVM0": {
            "disable-ansible-promise": True
        }
      }
    })}


@skipUnlessKvm
class TestWhitelistFirewallRequestCluster(TestWhitelistFirewallRequest):
  kvm_instance_partition_reference = 'wf1'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      "kvm-partition-dict": {
        "KVM0": {
            "whitelist-domains": cls.whitelist_domains,
            "disable-ansible-promise": True
        }
      }
    })}


@skipUnlessKvm
class TestDiskDevicePathWipeDiskOndestroy(KVMTestCase, KvmMixin):
  __partition_reference__ = 'ddpwdo'
  kvm_instance_partition_reference = 'ddpwdo0'

  def test(self):
    self.rerequestInstance({
      'disk-device-path': '/dev/virt0 /dev/virt1',
      'wipe-disk-ondestroy': True
    })
    self.raising_waitForInstance(3)
    instance_path = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference)

    slapos_wipe_device_disk = os.path.join(
      instance_path, 'etc', 'prerm', 'slapos_wipe_device_disk')

    # check prerm script, it's trusted that prerm manager really works
    self.assertTrue(os.path.exists(slapos_wipe_device_disk))
    with open(slapos_wipe_device_disk) as fh:
      self.assertEqual(
        fh.read().strip(),
        r"""#!/bin/sh
dd if=/dev/zero of=/dev/virt0 bs=4096 count=500k
dd if=/dev/zero of=/dev/virt1 bs=4096 count=500k"""
      )
    self.assertTrue(os.access(slapos_wipe_device_disk, os.X_OK))


@skipUnlessKvm
class TestImageDownloadController(FakeImageServerMixin, KVMTestCase):
  __partition_reference__ = 'idc'
  maxDiff = None

  def setUp(self):
    super().setUp()
    self.working_directory = tempfile.mkdtemp()
    self.destination_directory = os.path.join(
      self.working_directory, 'destination')
    os.mkdir(self.destination_directory)
    self.config_json = os.path.join(
      self.working_directory, 'config.json')
    self.md5sum_fail_file = os.path.join(
      self.working_directory, 'md5sum_fail_file')
    self.error_state_file = os.path.join(
      self.working_directory, 'error_state_file')
    self.processed_md5sum = os.path.join(
      self.working_directory, 'processed_md5sum')
    self.image_download_controller = os.path.join(
      self.slap.instance_directory, self.__partition_reference__ + '0',
      'software_release', 'parts', 'image-download-controller',
      'image-download-controller.py')

  def tearDown(self):
    shutil.rmtree(self.working_directory)
    super().tearDown()

  def callImageDownloadController(self, *args):
    call_list = [sys.executable, self.image_download_controller] + list(args)
    try:
      return (0, subprocess.check_output(
        call_list, stderr=subprocess.STDOUT).decode('utf-8'))
    except subprocess.CalledProcessError as e:
      return (e.returncode, e.output.decode('utf-8'))

  def runImageDownloadControlerWithDict(self, json_dict):
    with open(self.config_json, 'w') as fh:
      json.dump(json_dict, fh, indent=2)
    return self.callImageDownloadController(
      self.config_json,
      'curl',  # comes from test environemnt, considered to be recent enough
      self.md5sum_fail_file,
      self.error_state_file,
      self.processed_md5sum
    )

  def assertFileContent(self, path, content):
    self.assertTrue(os.path.exists, path)
    with open(path) as fh:
      self.assertEqual(
        fh.read(),
        content)

  def test(self):
    json_dict = {
      'error-amount': 0,
      'config-md5sum': 'config-md5sum',
      'destination-directory': self.destination_directory,
      'image-list': [
        {
          'destination-tmp': 'tmp',
          'url': self.fake_image,
          'destination': 'destination',
          'image-number': '001',
          'gzipped': False,
          'md5sum': self.fake_image_md5sum,
        }
      ]
    }
    code, result = self.runImageDownloadControlerWithDict(
      json_dict
    )
    self.assertEqual(
      (code, result.strip()),
      (0, """
INF: Storing errors in %(error_state_file)s
INF: %(fake_image)s : Downloading
INF: %(fake_image)s : Stored with checksum %(checksum)s
""".strip() % {
        'fake_image': self.fake_image,
        'checksum': self.fake_image_md5sum,
        'error_state_file': self.error_state_file,
        'destination': os.path.join(self.destination_directory, 'destination'),
      })
    )
    self.assertFileContent(self.md5sum_fail_file, '')
    self.assertFileContent(self.error_state_file, '')
    self.assertFileContent(self.processed_md5sum, 'config-md5sum')
    self.assertFalse(
      os.path.exists(os.path.join(self.destination_directory, 'tmp')))
    self.assertFileContent(
      os.path.join(self.destination_directory, 'destination'),
      'fake_image_content'
    )

    # Nothing happens if all is downloaded
    code, result = self.runImageDownloadControlerWithDict(
      json_dict
    )
    self.assertEqual(
      (code, result.strip()),
      (0, """
INF: Storing errors in %(error_state_file)s
INF: %(fake_image)s : already downloaded
""".strip() % {
        'fake_image': self.fake_image,
        'checksum': self.fake_image_md5sum,
        'error_state_file': self.error_state_file,
        'destination': os.path.join(self.destination_directory, 'destination'),
      })
    )

  def test_fail(self):
    json_dict = {
      'error-amount': 0,
      'config-md5sum': 'config-md5sum',
      'destination-directory': self.destination_directory,
      'image-list': [
        {
          'destination-tmp': 'tmp',
          'url': self.fake_image,
          'destination': 'destination',
          'image-number': '001',
          'gzipped': False,
          'md5sum': self.fake_image_wrong_md5sum,
        }
      ]
    }
    for try_num in range(1, 5):
      code, result = self.runImageDownloadControlerWithDict(
        json_dict
      )
      self.assertEqual(
        (code, result.strip()),
        (1, """
INF: Storing errors in %(error_state_file)s
INF: %(fake_image)s : Downloading
""".  strip() % {
          'fake_image': self.fake_image,
          'error_state_file': self.error_state_file,
          'destination': os.path.join(
            self.destination_directory, 'destination'),
        })
      )
      fake_image_url = '#'.join([
        self.fake_image, self.fake_image_wrong_md5sum])
      self.assertFileContent(
        self.md5sum_fail_file, """{
  "%s": %s
}""" % (fake_image_url, try_num))
      self.assertFileContent(
        self.error_state_file, """
        ERR: %(fake_image)s : MD5 mismatch expected is %(wrong_checksum)s """
        """but got instead %(real_checksum)s""".strip() % {
          'fake_image': self.fake_image,
          'wrong_checksum': self.fake_image_wrong_md5sum,
          'real_checksum': self.fake_image_md5sum,
        })
      self.assertFileContent(self.processed_md5sum, 'config-md5sum')
      self.assertFalse(
        os.path.exists(os.path.join(self.destination_directory, 'tmp')))
      self.assertFalse(
        os.path.exists(
          os.path.join(self.destination_directory, 'destination')))

    code, result = self.runImageDownloadControlerWithDict(
      json_dict
    )
    self.assertEqual(
      (code, result.strip()),
      (1, """
INF: Storing errors in %(error_state_file)s
""".  strip() % {
        'fake_image': self.fake_image,
        'error_state_file': self.error_state_file,
        'destination': os.path.join(
          self.destination_directory, 'destination'),
      })
    )
    fake_image_url = '#'.join([
      self.fake_image, self.fake_image_wrong_md5sum])
    self.assertFileContent(
      self.md5sum_fail_file, """{
  "%s": %s
}""" % (fake_image_url, 4))
    self.assertFileContent(
      self.error_state_file, """
      ERR: %(fake_image)s : Checksum is incorrect after 4 tries, will not """
      """retry""".strip() % {
        'fake_image': self.fake_image,
      })
    self.assertFileContent(self.processed_md5sum, 'config-md5sum')
    self.assertFalse(
      os.path.exists(os.path.join(self.destination_directory, 'tmp')))
    self.assertFalse(
      os.path.exists(
        os.path.join(self.destination_directory, 'destination')))


@skipUnlessKvm
class TestParameterDefault(KVMTestCase, KvmMixin):
  __partition_reference__ = 'pd'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'default'

  def mangleParameterDict(self, parameter_dict):
    return parameter_dict

  def _test(self, parameter_dict, key, value):
    self.rerequestInstance(self.mangleParameterDict(parameter_dict))
    self.waitForInstanceWithPropagation()

    kvm_raw_json = glob.glob(os.path.join(
      self.slap.instance_directory, '*', 'etc', 'kvm_raw.json'))
    self.assertEqual(len(kvm_raw_json), 1)
    with open(kvm_raw_json[0]) as fh:
      kvm_raw_data = json.load(fh)
    self.assertIn(key, kvm_raw_data)
    self.assertEqual(value, kvm_raw_data[key])

  def test_disk_type_default(self):
    self._test({}, "disk-type", "virtio")

  def test_disk_type_set(self):
    self._test({'disk-type': 'ide'}, "disk-type", "ide")

  def test_network_adapter_default(self):
    self._test({}, "network-adapter", "virtio-net-pci")

  def test_network_adapter_set(self):
    self._test({'network-adapter': 'e1000'}, "network-adapter", "e1000")

  def test_cpu_count_default(self):
    self._test({}, "smp-count", "2")

  def test_cpu_count_set(self):
    self._test({'cpu-count': 4}, "smp-count", "4")

  def test_ram_size_default(self):
    self._test({}, "ram-size", "4096")

  def test_ram_size_set(self):
    self._test({'ram-size': 2048}, "ram-size", "2048")


@skipUnlessKvm
class TestParameterResilient(TestParameterDefault):
  __partition_reference__ = 'pr'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'

  def test_cpu_count_set(self):
    self._test({'cpu-count': 4}, "smp-count", 4)

  def test_ram_size_set(self):
    self._test({'ram-size': 2048}, "ram-size", 2048)


@skipUnlessKvm
class TestParameterCluster(TestParameterDefault):
  __partition_reference__ = 'pc'

  parameter_dict = {
    "disable-ansible-promise": True
  }

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      "kvm-partition-dict": {
        "KVM0": cls.parameter_dict
      }
    })}

  def mangleParameterDict(self, parameter_dict):
    local_parameter_dict = self.parameter_dict.copy()
    local_parameter_dict.update(parameter_dict)
    return {
      "kvm-partition-dict": {
        "KVM0": local_parameter_dict
      }
    }

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'


class ExternalDiskMixin(KvmMixin):
  @classmethod
  def _prepareExternalStorageList(cls):
    external_storage_path = os.path.join(cls.working_directory, 'STORAGE')
    os.mkdir(external_storage_path)

    # We already reuse tap from top level partition

    instance_directory = cls.slap.instance_directory

    for partition in os.listdir(instance_directory):
      if not partition.startswith(cls.__partition_reference__):
        continue

      partition_path = os.path.join(instance_directory, partition)

      partition_store_list = []
      for number in range(10):
        storage = os.path.join(external_storage_path, f'data{number}')
        if not os.path.exists(storage):
          os.mkdir(storage)
        partition_store = os.path.join(storage, partition)
        os.mkdir(partition_store)
        partition_store_list.append(partition_store)

      cls._updateSlaposResource(
        partition_path,
        external_storage_list=partition_store_list,
      )

    # above is not enough: the presence of parameter is required in slapos.cfg
    slapos_config = []
    with open(cls.slap._slapos_config) as fh:
      for line in fh.readlines():
        if line.strip() == '[slapos]':
          slapos_config.append('[slapos]\n')
          slapos_config.append(
            f'instance_storage_home = {external_storage_path}\n')
        else:
          slapos_config.append(line)
    with open(cls.slap._slapos_config, 'w') as fh:
      fh.write(''.join(slapos_config))
    # as out of slapos control change applied force reprocessing
    cls.waitForInstanceWithForce()

  @classmethod
  def _dropExternalStorageList(cls):
    slapos_config = []
    with open(cls.slap._slapos_config) as fh:
      for line in fh.readlines():
        if line.startswith("instance_storage_home ="):
          continue
        slapos_config.append(line)
    with open(cls.slap._slapos_config, 'w') as fh:
      fh.write(''.join(slapos_config))
    # as out of slapos control change applied force reprocessing and ignore
    # errors, as test can leave the partitions in inconsistent state
    try:
      cls.waitForInstanceWithForce()
    except SlapOSNodeCommandError:
      pass

  def getRunningDriveList(self, kvm_instance_partition):
    _match_drive = re.compile('.*file.*if=virtio.*').match
    kvm_pid_file_list = glob.glob(os.path.join(
      self.slap._instance_root, '*', 'var', 'run', 'kvm.pid'))
    self.assertEqual(1, len(kvm_pid_file_list))
    with open(kvm_pid_file_list[0]) as fh:
      kvm_pid = int(fh.read().strip())
    drive_list = []
    for entry in psutil.Process(kvm_pid).cmdline():
      m = _match_drive(entry)
      if m:
        path = m.group(0)
        drive_list.append(
          path.replace(kvm_instance_partition, '${partition}')
        )
    return drive_list


class ExternalDiskModernMixin(object):
  __partition_reference__ = 'edm'
  kvm_instance_partition_reference = 'edm0'

  @classmethod
  def setUpClass(cls):
    super().setUpClass()

  @classmethod
  def _setUpClass(cls):
    super()._setUpClass()
    cls.working_directory = tempfile.mkdtemp()
    # setup the external_storage_list, to mimic part of slapformat
    cls._prepareExternalStorageList()
    # re-run the instance, as information has been updated
    cls.waitForInstance()

  @classmethod
  def tearDownClass(cls):
    cls._dropExternalStorageList()
    super().tearDownClass()
    shutil.rmtree(cls.working_directory)

  def getExternalDiskInstanceParameterDict(
    self, first, second, third, update_dict=None):
    parameter_dict = {
      "external-disk": {
          "second disk": {
              "path": second,
              "index": 2,
          },
          "third disk": {
              "path": third,
              "index": 3,
              "cache": "none"
          },
          "first disk": {
              "path": first,
              "index": 1,
              "format": "qcow2"
          },
      }
    }
    if update_dict is not None:
      parameter_dict.update(update_dict)
    return parameter_dict

  def prepareEnv(self):
    # Disks can't be created in /tmp, as it's specially mounted on testnodes
    # and then KVM can't use them:
    # -drive file=/tmp/tmpX/third_disk,if=virtio,cache=none: Could not open
    # '/tmp/tmpX/third_disk': filesystem does not support O_DIRECT
    self.working_directory = tempfile.mkdtemp(dir=self.slap.instance_directory)
    self.addCleanup(shutil.rmtree, self.working_directory)
    self.kvm_instance_partition = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference)
    # find qemu_img from the tested SR via it's partition parameter, as
    # otherwise qemu-kvm would be dependency of test suite
    with open(
      glob.glob(os.path.join(
          self.slap._instance_root, '*', 'etc', 'kvm_raw.json'))[0]) as fh:
      self.qemu_img = json.load(fh)['qemu-img-path']
    self.first_disk = os.path.join(self.working_directory, 'first_disk')
    subprocess.check_call([
      self.qemu_img, "create", "-f", "qcow2", self.first_disk, "1M"])
    self.second_disk_name = 'second_disk'
    self.second_disk = os.path.join(
      self.kvm_instance_partition, self.second_disk_name)
    subprocess.check_call([
      self.qemu_img, "create", "-f", "qcow2", os.path.join(
        self.kvm_instance_partition, self.second_disk), "1M"])
    self.third_disk = os.path.join(self.working_directory, 'third_disk')
    subprocess.check_call([
      self.qemu_img, "create", "-f", "qcow2", self.third_disk, "1M"])
    self.rerequestInstance(
        self.getExternalDiskInstanceParameterDict(
          self.first_disk, self.second_disk_name, self.third_disk))

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'default'


@skipUnlessKvm
class TestExternalDiskModern(
  ExternalDiskModernMixin, KVMTestCase, ExternalDiskMixin):
  def test(self):
    self.prepareEnv()
    self.waitForInstanceWithPropagation()
    drive_list = self.getRunningDriveList(self.kvm_instance_partition)
    self.assertEqual(
      drive_list,
      [
        'node-name=virtual1,file=${partition}/srv/virtual.qcow2,if=virtio,'
        'discard=on,format=qcow2',
        'file={}/first_disk,if=virtio,cache=writeback,format=qcow2'.format(
          self.working_directory),
        'file=${partition}/second_disk,if=virtio,cache=writeback',
        'file={}/third_disk,if=virtio,cache=none'.format(
          self.working_directory)
      ]
    )


@skipUnlessKvm
class TestExternalDiskModernCluster(TestExternalDiskModern):
  kvm_instance_partition_reference = 'edm1'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      "kvm-partition-dict": {
        "kvm-default": {
            "disable-ansible-promise": True,
        }
      }
    })}

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'

  def getExternalDiskInstanceParameterDict(self, *args, **kwargs):
    partition_dict = super().getExternalDiskInstanceParameterDict(
      *args, **kwargs)
    partition_dict.update({"disable-ansible-promise": True})
    return {
      "kvm-partition-dict": {
        "kvm-default": partition_dict
      }
    }


@skipUnlessKvm
class TestExternalDiskModernIndexRequired(KVMTestCase, ExternalDiskMixin):
  __partition_reference__ = 'edm'
  kvm_instance_partition_reference = 'edm0'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'default'

  @classmethod
  def setUpClass(cls):
    super().setUpClass()

  def getExternalDiskInstanceParameterDict(self, first, second, third):
    return {
      "external-disk": {
          "second disk": {
              "path": second,
          },
          "third disk": {
              "path": third,
              "index": 3,
          },
          "first disk": {
              "path": first,
              "index": 1,
          },
      }
    }

  def test(self):
    # Disks can't be created in /tmp, as it's specially mounted on testnodes
    # and then KVM can't use them:
    # -drive file=/tmp/tmpX/third_disk,if=virtio,cache=none: Could not open
    # '/tmp/tmpX/third_disk': filesystem does not support O_DIRECT
    self.working_directory = tempfile.mkdtemp(dir=self.slap.instance_directory)
    self.addCleanup(shutil.rmtree, self.working_directory)
    kvm_instance_partition = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference)
    # find qemu_img from the tested SR via it's partition parameter, as
    # otherwise qemu-kvm would be dependency of test suite
    with open(
      glob.glob(os.path.join(
          self.slap._instance_root, '*', 'etc', 'kvm_raw.json'))[0]) as fh:
      qemu_img = json.load(fh)['qemu-img-path']

    self.first_disk = os.path.join(self.working_directory, 'first_disk')
    subprocess.check_call([
      qemu_img, "create", "-f", "qcow2", self.first_disk, "1M"])
    second_disk = 'second_disk'
    self.second_disk = os.path.join(kvm_instance_partition, second_disk)
    subprocess.check_call([
      qemu_img, "create", "-f", "qcow2", os.path.join(
        kvm_instance_partition, self.second_disk), "1M"])
    self.third_disk = os.path.join(self.working_directory, 'third_disk')
    subprocess.check_call([
      qemu_img, "create", "-f", "qcow2", self.third_disk, "1M"])
    self.rerequestInstance(
        self.getExternalDiskInstanceParameterDict(
          self.first_disk, second_disk, self.third_disk))
    self.raising_waitForInstance(10)


@skipUnlessKvm
class TestInstanceHttpServer(KVMTestCase, KvmMixin):
  __partition_reference__ = 'ihs'
  kvm_instance_partition_reference = 'ihs0'

  @classmethod
  def startHttpServer(cls):
    cls.http_directory = tempfile.mkdtemp()
    server = SocketServer.TCPServer(
      (cls._ipv4_address, findFreeTCPPort(cls._ipv4_address)),
      HttpHandler)

    bootstrap_script = b'bootstrap_script'
    cls.bootstrap_script_md5sum = hashlib.md5(bootstrap_script).hexdigest()
    with open(os.path.join(
      cls.http_directory, cls.bootstrap_script_md5sum), 'wb') as fh:
      fh.write(bootstrap_script)

    url = 'http://%s:%s' % server.server_address
    cls.bootstrap_script_url = '/'.join([url, cls.bootstrap_script_md5sum])

    old_dir = os.path.realpath(os.curdir)
    os.chdir(cls.http_directory)
    try:
      cls.server_process = multiprocessing.Process(
        target=server.serve_forever, name='HttpServer', daemon=True)
      cls.server_process.start()
    finally:
      os.chdir(old_dir)

  @classmethod
  def stopHttpServer(cls):
    cls.logger.debug(f'Stopping process {cls.server_process}')
    cls.server_process.join(10)
    cls.server_process.terminate()
    time.sleep(0.1)
    if cls.server_process.is_alive():
      cls.logger.warning(
        f'Process {cls.server_process} still alive')

    shutil.rmtree(cls.http_directory)

  @classmethod
  def setUpClass(cls):
    try:
      cls.startHttpServer()
      super().setUpClass()
    except BaseException:
      cls.stopHttpServer()
      raise

  @classmethod
  def tearDownClass(cls):
    super().tearDownClass()
    cls.stopHttpServer()

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'enable-http-server': True,
      'bootstrap-script-url': '{}#{}'.format(
        cls.bootstrap_script_url, cls.bootstrap_script_md5sum),
      'data-to-vm': """data
to
vm""",
    })}

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    present_key_list = []
    assert_key_list = [
     'backend-url', 'url', 'monitor-setup-url', 'ipv6-network-info',
     'tap-ipv4', 'tap-ipv6', 'username', 'password']
    for k in assert_key_list:
      if k in connection_parameter_dict:
        present_key_list.append(k)
        connection_parameter_dict.pop(k)
    self.assertEqual(
      connection_parameter_dict,
      {
        'ipv6': self.computer_partition_ipv6_address,
        'monitor-base-url':
        f'https://[{self.computer_partition_ipv6_address}]:8026',
        'nat-rule-port-tcp-22':
        f'{self.computer_partition_ipv6_address} : 10022',
        'nat-rule-port-tcp-443':
        f'{self.computer_partition_ipv6_address} : 10443',
        'nat-rule-port-tcp-80':
        f'{self.computer_partition_ipv6_address} : 10080',
      }
    )
    self.assertEqual(set(present_key_list), set(assert_key_list))
    self.assertEqual(
      """ihs0:6tunnel-10022-{hash}-on-watch RUNNING
ihs0:6tunnel-10080-{hash}-on-watch RUNNING
ihs0:6tunnel-10443-{hash}-on-watch RUNNING
ihs0:boot-image-url-list-updater-{hash} EXITED
ihs0:boot-image-url-select-updater-{hash} EXITED
ihs0:bootstrap-monitor EXITED
ihs0:certificate_authority-{hash}-on-watch RUNNING
ihs0:crond-{hash}-on-watch RUNNING
ihs0:http-server-{hash}-on-watch RUNNING
ihs0:kvm-{kvm-hash-value}-on-watch RUNNING
ihs0:monitor-httpd-{hash}-on-watch RUNNING
ihs0:monitor-httpd-graceful EXITED
ihs0:nginx-graceful EXITED
ihs0:nginx-on-watch RUNNING
ihs0:whitelist-domains-download-{hash} RUNNING
ihs0:whitelist-firewall-{hash} RUNNING""",
      self.getProcessInfo([
        'var/boot-image-url-list/boot-image-url-list.json',
        'var/boot-image-url-select/boot-image-url-select.json'
      ])
    )
    public_dir = os.path.join(
      self.computer_partition_root_path, 'srv', 'public')
    self.assertEqual(
      ['data', 'gateway', 'hostname', 'ipv4',
       'ipv6_config.sh', 'netmask', 'network', 'vm-bootstrap'],
      sorted(os.listdir(public_dir))
    )
    with open(os.path.join(public_dir, 'data')) as fh:
      self.assertEqual("""data
to
vm""", fh.read())
    with open(os.path.join(public_dir, 'vm-bootstrap')) as fh:
      self.assertEqual('bootstrap_script', fh.read())


@skipUnlessKvm
class TestDefaultDiskImageCorruption(KVMTestCase, KvmMixin):
  __partition_reference__ = 'ddic'
  kvm_instance_partition_reference = 'ddic0'

  def _test(self, partition_type):
    image = self.getPartitionPath(partition_type, 'srv', 'virtual.qcow2')
    with open(image, 'w') as fh:
      fh.write('damage')
    partition = self.getPartitionPath(partition_type)
    promise = 'kvm-disk-image-corruption.py'
    output = self.assertPromiseFailsInDir(partition, promise)
    self.assertIn(
      'qemu-img: This image format does not support checks', output)

  def test(self):
    self._test('default')


@skipUnlessKvm
class TestResilientDiskImageCorruption(TestDefaultDiskImageCorruption):
  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'

  def test(self):
    self._test('kvm-export')

  def test_kvm_import(self):
    self._test('kvm-import')

@skipUnlessKvm
class TestKVMMonitoringPropagation(
    MonitoringPropagationTestMixin, KVMTestCase):
  """Verify monitor-interface-url propagation for a standalone KVM instance."""
  __partition_reference__ = 'km'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'monitor-interface-url': cls.MONITOR_INTERFACE_URL,
    })}


@skipUnlessKvm
class TestKVMClusterMonitoringPropagation(
    MonitoringPropagationTestMixin, KVMTestCase):
  """Verify monitor-interface-url propagation for the 'parent' kvm-cluster."""
  __partition_reference__ = 'kcm'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'monitor-interface-url': cls.MONITOR_INTERFACE_URL,
      'kvm-partition-dict': {
        'KVM0': {
          'disable-ansible-promise': True,
        }
      },
    })}

@skipUnlessKvm
class TestKVMResilientMonitoringPropagation(
    MonitoringPropagationTestMixin, KVMTestCase):
  """Verify monitor-interface-url propagation for the kvm-resilient."""
  __partition_reference__ = 'krm'
  instance_max_retry = 20

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'monitor-interface-url': cls.MONITOR_INTERFACE_URL,
    })}

  @classmethod
  def waitForInstance(cls):
    # First pass: parent runs child partition requests.
    # Second pass: children run their buildout and set their monitoring params.
    for _ in range(2):
      super().waitForInstance()