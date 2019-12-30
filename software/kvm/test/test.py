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
import re
import requests
import six
import slapos.util
import subprocess
import sqlite3
from six.moves.urllib.parse import parse_qs, urlparse
import unittest

from slapos.recipe.librecipe import generateHashFromFiles
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


def sanityCheck():
  try:
    output = subprocess.check_output("lsmod | grep kvm_intel", shell=True)
  except subprocess.CalledProcessError as e:
    state = False
    output = e.output
  else:
    state = True
  if state is True and re.search(br'kvm.*kvm_intel', output):
    return True


if sanityCheck():
  setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
      os.path.join(os.path.dirname(__file__), '..',
                   'software%s.cfg' % ("-py3" if six.PY3 else ""))))
else:
  setUpModule, InstanceTestCase = None, unittest.TestCase

  class SanityCheckTestCase(unittest.TestCase):
    def test_kvm_sanity_check(self):
      if not(sanityCheck()):
        self.fail('This environment is not usable for kvm testing, as it '
                  'lacks kvm_intel kernel module')


@unittest.skipIf(not sanityCheck(), 'missing kvm_intel module')
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
        partition_information['connection_xml'].encode('utf-8'))
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


@unittest.skipIf(not sanityCheck(), 'missing kvm_intel module')
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
    self.assertTrue('<title>noVNC</title>' in result.text)
    self.assertFalse('url-additional' in connection_parameter_dict)


@unittest.skipIf(not sanityCheck(), 'missing kvm_intel module')
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
    self.assertTrue('<title>noVNC</title>' in result.text)

    result = requests.get(
      connection_parameter_dict['url-additional'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertTrue('<title>noVNC</title>' in result.text)


@unittest.skipIf(not sanityCheck(), 'missing kvm_intel module')
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
    result = requests.get(connection_parameter_dict['kvm0-url'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertTrue('<title>noVNC</title>' in result.text)
    self.assertFalse('kvm0-url-additional' in connection_parameter_dict)


@unittest.skipIf(not sanityCheck(), 'missing kvm_intel module')
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
    result = requests.get(connection_parameter_dict['kvm0-url'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertTrue('<title>noVNC</title>' in result.text)

    result = requests.get(
      connection_parameter_dict['kvm0-url-additional'], verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertTrue('<title>noVNC</title>' in result.text)


@unittest.skipIf(not sanityCheck(), 'missing kvm_intel module')
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

@unittest.skipIf(not sanityCheck(), 'missing kvm_intel module')
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
    result = requests.get(connection_parameter_dict['upload_url'].strip(), verify=False)
    self.assertEqual(
      httplib.OK,
      result.status_code
    )
    self.assertIn('<title>Upload new File</title>', result.text)
    self.assertIn("WARNING", connection_parameter_dict['status_message'])
