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

import os
import logging
import shutil
import slapos.proxy
import slapos.proxy.views as views
import slapos.slap.slap
import tempfile
import unittest
import xml_marshaller

class WrongFormat(Exception):
  pass

class ProxyOption:
  """
  Will simulate options given to slapproxy
  """
  def __init__(self, proxy_db):
    self.verbose=True
    self.database_uri=proxy_db
    self.console = False
    self.log_file = None

class BasicMixin:
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
"""% dict (tempdir = self._tempdir, proxyaddr = self.proxyaddr))
    for directory in ("opt", "srv", "lib"):
      path = os.path.join(self._tempdir, directory)
      os.mkdir(path)

  def startProxy(self):
    """
    Set config for slapproxy and start it
    """
    config = slapos.proxy.ProxyConfig()
    config.setConfig(*(ProxyOption(self.proxy_db),
                       self.slapos_cfg))
    views.app.config['TESTING'] = True
    views.app.config['computer_id'] = self.computer_id
    views.app.config['DATABASE_URI'] = self.proxy_db
    views.app.config['HOST'] = config.host
    views.app.config['port'] = config.port
    self.app = views.app.test_client()

  def add_free_partition (self, partition_amount):
    """
    Will simulate a slapformat first run
    and create "partition_amount" partitions
    """
    computer_dict = {'reference':self.computer_id,
                     'address':'123.456.789',
                     'netmask':'fffffffff',
                     'partition_list':[]}
    for i in range(0, partition_amount):
      partition_example = {'reference':'slappart%s' %i,
                           'address_list':[]}
      computer_dict['partition_list'].append(partition_example)

    request_dict = { 'computer_id': self.computer_id,
                     'xml': xml_marshaller.xml_marshaller.dumps(computer_dict),
                     }
    self.app.post('/loadComputerConfigurationFromXML',
                       data = request_dict)


  def tearDown(self):
    """
    Remove files generated for test
    """
    shutil.rmtree(self._tempdir, True)


class TestInformation(BasicMixin, unittest.TestCase):
  """
  Test Basic response of slapproxy
  """

  def test_getComputerInformation (self):
    """
    Check that getComputerInformation return a Computer
    and database is generated
    """
    rv = self.app.get('/getComputerInformation?computer_id='
                      +self.computer_id)
    self.assertIsInstance(
      xml_marshaller.xml_marshaller.loads(rv.data),
      slapos.slap.Computer)
    self.assertTrue(os.path.exists(self.proxy_db))

  def test_getFullComputerInformation (self):
    """
    Check that getFullComputerInformation return a Computer
    and database is generated
    """
    rv = self.app.get('/getFullComputerInformation?computer_id='
                      + self.computer_id)
    self.assertIsInstance(
      xml_marshaller.xml_marshaller.loads(rv.data),
      slapos.slap.Computer)
    self.assertTrue(os.path.exists(self.proxy_db))

  def test_getComputerInformation_wrong_computer (self):
    """
    Test that computer information won't be given to a requester different
    from the one specified
    """
    with self.assertRaises(slapos.slap.NotFoundError):
      self.app.get('/getComputerInformation?computer_id='
                      + self.computer_id + '42')

  def test_partition_are_empty (self):
    """
    Test that empty partition are empty :)
    """
    self.add_free_partition(10)
    rv = self.app.get('/getFullComputerInformation?computer_id='
                      + self.computer_id)
    computer = xml_marshaller.xml_marshaller.loads(rv.data)
    for slap_partition in computer._computer_partition_list:
        self.assertIsNone(slap_partition._software_release_document)
        self.assertEqual(slap_partition._requested_state, 'destroyed')
        self.assertEqual(slap_partition._need_modification, 0)



class MasterMixin(BasicMixin):
  """
  Define advanced tool for test proxy simulating behavior slap library tools
  """

  def request(self, software_release, software_type, partition_reference,
              partition_id,
              shared=False, partition_parameter_kw=None, filter_kw=None,
              state=None):
    """
    Simulate a request with above parameters
    Return response by server (a computer partition or an error)
    """
    if partition_parameter_kw is None:
      partition_parameter_kw = {}
    if filter_kw is None:
      filter_kw = {}
   # Let enforce a default software type
    if software_type is None:
      software_type = 'default'

    request_dict = { 'computer_id': self.computer_id,
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
    rv = self.app.post('/requestComputerPartition',
                       data = request_dict)
    xml = rv.data
    try:
      software_instance = xml_marshaller.xml_marshaller.loads(xml)
    except:
      raise WrongFormat("Could not be parsed by xml_marshaller")

    computer_partition = slapos.slap.ComputerPartition(
      software_instance.slap_computer_id,
      software_instance.slap_computer_partition_id,
      )
    if shared:
      computer_partition._synced = True
      computer_partition._connection_dict = getattr(software_instance,
                                                  '_connection_dict', None)
      computer_partition._parameter_dict = getattr(software_instance,
                                                 '_parameter_dict', None)
    return computer_partition


  def setConnectionDict(self, partition_id,
                        connection_dict, slave_reference=None):
    self.app.post('/setComputerPartitionConnectionXml', data = {
        'computer_id': self.computer_id,
        'computer_partition_id': partition_id,
        'connection_xml': xml_marshaller.xml_marshaller.dumps(connection_dict),
        'slave_reference': slave_reference})

  def getPartitionInformation(self,computer_partition_id):
    """
    Return computer information as stored in proxy for corresponding id
    """
    rv = self.app.get('/getFullComputerInformation?computer_id='
                      + self.computer_id)
    computer = xml_marshaller.xml_marshaller.loads(rv.data)
    for instance in computer._computer_partition_list:
      if instance._partition_id == computer_partition_id:
        return instance


class TestRequest (MasterMixin, unittest.TestCase):
  """
  Set of tests for requests
  """
  def test_two_request_one_partition_free (self):
    """
    Since slapproxy does not implement scope, providing two partition_id
    values will still succeed, even if only one partition is available.
    """
    self.add_free_partition(1)
    self.assertIsInstance(self.request('http://sr//', None,
                                       'Maria', 'slappart2'),
                          slapos.slap.ComputerPartition)
    self.assertIsInstance(self.request('http://sr//', None,
                                       'Maria', 'slappart3'),
                          slapos.slap.ComputerPartition)

  def test_two_request_two_partition_free (self):
    """
    If two requests are made with two available partition
    both will succeed
    """
    self.add_free_partition(2)
    self.assertIsInstance(self.request('http://sr//', None,
                                       'Maria', 'slappart2'),
                          slapos.slap.ComputerPartition)
    self.assertIsInstance(self.request('http://sr//', None,
                                       'Maria', 'slappart3'),
                          slapos.slap.ComputerPartition)

  def test_two_same_request_from_one_partition (self):
    """
    Request will return same partition for two equal requests
    """
    self.add_free_partition(2)
    self.assertEqual(
      self.request('http://sr//', None, 'Maria', 'slappart2').__dict__,
      self.request('http://sr//', None, 'Maria', 'slappart2').__dict__)

  def test_two_requests_with_different_parameters_but_same_reference (self):
    """
    Request will return same partition for two different requests but will
    only update parameters
    """
    self.add_free_partition(2)
    wanted_domain1 = 'fou.org'
    wanted_domain2 = 'carzy.org'

    request1 = self.request('http://sr//', None, 'Maria', 'slappart2',
                            partition_parameter_kw = {'domain':wanted_domain1})
    request1_dict = request1.__dict__
    requested_result1 = self.getPartitionInformation(
      request1_dict['_partition_id'])
    request2 = self.request('http://sr1//', 'Papa', 'Maria', 'slappart2',
                            partition_parameter_kw = {'domain':wanted_domain2})
    request2_dict = request2.__dict__
    requested_result2 = self.getPartitionInformation(
      request2_dict['_partition_id'])
    # Test we received same partition
    for key in request1_dict:
      self.assertEqual(request1_dict[key],request2_dict[key])
    # Test that only parameters changed
    for key in requested_result2.__dict__ :
      if not key in ('_parameter_dict',
                     '_software_release_document'):
        self.assertEqual(requested_result2.__dict__[key],
                         requested_result1.__dict__[key])
      elif key in ('_software_release_document'):
        self.assertEqual(requested_result2.__dict__[key].__dict__,
                         requested_result1.__dict__[key].__dict__)
    #Test parameters where set correctly
    self.assertEqual(wanted_domain1,
                     requested_result1._parameter_dict['domain'])
    self.assertEqual(wanted_domain2,
                     requested_result2._parameter_dict['domain'])

  def test_two_different_request_from_two_partition (self):
    """
    Since slapproxy does not implement scope, two request with
    different partition_id will still return the same partition.
    """
    self.add_free_partition(2)
    self.assertEqual(
      self.request('http://sr//', None, 'Maria', 'slappart2').__dict__,
      self.request('http://sr//', None, 'Maria', 'slappart3').__dict__)

  def test_two_different_request_from_one_partition (self):
    """
    Two different request from same partition
    will return two different partitions
    """
    self.add_free_partition(2)
    self.assertNotEqual(
      self.request('http://sr//', None, 'Maria', 'slappart2').__dict__,
      self.request('http://sr//', None, 'frontend', 'slappart2').__dict__)

  def test_slave_request_no_corresponding_partition (self):
    """
    Slave instance request will fail if no corresponding are found
    """
    self.add_free_partition(2)
    with self.assertRaises(WrongFormat):
      self.request('http://sr//', None, 'Maria', 'slappart2', shared=True)

  def test_slave_request_set_parameters (self):
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
                                    'Maria', 'slappart4')._partition_id
    # First request of slave instance
    wanted_domain = 'fou.org'
    self.request('http://sr//', None, 'Maria', 'slappart2', shared=True,
                 partition_parameter_kw = {'domain':wanted_domain})
    # Get updated information for master partition
    master_partition = self.getPartitionInformation(master_partition_id)

    our_slave = master_partition._parameter_dict['slave_instance_list'][0]
    self.assertEqual(our_slave.get('domain'),wanted_domain)

  def test_slave_request_set_parameters_are_updated (self):
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
                                    'Maria', 'slappart4')._partition_id
    # First request of slave instance
    wanted_domain_1 = 'crazy.org'
    self.request('http://sr//', None, 'Maria', 'slappart2', shared=True,
                 partition_parameter_kw = {'domain':wanted_domain_1})
    # Get updated information for master partition
    master_partition = self.getPartitionInformation(master_partition_id)
    our_slave = master_partition._parameter_dict['slave_instance_list'][0]
    self.assertEqual(our_slave.get('domain'),wanted_domain_1)

    # Second request of slave instance
    wanted_domain_2 = 'maluco.org'
    self.request('http://sr//', None, 'Maria', 'slappart2', shared=True,
                 partition_parameter_kw = {'domain':wanted_domain_2})
    # Get updated information for master partition
    master_partition = self.getPartitionInformation(master_partition_id)

    our_slave = master_partition._parameter_dict['slave_instance_list'][0]
    self.assertNotEqual(our_slave.get('domain'),wanted_domain_1)
    self.assertEqual(our_slave.get('domain'),wanted_domain_2)


  def test_slave_request_one_corresponding_partition (self):
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
                                    'Maria', 'slappart4')._partition_id
    # First request of slave instance
    name = 'Maria'
    requester = 'slappart2'
    our_slave  = self.request('http://sr//', None,
                              name, requester, shared=True)
    self.assertIsInstance(our_slave, slapos.slap.ComputerPartition)
    self.assertEqual(our_slave._connection_dict,{})
    # Get updated information for master partition
    master_partition = self.getPartitionInformation(master_partition_id)
    slave_for_master = master_partition._parameter_dict['slave_instance_list'][0]
    # Send information about slave
    slave_address = {'url':'%s.master.com'}
    self.setConnectionDict(partition_id=master_partition._partition_id,
                           connection_dict=slave_address,
                           slave_reference=slave_for_master['slave_reference'])
    # Successfull slave request with connection parameters
    our_slave  = self.request('http://sr//', None,
                              name, requester, shared=True)
    self.assertIsInstance(our_slave, slapos.slap.ComputerPartition)
    self.assertEqual(slave_address, our_slave._connection_dict)
