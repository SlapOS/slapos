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

import six.moves.http_client as httplib
import json
import os
import hashlib
import psutil
import requests
import six
import slapos.util
import sqlite3
from six.moves.urllib.parse import parse_qs, urlparse
import unittest
import subprocess

from slapos.recipe.librecipe import generateHashFromFiles
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.slap.standalone import SlapOSNodeCommandError

has_kvm = os.access('/dev/kvm', os.R_OK | os.W_OK)
skipUnlessKvm = unittest.skipUnless(has_kvm, 'kvm not loaded or not allowed')
skipIfPython3 = unittest.skipIf(
  six.PY3, 'rdiff-backup is not compatible with Python 3 yet')

if has_kvm:
  setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
      os.path.join(os.path.dirname(__file__), '..',
                   'software%s.cfg' % ("-py3" if six.PY3 else ""))))
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
    # Debian 10 image
    "virtual-hard-drive-url":
    "http://shacache.org/shacache/9d3e6d017754fdd08e5ecf78093dec27fd792fb183d"
    "f6146006adf003b6f4b98c0388d5a11566627101f7855d77f60e3dd4ba7ce66850f4a8f0"
    "30573b904d5ab",
    "virtual-hard-drive-md5sum": "b7928d7b0a2b5e2888f5ddf68f5fe422",
    "virtual-hard-drive-gzipped": False,
    "hard-drive-url-check-certificate": False,
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
@skipUnlessKvm
class ServicesTestCase(InstanceTestCase):
  def test_hashes(self):
    hash_files = [
      'software_release/buildout.cfg',
    ]
    expected_process_names = [
      '6tunnel-10022-{hash}-on-watch',
      '6tunnel-10080-{hash}-on-watch',
      '6tunnel-10443-{hash}-on-watch',
      'certificate_authority-{hash}-on-watch',
      'crond-{hash}-on-watch',
      'kvm-{hash}-on-watch',
      'websockify-{hash}-on-watch',
    ]

    with self.slap.instance_supervisor_rpc as supervisor:
      process_names = [process['name']
                       for process in supervisor.getAllProcessInfo()]

    hash_files = [os.path.join(self.computer_partition_root_path, path)
                  for path in hash_files]

    for name in expected_process_names:
      h = generateHashFromFiles(hash_files)
      expected_process_name = name.format(hash=h)

      self.assertIn(expected_process_name, process_names)


class MonitorAccessMixin(object):
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
    connection = self.sqlite3_connect()

    def dict_factory(cursor, row):
      d = {}
      for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
      return d
    connection.row_factory = dict_factory
    cursor = connection.cursor()

    cursor.execute(
      "SELECT reference, xml, connection_xml, partition_reference, "
      "software_release, requested_state, software_type "
      "FROM partition14 "
      "WHERE slap_state='busy'")
    return cursor.fetchall()

  def test_access_monitor(self):
    connection_parameter_dict = self.computer_partition\
      .getConnectionParameterDict()
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
      connection_dict = slapos.util.xml2dict(
        connection_xml if six.PY3 else connection_xml.encode('utf-8'))
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
class TestAccessDefault(MonitorAccessMixin, InstanceTestCase):
  __partition_reference__ = 'ad'
  expected_partition_with_monitor_base_url_count = 1

  def test(self):
    connection_parameter_dict = self.computer_partition\
      .getConnectionParameterDict()
    result = requests.get(connection_parameter_dict['url'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)
    self.assertNotIn('url-additional', connection_parameter_dict)


@skipUnlessKvm
class TestAccessDefaultAdditional(MonitorAccessMixin, InstanceTestCase):
  __partition_reference__ = 'ada'
  expected_partition_with_monitor_base_url_count = 1

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
class TestAccessDefaultBootstrap(MonitorAccessMixin, InstanceTestCase):
  __partition_reference__ = 'adb'
  expected_partition_with_monitor_base_url_count = 1

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(dict(
      bootstrap_common_param_dict, **bootstrap_machine_param_dict))}

  def test(self):
    connection_parameter_dict = self.computer_partition\
      .getConnectionParameterDict()

    result = requests.get(connection_parameter_dict['url'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)


@skipUnlessKvm
class TestAccessKvmCluster(MonitorAccessMixin, InstanceTestCase):
  __partition_reference__ = 'akc'
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
    connection_parameter_dict = self.computer_partition\
      .getConnectionParameterDict()
    result = requests.get(connection_parameter_dict['KVM0-url'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>noVNC</title>', result.text)
    self.assertNotIn('KVM0-url-additional', connection_parameter_dict)


@skipUnlessKvm
class TestAccessKvmClusterAdditional(MonitorAccessMixin, InstanceTestCase):
  __partition_reference__ = 'akca'
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
    connection_parameter_dict = self.computer_partition\
      .getConnectionParameterDict()
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


@skipIfPython3
@skipUnlessKvm
class TestAccessKvmClusterBootstrap(MonitorAccessMixin, InstanceTestCase):
  __partition_reference__ = 'akcb'
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
              # Debian 9 image
              "virtual-hard-drive-url":
              "http://shacache.org/shacache/ce07873dbab7fa8501d1bf5565c2737b2"
              "eed6c8b9361b4997b21daf5f5d1590972db9ac00131cc5b27d9aa353f2f940"
              "71e073f9980cc61badd6d2427f592e6e8",
              "virtual-hard-drive-md5sum": "2b113e3cd8276b9740189622603d6f99"
          })
      }
    }))}

  def test(self):
    connection_parameter_dict = self.computer_partition\
      .getConnectionParameterDict()
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


@skipIfPython3
@skipUnlessKvm
class TestInstanceResilient(InstanceTestCase):
  __partition_reference__ = 'ir'
  instance_max_retry = 20

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-resilient'

  def test(self):
    # just check that keys returned on requested partition are for resilient
    self.assertSetEqual(
      set(self.computer_partition.getConnectionParameterDict().keys()),
      set([
        'backend-url',
        'feed-url-kvm-1-pull',
        'feed-url-kvm-1-push',
        'ipv6',
        'ipv6-network-info',
        'monitor-base-url',
        'monitor-password',
        'monitor-setup-url',
        'monitor-user',
        'takeover-kvm-1-password',
        'takeover-kvm-1-url',
        'url']))


@skipIfPython3
@skipUnlessKvm
class TestAccessResilientAdditional(InstanceTestCase):
  __partition_reference__ = 'ara'
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


class TestInstanceNbdServer(InstanceTestCase):
  __partition_reference__ = 'ins'
  instance_max_retry = 5

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'nbd'

  @classmethod
  def getInstanceParameterDict(cls):
    # port 8080 is used by testnode, use another one
    return {
      'otu-port': '8090'
    }

  def test(self):
    connection_parameter_dict = self.computer_partition\
      .getConnectionParameterDict()
    result = requests.get(
      connection_parameter_dict['upload_url'].strip(), verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>Upload new File</title>', result.text)
    self.assertIn("WARNING", connection_parameter_dict['status_message'])


@skipUnlessKvm
class TestImageUrlList(InstanceTestCase):
  __partition_reference__ = 'iul'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'default'

  @classmethod
  def getInstanceParameterDict(cls):
    # start with empty, but working configuration
    return {}

  def tearDown(self):
    # clean up the instance for other tests
    # 1st remove all images...
    self.rerequestInstance({'image-url-list': ''})
    self.slap.waitForInstance(max_retry=10)
    # 2nd ...move instance to "default" state
    self.rerequestInstance({})
    self.slap.waitForInstance(max_retry=10)

  def rerequestInstance(self, parameter_dict, state='started'):
    software_url = self.getSoftwareURL()
    software_type = self.getInstanceSoftwareType()
    return self.slap.request(
        software_release=software_url,
        software_type=software_type,
        partition_reference=self.default_partition_reference,
        partition_parameter_kw=parameter_dict,
        state=state)

  fake_image, = (
      "https://shacache.nxdcdn.com/shacache/05105cd25d1ad798b71fd46a206c9b73d"
      "a2c285a078af33d0e739525a595886785725a68811578bc21f75d0a97700a66d5e75bc"
      "e5b2721ca4556a0734cb13e65",)
  fake_image_md5sum = "c98825aa1b6c8087914d2bfcafec3058"
  fake_image2, = (
      "https://shacache.nxdcdn.com/shacache/54f8a83a32bbf52602d9d211d592ee705"
      "99f0c6b6aafe99e44aeadb0c8d3036a0e673aa994ffdb28d9fb0de155720123f74d814"
      "2a74b7675a8d8ca20476dba6e",)
  fake_image2_md5sum = "d4316a4d05f527d987b9d6e43e4c2bc6"
  fake_image_wrong_md5sum = "c98825aa1b6c8087914d2bfcafec3057"

  def raising_waitForInstance(self, max_retry):
    with self.assertRaises(SlapOSNodeCommandError):
      self.slap.waitForInstance(max_retry=max_retry)

  def test(self):
    partition_parameter_kw = {
      'image-url-list': "%s#%s\n%s#%s" % (
        self.fake_image, self.fake_image_md5sum, self.fake_image2,
        self.fake_image2_md5sum)
    }
    self.rerequestInstance(partition_parameter_kw)
    self.slap.waitForInstance(max_retry=10)
    # check that image is correctly downloaded and linked
    image_repository = os.path.join(
      self.computer_partition_root_path, 'srv', 'image-repository')
    image = os.path.join(image_repository, self.fake_image_md5sum)
    image_link = os.path.join(image_repository, 'image_001')
    self.assertTrue(os.path.exists(image))
    with open(image, 'rb') as fh:
      image_md5sum = hashlib.md5(fh.read()).hexdigest()
    self.assertEqual(image_md5sum, self.fake_image_md5sum)
    self.assertTrue(os.path.islink(image_link))
    self.assertEqual(os.readlink(image_link), image)

    image2 = os.path.join(image_repository, self.fake_image2_md5sum)
    image2_link = os.path.join(image_repository, 'image_002')
    self.assertTrue(os.path.exists(image2))
    with open(image2, 'rb') as fh:
      image2_md5sum = hashlib.md5(fh.read()).hexdigest()
    self.assertEqual(image2_md5sum, self.fake_image2_md5sum)
    self.assertTrue(os.path.islink(image2_link))
    self.assertEqual(os.readlink(image2_link), image2)

    # check that the image is NOT YET available in kvm
    with self.slap.instance_supervisor_rpc as instance_supervisor:
      kvm_pid = [q for q in instance_supervisor.getAllProcessInfo()
                 if 'kvm-' in q['name']][0]['pid']
      kvm_process = psutil.Process(kvm_pid)
      cmd_line = ''.join(kvm_process.cmdline())
      self.assertNotIn(
        'srv/image-repository/image_001,media=cdrom',
        cmd_line
      )
      self.assertNotIn(
        'srv/image-repository/image_002,media=cdrom',
        cmd_line
      )

    # mimic the requirement: restart the instance by requesting it stopped and
    # then started started, like user have to do it
    self.rerequestInstance(partition_parameter_kw, state='stopped')
    self.slap.waitForInstance(max_retry=1)
    self.rerequestInstance(partition_parameter_kw, state='started')
    self.slap.waitForInstance(max_retry=1)

    # now the image is available in the kvm
    with self.slap.instance_supervisor_rpc as instance_supervisor:
      kvm_pid = [q for q in instance_supervisor.getAllProcessInfo()
                 if 'kvm-' in q['name']][0]['pid']
      kvm_process = psutil.Process(kvm_pid)
      cmd_line = ''.join(kvm_process.cmdline())
      self.assertIn(
        'srv/image-repository/image_001,media=cdrom',
        cmd_line
      )
      self.assertIn(
        'srv/image-repository/image_002,media=cdrom',
        cmd_line
      )

    # cleanup of images works, also asserts that configuration changes are
    # reflected
    self.rerequestInstance({'image-url-list': ''})
    self.slap.waitForInstance(max_retry=2)
    self.assertEqual(
      os.listdir(image_repository),
      []
    )

  def assertPromiseFails(self, promise):
    monitor_run_promise = os.path.join(
      self.computer_partition_root_path, 'software_release', 'bin',
      'monitor.runpromise'
    )
    monitor_configuration = os.path.join(
      self.computer_partition_root_path, 'etc', 'monitor.conf')

    self.assertNotEqual(
      0,
      subprocess.call([
        monitor_run_promise, '-c', monitor_configuration, '-a', '-f',
        '--run-only', promise])
    )

  def test_bad_parameter(self):
    self.rerequestInstance({
      'image-url-list': "jsutbad"
    })
    self.raising_waitForInstance(3)
    self.assertPromiseFails('image-url-list-config-state-promise.py')

  def test_incorrect_md5sum(self):
    self.rerequestInstance({
      'image-url-list': "%s#" % (self.fake_image,)
    })
    self.raising_waitForInstance(3)
    self.assertPromiseFails('image-url-list-config-state-promise.py')
    self.rerequestInstance({
      'image-url-list': "url#asdasd"
    })
    self.raising_waitForInstance(3)
    self.assertPromiseFails('image-url-list-config-state-promise.py')

  def test_not_matching_md5sum(self):
    self.rerequestInstance({
      'image-url-list': "%s#%s" % (
        self.fake_image, self.fake_image_wrong_md5sum)
    })
    self.raising_waitForInstance(3)
    self.assertPromiseFails('image-url-list-download-md5sum-promise.py')
    self.assertPromiseFails('image-url-list-download-state-promise.py')

  def test_unreachable_host(self):
    self.rerequestInstance({
      'image-url-list': "evennotahost#%s" % (
        self.fake_image_md5sum,)
    })
    self.raising_waitForInstance(3)
    self.assertPromiseFails('image-url-list-download-state-promise.py')

  def test_too_many_images(self):
    self.rerequestInstance({
      'image-url-list': """
      image1#11111111111111111111111111111111
      image2#22222222222222222222222222222222
      image3#33333333333333333333333333333333
      image4#44444444444444444444444444444444
      image5#55555555555555555555555555555555
      image6#66666666666666666666666666666666
      """
    })
    self.raising_waitForInstance(3)
    self.assertPromiseFails('image-url-list-config-state-promise.py')


@skipUnlessKvm
class TestImageUrlListKvmCluster(InstanceTestCase):
  __partition_reference__ = 'iulkc'

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'kvm-cluster'

  fake_image, = (
      "https://shacache.nxdcdn.com/shacache/05105cd25d1ad798b71fd46a206c9b73d"
      "a2c285a078af33d0e739525a595886785725a68811578bc21f75d0a97700a66d5e75bc"
      "e5b2721ca4556a0734cb13e65",)
  fake_image_md5sum = "c98825aa1b6c8087914d2bfcafec3058"
  fake_image2, = (
      "https://shacache.nxdcdn.com/shacache/54f8a83a32bbf52602d9d211d592ee705"
      "99f0c6b6aafe99e44aeadb0c8d3036a0e673aa994ffdb28d9fb0de155720123f74d814"
      "2a74b7675a8d8ca20476dba6e",)
  fake_image2_md5sum = "d4316a4d05f527d987b9d6e43e4c2bc6"

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      "kvm-partition-dict": {
        "KVM0": {
            "disable-ansible-promise": True,
            "image-url-list": "%s#%s" % (
              cls.fake_image, cls.fake_image_md5sum)
        },
        "KVM1": {
            "disable-ansible-promise": True,
            "image-url-list": "%s#%s" % (
              cls.fake_image2, cls.fake_image2_md5sum)
        }
      }
    })}

  def test(self):
    # Note: As there is no way to introspect nicely where partition landed
    #       we assume ordering of the cluster requests
    KVM0_config = os.path.join(
      self.slap.instance_directory, self.__partition_reference__ + '1', 'etc',
      'image-url-list.conf')
    KVM1_config = os.path.join(
      self.slap.instance_directory, self.__partition_reference__ + '2', 'etc',
      'image-url-list.conf')
    with open(KVM0_config, 'r') as fh:
      self.assertEqual(
        "%s#%s" % (self.fake_image, self.fake_image_md5sum),
        fh.read()
      )
    with open(KVM1_config, 'r') as fh:
      self.assertEqual(
        "%s#%s" % (self.fake_image2, self.fake_image2_md5sum),
        fh.read()
      )
