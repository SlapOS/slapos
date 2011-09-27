##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
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
import xml_marshaller
import unittest
import urlparse
import httplib
import slapos.slap
import os

class UndefinedYetException(Exception):
  """To catch exceptions which are not yet defined"""

class SlapMixin(unittest.TestCase):
  """
  Usefull methods for slap tests
  """
  def setUp(self):
    self._server_url = os.environ.get('TEST_SLAP_SERVER_URL', None)
    if self._server_url is None:
      self._patchHttplib()
      self.server_url = 'http://localhost/'
    else:
      self.server_url = self._server_url

  def tearDown(self):
    if self._server_url is None:
      self._unpatchHttplib()

  def _patchHttplib(self):
    """Overrides httplib"""
    import mock.httplib

    self.saved_httplib = dict()

    for fake in vars(mock.httplib):
      self.saved_httplib[fake] = getattr(httplib, fake, None)
      setattr(httplib, fake, getattr(mock.httplib, fake))

  def _unpatchHttplib(self):
    """Restores httplib overriding"""
    import httplib
    for name, original_value in self.saved_httplib.items():
      setattr(httplib, name, original_value)
    del self.saved_httplib

  def _getTestComputerId(self):
    """
    Returns the computer id used by the test
    """
    return self.id()
    return os.environ.get('TEST_SLAP_COMPUTER_ID', self.id())

class TestSlap(SlapMixin):
  """
  Test slap against slap server
  """

  def test_slap_initialisation(self):
    """
    Asserts that slap initialisation works properly in case of 
    passing correct url
    """
    slap_instance = slapos.slap.slap()
    slap_instance.initializeConnection(self.server_url)
    self.assertTrue(slapos.slap.SlapDocument._connection_helper.host in self.server_url)
    self.assertTrue(slapos.slap.SlapDocument._connection_helper.path in self.server_url)

  def test_slap_initialisation_wrong_url(self):
    """
    Asserts that slap initialisation raises exception when passed url 
    is not correct
    """
    server_url = 'https://user:pass@server/path/path?parameter=notAcceptable'
    slap_instance = slapos.slap.slap()
    self.assertRaises(AttributeError, 
                      slap_instance.initializeConnection, server_url)

  def test_registerComputer_with_new_guid(self):
    """
    Asserts that calling slap.registerComputer with new guid returns 
    Computer object
    """
    computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    self.assertTrue(isinstance(computer, slapos.slap.Computer))

  def test_registerComputer_with_existing_guid(self):
    """
    Asserts that calling slap.registerComputer with already used guid 
    returns Computer object
    """
    computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    self.assertTrue(isinstance(computer, slapos.slap.Computer))

    computer2 = self.slap.registerComputer(computer_guid)
    self.assertTrue(isinstance(computer2, slapos.slap.Computer))

  # XXX: There is naming conflict in slap library.
  # SoftwareRelease is currently used as suboject of Slap transmission object
  def test_registerSoftwareRelease_with_new_uri(self):
    """
    Asserts that calling slap.registerSoftwareRelease with new guid 
    returns SoftwareRelease object
    """
    software_release_uri = 'http://server/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    software_release = self.slap.registerSoftwareRelease(software_release_uri)
    self.assertTrue(isinstance(software_release,
        slapos.slap.SoftwareRelease))

  def test_registerSoftwareRelease_with_existing_uri(self):
    """
    Asserts that calling slap.registerSoftwareRelease with already 
    used guid returns SoftwareRelease object
    """
    software_release_uri = 'http://server/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    software_release = self.slap.registerSoftwareRelease(software_release_uri)
    self.assertTrue(isinstance(software_release,
        slapos.slap.SoftwareRelease))

    software_release2 = self.slap.registerSoftwareRelease(software_release_uri)
    self.assertTrue(isinstance(software_release2,
        slapos.slap.SoftwareRelease))

  def test_registerComputerPartition_new_partition_id_known_computer_guid(self):
    """
    Asserts that calling slap.registerComputerPartition on known computer 
    returns ComputerPartition object
    """
    self.computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    self.partition_id = 'PARTITION_01'
    self.slap.registerComputer(self.computer_guid)

    partition = self.slap.registerComputerPartition(self.computer_guid, 
                                                    self.partition_id)
    self.assertTrue(isinstance(partition, slapos.slap.ComputerPartition))

  def test_registerComputerPartition_existing_partition_id_known_computer_guid(self):
    """
    Asserts that calling slap.registerComputerPartition on known computer 
    returns ComputerPartition object
    """
    self.test_registerComputerPartition_new_partition_id_known_computer_guid()
    partition = self.slap.registerComputerPartition(self.computer_guid,
        self.partition_id)
    self.assertTrue(isinstance(partition, slapos.slap.ComputerPartition))

  def test_registerComputerPartition_unknown_computer_guid(self):
    """
    Asserts that calling slap.registerComputerPartition on unknown 
    computer raises (not defined yet) exception
    """
    computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)

    partition_id = 'PARTITION_01'

    self.assertRaises(UndefinedYetException,
        self.slap.registerComputerPartition, computer_guid, partition_id)

class TestComputer(SlapMixin):
  """
  Tests slapos.slap.slap.Computer class functionality
  """

  def test_computer_getComputerPartitionList_no_partition(self):
    """
    Asserts that calling Computer.getComputerPartitionList without Computer
    Partitions returns empty list
    """
    self.computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    self.computer = self.slap.registerComputer(self.computer_guid)
    self.assertEqual(self.computer.getComputerPartitionList(), [])

  def test_computer_getComputerPartitionList_only_partition(self):
    """
    Asserts that calling Computer.getComputerPartitionList with only 
    Computer Partitions returns empty list
    """
    self.computer_guid = self._getTestComputerId()
    partition_id = 'PARTITION_01'
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    self.computer = self.slap.registerComputer(self.computer_guid)
    self.partition = self.slap.registerComputerPartition(self.computer_guid,
        partition_id)
    self.assertEqual(self.computer.getComputerPartitionList(), [])

  def test_computer_reportUsage_non_valid_xml_raises(self):
    """
    Asserts that calling Computer.reportUsage with non DTD 
    (not defined yet) XML raises (not defined yet) exception
    """
    self.computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    self.computer = self.slap.registerComputer(self.computer_guid)
    non_dtd_xml = """<xml>
<non-dtd-parameter name="xerxes">value<non-dtd-parameter name="xerxes">
</xml>"""
    self.assertRaises(UndefinedYetException, self.computer.reportUsage,
        non_dtd_xml)

  def test_computer_reportUsage_valid_xml_invalid_partition_raises(self):
    """
    Asserts that calling Computer.reportUsage with DTD (not defined 
    yet) XML which refers to invalid partition raises (not defined yet)
    exception
    """
    self.computer_guid = self._getTestComputerId()
    partition_id = 'PARTITION_01'
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    self.computer = self.slap.registerComputer(self.computer_guid)
    self.partition = self.slap.registerComputerPartition(self.computer_guid,
        partition_id)
    # XXX: As DTD is not defined currently proper XML is not known
    bad_partition_dtd_xml = """<xml>
<computer-partition id='ANOTHER_PARTITION>96.5% CPU</computer-partition>
</xml>"""
    self.assertRaises(UndefinedYetException, self.computer.reportUsage,
        bad_partition_dtd_xml)

class RequestWasCalled(Exception):
  pass

class TestComputerPartition(SlapMixin):
  """
  Tests slapos.slap.slap.ComputerPartition class functionality
  """

  def test_request_sends_request(self):
    partition_id = 'PARTITION_01'
    request_called_amount = 0
    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'registerComputerPartition' and \
         'computer_reference' in parsed_qs and \
         'computer_partition_reference' in parsed_qs:
        slap_partition = slapos.slap.ComputerPartition(
          parsed_qs['computer_reference'][0],
          parsed_qs['computer_partition_reference'][0])
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_partition))
      elif parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        slap_partition = slapos.slap.ComputerPartition(
          parsed_qs['computer_id'][0],
          partition_id)
        slap_computer._computer_partition_list = [slap_partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      elif parsed_url.path == 'requestComputerPartition':
        raise RequestWasCalled
      else:
        return (404, {}, '')
    httplib.HTTPConnection._callback = server_response
    self.computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        self.computer_guid, partition_id)
    self.assertRaises(RequestWasCalled, computer_partition.request,
        'http://server/new/' + self._getTestComputerId(),
        'software_type',
        'myref')

  def test_request_not_raises(self):
    partition_id = 'PARTITION_01'
    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'registerComputerPartition' and \
         'computer_reference' in parsed_qs and \
         'computer_partition_reference' in parsed_qs:
        slap_partition = slapos.slap.ComputerPartition(
          parsed_qs['computer_reference'][0],
          parsed_qs['computer_partition_reference'][0])
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_partition))
      elif parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        slap_partition = slapos.slap.ComputerPartition(
          parsed_qs['computer_id'][0],
          partition_id)
        slap_computer._computer_partition_list = [slap_partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      elif parsed_url.path == 'requestComputerPartition':
        return (408, {}, '')
      else:
        return (404, {}, '')
    httplib.HTTPConnection._callback = server_response
    self.computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        self.computer_guid, partition_id)
    requested_partition = computer_partition.request(
        'http://server/new/' + self._getTestComputerId(),
        'software_type',
        'myref')
    self.assertTrue(isinstance(requested_partition,
        slapos.slap.ComputerPartition))

  def test_request_raises_later(self):
    partition_id = 'PARTITION_01'
    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'registerComputerPartition' and \
         'computer_reference' in parsed_qs and \
         'computer_partition_reference' in parsed_qs:
        slap_partition = slapos.slap.ComputerPartition(
          parsed_qs['computer_reference'][0],
          parsed_qs['computer_partition_reference'][0])
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_partition))
      elif parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        slap_partition = slapos.slap.ComputerPartition(
          parsed_qs['computer_id'][0],
          partition_id)
        slap_computer._computer_partition_list = [slap_partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      elif parsed_url.path == 'requestComputerPartition':
        return (408, {}, '')
      else:
        return (404, {}, '')
    httplib.HTTPConnection._callback = server_response
    self.computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        self.computer_guid, partition_id)
    requested_partition = computer_partition.request(
        'http://server/new/' + self._getTestComputerId(),
        'software_type',
        'myref')
    self.assertTrue(isinstance(requested_partition,
        slapos.slap.ComputerPartition))
    # as request method does not raise, accessing data raises
    self.assertRaises(slapos.slap.ResourceNotReady, requested_partition.getId)

  def test_request_fullfilled_work(self):
    partition_id = 'PARTITION_01'
    requested_partition_id = 'PARTITION_02'
    computer_guid = self._getTestComputerId()
    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'registerComputerPartition' and \
         'computer_reference' in parsed_qs and \
         'computer_partition_reference' in parsed_qs:
        slap_partition = slapos.slap.ComputerPartition(
          parsed_qs['computer_reference'][0],
          parsed_qs['computer_partition_reference'][0])
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_partition))
      elif parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        slap_partition = slapos.slap.ComputerPartition(
          parsed_qs['computer_id'][0],
          partition_id)
        slap_computer._computer_partition_list = [slap_partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      elif parsed_url.path == 'requestComputerPartition':
        from slapos.slap.slap import SoftwareInstance
        slap_partition = SoftwareInstance(
          slap_computer_id=computer_guid,
          slap_computer_partition_id=requested_partition_id)
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_partition))
      else:
        return (404, {}, '')
    httplib.HTTPConnection._callback = server_response
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        computer_guid, partition_id)
    requested_partition = computer_partition.request(
        'http://server/new/' + self._getTestComputerId(),
        'software_type',
        'myref')
    self.assertTrue(isinstance(requested_partition,
        slapos.slap.ComputerPartition))
    # as request method does not raise, accessing data in case when
    # request was done works correctly
    self.assertEqual(requested_partition_id, requested_partition.getId())

  def _test_new_computer_partition_state(self, state):
    """
    Helper method to automate assertions of failing states on new Computer 
    Partition
    """
    self.computer_guid = self._getTestComputerId()
    partition_id = 'PARTITION_01'
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        self.computer_guid, partition_id)
    method = getattr(computer_partition, state)
    self.assertRaises(UndefinedYetException, method)

  def test_available_new_ComputerPartition_raises(self):
    """
    Asserts that calling ComputerPartition.available on new partition 
    raises (not defined yet) exception
    """
    self._test_new_computer_partition_state('available')

  def test_building_new_ComputerPartition_raises(self):
    """
    Asserts that calling ComputerPartition.building on new partition raises 
    (not defined yet) exception
    """
    self._test_new_computer_partition_state('building')

  def test_started_new_ComputerPartition_raises(self):
    """
    Asserts that calling ComputerPartition.started on new partition raises 
    (not defined yet) exception
    """
    self._test_new_computer_partition_state('started')

  def test_stopped_new_ComputerPartition_raises(self):
    """
    Asserts that calling ComputerPartition.stopped on new partition raises 
    (not defined yet) exception
    """
    self._test_new_computer_partition_state('stopped')

  def test_error_new_ComputerPartition_works(self):
    """
    Asserts that calling ComputerPartition.error on new partition works
    """
    self.computer_guid = self._getTestComputerId()
    partition_id = 'PARTITION_01'
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer_partition = self.slap.registerComputerPartition(
        self.computer_guid, partition_id)
    # XXX: Interface does not define return value
    computer_partition.error('some error')

class TestSoftwareRelease(SlapMixin):
  """
  Tests slap.SoftwareRelease class functionality
  """

  def _test_new_software_release_state(self, state):
    """
    Helper method to automate assertions of failing states on new Software 
    Release
    """
    self.software_release_uri = 'http://server/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    software_release = self.slap.registerSoftwareRelease(
        self.software_release_uri)
    method = getattr(software_release, state)
    self.assertRaises(UndefinedYetException, method)

  def test_available_new_SoftwareRelease_raises(self):
    """
    Asserts that calling SoftwareRelease.available on new software release 
    raises (not defined yet) exception
    """
    self._test_new_software_release_state('available')

  def test_building_new_SoftwareRelease_raises(self):
    """
    Asserts that calling SoftwareRelease.building on new software release 
    raises (not defined yet) exception
    """
    self._test_new_software_release_state('building')

  def test_error_new_SoftwareRelease_works(self):
    """
    Asserts that calling SoftwareRelease.error on new software release works
    """
    self.software_release_uri = 'http://server/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    software_release = self.slap.registerSoftwareRelease(
        self.software_release_uri)
    # XXX: Interface does not define return value
    software_release.error('some error')

class TestOpenOrder(SlapMixin):
  def test_request_sends_request(self):
    software_release_uri = 'http://server/new/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    # XXX: Interface lack registerOpenOrder method declaration
    open_order = self.slap.registerOpenOrder()
    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      if parsed_url.path == 'requestComputerPartition':
        raise RequestWasCalled
    httplib.HTTPConnection._callback = server_response
    self.assertRaises(RequestWasCalled, open_order.request, software_release_uri, 'myrefe')

  def test_request_not_raises(self):
    software_release_uri = 'http://server/new/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    # XXX: Interface lack registerOpenOrder method declaration
    open_order = self.slap.registerOpenOrder()
    computer_partition = open_order.request(software_release_uri, 'myrefe')
    self.assertTrue(isinstance(computer_partition,
        slapos.slap.ComputerPartition))

  def test_request_raises_later(self):
    software_release_uri = 'http://server/new/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    # XXX: Interface lack registerOpenOrder method declaration
    open_order = self.slap.registerOpenOrder()
    def server_response(self, path, method, body, header):
      return (408, {}, '')
    httplib.HTTPConnection._callback = server_response
    computer_partition = open_order.request(software_release_uri, 'myrefe')
    self.assertTrue(isinstance(computer_partition,
        slapos.slap.ComputerPartition))

    self.assertRaises(slapos.slap.ResourceNotReady, computer_partition.getId)

  def test_request_fullfilled_work(self):
    software_release_uri = 'http://server/new/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    # XXX: Interface lack registerOpenOrder method declaration
    open_order = self.slap.registerOpenOrder()
    computer_guid = self._getTestComputerId()
    requested_partition_id = 'PARTITION_01'
    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      from slapos.slap.slap import SoftwareInstance
      slap_partition = SoftwareInstance(
        slap_computer_id=computer_guid,
        slap_computer_partition_id=requested_partition_id)
      return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_partition))
    httplib.HTTPConnection._callback = server_response

    computer_partition = open_order.request(software_release_uri, 'myrefe')
    self.assertTrue(isinstance(computer_partition,
        slapos.slap.ComputerPartition))
    self.assertTrue(requested_partition_id, computer_partition.getId())

if __name__ == '__main__':
  print 'Testing against SLAP server %r' % SERVER_URL
  print 'You can point to any SLAP server by setting TEST_SLAP_SERVER_URL '\
      'environment variable'
  unittest.main()
