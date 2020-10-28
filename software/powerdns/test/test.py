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

import dns.edns
import dns.message
import dns.query
import http.client
import os
import requests

from slapos.recipe.librecipe import generateHashFromFiles
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))

DNS_PORT = 5353

AFRICAN_SUBNET = '41.0.0.0'
CHINA_TELECOM_SUBNET = '1.0.32.0'
CHINA_UNICOM_SUBNET = '116.181.0.0'
CHINA_MOBILE_SUBNET = '112.21.42.5'
EAST_ASIAN_SUBNET = '1.11.0.0'
EUROPEAN_SUBNET = '5.42.160.0'
HONG_KONG_SUBNET = '1.32.192.0'
JAPANESE_SUBNET = '1.0.16.0'
NORTH_AMERICAN_SUBNET = '3.0.0.0'
OCEANIAN_SUBNET = '1.120.0.0'
SOUTH_AMERICAN_SUBNET = '45.70.188.0'
WEST_ASIAN_SUBNET = '46.70.0.0'


class PowerDNSTestCase(SlapOSInstanceTestCase):
  # power dns uses sockets and need shorter paths on test nodes.
  __partition_reference__ = 'pdns'
  default_supported_zone_list = 'domain.com'

  # focus to test connexion parameters only depending on PowerDNS
  def getPowerDNSParameterDict(self, parameter_dict):
    new_parameter_dict = {}
    for key, value in parameter_dict.items():
      if key in [
        'ns-record',
        'ns1-port',
        'ns1-ipv6',
        'slave-amount',
      ]:
        new_parameter_dict[key] = value
    return new_parameter_dict

  def getPowerDNSConnexionParameterDict(self):
    return self.getPowerDNSParameterDict(
      self.requestDefaultInstance().getConnectionParameterDict()
    )

  def _test_parameter_dict(self, supported_zone_list=None, dns_quantity=1,
                           slave_amount=0):
    if supported_zone_list is None:
      supported_zone_list = self.default_supported_zone_list

    parameter_dict = self.getPowerDNSConnexionParameterDict()
    expected_dict = {
      'ns-record': '',
    }

    ns_record = []
    for replicate_nb in range(1, dns_quantity + 1):
      ns_id = 'ns%s' % replicate_nb
      ns_record.append('%s.%s' % (ns_id, "domain.com"))
      expected_dict[ns_id + '-port'] = str(DNS_PORT)
      expected_dict[ns_id + '-ipv6'] = self._ipv6_address
    expected_dict['ns-record'] = ','.join(ns_record)
    expected_dict['slave-amount'] = str(slave_amount)

    self.assertEqual(expected_dict, parameter_dict)


class ServicesTestCase(PowerDNSTestCase):

  def test_hashes(self):
    hash_files = [
      'software_release/buildout.cfg',
    ]
    expected_process_names = [
      'pdns-{hash}-on-watch',
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


class TestMonitorAccess(PowerDNSTestCase):

  def test(self):
    connection_parameter_dict = self.requestDefaultInstance()\
      .getConnectionParameterDict()
    monitor_base_url = connection_parameter_dict.get('monitor-url')
    result = requests.get(
      monitor_base_url, verify=False, auth=(
        connection_parameter_dict.get('monitor-user'),
        connection_parameter_dict.get('monitor-password')
      )
    )

    self.assertEqual(
      http.client.OK,
      result.status_code
    )


class TestMasterRequest(PowerDNSTestCase):

  def test(self):
    self._test_parameter_dict()


class TestMasterRequestSingleDomain(PowerDNSTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'supported-zone-list': 'toto.example.com',
    }

  def test(self):
    self._test_parameter_dict(
      supported_zone_list=self.getInstanceParameterDict()['supported-zone-list']
    )


class TestMasterRequestDomains(TestMasterRequestSingleDomain):

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'supported-zone-list': 'toto.example.com tata.example.com',
    }


class PowerDNSSlaveTestCase(PowerDNSTestCase):

  @classmethod
  def requestDefaultInstance(cls, state='started'):
    default_instance = super().requestDefaultInstance(state=state)
    cls.requestSlaves()
    return default_instance

  @classmethod
  def requestSlaves(cls):
    software_url = cls.getSoftwareURL()
    software_type = cls.getInstanceSoftwareType()
    for slave_reference, partition_parameter_kw in cls\
            .getSlaveParameterDictDict().items():
      cls.logger.debug(
        'requesting slave "%s" software:%s parameters:%s',
        slave_reference, software_url, partition_parameter_kw
      )
      cls.slap.request(
        software_release=software_url,
        software_type=software_type,
        partition_reference=slave_reference,
        partition_parameter_kw=partition_parameter_kw,
        shared=True
      )

  @classmethod
  def getSlaveConnectionParameterDictList(cls):
    parameter_dict_list = []

    for slave_reference, partition_parameter_kw in cls\
            .getSlaveParameterDictDict().items():
      parameter_dict_list.append(cls.slap.request(
        software_release=cls.getSoftwareURL(),
        software_type=cls.getInstanceSoftwareType(),
        partition_reference=slave_reference,
        partition_parameter_kw=partition_parameter_kw,
        shared=True
      ).getConnectionParameterDict())
    return parameter_dict_list

  @classmethod
  def getSlaveParameterDictDict(cls):
    return {
      'slave-pdns1': {
        'record': 'test1',
        'applicable-zone': 'domain.com',
        'origin': 'nexedi.com',
        'default': 'test1.com.',
        'africa': 'test1africa.com.',
        'china-telecom': 'test1china-telecom.com.',
        'china-unicom': 'test1china-unicom.com.',
        'china-mobile': 'test1china-mobile.com.',
        'east-asia': 'test1east-asia.com.',
        'europe': 'test1europe.com.',
        'hong-kong': 'test1hong-kong.com.',
        'japan': 'test1japan.com.',
        'north-america': 'test1north-america.com.',
        'oceania': 'test1oceania.com.',
        'south-america': 'test1south-america.com.',
        'west-asia': 'test1west-asia.com.',
      },
      'slave-pdns2': {
        'record': 'test2',
        'applicable-zone': 'domain.com',
        'origin': 'nexedi.com',
        'default': 'test2.com.',
        'china-telecom': 'test2china-telecom.com.',
        'europe': 'test2europe.com.',
      },
    }

  def dns_query(self, domain_name, subnet):
    message = dns.message.make_query(domain_name, 'A')
    client_subnet_option = dns.edns.ECSOption(subnet)
    message.use_edns(options=[client_subnet_option])
    answer = dns.query.udp(message, self._ipv6_address, port=DNS_PORT)
    rrset = answer.get_rrset(
            dns.message.ANSWER,
            dns.name.from_text(domain_name),
            dns.rdataclass.IN,
            dns.rdatatype.CNAME
          )
    self.assertIsNotNone(rrset)
    return rrset.to_text().split()[-1]

  def _test_dns_resolver(self, supported_zone_list):
    slave_parameter_dict_dict = self.getSlaveParameterDictDict()
    subnet_dict = {
      'africa': AFRICAN_SUBNET,
      'china-telecom': CHINA_TELECOM_SUBNET,
      'china-unicom': CHINA_UNICOM_SUBNET,
      'china-mobile': CHINA_MOBILE_SUBNET,
      'east-asia': EAST_ASIAN_SUBNET,
      'europe': EUROPEAN_SUBNET,
      'hong-kong': HONG_KONG_SUBNET,
      'japan': JAPANESE_SUBNET,
      'north-america': NORTH_AMERICAN_SUBNET,
      'oceania': OCEANIAN_SUBNET,
      'south-america': SOUTH_AMERICAN_SUBNET,
      'west-asia': WEST_ASIAN_SUBNET,
    }
    default_rr_dict = {
      'europe': 'eu',
      'africa': 'af',
      'south-america': 'sa',
      'north-america': 'na',
      'china-telecom': 'cn-t',
      'china-unicom': 'cn-u',
      'china-mobile': 'cn-m',
      'japan': 'jp',
      'hong-kong': 'hk',
      'east-asia': 'as',
      'west-asia': 'eu',
      'oceania': 'oc',
    }

    for slave_name in slave_parameter_dict_dict:
      slave_parameter_dict = slave_parameter_dict_dict[slave_name]
      domain_name = '%s.%s' % (
        slave_parameter_dict['record'], slave_parameter_dict['applicable-zone']
      )
      for region in subnet_dict:
        self.assertEqual(
          slave_parameter_dict.pop(
            region,
            '%s.%s.' % (default_rr_dict[region], slave_parameter_dict['origin'])
          ),
          self.dns_query(domain_name, subnet_dict[region])
        )

  def _test_slaves(self, supported_zone_list=None):
    if supported_zone_list is None:
      supported_zone_list = self.default_supported_zone_list
    self._test_parameter_dict(
      supported_zone_list=supported_zone_list,
      slave_amount=len(self.getSlaveParameterDictDict())
    )
    self._test_dns_resolver(supported_zone_list)


class TestSlaveRequest(PowerDNSSlaveTestCase):

  def test(self):
    self._test_slaves()


class TestSlaveRequestSingleDomain(PowerDNSSlaveTestCase,
                                   TestMasterRequestSingleDomain):

  @classmethod
  def getSlaveParameterDictDict(cls):
    default_slave_parameter_dict_dict = super().getSlaveParameterDictDict()
    slave_parameter_dict_dict = {}
    supported_zone_list = cls\
      .getInstanceParameterDict()['supported-zone-list'].split()
    for zone, index in zip(
      supported_zone_list,
      range(len(supported_zone_list))
    ):
      for default_slave_name, slave in default_slave_parameter_dict_dict\
        .items():
        slave_name = '%s%s' % (default_slave_name, index)
        slave_parameter_dict_dict[slave_name] = slave
        slave_parameter_dict_dict[slave_name]['applicable-zone'] = zone
    return slave_parameter_dict_dict

  def test(self):
    self._test_slaves(supported_zone_list=self
                      .getInstanceParameterDict()['supported-zone-list'])


class TestSlaveRequestDomains(TestMasterRequestDomains,
                              TestSlaveRequestSingleDomain):
  pass
