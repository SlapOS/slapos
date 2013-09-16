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

class TestSlapOSMassUpgrade(testSlapOSMixin):
  def afterSetUp(self):
    super(TestSlapOSMassUpgrade, self).afterSetUp()
    self.new_id = self.generateNewId()

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
  
  def _makeSoftwareProduct(self, new_id):
    software_product = self.portal.software_product_module\
      .template_software_product.Base_createCloneDocument(batch_mode=1)
    software_product.edit(
      reference='TESTSOFTPROD-%s' % new_id,
      title='Test software product %s' % new_id
    )
    software_product.validate()

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

  def test_SoftwareProduct_getInstalledSoftwareReleaseList(self):
    computer = self._makeComputer(self.new_id)
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._makeSoftwareRelease(self.new_id)
    software_release.edit(aggregate_value = software_product.getRelativeUrl())
    self._makeSoftwareInstallation(self.new_id, computer,
      software_release.getUrlString())

    self.tic()
    self.assertEqual(
      len(software_product.SoftwareProduct_getInstalledSoftwareReleaseList()),
      1
    )

  def test_SoftwareProduct_getInstalledSoftwareReleaseList_no_installation(self):
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release = self._makeSoftwareRelease(self.new_id)
    software_release.edit(aggregate_value = software_product.getRelativeUrl())
    self.tic()

    self.assertEqual(
      len(software_product.SoftwareProduct_getInstalledSoftwareReleaseList()),
      0
    )
    
  def test_ComputerPartition_changeHostingSubscriptionSoftwareRelease(self):
    computer = self._makeComputer(self.new_id)
    self._makeComputerPartitions(computer)

    person = self._makePerson(self.new_id)
    host_sub = self._makeHostingSubscription(self.new_id)
    host_sub.edit(destination_section_value = person.getRelativeUrl())
    old_sr = self.generateNewSoftwareReleaseUrl()
    self._makeSoftwareInstance(host_sub,old_sr)
    instance = host_sub.getPredecessorValue()
    instance.edit(aggregate_value = computer.partition1.getRelativeUrl())
    self.tic()
    
    # Check setup
    self.assertEqual(old_sr, host_sub.getUrlString())

    slap_state = host_sub.getSlapState()

    new_sr = self.generateNewSoftwareReleaseUrl()

    computer.partition1.ComputerPartition_changeHostingSubscriptionSoftwareRelease(new_sr)

    # Check that url_string change, but slap state doesn't
    self.assertEqual(new_sr,host_sub.getUrlString())
    self.assertEqual(slap_state,host_sub.getSlapState())

  def test_ComputerPartition_changeHostingSubscriptionSoftwareRelease_instance_unallocated(self):
    computer = self._makeComputer(self.new_id)
    self._makeComputerPartitions(computer)

    person = self._makePerson(self.new_id)
    host_sub = self._makeHostingSubscription(self.new_id)
    host_sub.edit(destination_section_value = person.getRelativeUrl())
    old_sr = self.generateNewSoftwareReleaseUrl()
    self._makeSoftwareInstance(host_sub,old_sr)
    self.tic()
    
    # Check setup
    self.assertEqual(old_sr, host_sub.getUrlString())

    slap_state = host_sub.getSlapState()

    new_sr = self.generateNewSoftwareReleaseUrl()

    computer.partition1.ComputerPartition_changeHostingSubscriptionSoftwareRelease(new_sr)

    # Check that nothing change
    self.assertEqual(old_sr,host_sub.getUrlString())
    self.assertEqual(slap_state,host_sub.getSlapState())

  def _simulateComputerPartition_changeHostingSubscriptionSoftwareRelease(self):
    script_name = 'ComputerPartition_changeHostingSubscriptionSoftwareRelease'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by ComputerPartition_changeHostingSubscriptionSoftwareRelease') """ )
    transaction.commit()

  def _dropComputerPartition_changeHostingSubscriptionSoftwareRelease(self):
    script_name = 'ComputerPartition_changeHostingSubscriptionSoftwareRelease'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_SoftwareRelease_requestInstanceUpgrade(self):
    computer = self._makeComputer(self.new_id)
    self._makeComputerPartitions(computer)
    old_software_release = self._makeSoftwareRelease(self.new_id)
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub, old_software_release.getUrlString())
    instance = host_sub.getPredecessorValue()
    instance.edit(aggregate_value = computer.partition1.getRelativeUrl())
    computer.partition1.markBusy()
    self.tic()

    comp_reference_list = [computer.getReference()]
    
    self._simulateComputerPartition_changeHostingSubscriptionSoftwareRelease()
    try:
      old_software_release.SoftwareRelease_requestInstanceUpgrade(
          self.generateNewSoftwareReleaseUrl(),
          comp_reference_list,
          "Test SoftwareRelease_requestInstanceUpgrade %s" % self.new_id
      )
      self.tic()
    finally:
      self._dropComputerPartition_changeHostingSubscriptionSoftwareRelease()
 
    self.assertEqual('Visited by ComputerPartition_changeHostingSubscriptionSoftwareRelease',
      computer.partition1.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareRelease_requestInstanceUpgrade_partition_not_marked(self):
    computer = self._makeComputer(self.new_id)
    self._makeComputerPartitions(computer)
    old_software_release = self._makeSoftwareRelease(self.new_id)
    host_sub = self._makeHostingSubscription(self.new_id)
    self._makeSoftwareInstance(host_sub, old_software_release.getUrlString())
    instance = host_sub.getPredecessorValue()
    instance.edit(aggregate_value = computer.partition1.getRelativeUrl())
    self.tic()

    comp_reference_list = [computer.getReference()]
    
    self._simulateComputerPartition_changeHostingSubscriptionSoftwareRelease()
    try:
      old_software_release.SoftwareRelease_requestInstanceUpgrade(
          self.generateNewSoftwareReleaseUrl(),
          comp_reference_list,
          "Test SoftwareRelease_requestInstanceUpgrade %s" % self.new_id
      )
      self.tic()
    finally:
      self._dropComputerPartition_changeHostingSubscriptionSoftwareRelease()
 
    self.assertNotEqual('Visited by ComputerPartition_changeHostingSubscriptionSoftwareRelease',
      computer.partition1.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareRelease_requestInstanceUpgrade_no_instance(self):
    computer = self._makeComputer(self.new_id)
    self._makeComputerPartitions(computer)
    old_software_release = self._makeSoftwareRelease(self.new_id)
    computer.partition1.markBusy()
    self.tic()

    comp_reference_list = [computer.getReference()]
    
    self._simulateComputerPartition_changeHostingSubscriptionSoftwareRelease()
    try:
      old_software_release.SoftwareRelease_requestInstanceUpgrade(
          self.generateNewSoftwareReleaseUrl(),
          comp_reference_list,
          "Test SoftwareRelease_requestInstanceUpgrade %s" % self.new_id
      )
      self.tic()
    finally:
      self._dropComputerPartition_changeHostingSubscriptionSoftwareRelease()
 
    self.assertNotEqual('Visited by ComputerPartition_changeHostingSubscriptionSoftwareRelease',
      computer.partition1.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareRelease_requestInstanceUpgrade_no_computer(self):
    old_software_release = self._makeSoftwareRelease(self.new_id)

    comp_reference_list = []
    
    self._simulateComputerPartition_changeHostingSubscriptionSoftwareRelease()
    try:
      self.assertRaises(ValueError,old_software_release.SoftwareRelease_requestInstanceUpgrade,
          self.generateNewSoftwareReleaseUrl(),
          comp_reference_list,
          "Test SoftwareRelease_requestInstanceUpgrade %s" % self.new_id
      )
    finally:
      self._dropComputerPartition_changeHostingSubscriptionSoftwareRelease()

  def test_SoftwareRelease_requestInstanceUpgrade_no_new_sr(self):
    old_software_release = self._makeSoftwareRelease(self.new_id)
    computer = self._makeComputer(self.new_id)

    self.tic()
    comp_reference_list = [computer.getReference()]
    
    self._simulateComputerPartition_changeHostingSubscriptionSoftwareRelease()
    try:
      self.assertRaises(ValueError,old_software_release.SoftwareRelease_requestInstanceUpgrade,
          "",
          comp_reference_list,
          "Test SoftwareRelease_requestInstanceUpgrade %s" % self.new_id
      )
    finally:
      self._dropComputerPartition_changeHostingSubscriptionSoftwareRelease()

  def _simulateSoftwareRelease_requestInstanceUpgrade(self):
    script_name = 'SoftwareRelease_requestInstanceUpgrade'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context,action='edit_action', comment='Visited by SoftwareRelease_requestInstanceUpgrade') """ )
    transaction.commit()
    
  def _dropSoftwareRelease_requestInstanceUpgrade(self):
    script_name = 'SoftwareRelease_requestInstanceUpgrade'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_SoftwareProduct_launchMassUpgrade(self):
    computer = self._makeComputer(self.new_id)
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release1 = self._makeSoftwareRelease(self.new_id)
    software_release2 = self._makeSoftwareRelease(self.new_id)
    self.tic()
    selection_name = 'mass_upgrade_selection'
    listbox = [
      {
        'listbox_key':software_release1.getUrl(),
        'computer_filter':[computer.getReference()],
        'workflow_action':software_release2.getUrl()
      }
    ]

    self._simulateSoftwareRelease_requestInstanceUpgrade()
    try:
      software_product.SoftwareProduct_launchMassUpgrade(
          listbox,
          selection_name
      )
      self.tic()
    finally:
      self._dropSoftwareRelease_requestInstanceUpgrade()

    self.assertEqual('Visited by SoftwareRelease_requestInstanceUpgrade',
      software_release1.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareProduct_launchMassUpgrade_no_computer(self):
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release1 = self._makeSoftwareRelease(self.new_id)
    software_release2 = self._makeSoftwareRelease(self.new_id)
    self.tic()
    selection_name = 'mass_upgrade_selection'
    listbox = [
      {
        'listbox_key':software_release1.getUrl(),
        'computer_filter':[],
        'workflow_action':software_release2.getUrl()
      }
    ]

    self._simulateSoftwareRelease_requestInstanceUpgrade()
    try:
      software_product.SoftwareProduct_launchMassUpgrade(
          listbox,
          selection_name
      )
      self.tic()
    finally:
      self._dropSoftwareRelease_requestInstanceUpgrade()

    self.assertEqual('Visited by SoftwareRelease_requestInstanceUpgrade',
      software_release1.workflow_history['edit_workflow'][-1]['comment'])

  def test_SoftwareProduct_launchMassUpgrade_no_new_software_release(self):
    computer = self._makeComputer(self.new_id)
    software_product = self._makeSoftwareProduct(self.new_id)
    software_release1 = self._makeSoftwareRelease(self.new_id)
    self.tic()
    selection_name = 'mass_upgrade_selection'
    listbox = [
      {
        'listbox_key':software_release1.getUrl(),
        'computer_filter':[computer.getReference()],
        'workflow_action':""
      }
    ]

    self._simulateSoftwareRelease_requestInstanceUpgrade()
    try:
      software_product.SoftwareProduct_launchMassUpgrade(
          listbox,
          selection_name
      )
      self.tic()
    finally:
      self._dropSoftwareRelease_requestInstanceUpgrade()

    self.assertNotEqual('Visited by SoftwareRelease_requestInstanceUpgrade',
      software_release1.workflow_history['edit_workflow'][-1]['comment'])
