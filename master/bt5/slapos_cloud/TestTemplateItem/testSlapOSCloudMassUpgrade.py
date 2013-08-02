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

class TestSlapOSMassUpgrade(testSlapOSMixin):
  def afterSetUp(self):
    super(TestSlapOSMassUpgrade, self).afterSetUp()
    new_id = self.generateNewId()
    self.start_requested_software_release_url = self\
      .generateNewSoftwareReleaseUrl()
    self.destroy_requested_software_release_url = self\
      .generateNewSoftwareReleaseUrl()
    self._makePerson(new_id)
    self._makeComputer(new_id)
    self._makeComputerPartitions(self.computer)
    self._makeSoftwareProduct(new_id)
    self._makeSoftwareReleases(new_id)
    self._makeSoftwareInstallations(new_id)
    self._makeHostingSubscriptions(new_id)
    self._makeSoftwareInstances()
    self.tic()
    transaction.commit()

  def _makePerson(self,new_id):
    # Clone person document
    self.person_user = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    self.person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    self.person_user.validate()
    for assignment in self.person_user.contentValues(portal_type="Assignment"):
      assignment.open()
    transaction.commit()

  def _makeComputer(self,new_id):
    # Clone computer document
    self.computer = self.portal.computer_module\
      .template_computer.Base_createCloneDocument(batch_mode=1)
    self.computer.edit(
      title="computer start %s" % (new_id, ),
      reference="TESTCOMPS-%s" % (new_id, )
    )
    self.computer.validate()

    self.tic()
  
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
      self.tic()
  
  def _makeSoftwareProduct(self, new_id):
    self.software_product = self.portal.software_product_module\
      .template_software_product.Base_createCloneDocument(batch_mode=1)
    self.software_product.edit(
      reference='TESTSOFTPROD-%s' % new_id,
      title='Test software product %s' % new_id
    )
    self.software_product.validate()
    self.tic()

  def _makeSoftwareReleases(self, new_id):
    self.start_requested_software_release = self.portal.software_release_module\
      .template_software_release.Base_createCloneDocument(batch_mode=1)
    self.start_requested_software_release.edit(
      url_string=self.start_requested_software_release_url,
      aggregate=self.software_product.getRelativeUrl(),
      reference='TESTSOFTRELS-%s' % new_id,
      title='Start requested for %s' % self.computer.getUid()
    )
    self.start_requested_software_release.release()

    self.destroy_requested_software_release = self.portal.software_release_module\
      .template_software_release.Base_createCloneDocument(batch_mode=1)
    self.destroy_requested_software_release.edit(
      url_string=self.destroy_requested_software_release_url,
      aggregate=self.software_product.getRelativeUrl(),
      reference='TESTSOFTRELD-%s' % new_id,
      title='Destroy requested for %s' % self.computer\
        .getUid()
    )
    self.destroy_requested_software_release.release()
    self.tic()

  def _makeSoftwareInstallations(self, new_id,):
    self.start_requested_software_installation = self.portal\
      .software_installation_module.template_software_installation\
      .Base_createCloneDocument(batch_mode=1)
    self.start_requested_software_installation.edit(
      url_string=self.start_requested_software_release_url,
      aggregate=self.computer.getRelativeUrl(),
      reference='TESTSOFTINSTS-%s' % new_id,
      title='Start requested for %s' % self.computer.getUid()
    )

    self.start_requested_software_installation.validate()
    self.start_requested_software_installation.requestStart()

    self.destroy_requested_software_installation = self.portal\
      .software_installation_module.template_software_installation\
      .Base_createCloneDocument(batch_mode=1)
    self.destroy_requested_software_installation.edit(
      url_string=self.destroy_requested_software_release_url,
      aggregate=self.computer.getRelativeUrl(),
      reference='TESTSOFTINSTD-%s' % new_id,
      title='Destroy requested for %s' % self.computer\
        .getUid()
    )

    self.destroy_requested_software_installation.validate()
    self.destroy_requested_software_installation.requestStart()
    self.tic()

  def _makeHostingSubscriptions(self, new_id):
    self.start_requested_hosting_subscription = self.portal\
      .hosting_subscription_module.template_hosting_subscription\
      .Base_createCloneDocument(batch_mode=1)
    self.start_requested_hosting_subscription.validate()
    self.start_requested_hosting_subscription.edit(
        title= "Test hosting sub start %s" % new_id,
        reference="TESTHSS-%s" % new_id,
        destination_section_value=self.person_user,
    )

    self.destroy_requested_hosting_subscription = self.portal\
      .hosting_subscription_module.template_hosting_subscription\
      .Base_createCloneDocument(batch_mode=1)
    self.destroy_requested_hosting_subscription.validate()
    self.destroy_requested_hosting_subscription.edit(
        title= "Test hosting sub destroy %s" % new_id,
        reference="TESTHSD-%s" % new_id,
        destination_section_value=self.person_user,
    )
    self.tic()

  def _makeSoftwareInstances(self):
    kw = dict(
      software_release=self.start_requested_software_release_url,
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=self.start_requested_hosting_subscription.getTitle(),
      state='started'
    )
    self.start_requested_hosting_subscription.requestStart(**kw)
    self.start_requested_hosting_subscription.requestInstance(**kw)
    
    software_instance = self.start_requested_hosting_subscription\
      .getPredecessorValue()
    software_instance.edit(aggregate=self.computer.partition1\
      .getRelativeUrl())
 
    kwargs = dict(
      software_release=self.destroy_requested_software_release_url,
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=self.destroy_requested_hosting_subscription.getTitle(),
      state='started'
    ) 
    self.destroy_requested_hosting_subscription.requestStart(**kwargs)
    self.destroy_requested_hosting_subscription.requestInstance(**kwargs)
    
    software_instance = self.destroy_requested_hosting_subscription\
      .getPredecessorValue()
    software_instance.edit(aggregate=self.computer.partition2\
      .getRelativeUrl())
    self.computer.partition1.markBusy()
    self.computer.partition2.markBusy()
    self.computer.partition3.markBusy()

    self.tic()

  def test_SoftwareRelease_getUsage(self):
   # My setup create 1 instance for start_requested_software_release
   self.assertEqual(1,self.destroy_requested_software_release\
     .SoftwareRelease_getUsage())
   self.assertEqual(1,self.start_requested_software_release\
     .SoftwareRelease_getUsage())

  def test_HostingSubscription_changeSoftwareRelease(self):
    host_sub = self.destroy_requested_hosting_subscription
    slap_state = host_sub.getSlapState()

    new_sr = self.start_requested_software_release_url
    host_sub.HostingSubscription_changeSoftwareRelease(new_sr)

    # Check that url_string change, but slap state doesn't
    self.assertEqual(new_sr,host_sub.getUrlString())
    self.assertEqual(slap_state,host_sub.getSlapState())

  def test_SoftwareRelease_requestInstanceUpgrade_without_comps(self):
    self.destroy_requested_software_release\
      .SoftwareRelease_requestInstanceUpgrade(
        self.start_requested_software_release_url,
        [],
        "Test SoftwareRelease_requestInstanceUpgrade %s" % self.generateNewId()
      )
    self.tic()

    self.assertEqual(0,self.destroy_requested_software_release
      .SoftwareRelease_getUsage())
    self.assertEqual(2, self.start_requested_software_release\
      .SoftwareRelease_getUsage())

  def test_SoftwareRelease_requestInstanceUpgrade_with_comps(self):
    self.comp_reference_list = [].append(
      self.computer.getReference()
    )
    
    self.destroy_requested_software_release\
      .SoftwareRelease_requestInstanceUpgrade(
        self.start_requested_software_release.getUrlString(),
        self.comp_reference_list,
        "Test SoftwareRelease_requestInstanceUpgrade %s" % self.generateNewId()
      )
    self.tic()

    self.assertEqual(0,self.destroy_requested_software_release\
      .SoftwareRelease_getUsage())
    self.assertEqual(2, self.start_requested_software_release\
      .SoftwareRelease_getUsage())

  def test_SoftwareProduct_launchMassUpgrade_without_action(self):
    selection_name = 'mass_upgrade_selection'
    listbox = [{'listbox_key':'','computer_filter':[],'workflow_action':''}]
    self.software_product.SoftwareProduct_launchMassUpgrade(
        listbox,
        selection_name
    )
    self.tic()

    # Check that nothing change
    self.assertEqual(1,self.destroy_requested_software_release\
      .SoftwareRelease_getUsage())
    self.assertEqual(1,self.start_requested_software_release\
      .SoftwareRelease_getUsage())

  def test_SoftwareProduct_launchMassUpgrade_with_action_and_comp(self):
    selection_name = 'mass_upgrade_selection'
    listbox = [
      {
        'listbox_key':self.start_requested_software_release.getUrl(),
        'computer_filter':[self.computer.getReference()],
        'workflow_action':self.destroy_requested_software_release.getUrl()
      }
    ]
  
    self.software_product.SoftwareProduct_launchMassUpgrade(
        listbox,
        selection_name
      )
    self.tic()

    self.assertEqual(2,self.destroy_requested_software_release
      .SoftwareRelease_getUsage())
    self.assertEqual(0, self.start_requested_software_release\
      .SoftwareRelease_getUsage())
  
  def test_SoftwareProduct_launchMassUpgrade_with_action_and_without_comp(self):
    selection_name = 'mass_upgrade_selection'
    listbox = [
      {
        'listbox_key':self.start_requested_software_release.getUrl(),
        'computer_filter':[],
        'workflow_action':self.destroy_requested_software_release.getUrl()
      }
    ]
  
    self.software_product.SoftwareProduct_launchMassUpgrade(
        listbox,
        selection_name
      )
    self.tic()

    self.assertEqual(2,self.destroy_requested_software_release
      .SoftwareRelease_getUsage())
    self.assertEqual(0, self.start_requested_software_release\
      .SoftwareRelease_getUsage())
