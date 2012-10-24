# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
    testSlapOSMixin
import transaction
from Products.ERP5Type.Base import WorkflowMethod

from DateTime import DateTime
from App.Common import rfc1123_date

# blurb to make nice XML comparisions
import xml.dom.ext.reader.Sax
import xml.dom.ext
import StringIO
import difflib

class TestSlapOSSlapToolComputerAccess(testSlapOSMixin):

  def generateNewId(self):
    return self.portal.portal_ids.generateNewId(
        id_group=('slapos_core_test'))

  def generateNewSoftwareReleaseUrl(self):
    return 'http://example.org/test%s.cfg' % self.generateNewId()

  def generateNewSoftwareType(self):
    return 'Type%s' % self.generateNewId()

  def generateNewSoftwareTitle(self):
    return 'Title%s' % self.generateNewId()

  def generateSafeXml(self):
    return '<?xml version="1.0" encoding="utf-8"?><instance><parameter '\
      'id="param">%s</parameter></instance>' % self.generateNewId()

  def afterSetUp(self):
    self.portal_slap = self.portal.portal_slap
    new_id = self.generateNewId()

    # Prepare computer
    self.computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    self.computer.edit(
      title="Computer %s" % new_id,
      reference="TESTCOMP-%s" % new_id
    )

    self.computer.updateLocalRolesOnSecurityGroups()
    self.computer.validate()

    self.tic()

    self.computer_id = self.computer.getReference()
    self.login(self.computer_id)

  def beforeTearDown(self):
    pass

  def _makeComplexComputer(self):
    @WorkflowMethod.disable
    def setupSoftwareInstance(instance, **kw):
      instance.edit(**kw)

    for i in range(1, 5):
      id_ = 'partition%s' % i
      p = self.computer.newContent(portal_type='Computer Partition',
        id=id_,
        title=id_,
        reference=id_,
        default_network_address_ip_address='ip_address_%s' % i,
        default_network_address_netmask='netmask_%s' % i)
      p.markFree()
      p.validate()

    self.start_requested_software_installation = self.portal.software_installation_module\
        .template_software_installation.Base_createCloneDocument(batch_mode=1)
    self.start_requested_software_installation.edit(
        url_string=self.generateNewSoftwareReleaseUrl(),
        aggregate=self.computer.getRelativeUrl(),
        reference='TESTSOFTINST-%s' % self.generateNewId(),
        title='Start requested for %s' % self.computer.getTitle()
    )
    self.start_requested_software_installation.validate()
    self.start_requested_software_installation.requestStart()

    self.destroy_requested_software_installation = self.portal.software_installation_module\
        .template_software_installation.Base_createCloneDocument(batch_mode=1)
    self.destroy_requested_software_installation.edit(
        url_string=self.generateNewSoftwareReleaseUrl(),
        aggregate=self.computer.getRelativeUrl(),
        reference='TESTSOFTINST-%s' % self.generateNewId(),
        title='Destroy requested for %s' % self.computer.getTitle()
    )
    self.destroy_requested_software_installation.validate()
    self.destroy_requested_software_installation.requestStart()
    self.destroy_requested_software_installation.requestDestroy()

    self.destroyed_software_installation = self.portal.software_installation_module\
        .template_software_installation.Base_createCloneDocument(batch_mode=1)
    self.destroyed_software_installation.edit(
        url_string=self.generateNewSoftwareReleaseUrl(),
        aggregate=self.computer.getRelativeUrl(),
        reference='TESTSOFTINST-%s' % self.generateNewId(),
        title='Destroyed for %s' % self.computer.getTitle()
    )
    self.destroyed_software_installation.validate()
    self.destroyed_software_installation.requestStart()
    self.destroyed_software_installation.requestDestroy()
    self.destroyed_software_installation.invalidate()

    self.computer.partition1.markBusy()
    self.computer.partition2.markBusy()
    self.computer.partition3.markBusy()

    self.start_requested_software_instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    setupSoftwareInstance(self.start_requested_software_instance, **dict(
        title=self.generateNewSoftwareTitle(),
        reference="TESTSI-%s" % self.generateNewId(),
        root_software_release_url=\
          self.start_requested_software_installation.getUrlString(),
        source_reference=self.generateNewSoftwareType(),
        text_content=self.generateSafeXml(),
        sla_xml=self.generateSafeXml(),
        aggregate=self.computer.partition1.getRelativeUrl()
    ))
    self.portal.portal_workflow._jumpToStateFor(
        self.start_requested_software_instance, 'start_requested')
    self.start_requested_software_instance.validate()
    self.start_requested_software_instance.updateLocalRolesOnSecurityGroups()

    self.stop_requested_software_instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    setupSoftwareInstance(self.stop_requested_software_instance, **dict(
        title=self.generateNewSoftwareTitle(),
        reference="TESTSI-%s" % self.generateNewId(),
        root_software_release_url=\
          self.start_requested_software_installation.getUrlString(),
        source_reference=self.generateNewSoftwareType(),
        text_content=self.generateSafeXml(),
        sla_xml=self.generateSafeXml(),
        aggregate=self.computer.partition2.getRelativeUrl()
    ))
    self.portal.portal_workflow._jumpToStateFor(
        self.stop_requested_software_instance, 'stop_requested')
    self.stop_requested_software_instance.validate()
    self.stop_requested_software_instance.updateLocalRolesOnSecurityGroups()

    self.destroy_requested_software_instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    setupSoftwareInstance(self.destroy_requested_software_instance, **dict(
        title=self.generateNewSoftwareTitle(),
        reference="TESTSI-%s" % self.generateNewId(),
        root_software_release_url=\
          self.start_requested_software_installation.getUrlString(),
        source_reference=self.generateNewSoftwareType(),
        text_content=self.generateSafeXml(),
        sla_xml=self.generateSafeXml(),
        aggregate=self.computer.partition3.getRelativeUrl()
    ))
    self.portal.portal_workflow._jumpToStateFor(
        self.destroy_requested_software_instance, 'destroy_requested')
    self.destroy_requested_software_instance.validate()
    self.destroy_requested_software_instance.updateLocalRolesOnSecurityGroups()

    self.destroyed_software_instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    setupSoftwareInstance(self.destroyed_software_instance, **dict(
        title=self.generateNewSoftwareTitle(),
        reference="TESTSI-%s" % self.generateNewId(),
        root_software_release_url=\
          self.start_requested_software_installation.getUrlString(),
        source_reference=self.generateNewSoftwareType(),
        text_content=self.generateSafeXml(),
        sla_xml=self.generateSafeXml(),
        aggregate=self.computer.partition4.getRelativeUrl()
    ))
    self.portal.portal_workflow._jumpToStateFor(
        self.destroyed_software_instance, 'destroy_requested')
    self.destroyed_software_instance.validate()
    self.destroyed_software_instance.invalidate()
    self.destroyed_software_instance.updateLocalRolesOnSecurityGroups()

    self.tic()

  def _getPartitionXml(self):
    return """\
<?xml version='1.0' encoding='UTF-8'?>
<marshal>
  <object id='i2' module='slapos.slap.slap' class='Computer'>
    <tuple>
      <string>%(computer_id)s</string>
    </tuple>
    <dictionary id='i3'>
      <string>_computer_id</string>
      <string>%(computer_id)s</string>
      <string>_computer_partition_list</string>
      <list id='i4'>
        <object id='i5' module='slapos.slap.slap' class='ComputerPartition'>
          <tuple>
            <string>%(computer_id)s</string>
            <string>partition4</string>
          </tuple>
          <dictionary id='i6'>
            <string>_computer_id</string>
            <string>%(computer_id)s</string>
            <string>_need_modification</string>
            <int>0</int>
            <string>_partition_id</string>
            <string>partition4</string>
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
            <string>%(computer_id)s</string>
            <string>partition3</string>
          </tuple>
          <dictionary id='i8'>
            <string>_computer_id</string>
            <string>%(computer_id)s</string>
            <string>_connection_dict</string>
            <dictionary id='i9'>
              <string>parameter1</string>
              <string>valueof1</string>
              <string>parameter2</string>
              <string>https://niut:pass@example.com:4567/arfarf/oink?m=1#4.5</string>
            </dictionary>
            <string>_instance_guid</string>
            <string>%(partition_3_instance_guid)s</string>
            <string>_need_modification</string>
            <int>1</int>
            <string>_parameter_dict</string>
            <dictionary id='i10'>
              <string>ip_list</string>
              <list id='i11'>
                <tuple>
                  <string/>
                  <string>ip_address_3</string>
                </tuple>
              </list>
              <string>param</string>
              <string>%(partition_3_param)s</string>
              <string>slap_computer_id</string>
              <string>%(computer_id)s</string>
              <string>slap_computer_partition_id</string>
              <string>partition3</string>
              <string>slap_software_release_url</string>
              <string>%(partition_3_software_release_url)s</string>
              <string>slap_software_type</string>
              <string>%(partition_3_instance_software_type)s</string>
              <string>slave_instance_list</string>
              <list id='i12'/>
              <string>timestamp</string>
              <string>%(partition_3_timestamp)s</string>
            </dictionary>
            <string>_partition_id</string>
            <string>partition3</string>
            <string>_request_dict</string>
            <none/>
            <string>_requested_state</string>
            <string>destroyed</string>
            <string>_software_release_document</string>
            <object id='i13' module='slapos.slap.slap' class='SoftwareRelease'>
              <tuple>
                <string>%(partition_3_software_release_url)s</string>
                <string>%(computer_id)s</string>
              </tuple>
              <dictionary id='i14'>
                <string>_computer_guid</string>
                <string>%(computer_id)s</string>
                <string>_software_instance_list</string>
                <list id='i15'/>
                <string>_software_release</string>
                <string>%(partition_3_software_release_url)s</string>
              </dictionary>
            </object>
          </dictionary>
        </object>
        <object id='i16' module='slapos.slap.slap' class='ComputerPartition'>
          <tuple>
            <string>%(computer_id)s</string>
            <string>partition2</string>
          </tuple>
          <dictionary id='i17'>
            <string>_computer_id</string>
            <string>%(computer_id)s</string>
            <string>_connection_dict</string>
            <dictionary id='i18'>
              <string>parameter1</string>
              <string>valueof1</string>
              <string>parameter2</string>
              <string>https://niut:pass@example.com:4567/arfarf/oink?m=1#4.5</string>
            </dictionary>
            <string>_instance_guid</string>
            <string>%(partition_2_instance_guid)s</string>
            <string>_need_modification</string>
            <int>1</int>
            <string>_parameter_dict</string>
            <dictionary id='i19'>
              <string>ip_list</string>
              <list id='i20'>
                <tuple>
                  <string/>
                  <string>ip_address_2</string>
                </tuple>
              </list>
              <string>param</string>
              <string>%(partition_2_param)s</string>
              <string>slap_computer_id</string>
              <string>%(computer_id)s</string>
              <string>slap_computer_partition_id</string>
              <string>partition2</string>
              <string>slap_software_release_url</string>
              <string>%(partition_2_software_release_url)s</string>
              <string>slap_software_type</string>
              <string>%(partition_2_instance_software_type)s</string>
              <string>slave_instance_list</string>
              <list id='i21'/>
              <string>timestamp</string>
              <string>%(partition_2_timestamp)s</string>
            </dictionary>
            <string>_partition_id</string>
            <string>partition2</string>
            <string>_request_dict</string>
            <none/>
            <string>_requested_state</string>
            <string>stopped</string>
            <string>_software_release_document</string>
            <object id='i22' module='slapos.slap.slap' class='SoftwareRelease'>
              <tuple>
                <string>%(partition_2_software_release_url)s</string>
                <string>%(computer_id)s</string>
              </tuple>
              <dictionary id='i23'>
                <string>_computer_guid</string>
                <string>%(computer_id)s</string>
                <string>_software_instance_list</string>
                <list id='i24'/>
                <string>_software_release</string>
                <string>%(partition_2_software_release_url)s</string>
              </dictionary>
            </object>
          </dictionary>
        </object>
        <object id='i25' module='slapos.slap.slap' class='ComputerPartition'>
          <tuple>
            <string>%(computer_id)s</string>
            <string>partition1</string>
          </tuple>
          <dictionary id='i26'>
            <string>_computer_id</string>
            <string>%(computer_id)s</string>
            <string>_connection_dict</string>
            <dictionary id='i27'>
              <string>parameter1</string>
              <string>valueof1</string>
              <string>parameter2</string>
              <string>https://niut:pass@example.com:4567/arfarf/oink?m=1#4.5</string>
            </dictionary>
            <string>_instance_guid</string>
            <string>%(partition_1_instance_guid)s</string>
            <string>_need_modification</string>
            <int>1</int>
            <string>_parameter_dict</string>
            <dictionary id='i28'>
              <string>ip_list</string>
              <list id='i29'>
                <tuple>
                  <string/>
                  <string>ip_address_1</string>
                </tuple>
              </list>
              <string>param</string>
              <string>%(partition_1_param)s</string>
              <string>slap_computer_id</string>
              <string>%(computer_id)s</string>
              <string>slap_computer_partition_id</string>
              <string>partition1</string>
              <string>slap_software_release_url</string>
              <string>%(partition_1_software_release_url)s</string>
              <string>slap_software_type</string>
              <string>%(partition_1_instance_software_type)s</string>
              <string>slave_instance_list</string>
              <list id='i30'/>
              <string>timestamp</string>
              <string>%(partition_1_timestamp)s</string>
            </dictionary>
            <string>_partition_id</string>
            <string>partition1</string>
            <string>_request_dict</string>
            <none/>
            <string>_requested_state</string>
            <string>started</string>
            <string>_software_release_document</string>
            <object id='i31' module='slapos.slap.slap' class='SoftwareRelease'>
              <tuple>
                <string>%(partition_1_software_release_url)s</string>
                <string>%(computer_id)s</string>
              </tuple>
              <dictionary id='i32'>
                <string>_computer_guid</string>
                <string>%(computer_id)s</string>
                <string>_software_instance_list</string>
                <list id='i33'/>
                <string>_software_release</string>
                <string>%(partition_1_software_release_url)s</string>
              </dictionary>
            </object>
          </dictionary>
        </object>
      </list>
""" % dict(
  computer_id=self.computer_id,

  partition_3_instance_guid=self.computer.partition3.getAggregateRelatedValue(portal_type='Software Instance').getReference(),
  partition_3_instance_software_type=self.computer.partition3.getAggregateRelatedValue(portal_type='Software Instance').getSourceReference(),
  partition_3_timestamp=int(self.computer.partition3.getAggregateRelatedValue(portal_type='Software Instance').getModificationDate()),
  partition_3_param=self.computer.partition3.getAggregateRelatedValue(portal_type='Software Instance').getInstanceXmlAsDict()['param'],
  partition_3_software_release_url=self.computer.partition3.getAggregateRelatedValue(portal_type='Software Instance').getRootSoftwareReleaseUrl(),

  partition_2_instance_guid=self.computer.partition2.getAggregateRelatedValue(portal_type='Software Instance').getReference(),
  partition_2_instance_software_type=self.computer.partition2.getAggregateRelatedValue(portal_type='Software Instance').getSourceReference(),
  partition_2_timestamp=int(self.computer.partition2.getAggregateRelatedValue(portal_type='Software Instance').getModificationDate()),
  partition_2_param=self.computer.partition2.getAggregateRelatedValue(portal_type='Software Instance').getInstanceXmlAsDict()['param'],
  partition_2_software_release_url=self.computer.partition2.getAggregateRelatedValue(portal_type='Software Instance').getRootSoftwareReleaseUrl(),

  partition_1_instance_guid=self.computer.partition1.getAggregateRelatedValue(portal_type='Software Instance').getReference(),
  partition_1_instance_software_type=self.computer.partition1.getAggregateRelatedValue(portal_type='Software Instance').getSourceReference(),
  partition_1_timestamp=int(self.computer.partition1.getAggregateRelatedValue(portal_type='Software Instance').getModificationDate()),
  partition_1_param=self.computer.partition1.getAggregateRelatedValue(portal_type='Software Instance').getInstanceXmlAsDict()['param'],
  partition_1_software_release_url=self.computer.partition1.getAggregateRelatedValue(portal_type='Software Instance').getRootSoftwareReleaseUrl(),
  )

  def test_getFullComputerInformation(self):
    self.login()
    self._makeComplexComputer()
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
    expected_xml = self._getPartitionXml() + """\
      <string>_software_release_list</string>
      <list id='i34'>
        <object id='i35' module='slapos.slap.slap' class='SoftwareRelease'>
          <tuple>
            <string>%(destroy_requested_url)s</string>
            <string>%(computer_id)s</string>
          </tuple>
          <dictionary id='i36'>
            <string>_computer_guid</string>
            <string>%(computer_id)s</string>
            <string>_requested_state</string>
            <string>destroyed</string>
            <string>_software_instance_list</string>
            <list id='i37'/>
            <string>_software_release</string>
            <string>%(destroy_requested_url)s</string>
          </dictionary>
        </object>
        <object id='i38' module='slapos.slap.slap' class='SoftwareRelease'>
          <tuple>
            <string>%(start_requested_url)s</string>
            <string>%(computer_id)s</string>
          </tuple>
          <dictionary id='i39'>
            <string>_computer_guid</string>
            <string>%(computer_id)s</string>
            <string>_requested_state</string>
            <string>available</string>
            <string>_software_instance_list</string>
            <list id='i40'/>
            <string>_software_release</string>
            <string>%(start_requested_url)s</string>
          </dictionary>
        </object>
      </list>
    </dictionary>
  </object>
</marshal>
""" % dict(
  computer_id=self.computer_id,

  destroy_requested_url=self.destroy_requested_software_installation.getUrlString(),
  start_requested_url=self.start_requested_software_installation.getUrlString()
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_getComputerInformation(self):
    self.assertEqual('getFullComputerInformation',
      self.portal_slap.getComputerInformation.im_func.func_name)

  def test_not_accessed_getComputerStatus(self):
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
    <string>#error no data found for %(computer_id)s</string>
    <string>user</string>
    <string>%(computer_id)s</string>
  </dictionary>
</marshal>
""" % dict(
  created_at=created_at,
  computer_id=self.computer_id
)
    self.assertEqual(expected_xml, got_xml,
        '\n'.join([q for q in difflib.unified_diff(expected_xml.split('\n'), got_xml.split('\n'))]))

  def test_accessed_getComputerStatus(self):
    self.portal_slap.getComputerInformation(self.computer_id)
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
