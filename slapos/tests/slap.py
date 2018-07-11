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

import logging
import os
import unittest
import urlparse
import tempfile

import httmock

import slapos.slap
import xml_marshaller


class UndefinedYetException(Exception):
  """To catch exceptions which are not yet defined"""


class SlapMixin(unittest.TestCase):
  """
  Useful methods for slap tests
  """
  def setUp(self):
    self._server_url = os.environ.get('TEST_SLAP_SERVER_URL', None)
    if self._server_url is None:
      self.server_url = 'http://localhost/'
    else:
      self.server_url = self._server_url
    print 'Testing against SLAP server %r' % self.server_url
    self.slap = slapos.slap.slap()
    self.partition_id = 'PARTITION_01'
    if os.environ.has_key('SLAPGRID_INSTANCE_ROOT'):
      del os.environ['SLAPGRID_INSTANCE_ROOT']

  def tearDown(self):
    pass

  def _getTestComputerId(self):
    """
    Returns the computer id used by the test
    """
    return self.id()


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
    self.assertEquals(slap_instance._connection_helper.slapgrid_uri, self.server_url)

  def test_slap_initialisation_ipv6_and_port(self):
    slap_instance = slapos.slap.slap()
    slap_instance.initializeConnection("http://fe80:1234:1234:1234:1:1:1:1:5000/foo/")
    self.assertEqual(
        slap_instance._connection_helper.slapgrid_uri,
        "http://[fe80:1234:1234:1234:1:1:1:1]:5000/foo/"
    )

  def test_slap_initialisation_ipv6_without_port(self):
    slap_instance = slapos.slap.slap()
    slap_instance.initializeConnection("http://fe80:1234:1234:1234:1:1:1:1/foo/")
    self.assertEqual(
        slap_instance._connection_helper.slapgrid_uri,
        "http://[fe80:1234:1234:1234:1:1:1:1]/foo/"
    )

  def test_slap_initialisation_ipv6_with_bracket(self):
    slap_instance = slapos.slap.slap()
    slap_instance.initializeConnection("http://[fe80:1234:1234:1234:1:1:1:1]:5000/foo/")
    self.assertEqual(
        slap_instance._connection_helper.slapgrid_uri,
        "http://[fe80:1234:1234:1234:1:1:1:1]:5000/foo/"
    )

  def test_slap_initialisation_ipv4(self):
    slap_instance = slapos.slap.slap()
    slap_instance.initializeConnection("http://127.0.0.1:5000/foo/")
    self.assertEqual(
        slap_instance._connection_helper.slapgrid_uri,
        "http://127.0.0.1:5000/foo/"
    )

  def test_slap_initialisation_hostname(self):
    # XXX this really opens a connection !
    slap_instance = slapos.slap.slap()
    slap_instance.initializeConnection("http://example.com:80/foo/")
    self.assertEqual(
        slap_instance._connection_helper.slapgrid_uri,
        "http://example.com:80/foo/"
    )

  def test_registerComputer_with_new_guid(self):
    """
    Asserts that calling slap.registerComputer with new guid returns
    Computer object
    """
    computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    self.assertIsInstance(computer, slapos.slap.Computer)

  def test_registerComputer_with_existing_guid(self):
    """
    Asserts that calling slap.registerComputer with already used guid
    returns Computer object
    """
    computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    computer = self.slap.registerComputer(computer_guid)
    self.assertIsInstance(computer, slapos.slap.Computer)

    computer2 = self.slap.registerComputer(computer_guid)
    self.assertIsInstance(computer2, slapos.slap.Computer)

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
    self.assertIsInstance(software_release, slapos.slap.SoftwareRelease)

  def test_registerSoftwareRelease_with_existing_uri(self):
    """
    Asserts that calling slap.registerSoftwareRelease with already
    used guid returns SoftwareRelease object
    """
    software_release_uri = 'http://server/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    software_release = self.slap.registerSoftwareRelease(software_release_uri)
    self.assertIsInstance(software_release, slapos.slap.SoftwareRelease)

    software_release2 = self.slap.registerSoftwareRelease(software_release_uri)
    self.assertIsInstance(software_release2, slapos.slap.SoftwareRelease)

  def test_registerComputerPartition_new_partition_id_known_computer_guid(self):
    """
    Asserts that calling slap.registerComputerPartition on known computer
    returns ComputerPartition object
    """
    computer_guid = self._getTestComputerId()
    partition_id = self.partition_id
    self.slap.initializeConnection(self.server_url)
    self.slap.registerComputer(computer_guid)

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/registerComputerPartition'
            and qs == {
                'computer_reference': [computer_guid],
                'computer_partition_reference': [partition_id]
                }):
        partition = slapos.slap.ComputerPartition(computer_guid, partition_id)
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(partition)
                }
      else:
        return {'status_code': 400}

    self._handler = handler

    with httmock.HTTMock(handler):
      partition = self.slap.registerComputerPartition(computer_guid, partition_id)
      self.assertIsInstance(partition, slapos.slap.ComputerPartition)

  def test_registerComputerPartition_existing_partition_id_known_computer_guid(self):
    """
    Asserts that calling slap.registerComputerPartition on known computer
    returns ComputerPartition object
    """
    self.test_registerComputerPartition_new_partition_id_known_computer_guid()
    with httmock.HTTMock(self._handler):
      partition = self.slap.registerComputerPartition(self._getTestComputerId(),
                                                      self.partition_id)
      self.assertIsInstance(partition, slapos.slap.ComputerPartition)

  def test_registerComputerPartition_unknown_computer_guid(self):
    """
    Asserts that calling slap.registerComputerPartition on unknown
    computer raises NotFoundError exception
    """
    computer_guid = self._getTestComputerId()
    self.slap.initializeConnection(self.server_url)
    partition_id = 'PARTITION_01'

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/registerComputerPartition'
            and qs == {
                'computer_reference': [computer_guid],
                'computer_partition_reference': [partition_id]
                }):
        return {'status_code': 404}
      else:
        return {'status_code': 0}

    with httmock.HTTMock(handler):
      self.assertRaises(slapos.slap.NotFoundError,
                        self.slap.registerComputerPartition,
                        computer_guid, partition_id)


  def test_getFullComputerInformation_empty_computer_guid(self):
    """
    Asserts that calling getFullComputerInformation with empty computer_id
    raises early, before calling master.
    """
    self.slap.initializeConnection(self.server_url)

    def handler(url, req):
      # Shouldn't even be called
      self.assertFalse(True)

    with httmock.HTTMock(handler):
      self.assertRaises(slapos.slap.NotFoundError,
                        self.slap._connection_helper.getFullComputerInformation,
                        None)

  def test_registerComputerPartition_empty_computer_guid(self):
    """
    Asserts that calling registerComputerPartition with empty computer_id
    raises early, before calling master.
    """
    self.slap.initializeConnection(self.server_url)

    def handler(url, req):
      # Shouldn't even be called
      self.assertFalse(True)

    with httmock.HTTMock(handler):
      self.assertRaises(slapos.slap.NotFoundError,
                        self.slap.registerComputerPartition,
                        None, 'PARTITION_01')

  def test_registerComputerPartition_empty_computer_partition_id(self):
    """
    Asserts that calling registerComputerPartition with empty
    computer_partition_id raises early, before calling master.
    """
    self.slap.initializeConnection(self.server_url)

    def handler(url, req):
      # Shouldn't even be called
      self.assertFalse(True)

    with httmock.HTTMock(handler):
      self.assertRaises(slapos.slap.NotFoundError,
                        self.slap.registerComputerPartition,
                        self._getTestComputerId(), None)

  def test_registerComputerPartition_empty_computer_guid_empty_computer_partition_id(self):
    """
    Asserts that calling registerComputerPartition with empty
    computer_partition_id raises early, before calling master.
    """
    self.slap.initializeConnection(self.server_url)

    def handler(url, req):
      # Shouldn't even be called
      self.assertFalse(True)

    with httmock.HTTMock(handler):
      self.assertRaises(slapos.slap.NotFoundError,
                        self.slap.registerComputerPartition,
                        None, None)


  def test_getSoftwareReleaseListFromSoftwareProduct_software_product_reference(self):
    """
    Check that slap.getSoftwareReleaseListFromSoftwareProduct calls
    "/getSoftwareReleaseListFromSoftwareProduct" URL with correct parameters,
    with software_product_reference parameter being specified.
    """
    self.slap.initializeConnection(self.server_url)
    software_product_reference = 'random_reference'
    software_release_url_list = ['1', '2']

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/getSoftwareReleaseListFromSoftwareProduct'
            and qs == {'software_product_reference': [software_product_reference]}):
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(software_release_url_list)
                }

    with httmock.HTTMock(handler):
      self.assertEqual(
        self.slap.getSoftwareReleaseListFromSoftwareProduct(
          software_product_reference=software_product_reference),
        software_release_url_list
      )

  def test_getSoftwareReleaseListFromSoftwareProduct_software_release_url(self):
    """
    Check that slap.getSoftwareReleaseListFromSoftwareProduct calls
    "/getSoftwareReleaseListFromSoftwareProduct" URL with correct parameters,
    with software_release_url parameter being specified.
    """
    self.slap.initializeConnection(self.server_url)
    software_release_url = 'random_url'
    software_release_url_list = ['1', '2']

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/getSoftwareReleaseListFromSoftwareProduct'
         and qs == {'software_release_url': [software_release_url]}):
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(software_release_url_list)
                }

    with httmock.HTTMock(handler):
      self.assertEqual(
        self.slap.getSoftwareReleaseListFromSoftwareProduct(
            software_release_url=software_release_url),
        software_release_url_list
      )

  def test_getSoftwareReleaseListFromSoftwareProduct_too_many_parameters(self):
    """
    Check that slap.getSoftwareReleaseListFromSoftwareProduct raises if
    both parameters are set.
    """
    self.assertRaises(
      AttributeError,
      self.slap.getSoftwareReleaseListFromSoftwareProduct, 'foo', 'bar'
    )

  def test_getSoftwareReleaseListFromSoftwareProduct_no_parameter(self):
    """
    Check that slap.getSoftwareReleaseListFromSoftwareProduct raises if
    both parameters are either not set or None.
    """
    self.assertRaises(
      AttributeError,
      self.slap.getSoftwareReleaseListFromSoftwareProduct
    )

  def test_initializeConnection_getHateoasUrl(self):
    """
    Test that by default, slap will try to fetch Hateoas URL from XML/RPC URL.
    """
    hateoas_url = 'foo'
    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/getHateoasUrl'):
        return {
                'status_code': 200,
                'content': hateoas_url
                }

    with httmock.HTTMock(handler):
      self.slap.initializeConnection('http://%s' % self.id())
    self.assertEqual(
        self.slap._hateoas_navigator.slapos_master_hateoas_uri,
        hateoas_url
    )

  def test_initializeConnection_specifiedHateoasUrl(self):
    """
    Test that if rest URL is specified, slap will NOT try to fetch
    Hateoas URL from XML/RPC URL.
    """
    hateoas_url = 'foo'
    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/getHateoasUrl'):
        self.fail('slap should not have contacted master to get Hateoas URL.')

    with httmock.HTTMock(handler):
      self.slap.initializeConnection('http://%s' % self.id(), slapgrid_rest_uri=hateoas_url)
    self.assertEqual(
        self.slap._hateoas_navigator.slapos_master_hateoas_uri,
        hateoas_url
    )

  def test_initializeConnection_noHateoasUrl(self):
    """
    Test that if no rest URL is specified and master does not know about rest,
    it still work.
    """
    hateoas_url = 'foo'
    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/getHateoasUrl'):
        return {
                'status_code': 404,
                }

    with httmock.HTTMock(handler):
      self.slap.initializeConnection('http://%s' % self.id())
    self.assertEqual(None, getattr(self.slap, '_hateoas_navigator', None))


class TestComputer(SlapMixin):
  """
  Tests slapos.slap.slap.Computer class functionality
  """

  def test_computer_getComputerPartitionList_no_partition(self):
    """
    Asserts that calling Computer.getComputerPartitionList without Computer
    Partitions returns empty list
    """
    computer_guid = self._getTestComputerId()
    slap = self.slap
    slap.initializeConnection(self.server_url)

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/registerComputerPartition'
              and 'computer_reference' in qs
              and 'computer_partition_reference' in qs):
        slap_partition = slapos.slap.ComputerPartition(
            qs['computer_reference'][0],
            qs['computer_partition_reference'][0])
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_partition)
                }
      elif (url.path == '/getFullComputerInformation'
              and 'computer_id' in qs):
        slap_computer = slapos.slap.Computer(qs['computer_id'][0])
        slap_computer._software_release_list = []
        slap_computer._computer_partition_list = []
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_computer)
                }
      elif url.path == '/requestComputerPartition':
        return {'status_code': 408}
      else:
        return {'status_code': 404}

    with httmock.HTTMock(handler):
      computer = self.slap.registerComputer(computer_guid)
      self.assertEqual(computer.getComputerPartitionList(), [])

  def _test_computer_empty_computer_guid(self, computer_method):
    """
    Helper method checking if calling Computer method with empty id raises
    early.
    """
    self.slap.initializeConnection(self.server_url)

    def handler(url, req):
      # Shouldn't even be called
      self.assertFalse(True)

    with httmock.HTTMock(handler):
      computer = self.slap.registerComputer(None)
      self.assertRaises(slapos.slap.NotFoundError,
                        getattr(computer, computer_method))

  def test_computer_getComputerPartitionList_empty_computer_guid(self):
    """
    Asserts that calling getComputerPartitionList with empty
    computer_guid raises early, before calling master.
    """
    self._test_computer_empty_computer_guid('getComputerPartitionList')

  def test_computer_getSoftwareReleaseList_empty_computer_guid(self):
    """
    Asserts that calling getSoftwareReleaseList with empty
    computer_guid raises early, before calling master.
    """
    self._test_computer_empty_computer_guid('getSoftwareReleaseList')

  def test_computer_getComputerPartitionList_only_partition(self):
    """
    Asserts that calling Computer.getComputerPartitionList with only
    Computer Partitions returns empty list
    """
    self.computer_guid = self._getTestComputerId()
    partition_id = 'PARTITION_01'
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/registerComputerPartition'
            and qs == {
                'computer_reference': [self.computer_guid],
                'computer_partition_reference': [partition_id]
                }):
        partition = slapos.slap.ComputerPartition(self.computer_guid, partition_id)
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(partition)
                }
      elif (url.path == '/getFullComputerInformation'
              and 'computer_id' in qs):
        slap_computer = slapos.slap.Computer(qs['computer_id'][0])
        slap_computer._computer_partition_list = []
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_computer)
                }
      else:
        return {'status_code': 400}

    with httmock.HTTMock(handler):
      self.computer = self.slap.registerComputer(self.computer_guid)
      self.partition = self.slap.registerComputerPartition(self.computer_guid,
                                                           partition_id)
      self.assertEqual(self.computer.getComputerPartitionList(), [])

  @unittest.skip("Not implemented")
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
    self.assertRaises(UndefinedYetException,
                      self.computer.reportUsage,
                      non_dtd_xml)

  @unittest.skip("Not implemented")
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
    self.assertRaises(UndefinedYetException,
                      self.computer.reportUsage,
                      bad_partition_dtd_xml)


class RequestWasCalled(Exception):
  pass


class TestComputerPartition(SlapMixin):
  """
  Tests slapos.slap.slap.ComputerPartition class functionality
  """

  def test_request_sends_request(self):
    partition_id = 'PARTITION_01'

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/registerComputerPartition'
              and 'computer_reference' in qs
              and 'computer_partition_reference' in qs):
        slap_partition = slapos.slap.ComputerPartition(
            qs['computer_reference'][0],
            qs['computer_partition_reference'][0])
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_partition)
                }
      elif (url.path == '/getComputerInformation'
              and 'computer_id' in qs):
        slap_computer = slapos.slap.Computer(qs['computer_id'][0])
        slap_computer._software_release_list = []
        slap_partition = slapos.slap.ComputerPartition(
            qs['computer_id'][0],
            partition_id)
        slap_computer._computer_partition_list = [slap_partition]
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_computer)
                }
      elif url.path == '/requestComputerPartition':
        raise RequestWasCalled
      else:
        return {
                'status_code': 404
                }

    with httmock.HTTMock(handler):
      self.computer_guid = self._getTestComputerId()
      self.slap = slapos.slap.slap()
      self.slap.initializeConnection(self.server_url)
      computer_partition = self.slap.registerComputerPartition(
          self.computer_guid, partition_id)
      self.assertRaises(RequestWasCalled,
                        computer_partition.request,
                        'http://server/new/' + self._getTestComputerId(),
                        'software_type', 'myref')

  def test_request_not_raises(self):
    partition_id = 'PARTITION_01'

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/registerComputerPartition'
              and 'computer_reference' in qs
              and 'computer_partition_reference' in qs):
        slap_partition = slapos.slap.ComputerPartition(
            qs['computer_reference'][0],
            qs['computer_partition_reference'][0])
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_partition)
                }
      elif (url.path == '/getComputerInformation'
              and 'computer_id' in qs):
        slap_computer = slapos.slap.Computer(qs['computer_id'][0])
        slap_computer._software_release_list = []
        slap_partition = slapos.slap.ComputerPartition(
            qs['computer_id'][0],
            partition_id)
        slap_computer._computer_partition_list = [slap_partition]
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_computer)
                }
      elif url.path == '/requestComputerPartition':
        return {'status_code': 408}
      else:
        return {'status_code': 404}

    self.computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    with httmock.HTTMock(handler):
      computer_partition = self.slap.registerComputerPartition(
          self.computer_guid, partition_id)
      requested_partition = computer_partition.request(
          'http://server/new/' + self._getTestComputerId(),
          'software_type',
          'myref')
      self.assertIsInstance(requested_partition, slapos.slap.ComputerPartition)

  def test_request_raises_later(self):
    partition_id = 'PARTITION_01'

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/registerComputerPartition' and
              'computer_reference' in qs and
              'computer_partition_reference' in qs):
        slap_partition = slapos.slap.ComputerPartition(
            qs['computer_reference'][0],
            qs['computer_partition_reference'][0])
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_partition)
                }
      elif (url.path == '/getComputerInformation'
              and 'computer_id' in qs):
        slap_computer = slapos.slap.Computer(qs['computer_id'][0])
        slap_computer._software_release_list = []
        slap_partition = slapos.slap.ComputerPartition(
            qs['computer_id'][0],
            partition_id)
        slap_computer._computer_partition_list = [slap_partition]
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_computer)
                }
      elif url.path == '/requestComputerPartition':
        return {'status_code': 408}
      else:
        return {'status_code': 404}

    self.computer_guid = self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    with httmock.HTTMock(handler):
      computer_partition = self.slap.registerComputerPartition(
          self.computer_guid, partition_id)
      requested_partition = computer_partition.request(
          'http://server/new/' + self._getTestComputerId(),
          'software_type',
          'myref')
      self.assertIsInstance(requested_partition, slapos.slap.ComputerPartition)
      # as request method does not raise, accessing data raises
      self.assertRaises(slapos.slap.ResourceNotReady,
                        requested_partition.getId)

  def test_request_fullfilled_work(self):
    partition_id = 'PARTITION_01'
    requested_partition_id = 'PARTITION_02'
    computer_guid = self._getTestComputerId()

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/registerComputerPartition' and
              'computer_reference' in qs and
              'computer_partition_reference' in qs):
        slap_partition = slapos.slap.ComputerPartition(
            qs['computer_reference'][0],
            qs['computer_partition_reference'][0])
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_partition)
                }
      elif (url.path == '/getComputerInformation' and 'computer_id' in qs):
        slap_computer = slapos.slap.Computer(qs['computer_id'][0])
        slap_computer._software_release_list = []
        slap_partition = slapos.slap.ComputerPartition(
            qs['computer_id'][0],
            partition_id)
        slap_computer._computer_partition_list = [slap_partition]
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_computer)
                }
      elif url.path == '/requestComputerPartition':
        from slapos.slap.slap import SoftwareInstance
        slap_partition = SoftwareInstance(
            slap_computer_id=computer_guid,
            slap_computer_partition_id=requested_partition_id)
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_partition)
                }
      else:
        return {'status_code': 404}


    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)

    with httmock.HTTMock(handler):
      computer_partition = self.slap.registerComputerPartition(
          computer_guid, partition_id)
      requested_partition = computer_partition.request(
          'http://server/new/' + self._getTestComputerId(),
          'software_type',
          'myref')
      self.assertIsInstance(requested_partition, slapos.slap.ComputerPartition)
      # as request method does not raise, accessing data in case when
      # request was done works correctly
      self.assertEqual(requested_partition_id, requested_partition.getId())

  def test_request_with_slapgrid_request_transaction(self):
    from slapos.slap.slap import COMPUTER_PARTITION_REQUEST_LIST_TEMPLATE_FILENAME
    partition_id = 'PARTITION_01'
    instance_root = tempfile.mkdtemp()
    partition_root = os.path.join(instance_root, partition_id)
    os.mkdir(partition_root)
    os.environ['SLAPGRID_INSTANCE_ROOT'] = instance_root
    transaction_file_name = COMPUTER_PARTITION_REQUEST_LIST_TEMPLATE_FILENAME % partition_id
    transaction_file_path = os.path.join(partition_root, transaction_file_name)

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/registerComputerPartition'
              and 'computer_reference' in qs
              and 'computer_partition_reference' in qs):
        slap_partition = slapos.slap.ComputerPartition(
            qs['computer_reference'][0],
            qs['computer_partition_reference'][0])
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_partition)
                }
      elif (url.path == '/getComputerInformation'
              and 'computer_id' in qs):
        slap_computer = slapos.slap.Computer(qs['computer_id'][0])
        slap_computer._software_release_list = []
        slap_partition = slapos.slap.ComputerPartition(
            qs['computer_id'][0],
            partition_id)
        slap_computer._computer_partition_list = [slap_partition]
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(slap_computer)
                }
      elif url.path == '/requestComputerPartition':
        raise RequestWasCalled
      else:
        return {
                'status_code': 404
                }

    with httmock.HTTMock(handler):
      self.computer_guid = self._getTestComputerId()
      self.slap = slapos.slap.slap()
      self.slap.initializeConnection(self.server_url)
      computer_partition = self.slap.registerComputerPartition(
          self.computer_guid, partition_id)

      self.assertTrue(os.path.exists(transaction_file_path))
      with open(transaction_file_path, 'r') as f:
        content = f.read()
        self.assertEqual(content, '')
      self.assertRaises(RequestWasCalled,
                        computer_partition.request,
                        'http://server/new/' + self._getTestComputerId(),
                        'software_type', 'myref')
      self.assertTrue(os.path.exists(transaction_file_path))
      with open(transaction_file_path, 'r') as f:
        content_list = f.read().strip().split('\n')
        self.assertEqual(content_list, ['myref'])

      # Not override
      computer_partition = self.slap.registerComputerPartition(
          self.computer_guid, partition_id)
      self.assertTrue(os.path.exists(transaction_file_path))
      with open(transaction_file_path, 'r') as f:
        content_list = f.read().strip().split('\n')
        self.assertEqual(content_list, ['myref'])

      # Request a second instance
      self.assertRaises(RequestWasCalled,
                        computer_partition.request,
                        'http://server/new/' + self._getTestComputerId(),
                        'software_type', 'mysecondref')
      with open(transaction_file_path, 'r') as f:
        content_list = f.read().strip().split('\n')
        self.assertEquals(list(set(content_list)), ['myref', 'mysecondref'])

  def _test_new_computer_partition_state(self, state):
    """
    Helper method to automate assertions of failing states on new Computer
    Partition
    """
    computer_guid = self._getTestComputerId()
    partition_id = 'PARTITION_01'
    slap = self.slap
    slap.initializeConnection(self.server_url)

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/registerComputerPartition' and
              qs['computer_reference'][0] == computer_guid and
              qs['computer_partition_reference'][0] == partition_id):
        partition = slapos.slap.ComputerPartition(
            computer_guid, partition_id)
        return {
                'status_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(partition)
                }
      else:
        return {'status_code': 404}


    with httmock.HTTMock(handler):
      computer_partition = self.slap.registerComputerPartition(
          computer_guid, partition_id)
      self.assertRaises(slapos.slap.NotFoundError,
                        getattr(computer_partition, state))

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
    computer_guid = self._getTestComputerId()
    partition_id = 'PARTITION_01'
    slap = self.slap
    slap.initializeConnection(self.server_url)

    def handler(url, req):
      qs = urlparse.parse_qs(url.query)
      if (url.path == '/registerComputerPartition' and
              qs['computer_reference'][0] == computer_guid and
              qs['computer_partition_reference'][0] == partition_id):
        partition = slapos.slap.ComputerPartition(
            computer_guid, partition_id)
        return {
                'statu_code': 200,
                'content': xml_marshaller.xml_marshaller.dumps(partition)
                }
      elif url.path == '/softwareInstanceError':
        parsed_qs_body = urlparse.parse_qs(req.body)
        # XXX: why do we have computer_id and not computer_reference?
        # XXX: why do we have computer_partition_id and not
        # computer_partition_reference?
        if (parsed_qs_body['computer_id'][0] == computer_guid and
                parsed_qs_body['computer_partition_id'][0] == partition_id and
                parsed_qs_body['error_log'][0] == 'some error'):
          return {'status_code': 200}

      return {'status_code': 404}


    with httmock.HTTMock(handler):
      computer_partition = slap.registerComputerPartition(
          computer_guid, partition_id)
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
    self.assertRaises(NameError, method)

  def test_available_new_SoftwareRelease_raises(self):
    """
    Asserts that calling SoftwareRelease.available on new software release
    raises NameError exception
    """
    self._test_new_software_release_state('available')

  def test_building_new_SoftwareRelease_raises(self):
    """
    Asserts that calling SoftwareRelease.building on new software release
    raises NameError exception
    """
    self._test_new_software_release_state('building')

  def test_error_new_SoftwareRelease_works(self):
    """
    Asserts that calling SoftwareRelease.error on software release works
    """
    computer_guid = self._getTestComputerId()
    software_release_uri = 'http://server/' + self._getTestComputerId()
    slap = self.slap
    slap.initializeConnection(self.server_url)

    def handler(url, req):
      qs = urlparse.parse_qs(req.body)
      if (url.path == '/softwareReleaseError' and
              qs['computer_id'][0] == computer_guid and
              qs['url'][0] == software_release_uri and
              qs['error_log'][0] == 'some error'):
        return {
                'status_code': 200
                }
      return {'status_code': 404}


    with httmock.HTTMock(handler):
      software_release = self.slap.registerSoftwareRelease(software_release_uri)
      software_release._computer_guid = computer_guid
      software_release.error('some error')


class TestOpenOrder(SlapMixin):
  def test_request_sends_request(self):
    software_release_uri = 'http://server/new/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    # XXX: Interface lack registerOpenOrder method declaration
    open_order = self.slap.registerOpenOrder()

    def handler(url, req):
      if url.path == '/requestComputerPartition':
        raise RequestWasCalled

    with httmock.HTTMock(handler):
      self.assertRaises(RequestWasCalled,
                        open_order.request,
                        software_release_uri, 'myrefe')

  @unittest.skip('unclear what should be returned')
  def test_request_not_raises(self):
    software_release_uri = 'http://server/new/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    # XXX: Interface lack registerOpenOrder method declaration

    def handler(url, req):
      if url.path == '/requestComputerPartition':
        pass
        # XXX what to do here?

    with httmock.HTTMock(handler):
      open_order = self.slap.registerOpenOrder()
      computer_partition = open_order.request(software_release_uri, 'myrefe')
      self.assertIsInstance(computer_partition, slapos.slap.ComputerPartition)

  def test_request_raises_later(self):
    software_release_uri = 'http://server/new/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    # XXX: Interface lack registerOpenOrder method declaration
    open_order = self.slap.registerOpenOrder()

    def handler(url, req):
      return {'status_code': 408}

    with httmock.HTTMock(handler):
      computer_partition = open_order.request(software_release_uri, 'myrefe')
      self.assertIsInstance(computer_partition, slapos.slap.ComputerPartition)

      self.assertRaises(slapos.slap.ResourceNotReady,
                        computer_partition.getId)

  def test_request_fullfilled_work(self):
    software_release_uri = 'http://server/new/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    # XXX: Interface lack registerOpenOrder method declaration
    open_order = self.slap.registerOpenOrder()
    computer_guid = self._getTestComputerId()
    requested_partition_id = 'PARTITION_01'

    def handler(url, req):
      from slapos.slap.slap import SoftwareInstance
      slap_partition = SoftwareInstance(
          slap_computer_id=computer_guid,
          slap_computer_partition_id=requested_partition_id)
      return {
              'status_code': 200,
              'content': xml_marshaller.xml_marshaller.dumps(slap_partition)
              }

    with httmock.HTTMock(handler):
      computer_partition = open_order.request(software_release_uri, 'myrefe')
      self.assertIsInstance(computer_partition, slapos.slap.ComputerPartition)
      self.assertEqual(requested_partition_id, computer_partition.getId())


  def test_request_getConnectionParameter(self):
    """ Backward compatibility API for slapproxy older them 1.0.1 """
    software_release_uri = 'http://server/new/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    # XXX: Interface lack registerOpenOrder method declaration
    open_order = self.slap.registerOpenOrder()
    computer_guid = self._getTestComputerId()
    requested_partition_id = 'PARTITION_01'

    def handler(url, req):
      from slapos.slap.slap import SoftwareInstance
      slap_partition = SoftwareInstance(
          _connection_dict = {"url": 'URL_CONNECTION_PARAMETER'},
          slap_computer_id=computer_guid,
          slap_computer_partition_id=requested_partition_id)
      return {
              'status_code': 200,
              'content': xml_marshaller.xml_marshaller.dumps(slap_partition)
              }


    with httmock.HTTMock(handler):
      computer_partition = open_order.request(software_release_uri, 'myrefe')
      self.assertIsInstance(computer_partition, slapos.slap.ComputerPartition)
      self.assertEqual(requested_partition_id, computer_partition.getId())
      self.assertEqual("URL_CONNECTION_PARAMETER",
                       computer_partition.getConnectionParameter('url'))


  def test_request_connection_dict_backward_compatibility(self):
    """ Backward compatibility API for slapproxy older them 1.0.1 """
    software_release_uri = 'http://server/new/' + self._getTestComputerId()
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.server_url)
    # XXX: Interface lack registerOpenOrder method declaration
    open_order = self.slap.registerOpenOrder()
    computer_guid = self._getTestComputerId()
    requested_partition_id = 'PARTITION_01'

    def handler(url, req):
      from slapos.slap.slap import SoftwareInstance
      slap_partition = SoftwareInstance(
          connection_xml="""<?xml version='1.0' encoding='utf-8'?>
<instance>
  <parameter id="url">URL_CONNECTION_PARAMETER</parameter>
</instance>""",
          slap_computer_id=computer_guid,
          slap_computer_partition_id=requested_partition_id)
      return {
              'status_code': 200,
              'content': xml_marshaller.xml_marshaller.dumps(slap_partition)
              }

    with httmock.HTTMock(handler):
      computer_partition = open_order.request(software_release_uri, 'myrefe')
      self.assertIsInstance(computer_partition, slapos.slap.ComputerPartition)
      self.assertEqual(requested_partition_id, computer_partition.getId())
      self.assertEqual("URL_CONNECTION_PARAMETER",
                       computer_partition.getConnectionParameter('url'))


class TestSoftwareProductCollection(SlapMixin):
  def setUp(self):
    SlapMixin.setUp(self)
    self.real_getSoftwareReleaseListFromSoftwareProduct =\
        slapos.slap.slap.getSoftwareReleaseListFromSoftwareProduct

    def fake_getSoftwareReleaseListFromSoftwareProduct(inside_self, software_product_reference):
      return self.getSoftwareReleaseListFromSoftwareProduct_response
    slapos.slap.slap.getSoftwareReleaseListFromSoftwareProduct =\
        fake_getSoftwareReleaseListFromSoftwareProduct

    self.product_collection = slapos.slap.SoftwareProductCollection(
        logging.getLogger(), slapos.slap.slap())

  def tearDown(self):
    slapos.slap.slap.getSoftwareReleaseListFromSoftwareProduct =\
        self.real_getSoftwareReleaseListFromSoftwareProduct

  def test_get_product(self):
    """
    Test that the get method (aliased to __getattr__) returns the first element
    of the list given by getSoftwareReleaseListFromSoftwareProduct (i.e the
    best one).
    """
    self.getSoftwareReleaseListFromSoftwareProduct_response = ['0', '1', '2']
    self.assertEqual(
      self.product_collection.get('random_reference'),
      self.getSoftwareReleaseListFromSoftwareProduct_response[0]
    )

  def test_get_product_empty_product(self):
    """
    Test that the get method (aliased to __getattr__) raises if no
    Software Release is related to the Software Product, or if the
    Software Product does not exist.
    """
    self.getSoftwareReleaseListFromSoftwareProduct_response = []
    self.assertRaises(
      AttributeError,
      self.product_collection.get, 'random_reference',
    )

  def test_get_product_getattr(self):
    """
    Test that __getattr__ method is bound to get() method.
    """
    self.getSoftwareReleaseListFromSoftwareProduct_response = ['0']
    self.product_collection.foo
    self.assertEqual(
      self.product_collection.__getattr__,
      self.product_collection.get
    )
    self.assertEqual(self.product_collection.foo, '0')

if __name__ == '__main__':
  print 'You can point to any SLAP server by setting TEST_SLAP_SERVER_URL '\
      'environment variable'
  unittest.main()

