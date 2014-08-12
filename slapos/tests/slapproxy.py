# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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

import ConfigParser
import os
import logging
import shutil
import tempfile
import unittest
import xml_marshaller
from xml_marshaller.xml_marshaller import loads, dumps

import slapos.proxy
import slapos.proxy.views as views
import slapos.slap.slap


class WrongFormat(Exception):
  pass


class ProxyOption(object):
  """
  Will simulate options given to slapproxy
  """
  def __init__(self, proxy_db):
    self.verbose = True
    self.database_uri = proxy_db
    self.console = False
    self.log_file = None


class BasicMixin(object):
  def setUp(self):
    """
    Will set files and start slapproxy
    """
    self._tempdir = tempfile.mkdtemp()
    logging.basicConfig(level=logging.DEBUG)
    self.setFiles()
    self.startProxy()

  def setFiles(self):
    """
    Set environment to run slapproxy
    """
    self.slapos_cfg = os.path.join(self._tempdir, 'slapos.cfg')
    self.proxy_db = os.path.join(self._tempdir, 'lib', 'proxy.db')
    self.proxyaddr = 'http://127.0.0.1:8080/'
    self.computer_id = 'computer'
    open(self.slapos_cfg, 'w').write("""[slapos]
software_root = %(tempdir)s/opt/slapgrid
instance_root = %(tempdir)s/srv/slapgrid
master_url = %(proxyaddr)s
computer_id = computer
[slapproxy]
host = 127.0.0.1
port = 8080
database_uri = %(tempdir)s/lib/proxy.db
""" % {'tempdir': self._tempdir, 'proxyaddr': self.proxyaddr})
    for directory in ['opt', 'srv', 'lib']:
      path = os.path.join(self._tempdir, directory)
      os.mkdir(path)

  def startProxy(self):
    """
    Set config for slapproxy and start it
    """
    conf = slapos.proxy.ProxyConfig(logger=logging.getLogger())
    configp = ConfigParser.SafeConfigParser()
    configp.read(self.slapos_cfg)
    conf.mergeConfig(ProxyOption(self.proxy_db), configp)
    conf.setConfig()
    views.app.config['TESTING'] = True
    views.app.config['computer_id'] = self.computer_id
    views.app.config['DATABASE_URI'] = self.proxy_db
    views.app.config['HOST'] = conf.host
    views.app.config['port'] = conf.port
    self.app_config = views.app.config
    self.app = views.app.test_client()

  def add_free_partition(self, partition_amount, computer_id=None):
    """
    Will simulate a slapformat first run
    and create "partition_amount" partitions
    """
    if not computer_id:
      computer_id = self.computer_id
    computer_dict = {
        'reference': computer_id,
        'address': '123.456.789',
        'netmask': 'fffffffff',
        'partition_list': [],
    }
    for i in range(partition_amount):
      partition_example = {
          'reference': 'slappart%s' % i,
          'address_list': [],
      }
      computer_dict['partition_list'].append(partition_example)

    request_dict = {
        'computer_id': self.computer_id,
        'xml': xml_marshaller.xml_marshaller.dumps(computer_dict),
    }
    self.app.post('/loadComputerConfigurationFromXML',
                  data=request_dict)

  def tearDown(self):
    """
    Remove files generated for test
    """
    shutil.rmtree(self._tempdir, True)


class TestInformation(BasicMixin, unittest.TestCase):
  """
  Test Basic response of slapproxy
  """

  def test_getComputerInformation(self):
    """
    Check that getComputerInformation return a Computer
    and database is generated
    """
    rv = self.app.get('/getComputerInformation?computer_id=%s' % self.computer_id)
    self.assertIsInstance(
        xml_marshaller.xml_marshaller.loads(rv.data),
        slapos.slap.Computer)
    self.assertTrue(os.path.exists(self.proxy_db))

  def test_getFullComputerInformation(self):
    """
    Check that getFullComputerInformation return a Computer
    and database is generated
    """
    rv = self.app.get('/getFullComputerInformation?computer_id=%s' % self.computer_id)
    self.assertIsInstance(
        xml_marshaller.xml_marshaller.loads(rv.data),
        slapos.slap.Computer)
    self.assertTrue(os.path.exists(self.proxy_db))

  def test_getComputerInformation_wrong_computer(self):
    """
    Test that computer information won't be given to a requester different
    from the one specified
    """
    with self.assertRaises(slapos.slap.NotFoundError):
      self.app.get('/getComputerInformation?computer_id=%s42' % self.computer_id)

  def test_partition_are_empty(self):
    """
    Test that empty partition are empty :)
    """
    self.add_free_partition(10)
    rv = self.app.get('/getFullComputerInformation?computer_id=%s' % self.computer_id)
    computer = xml_marshaller.xml_marshaller.loads(rv.data)
    for slap_partition in computer._computer_partition_list:
        self.assertIsNone(slap_partition._software_release_document)
        self.assertEqual(slap_partition._requested_state, 'destroyed')
        self.assertEqual(slap_partition._need_modification, 0)

  def test_getSoftwareReleaseListFromSoftwareProduct_software_product_reference(self):
    """
    Check that calling getSoftwareReleaseListFromSoftwareProduct() in slapproxy
    using a software_product_reference as parameter behaves correctly.
    """
    software_product_reference = 'my_product'
    software_release_url = 'my_url'
    self.app_config['software_product_list'] = {
        software_product_reference: software_release_url
    }
    response = self.app.get('/getSoftwareReleaseListFromSoftwareProduct'
                            '?software_product_reference=%s' %\
                            software_product_reference)
    software_release_url_list = xml_marshaller.xml_marshaller.loads(
        response.data)
    self.assertEqual(
        software_release_url_list,
        [software_release_url]
    )

  def test_getSoftwareReleaseListFromSoftwareProduct_noSoftwareProduct(self):
    """
    Check that calling getSoftwareReleaseListFromSoftwareProduct() in slapproxy
    using a software_product_reference that doesn't exist as parameter
    returns empty list.
    """
    self.app_config['software_product_list'] = {'random': 'random'}
    response = self.app.get('/getSoftwareReleaseListFromSoftwareProduct'
                            '?software_product_reference=idonotexist')
    software_release_url_list = xml_marshaller.xml_marshaller.loads(
        response.data)
    self.assertEqual(
        software_release_url_list,
        []
    )

  def test_getSoftwareReleaseListFromSoftwareProduct_bothParameter(self):
    """
    Test that a call to getSoftwareReleaseListFromSoftwareProduct with no
    parameter raises
    """
    self.assertRaises(
        AssertionError,
       self.app.get,
       '/getSoftwareReleaseListFromSoftwareProduct'
       '?software_product_reference=foo'
       '&software_release_url=bar'
    )

  def test_getSoftwareReleaseListFromSoftwareProduct_noParameter(self):
    """
    Test that a call to getSoftwareReleaseListFromSoftwareProduct with both
    software_product_reference and software_release_url parameters raises
    """
    self.assertRaises(
        AssertionError,
        self.app.get, '/getSoftwareReleaseListFromSoftwareProduct'
    )


class MasterMixin(BasicMixin, unittest.TestCase):
  """
  Define advanced tool for test proxy simulating behavior slap library tools
  """
  def _requestComputerPartition(self, software_release, software_type, partition_reference,
              partition_id,
              shared=False, partition_parameter_kw=None, filter_kw=None,
              state=None):
    """
    Check parameters, call requestComputerPartition server method and return result
    """
    if partition_parameter_kw is None:
      partition_parameter_kw = {}
    if filter_kw is None:
      filter_kw = {}
   # Let's enforce a default software type
    if software_type is None:
      software_type = 'default'

    request_dict = {
        'computer_id': self.computer_id,
        'computer_partition_id': partition_id,
        'software_release': software_release,
        'software_type': software_type,
        'partition_reference': partition_reference,
        'shared_xml': xml_marshaller.xml_marshaller.dumps(shared),
        'partition_parameter_xml': xml_marshaller.xml_marshaller.dumps(
            partition_parameter_kw),
        'filter_xml': xml_marshaller.xml_marshaller.dumps(filter_kw),
        'state': xml_marshaller.xml_marshaller.dumps(state),
    }
    return self.app.post('/requestComputerPartition', data=request_dict)
	
  def request(self, *args, **kwargs):
    """
    Simulate a request with above parameters
    Return response by server (a computer partition or an error)
    """
    rv = self._requestComputerPartition(*args, **kwargs)
    self.assertEqual(rv._status_code, 200)
    xml = rv.data
    software_instance = xml_marshaller.xml_marshaller.loads(xml)

    computer_partition = slapos.slap.ComputerPartition(
        software_instance.slap_computer_id,
        software_instance.slap_computer_partition_id)
    
    computer_partition.__dict__.update(software_instance.__dict__)
    return computer_partition

  def supply(self, url, computer_id=None, state=''):
    if not computer_id:
      computer_id = self.computer_id
    request_dict = {'url':url, 'computer_id': computer_id, 'state':state}
    rv = self.app.post('/supplySupply',
                       data=request_dict)
    # XXX return a Software Release

  def setConnectionDict(self, partition_id,
                        connection_dict, slave_reference=None):
    self.app.post('/setComputerPartitionConnectionXml', data={
        'computer_id': self.computer_id,
        'computer_partition_id': partition_id,
        'connection_xml': xml_marshaller.xml_marshaller.dumps(connection_dict),
        'slave_reference': slave_reference})

  def getPartitionInformation(self, computer_partition_id):
    """
    Return computer information as stored in proxy for corresponding id
    """
    rv = self.app.get('/getFullComputerInformation?computer_id=%s' % self.computer_id)
    computer = xml_marshaller.xml_marshaller.loads(rv.data)
    for instance in computer._computer_partition_list:
      if instance._partition_id == computer_partition_id:
        return instance


class TestRequest(MasterMixin):
  """
  Set of tests for requests
  """

  def test_request_consistent_parameters(self):
    """
    Check that all different parameters related to requests (like instance_guid, state) are set and consistent
    """
    self.add_free_partition(1)
    partition = self.request('http://sr//', None, 'MyFirstInstance', 'slappart0')
    self.assertEqual(partition.getState(), 'started')
    self.assertEqual(partition.getInstanceGuid(), 'computer-slappart0')

  def test_two_request_one_partition_free(self):
    """
    Since slapproxy does not implement scope, providing two partition_id
    values will still succeed, even if only one partition is available.
    """
    self.add_free_partition(1)
    self.assertIsInstance(self.request('http://sr//', None,
                                       'MyFirstInstance', 'slappart2'),
                          slapos.slap.ComputerPartition)
    self.assertIsInstance(self.request('http://sr//', None,
                                       'MyFirstInstance', 'slappart3'),
                          slapos.slap.ComputerPartition)

  def test_two_request_two_partition_free(self):
    """
    If two requests are made with two available partition
    both will succeed
    """
    self.add_free_partition(2)
    self.assertIsInstance(self.request('http://sr//', None,
                                       'MyFirstInstance', 'slappart2'),
                          slapos.slap.ComputerPartition)
    self.assertIsInstance(self.request('http://sr//', None,
                                       'MyFirstInstance', 'slappart3'),
                          slapos.slap.ComputerPartition)

  def test_two_same_request_from_one_partition(self):
    """
    Request will return same partition for two equal requests
    """
    self.add_free_partition(2)
    self.assertEqual(
        self.request('http://sr//', None, 'MyFirstInstance', 'slappart2').__dict__,
        self.request('http://sr//', None, 'MyFirstInstance', 'slappart2').__dict__)

  def test_two_requests_with_different_parameters_but_same_reference(self):
    """
    Request will return same partition for two different requests but will
    only update parameters
    """
    self.add_free_partition(2)
    wanted_domain1 = 'fou.org'
    wanted_domain2 = 'carzy.org'

    request1 = self.request('http://sr//', None, 'MyFirstInstance', 'slappart2',
                            partition_parameter_kw={'domain': wanted_domain1})
    request1_dict = request1.__dict__
    requested_result1 = self.getPartitionInformation(
        request1_dict['_partition_id'])
    request2 = self.request('http://sr1//', 'Papa', 'MyFirstInstance', 'slappart2',
                            partition_parameter_kw={'domain': wanted_domain2})
    request2_dict = request2.__dict__
    requested_result2 = self.getPartitionInformation(
        request2_dict['_partition_id'])
    # Test we received same partition
    for key in ['_partition_id', '_computer_id']:
      self.assertEqual(request1_dict[key], request2_dict[key])
    # Test that only parameters changed
    for key in requested_result2.__dict__:
      if key not in ['_parameter_dict',
                     '_software_release_document']:
        self.assertEqual(requested_result2.__dict__[key],
                         requested_result1.__dict__[key])
      elif key in ['_software_release_document']:
        self.assertEqual(requested_result2.__dict__[key].__dict__,
                         requested_result1.__dict__[key].__dict__)
    #Test parameters where set correctly
    self.assertEqual(wanted_domain1,
                     requested_result1._parameter_dict['domain'])
    self.assertEqual(wanted_domain2,
                     requested_result2._parameter_dict['domain'])

  def test_two_different_request_from_two_partition(self):
    """
    Since slapproxy does not implement scope, two request with
    different partition_id will still return the same partition.
    """
    self.add_free_partition(2)
    self.assertEqual(
        self.request('http://sr//', None, 'MyFirstInstance', 'slappart2').__dict__,
        self.request('http://sr//', None, 'MyFirstInstance', 'slappart3').__dict__)

  def test_two_different_request_from_one_partition(self):
    """
    Two different request from same partition
    will return two different partitions
    """
    self.add_free_partition(2)
    self.assertNotEqual(
        self.request('http://sr//', None, 'MyFirstInstance', 'slappart2').__dict__,
        self.request('http://sr//', None, 'frontend', 'slappart2').__dict__)


class TestSlaveRequest(MasterMixin):
  """
  Test requests related to slave instances.
  """
  def test_slave_request_no_corresponding_partition(self):
    """
    Slave instance request will fail if no corresponding are found
    """
    self.add_free_partition(2)
    rv = self._requestComputerPartition('http://sr//', None, 'MyFirstInstance', 'slappart2', shared=True)
    self.assertEqual(rv._status_code, 404)

  def test_slave_request_set_parameters(self):
    """
    Parameters sent in slave request must be put in slave master
    slave instance list.
    1. We request a slave instance we defined parameters
    2. We check parameters are in the dictionnary defining slave in
        slave master slave_instance_list
    """
    self.add_free_partition(6)
    # Provide partition
    master_partition_id = self.request('http://sr//', None,
                                       'MyFirstInstance', 'slappart4')._partition_id
    # First request of slave instance
    wanted_domain = 'fou.org'
    self.request('http://sr//', None, 'MyFirstInstance', 'slappart2', shared=True,
                 partition_parameter_kw={'domain': wanted_domain})
    # Get updated information for master partition
    master_partition = self.getPartitionInformation(master_partition_id)

    our_slave = master_partition._parameter_dict['slave_instance_list'][0]
    self.assertEqual(our_slave.get('domain'), wanted_domain)

  def test_master_instance_with_no_slave(self):
    """
    Test that a master instance with no requested slave
    has an empty slave_instance_list parameter.
    """
    self.add_free_partition(6)
    # Provide partition
    master_partition_id = self.request('http://sr//', None, 'MyMasterInstance', 'slappart4')._partition_id
    master_partition = self.getPartitionInformation(master_partition_id)
    self.assertEqual(len(master_partition._parameter_dict['slave_instance_list']), 0)

  def test_slave_request_set_parameters_are_updated(self):
    """
    Parameters sent in slave request must be put in slave master
    slave instance list and updated when they change.
    1. We request a slave instance we defined parameters
    2. We check parameters are in the dictionnary defining slave in
        slave master slave_instance_list
    3. We request same slave instance with changed parameters
    4. We check parameters are in the dictionnary defining slave in
        slave master slave_instance_list have changed
    """
    self.add_free_partition(6)
    # Provide partition
    master_partition_id = self.request('http://sr//', None,
                                       'MyFirstInstance', 'slappart4')._partition_id
    # First request of slave instance
    wanted_domain_1 = 'crazy.org'
    self.request('http://sr//', None, 'MyFirstInstance', 'slappart2', shared=True,
                 partition_parameter_kw={'domain': wanted_domain_1})
    # Get updated information for master partition
    master_partition = self.getPartitionInformation(master_partition_id)
    our_slave = master_partition._parameter_dict['slave_instance_list'][0]
    self.assertEqual(our_slave.get('domain'), wanted_domain_1)

    # Second request of slave instance
    wanted_domain_2 = 'maluco.org'
    self.request('http://sr//', None, 'MyFirstInstance', 'slappart2', shared=True,
                 partition_parameter_kw={'domain': wanted_domain_2})
    # Get updated information for master partition
    master_partition = self.getPartitionInformation(master_partition_id)

    our_slave = master_partition._parameter_dict['slave_instance_list'][0]
    self.assertNotEqual(our_slave.get('domain'), wanted_domain_1)
    self.assertEqual(our_slave.get('domain'), wanted_domain_2)

  def test_slave_request_set_connection_parameters(self):
    """
    Parameters set in slave instance by master instance must be put in slave instance connection parameters.
    1. We request a slave instance
    2. We set connection parameters for this slave instance
    2. We check parameter is present when we do request() for the slave.
    """
    self.add_free_partition(6)
    # Provide partition
    master_partition_id = self.request('http://sr//', None, 'MyMasterInstance', 'slappart4')._partition_id
    # First request of slave instance
    self.request('http://sr//', None, 'MySlaveInstance', 'slappart2', shared=True)
    # Set connection parameter
    master_partition = self.getPartitionInformation(master_partition_id)
    # XXX change slave reference to be compatible with multiple nodes
    self.setConnectionDict(partition_id=master_partition._partition_id,
                           connection_dict={'foo': 'bar'},
                           slave_reference=master_partition._parameter_dict['slave_instance_list'][0]['slave_reference'])
    
    # Get updated information for slave partition
    slave_partition = self.request('http://sr//', None, 'MySlaveInstance', 'slappart2', shared=True)
    self.assertEqual(slave_partition.getConnectionParameter('foo'), 'bar')

  def test_slave_request_one_corresponding_partition(self):
    """
    Successfull request slave instance follow these steps:
    1. Provide one corresponding partition
    2. Ask for Slave instance. But no connection parameters
       But slave is added to Master Instance slave list
    3. Master Instance get updated information (including slave list)
    4. Master instance post information about slave connection parameters
    5. Ask for slave instance is successfull and return a computer instance
        with connection information
    """
    self.add_free_partition(6)
    # Provide partition
    master_partition_id = self.request('http://sr//', None,
                                       'MyFirstInstance', 'slappart4')._partition_id
    # First request of slave instance
    name = 'MyFirstInstance'
    requester = 'slappart2'
    our_slave = self.request('http://sr//', None,
                             name, requester, shared=True)
    self.assertIsInstance(our_slave, slapos.slap.ComputerPartition)
    self.assertEqual(our_slave._connection_dict, {})
    # Get updated information for master partition
    master_partition = self.getPartitionInformation(master_partition_id)
    slave_for_master = master_partition._parameter_dict['slave_instance_list'][0]
    # Send information about slave
    slave_address = {'url': '%s.master.com'}
    self.setConnectionDict(partition_id=master_partition._partition_id,
                           connection_dict=slave_address,
                           slave_reference=slave_for_master['slave_reference'])
    # Successfull slave request with connection parameters
    our_slave = self.request('http://sr//', None,
                             name, requester, shared=True)
    self.assertIsInstance(our_slave, slapos.slap.ComputerPartition)
    self.assertEqual(slave_address, our_slave._connection_dict)

class TestMultiNodeSupport(MasterMixin):
  def test_multi_node_support_different_software_release_list(self):
    """
    Test that two different registered computers have their own
    Software Release list.
    """
    self.add_free_partition(6, computer_id='COMP-0')
    self.add_free_partition(6, computer_id='COMP-1')
    software_release_1_url = 'http://sr1'
    software_release_2_url = 'http://sr2'
    software_release_3_url = 'http://sr3'
    self.supply(software_release_1_url, 'COMP-0')
    self.supply(software_release_2_url, 'COMP-1')
    self.supply(software_release_3_url, 'COMP-0')
    self.supply(software_release_3_url, 'COMP-1')
    
    computer_default = loads(self.app.get('/getFullComputerInformation?computer_id=%s' % self.computer_id).data)
    computer_0 = loads(self.app.get('/getFullComputerInformation?computer_id=COMP-0').data)
    computer_1 = loads(self.app.get('/getFullComputerInformation?computer_id=COMP-1').data) 
    self.assertEqual(len(computer_default._software_release_list), 0)
    self.assertEqual(len(computer_0._software_release_list), 2)
    self.assertEqual(len(computer_1._software_release_list), 2)

    self.assertEqual(
        computer_0._software_release_list[0]._software_release,
        software_release_1_url
    )
    self.assertEqual(
        computer_0._software_release_list[0]._computer_guid,
        'COMP-0'
    )

    self.assertEqual(
        computer_0._software_release_list[1]._software_release,
        software_release_3_url
    )
    self.assertEqual(
        computer_0._software_release_list[1]._computer_guid,
        'COMP-0'
    )

    self.assertEqual(
        computer_1._software_release_list[0]._software_release,
        software_release_2_url
    )
    self.assertEqual(
        computer_1._software_release_list[0]._computer_guid,
        'COMP-1'
    )

    self.assertEqual(
        computer_1._software_release_list[1]._software_release,
        software_release_3_url
    )
    self.assertEqual(
        computer_1._software_release_list[1]._computer_guid,
        'COMP-1'
    )

  def test_multi_node_support_remove_software_release(self):
    """
    Test that removing a software from a Computer doesn't
    affect other computer
    """
    software_release_url = 'http://sr'
    self.add_free_partition(6, computer_id='COMP-0')
    self.add_free_partition(6, computer_id='COMP-1')
    self.supply(software_release_url, 'COMP-0')
    self.supply(software_release_url, 'COMP-1')
    self.supply(software_release_url, 'COMP-0', state='destroyed')
    computer_0 = loads(self.app.get('/getFullComputerInformation?computer_id=COMP-0').data)
    computer_1 = loads(self.app.get('/getFullComputerInformation?computer_id=COMP-1').data)

    self.assertEqual(len(computer_0._software_release_list), 0)
    self.assertEqual(len(computer_1._software_release_list), 1)

    self.assertEqual(
        computer_1._software_release_list[0]._software_release,
        software_release_url
    )
    self.assertEqual(
        computer_1._software_release_list[0]._computer_guid,
        'COMP-1'
    )

  def test_multi_node_support_instance_default_computer(self):
    """
    Test that instance request behaves correctly with default computer
    """
    software_release_url = 'http://sr'
    computer_0_id = 'COMP-0'
    computer_1_id = 'COMP-1'
    self.add_free_partition(6, computer_id=computer_0_id)
    self.add_free_partition(6, computer_id=computer_1_id)

    # Request without SLA -> goes to default computer only.
    # It should fail if we didn't registered partitions for default computer
    # (default computer is always registered)
    rv = self._requestComputerPartition('http://sr//', None, 'MyFirstInstance', 'slappart2')
    self.assertEqual(rv._status_code, 404)

    rv = self._requestComputerPartition('http://sr//', None, 'MyFirstInstance', 'slappart2',
                                        filter_kw={'computer_guid':self.computer_id})
    self.assertEqual(rv._status_code, 404)

    # Register default computer: deployment works
    self.add_free_partition(1)
    self.request('http://sr//', None, 'MyFirstInstance', 'slappart0')
    computer_default = loads(self.app.get(
        '/getFullComputerInformation?computer_id=%s' % self.computer_id).data)
    self.assertEqual(len(computer_default._software_release_list), 0)

    # No free space on default computer: request without SLA fails
    rv = self._requestComputerPartition('http://sr//', None, 'CanIHasPartition', 'slappart2',
                                        filter_kw={'computer_guid':self.computer_id})
    self.assertEqual(rv._status_code, 404)

  def test_multi_node_support_instance(self):
    """
    Test that instance request behaves correctly with several
    registered computers
    """
    software_release_url = 'http://sr'
    computer_0_id = 'COMP-0'
    computer_1_id = 'COMP-1'
    software_release_1 = 'http://sr//'
    software_release_2 = 'http://othersr//'

    self.add_free_partition(2, computer_id=computer_1_id)

    # Deploy to first non-default computer using SLA
    # It should fail since computer is not registered
    rv = self._requestComputerPartition(software_release_1, None, 'MyFirstInstance', 'slappart2', filter_kw={'computer_guid':computer_0_id})
    self.assertEqual(rv._status_code, 404)

    self.add_free_partition(2, computer_id=computer_0_id)

    # Deploy to first non-default computer using SLA
    partition = self.request(software_release_1, None, 'MyFirstInstance', 'slappart0', filter_kw={'computer_guid':computer_0_id})
    self.assertEqual(partition.getState(), 'started')
    self.assertEqual(partition._partition_id, 'slappart0')
    self.assertEqual(partition._computer_id, computer_0_id)
    # All other instances should be empty
    computer_0 = loads(self.app.get('/getFullComputerInformation?computer_id=COMP-0').data)
    computer_1 = loads(self.app.get('/getFullComputerInformation?computer_id=COMP-1').data)
    self.assertEqual(computer_0._computer_partition_list[0]._software_release_document._software_release, software_release_1)
    self.assertTrue(computer_0._computer_partition_list[1]._software_release_document == None)
    self.assertTrue(computer_1._computer_partition_list[0]._software_release_document == None)
    self.assertTrue(computer_1._computer_partition_list[1]._software_release_document == None)

    # Deploy to second non-default computer using SLA
    partition = self.request(software_release_2, None, 'MySecondInstance', 'slappart0', filter_kw={'computer_guid':computer_1_id})
    self.assertEqual(partition.getState(), 'started')
    self.assertEqual(partition._partition_id, 'slappart0')
    self.assertEqual(partition._computer_id, computer_1_id)
    # The two remaining instances should be free, and MyfirstInstance should still be there
    computer_0 = loads(self.app.get('/getFullComputerInformation?computer_id=COMP-0').data)
    computer_1 = loads(self.app.get('/getFullComputerInformation?computer_id=COMP-1').data)
    self.assertEqual(computer_0._computer_partition_list[0]._software_release_document._software_release, software_release_1)
    self.assertTrue(computer_0._computer_partition_list[1]._software_release_document == None)
    self.assertEqual(computer_1._computer_partition_list[0]._software_release_document._software_release, software_release_2)
    self.assertTrue(computer_1._computer_partition_list[1]._software_release_document == None)

  def test_multi_node_support_change_instance_state(self):
    """
    Test that destroying an instance (i.e change state) from a Computer doesn't
    affect other computer
    """
    software_release_url = 'http://sr'
    computer_0_id = 'COMP-0'
    computer_1_id = 'COMP-1'
    self.add_free_partition(6, computer_id=computer_0_id)
    self.add_free_partition(6, computer_id=computer_1_id)
    partition_first = self.request('http://sr//', None, 'MyFirstInstance', 'slappart0', filter_kw={'computer_guid':computer_0_id})
    partition_second = self.request('http://sr//', None, 'MySecondInstance', 'slappart0', filter_kw={'computer_guid':computer_1_id})

    partition_first = self.request('http://sr//', None, 'MyFirstInstance', 'slappart0', filter_kw={'computer_guid':computer_0_id}, state='stopped')

    computer_0 = loads(self.app.get('/getFullComputerInformation?computer_id=COMP-0').data)
    computer_1 = loads(self.app.get('/getFullComputerInformation?computer_id=COMP-1').data)
    self.assertEqual(computer_0._computer_partition_list[0].getState(), 'stopped')
    self.assertEqual(computer_0._computer_partition_list[1].getState(), 'destroyed')
    self.assertEqual(computer_1._computer_partition_list[0].getState(), 'started')
    self.assertEqual(computer_1._computer_partition_list[1].getState(), 'destroyed')

  def test_multi_node_support_same_reference(self):
    """
    Test that requesting an instance with same reference to two
    different nodes behaves like master: once an instance is assigned to a node,
    changing SLA will not change node.
    """
    software_release_url = 'http://sr'
    computer_0_id = 'COMP-0'
    computer_1_id = 'COMP-1'
    self.add_free_partition(2, computer_id=computer_0_id)
    self.add_free_partition(2, computer_id=computer_1_id)
    partition = self.request('http://sr//', None, 'MyFirstInstance', 'slappart0', filter_kw={'computer_guid':computer_0_id})
    partition = self.request('http://sr//', None, 'MyFirstInstance', 'slappart0', filter_kw={'computer_guid':computer_1_id})

    self.assertEqual(partition._computer_id, computer_0_id)

    computer_1 = loads(self.app.get('/getFullComputerInformation?computer_id=COMP-1').data)
    self.assertTrue(computer_1._computer_partition_list[0]._software_release_document == None)
    self.assertTrue(computer_1._computer_partition_list[1]._software_release_document == None)

  def test_multi_node_support_slave_instance(self):
    """
    Test that slave instances are correctly deployed if SLA is specified
    but deployed only on default computer if not specified (i.e not deployed
    if default computer doesn't have corresponding master instance).
    """
    computer_0_id = 'COMP-0'
    computer_1_id = 'COMP-1'
    self.add_free_partition(2, computer_id=computer_0_id)
    self.add_free_partition(2, computer_id=computer_1_id)
    self.add_free_partition(2)
    self.request('http://sr2//', None, 'MyFirstInstance', 'slappart0', filter_kw={'computer_guid':computer_0_id})
    self.request('http://sr//', None, 'MyOtherInstance', 'slappart0', filter_kw={'computer_guid':computer_1_id})

    # Request slave without SLA: will fail
    rv = self._requestComputerPartition('http://sr//', None, 'MySlaveInstance', 'slappart2', shared=True)
    self.assertEqual(rv._status_code, 404)

    # Request slave with SLA on incorrect computer: will fail
    rv = self._requestComputerPartition('http://sr//', None, 'MySlaveInstance', 'slappart2', shared=True, filter_kw={'computer_guid':computer_0_id})
    self.assertEqual(rv._status_code, 404)

    # Request computer on correct computer: will succeed
    partition = self.request('http://sr//', None, 'MySlaveInstance', 'slappart2', shared=True, filter_kw={'computer_guid':computer_1_id})
    self.assertEqual(partition._computer_id, computer_1_id)

  def test_multi_node_support_instance_guid(self):
    """
    Test that instance_guid support behaves correctly with multiple nodes.
    Warning: proxy doesn't gives unique id of instance, but gives instead unique id
    of partition.
    """
    computer_0_id = 'COMP-0'
    computer_1_id = 'COMP-1'
    self.add_free_partition(2, computer_id=computer_0_id)
    self.add_free_partition(2, computer_id=computer_1_id)
    self.add_free_partition(2)
    partition_computer_0 = self.request('http://sr2//', None, 'MyFirstInstance', 'slappart0', filter_kw={'computer_guid':computer_0_id})
    partition_computer_1 = self.request('http://sr//', None, 'MyOtherInstance', 'slappart0', filter_kw={'computer_guid':computer_1_id})
    partition_computer_default = self.request('http://sr//', None, 'MyThirdInstance', 'slappart0') 

    self.assertEqual(partition_computer_0.getInstanceGuid(), 'COMP-0-slappart0')
    self.assertEqual(partition_computer_1.getInstanceGuid(), 'COMP-1-slappart0')
    self.assertEqual(partition_computer_default.getInstanceGuid(), 'computer-slappart0')

  def test_multi_node_support_getComputerInformation(self):
    """
    Test that computer information will not be given if computer is not registered.
    Test that it still should work for the 'default' computer specified in slapos config
    even if not yet registered.
    Test that computer information is given if computer is registered. 
    """
    new_computer_id = '%s42' % self.computer_id
    with self.assertRaises(slapos.slap.NotFoundError):
      self.app.get('/getComputerInformation?computer_id=%s42' % new_computer_id)

    try:
      self.app.get('/getComputerInformation?computer_id=%s' % self.computer_id)
    except slapos.slap.NotFoundError:
      self.fail('Could not fetch informations for default computer.')

    self.add_free_partition(1, computer_id=new_computer_id)
    try:
      self.app.get('/getComputerInformation?computer_id=%s' % new_computer_id)
    except slapos.slap.NotFoundError:
      self.fail('Could not fetch informations for registered computer.')

