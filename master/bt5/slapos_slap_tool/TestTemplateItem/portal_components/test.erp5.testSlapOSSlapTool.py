# -*- coding: utf-8 -*-
# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
    testSlapOSMixin

from DateTime import DateTime
from App.Common import rfc1123_date

import os
import tempfile

# blurb to make nice XML comparisions
import xml.dom.ext.reader.Sax
import xml.dom.ext
import StringIO
import difflib
import transaction
from OFS.Traversable import NotFound

class Simulator:
  def __init__(self, outfile, method):
    self.outfile = outfile
    self.method = method

  def __call__(self, *args, **kwargs):
    """Simulation Method"""
    old = open(self.outfile, 'r').read()
    if old:
      l = eval(old)
    else:
      l = []
    l.append({'recmethod': self.method,
      'recargs': args,
      'reckwargs': kwargs})
    open(self.outfile, 'w').write(repr(l))

class TestSlapOSSlapToolMixin(testSlapOSMixin):
  def afterSetUp(self, person=None):
    testSlapOSMixin.afterSetUp(self)
    self.portal_slap = self.portal.portal_slap
    new_id = self.generateNewId()

    # Prepare computer
    self.computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    self.computer.edit(
      title="Computer %s" % new_id,
      reference="TESTCOMP-%s" % new_id
    )
    if (person is not None):
      self.computer.edit(
        source_administration_value=person,
        )

    self.computer.validate()

    self.tic()

    self.computer_id = self.computer.getReference()
    self.pinDateTime(DateTime())

  def beforeTearDown(self):
    self.unpinDateTime()
    self._cleaupREQUEST()

class TestSlapOSSlapToolComputerAccess(TestSlapOSSlapToolMixin):
  def test_getFullComputerInformation(self):
    self._makeComplexComputer(with_slave=True)
    self.login(self.computer_id)
    response = self.portal_slap.getFullComputerInformation(self.computer_id)
    self.assertEqual(200, response.status)
    self.assertEqual('public, max-age=1, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    
      
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <object id='i2' module='slapos.slap.slap' class='Computer'>
    <tuple>
      <unicode>%(computer_id)s</unicode>
    </tuple>
    <dictionary id='i3'>
      <string>_computer_id</string>
      <unicode>%(computer_id)s</unicode>
      <string>_computer_partition_list</string>
      <list id='i4'>
        <object id='i5' module='slapos.slap.slap' class='ComputerPartition'>
          <tuple>
            <unicode>%(computer_id)s</unicode>
            <unicode>partition4</unicode>
          </tuple>
          <dictionary id='i6'>
            <string>_computer_id</string>
            <unicode>%(computer_id)s</unicode>
            <string>_need_modification</string>
            <int>0</int>
            <string>_partition_id</string>
            <unicode>partition4</unicode>
            <string>_request_dict</string>
            <none/>
            <string>_requested_state</string>
            <string>destroyed</string>
            <string>_software_release_document</string>
            <none/>
          </dictionary>
        </object>
        <object id='i7' module='slapos.slap.slap' class='ComputerPartition'>
          <tuple>
            <unicode>%(computer_id)s</unicode>
            <unicode>partition3</unicode>
          </tuple>
          <dictionary id='i8'>
            <string>_computer_id</string>
            <unicode>%(computer_id)s</unicode>
            <string>_connection_dict</string>
            <dictionary id='i9'/>
            <string>_filter_dict</string>
            <dictionary id='i10'>
              <unicode>paramé</unicode>
              <unicode>%(partition_3_sla)s</unicode>
            </dictionary>
            <string>_instance_guid</string>
            <unicode>%(partition_3_instance_guid)s</unicode>
            <string>_need_modification</string>
            <int>1</int>
            <string>_parameter_dict</string>
            <dictionary id='i11'>
              <string>full_ip_list</string>
              <list id='i12'/>
              <string>ip_list</string>
              <list id='i13'>
                <tuple>
                  <unicode/>
                  <unicode>ip_address_3</unicode>
                </tuple>
              </list>
              <unicode>paramé</unicode>
              <unicode>%(partition_3_param)s</unicode>
              <string>slap_computer_id</string>
              <unicode>%(computer_id)s</unicode>
              <string>slap_computer_partition_id</string>
              <unicode>partition3</unicode>
              <string>slap_software_release_url</string>
              <unicode>%(partition_3_software_release_url)s</unicode>
              <string>slap_software_type</string>
              <unicode>%(partition_3_instance_software_type)s</unicode>
              <string>slave_instance_list</string>
              <list id='i14'/>
              <string>timestamp</string>
              <string>%(partition_3_timestamp)s</string>
            </dictionary>
            <string>_partition_id</string>
            <unicode>partition3</unicode>
            <string>_request_dict</string>
            <none/>
            <string>_requested_state</string>
            <string>destroyed</string>
            <string>_software_release_document</string>
            <object id='i15' module='slapos.slap.slap' class='SoftwareRelease'>
              <tuple>
                <unicode>%(partition_3_software_release_url)s</unicode>
                <unicode>%(computer_id)s</unicode>
              </tuple>
              <dictionary id='i16'>
                <string>_computer_guid</string>
                <unicode>%(computer_id)s</unicode>
                <string>_software_instance_list</string>
                <list id='i17'/>
                <string>_software_release</string>
                <unicode>%(partition_3_software_release_url)s</unicode>
              </dictionary>
            </object>
          </dictionary>
        </object>
        <object id='i18' module='slapos.slap.slap' class='ComputerPartition'>
          <tuple>
            <unicode>%(computer_id)s</unicode>
            <unicode>partition2</unicode>
          </tuple>
          <dictionary id='i19'>
            <string>_computer_id</string>
            <unicode>%(computer_id)s</unicode>
            <string>_connection_dict</string>
            <dictionary id='i20'/>
            <string>_filter_dict</string>
            <dictionary id='i21'>
              <unicode>paramé</unicode>
              <unicode>%(partition_2_sla)s</unicode>
            </dictionary>
            <string>_instance_guid</string>
            <unicode>%(partition_2_instance_guid)s</unicode>
            <string>_need_modification</string>
            <int>1</int>
            <string>_parameter_dict</string>
            <dictionary id='i22'>
              <string>full_ip_list</string>
              <list id='i23'/>
              <string>ip_list</string>
              <list id='i24'>
                <tuple>
                  <unicode/>
                  <unicode>ip_address_2</unicode>
                </tuple>
              </list>
              <unicode>paramé</unicode>
              <unicode>%(partition_2_param)s</unicode>
              <string>slap_computer_id</string>
              <unicode>%(computer_id)s</unicode>
              <string>slap_computer_partition_id</string>
              <unicode>partition2</unicode>
              <string>slap_software_release_url</string>
              <unicode>%(partition_2_software_release_url)s</unicode>
              <string>slap_software_type</string>
              <unicode>%(partition_2_instance_software_type)s</unicode>
              <string>slave_instance_list</string>
              <list id='i25'/>
              <string>timestamp</string>
              <string>%(partition_2_timestamp)s</string>
            </dictionary>
            <string>_partition_id</string>
            <unicode>partition2</unicode>
            <string>_request_dict</string>
            <none/>
            <string>_requested_state</string>
            <string>stopped</string>
            <string>_software_release_document</string>
            <object id='i26' module='slapos.slap.slap' class='SoftwareRelease'>
              <tuple>
                <unicode>%(partition_2_software_release_url)s</unicode>
                <unicode>%(computer_id)s</unicode>
              </tuple>
              <dictionary id='i27'>
                <string>_computer_guid</string>
                <unicode>%(computer_id)s</unicode>
                <string>_software_instance_list</string>
                <list id='i28'/>
                <string>_software_release</string>
                <unicode>%(partition_2_software_release_url)s</unicode>
              </dictionary>
            </object>
          </dictionary>
        </object>
        <object id='i29' module='slapos.slap.slap' class='ComputerPartition'>
          <tuple>
            <unicode>%(computer_id)s</unicode>
            <unicode>partition1</unicode>
          </tuple>
          <dictionary id='i30'>
            <string>_computer_id</string>
            <unicode>%(computer_id)s</unicode>
            <string>_connection_dict</string>
            <dictionary id='i31'/>
            <string>_filter_dict</string>
            <dictionary id='i32'>
              <unicode>paramé</unicode>
              <unicode>%(partition_1_sla)s</unicode>
            </dictionary>
            <string>_instance_guid</string>
            <unicode>%(partition_1_instance_guid)s</unicode>
            <string>_need_modification</string>
            <int>1</int>
            <string>_parameter_dict</string>
            <dictionary id='i33'>
              <string>full_ip_list</string>
              <list id='i34'/>
              <string>ip_list</string>
              <list id='i35'>
                <tuple>
                  <unicode/>
                  <unicode>ip_address_1</unicode>
                </tuple>
              </list>
              <unicode>paramé</unicode>
              <unicode>%(partition_1_param)s</unicode>
              <string>slap_computer_id</string>
              <unicode>%(computer_id)s</unicode>
              <string>slap_computer_partition_id</string>
              <unicode>partition1</unicode>
              <string>slap_software_release_url</string>
              <unicode>%(partition_1_software_release_url)s</unicode>
              <string>slap_software_type</string>
              <unicode>%(partition_1_instance_software_type)s</unicode>
              <string>slave_instance_list</string>
              <list id='i36'>
                <dictionary id='i37'>
                  <unicode>paramé</unicode>
                  <unicode>%(slave_1_param)s</unicode>
                  <string>slap_software_type</string>
                  <unicode>%(slave_1_software_type)s</unicode>
                  <string>slave_reference</string>
                  <unicode>%(slave_1_instance_guid)s</unicode>
                  <string>slave_title</string>
                  <unicode>%(slave_1_title)s</unicode>
                  <string>timestamp</string>
                  <int>%(partition_1_timestamp)s</int>
                </dictionary>
              </list>
              <string>timestamp</string>
              <string>%(partition_1_timestamp)s</string>
            </dictionary>
            <string>_partition_id</string>
            <unicode>partition1</unicode>
            <string>_request_dict</string>
            <none/>
            <string>_requested_state</string>
            <string>started</string>
            <string>_software_release_document</string>
            <object id='i38' module='slapos.slap.slap' class='SoftwareRelease'>
              <tuple>
                <unicode>%(partition_1_software_release_url)s</unicode>
                <unicode>%(computer_id)s</unicode>
              </tuple>
              <dictionary id='i39'>
                <string>_computer_guid</string>
                <unicode>%(computer_id)s</unicode>
                <string>_software_instance_list</string>
                <list id='i40'/>
                <string>_software_release</string>
                <unicode>%(partition_1_software_release_url)s</unicode>
              </dictionary>
            </object>
          </dictionary>
        </object>
      </list>
      <string>_software_release_list</string>
      <list id='i41'>
        <object id='i42' module='slapos.slap.slap' class='SoftwareRelease'>
          <tuple>
            <unicode>%(destroy_requested_url)s</unicode>
            <unicode>%(computer_id)s</unicode>
          </tuple>
          <dictionary id='i43'>
            <string>_computer_guid</string>
            <unicode>%(computer_id)s</unicode>
            <string>_requested_state</string>
            <string>destroyed</string>
            <string>_software_instance_list</string>
            <list id='i44'/>
            <string>_software_release</string>
            <unicode>%(destroy_requested_url)s</unicode>
          </dictionary>
        </object>
        <object id='i45' module='slapos.slap.slap' class='SoftwareRelease'>
          <tuple>
            <unicode>%(start_requested_url)s</unicode>
            <unicode>%(computer_id)s</unicode>
          </tuple>
          <dictionary id='i46'>
            <string>_computer_guid</string>
            <unicode>%(computer_id)s</unicode>
            <string>_requested_state</string>
            <string>available</string>
            <string>_software_instance_list</string>
            <list id='i47'/>
            <string>_software_release</string>
            <unicode>%(start_requested_url)s</unicode>
          </dictionary>
        </object>
      </list>
    </dictionary>
  </object>
</marshal>
""" % dict(
  computer_id=self.computer_id,
  destroy_requested_url=self.destroy_requested_software_installation.getUrlString(),
  partition_1_instance_guid=self.computer.partition1.getAggregateRelatedValue(portal_type='Software Instance').getReference(),
  partition_1_instance_software_type=self.computer.partition1.getAggregateRelatedValue(portal_type='Software Instance').getSourceReference(),
  partition_1_param=self.computer.partition1.getAggregateRelatedValue(portal_type='Software Instance').getInstanceXmlAsDict()['paramé'],
  partition_1_sla=self.computer.partition1.getAggregateRelatedValue(portal_type='Software Instance').getSlaXmlAsDict()['paramé'],
  partition_1_software_release_url=self.computer.partition1.getAggregateRelatedValue(portal_type='Software Instance').getUrlString(),
  partition_1_timestamp=int(self.computer.partition1.getAggregateRelatedValue(portal_type='Software Instance').getModificationDate()),
  partition_2_instance_guid=self.computer.partition2.getAggregateRelatedValue(portal_type='Software Instance').getReference(),
  partition_2_instance_software_type=self.computer.partition2.getAggregateRelatedValue(portal_type='Software Instance').getSourceReference(),
  partition_2_param=self.computer.partition2.getAggregateRelatedValue(portal_type='Software Instance').getInstanceXmlAsDict()['paramé'],
  partition_2_sla=self.computer.partition2.getAggregateRelatedValue(portal_type='Software Instance').getSlaXmlAsDict()['paramé'],
  partition_2_software_release_url=self.computer.partition2.getAggregateRelatedValue(portal_type='Software Instance').getUrlString(),
  partition_2_timestamp=int(self.computer.partition2.getAggregateRelatedValue(portal_type='Software Instance').getModificationDate()),
  partition_3_instance_guid=self.computer.partition3.getAggregateRelatedValue(portal_type='Software Instance').getReference(),
  partition_3_instance_software_type=self.computer.partition3.getAggregateRelatedValue(portal_type='Software Instance').getSourceReference(),
  partition_3_param=self.computer.partition3.getAggregateRelatedValue(portal_type='Software Instance').getInstanceXmlAsDict()['paramé'],
  partition_3_sla=self.computer.partition3.getAggregateRelatedValue(portal_type='Software Instance').getSlaXmlAsDict()['paramé'],
  partition_3_software_release_url=self.computer.partition3.getAggregateRelatedValue(portal_type='Software Instance').getUrlString(),
  partition_3_timestamp=int(self.computer.partition3.getAggregateRelatedValue(portal_type='Software Instance').getModificationDate()),
  slave_1_param=self.start_requested_slave_instance.getInstanceXmlAsDict()['paramé'],
  slave_1_software_type=self.start_requested_slave_instance.getSourceReference(),
  slave_1_instance_guid=self.start_requested_slave_instance.getReference(),
  slave_1_title=self.start_requested_slave_instance.getTitle(),
  start_requested_url=self.start_requested_software_installation.getUrlString()
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_getComputerInformation(self):
    self.assertEqual('getFullComputerInformation',
      self.portal_slap.getComputerInformation.im_func.func_name)

  def test_not_accessed_getComputerStatus(self):
    self.login(self.computer_id)
    created_at = rfc1123_date(DateTime())
    response = self.portal_slap.getComputerStatus(self.computer_id)
    self.assertEqual(200, response.status)
    self.assertEqual('public, max-age=60, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()

    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <string>created_at</string>
    <string>%(created_at)s</string>
    <string>text</string>
    <unicode>#error no data found for %(computer_id)s</unicode>
    <string>user</string>
    <unicode>SlapOS Master</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  computer_id=self.computer_id
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_accessed_getComputerStatus(self):
    self.login(self.computer_id)
    
    self.portal_slap.getFullComputerInformation(self.computer_id)
    created_at = rfc1123_date(DateTime())
    response = self.portal_slap.getComputerStatus(self.computer_id)
    self.assertEqual(200, response.status)
    self.assertEqual('public, max-age=60, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))

    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()

    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>#access %(computer_id)s</unicode>
    <unicode>user</unicode>
    <unicode>%(computer_id)s</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  computer_id=self.computer_id
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def assertComputerBangSimulator(self, args, kwargs):
    stored = eval(open(self.computer_bang_simulator).read())
    # do the same translation magic as in workflow
    kwargs['comment'] = kwargs.pop('comment')
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'reportComputerBang'}])

  def test_computerBang(self):
    self._makeComplexComputer()
    self.computer_bang_simulator = tempfile.mkstemp()[1]
    try:
      self.login(self.computer_id)
      self.computer.reportComputerBang = Simulator(
        self.computer_bang_simulator, 'reportComputerBang')
      error_log = 'Please bang me'
      response = self.portal_slap.computerBang(self.computer_id,
        error_log)
      self.assertEqual('None', response)
      created_at = rfc1123_date(DateTime())
      response = self.portal_slap.getComputerStatus(self.computer_id)
      # check returned XML
      xml_fp = StringIO.StringIO()

      xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
          stream=xml_fp)
      xml_fp.seek(0)
      got_xml = xml_fp.read()
      expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>#error bang</unicode>
    <unicode>user</unicode>
    <unicode>%(computer_id)s</unicode>
  </dictionary>
</marshal>
""" % dict(
    created_at=created_at,
    computer_id=self.computer_id,
  )
      self.assertEqual(expected_xml, got_xml,
          '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))
      self.assertComputerBangSimulator((), {'comment': error_log})
    finally:
      if os.path.exists(self.computer_bang_simulator):
        os.unlink(self.computer_bang_simulator)

  def assertLoadComputerConfigurationFromXML(self, args, kwargs):
    stored = eval(open(self.computer_load_configuration_simulator).read())
    # do the same translation magic as in workflow
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'Computer_updateFromDict'}])

  def test_loadComputerConfigurationFromXML(self):
    self.computer_load_configuration_simulator = tempfile.mkstemp()[1]
    try:
      self.login(self.computer_id)
      self.computer.Computer_updateFromDict = Simulator(
        self.computer_load_configuration_simulator, 'Computer_updateFromDict')

      computer_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <string>reference</string>
    <string>%(computer_reference)s</string>
  </dictionary>
</marshal>
""" % {'computer_reference': self.computer.getReference()}

      response = self.portal_slap.loadComputerConfigurationFromXML(
        computer_xml)
      self.assertEqual('Content properly posted.', response)
      self.assertLoadComputerConfigurationFromXML(
        ({'reference': self.computer.getReference()},), {})
    finally:
      if os.path.exists(self.computer_load_configuration_simulator):
        os.unlink(self.computer_load_configuration_simulator)
  
  def test_not_accessed_getSoftwareInstallationStatus(self):
    self._makeComplexComputer()
    self.computer_bang_simulator = tempfile.mkstemp()[1]
    self.login(self.computer_id)
    created_at = rfc1123_date(DateTime())
    software_installation = self.start_requested_software_installation
    url_string = software_installation.getUrlString()
    response = self.portal_slap.getSoftwareInstallationStatus(url_string,
                            self.computer_id)
    self.assertEqual(200, response.status)
    self.assertEqual('public, max-age=60, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()

    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <string>created_at</string>
    <string>%(created_at)s</string>
    <string>text</string>
    <unicode>#error no data found for %(reference)s</unicode>
    <string>user</string>
    <unicode>SlapOS Master</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  reference=software_installation.getReference()
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))
    

  def test_destroyedSoftwareRelease_noSoftwareInstallation(self):
    self.login(self.computer_id)
    self.assertRaises(NotFound,
        self.portal_slap.destroyedSoftwareRelease,
        "http://example.org/foo", self.computer_id)

  def test_destroyedSoftwareRelease_noDestroyRequested(self):
    self._makeComplexComputer()
    self.login(self.computer_id)
    self.assertRaises(NotFound,
        self.portal_slap.destroyedSoftwareRelease,
        self.start_requested_software_installation.getUrlString(),
        self.computer_id)

  def test_destroyedSoftwareRelease_destroyRequested(self):
    self._makeComplexComputer()
    self.login(self.computer_id)
    destroy_requested = self.destroy_requested_software_installation
    self.assertEquals(destroy_requested.getValidationState(), "validated")
    self.portal_slap.destroyedSoftwareRelease(
        destroy_requested.getUrlString(), self.computer_id)
    self.assertEquals(destroy_requested.getValidationState(), "invalidated")

  def test_availableSoftwareRelease(self):
    self._makeComplexComputer()
    self.computer_bang_simulator = tempfile.mkstemp()[1]
    self.login(self.computer_id)
    software_installation = self.start_requested_software_installation
    url_string = software_installation.getUrlString()
    response = self.portal_slap.availableSoftwareRelease(
                  url_string, self.computer_id)
    self.assertEqual('None', response)
    created_at = rfc1123_date(DateTime())
    response = self.portal_slap.getSoftwareInstallationStatus(
                      url_string, self.computer_id)
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>#access software release %(url_string)s available</unicode>
    <unicode>user</unicode>
    <unicode>%(computer_id)s</unicode>
  </dictionary>
</marshal>
""" % dict(
    created_at=created_at,
    url_string=url_string,
    computer_id=self.computer_id,
  )
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_buildingSoftwareRelease(self):
    self._makeComplexComputer()
    self.computer_bang_simulator = tempfile.mkstemp()[1]
    self.login(self.computer_id)
    software_installation = self.start_requested_software_installation
    url_string = software_installation.getUrlString()
    response = self.portal_slap.buildingSoftwareRelease(
                  url_string, self.computer_id)
    self.assertEqual('None', response)
    created_at = rfc1123_date(DateTime())
    response = self.portal_slap.getSoftwareInstallationStatus(
                      url_string, self.computer_id)
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>building software release %(url_string)s</unicode>
    <unicode>user</unicode>
    <unicode>%(computer_id)s</unicode>
  </dictionary>
</marshal>
""" % dict(
    created_at=created_at,
    url_string=url_string,
    computer_id=self.computer_id,
  )
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_softwareReleaseError(self):
    self._makeComplexComputer()
    self.computer_bang_simulator = tempfile.mkstemp()[1]
    self.login(self.computer_id)
    software_installation = self.start_requested_software_installation
    url_string = software_installation.getUrlString()
    response = self.portal_slap.softwareReleaseError(
                  url_string, self.computer_id, 'error log')
    self.assertEqual('None', response)
    created_at = rfc1123_date(DateTime())
    response = self.portal_slap.getSoftwareInstallationStatus(
                      url_string, self.computer_id)
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>#error while installing %(url_string)s</unicode>
    <unicode>user</unicode>
    <unicode>%(computer_id)s</unicode>
  </dictionary>
</marshal>
""" % dict(
    created_at=created_at,
    url_string=url_string,
    computer_id=self.computer_id,
  )
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_useComputer_wrong_xml(self):
    self.login(self.computer_id)
    response = self.portal_slap.useComputer(
        self.computer_id, "foobar")
    self.assertEqual(400, response.status)
    self.assertEqual("", response.body)

  def assertReportComputerConsumption(self, args, kwargs):
    stored = eval(open(self.computer_use_computer_simulator).read())
    # do the same translation magic as in workflow
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'Computer_reportComputerConsumption'}])

  def test_useComputer_expected_xml(self):
    self.computer_use_computer_simulator = tempfile.mkstemp()[1]
    try:
      self.login(self.computer_id)
      self.computer.Computer_reportComputerConsumption = Simulator(
        self.computer_use_computer_simulator,
        'Computer_reportComputerConsumption')
  
      consumption_xml = """<?xml version='1.0' encoding='utf-8'?>
<journal>
<transaction type="Sale Packing List">
<title>Resource consumptions</title>
<start_date></start_date>
<stop_date></stop_date>
<reference>testusagé</reference>
<currency></currency>
<payment_mode></payment_mode>
<category></category>
<arrow type="Administration">
<source></source>
<destination></destination>
</arrow>
<movement>
<resource>CPU Consumption</resource>
<title>Title Sale Packing List Line 1</title>
<reference>slappart0</reference>
<quantity>42.42</quantity>
<price>0.00</price>
<VAT>None</VAT>
<category>None</category>
</movement>
</transaction>
</journal>"""
  
      response = self.portal_slap.useComputer(
        self.computer_id, consumption_xml)
      self.assertEqual(200, response.status)
      self.assertEqual("OK", response.body)
      self.assertReportComputerConsumption(
        ("testusagé", consumption_xml,), {})
    finally:
      if os.path.exists(self.computer_use_computer_simulator):
        os.unlink(self.computer_use_computer_simulator)

  def test_useComputer_empty_reference(self):
    self.computer_use_computer_simulator = tempfile.mkstemp()[1]
    try:
      self.login(self.computer_id)
      self.computer.Computer_reportComputerConsumption = Simulator(
        self.computer_use_computer_simulator,
        'Computer_reportComputerConsumption')
  
      consumption_xml = """<?xml version='1.0' encoding='utf-8'?>
<journal>
<transaction type="Sale Packing List">
<title>Resource consumptions</title>
<start_date></start_date>
<stop_date></stop_date>
<reference></reference>
<currency></currency>
<payment_mode></payment_mode>
<category></category>
<arrow type="Administration">
<source></source>
<destination></destination>
</arrow>
<movement>
<resource>CPU Consumption</resource>
<title>Title Sale Packing List Line 1</title>
<reference>slappart0</reference>
<quantity>42.42</quantity>
<price>0.00</price>
<VAT>None</VAT>
<category>None</category>
</movement>
</transaction>
</journal>"""
  
      response = self.portal_slap.useComputer(
        self.computer_id, consumption_xml)
      self.assertEqual(200, response.status)
      self.assertEqual("OK", response.body)
      self.assertReportComputerConsumption(
        ("", consumption_xml,), {})
    finally:
      if os.path.exists(self.computer_use_computer_simulator):
        os.unlink(self.computer_use_computer_simulator)


class TestSlapOSSlapToolInstanceAccess(TestSlapOSSlapToolMixin):
  def test_getComputerPartitionCertificate(self):
    self._makeComplexComputer()
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    self.login(self.start_requested_software_instance.getReference())
    response = self.portal_slap.getComputerPartitionCertificate(self.computer_id,
        partition_id)
    self.assertEqual(200, response.status)
    self.assertEqual( 'public, max-age=0, must-revalidate',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <string>certificate</string>
    <string>%(instance_certificate)s</string>
    <string>key</string>
    <string>%(instance_key)s</string>
  </dictionary>
</marshal>
""" % dict(
  instance_certificate=self.start_requested_software_instance.getSslCertificate(),
  instance_key=self.start_requested_software_instance.getSslKey()
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_getFullComputerInformation(self):
    self._makeComplexComputer(with_slave=True)
    self.login(self.start_requested_software_instance.getReference())
    response = self.portal_slap.getFullComputerInformation(self.computer_id)
    self.assertEqual(200, response.status)
    self.assertEqual('public, max-age=1, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <object id='i2' module='slapos.slap.slap' class='Computer'>
    <tuple>
      <unicode>%(computer_id)s</unicode>
    </tuple>
    <dictionary id='i3'>
      <string>_computer_id</string>
      <unicode>%(computer_id)s</unicode>
      <string>_computer_partition_list</string>
      <list id='i4'>
        <object id='i5' module='slapos.slap.slap' class='ComputerPartition'>
          <tuple>
            <unicode>%(computer_id)s</unicode>
            <unicode>partition1</unicode>
          </tuple>
          <dictionary id='i6'>
            <string>_computer_id</string>
            <unicode>%(computer_id)s</unicode>
            <string>_connection_dict</string>
            <dictionary id='i7'/>
            <string>_filter_dict</string>
            <dictionary id='i8'>
              <unicode>paramé</unicode>
              <unicode>%(sla)s</unicode>
            </dictionary>
            <string>_instance_guid</string>
            <unicode>%(instance_guid)s</unicode>
            <string>_need_modification</string>
            <int>1</int>
            <string>_parameter_dict</string>
            <dictionary id='i9'>
              <string>full_ip_list</string>
              <list id='i10'/>
              <string>ip_list</string>
              <list id='i11'>
                <tuple>
                  <unicode/>
                  <unicode>ip_address_1</unicode>
                </tuple>
              </list>
              <unicode>paramé</unicode>
              <unicode>%(param)s</unicode>
              <string>slap_computer_id</string>
              <unicode>%(computer_id)s</unicode>
              <string>slap_computer_partition_id</string>
              <unicode>partition1</unicode>
              <string>slap_software_release_url</string>
              <unicode>%(software_release_url)s</unicode>
              <string>slap_software_type</string>
              <unicode>%(software_type)s</unicode>
              <string>slave_instance_list</string>
              <list id='i12'>
                <dictionary id='i13'>
                  <unicode>paramé</unicode>
                  <unicode>%(slave_1_param)s</unicode>
                  <string>slap_software_type</string>
                  <unicode>%(slave_1_software_type)s</unicode>
                  <string>slave_reference</string>
                  <unicode>%(slave_1_instance_guid)s</unicode>
                  <string>slave_title</string>
                  <unicode>%(slave_1_title)s</unicode>
                  <string>timestamp</string>
                  <int>%(timestamp)s</int>
                </dictionary>
              </list>
              <string>timestamp</string>
              <string>%(timestamp)s</string>
            </dictionary>
            <string>_partition_id</string>
            <unicode>partition1</unicode>
            <string>_request_dict</string>
            <none/>
            <string>_requested_state</string>
            <string>started</string>
            <string>_software_release_document</string>
            <object id='i14' module='slapos.slap.slap' class='SoftwareRelease'>
              <tuple>
                <unicode>%(software_release_url)s</unicode>
                <unicode>%(computer_id)s</unicode>
              </tuple>
              <dictionary id='i15'>
                <string>_computer_guid</string>
                <unicode>%(computer_id)s</unicode>
                <string>_software_instance_list</string>
                <list id='i16'/>
                <string>_software_release</string>
                <unicode>%(software_release_url)s</unicode>
              </dictionary>
            </object>
          </dictionary>
        </object>
      </list>
      <string>_software_release_list</string>
      <list id='i17'/>
    </dictionary>
  </object>
</marshal>
""" % dict(
    computer_id=self.computer_id,
    instance_guid=self.start_requested_software_instance.getReference(),
    software_release_url=self.start_requested_software_instance.getUrlString(),
    software_type=self.start_requested_software_instance.getSourceReference(),
    param=self.start_requested_software_instance.getInstanceXmlAsDict()['paramé'],
    sla=self.start_requested_software_instance.getSlaXmlAsDict()['paramé'],
    timestamp=int(self.start_requested_software_instance.getModificationDate()),
    slave_1_param=self.start_requested_slave_instance.getInstanceXmlAsDict()['paramé'],
    slave_1_software_type=self.start_requested_slave_instance.getSourceReference(),
    slave_1_instance_guid=self.start_requested_slave_instance.getReference(),
    slave_1_title=self.start_requested_slave_instance.getTitle(),
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_getComputerPartitionStatus(self):
    self._makeComplexComputer()
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    created_at = rfc1123_date(DateTime())
    self.login(self.start_requested_software_instance.getReference())
    response = self.portal_slap.getComputerPartitionStatus(self.computer_id,
      partition_id)
    self.assertEqual(200, response.status)
    self.assertEqual( 'public, max-age=60, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <string>created_at</string>
    <string>%(created_at)s</string>
    <string>text</string>
    <unicode>#error no data found for %(instance_guid)s</unicode>
    <string>user</string>
    <unicode>SlapOS Master</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  instance_guid=self.start_requested_software_instance.getReference(),
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_getComputerPartitionStatus_visited(self):
    self._makeComplexComputer()
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    created_at = rfc1123_date(DateTime())
    self.login(self.start_requested_software_instance.getReference())
    self.portal_slap.registerComputerPartition(self.computer_id, partition_id)
    response = self.portal_slap.getComputerPartitionStatus(self.computer_id,
      partition_id)
    self.assertEqual(200, response.status)
    self.assertEqual( 'public, max-age=60, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <string>created_at</string>
    <string>%(created_at)s</string>
    <string>text</string>
    <unicode>#error no data found for %(instance_guid)s</unicode>
    <string>user</string>
    <unicode>SlapOS Master</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  instance_guid=self.start_requested_software_instance.getReference(),
  computer_id=self.computer_id,
  partition_id=partition_id
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_registerComputerPartition_withSlave(self):
    self._makeComplexComputer(with_slave=True)
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    self.login(self.start_requested_software_instance.getReference())
    response = self.portal_slap.registerComputerPartition(self.computer_id, partition_id)
    self.assertEqual(200, response.status)
    self.assertEqual( 'public, max-age=1, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <object id='i2' module='slapos.slap.slap' class='ComputerPartition'>
    <tuple>
      <unicode>%(computer_id)s</unicode>
      <unicode>partition1</unicode>
    </tuple>
    <dictionary id='i3'>
      <string>_computer_id</string>
      <unicode>%(computer_id)s</unicode>
      <string>_connection_dict</string>
      <dictionary id='i4'/>
      <string>_filter_dict</string>
      <dictionary id='i5'>
        <unicode>paramé</unicode>
        <unicode>%(sla)s</unicode>
      </dictionary>
      <string>_instance_guid</string>
      <unicode>%(instance_guid)s</unicode>
      <string>_need_modification</string>
      <int>1</int>
      <string>_parameter_dict</string>
      <dictionary id='i6'>
        <string>full_ip_list</string>
        <list id='i7'/>
        <string>ip_list</string>
        <list id='i8'>
          <tuple>
            <unicode/>
            <unicode>ip_address_1</unicode>
          </tuple>
        </list>
        <unicode>paramé</unicode>
        <unicode>%(param)s</unicode>
        <string>slap_computer_id</string>
        <unicode>%(computer_id)s</unicode>
        <string>slap_computer_partition_id</string>
        <unicode>partition1</unicode>
        <string>slap_software_release_url</string>
        <unicode>%(software_release_url)s</unicode>
        <string>slap_software_type</string>
        <unicode>%(software_type)s</unicode>
        <string>slave_instance_list</string>
        <list id='i9'>
          <dictionary id='i10'>
            <unicode>paramé</unicode>
            <unicode>%(slave_1_param)s</unicode>
            <string>slap_software_type</string>
            <unicode>%(slave_1_software_type)s</unicode>
            <string>slave_reference</string>
            <unicode>%(slave_1_instance_guid)s</unicode>
            <string>slave_title</string>
            <unicode>%(slave_1_title)s</unicode>
            <string>timestamp</string>
            <int>%(timestamp)s</int>
          </dictionary>
        </list>
        <string>timestamp</string>
        <string>%(timestamp)s</string>
      </dictionary>
      <string>_partition_id</string>
      <unicode>partition1</unicode>
      <string>_request_dict</string>
      <none/>
      <string>_requested_state</string>
      <string>started</string>
      <string>_software_release_document</string>
      <object id='i11' module='slapos.slap.slap' class='SoftwareRelease'>
        <tuple>
          <unicode>%(software_release_url)s</unicode>
          <unicode>%(computer_id)s</unicode>
        </tuple>
        <dictionary id='i12'>
          <string>_computer_guid</string>
          <unicode>%(computer_id)s</unicode>
          <string>_software_instance_list</string>
          <list id='i13'/>
          <string>_software_release</string>
          <unicode>%(software_release_url)s</unicode>
        </dictionary>
      </object>
      <string>_synced</string>
      <bool>1</bool>
    </dictionary>
  </object>
</marshal>
""" % dict(
  computer_id=self.computer_id,
  param=self.start_requested_software_instance.getInstanceXmlAsDict()['paramé'],
  sla=self.start_requested_software_instance.getSlaXmlAsDict()['paramé'],
  software_release_url=self.start_requested_software_instance.getUrlString(),
  timestamp=int(self.start_requested_software_instance.getModificationDate()),
  instance_guid=self.start_requested_software_instance.getReference(),
  software_type=self.start_requested_software_instance.getSourceReference(),
  slave_1_param=self.start_requested_slave_instance.getInstanceXmlAsDict()['paramé'],
  slave_1_software_type=self.start_requested_slave_instance.getSourceReference(),
  slave_1_instance_guid=self.start_requested_slave_instance.getReference(),
  slave_1_title=self.start_requested_slave_instance.getTitle(),
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_registerComputerPartition(self):
    self._makeComplexComputer()
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    self.login(self.start_requested_software_instance.getReference())
    response = self.portal_slap.registerComputerPartition(self.computer_id, partition_id)
    self.assertEqual(200, response.status)
    self.assertEqual( 'public, max-age=1, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <object id='i2' module='slapos.slap.slap' class='ComputerPartition'>
    <tuple>
      <unicode>%(computer_id)s</unicode>
      <unicode>partition1</unicode>
    </tuple>
    <dictionary id='i3'>
      <string>_computer_id</string>
      <unicode>%(computer_id)s</unicode>
      <string>_connection_dict</string>
      <dictionary id='i4'/>
      <string>_filter_dict</string>
      <dictionary id='i5'>
        <unicode>paramé</unicode>
        <unicode>%(sla)s</unicode>
      </dictionary>
      <string>_instance_guid</string>
      <unicode>%(instance_guid)s</unicode>
      <string>_need_modification</string>
      <int>1</int>
      <string>_parameter_dict</string>
      <dictionary id='i6'>
        <string>full_ip_list</string>
        <list id='i7'/>
        <string>ip_list</string>
        <list id='i8'>
          <tuple>
            <unicode/>
            <unicode>ip_address_1</unicode>
          </tuple>
        </list>
        <unicode>paramé</unicode>
        <unicode>%(param)s</unicode>
        <string>slap_computer_id</string>
        <unicode>%(computer_id)s</unicode>
        <string>slap_computer_partition_id</string>
        <unicode>partition1</unicode>
        <string>slap_software_release_url</string>
        <unicode>%(software_release_url)s</unicode>
        <string>slap_software_type</string>
        <unicode>%(software_type)s</unicode>
        <string>slave_instance_list</string>
        <list id='i9'/>
        <string>timestamp</string>
        <string>%(timestamp)s</string>
      </dictionary>
      <string>_partition_id</string>
      <unicode>partition1</unicode>
      <string>_request_dict</string>
      <none/>
      <string>_requested_state</string>
      <string>started</string>
      <string>_software_release_document</string>
      <object id='i10' module='slapos.slap.slap' class='SoftwareRelease'>
        <tuple>
          <unicode>%(software_release_url)s</unicode>
          <unicode>%(computer_id)s</unicode>
        </tuple>
        <dictionary id='i11'>
          <string>_computer_guid</string>
          <unicode>%(computer_id)s</unicode>
          <string>_software_instance_list</string>
          <list id='i12'/>
          <string>_software_release</string>
          <unicode>%(software_release_url)s</unicode>
        </dictionary>
      </object>
      <string>_synced</string>
      <bool>1</bool>
    </dictionary>
  </object>
</marshal>
""" % dict(
  computer_id=self.computer_id,
  param=self.start_requested_software_instance.getInstanceXmlAsDict()['paramé'],
  sla=self.start_requested_software_instance.getSlaXmlAsDict()['paramé'],
  software_release_url=self.start_requested_software_instance.getUrlString(),
  timestamp=int(self.start_requested_software_instance.getModificationDate()),
  instance_guid=self.start_requested_software_instance.getReference(),
  software_type=self.start_requested_software_instance.getSourceReference()
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def assertInstanceUpdateConnectionSimulator(self, args, kwargs):
    stored = eval(open(self.instance_update_connection_simulator).read())
    # do the same translation magic as in workflow
    kwargs['connection_xml'] = kwargs.pop('connection_xml')
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'updateConnection'}])

  def test_setConnectionXml_withSlave(self):
    self._makeComplexComputer(with_slave=True)
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    slave_reference = self.start_requested_slave_instance.getReference()
    connection_xml = """<marshal>
  <dictionary id="i2">
    <unicode>p1é</unicode>
    <unicode>v1é</unicode>
    <unicode>p2é</unicode>
    <unicode>v2é</unicode>
  </dictionary>
</marshal>"""
    stored_xml = """<?xml version='1.0' encoding='utf-8'?>
<instance>
  <parameter id="p1é">v1é</parameter>
  <parameter id="p2é">v2é</parameter>
</instance>
"""
    self.login(self.start_requested_software_instance.getReference())

    self.instance_update_connection_simulator = tempfile.mkstemp()[1]
    try:
      self.start_requested_slave_instance.updateConnection = Simulator(
        self.instance_update_connection_simulator, 'updateConnection')
      response = self.portal_slap.setComputerPartitionConnectionXml(
        self.computer_id, partition_id, connection_xml, slave_reference)
      self.assertEqual('None', response)
      self.assertInstanceUpdateConnectionSimulator((),
          {'connection_xml': stored_xml})
    finally:
      if os.path.exists(self.instance_update_connection_simulator):
        os.unlink(self.instance_update_connection_simulator)

  def test_setConnectionXml(self):
    self._makeComplexComputer()
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    connection_xml = """<marshal>
  <dictionary id="i2">
    <unicode>p1é</unicode>
    <unicode>v1é</unicode>
    <unicode>p2é</unicode>
    <unicode>v2é</unicode>
  </dictionary>
</marshal>"""
    stored_xml = """<?xml version='1.0' encoding='utf-8'?>
<instance>
  <parameter id="p1é">v1é</parameter>
  <parameter id="p2é">v2é</parameter>
</instance>
"""
    self.login(self.start_requested_software_instance.getReference())

    self.instance_update_connection_simulator = tempfile.mkstemp()[1]
    try:
      self.start_requested_software_instance.updateConnection = Simulator(
        self.instance_update_connection_simulator, 'updateConnection')
      response = self.portal_slap.setComputerPartitionConnectionXml(
          self.computer_id, partition_id, connection_xml)
      self.assertEqual('None', response)
      self.assertInstanceUpdateConnectionSimulator((),
          {'connection_xml': stored_xml})
    finally:
      if os.path.exists(self.instance_update_connection_simulator):
        os.unlink(self.instance_update_connection_simulator)

  def test_softwareInstanceError(self):
    self._makeComplexComputer()
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    self.login(self.start_requested_software_instance.getReference())
    error_log = 'The error'
    response = self.portal_slap.softwareInstanceError(self.computer_id,
      partition_id, error_log)
    self.assertEqual('None', response)
    created_at = rfc1123_date(DateTime())
    response = self.portal_slap.getComputerPartitionStatus(self.computer_id,
      partition_id)
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>#error while instanciating</unicode>
    <unicode>user</unicode>
    <unicode>%(instance_guid)s</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  instance_guid=self.start_requested_software_instance.getReference(),
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def assertInstanceBangSimulator(self, args, kwargs):
    stored = eval(open(self.instance_bang_simulator).read())
    # do the same translation magic as in workflow
    kwargs['comment'] = kwargs.pop('comment')
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'bang'}])

  def test_softwareInstanceBang(self):
    self._makeComplexComputer()
    self.instance_bang_simulator = tempfile.mkstemp()[1]
    try:
      partition_id = self.start_requested_software_instance.getAggregateValue(
          portal_type='Computer Partition').getReference()
      self.login(self.start_requested_software_instance.getReference())
      self.start_requested_software_instance.bang = Simulator(
        self.instance_bang_simulator, 'bang')
      error_log = 'Please bang me'
      response = self.portal_slap.softwareInstanceBang(self.computer_id,
        partition_id, error_log)
      self.assertEqual('OK', response)
      created_at = rfc1123_date(DateTime())
      response = self.portal_slap.getComputerPartitionStatus(self.computer_id,
        partition_id)
      # check returned XML
      xml_fp = StringIO.StringIO()

      xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
          stream=xml_fp)
      xml_fp.seek(0)
      got_xml = xml_fp.read()
      expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>#error bang called</unicode>
    <unicode>user</unicode>
    <unicode>%(instance_guid)s</unicode>
  </dictionary>
</marshal>
""" % dict(
    created_at=created_at,
    instance_guid=self.start_requested_software_instance.getReference(),
  )
      self.assertEqual(expected_xml, got_xml,
          '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))
      self.assertInstanceBangSimulator((), {'comment': error_log, 'bang_tree': True})
    finally:
      if os.path.exists(self.instance_bang_simulator):
        os.unlink(self.instance_bang_simulator)
      
  def assertInstanceRenameSimulator(self, args, kwargs):
    stored = eval(open(self.instance_rename_simulator).read())
    # do the same translation magic as in workflow
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'rename'}])

  def test_softwareInstanceRename(self):
    self._makeComplexComputer()
    self.instance_rename_simulator = tempfile.mkstemp()[1]
    try:
      partition_id = self.start_requested_software_instance.getAggregateValue(
          portal_type='Computer Partition').getReference()
      self.login(self.start_requested_software_instance.getReference())
      self.start_requested_software_instance.rename = Simulator(
        self.instance_rename_simulator, 'rename')
      new_name = 'new me'
      response = self.portal_slap.softwareInstanceRename(new_name, self.computer_id,
        partition_id)
      self.assertEqual('None', response)
      self.assertInstanceRenameSimulator((), {
          'comment': 'Rename %s into %s' % (self.start_requested_software_instance.getTitle(),
            new_name), 'new_name': new_name})
    finally:
      if os.path.exists(self.instance_rename_simulator):
        os.unlink(self.instance_rename_simulator)
      
  def test_destroyedComputerPartition(self):
    self._makeComplexComputer()
    partition_id = self.destroy_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    self.login(self.destroy_requested_software_instance.getReference())
    response = self.portal_slap.destroyedComputerPartition(self.computer_id,
      partition_id)
    self.assertEqual('None', response)
    self.assertEqual('invalidated',
        self.destroy_requested_software_instance.getValidationState())
    self.assertEqual(None, self.destroy_requested_software_instance.getSslKey())
    self.assertEqual(None, self.destroy_requested_software_instance.getSslCertificate())

  def assertInstanceRequestSimulator(self, args, kwargs):
    stored = eval(open(self.instance_request_simulator).read())
    # do the same translation magic as in workflow
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'requestInstance'}])

  def test_request_withSlave(self):
    self._makeComplexComputer()
    self.instance_request_simulator = tempfile.mkstemp()[1]
    try:
      partition_id = self.start_requested_software_instance.getAggregateValue(
          portal_type='Computer Partition').getReference()
      self.login(self.start_requested_software_instance.getReference())
      self.start_requested_software_instance.requestInstance = Simulator(
        self.instance_request_simulator, 'requestInstance')
      response = self.portal_slap.requestComputerPartition(
          computer_id=self.computer_id,
          computer_partition_id=partition_id,
          software_release='req_release',
          software_type='req_type',
          partition_reference='req_reference',
          partition_parameter_xml='<marshal><dictionary id="i2"/></marshal>',
          filter_xml='<marshal><dictionary id="i2"/></marshal>',
          state='<marshal><string>started</string></marshal>',
          shared_xml='<marshal><bool>1</bool></marshal>',
          )
      self.assertEqual(408, response.status)
      self.assertEqual('private',
          response.headers.get('cache-control'))
      self.assertInstanceRequestSimulator((), {
          'instance_xml': "<?xml version='1.0' encoding='utf-8'?>\n<instance/>\n",
          'software_title': 'req_reference',
          'software_release': 'req_release',
          'state': 'started',
          'sla_xml': "<?xml version='1.0' encoding='utf-8'?>\n<instance/>\n",
          'software_type': 'req_type',
          'shared': True})
    finally:
      if os.path.exists(self.instance_request_simulator):
        os.unlink(self.instance_request_simulator)

  def test_request(self):
    self._makeComplexComputer()
    self.instance_request_simulator = tempfile.mkstemp()[1]
    try:
      partition_id = self.start_requested_software_instance.getAggregateValue(
          portal_type='Computer Partition').getReference()
      self.login(self.start_requested_software_instance.getReference())
      self.start_requested_software_instance.requestInstance = Simulator(
        self.instance_request_simulator, 'requestInstance')
      response = self.portal_slap.requestComputerPartition(
          computer_id=self.computer_id,
          computer_partition_id=partition_id,
          software_release='req_release',
          software_type='req_type',
          partition_reference='req_reference',
          partition_parameter_xml='<marshal><dictionary id="i2"/></marshal>',
          filter_xml='<marshal><dictionary id="i2"/></marshal>',
          state='<marshal><string>started</string></marshal>',
          shared_xml='<marshal><bool>0</bool></marshal>',
          )
      self.assertEqual(408, response.status)
      self.assertEqual('private',
          response.headers.get('cache-control'))
      self.assertInstanceRequestSimulator((), {
          'instance_xml': "<?xml version='1.0' encoding='utf-8'?>\n<instance/>\n",
          'software_title': 'req_reference',
          'software_release': 'req_release',
          'state': 'started',
          'sla_xml': "<?xml version='1.0' encoding='utf-8'?>\n<instance/>\n",
          'software_type': 'req_type',
          'shared': False})
    finally:
      if os.path.exists(self.instance_request_simulator):
        os.unlink(self.instance_request_simulator)

  def test_availableComputerPartition(self):
    self._makeComplexComputer()
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    self.login(self.start_requested_software_instance.getReference())
    response = self.portal_slap.availableComputerPartition(self.computer_id,
      partition_id)
    self.assertEqual('None', response)
    created_at = rfc1123_date(DateTime())
    response = self.portal_slap.getComputerPartitionStatus(self.computer_id,
      partition_id)
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>#access instance available</unicode>
    <unicode>user</unicode>
    <unicode>%(instance_guid)s</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  instance_guid=self.start_requested_software_instance.getReference(),
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_buildingComputerPartition(self):
    self._makeComplexComputer()
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    self.login(self.start_requested_software_instance.getReference())
    response = self.portal_slap.buildingComputerPartition(self.computer_id,
      partition_id)
    self.assertEqual('None', response)
    created_at = rfc1123_date(DateTime())
    response = self.portal_slap.getComputerPartitionStatus(self.computer_id,
      partition_id)
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>building the instance</unicode>
    <unicode>user</unicode>
    <unicode>%(instance_guid)s</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  instance_guid=self.start_requested_software_instance.getReference(),
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_stoppedComputerPartition(self):
    self._makeComplexComputer()
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    self.login(self.start_requested_software_instance.getReference())
    response = self.portal_slap.stoppedComputerPartition(self.computer_id,
      partition_id)
    self.assertEqual('None', response)
    created_at = rfc1123_date(DateTime())
    response = self.portal_slap.getComputerPartitionStatus(self.computer_id,
      partition_id)
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>#access Instance correctly stopped</unicode>
    <unicode>user</unicode>
    <unicode>%(instance_guid)s</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  instance_guid=self.start_requested_software_instance.getReference(),
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_startedComputerPartition(self):
    self._makeComplexComputer()
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    self.login(self.start_requested_software_instance.getReference())
    response = self.portal_slap.startedComputerPartition(self.computer_id,
      partition_id)
    self.assertEqual('None', response)
    created_at = rfc1123_date(DateTime())
    response = self.portal_slap.getComputerPartitionStatus(self.computer_id,
      partition_id)
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>#access Instance correctly started</unicode>
    <unicode>user</unicode>
    <unicode>%(instance_guid)s</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  instance_guid=self.start_requested_software_instance.getReference(),
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_getSoftwareReleaseListFromSoftwareProduct(self):
    new_id = self.generateNewId()
    software_product = self._makeSoftwareProduct(new_id)
    # 2 published software releases
    software_release1 = self._makeSoftwareRelease(new_id)
    software_release2 = self._makeSoftwareRelease(self.generateNewId())
    software_release1.publish()
    software_release2.publish()
    # 1 released software release, should not appear
    software_release3 = self._makeSoftwareRelease(new_id)
    self.assertTrue(software_release3.getValidationState() == 'released')
    software_release1.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/1.cfg',
        effective_date=DateTime()
    )
    software_release2.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/2.cfg',
        effective_date=DateTime()
    )
    software_release3.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/3.cfg'
    )
    self.tic()

    response = self.portal_slap.getSoftwareReleaseListFromSoftwareProduct(
        software_product.getReference())
    # check returned XML
    xml_fp = StringIO.StringIO()
    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <list id='i2'>
    <string>%s</string>
    <string>%s</string>
  </list>
</marshal>
""" % (software_release2.getUrlString(), software_release1.getUrlString())
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))
  
  def test_getSoftwareReleaseListFromSoftwareProduct_effectiveDate(self):
    new_id = self.generateNewId()
    software_product = self._makeSoftwareProduct(new_id)
    # 3 published software releases
    software_release1 = self._makeSoftwareRelease(new_id)
    software_release2 = self._makeSoftwareRelease(self.generateNewId())
    software_release3 = self._makeSoftwareRelease(self.generateNewId())
    software_release1.publish()
    software_release2.publish()
    software_release3.publish()
    software_release1.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/1.cfg',
        effective_date=(DateTime() - 1)
    )
    # Should not be considered yet!
    software_release2.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/2.cfg',
        effective_date=(DateTime() + 1)
    )
    software_release3.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/3.cfg',
        effective_date=DateTime()
    )
    self.tic()

    response = self.portal_slap.getSoftwareReleaseListFromSoftwareProduct(
        software_product.getReference())
    # check returned XML
    xml_fp = StringIO.StringIO()
    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <list id='i2'>
    <string>%s</string>
    <string>%s</string>
    <string>%s</string>
  </list>
</marshal>
""" % (software_release3.getUrlString(), software_release1.getUrlString(),
        software_release2.getUrlString())
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_getSoftwareReleaseListFromSoftwareProduct_emptySoftwareProduct(self):
    new_id = self.generateNewId()
    software_product = self._makeSoftwareProduct(new_id)

    response = self.portal_slap.getSoftwareReleaseListFromSoftwareProduct(
        software_product.getReference())
    # check returned XML
    xml_fp = StringIO.StringIO()
    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <list id='i2'/>
</marshal>
""" 
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_getSoftwareReleaseListFromSoftwareProduct_NoSoftwareProduct(self):
    response = self.portal_slap.getSoftwareReleaseListFromSoftwareProduct(
        'Can I has a nonexistent software product?')
    # check returned XML
    xml_fp = StringIO.StringIO()
    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <list id='i2'/>
</marshal>
""" 
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_getSoftwareReleaseListFromSoftwareProduct_fromUrl(self):
    new_id = self.generateNewId()
    software_product = self._makeSoftwareProduct(new_id)
    # 2 published software releases
    software_release1 = self._makeSoftwareRelease(new_id)
    software_release2 = self._makeSoftwareRelease(self.generateNewId())
    software_release1.publish()
    software_release2.publish()
    # 1 released software release, should not appear
    software_release3 = self._makeSoftwareRelease(new_id)
    self.assertTrue(software_release3.getValidationState() == 'released')
    software_release1.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/1.cfg'
    )
    software_release2.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/2.cfg'
    )
    software_release3.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/3.cfg'
    )
    self.tic()

    response = self.portal_slap.getSoftwareReleaseListFromSoftwareProduct(
        software_release_url=software_release2.getUrlString())
    # check returned XML
    xml_fp = StringIO.StringIO()
    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <list id='i2'>
    <string>%s</string>
    <string>%s</string>
  </list>
</marshal>
""" % (software_release2.getUrlString(), software_release1.getUrlString())
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))


class TestSlapOSSlapToolPersonAccess(TestSlapOSSlapToolMixin):
  def afterSetUp(self):
    password = self.generateNewId()
    reference = 'test_%s' % self.generateNewId()
    person = self.portal.person_module.newContent(portal_type='Person',
      title=reference,
      reference=reference, password=password)
    person.newContent(portal_type='Assignment', role='member').open()

    transaction.commit()
    person.recursiveImmediateReindexObject()
    self.person = person
    self.person_reference = person.getReference()
    TestSlapOSSlapToolMixin.afterSetUp(self, person=person)

  def test_not_accessed_getComputerStatus(self):
    self.login(self.person_reference)
    created_at = rfc1123_date(DateTime())
    response = self.portal_slap.getComputerStatus(self.computer_id)
    self.assertEqual(200, response.status)
    self.assertEqual('public, max-age=60, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()

    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <string>created_at</string>
    <string>%(created_at)s</string>
    <string>text</string>
    <unicode>#error no data found for %(computer_id)s</unicode>
    <string>user</string>
    <unicode>SlapOS Master</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  computer_id=self.computer_id
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_accessed_getComputerStatus(self):
    self.login(self.computer_id)
    self.portal_slap.getFullComputerInformation(self.computer_id)
    self.login(self.person_reference)
    created_at = rfc1123_date(DateTime())
    response = self.portal_slap.getComputerStatus(self.computer_id)
    self.assertEqual(200, response.status)
    self.assertEqual('public, max-age=60, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))

    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()

    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>#access %(computer_id)s</unicode>
    <unicode>user</unicode>
    <unicode>%(computer_id)s</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  computer_id=self.computer_id
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def assertComputerBangSimulator(self, args, kwargs):
    stored = eval(open(self.computer_bang_simulator).read())
    # do the same translation magic as in workflow
    kwargs['comment'] = kwargs.pop('comment')
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'reportComputerBang'}])

  def test_computerBang(self):
    self.login(self.person_reference)
    self.computer_bang_simulator = tempfile.mkstemp()[1]
    try:
      self.computer.reportComputerBang = Simulator(
        self.computer_bang_simulator, 'reportComputerBang')
      error_log = 'Please bang me'
      response = self.portal_slap.computerBang(self.computer_id,
        error_log)
      self.assertEqual('None', response)
      created_at = rfc1123_date(DateTime())
      response = self.portal_slap.getComputerStatus(self.computer_id)
      # check returned XML
      xml_fp = StringIO.StringIO()

      xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
          stream=xml_fp)
      xml_fp.seek(0)
      got_xml = xml_fp.read()
      expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>#error bang</unicode>
    <unicode>user</unicode>
    <unicode>%(person_reference)s</unicode>
  </dictionary>
</marshal>
""" % dict(
    created_at=created_at,
    person_reference=self.person_reference,
  )
      self.assertEqual(expected_xml, got_xml,
          '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))
      self.assertComputerBangSimulator((), {'comment': error_log})
    finally:
      if os.path.exists(self.computer_bang_simulator):
        os.unlink(self.computer_bang_simulator)

  def test_getComputerPartitionStatus(self):
    self._makeComplexComputer()
    self.login(self.person_reference)
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    created_at = rfc1123_date(DateTime())
    self.login(self.start_requested_software_instance.getReference())
    response = self.portal_slap.getComputerPartitionStatus(self.computer_id,
      partition_id)
    self.assertEqual(200, response.status)
    self.assertEqual( 'public, max-age=60, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <string>created_at</string>
    <string>%(created_at)s</string>
    <string>text</string>
    <unicode>#error no data found for %(instance_guid)s</unicode>
    <string>user</string>
    <unicode>SlapOS Master</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  instance_guid=self.start_requested_software_instance.getReference(),
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_getComputerPartitionStatus_visited(self):
    self._makeComplexComputer(person=self.person)
    self.login(self.person_reference)
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    created_at = rfc1123_date(DateTime())
    self.login(self.start_requested_software_instance.getReference())
    self.portal_slap.registerComputerPartition(self.computer_id, partition_id)
    self.login(self.person_reference)
    response = self.portal_slap.getComputerPartitionStatus(self.computer_id,
      partition_id)
    self.assertEqual(200, response.status)
    self.assertEqual( 'public, max-age=60, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <string>created_at</string>
    <string>%(created_at)s</string>
    <string>text</string>
    <unicode>#error no data found for %(instance_guid)s</unicode>
    <string>user</string>
    <unicode>SlapOS Master</unicode>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  instance_guid=self.start_requested_software_instance.getReference(),
  computer_id=self.computer_id,
  partition_id=partition_id
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_registerComputerPartition_withSlave(self):
    self._makeComplexComputer(person=self.person, with_slave=True)
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    self.login(self.person_reference)
    response = self.portal_slap.registerComputerPartition(self.computer_id, partition_id)
    self.assertEqual(200, response.status)
    self.assertEqual( 'public, max-age=1, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <object id='i2' module='slapos.slap.slap' class='ComputerPartition'>
    <tuple>
      <unicode>%(computer_id)s</unicode>
      <unicode>partition1</unicode>
    </tuple>
    <dictionary id='i3'>
      <string>_computer_id</string>
      <unicode>%(computer_id)s</unicode>
      <string>_connection_dict</string>
      <dictionary id='i4'/>
      <string>_filter_dict</string>
      <dictionary id='i5'>
        <unicode>paramé</unicode>
        <unicode>%(sla)s</unicode>
      </dictionary>
      <string>_instance_guid</string>
      <unicode>%(instance_guid)s</unicode>
      <string>_need_modification</string>
      <int>1</int>
      <string>_parameter_dict</string>
      <dictionary id='i6'>
        <string>full_ip_list</string>
        <list id='i7'/>
        <string>ip_list</string>
        <list id='i8'>
          <tuple>
            <unicode/>
            <unicode>ip_address_1</unicode>
          </tuple>
        </list>
        <unicode>paramé</unicode>
        <unicode>%(param)s</unicode>
        <string>slap_computer_id</string>
        <unicode>%(computer_id)s</unicode>
        <string>slap_computer_partition_id</string>
        <unicode>partition1</unicode>
        <string>slap_software_release_url</string>
        <unicode>%(software_release_url)s</unicode>
        <string>slap_software_type</string>
        <unicode>%(software_type)s</unicode>
        <string>slave_instance_list</string>
        <list id='i9'>
          <dictionary id='i10'>
            <unicode>paramé</unicode>
            <unicode>%(slave_1_param)s</unicode>
            <string>slap_software_type</string>
            <unicode>%(slave_1_software_type)s</unicode>
            <string>slave_reference</string>
            <unicode>%(slave_1_instance_guid)s</unicode>
            <string>slave_title</string>
            <unicode>%(slave_1_title)s</unicode>
            <string>timestamp</string>
            <int>%(timestamp)s</int>
          </dictionary>
        </list>
        <string>timestamp</string>
        <string>%(timestamp)s</string>
      </dictionary>
      <string>_partition_id</string>
      <unicode>partition1</unicode>
      <string>_request_dict</string>
      <none/>
      <string>_requested_state</string>
      <string>started</string>
      <string>_software_release_document</string>
      <object id='i11' module='slapos.slap.slap' class='SoftwareRelease'>
        <tuple>
          <unicode>%(software_release_url)s</unicode>
          <unicode>%(computer_id)s</unicode>
        </tuple>
        <dictionary id='i12'>
          <string>_computer_guid</string>
          <unicode>%(computer_id)s</unicode>
          <string>_software_instance_list</string>
          <list id='i13'/>
          <string>_software_release</string>
          <unicode>%(software_release_url)s</unicode>
        </dictionary>
      </object>
      <string>_synced</string>
      <bool>1</bool>
    </dictionary>
  </object>
</marshal>
""" % dict(
  computer_id=self.computer_id,
  param=self.start_requested_software_instance.getInstanceXmlAsDict()['paramé'],
  sla=self.start_requested_software_instance.getSlaXmlAsDict()['paramé'],
  software_release_url=self.start_requested_software_instance.getUrlString(),
  timestamp=int(self.start_requested_software_instance.getModificationDate()),
  instance_guid=self.start_requested_software_instance.getReference(),
  software_type=self.start_requested_software_instance.getSourceReference(),
  slave_1_param=self.start_requested_slave_instance.getInstanceXmlAsDict()['paramé'],
  slave_1_software_type=self.start_requested_slave_instance.getSourceReference(),
  slave_1_instance_guid=self.start_requested_slave_instance.getReference(),
  slave_1_title=self.start_requested_slave_instance.getTitle(),
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_registerComputerPartition(self):
    self._makeComplexComputer(person=self.person)
    partition_id = self.start_requested_software_instance.getAggregateValue(
        portal_type='Computer Partition').getReference()
    self.login(self.person_reference)
    response = self.portal_slap.registerComputerPartition(self.computer_id, partition_id)
    self.assertEqual(200, response.status)
    self.assertEqual( 'public, max-age=1, stale-if-error=604800',
        response.headers.get('cache-control'))
    self.assertEqual('REMOTE_USER',
        response.headers.get('vary'))
    self.assertTrue('last-modified' in response.headers)
    self.assertEqual('text/xml; charset=utf-8',
        response.headers.get('content-type'))
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <object id='i2' module='slapos.slap.slap' class='ComputerPartition'>
    <tuple>
      <unicode>%(computer_id)s</unicode>
      <unicode>partition1</unicode>
    </tuple>
    <dictionary id='i3'>
      <string>_computer_id</string>
      <unicode>%(computer_id)s</unicode>
      <string>_connection_dict</string>
      <dictionary id='i4'/>
      <string>_filter_dict</string>
      <dictionary id='i5'>
        <unicode>paramé</unicode>
        <unicode>%(sla)s</unicode>
      </dictionary>
      <string>_instance_guid</string>
      <unicode>%(instance_guid)s</unicode>
      <string>_need_modification</string>
      <int>1</int>
      <string>_parameter_dict</string>
      <dictionary id='i6'>
        <string>full_ip_list</string>
        <list id='i7'/>
        <string>ip_list</string>
        <list id='i8'>
          <tuple>
            <unicode/>
            <unicode>ip_address_1</unicode>
          </tuple>
        </list>
        <unicode>paramé</unicode>
        <unicode>%(param)s</unicode>
        <string>slap_computer_id</string>
        <unicode>%(computer_id)s</unicode>
        <string>slap_computer_partition_id</string>
        <unicode>partition1</unicode>
        <string>slap_software_release_url</string>
        <unicode>%(software_release_url)s</unicode>
        <string>slap_software_type</string>
        <unicode>%(software_type)s</unicode>
        <string>slave_instance_list</string>
        <list id='i9'/>
        <string>timestamp</string>
        <string>%(timestamp)s</string>
      </dictionary>
      <string>_partition_id</string>
      <unicode>partition1</unicode>
      <string>_request_dict</string>
      <none/>
      <string>_requested_state</string>
      <string>started</string>
      <string>_software_release_document</string>
      <object id='i10' module='slapos.slap.slap' class='SoftwareRelease'>
        <tuple>
          <unicode>%(software_release_url)s</unicode>
          <unicode>%(computer_id)s</unicode>
        </tuple>
        <dictionary id='i11'>
          <string>_computer_guid</string>
          <unicode>%(computer_id)s</unicode>
          <string>_software_instance_list</string>
          <list id='i12'/>
          <string>_software_release</string>
          <unicode>%(software_release_url)s</unicode>
        </dictionary>
      </object>
      <string>_synced</string>
      <bool>1</bool>
    </dictionary>
  </object>
</marshal>
""" % dict(
  computer_id=self.computer_id,
  param=self.start_requested_software_instance.getInstanceXmlAsDict()['paramé'],
  sla=self.start_requested_software_instance.getSlaXmlAsDict()['paramé'],
  software_release_url=self.start_requested_software_instance.getUrlString(),
  timestamp=int(self.start_requested_software_instance.getModificationDate()),
  instance_guid=self.start_requested_software_instance.getReference(),
  software_type=self.start_requested_software_instance.getSourceReference()
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def assertInstanceBangSimulator(self, args, kwargs):
    stored = eval(open(self.instance_bang_simulator).read())
    # do the same translation magic as in workflow
    kwargs['comment'] = kwargs.pop('comment')
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'bang'}])

  def test_softwareInstanceBang(self):
    self._makeComplexComputer(person=self.person)
    self.instance_bang_simulator = tempfile.mkstemp()[1]
    try:
      partition_id = self.start_requested_software_instance.getAggregateValue(
          portal_type='Computer Partition').getReference()
      self.login(self.person_reference)
      self.start_requested_software_instance.bang = Simulator(
        self.instance_bang_simulator, 'bang')
      error_log = 'Please bang me'
      response = self.portal_slap.softwareInstanceBang(self.computer_id,
        partition_id, error_log)
      self.assertEqual('OK', response)
      created_at = rfc1123_date(DateTime())
      response = self.portal_slap.getComputerPartitionStatus(self.computer_id,
        partition_id)
      # check returned XML
      xml_fp = StringIO.StringIO()

      xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response.body),
          stream=xml_fp)
      xml_fp.seek(0)
      got_xml = xml_fp.read()
      expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <unicode>created_at</unicode>
    <unicode>%(created_at)s</unicode>
    <unicode>text</unicode>
    <unicode>#error bang called</unicode>
    <unicode>user</unicode>
    <unicode>%(person_reference)s</unicode>
  </dictionary>
</marshal>
""" % dict(
    created_at=created_at,
    person_reference=self.person_reference,
  )
      self.assertEqual(expected_xml, got_xml,
          '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))
      self.assertInstanceBangSimulator((), {'comment': error_log, 'bang_tree': True})
    finally:
      if os.path.exists(self.instance_bang_simulator):
        os.unlink(self.instance_bang_simulator)
      
  def assertInstanceRenameSimulator(self, args, kwargs):
    stored = eval(open(self.instance_rename_simulator).read())
    # do the same translation magic as in workflow
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'rename'}])

  def test_softwareInstanceRename(self):
    self._makeComplexComputer(person=self.person)
    self.instance_rename_simulator = tempfile.mkstemp()[1]
    try:
      partition_id = self.start_requested_software_instance.getAggregateValue(
          portal_type='Computer Partition').getReference()
      self.login(self.person_reference)
      self.start_requested_software_instance.rename = Simulator(
        self.instance_rename_simulator, 'rename')
      new_name = 'new me'
      response = self.portal_slap.softwareInstanceRename(new_name, self.computer_id,
        partition_id)
      self.assertEqual('None', response)
      self.assertInstanceRenameSimulator((), {
          'comment': 'Rename %s into %s' % (self.start_requested_software_instance.getTitle(),
            new_name), 'new_name': new_name})
    finally:
      if os.path.exists(self.instance_rename_simulator):
        os.unlink(self.instance_rename_simulator)

  def assertInstanceRequestSimulator(self, args, kwargs):
    stored = eval(open(self.instance_request_simulator).read())
    # do the same translation magic as in workflow
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'requestSoftwareInstance'}])

  def test_request_withSlave(self):
    self.instance_request_simulator = tempfile.mkstemp()[1]
    try:
      self.login(self.person_reference)
      self.person.requestSoftwareInstance = Simulator(
        self.instance_request_simulator, 'requestSoftwareInstance')
      response = self.portal_slap.requestComputerPartition(
          software_release='req_release',
          software_type='req_type',
          partition_reference='req_reference',
          partition_parameter_xml='<marshal><dictionary id="i2"/></marshal>',
          filter_xml='<marshal><dictionary id="i2"/></marshal>',
          state='<marshal><string>started</string></marshal>',
          shared_xml='<marshal><bool>1</bool></marshal>',
          )
      self.assertEqual(408, response.status)
      self.assertEqual('private',
          response.headers.get('cache-control'))
      self.assertInstanceRequestSimulator((), {
          'instance_xml': "<?xml version='1.0' encoding='utf-8'?>\n<instance/>\n",
          'software_title': 'req_reference',
          'software_release': 'req_release',
          'state': 'started',
          'sla_xml': "<?xml version='1.0' encoding='utf-8'?>\n<instance/>\n",
          'software_type': 'req_type',
          'shared': True})
    finally:
      if os.path.exists(self.instance_request_simulator):
        os.unlink(self.instance_request_simulator)

  def test_request(self):
    self.instance_request_simulator = tempfile.mkstemp()[1]
    try:
      self.login(self.person_reference)
      self.person.requestSoftwareInstance = Simulator(
        self.instance_request_simulator, 'requestSoftwareInstance')
      response = self.portal_slap.requestComputerPartition(
          software_release='req_release',
          software_type='req_type',
          partition_reference='req_reference',
          partition_parameter_xml='<marshal><dictionary id="i2"/></marshal>',
          filter_xml='<marshal><dictionary id="i2"/></marshal>',
          state='<marshal><string>started</string></marshal>',
          shared_xml='<marshal><bool>0</bool></marshal>',
          )
      self.assertEqual(408, response.status)
      self.assertEqual('private',
          response.headers.get('cache-control'))
      self.assertInstanceRequestSimulator((), {
          'instance_xml': "<?xml version='1.0' encoding='utf-8'?>\n<instance/>\n",
          'software_title': 'req_reference',
          'software_release': 'req_release',
          'state': 'started',
          'sla_xml': "<?xml version='1.0' encoding='utf-8'?>\n<instance/>\n",
          'software_type': 'req_type',
          'shared': False})
    finally:
      if os.path.exists(self.instance_request_simulator):
        os.unlink(self.instance_request_simulator)

  def test_request_allocated_instance(self):
    self.tic()
    self.person.edit(
      default_email_coordinate_text="%s@example.org" % self.person.getReference(),
      career_role='member',
    )
    self._makeComplexComputer(person=self.person)
    self.start_requested_software_instance.updateLocalRolesOnSecurityGroups()
    self.tic()
    self.login(self.person_reference)
    response = self.portal_slap.requestComputerPartition(
      software_release=self.start_requested_software_instance.getUrlString(),
      software_type=self.start_requested_software_instance.getSourceReference(),
      partition_reference=self.start_requested_software_instance.getTitle(),
      partition_parameter_xml='<marshal><dictionary id="i2"/></marshal>',
      filter_xml='<marshal><dictionary id="i2"/></marshal>',
      state='<marshal><string>started</string></marshal>',
      shared_xml='<marshal><bool>0</bool></marshal>',
      )
    self.assertEqual(type(response), str)
    # check returned XML
    xml_fp = StringIO.StringIO()

    xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response),
        stream=xml_fp)
    xml_fp.seek(0)
    got_xml = xml_fp.read()
    expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <object id='i2' module='slapos.slap.slap' class='SoftwareInstance'>
    <tuple/>
    <dictionary id='i3'>
      <string>_connection_dict</string>
      <dictionary id='i4'/>
      <string>_filter_dict</string>
      <dictionary id='i5'/>
      <string>_instance_guid</string>
      <unicode>%(instance_guid)s</unicode>
      <string>_parameter_dict</string>
      <dictionary id='i6'/>
      <string>_requested_state</string>
      <string>%(state)s</string>
      <string>full_ip_list</string>
      <list id='i7'/>
      <string>ip_list</string>
      <list id='i8'>
        <tuple>
          <unicode/>
          <unicode>%(ip)s</unicode>
        </tuple>
      </list>
      <string>slap_computer_id</string>
      <unicode>%(computer_id)s</unicode>
      <string>slap_computer_partition_id</string>
      <unicode>%(partition_id)s</unicode>
      <string>slap_software_release_url</string>
      <unicode>%(url_string)s</unicode>
      <string>slap_software_type</string>
      <unicode>%(type)s</unicode>
      <string>slave_instance_list</string>
      <list id='i9'/>
      <string>timestamp</string>
      <string>%(timestamp)s</string>
    </dictionary>
  </object>
</marshal>
""" % dict(
    instance_guid=self.start_requested_software_instance.getReference(),
    state="started",
    url_string=self.start_requested_software_instance.getUrlString(),
    type=self.start_requested_software_instance.getSourceReference(),
    timestamp=int(self.start_requested_software_instance.getModificationDate()),
    computer_id=self.computer_id,
    partition_id=self.start_requested_software_instance.getAggregateId(),
    ip=self.start_requested_software_instance.getAggregateValue()\
               .getDefaultNetworkAddressIpAddress(),
  )
    self.assertEqual(expected_xml, got_xml,
      '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'),
                                                 got_xml.split('\n'))]))

  def assertSupplySimulator(self, args, kwargs):
    stored = eval(open(self.computer_supply_simulator).read())
    # do the same translation magic as in workflow
    kwargs['software_release_url'] = kwargs.pop('software_release_url')
    kwargs['state'] = kwargs.pop('state')
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'requestSoftwareRelease'}])

  def test_computerSupply(self):
    self.computer_supply_simulator = tempfile.mkstemp()[1]
    try:
      self.login(self.person_reference)
      self.computer.requestSoftwareRelease = Simulator(
        self.computer_supply_simulator, 'requestSoftwareRelease')
      software_url = 'live_test_url_%s' % self.generateNewId()
      response = self.portal_slap.supplySupply(
          software_url,
          self.computer_id,
          state='destroyed')
      self.assertEqual('None', response)
      self.assertSupplySimulator((), {
        'software_release_url': software_url,
        'state': 'destroyed'})
    finally:
      if os.path.exists(self.computer_supply_simulator):
        os.unlink(self.computer_supply_simulator)

  def assertRequestComputerSimulator(self, args, kwargs):
    stored = eval(open(self.computer_request_computer_simulator).read())
    # do the same translation magic as in workflow
    kwargs['computer_title'] = kwargs.pop('computer_title')
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'requestComputer'}])

  def test_requestComputer(self):
    self.computer_request_computer_simulator = tempfile.mkstemp()[1]
    try:
      self.login(self.person_reference)
      self.person.requestComputer = Simulator(
        self.computer_request_computer_simulator, 'requestComputer')

      computer_id = 'Foo Computer'
      computer_reference = 'live_comp_%s' % self.generateNewId()
      self.portal.REQUEST.set('computer_reference', computer_reference)
      response = self.portal_slap.requestComputer(computer_id)

      # check returned XML
      xml_fp = StringIO.StringIO()

      xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response),
          stream=xml_fp)
      xml_fp.seek(0)
      got_xml = xml_fp.read()
      expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <object id='i2' module='slapos.slap.slap' class='Computer'>
    <tuple>
      <unicode>%(computer_id)s</unicode>
    </tuple>
    <dictionary id='i3'>
      <string>_computer_id</string>
      <unicode>%(computer_id)s</unicode>
    </dictionary>
  </object>
</marshal>
""" % {'computer_id': computer_reference}

      self.assertEqual(expected_xml, got_xml,
          '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))
      self.assertRequestComputerSimulator((), {'computer_title': computer_id})
    finally:
      if os.path.exists(self.computer_request_computer_simulator):
        os.unlink(self.computer_request_computer_simulator)

  def assertGenerateComputerCertificateSimulator(self, args, kwargs):
    stored = eval(open(self.generate_computer_certificate_simulator).read())
    # do the same translation magic as in workflow
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'generateComputerCertificate'}])

  def test_generateComputerCertificate(self):
    self.generate_computer_certificate_simulator = tempfile.mkstemp()[1]
    try:
      self.login(self.person_reference)
      self.computer.generateCertificate = Simulator(
        self.generate_computer_certificate_simulator, 
        'generateComputerCertificate')

      computer_certificate = 'live_\ncertificate_%s' % self.generateNewId()
      computer_key = 'live_\nkey_%s' % self.generateNewId()
      self.portal.REQUEST.set('computer_certificate', computer_certificate)
      self.portal.REQUEST.set('computer_key', computer_key)
      response = self.portal_slap.generateComputerCertificate(self.computer_id)

      # check returned XML
      xml_fp = StringIO.StringIO()

      xml.dom.ext.PrettyPrint(xml.dom.ext.reader.Sax.FromXml(response),
          stream=xml_fp)
      xml_fp.seek(0)
      got_xml = xml_fp.read()
      expected_xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <dictionary id='i2'>
    <string>certificate</string>
    <unicode>%(computer_certificate)s</unicode>
    <string>key</string>
    <unicode>%(computer_key)s</unicode>
  </dictionary>
</marshal>
""" % {'computer_key': computer_key, 'computer_certificate': computer_certificate}

      self.assertEqual(expected_xml, got_xml,
          '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))
      self.assertGenerateComputerCertificateSimulator((), {})
    finally:
      if os.path.exists(self.generate_computer_certificate_simulator):
        os.unlink(self.generate_computer_certificate_simulator)

  def assertRevokeComputerCertificateSimulator(self, args, kwargs):
    stored = eval(open(self.revoke_computer_certificate_simulator).read())
    # do the same translation magic as in workflow
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'revokeComputerCertificate'}])

  def test_revokeComputerCertificate(self):
    self.revoke_computer_certificate_simulator = tempfile.mkstemp()[1]
    try:
      self.login(self.person_reference)
      self.computer.revokeCertificate = Simulator(
        self.revoke_computer_certificate_simulator, 
        'revokeComputerCertificate')

      response = self.portal_slap.revokeComputerCertificate(self.computer_id)
      self.assertEqual('None', response)
      self.assertRevokeComputerCertificateSimulator((), {})
    finally:
      if os.path.exists(self.revoke_computer_certificate_simulator):
        os.unlink(self.revoke_computer_certificate_simulator)

  def test_getHateoasUrl_NotConfigured(self):
    for preference in \
      self.portal.portal_catalog(portal_type="System Preference"):
      preference = preference.getObject()
      if preference.getPreferenceState() == 'global':
        preference.setPreferredHateoasUrl('')
    self.tic()
    self.login(self.person_reference)
    self.assertRaises(NotFound, self.portal_slap.getHateoasUrl)

  def test_getHateoasUrl(self):
    for preference in \
      self.portal.portal_catalog(portal_type="System Preference"):
      preference = preference.getObject()
      if preference.getPreferenceState() == 'global':
        preference.setPreferredHateoasUrl('foo')
    self.tic()
    self.login(self.person_reference)
    response = self.portal_slap.getHateoasUrl()
    self.assertEqual(200, response.status)
    self.assertEqual('foo', response.body)
