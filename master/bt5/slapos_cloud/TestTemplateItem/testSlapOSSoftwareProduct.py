# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import testSlapOSMixin
from AccessControl import getSecurityManager
from DateTime import DateTime
import transaction

class BaseTestSlapOSMixin(testSlapOSMixin):
  
  def afterSetUp(self):
    super(BaseTestSlapOSMixin, self).afterSetUp()
    self.request_kw = dict(
        software_title=self.generateNewSoftwareTitle(),
        software_type=self.generateNewSoftwareType(),
        instance_xml=self.generateSafeXml(),
        sla_xml=self.generateEmptyXml(),
        shared=False,
        state="started"
    )
    
  def _makePerson(self, new_id):
    # Clone computer document
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    person.edit(
      title="live_test_%s" % new_id,
      reference='TESTPERSON-%s' % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )
    
    person.validate()
    for assignment in person.contentValues(portal_type="Assignment"):
      assignment.open()
    transaction.commit()
    
    return person

  def _makeComputer(self,new_id):
    # Clone computer document
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    computer = self.portal.computer_module\
      .template_computer.Base_createCloneDocument(batch_mode=1)
    computer.edit(
      title="computer ticket %s" % (new_id, ),
      reference="TESTCOMPT-%s" % (new_id, ),
      source_administration_value=person
    )
    computer.validate()

    return computer

  def _makeComputerPartitions(self, computer):
    for i in range(1, 5):
      id_ = 'partition%s' % (i, )
      p = computer.newContent(portal_type='Computer Partition',
        id=id_,
        title=id_,
        reference=id_,
        default_network_address_ip_address='ip_address_%s' % i,
        default_network_address_netmask='netmask_%s' % i)
      p.markFree()
      p.validate
  
  def _markComputerPartitionBusy(self, computer, software_instance):
    for partition in computer.contentValues(portal_type='Computer Partition'):
      if partition.getSlapState() == 'free':
        software_instance.edit(aggregate=partition.getRelativeUrl())
        break;

  def _makeSoftwareInstallation(self, new_id, computer, software_release_url):
     software_installation = self.portal\
       .software_installation_module.template_software_installation\
       .Base_createCloneDocument(batch_mode=1)
     software_installation.edit(
       url_string=software_release_url,
       aggregate=computer.getRelativeUrl(),
       reference='TESTSOFTINSTS-%s' % new_id,
       title='Start requested for %s' % computer.getUid()
     )
     software_installation.validate()
     software_installation.requestStart()

     return software_installation

  def _makeHostingSubscription(self, new_id, software_url="", person=None):
    if not person:
      person = self._makePerson(new_id)
    
    hosting_subscription = self.portal\
      .hosting_subscription_module.template_hosting_subscription\
      .Base_createCloneDocument(batch_mode=1)
    hosting_subscription.edit(
        title=self.request_kw['software_title'],
        reference="TESTHS-%s" % new_id,
        url_string=software_url,
        source_reference=self.request_kw['software_type'],
        text_content=self.request_kw['instance_xml'],
        sla_xml=self.request_kw['sla_xml'],
        root_slave=self.request_kw['shared'],
        destination_section=person.getRelativeUrl()
    )
    hosting_subscription.validate()
    self.portal.portal_workflow._jumpToStateFor(hosting_subscription, 'start_requested')

    return hosting_subscription

  def _makeSoftwareInstance(self, hosting_subscription, software_url):
    
    software_instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    software_instance.edit(
        title=self.request_kw['software_title'],
        reference="TESTSI-%s" % self.generateNewId(),
        url_string=software_url,
        source_reference=self.request_kw['software_type'],
        text_content=self.request_kw['instance_xml'],
        sla_xml=self.request_kw['sla_xml'],
        specialise=hosting_subscription.getRelativeUrl()
    )
    hosting_subscription.edit(
        predecessor=software_instance.getRelativeUrl()
    )
    self.portal.portal_workflow._jumpToStateFor(software_instance, 'start_requested')
    software_instance.validate()
    
    return software_instance
  

class TestSoftwareReleaseListFromSoftwareProduct(testSlapOSMixin):
  def afterSetUp(self):
    super(TestSoftwareReleaseListFromSoftwareProduct, self).afterSetUp()
    self.user_id = getSecurityManager().getUser().getId()

  def beforeTearDown(self):
    transaction.abort()

  def generateNewId(self):
    return str(self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_core_test')))
  
  def test_getSortedSoftwareReleaseListFromSoftwareProduct(self):
    new_id = self.generateNewId()
    software_product = self._makeSoftwareProduct(new_id)
    release_list = software_product.SoftwareProduct_getSortedSoftwareReleaseList(
      software_product.getReference())
    self.assertEqual(release_list, [])
    
    # published software release
    software_release1 = self._makeSoftwareRelease(new_id)
    software_release1.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/1-%s.cfg' % new_id
    )
    software_release1.publish()
    software_release2 = self._makeSoftwareRelease(self.generateNewId())
    software_release2.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/2-%s.cfg' % new_id
    )
    software_release2.publish()
    # 1 released software release, should not appear
    software_release3 = self._makeSoftwareRelease(new_id)
    self.assertTrue(software_release3.getValidationState() == 'released')
    software_release3.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/3-%s.cfg' % new_id
    )
    self.tic()

    release_list = software_product.SoftwareProduct_getSortedSoftwareReleaseList(
      software_product.getReference())
    self.assertEquals([release.getUrlString() for release in release_list],
      ['http://example.org/2-%s.cfg' % new_id, 'http://example.org/1-%s.cfg' % new_id])
    
    
  def test_getSortedSoftwareReleaseListFromSoftwareProduct_Changed(self):
    new_id = self.generateNewId()
    software_product = self._makeSoftwareProduct(new_id)
    release_list = software_product.SoftwareProduct_getSortedSoftwareReleaseList(
      software_product.getReference())
    self.assertEqual(release_list, [])
    
    # 2 published software releases
    software_release2 = self._makeSoftwareRelease(self.generateNewId())
    software_release2.publish()
    software_release2.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/2-%s.cfg' % new_id
    )
    # Newest software release
    software_release1 = self._makeSoftwareRelease(new_id)
    software_release1.publish()
    software_release1.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/1-%s.cfg' % new_id
    )
    self.tic()

    release_list = software_product.SoftwareProduct_getSortedSoftwareReleaseList(
      software_product.getReference())
    self.assertEquals([release.getUrlString() for release in release_list],
      ['http://example.org/1-%s.cfg' % new_id, 'http://example.org/2-%s.cfg' % new_id])
    release_list = software_product.SoftwareProduct_getSortedSoftwareReleaseList(
      software_release_url='http://example.org/1-%s.cfg' % new_id)
    self.assertEquals([release.getUrlString() for release in release_list],
      ['http://example.org/1-%s.cfg' % new_id, 'http://example.org/2-%s.cfg' % new_id])
  
  
class TestSlapOSUpgradeHostingSubscription(BaseTestSlapOSMixin):
  def afterSetUp(self):
    super(TestSlapOSUpgradeHostingSubscription, self).afterSetUp()
    self.new_id = self.generateNewId()

  def beforeTearDown(self):
    transaction.abort()
  
  def generateNewId(self):
    return str(self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_core_test')))
  
  def _requestSoftwareRelease(self, new_id, software_product_url, software_url):
    software_release = self._makeSoftwareRelease(new_id)
    software_release.edit(
        aggregate_value=software_product_url,
        url_string=software_url
    )
    software_release.publish()
    return software_release
    
  def test_HostingSubscription_getNewerSofwareRelease(self):
    computer = self._makeComputer(self.new_id)
    software_product = self._makeSoftwareProduct(self.new_id)
    oldest_software_url = 'http://example.org/oldest-%s.cfg' % self.new_id
    newest_software_url = 'http://example.org/newest-%s.cfg' % self.new_id
    
    self._requestSoftwareRelease(self.new_id,
                                software_product.getRelativeUrl(),
                                oldest_software_url)
    self._requestSoftwareRelease(self.generateNewId(),
                                software_product.getRelativeUrl(),
                                newest_software_url)
    self._makeSoftwareInstallation(self.new_id, computer, oldest_software_url)
    
    hosting_subscription = self._makeHostingSubscription(self.new_id, oldest_software_url)
    self.tic()
    self.assertEqual(hosting_subscription.HostingSubscription_getNewerSofwareRelease(),
                            "")
    
    self._makeSoftwareInstance(hosting_subscription, oldest_software_url)
    self.tic()
    self.assertEqual(hosting_subscription.HostingSubscription_getNewerSofwareRelease(),
                            newest_software_url)

  def test_HostingSubscription_isUpgradable(self):
    computer = self._makeComputer(self.new_id)
    self._makeComputerPartitions(computer)
    software_product = self._makeSoftwareProduct(self.new_id)
    oldest_software_url = 'http://example.org/oldest-%s.cfg' % self.new_id
    newest_software_url = 'http://example.org/newest-%s.cfg' % self.new_id
    self._requestSoftwareRelease(self.new_id,
                                software_product.getRelativeUrl(),
                                oldest_software_url)
    self._makeSoftwareInstallation(self.new_id, computer, oldest_software_url)
    hosting_subscription = self._makeHostingSubscription(self.new_id, oldest_software_url)
    self.tic()
    self.assertEqual(hosting_subscription.HostingSubscription_isUpgradable(),
                      False)
    
    self._makeSoftwareInstance(hosting_subscription, oldest_software_url)
    self._markComputerPartitionBusy(computer, hosting_subscription.getPredecessorValue())
    self._requestSoftwareRelease(self.generateNewId(),
                                software_product.getRelativeUrl(),
                                newest_software_url)
    self.tic()
    self.assertEqual(hosting_subscription.HostingSubscription_isUpgradable(),
                      False)
    self._makeSoftwareInstallation(self.generateNewId(), computer, newest_software_url)
    self.tic()
    self.assertEqual(hosting_subscription.HostingSubscription_isUpgradable(),
                      True)
    
    self.portal.portal_workflow._jumpToStateFor(hosting_subscription, 'destroy_requested')
    self.assertEqual(hosting_subscription.HostingSubscription_isUpgradable(),
                      False)
    