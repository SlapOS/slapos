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

from slapos.qemuqmpclient import QemuQMPWrapper
from slapos.proxy.db_version import DB_VERSION
from slapos.recipe.librecipe import generateHashFromFiles
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.slap.standalone import SlapOSNodeCommandError
from slapos.testing.utils import findFreeTCPPort

has_kvm = os.access('/dev/kvm', os.R_OK | os.W_OK)
skipUnlessKvm = unittest.skipUnless(has_kvm, 'kvm not loaded or not allowed')

if has_kvm:
  setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.join(os.path.dirname(__file__), 'test-software.cfg'))
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
    "slave-frontend": {
        "slave-frontend-dict": {}
    },
    "authorized-keys": [
        "ssh-rsa %s key_one" % ("A" * 372),
        "ssh-rsa %s key_two" % ("B" * 372),
        "ssh-rsa %s key_three" % ("C" * 372)
    ],
    "fw-restricted-access": "off",
    "fw-authorized-sources": [],
    "fw-reject-sources": ["10.32.0.0/13"]
}

bootstrap_machine_param_dict = {
    "computer-guid": "local",
    "disable-ansible-promise": True,
    "state": "started",
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
    "enable-vhost": True,
    "external-disk-number": 1,
    "external-disk-size": 100,
    "external-disk-format": "qcow2",
    "enable-monitor": True,
    "keyboard-layout-language": "fr"
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
    with self.slap.instance_supervisor_rpc as instance_supervisor:
      kvm_pid = next(q for q in instance_supervisor.getAllProcessInfo()
                     if 'kvm-' in q['name'])['pid']
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
  def assertPromiseFails(self, promise):
    partition_directory = os.path.join(
      self.slap.instance_directory,
      self.kvm_instance_partition_reference)
    monitor_run_promise = os.path.join(
      partition_directory, 'software_release', 'bin',
      'monitor.runpromise'
    )
    monitor_configuration = os.path.join(
      partition_directory, 'etc', 'monitor.conf')

    self.assertNotEqual(
      0,
      subprocess.call([
        monitor_run_promise, '-c', monitor_configuration, '-a', '-f',
        '--run-only', promise])
    )

  @classmethod
  def getPartitionId(cls, instance_type):
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
      cls.slap._instance_root, cls.getPartitionId(instance_type), *paths)

  @classmethod
  def getBackupPartitionPath(cls, *paths):
    return cls.getPartitionPath(
      'kvm-export', 'srv', 'backup', 'kvm',
      cls.disk_type_backup_mapping[cls.disk_type], *paths)

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
       os.path.join(kvm_partition, 'bin', 'kvm_raw')
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
        partition_parameter_kw=parameter_dict,
        state=state)


class KvmMixinJson:
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      '_': json.dumps(super().getInstanceParameterDict())}

  def rerequestInstance(self, parameter_dict=None, *args, **kwargs):
    if parameter_dict is None:
      parameter_dict = {}
    return super().rerequestInstance(
      parameter_dict={'_': json.dumps(parameter_dict)},
      *args, **kwargs
    )


@skipUnlessKvm
class TestInstance(KVMTestCase, KvmMixin):
  __partition_reference__ = 'i'
  kvm_instance_partition_reference = 'i0'

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    present_key_list = []
    assert_key_list = [
     'backend-url', 'url', 'monitor-setup-url', 'ipv6-network-info',
     'tap-ipv4', 'tap-ipv6']
    for k in assert_key_list:
      if k in connection_parameter_dict:
        present_key_list.append(k)
        connection_parameter_dict.pop(k)
    self.assertEqual(
      connection_parameter_dict,
      {
        'ipv6': self.computer_partition_ipv6_address,
        'maximum-extra-disk-amount': '0',
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
i0:kvm_controller EXITED
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
      [
        '${inst}/srv/boot-image-url-select-repository/'
        '326b7737c4262e8eb09cd26773f3356a'
      ],
      self.getRunningImageList()
    )


@skipUnlessKvm
class TestInstanceJson(
  KvmMixinJson, TestInstance):
  pass


@skipUnlessKvm
class TestMemoryManagement(KVMTestCase, KvmMixin):
  __partition_reference__ = 'i'
  kvm_instance_partition_reference = 'i0'

  def getKvmProcessInfo(self, switch_list):
    return_list = []
    with self.slap.instance_supervisor_rpc as instance_supervisor:
      kvm_pid = [q for q in instance_supervisor.getAllProcessInfo()
                 if 'kvm-' in q['name']][0]['pid']
      kvm_process = psutil.Process(kvm_pid)
      get_next = False
      for entry in kvm_process.cmdline():
        if get_next:
          return_list.append(entry)
          get_next = False
        elif entry in switch_list:
          get_next = True
    return kvm_pid, return_list

  def test(self):
    kvm_pid_1, info_list = self.getKvmProcessInfo(['-smp', '-m'])
    self.assertEqual(
      ['2,maxcpus=3', '4096M,slots=128,maxmem=4608M'],
      info_list
    )
    self.rerequestInstance({
      'ram-size': '1536',
      'cpu-count': '2',
    })
    self.slap.waitForInstance(max_retry=10)
    kvm_pid_2, info_list = self.getKvmProcessInfo(['-smp', '-m'])
    self.assertEqual(
      ['2,maxcpus=3', '1536M,slots=128,maxmem=2048M'],
      info_list
    )

    # assert that process was restarted
    self.assertNotEqual(kvm_pid_1, kvm_pid_2, "Unexpected: KVM not restarted")

  def tearDown(self):
    self.rerequestInstance()
    self.slap.waitForInstance(max_retry=10)

  def test_enable_device_hotplug(self):
    def getHotpluggedCpuRamValue():
      qemu_wrapper = QemuQMPWrapper(os.path.join(
        self.computer_partition_root_path, 'var', 'qmp_socket'))
      ram_mb = sum(
        q['size']
        for q in qemu_wrapper.getMemoryInfo()['hotplugged']) / 1024 / 1024
      cpu_count = len(
        [q['CPU'] for q in qemu_wrapper.getCPUInfo()['hotplugged']])
      return {'cpu_count': cpu_count, 'ram_mb': ram_mb}

    kvm_pid_1, info_list = self.getKvmProcessInfo(['-smp', '-m'])
    self.assertEqual(
      ['2,maxcpus=3', '4096M,slots=128,maxmem=4608M'],
      info_list
    )
    self.assertEqual(
      getHotpluggedCpuRamValue(),
      {'cpu_count': 0, 'ram_mb': 0}
    )

    parameter_dict = {
      'enable-device-hotplug': 'true',
      # to avoid restarts the max RAM and CPU has to be static
      'ram-max-size': '8192',
      'cpu-max-count': '6',
    }
    self.rerequestInstance(parameter_dict)
    self.slap.waitForInstance(max_retry=2)
    kvm_pid_2, info_list = self.getKvmProcessInfo(['-smp', '-m'])

    self.assertEqual(
      ['2,maxcpus=6', '4096M,slots=128,maxmem=8192M'],
      info_list
    )
    self.assertEqual(
      getHotpluggedCpuRamValue(),
      {'cpu_count': 0, 'ram_mb': 0}
    )
    self.assertNotEqual(kvm_pid_1, kvm_pid_2, "Unexpected: KVM not restarted")
    parameter_dict.update(**{
      'ram-size': '5120',
      'cpu-count': '4'
    })
    self.rerequestInstance(parameter_dict)
    self.slap.waitForInstance(max_retry=10)
    kvm_pid_3, info_list = self.getKvmProcessInfo(['-smp', '-m'])

    self.assertEqual(
      ['2,maxcpus=6', '4096M,slots=128,maxmem=8192M'],
      info_list
    )
    self.assertEqual(kvm_pid_2, kvm_pid_3, "Unexpected: KVM restarted")
    self.assertEqual(
      getHotpluggedCpuRamValue(),
      {'cpu_count': 2, 'ram_mb': 1024}
    )


@skipUnlessKvm
class TestMemoryManagementJson(KvmMixinJson, TestMemoryManagement):
  pass


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
      connection_dict = json.loads(slapos.util.xml2dict(connection_xml)['_'])
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
    result = requests.get(connection_parameter_dict['url'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)
    self.assertNotIn('url-additional', connection_parameter_dict)


@skipUnlessKvm
class TestAccessDefaultJson(KvmMixinJson, TestAccessDefault):
  pass


@skipUnlessKvm
class TestAccessDefaultAdditional(MonitorAccessMixin, KVMTestCase):
  __partition_reference__ = 'ada'
  kvm_instance_partition_reference = 'ada0'
  expected_partition_with_monitor_base_url_count = 1

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'frontend-additional-instance-guid': 'SOMETHING'
    }

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()

    result = requests.get(connection_parameter_dict['url'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)

    result = requests.get(
      connection_parameter_dict['url-additional'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)

@skipUnlessKvm
class TestAccessDefaultAdditionalJson(TestAccessDefaultAdditional):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'frontend-additional-software-url': 'http://git.erp5.org/gitweb/slapos.git/blob_plain/HEAD:/software/apache-frontend/software.cfg'
    }

@skipUnlessKvm
class TestAccessDefaultAdditionalJson(
  KvmMixinJson, TestAccessDefaultAdditional):
  pass


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

    result = requests.get(connection_parameter_dict['url'], verify=False)
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
    result = requests.get(connection_parameter_dict['KVM0-url'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)
    self.assertNotIn('KVM0-url-additional', connection_parameter_dict)


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
    result = requests.get(connection_parameter_dict['KVM0-url'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)

    result = requests.get(
      connection_parameter_dict['KVM0-url-additional'], verify=False)
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
      "kvm-partition-dict": {
          "test-machine1": bootstrap_machine_param_dict,
          "test-machine2": dict(bootstrap_machine_param_dict, **{
              "virtual-hard-drive-url":
              "http://shacache.org/shacache/5bdc95ea3f8ca40ff4fb8d086776e393"
              "87a68e91f76b1a5f883dfc33fa13cf1ee71c7d218a4e9401f56519a352791"
              "272ada4a5c334b3ca38a32c0bcacb6838e2",
              "virtual-hard-drive-md5sum": "deaf751a31dd6aec320d67c75c88c2e1",
              "virtual-hard-drive-gzipped": True,
          })
      }
    }))}

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    result = requests.get(
      connection_parameter_dict['test-machine1-url'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)
    result = requests.get(
      connection_parameter_dict['test-machine2-url'], verify=False)
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
          'kvm-export', 'var', 'cron-environment.json')) as fh:
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
  disk_type_backup_mapping = {
    'virtio': 'virtio0',
    'ide': 'ide0-hd0',
  }

  @classmethod
  def getInstanceParameterDict(cls):
    parameter_dict = {}
    if cls.disk_type != 'virtio':
      parameter_dict['disk-type'] = cls.disk_type
    return parameter_dict

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
      self.importer_partition, 'srv', 'backup', 'kvm',
      self.disk_type_backup_mapping[self.disk_type])
    # sanity check - no export/import happened yet
    self.assertFalse(os.path.exists(self.getBackupPartitionPath()))
    self.call_exporter()

    equeue_log = awaitBackup(equeue_file)
    self.assertNotIn('qemu-img rebase', equeue_log)
    self.assertEqual(
      os.listdir(self.getBackupPartitionPath()),
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
      os.listdir(self.getBackupPartitionPath()),
      os.listdir(destination_backup)
    )
    self.assertTrue(os.path.exists(destination_qcow2))
    # takeover
    connection_parameter = self.computer_partition.getConnectionParameterDict()
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
    self.assertIn(
      'Post take-over cleanup',
      status_text
    )
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
        'backup', 'proof.signature', 'virtual.qcow2', 'sshkeys', 'backup.diff'
        ,'monitor', 'cgi-bin', 'passwd', 'ssl', 'equeue.db'])
    )

  def initialBackup(self):
    status_text = self.call_exporter()
    equeue_file = self.getPartitionPath(
      'kvm-import', 'var', 'log', 'equeue.log')
    # clean up equeue file for precise assertion
    with open(equeue_file, 'w') as fh:
      fh.write('')
    awaitBackup(equeue_file)
    self.assertEqual(
      len(glob.glob(self.getBackupPartitionPath('FULL-*.qcow2'))),
      1)
    self.assertEqual(
      len(glob.glob(self.getBackupPartitionPath('INC-*.qcow2'))),
      0)
    self.assertNotIn(
      'Recovered from partial backup by removing partial',
      status_text
    )
    self.assertNotIn(
      'Recovered from empty backup',
      status_text
    )
    self.assertNotIn(
      'Post take-over cleanup',
      status_text
    )
    self.assertImported()


@skipUnlessKvm
class TestInstanceResilientBackupExporter(
  TestInstanceResilientBackupExporterMixin, KVMTestCase):
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
class TestInstanceResilientBackupExporterPartialRecovery(
  TestInstanceResilientBackupExporterMixin, KVMTestCase):
  def test(self):
    self.initialBackup()
    # cover .partial file in the backup directory with fallback to full
    current_backup = glob.glob(self.getBackupPartitionPath('FULL-*'))[0]
    with open(current_backup + '.partial', 'w') as fh:
      fh.write('')
    status_text = self.call_exporter()
    self.assertEqual(
      len(glob.glob(self.getBackupPartitionPath('FULL-*.qcow2'))),
      1)
    self.assertEqual(
      len(glob.glob(self.getBackupPartitionPath('INC-*.qcow2'))),
      1)
    self.assertIn(
      'Recovered from partial backup by removing partial',
      status_text
    )
    self.assertTrue(os.path.exists(os.path.join(
      self.getPartitionPath(
        'kvm-export', 'etc', 'plugin', 'check-backup-directory.py'))))


@skipUnlessKvm
class TestInstanceResilientBackupExporterEmptyRecovery(
  TestInstanceResilientBackupExporterMixin, KVMTestCase):
  def test(self):
    self.initialBackup()
    # cover empty backup recovery
    current_backup_list = glob.glob(self.getBackupPartitionPath('*.qcow2'))
    self.assertEqual(
      1,
      len(current_backup_list)
    )
    for file in current_backup_list:
      os.unlink(file)
    status_text = self.call_exporter()
    self.assertEqual(
      len(glob.glob(self.getBackupPartitionPath('FULL-*.qcow2'))),
      1)
    self.assertEqual(
      len(glob.glob(self.getBackupPartitionPath('INC-*.qcow2'))),
      0)
    self.assertIn(
      'Recovered from empty backup',
      status_text
    )


@skipUnlessKvm
class TestInstanceResilientBackupExporterIde(
  TestInstanceResilientBackupExporter):
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
class TestInstanceResilient(KVMTestCase, KvmMixin):
  __partition_reference__ = 'ir'
  kvm_instance_partition_reference = 'ir0'
  instance_max_retry = 20

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls.pbs1_ipv6 = cls.getPartitionIPv6(cls.getPartitionId('PBS (kvm / 1)'))
    cls.kvm_instance_partition_reference = cls.getPartitionId('kvm0')
    cls.kvm0_ipv6 = cls.getPartitionIPv6(cls.kvm_instance_partition_reference)
    cls.kvm1_ipv6 = cls.getPartitionIPv6(cls.getPartitionId('kvm1'))

  def test(self):
    connection_parameter_dict = self\
      .computer_partition.getConnectionParameterDict()
    present_key_list = []
    assert_key_list = [
     'monitor-password', 'takeover-kvm-1-password', 'backend-url', 'url',
     'monitor-setup-url', 'ipv6-network-info']
    for k in assert_key_list:
      if k in connection_parameter_dict:
        present_key_list.append(k)
        connection_parameter_dict.pop(k)
    self.assertIn('feed-url-kvm-1-pull', connection_parameter_dict)
    feed_pull = connection_parameter_dict.pop('feed-url-kvm-1-pull')
    self.assertRegex(
      feed_pull,
      'http://\\[{}\\]:[0-9][0-9][0-9][0-9]/get/local-ir0-kvm-1-pull'.format(
        self.pbs1_ipv6))
    feed_push = connection_parameter_dict.pop('feed-url-kvm-1-push')
    self.assertRegex(
      feed_push,
      'http://\\[{}\\]:[0-9][0-9][0-9][0-9]/get/local-ir0-kvm-1-push'.format(
        self.pbs1_ipv6))
    self.assertEqual(
      connection_parameter_dict,
      {
        'ipv6': self.kvm0_ipv6,
        'monitor-base-url':
        f'https://[{self.computer_partition_ipv6_address}]:8160',
        'monitor-user': 'admin',
        'takeover-kvm-1-url': f'http://[{self.kvm1_ipv6}]:9263/',
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
ir2:6tunnel-10022-{hash}-on-watch RUNNING
ir2:6tunnel-10080-{hash}-on-watch RUNNING
ir2:6tunnel-10443-{hash}-on-watch RUNNING
ir2:boot-image-url-list-updater-{hash} EXITED
ir2:boot-image-url-select-updater-{hash} EXITED
ir2:bootstrap-monitor EXITED
ir2:certificate_authority-{hash}-on-watch RUNNING
ir2:crond-{hash}-on-watch RUNNING
ir2:equeue-on-watch RUNNING
ir2:kvm-{kvm-hash-value}-on-watch RUNNING
ir2:kvm_controller EXITED
ir2:monitor-httpd-{hash}-on-watch RUNNING
ir2:monitor-httpd-graceful EXITED
ir2:nginx-graceful EXITED
ir2:nginx-on-watch RUNNING
ir2:notifier-on-watch RUNNING
ir2:resilient_sshkeys_authority-on-watch RUNNING
ir2:sshd-graceful EXITED
ir2:sshd-on-watch RUNNING
ir2:whitelist-domains-download-{hash} RUNNING
ir2:whitelist-firewall-{hash} RUNNING
ir3:bootstrap-monitor EXITED
ir3:certificate_authority-{hash}-on-watch RUNNING
ir3:crond-{hash}-on-watch RUNNING
ir3:equeue-on-watch RUNNING
ir3:monitor-httpd-{hash}-on-watch RUNNING
ir3:monitor-httpd-graceful EXITED
ir3:notifier-on-watch RUNNING
ir3:resilient-web-takeover-httpd-on-watch RUNNING
ir3:resilient_sshkeys_authority-on-watch RUNNING
ir3:sshd-graceful EXITED
ir3:sshd-on-watch RUNNING""",
      self.getProcessInfo([
        'var/boot-image-url-list/boot-image-url-list.json',
        'var/boot-image-url-select/boot-image-url-select.json'
      ])
    )


@skipUnlessKvm
class TestInstanceResilientJson(
  KvmMixinJson, TestInstanceResilient):
  pass


@skipUnlessKvm
class TestInstanceResilientDiskTypeIde(KVMTestCase, KvmMixin):
  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'disk-type': 'ide'
    }


@skipUnlessKvm
class TestInstanceResilientDiskTypeIdeJson(
  KvmMixinJson, TestInstanceResilientDiskTypeIde):
  pass


@skipUnlessKvm
class TestAccessResilientAdditional(KVMTestCase):
  __partition_reference__ = 'ara'
  kvm_instance_partition_reference = 'ara0'
  expected_partition_with_monitor_base_url_count = 1

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'frontend-additional-instance-guid': 'SOMETHING'
    }

  def test(self):
    connection_parameter_dict = self.computer_partition\
      .getConnectionParameterDict()

    result = requests.get(connection_parameter_dict['url'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)

    result = requests.get(
      connection_parameter_dict['url-additional'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)


@skipUnlessKvm
class TestAccessResilientAdditionalJson(
  KvmMixinJson, TestAccessResilientAdditional):
  pass


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
    return {
      "virtual-hard-drive-url": cls.real_image,
      "virtual-hard-drive-md5sum": cls.real_image_md5sum
    }

  def test(self):
    kvm_partition = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference)
    image_repository = os.path.join(
      kvm_partition,
      'srv', 'virtual-hard-drive-url-repository')
    self.assertEqual(
      [self.getInstanceParameterDict()['virtual-hard-drive-md5sum']],
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
    return {
      "virtual-hard-drive-url": cls.real_gzip,
      "virtual-hard-drive-md5sum": cls.real_gzip_md5sum,
      "virtual-hard-drive-gzipped": True
    }


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
    return {
      cls.key: cls.test_input % (
        cls.fake_image, cls.fake_image_md5sum, cls.fake_image2,
        cls.fake_image2_md5sum)
    }

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
      [
        '${inst}/srv/boot-image-url-select-repository/'
        '326b7737c4262e8eb09cd26773f3356a'
      ],
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
class TestBootImageUrlListJson(
  KvmMixinJson, TestBootImageUrlList):
  pass


@skipUnlessKvm
class TestBootImageUrlListResilient(TestBootImageUrlList):
  kvm_instance_partition_reference = 'biul2'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'


@skipUnlessKvm
class TestBootImageUrlListResilientJson(
  KvmMixinJson, TestBootImageUrlListResilient):
  pass


@skipUnlessKvm
class TestBootImageUrlSelect(FakeImageServerMixin, KVMTestCase):
  __partition_reference__ = 'bius'
  kvm_instance_partition_reference = 'bius0'

  config_state_promise = 'boot-image-url-select-config-state-promise.py'

  def test(self):
    # check the default image
    image_repository = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference,
      'srv', 'boot-image-url-select-repository')
    self.assertEqual(
      ['326b7737c4262e8eb09cd26773f3356a'],
      os.listdir(image_repository)
    )
    image = os.path.join(image_repository, '326b7737c4262e8eb09cd26773f3356a')
    self.assertTrue(os.path.exists(image))
    with open(image, 'rb') as fh:
      image_md5sum = hashlib.md5(fh.read()).hexdigest()
    self.assertEqual(image_md5sum, '326b7737c4262e8eb09cd26773f3356a')
    self.assertEqual(
      [
        '${inst}/srv/boot-image-url-select-repository/'
        '326b7737c4262e8eb09cd26773f3356a'
      ],
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
    if self.getInstanceSoftwareType() == 'kvm-resilient':
      self.waitForInstance()
    self.raising_waitForInstance(3)
    self.assertPromiseFails(self.config_state_promise)

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
      ['326b7737c4262e8eb09cd26773f3356a']
    )
    self.assertEqual(
      os.listdir(os.path.join(
        kvm_instance_partition, 'srv', 'boot-image-url-list-repository')),
      []
    )

    # again only default image is available in the running process
    self.assertEqual(
      [
        '${inst}/srv/boot-image-url-select-repository/'
        '326b7737c4262e8eb09cd26773f3356a'
      ],
      self.getRunningImageList()
    )


@skipUnlessKvm
class TestBootImageUrlSelectJson(
  KvmMixinJson, TestBootImageUrlSelect):
  pass


@skipUnlessKvm
class TestBootImageUrlSelectResilient(TestBootImageUrlSelect):
  kvm_instance_partition_reference = 'bius2'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'


@skipUnlessKvm
class TestBootImageUrlSelectResilientJson(
  KvmMixinJson, TestBootImageUrlSelectResilient):
  pass


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
        },
        "KVM1": {
            "disable-ansible-promise": True,
        }
      }
    })}

  def test(self):
    # Note: As there is no way to introspect nicely where partition landed
    #       we assume ordering of the cluster requests
    self.rerequestInstance({'_': json.dumps({
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
    })})
    self.waitForInstanceWithPropagation()
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
        },
        "KVM1": {
            "disable-ansible-promise": True,
        }
      }
    })}

  def test(self):
    # Note: As there is no way to introspect nicely where partition landed
    #       we assume ordering of the cluster requests
    self.rerequestInstance({'_': json.dumps({
      "kvm-partition-dict": {
        "KVM0": {
            "disable-ansible-promise": True,
            "boot-image-url-select": "Debian Bullseye 11 netinst x86_64"
        },
        "KVM1": {
            "disable-ansible-promise": True,
            "boot-image-url-select": "Debian Bookworm 12 netinst x86_64"
        }
      }
    })})
    self.waitForInstanceWithPropagation()
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
      self.assertEqual(
        '["https://shacache.nxdcdn.com/33c08e56c83d13007e4a5511b9bf2c4926c4aa'
        '12fd5dd56d493c0653aecbab380988c5bf1671dbaea75c582827797d98c4a611f7fb'
        '2b131fbde2c677d5258ec9#326b7737c4262e8eb09cd26773f3356a"]',
        fh.read().strip()
      )


@skipUnlessKvm
class TestNatRules(KvmMixin, KVMTestCase):
  __partition_reference__ = 'nr'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'nat-rules': '100 200',
    }

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
class TestNatRulesJson(
  KvmMixinJson, TestNatRules):
  pass


@skipUnlessKvm
class TestNatRulesKvmCluster(KVMTestCase):
  __partition_reference__ = 'nrkc'

  nat_rules = ["100", "200", "300"]

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
    with self.slap.instance_supervisor_rpc as instance_supervisor:
      kvm_pid = [q for q in instance_supervisor.getAllProcessInfo()
                 if 'kvm-' in q['name']][0]['pid']
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
class TestNatRulesKvmClusterComplex(TestNatRulesKvmCluster):
  __partition_reference__ = 'nrkcc'
  nat_rules = ["100", "200 300"]


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
class TestWhitelistFirewallJson(
  KvmMixinJson, TestWhitelistFirewall):
  pass


@skipUnlessKvm
class TestWhitelistFirewallRequest(TestWhitelistFirewall):
  whitelist_domains = '2.2.2.2 3.3.3.3\n4.4.4.4'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'whitelist-domains': cls.whitelist_domains,
    }

  def test(self):
    super().test()
    self.assertIn('2.2.2.2', self.content_json)
    self.assertIn('3.3.3.3', self.content_json)
    self.assertIn('4.4.4.4', self.content_json)


@skipUnlessKvm
class TestWhitelistFirewallRequestJson(
  KvmMixinJson, TestWhitelistFirewallRequest):
  pass


@skipUnlessKvm
class TestWhitelistFirewallResilient(TestWhitelistFirewall):
  kvm_instance_partition_reference = 'wf2'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'


@skipUnlessKvm
class TestWhitelistFirewallResilientJson(
  KvmMixinJson, TestWhitelistFirewallResilient):
  pass


@skipUnlessKvm
class TestWhitelistFirewallRequestResilient(TestWhitelistFirewallRequest):
  kvm_instance_partition_reference = 'wf2'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'


@skipUnlessKvm
class TestWhitelistFirewallRequestResilientJson(
  KvmMixinJson, TestWhitelistFirewallRequestResilient):
  pass


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
class TestDiskDevicePathWipeDiskOndestroyJson(
  KvmMixinJson, TestDiskDevicePathWipeDiskOndestroy):
  pass


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

  def _test(self, parameter_dict, expected):
    self.rerequestInstance(self.mangleParameterDict(parameter_dict))
    self.waitForInstanceWithPropagation()

    kvm_raw = glob.glob(os.path.join(
      self.slap.instance_directory, '*', 'bin', 'kvm_raw'))
    self.assertEqual(len(kvm_raw), 1)
    kvm_raw = kvm_raw[0]
    with open(kvm_raw) as fh:
      kvm_raw = fh.read()
    self.assertIn(expected, kvm_raw)

  def test_disk_type_default(self):
    self._test({}, "disk_type = 'virtio'")

  def test_disk_type_set(self):
    self._test({'disk-type': 'ide'}, "disk_type = 'ide'")

  def test_network_adapter_default(self):
    self._test({}, "network_adapter = 'virtio-net-pci")

  def test_network_adapter_set(self):
    self._test({'network-adapter': 'e1000'}, "network_adapter = 'e1000'")

  def test_cpu_count_default(self):
    self._test({}, "init_smp_count = 2")

  def test_cpu_count_default_max(self):
    self._test({}, "smp_max_count = 3")

  def test_cpu_count_set(self):
    self._test({'cpu-count': 4}, "init_smp_count = 4")

  def test_cpu_count_set_max(self):
    self._test({'cpu-count': 4}, "smp_max_count = 5")

  def test_ram_size_default(self):
    self._test({}, "init_ram_size = 4096")

  def test_ram_size_default_max(self):
    self._test({}, "ram_max_size = '4608'")

  def test_ram_size_set(self):
    self._test({'ram-size': 2048}, "init_ram_size = 2048")

  def test_ram_size_set_max(self):
    self._test({'ram-size': 2048}, "ram_max_size = '2560'")


@skipUnlessKvm
class TestParameterDefaultJson(
  KvmMixinJson, TestParameterDefault):
  pass


@skipUnlessKvm
class TestParameterResilient(TestParameterDefault):
  __partition_reference__ = 'pr'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'


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
    local_parameter_dict = self.getInstanceParameterDict().copy()
    local_parameter_dict.update(parameter_dict)
    return {'_': json.dumps({
      "kvm-partition-dict": {
        "KVM0": local_parameter_dict
      }
    })}

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
    _match_drive = re.compile('file.*if=virtio.*').match
    with self.slap.instance_supervisor_rpc as instance_supervisor:
      kvm_pid = next(q for q in instance_supervisor.getAllProcessInfo()
                     if 'kvm-' in q['name'])['pid']
    drive_list = []
    for entry in psutil.Process(kvm_pid).cmdline():
      m = _match_drive(entry)
      if m:
        path = m.group(0)
        drive_list.append(
          path.replace(kvm_instance_partition, '${partition}')
        )
    return drive_list


@skipUnlessKvm
class TestExternalDisk(KVMTestCase, ExternalDiskMixin):
  __partition_reference__ = 'ed'
  kvm_instance_partition_reference = 'ed0'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'default'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'external-disk-number': 2,
      'external-disk-size': 1
    }

  @classmethod
  def _setUpClass(cls):
    super()._setUpClass()
    cls.working_directory = tempfile.mkdtemp()
    # setup the external_storage_list, to mimic part of slapformat
    cls._prepareExternalStorageList()

  @classmethod
  def tearDownClass(cls):
    cls._dropExternalStorageList()
    super().tearDownClass()
    shutil.rmtree(cls.working_directory)

  def test(self):
    kvm_instance_partition = os.path.join(
      self.slap.instance_directory, self.kvm_instance_partition_reference)
    drive_list = self.getRunningDriveList(kvm_instance_partition)

    # Note: Do to unknown set of drives it's impossible to directly check
    #       drive paths, thus the count is important
    self.assertEqual(
      1 + 2,  # 1 the default drive, 2 additional ones
      len(drive_list)
    )

    # restart the VM
    self.requestDefaultInstance(state='stopped')
    self.waitForInstance()
    self.requestDefaultInstance(state='started')
    self.waitForInstance()
    restarted_drive_list = self.getRunningDriveList(kvm_instance_partition)
    self.assertEqual(drive_list, restarted_drive_list)
    # prove that even on resetting parameters, drives are still there
    self.rerequestInstance(state='stopped')
    self.waitForInstance()
    self.rerequestInstance()
    self.waitForInstance()
    dropped_drive_list = self.getRunningDriveList(kvm_instance_partition)
    self.assertEqual(drive_list, dropped_drive_list)


@skipUnlessKvm
class TestExternalDiskJson(
  KvmMixinJson, TestExternalDisk):
  pass


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
              "format": "qcow"
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
          self.slap._instance_root, '*', 'bin', 'kvm_raw'))[0]) as fh:
      self.qemu_img = [
        q for q in fh.readlines()
        if 'qemu_img_path = ' in q][0].split()[-1].replace("'", "")
    self.first_disk = os.path.join(self.working_directory, 'first_disk')
    subprocess.check_call([
      self.qemu_img, "create", "-f", "qcow", self.first_disk, "1M"])
    self.second_disk_name = 'second_disk'
    self.second_disk = os.path.join(
      self.kvm_instance_partition, self.second_disk_name)
    subprocess.check_call([
      self.qemu_img, "create", "-f", "qcow2", os.path.join(
        self.kvm_instance_partition, self.second_disk), "1M"])
    self.third_disk = os.path.join(self.working_directory, 'third_disk')
    subprocess.check_call([
      self.qemu_img, "create", "-f", "qcow2", self.third_disk, "1M"])
    self.rerequestInstance({'_': json.dumps(
        self.getExternalDiskInstanceParameterDict(
          self.first_disk, self.second_disk_name, self.third_disk))})

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
        'file=${partition}/srv/virtual.qcow2,if=virtio,discard=on,'
        'format=qcow2',
        'file={}/first_disk,if=virtio,cache=writeback,format=qcow'.format(
          self.working_directory),
        'file=${partition}/second_disk,if=virtio,cache=writeback',
        'file={}/third_disk,if=virtio,cache=none'.format(
          self.working_directory)
      ]
    )


@skipUnlessKvm
class TestExternalDiskModernConflictAssurance(
  ExternalDiskModernMixin, KVMTestCase, ExternalDiskMixin):
  def test(self):
    self.prepareEnv()
    # Create conflicting configuration
    parameter_dict = {
      "external-disk-number": 1,
      "external-disk-size": 10,
      "external-disk-format": "qcow2",
    }
    self.rerequestInstance({'_': json.dumps(parameter_dict)})
    self.waitForInstance()
    data_disk_ids = os.path.join(
      self.kvm_instance_partition, 'etc', '.data-disk-ids')
    data_disk_amount = os.path.join(
      self.kvm_instance_partition, 'etc', '.data-disk-amount')
    self.assertTrue(os.path.exists(data_disk_ids))
    self.assertTrue(os.path.exists(data_disk_amount))
    with open(data_disk_amount) as fh:
      self.assertEqual(1, int(fh.read()))
    parameter_dict.update(self.getExternalDiskInstanceParameterDict(
      self.first_disk, self.second_disk_name, self.third_disk))
    parameter_dict["external-disk-number"] = 0
    # assert mutual exclusivity of old and modern
    self.rerequestInstance({'_': json.dumps(parameter_dict)})
    self.raising_waitForInstance(3)
    # Fix the situation
    with open(data_disk_amount, 'w') as fh:
      fh.write("0")
    self.waitForInstance()


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
          self.slap._instance_root, '*', 'bin', 'kvm_raw'))[0]) as fh:
      qemu_img = [
        q for q in fh.readlines()
        if 'qemu_img_path = ' in q][0].split()[-1].replace("'", "")

    self.first_disk = os.path.join(self.working_directory, 'first_disk')
    subprocess.check_call([
      qemu_img, "create", "-f", "qcow", self.first_disk, "1M"])
    second_disk = 'second_disk'
    self.second_disk = os.path.join(kvm_instance_partition, second_disk)
    subprocess.check_call([
      qemu_img, "create", "-f", "qcow2", os.path.join(
        kvm_instance_partition, self.second_disk), "1M"])
    self.third_disk = os.path.join(self.working_directory, 'third_disk')
    subprocess.check_call([
      qemu_img, "create", "-f", "qcow2", self.third_disk, "1M"])
    self.rerequestInstance({'_': json.dumps(
        self.getExternalDiskInstanceParameterDict(
          self.first_disk, second_disk, self.third_disk))})
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
    return {
      'enable-http-server': True,
      'bootstrap-script-url': '{}#{}'.format(
        cls.bootstrap_script_url, cls.bootstrap_script_md5sum),
      'data-to-vm': """data
to
vm""",
    }

  def test(self):
    connection_parameter_dict = self.getConnectionParameterDictJson()
    present_key_list = []
    assert_key_list = [
     'backend-url', 'url', 'monitor-setup-url', 'ipv6-network-info',
     'tap-ipv4', 'tap-ipv6']
    for k in assert_key_list:
      if k in connection_parameter_dict:
        present_key_list.append(k)
        connection_parameter_dict.pop(k)
    self.assertEqual(
      connection_parameter_dict,
      {
        'ipv6': self.computer_partition_ipv6_address,
        'maximum-extra-disk-amount': '0',
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
ihs0:kvm_controller EXITED
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
class TestInstanceHttpServerJson(
  KvmMixinJson, TestInstanceHttpServer):
  pass
