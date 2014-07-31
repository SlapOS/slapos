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
from Products.SlapOS.tests.testSlapOSMixin import testSlapOSMixin
from Products.ERP5Type.tests.utils import createZODBPythonScript
from DateTime import DateTime

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

     
  def testUpgradeDecision_getSoftwareRelease(self):
    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()

    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValue(software_release)

    found_software_release = upgrade_decision.UpgradeDecision_getSoftwareRelease()
    self.assertEquals(software_release.getRelativeUrl(),
                      found_software_release.getRelativeUrl())

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


  def testSoftwareRelease_createUpgradeDecision_computer(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(source_administration_value=person)
    software_release = self._makeSoftwareRelease(self.new_id)
    
    upgrade_decision = software_release.SoftwareRelease_createUpgradeDecision(
          source_url=computer.getRelativeUrl(),
          title="TEST-SRUPDE-%s" % self.new_id)
    self.tic()
    
    self.assertEqual(upgrade_decision.getSimulationState(), 'confirmed')
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
    
    self.assertEqual(upgrade_decision.getSimulationState(), 'confirmed')
    self.assertEqual(upgrade_decision.getDestinationSection(),
                       person.getRelativeUrl())
    
    decision_line = upgrade_decision.contentValues(
                    portal_type='Upgrade Decision Line')[0]
                    
    self.assertEqual(decision_line.getAggregate(portal_type='Hosting Subscription'),
                      hosting_subscription.getRelativeUrl())
    self.assertEqual(decision_line.getAggregate(portal_type='Software Release'),
                      software_release.getRelativeUrl())
  
  
  def testSoftwareRelease_isUpgradeDecisionInProgress(self):
    computer = self._makeComputer(self.new_id)
    software_release = self._makeSoftwareRelease(self.new_id)
    upgrade_decision = self._makeUpgradeDecision()
    upgrade_decision_line = self._makeUpgradeDecisionLine(upgrade_decision)
    upgrade_decision_line.setAggregateValueList([software_release, computer])
    software_release2 = self._makeSoftwareRelease(self.generateNewId())
    upgrade_decision.confirm()
    
    self.tic()
    
    in_progress = software_release.SoftwareRelease_isUpgradeDecisionInProgress(
                                title=upgrade_decision.getTitle()
                              )
    self.assertEqual(in_progress, True)
    
    in_progress = software_release.SoftwareRelease_isUpgradeDecisionInProgress()
    self.assertEqual(in_progress, True)
    
    in_progress = software_release.SoftwareRelease_isUpgradeDecisionInProgress(
                                title=upgrade_decision.getTitle(),
                                simulation_state='stopped'
                              )
    self.assertEqual(in_progress, False)
    
    in_progress = software_release2.SoftwareRelease_isUpgradeDecisionInProgress(
                                title=upgrade_decision.getTitle()
                              )
    self.assertEqual(in_progress, False)
    
  
  def testComputer_checkAndCreateUpgradeDecision(self):
    person = self._makePerson(self.new_id)
    computer = self._makeComputer(self.new_id)
    computer.edit(source_administration_value=person)
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._requestSoftwareRelease(self.new_id,
                                    software_product.getRelativeUrl())
    self._makeSoftwareInstallation(self.new_id,
                              computer, software_release.getUrlString())
    self.tic()
    
    upgrade_decision = computer.Computer_checkAndCreateUpgradeDecision()
    self.assertEqual(upgrade_decision, None)
    
    software_release2 = self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl())
    # Should be ignored, Publication Date is for tomorrow
    self._requestSoftwareRelease(self.generateNewId(),
                                      software_product.getRelativeUrl(),
                                      (DateTime() + 1))
    self.tic()
    
    upgrade_decision = computer.Computer_checkAndCreateUpgradeDecision()
    
    self.assertEqual(upgrade_decision.getSimulationState(), 'confirmed')
    
    computer_aggregate = upgrade_decision.UpgradeDecision_getComputer()
    self.assertEqual(computer_aggregate.getReference(),
                      computer.getReference())
    url_string = upgrade_decision.UpgradeDecision_getSoftwareRelease()
    self.assertEqual(url_string.getUrlString(),
                                software_release2.getUrlString())
    
    self.tic()
    upgrade_decision2 = computer.Computer_checkAndCreateUpgradeDecision()
    
    self.assertEqual(upgrade_decision2, None)
  
  
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
    self.assertEqual(upgrade_decision, None)
    
    # Create Hosting Subscription
    hosting_subscription = self._makeFullHostingSubscription(self.new_id,
                                    url_string, person)
    self.tic()
    
    upgrade_decision = computer.Computer_hostingSubscriptionCreateUpgradeDecision()
    self.assertEqual(upgrade_decision, None)
    
    self._makeFullSoftwareInstance(hosting_subscription, url_string)
    self._markComputerPartitionBusy(computer,
                                    hosting_subscription.getPredecessorValue())
    
    self._requestSoftwareRelease(self.generateNewId(),
                                    software_product.getRelativeUrl())
    self.tic()
    
    upgrade_decision = computer.Computer_hostingSubscriptionCreateUpgradeDecision()
    self.assertEqual(upgrade_decision, None)
  
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
    self._makeSoftwareInstallation(self.new_id, computer,
                                    software_release2.getUrlString())
    self.tic()
    
    upgrade_decision = computer.Computer_hostingSubscriptionCreateUpgradeDecision()
    self.assertEqual(upgrade_decision.getSimulationState(), 'confirmed')
    
    self.assertEqual(upgrade_decision.UpgradeDecision_getHostingSubscription().\
                      getReference(), hosting_subscription.getReference())

    self.assertEqual(upgrade_decision.UpgradeDecision_getSoftwareRelease().\
                              getUrlString(), software_release2.getUrlString())
    
    self.tic()
    upgrade_decision2 = computer.Computer_hostingSubscriptionCreateUpgradeDecision()
    self.assertEqual(upgrade_decision2, None)
    
    