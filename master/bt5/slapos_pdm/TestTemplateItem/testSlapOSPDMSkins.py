# -*- coding:utf-8 -*-
##############################################################################
#
# Copyright (c) 2002-2013 Nexedi SA and Contributors. All Rights Reserved.
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
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#
##############################################################################

import transaction
from functools import wraps
from Products.SlapOS.tests.testSlapOSMixin import testSlapOSMixin
from Products.ERP5Type.tests.utils import createZODBPythonScript
from DateTime import DateTime

def simulate(script_id, params_string, code_string):
  def upperWrap(f):
    @wraps(f)
    def decorated(self, *args, **kw):
      if script_id in self.portal.portal_skins.custom.objectIds():
        raise ValueError('Precondition failed: %s exists in custom' % script_id)
      createZODBPythonScript(self.portal.portal_skins.custom,
                          script_id, params_string, code_string)
      try:
        result = f(self, *args, **kw)
      finally:
        if script_id in self.portal.portal_skins.custom.objectIds():
          self.portal.portal_skins.custom.manage_delObjects(script_id)
        transaction.commit()
      return result
    return decorated
  return upperWrap

class TestSlapOSPDMSkins(testSlapOSMixin):
  def afterSetUp(self):
    super(TestSlapOSPDMSkins, self).afterSetUp()
    self.new_id = self.generateNewId()
    self.request_kw = dict(
        software_title=self.generateNewSoftwareTitle(),
        software_type=self.generateNewSoftwareType(),
        instance_xml=self.generateSafeXml(),
        sla_xml=self.generateEmptyXml(),
        shared=False,
        state="started"
    )
  
  def beforeTearDown(self):
    id_list = []
    for upgrade_decision in self.portal.portal_catalog(
               portal_type="Upgrade Decision", reference="UD-TEST%"):
      id_list.append(upgrade_decision.getId())
    self.portal.upgrade_decision_module.manage_delObjects(id_list)
    self.tic()

  def generateNewId(self):
     return "%sTEST" % self.portal.portal_ids.generateNewId(
         id_group=('slapos_core_test'))
 

  def _makePerson(self,new_id):
    # Clone person document
    person_user = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    person_user.validate()
    for assignment in person_user.contentValues(portal_type="Assignment"):
      assignment.open()
    transaction.commit()

    return person_user

  def _makeComputer(self,new_id):
    # Clone computer document
    computer = self.portal.computer_module\
      .template_computer.Base_createCloneDocument(batch_mode=1)
    computer.edit(
      title="computer start %s" % (new_id, ),
      reference="TESTCOMPS-%s" % (new_id, )
    )
    computer.validate()

    return computer

  def _makeComputerPartitions(self,computer):
    for i in range(1, 5):
      id_ = 'partition%s' % (i, )
      p = computer.newContent(portal_type='Computer Partition',
        id=id_,
        title=id_,
        reference=id_,
        default_network_address_ip_address='ip_address_%s' % i,
        default_network_address_netmask='netmask_%s' % i)
      p.markFree()
      p.validate()
  
  def _markComputerPartitionBusy(self, computer, software_instance):
    for partition in computer.contentValues(portal_type='Computer Partition'):
      if partition.getSlapState() == 'free':
        software_instance.edit(aggregate=partition.getRelativeUrl())
        partition.markBusy()
        break;
  
  def _makeSoftwareProduct(self, new_id):
    software_product = self.portal.software_product_module\
      .template_software_product.Base_createCloneDocument(batch_mode=1)
    software_product.edit(
      reference='TESTSOFTPROD-%s' % new_id,
      title='Test software product %s' % new_id
    )
    software_product.validate()
    software_product.publish()

    return software_product

  def _makeSoftwareRelease(self, new_id):
    software_release = self.portal.software_release_module\
      .template_software_release.Base_createCloneDocument(batch_mode=1)
    software_release.edit(
      url_string=self.generateNewSoftwareReleaseUrl(),
      reference='TESTSOFTRELS-%s' % new_id,
      title='Start requested for %s' % new_id
    )
    software_release.release()

    return software_release
  
  def _requestSoftwareRelease(self, new_id, software_product_url, effective_date=None):
    software_release = self._makeSoftwareRelease(new_id)
    if not effective_date:
      effective_date = DateTime()
    software_release.edit(
        aggregate_value=software_product_url,
        effective_date=effective_date
    )
    software_release.publish()
    return software_release
  
  def _makeCustomSoftwareRelease(self, new_id, software_product_url, software_url):
      software_release = self._makeSoftwareRelease(new_id)
      software_release.edit(
          aggregate_value=software_product_url,
          url_string=software_url
      )
      software_release.publish()
      return software_release

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

  def _makeHostingSubscription(self, new_id):
    hosting_subscription = self.portal\
      .hosting_subscription_module.template_hosting_subscription\
      .Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    hosting_subscription.edit(
        title= "Test hosting sub start %s" % new_id,
        reference="TESTHSS-%s" % new_id,
    )

    return hosting_subscription

  def _makeSoftwareInstance(self, hosting_subscription, software_url):

    kw = dict(
      software_release=software_url,
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='started'
    )
    hosting_subscription.requestStart(**kw)
    hosting_subscription.requestInstance(**kw)
    
  def _makeFullHostingSubscription(self, new_id, software_url="", person=None):
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

  def _makeFullSoftwareInstance(self, hosting_subscription, software_url):
    
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

  def _makeUpgradeDecision(self):
    return self.portal.\
       upgrade_decision_module.newContent(
         portal_type="Upgrade Decision",
         title="TESTUPDE-%s" % self.new_id)
  
  def _makeUpgradeDecisionLine(self, upgrade_decision):
    return upgrade_decision.newContent(
         portal_type="Upgrade Decision Line",
         title="TESTUPDE-%s" % self.new_id)
  
  
  def test_getSortedSoftwareReleaseListFromSoftwareProduct(self):
    new_id = self.generateNewId()
    software_product = self._makeSoftwareProduct(new_id)
    release_list = software_product.SoftwareProduct_getSortedSoftwareReleaseList(
      software_product.getReference())
    self.assertEqual(release_list, [])
    
    # published software release
    software_release1 = self._makeSoftwareRelease(new_id)
    software_release1.edit(aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/1-%s.cfg' % new_id,
        effective_date=(DateTime() + 5)
    )
    software_release1.publish()
    software_release2 = self._makeSoftwareRelease(self.generateNewId())
    software_release2.edit(aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/2-%s.cfg' % new_id
    )
    software_release2.publish()
    # 1 released software release, should not appear
    software_release3 = self._makeSoftwareRelease(new_id)
    self.assertTrue(software_release3.getValidationState() == 'released')
    software_release3.edit(aggregate_value=software_product.getRelativeUrl(),
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
    software_release2.edit(aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/2-%s.cfg' % new_id,
        effective_date=(DateTime() - 2)
    )
    # Newest software release
    software_release1 = self._makeSoftwareRelease(new_id)
    software_release1.publish()
    software_release1.edit(aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/1-%s.cfg' % new_id,
        effective_date=DateTime()
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
  
  
  def test_HostingSubscription_getNewerSofwareRelease(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(source_administration_value=person)
    software_product = self._makeSoftwareProduct(self.new_id)
    oldest_software_url = 'http://example.org/oldest-%s.cfg' % self.new_id
    newest_software_url = 'http://example.org/newest-%s.cfg' % self.new_id
    
    self._makeCustomSoftwareRelease(self.new_id,
                                software_product.getRelativeUrl(),
                                oldest_software_url)
    self._makeCustomSoftwareRelease(self.generateNewId(),
                                software_product.getRelativeUrl(),
                                newest_software_url)
    self._makeSoftwareInstallation(self.new_id, computer, oldest_software_url)
    
    hosting_subscription = self._makeFullHostingSubscription(self.new_id,
                                    oldest_software_url, person)
    self.tic()
    self.assertEqual(hosting_subscription.HostingSubscription_getNewerSofwareRelease(),
                            None)
    
    self._makeFullSoftwareInstance(hosting_subscription, oldest_software_url)
    self.tic()
    release = hosting_subscription.HostingSubscription_getNewerSofwareRelease()
    self.assertEqual(release.getUrlString(), newest_software_url)

  def testHostingSubscription_getUpgradableSoftwareRelease_no_installation(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(source_administration_value=person)
    self._makeComputerPartitions(computer)
    software_product = self._makeSoftwareProduct(self.new_id)
    oldest_software_url = 'http://example.org/oldest-%s.cfg' % self.new_id
    newest_software_url = 'http://example.org/newest-%s.cfg' % self.new_id
    self._makeCustomSoftwareRelease(self.new_id,
                                software_product.getRelativeUrl(),
                                oldest_software_url)
    self._makeSoftwareInstallation(self.new_id, computer, oldest_software_url)
    hs = self._makeFullHostingSubscription(self.new_id,
                                    oldest_software_url, person)
    self.tic()
    self.assertEqual(hs.HostingSubscription_getUpgradableSoftwareRelease(),
                      None)
    
    self._makeFullSoftwareInstance(hs, oldest_software_url)
    self._markComputerPartitionBusy(computer, hs.getPredecessorValue())
    self._makeCustomSoftwareRelease(self.generateNewId(),
                                software_product.getRelativeUrl(),
                                newest_software_url)
    self.tic()
    self.assertEqual(hs.HostingSubscription_getUpgradableSoftwareRelease(),
                      None)
  
  def testHostingSubscription_getUpgradableSoftwareRelease(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(source_administration_value=person)
    self._makeComputerPartitions(computer)
    software_product = self._makeSoftwareProduct(self.new_id)
    oldest_software_url = 'http://example.org/oldest-%s.cfg' % self.new_id
    newest_software_url = 'http://example.org/newest-%s.cfg' % self.new_id
    self._makeCustomSoftwareRelease(self.new_id,
                                software_product.getRelativeUrl(),
                                oldest_software_url)
    self._makeSoftwareInstallation(self.new_id, computer, oldest_software_url)
    hs = self._makeFullHostingSubscription(self.new_id,
                                    oldest_software_url, person)
    
    self._makeFullSoftwareInstance(hs, oldest_software_url)
    self._markComputerPartitionBusy(computer, hs.getPredecessorValue())
    self._makeCustomSoftwareRelease(self.generateNewId(),
                                software_product.getRelativeUrl(),
                                newest_software_url)
    self._makeSoftwareInstallation(self.generateNewId(), computer,
                                    newest_software_url)
    # software_release should be ignored!
    software_release = self._makeSoftwareRelease(self.generateNewId())
    self._makeSoftwareInstallation(self.generateNewId(),
                              computer, software_release.getUrlString())
    self.tic()
    release = hs.HostingSubscription_getUpgradableSoftwareRelease()
    self.assertEqual(release.getUrlString(), newest_software_url)
    
    self.portal.portal_workflow._jumpToStateFor(hs, 'destroy_requested')
    self.tic()
    self.assertEqual(hs.HostingSubscription_getUpgradableSoftwareRelease(),
                      None)
                      

  def testUpgradeDecision_getComputer(self):
    computer = self._makeComputer(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(computer)

    found_computer = upgrade_decision.UpgradeDecision_getComputer()
    self.assertEquals(computer.getRelativeUrl(),
                      found_computer.getRelativeUrl())

  def testUpgradeDecision_getComputer_2_lines(self):
    computer = self._makeComputer(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(computer)

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)

    found_computer = upgrade_decision.UpgradeDecision_getComputer()
    self.assertEquals(computer.getRelativeUrl(),
                      found_computer.getRelativeUrl())

  def testUpgradeDecision_getComputer_2_computer(self):
    computer = self._makeComputer(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(computer)

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(computer)

    self.assertRaises(ValueError, upgrade_decision.UpgradeDecision_getComputer)

  def testUpgradeDecision_getComputer_O_computer(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)

    found_computer = upgrade_decision.UpgradeDecision_getComputer()
    self.assertEquals(None, found_computer)


  def testUpgradeDecision_getHostingSubscription(self):
    hosting_subscription = self._makeHostingSubscription(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(hosting_subscription)

    found_hosting_subscription = upgrade_decision.UpgradeDecision_getHostingSubscription()
    self.assertEquals(hosting_subscription.getRelativeUrl(),
                      found_hosting_subscription.getRelativeUrl())


  def testUpgradeDecision_getHostingSubscription_2_lines(self):
    hosting_subscription = self._makeHostingSubscription(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(hosting_subscription)

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)

    found_hosting_subscription = upgrade_decision.UpgradeDecision_getHostingSubscription()
    self.assertEquals(hosting_subscription.getRelativeUrl(),
                      found_hosting_subscription.getRelativeUrl())


  def testUpgradeDecision_getHostingSubscription_2_hosting(self):
    hosting_subscription = self._makeHostingSubscription(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(hosting_subscription)

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(hosting_subscription)

    self.assertRaises(ValueError, upgrade_decision.UpgradeDecision_getHostingSubscription)

  def testUpgradeDecision_getHostingSubscription_O_hosting(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)

    found_hosting_subscription = upgrade_decision.UpgradeDecision_getHostingSubscription()
    self.assertEquals(None, found_hosting_subscription)

     
  def testUpgradeDecision_getSoftwareRelease(self):
    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(software_release)

    found_software_release = upgrade_decision.UpgradeDecision_getSoftwareRelease()
    self.assertEquals(software_release.getRelativeUrl(),
                      found_software_release.getRelativeUrl())

  def testUpgradeDecision_getSoftwareRelease_2_lines(self):
    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(software_release)

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)

    found_software_release = upgrade_decision.UpgradeDecision_getSoftwareRelease()
    self.assertEquals(software_release.getRelativeUrl(),
                      found_software_release.getRelativeUrl())

  def testUpgradeDecision_getSoftwareRelease_2_sr(self):
    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(software_release)

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(software_release)

    self.assertRaises(ValueError, upgrade_decision.UpgradeDecision_getSoftwareRelease)

  def testUpgradeDecision_getSoftwareRelease_O_sr(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)

    found_software_release = upgrade_decision.UpgradeDecision_getSoftwareRelease()
    self.assertEquals(None, found_software_release)

  def testUpgradeDecision_upgradeHostingSubscription(self):

    person = self._makePerson(self.new_id)
    hosting_subscription = self._makeHostingSubscription(self.new_id)
    hosting_subscription.edit(
          destination_section_value = person.getRelativeUrl())

    self._makeSoftwareInstance(hosting_subscription,
                               hosting_subscription.getUrlString())
   
    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList(
       [software_release, hosting_subscription])
    self.tic()
   
    slap_state = hosting_subscription.getSlapState()
    
    self.assertFalse(upgrade_decision.UpgradeDecision_upgradeHostingSubscription())
    self.assertNotEqual(software_release.getUrlString(),
                     hosting_subscription.getUrlString())

    upgrade_decision.confirm()
    upgrade_decision.start()

    # Check that url_string change, but slap state doesn't
    self.assertNotEqual(software_release.getUrlString(),
                     hosting_subscription.getUrlString())

    self.assertTrue(upgrade_decision.UpgradeDecision_upgradeHostingSubscription())
    self.assertEqual(software_release.getUrlString(),
                     hosting_subscription.getUrlString())

    self.assertEqual(slap_state, hosting_subscription.getSlapState())
    self.assertEqual('stopped', upgrade_decision.getSimulationState())

  def testUpgradeDecision_processUpgradeeHostingSubscription(self):
    person = self._makePerson(self.new_id)
    hosting_subscription = self._makeHostingSubscription(self.new_id)
    hosting_subscription.edit(
          destination_section_value = person.getRelativeUrl())

    self._makeSoftwareInstance(hosting_subscription,
                               hosting_subscription.getUrlString())
   
    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList(
       [software_release, hosting_subscription])
    self.tic()
   
    slap_state = hosting_subscription.getSlapState()
    
    self.assertFalse(upgrade_decision.UpgradeDecision_processUpgrade())
    self.assertNotEqual(software_release.getUrlString(),
                     hosting_subscription.getUrlString())

    upgrade_decision.confirm()
    upgrade_decision.start()

    # Check that url_string change, but slap state doesn't
    self.assertNotEqual(software_release.getUrlString(),
                     hosting_subscription.getUrlString())

    self.assertTrue(upgrade_decision.UpgradeDecision_processUpgrade())
    self.assertEqual(software_release.getUrlString(),
                     hosting_subscription.getUrlString())

    self.assertEqual(slap_state, hosting_subscription.getSlapState())
    self.assertEqual('stopped', upgrade_decision.getSimulationState())


  def testUpgradeDecision_upgradeHostingSubscription_no_software_release(self):

    person = self._makePerson(self.new_id)
    hosting_subscription = self._makeHostingSubscription(self.new_id)
    hosting_subscription.edit(
          destination_section_value = person.getRelativeUrl())

    self._makeSoftwareInstance(hosting_subscription,
                               hosting_subscription.getUrlString())
   
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([hosting_subscription])
    self.tic()
   
    upgrade_decision.confirm()
    upgrade_decision.start()

    self.assertFalse(upgrade_decision.UpgradeDecision_upgradeHostingSubscription())
    self.assertEqual('started', upgrade_decision.getSimulationState())

  def testUpgradeDecision_upgradeHostingSubscription_no_hosting_subscripion(self):

    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release])
    self.tic()
    
    upgrade_decision.confirm()
    upgrade_decision.start()

    self.assertFalse(upgrade_decision.UpgradeDecision_upgradeHostingSubscription())
    self.assertEqual('started', upgrade_decision.getSimulationState())
    
  def testUpgradeDecision_upgradeComputer_no_software_release(self):

    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(
          source_administration_value = person.getRelativeUrl())

    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([computer])
    self.tic()
   
    upgrade_decision.confirm()
    upgrade_decision.start()

    self.assertFalse(upgrade_decision.UpgradeDecision_upgradeComputer())
    self.assertEqual('started', upgrade_decision.getSimulationState())


  def testUpgradeDecision_upgradeComputer_no_hosting_subscripion(self):

    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release])
    self.tic()
    
    upgrade_decision.confirm()
    upgrade_decision.start()

    self.assertFalse(upgrade_decision.UpgradeDecision_upgradeComputer())
    self.assertEqual('started', upgrade_decision.getSimulationState())
    
  def testUpgradeDecision_upgradeComputer(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release, computer])
    url = software_release.getUrlString()
    
    self.tic()

    self.assertFalse(upgrade_decision.UpgradeDecision_upgradeComputer())

    upgrade_decision.confirm()
    upgrade_decision.start()

    self.assertTrue(upgrade_decision.UpgradeDecision_upgradeComputer())
    self.tic()
    
    software_installation = computer.getAggregateRelatedValue(
            portal_type='Software Installation')
    self.assertEqual('start_requested', software_installation.getSlapState())
    self.assertEqual(url, software_installation.getUrlString())
    self.assertEqual('validated', software_installation.getValidationState())
    self.assertEqual('stopped', upgrade_decision.getSimulationState())


  def testUpgradeDecision_processUpgradeComputer(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release, computer])
    url = software_release.getUrlString()
    
    self.tic()

    self.assertFalse(upgrade_decision.UpgradeDecision_processUpgrade())

    upgrade_decision.confirm()
    upgrade_decision.start()

    self.assertTrue(upgrade_decision.UpgradeDecision_processUpgrade())
    self.tic()
    
    software_installation = computer.getAggregateRelatedValue(
            portal_type='Software Installation')
    self.assertEqual('start_requested', software_installation.getSlapState())
    self.assertEqual(url, software_installation.getUrlString())
    self.assertEqual('validated', software_installation.getValidationState())
    self.assertEqual('stopped', upgrade_decision.getSimulationState())


  def testSoftwareRelease_createUpgradeDecision_computer(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(source_administration_value=person)
    software_release = self._makeSoftwareRelease(self.new_id)
    
    upgrade_decision = software_release.SoftwareRelease_createUpgradeDecision(
          source_url=computer.getRelativeUrl(),
          title="TEST-SRUPDE-%s" % self.new_id)
    self.tic()
    
    self.assertEqual(upgrade_decision.getSimulationState(), 'draft')
    self.assertEqual(upgrade_decision.getDestinationSection(),
                       person.getRelativeUrl())
    
    decision_line = upgrade_decision.contentValues(
                    portal_type='Upgrade Decision Line')[0]
    
    self.assertEqual(decision_line.getTitle(),
                        'Request decision upgrade for %s on Computer %s' % (
                        software_release.getTitle(), computer.getReference())
                    )
    self.assertEqual(decision_line.getAggregate(portal_type='Computer'),
                      computer.getRelativeUrl())
    self.assertEqual(decision_line.getAggregate(portal_type='Software Release'),
                      software_release.getRelativeUrl())
  
  
  def testSoftwareRelease_createUpgradeDecision_hostingSubscription(self):
    person = self._makePerson(self.new_id)
    hosting_subscription = self._makeHostingSubscription(self.new_id)
    hosting_subscription.edit(
          destination_section_value = person.getRelativeUrl())
    software_release = self._makeSoftwareRelease(self.new_id)
    
    upgrade_decision = software_release.SoftwareRelease_createUpgradeDecision(
          source_url=hosting_subscription.getRelativeUrl(),
          title="TEST-SRUPDE-%s" % self.new_id)
    self.tic()
    
    self.assertEqual(upgrade_decision.getSimulationState(), 'draft')
    self.assertEqual(upgrade_decision.getDestinationSection(),
                       person.getRelativeUrl())
    
    decision_line = upgrade_decision.contentValues(
                    portal_type='Upgrade Decision Line')[0]
                    
    self.assertEqual(decision_line.getAggregate(portal_type='Hosting Subscription'),
                      hosting_subscription.getRelativeUrl())
    self.assertEqual(decision_line.getAggregate(portal_type='Software Release'),
                      software_release.getRelativeUrl())
  
  
  def testSoftwareRelease_getUpgradeDecisionInProgress(self):
    computer = self._makeComputer(self.new_id)
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._requestSoftwareRelease(self.new_id,
                                    software_product.getRelativeUrl())
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release, computer])
    software_release2 = self._makeSoftwareRelease(self.generateNewId())
    upgrade_decision.confirm()
    reference = upgrade_decision.getReference()
    
    self.tic()
    
    in_progress = software_release.SoftwareRelease_getUpgradeDecisionInProgress(
                                computer.getUid())
    self.assertEqual(in_progress.getReference(), reference)
    
    in_progress = software_release.SoftwareRelease_getUpgradeDecisionInProgress(
                                software_release.getUid())
    self.assertEqual(in_progress.getReference(), reference)
    
    in_progress = software_release2.SoftwareRelease_getUpgradeDecisionInProgress(
                                computer.getUid())
    self.assertEqual(in_progress, None)
  
  def testSoftwareRelease_getUpgradeDecisionInProgress_cancelled(self):
    computer = self._makeComputer(self.new_id)
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._requestSoftwareRelease(self.new_id,
                                    software_product.getRelativeUrl())
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release, computer])
    upgrade_decision.confirm()
    upgrade_decision.cancel()
    
    self.tic()
    in_progress = software_release.SoftwareRelease_getUpgradeDecisionInProgress(
                                computer.getUid())
    self.assertEqual(in_progress, None)
    
    upgrade_decision2 = self._makeUpgradeDecision()
    upgrade_decision_line2 = self._makeUpgradeDecisionLine(upgrade_decision2)
    upgrade_decision_line2.setAggregateValueList([software_release, computer])
    upgrade_decision2.confirm()
    upgrade_decision2.start()
    self.tic()
    
    in_progress = software_release.SoftwareRelease_getUpgradeDecisionInProgress(
                                computer.getUid())
    self.assertEqual(in_progress.getReference(), upgrade_decision2.getReference())
  
  def testSoftwareRelease_getUpgradeDecisionInProgress_hosting_subs(self):
    person = self._makePerson(self.new_id)
    hosting_subscription = self._makeHostingSubscription(self.new_id)
    hosting_subscription.edit(
          destination_section_value = person.getRelativeUrl())
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._requestSoftwareRelease(self.new_id,
                                    software_product.getRelativeUrl())
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release,
                                                      hosting_subscription])
    upgrade_decision.confirm()
    reference = upgrade_decision.getReference()
    self.tic()
    
    in_progress = software_release.SoftwareRelease_getUpgradeDecisionInProgress(
                                hosting_subscription.getUid())
    self.assertEqual(in_progress.getReference(), reference)
    
    upgrade_decision.cancel()
    self.tic()
    
    in_progress = software_release.SoftwareRelease_getUpgradeDecisionInProgress(
                                hosting_subscription.getUid())
    self.assertEqual(in_progress, None)
  
  
  def testSoftwareRelease_getUpgradeDecisionInProgress_software_product(self):
    computer = self._makeComputer(self.new_id)
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._requestSoftwareRelease(self.new_id,
                                    software_product.getRelativeUrl())
    software_release2 = self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl())
    software_release3 = self._makeSoftwareRelease(self.generateNewId())
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release, computer])
    upgrade_decision.confirm()
    reference = upgrade_decision.getReference()
    
    self.tic()
    
    in_progress = software_release.SoftwareRelease_getUpgradeDecisionInProgress(
                                computer.getUid())
    self.assertEqual(in_progress.getReference(), reference)
    
    in_progress = software_release2.SoftwareRelease_getUpgradeDecisionInProgress(
                                computer.getUid())
    self.assertEqual(in_progress.getReference(), reference)
    
    in_progress = software_release3.SoftwareRelease_getUpgradeDecisionInProgress(
                                computer.getUid())
    self.assertEqual(in_progress, None)
  
  
  def testSoftwareRelease_getUpgradeDecisionInProgress_software_product_hs(self):
    person = self._makePerson(self.new_id)
    hosting_subscription = self._makeHostingSubscription(self.new_id)
    hosting_subscription.edit(
          destination_section_value = person.getRelativeUrl())
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._requestSoftwareRelease(self.new_id,
                                    software_product.getRelativeUrl())
    software_release2 = self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl())
    software_release3 = self._makeSoftwareRelease(self.generateNewId())
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release,
                                                      hosting_subscription])
    upgrade_decision.confirm()
    reference = upgrade_decision.getReference()
    reference = upgrade_decision.getReference()
    
    self.tic()
    
    in_progress = software_release.SoftwareRelease_getUpgradeDecisionInProgress(
                                hosting_subscription.getUid())
    self.assertEqual(in_progress.getReference(), reference)
    
    in_progress = software_release2.SoftwareRelease_getUpgradeDecisionInProgress(
                                hosting_subscription.getUid())
    self.assertEqual(in_progress.getReference(), reference)
    
    in_progress = software_release3.SoftwareRelease_getUpgradeDecisionInProgress(
                                hosting_subscription.getUid())
    self.assertEqual(in_progress, None)
  
  
  def testUpgradeDecision_tryToCancel(self):
    computer = self._makeComputer(self.new_id)
    software_release = self._makeSoftwareRelease(self.new_id)
    software_release2 = self._makeSoftwareRelease(self.generateNewId())
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release, computer])
    upgrade_decision.confirm()
    
    upgrade_decision2 = self._makeUpgradeDecision()
    upgrade_decision_line2 = self._makeUpgradeDecisionLine(upgrade_decision2)
    upgrade_decision_line2.setAggregateValueList([software_release, computer])
    upgrade_decision2.confirm()
    upgrade_decision2.start()
    
    url = software_release.getUrlString()
    url2 = software_release2.getUrlString()
    
    # Cancel is not possible with the same url_string
    self.assertEqual(upgrade_decision.UpgradeDecision_tryToCancel(url), False)
    self.assertEqual(upgrade_decision.UpgradeDecision_tryToCancel(url2), True)
    self.assertEqual(upgrade_decision.getSimulationState(), 'cancelled')
    
    # Cancel is no longer possible
    self.assertEqual(upgrade_decision2.UpgradeDecision_tryToCancel(url), False)
    self.assertEqual(upgrade_decision2.UpgradeDecision_tryToCancel(url2), False)
    self.assertEqual(upgrade_decision2.getSimulationState(), 'started')
    
    
  def testComputer_checkAndCreateUpgradeDecision(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(source_administration_value=person,
                  allocation_scope="open/public")
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._requestSoftwareRelease(self.new_id,
                                    software_product.getRelativeUrl())
    self._makeSoftwareInstallation(self.new_id,
                              computer, software_release.getUrlString())
    self.tic()
    upgrade_decision = computer.Computer_checkAndCreateUpgradeDecision()
    self.assertEqual(len(upgrade_decision), 0)
    
    software_release2 = self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl())
    # Should be ignored, Publication Date is for tomorrow
    self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl(),
                                      (DateTime() + 1))
    self.tic()
    
    upgrade_decision = computer.Computer_checkAndCreateUpgradeDecision()
    self.assertEqual(len(upgrade_decision), 1)
    self.assertEqual(upgrade_decision[0].getSimulationState(), 'started')
    
    computer_aggregate = upgrade_decision[0].UpgradeDecision_getComputer()
    self.assertEqual(computer_aggregate.getReference(),
                      computer.getReference())
    release = upgrade_decision[0].UpgradeDecision_getSoftwareRelease()
    self.assertEqual(release.getUrlString(),
                                software_release2.getUrlString())
    self.tic()
    upgrade_decision2 = computer.Computer_checkAndCreateUpgradeDecision()
    self.assertEqual(len(upgrade_decision2), 0)
  
  def testComputer_checkAndCreateUpgradeDecision_personal_with_exist(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(source_administration_value=person,
                  allocation_scope="open/personal")
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._requestSoftwareRelease(self.new_id,
                                    software_product.getRelativeUrl())
    self._makeSoftwareInstallation(self.new_id,
                              computer, software_release.getUrlString())
    self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl())
    self.tic()
    
    upgrade_decision = computer.Computer_checkAndCreateUpgradeDecision()[0]
    self.assertEqual(upgrade_decision.getSimulationState(), 'planned')
    
    software_release3 = self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl())
    self.tic()
    
    upgrade_decision2 = computer.Computer_checkAndCreateUpgradeDecision()[0]
    
    self.assertEqual(upgrade_decision.getSimulationState(), 'cancelled')
    self.assertEqual(upgrade_decision2.getSimulationState(), 'planned')
    release = upgrade_decision2.UpgradeDecision_getSoftwareRelease()
    self.assertEqual(release.getUrlString(),
                                software_release3.getUrlString())
  
  def testComputer_checkAndCreateUpgradeDecision_public_with_exist(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(source_administration_value=person,
                  allocation_scope="open/public")
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._requestSoftwareRelease(self.new_id,
                                    software_product.getRelativeUrl())
    self._makeSoftwareInstallation(self.new_id,
                              computer, software_release.getUrlString())
    self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl())
    self.tic()
    
    upgrade_decision = computer.Computer_checkAndCreateUpgradeDecision()[0]
    self.assertEqual(upgrade_decision.getSimulationState(), 'started')
    
    self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl())
    self.tic()
    
    upgrade_decision2 = computer.Computer_checkAndCreateUpgradeDecision()
    
    self.assertEqual(len(upgrade_decision2), 0)
    self.assertEqual(upgrade_decision.getSimulationState(), 'started')
    
  
  def testComputer_hostingSubscriptionCreateUpgradeDecision_no_newer(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(source_administration_value=person)
    self._makeComputerPartitions(computer)
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._requestSoftwareRelease(self.new_id,
                                    software_product.getRelativeUrl())
    url_string = software_release.getUrlString()
    self._makeSoftwareInstallation(self.new_id, computer, url_string)
    self.tic()
    
    upgrade_decision = computer.Computer_hostingSubscriptionCreateUpgradeDecision()
    self.assertEqual(len(upgrade_decision), 0)
    
    # Create Hosting Subscription
    hosting_subscription = self._makeFullHostingSubscription(self.new_id,
                                    url_string, person)
    self.tic()
    
    upgrade_decision = computer.Computer_hostingSubscriptionCreateUpgradeDecision()
    self.assertEqual(len(upgrade_decision), 0)
    
    self._makeFullSoftwareInstance(hosting_subscription, url_string)
    self._markComputerPartitionBusy(computer,
                                    hosting_subscription.getPredecessorValue())
    
    self._requestSoftwareRelease(self.generateNewId(),
                                    software_product.getRelativeUrl())
    self.tic()
    
    upgrade_decision = computer.Computer_hostingSubscriptionCreateUpgradeDecision()
    self.assertEqual(len(upgrade_decision), 0)
  
  def testComputer_hostingSubscriptionCreateUpgradeDecision(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(source_administration_value=person)
    self._makeComputerPartitions(computer)
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._requestSoftwareRelease(self.new_id,
                                    software_product.getRelativeUrl())
    url_string = software_release.getUrlString()
    
    self._makeSoftwareInstallation(self.new_id, computer, url_string)
    
    # Create Hosting Subscription and Software Instance
    hosting_subscription = self._makeFullHostingSubscription(self.new_id,
                                    url_string, person)
    self._makeFullSoftwareInstance(hosting_subscription, url_string)
    self._markComputerPartitionBusy(computer,
                                    hosting_subscription.getPredecessorValue())
    
    # Install the Newest software release
    software_release2 = self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl())
    self._makeSoftwareInstallation(self.generateNewId(), computer,
                                    software_release2.getUrlString())
    self.tic()
    
    up_decision = computer.Computer_hostingSubscriptionCreateUpgradeDecision()[0]
    self.assertEqual(up_decision.getSimulationState(), 'planned')
    
    self.assertEqual(up_decision.UpgradeDecision_getHostingSubscription().\
                      getReference(), hosting_subscription.getReference())

    self.assertEqual(up_decision.UpgradeDecision_getSoftwareRelease().\
                              getUrlString(), software_release2.getUrlString())
    
    self.tic()
    up_decision2 = computer.Computer_hostingSubscriptionCreateUpgradeDecision()
    self.assertEqual(len(up_decision2), 0)
  
  
  def testComputer_hostingSubscriptionCreateUpgradeDecision_with_exist(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(source_administration_value=person)
    self._makeComputerPartitions(computer)
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._requestSoftwareRelease(self.new_id,
                                    software_product.getRelativeUrl())
    url_string = software_release.getUrlString()
    
    self._makeSoftwareInstallation(self.new_id, computer, url_string)
    
    # Create Hosting Subscription and Software Instance
    hosting_subscription = self._makeFullHostingSubscription(self.new_id,
                                    url_string, person)
    self._makeFullSoftwareInstance(hosting_subscription, url_string)
    self._markComputerPartitionBusy(computer,
                                    hosting_subscription.getPredecessorValue())
    
    # Install the Newest software release
    software_release2 = self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl())
    self._makeSoftwareInstallation(self.generateNewId(), computer,
                                    software_release2.getUrlString())
    self.tic()
    
    up_decision = computer.Computer_hostingSubscriptionCreateUpgradeDecision()[0]
    self.assertEqual(up_decision.getSimulationState(), 'planned')
    
    # Install the another software release
    software_release3 = self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl())
    self._makeSoftwareInstallation(self.generateNewId(), computer,
                                    software_release3.getUrlString())
    self.tic()
    
    up_decision2 = computer.Computer_hostingSubscriptionCreateUpgradeDecision()[0]
    self.assertEqual(up_decision2.getSimulationState(), 'planned')
    self.assertEqual(up_decision.getSimulationState(), 'cancelled')
    release = up_decision2.UpgradeDecision_getSoftwareRelease()
    self.assertEqual(release.getUrlString(),
                                software_release3.getUrlString())
    
  
  def testBase_acceptUpgradeDecision_no_reference(self):
    upgrade_decision = self._makeUpgradeDecision()
    self.assertRaises(ValueError, self.portal.Base_acceptUpgradeDecision, None)
    
  def testBase_acceptUpgradeDecision_duplicated_reference(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTBADREFERENCE")
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTBADREFERENCE")
    self.tic()
    self.assertRaises(ValueError, self.portal.Base_acceptUpgradeDecision, None)

  def testBase_acceptUpgradeDecision_no_upgrade_decision(self):
    redirect_url = self.portal.Base_acceptUpgradeDecision('UD-UNEXISTING')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Unable%20to%20find%20the%20Upgrade%20Decision."), 
      "%s contains the wrong message" %  redirect_url)
     
  def testBase_acceptUpgradeDecision_draft_upgrade_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTDRAFT")
    self.tic()
    redirect_url = self.portal.Base_acceptUpgradeDecision('UD-TESTDRAFT')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Sorry%2C%20the%20upgrade%20is%20not%20possible%20yet%21"), 
      "%s contains the wrong message" %  redirect_url)

  def testBase_acceptUpgradeDecision_planned_upgrade_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTPLANNED")
    upgrade_decision.plan()
    self.tic()
    redirect_url = self.portal.Base_acceptUpgradeDecision('UD-TESTPLANNED')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Sorry%2C%20the%20upgrade%20is%20not%20possible%20yet%21"), 
      "%s contains the wrong message" %  redirect_url)

  def testBase_acceptUpgradeDecision_confirmed_upgrade_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTCONFIRMED")
    upgrade_decision.confirm()
    self.tic()
    redirect_url = self.portal.Base_acceptUpgradeDecision('UD-TESTCONFIRMED')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=This%20Upgrade%20Decision%20has%20been%20"\
      "requested%2C%20it%20will%20be%20processed%20in%20few%20minutes."), 
      "%s contains the wrong message" %  redirect_url)
    self.assertEquals(upgrade_decision.getSimulationState(), 'started')

  def testBase_acceptUpgradeDecision_started_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTSTARTED")
    upgrade_decision.start()
    self.tic()
    redirect_url = self.portal.Base_acceptUpgradeDecision('UD-TESTSTARTED')
    self.assertTrue(redirect_url.endswith(
     "?portal_status_message=This%20Upgrade%20Decision%20is%20already%20Started."), 
     "%s contains the wrong message" %  redirect_url)

  def testBase_acceptUpgradeDecision_stop_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTSTOP")
    upgrade_decision.start()
    upgrade_decision.stop()
    self.tic()
    redirect_url = self.portal.Base_acceptUpgradeDecision('UD-TESTSTOP')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=This%20Upgrade%20Decision%20has%20been%20already%20processed."),
      "%s contains the wrong message" %  redirect_url)

  def testBase_acceptUpgradeDecision_delivered_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTDELIVERED")
    upgrade_decision.start()
    upgrade_decision.stop()
    upgrade_decision.deliver()
    self.tic()
    redirect_url = self.portal.Base_acceptUpgradeDecision('UD-TESTDELIVERED')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=This%20Upgrade%20Decision%20has%20been%20already%20processed."),
      "%s contains the wrong message" %  redirect_url)

  def testBase_acceptUpgradeDecision_cancelled_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTCANCELLED")
    upgrade_decision.cancel()
    self.tic()
    redirect_url = self.portal.Base_acceptUpgradeDecision('UD-TESTCANCELLED')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Sorry%2C%20the%20upgrade%20is%20not%20possble%2C%20Upgrade%20Decision%20was%20Canceled%20or%20Rejected%21"),
      "%s contains the wrong message" %  redirect_url)

  def testBase_acceptUpgradeDecision_rejected_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTREJECT")
    upgrade_decision.cancel()
    self.tic()
    redirect_url = self.portal.Base_acceptUpgradeDecision('UD-TESTREJECT')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Sorry%2C%20the%20upgrade%20is%20not%20possble%2C%20Upgrade%20Decision%20was%20Canceled%20or%20Rejected%21"),
      "%s contains the wrong message" %  redirect_url)

  def testBase_rejectUpgradeDecision_no_reference(self):
    upgrade_decision = self._makeUpgradeDecision()
    self.assertRaises(ValueError, self.portal.Base_rejectUpgradeDecision, None)
    
  def testBase_rejectUpgradeDecision_duplicated_reference(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTBADREFERENCE")
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTBADREFERENCE")
    self.tic()
    self.assertRaises(ValueError, self.portal.Base_acceptUpgradeDecision, None)

  def testBase_rejectUpgradeDecision_no_upgrade_decision(self):
    redirect_url = self.portal.Base_rejectUpgradeDecision('UD-UNEXISTING')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Unable%20to%20find%20the%20Upgrade%20Decision."), 
      "%s contains the wrong message" %  redirect_url)
     
  def testBase_rejectUpgradeDecision_draft_upgrade_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTDRAFT")
    self.tic()
    redirect_url = self.portal.Base_rejectUpgradeDecision('UD-TESTDRAFT')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Thanks%20Upgrade%20Decision%20has%20been"\
      "%20rejected%20Successfully%20%28You%20cannot%20use%20it%20anymore%29."), 
      "%s contains the wrong message" %  redirect_url)
    self.assertEquals(upgrade_decision.getSimulationState(), 'rejected')

  def testBase_rejectUpgradeDecision_planned_upgrade_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTPLANNED")
    upgrade_decision.plan()
    self.tic()
    redirect_url = self.portal.Base_rejectUpgradeDecision('UD-TESTPLANNED')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Thanks%20Upgrade%20Decision%20has%20been"\
      "%20rejected%20Successfully%20%28You%20cannot%20use%20it%20anymore%29."), 
      "%s contains the wrong message" %  redirect_url)
    self.assertEquals(upgrade_decision.getSimulationState(), 'rejected')

  def testBase_rejectUpgradeDecision_confirmed_upgrade_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTCONFIRMED")
    upgrade_decision.confirm()
    self.tic()
    redirect_url = self.portal.Base_rejectUpgradeDecision('UD-TESTCONFIRMED')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Thanks%20Upgrade%20Decision%20has%20been"\
      "%20rejected%20Successfully%20%28You%20cannot%20use%20it%20anymore%29."),
      "%s contains the wrong message" %  redirect_url)
    self.assertEquals(upgrade_decision.getSimulationState(), 'rejected')

  def testBase_rejectUpgradeDecision_started_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTSTARTED")
    upgrade_decision.start()
    self.tic()
    redirect_url = self.portal.Base_rejectUpgradeDecision('UD-TESTSTARTED')
    self.assertTrue(redirect_url.endswith(
     "?portal_status_message=Sorry%2C%20This%20Upgrade%20Decision%20is%20"\
     "already%20Started%2C%20you%20cannot%20reject%20it%20anymore."),
     "%s contains the wrong message" %  redirect_url)

  def testBase_rejectUpgradeDecision_stop_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTSTOP")
    upgrade_decision.start()
    upgrade_decision.stop()
    self.tic()
    redirect_url = self.portal.Base_rejectUpgradeDecision('UD-TESTSTOP')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Sorry%2C%20this%20Upgrade%20Decision%20has%20been%20already%20processed."),
      "%s contains the wrong message" %  redirect_url)

  def testBase_rejectUpgradeDecision_delivered_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTDELIVERED")
    upgrade_decision.start()
    upgrade_decision.stop()
    upgrade_decision.deliver()
    self.tic()
    redirect_url = self.portal.Base_rejectUpgradeDecision('UD-TESTDELIVERED')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Sorry%2C%20this%20Upgrade%20Decision%20has%20been%20already%20processed."),
      "%s contains the wrong message" %  redirect_url)

  def testBase_rejectUpgradeDecision_cancelled_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTCANCELLED")
    upgrade_decision.cancel()
    self.tic()
    redirect_url = self.portal.Base_rejectUpgradeDecision('UD-TESTCANCELLED')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Upgrade%20Decision%20is%20already%20Rejected%21"),
      "%s contains the wrong message" %  redirect_url)

  def testBase_rejectUpgradeDecision_reject_decision(self):
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.setReference("UD-TESTREJECT")
    upgrade_decision.reject()
    self.tic()
    redirect_url = self.portal.Base_rejectUpgradeDecision('UD-TESTREJECT')
    self.assertTrue(redirect_url.endswith(
      "?portal_status_message=Upgrade%20Decision%20is%20already%20Rejected%21"),
      "%s contains the wrong message" %  redirect_url)

  def testUpgradeDecision_isUpgradeFinished_computer(self):
    computer = self._makeComputer(self.new_id)
    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release, computer])

    upgrade_decision.confirm()
    upgrade_decision.stop()
    
    self.assertFalse(upgrade_decision.UpgradeDecision_isUpgradeFinished())
    self._makeSoftwareInstallation(self.new_id, computer, 
                                   software_release.getUrlString())
    self.tic()
    self.assertTrue(upgrade_decision.UpgradeDecision_isUpgradeFinished())

  def testUpgradeDecision_isUpgradeFinished_hosting_subscription(self):
    hosting_subscription = self._makeHostingSubscription(self.new_id)
    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release,
                                                hosting_subscription])

    upgrade_decision.confirm()
    upgrade_decision.stop()
    
    self.assertFalse(upgrade_decision.UpgradeDecision_isUpgradeFinished())
    hosting_subscription.setUrlString(software_release.getUrlString()) 
    self.assertTrue(upgrade_decision.UpgradeDecision_isUpgradeFinished())

  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "slapos-upgrade-computer.notification"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["testUpgradeDecision_notify_computer"])')
  def testUpgradeDecision_notify_computer(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    software_release = self._makeSoftwareRelease(self.new_id)
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release.setAggregateValue(software_product)
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.edit(destination_decision_value=person)
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release, computer])
    
    notification_message = self.portal.notification_message_module.newContent(
      portal_type="Notification Message",
      title='Test NM title %s' % self.new_id,
      text_content_substitution_mapping_method_id=
          "NotificationMessage_getSubstitutionMappingDictFromArgument",
      text_content="""${software_product_title}
${computer_title}
${computer_reference}
${software_release_name}
${software_release_reference}
${upgrade_accept_link}
${upgrade_reject_link}
${new_software_release_url}""",
      content_type='text/html',
      )
    self.portal.REQUEST\
        ['testUpgradeDecision_notify_computer'] = \
        notification_message.getRelativeUrl()
    
    self.tic()
    
    self.assertEquals(None, upgrade_decision.UpgradeDecision_notify())
    
    upgrade_decision.plan()
    
    self.tic()
    
    self.assertEquals(None, upgrade_decision.UpgradeDecision_notify())
    
    self.tic()
    
    self.assertEquals(upgrade_decision.getSimulationState(), 'confirmed')
    self.assertEquals(len(upgrade_decision.getFollowUpRelatedValueList()), 1)
    event = upgrade_decision.getFollowUpRelatedValue()
    
    self.assertEquals(event.getTitle(), 
     "New Software available for Installation at %s" % computer.getTitle())
     
    self.assertEqual(event.getTextContent().splitlines(),
      [software_product.getTitle(), computer.getTitle(), computer.getReference(),
       software_release.getTitle(), software_release.getReference(), 
       'Base_acceptUpgradeDecision?reference=%s' % upgrade_decision.getReference(),
       'Base_rejectUpgradeDecision?reference=%s' % upgrade_decision.getReference(),
       software_release.getUrlString()])
      
      
    self.assertEquals(event.getSimulationState(), "delivered")

  @simulate('NotificationTool_getDocumentValue',
            'reference=None',
  'assert reference == "slapos-upgrade-hosting-subscription.notification"\n' \
  'return context.restrictedTraverse(' \
  'context.REQUEST["testUpgradeDecision_notify_hosting_subscription"])')
  def testUpgradeDecision_notify_hosting_subscription(self):
    person = self._makePerson(self.new_id)
    hosting_subscription = self._makeHostingSubscription(self.new_id)
    software_release = self._makeSoftwareRelease(self.new_id)
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release.setAggregateValue(software_product)
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision.edit(destination_decision_value=person)
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release, 
                                                hosting_subscription])

    old_url = hosting_subscription.getUrlString()

    notification_message = self.portal.notification_message_module.newContent(
      portal_type="Notification Message",
      title='Test NM title %s' % self.new_id,
      text_content_substitution_mapping_method_id=
          "NotificationMessage_getSubstitutionMappingDictFromArgument",
      text_content="""${software_product_title}
${hosting_subscription_title}
${old_software_release_url}
${software_release_name}
${software_release_reference}
${upgrade_accept_link}
${upgrade_reject_link}
${new_software_release_url}""",
      content_type='text/html',
      )
    self.portal.REQUEST\
        ['testUpgradeDecision_notify_hosting_subscription'] = \
        notification_message.getRelativeUrl()
    
    self.tic()
    
    self.assertEquals(None, upgrade_decision.UpgradeDecision_notify())
    
    upgrade_decision.plan()
    
    self.tic()
    
    self.assertEquals(None, upgrade_decision.UpgradeDecision_notify())
    
    self.tic()
    
    self.assertEquals(upgrade_decision.getSimulationState(), 'confirmed')
    self.assertEquals(len(upgrade_decision.getFollowUpRelatedValueList()), 1)
    event = upgrade_decision.getFollowUpRelatedValue()
    
    self.assertEquals(event.getTitle(), 
     "New Upgrade available for %s" % hosting_subscription.getTitle())
     
    self.assertEqual(event.getTextContent().splitlines(),
      [software_product.getTitle(), hosting_subscription.getTitle(), 
       old_url, software_release.getTitle(), software_release.getReference(), 
       'Base_acceptUpgradeDecision?reference=%s' % upgrade_decision.getReference(),
       'Base_rejectUpgradeDecision?reference=%s' % upgrade_decision.getReference(),
       software_release.getUrlString()])

    self.assertEquals(event.getSimulationState(), "delivered")
    
    
