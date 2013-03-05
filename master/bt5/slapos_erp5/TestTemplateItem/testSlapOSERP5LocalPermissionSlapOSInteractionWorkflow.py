# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from testSlapOSERP5GroupRoleSecurity import TestSlapOSGroupRoleSecurityMixin
import transaction

class TestSlapOSLocalPermissionSlapOSInteractionWorkflow(
    TestSlapOSGroupRoleSecurityMixin):
  def _makePerson(self):
    new_id = self.generateNewId()
    self.person_user = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    self.person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
    )
    self.person_reference = self.person_user.getReference()

  def test_ComputerModel_edit(self):
    self._makePerson()
    model = self.portal.computer_model_module.newContent(
        portal_type='Computer Model')
    self.assertSecurityGroup(model, ['G-COMPANY', self.user_id], False)

    model.edit(source_administration=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(model,
        ['G-COMPANY', self.user_id, self.person_reference], False)

  def test_ComputerNetwork_edit(self):
    self._makePerson()
    network = self.portal.computer_network_module.newContent(
        portal_type='Computer Network')
    self.assertSecurityGroup(network, ['G-COMPANY', self.user_id,
        'R-SHADOW-PERSON'], False)

    network.edit(source_administration=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(network,
        ['G-COMPANY', self.user_id, self.person_reference, 'R-SHADOW-PERSON'],
        False)

  def test_Computer_setReference(self):
    computer = self.portal.computer_module.newContent(portal_type='Computer')
    self.assertSecurityGroup(computer, ['G-COMPANY', self.user_id], False)

    computer.edit(reference='TESTCOMP-%s' % self.generateNewId())
    transaction.commit()

    self.assertSecurityGroup(computer, ['G-COMPANY', self.user_id,
        computer.getReference()], False)

  def test_Computer_setSourceAdministration(self):
    self._makePerson()
    computer = self.portal.computer_module.newContent(
        portal_type='Computer')
    self.assertSecurityGroup(computer, ['G-COMPANY', self.user_id], False)

    computer.edit(source_administration=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(computer, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_Computer_setAllocationScope(self):
    computer = self.portal.computer_module.newContent(portal_type='Computer')
    self.assertSecurityGroup(computer, ['G-COMPANY', self.user_id], False)

    computer.edit(allocation_scope='open/public')
    transaction.commit()

    self.assertSecurityGroup(computer, ['G-COMPANY', self.user_id,
        'R-SHADOW-PERSON'], False)

  def test_Computer_setDestinationSection(self):
    self._makePerson()
    computer = self.portal.computer_module.newContent(
        portal_type='Computer')
    self.assertSecurityGroup(computer, ['G-COMPANY', self.user_id], False)

    computer.edit(source_administration=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(computer, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_Computer_reindexObject(self):
    computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    self.tic()
    comment = 'recursiveReindexObject triggered on reindexObject'
    def verify_recursiveReindexObject_call(self, *args, **kw):
      if self.getRelativeUrl() == computer.getRelativeUrl():
        if computer.workflow_history['edit_workflow'][-1]['comment'] != comment:
          computer.portal_workflow.doActionFor(computer, action='edit_action',
          comment=comment)
      else:
        return self.recursiveReindexObject_call(*args, **kw)

    # Replace recursiveReindexObject by a dummy method
    from Products.ERP5Type.Core.Folder import Folder
    Folder.recursiveReindexObject_call = Folder.recursiveReindexObject
    Folder.recursiveReindexObject = verify_recursiveReindexObject_call
    try:
      computer.reindexObject()
      self.tic()
    finally:
      Folder.recursiveReindexObject = Folder.recursiveReindexObject_call
    self.assertEqual(comment,
        computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_HostingSubscription_setReference(self):
    hosting_subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription')
    self.assertSecurityGroup(hosting_subscription, [self.user_id,
        hosting_subscription.getId(), 'G-COMPANY'],
        False)

    hosting_subscription.edit(reference='TESTHS-%s' % self.generateNewId())
    transaction.commit()

    self.assertSecurityGroup(hosting_subscription, [self.user_id,
        hosting_subscription.getReference(), 'G-COMPANY'], False)

  def test_HostingSubscription_setDestinationSection(self):
    self._makePerson()
    hosting_subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription')
    self.assertSecurityGroup(hosting_subscription, [self.user_id,
        hosting_subscription.getId(), 'G-COMPANY'],
        False)

    hosting_subscription.edit(
        destination_section=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(hosting_subscription, [self.user_id,
        hosting_subscription.getId(), self.person_user.getReference(),
        'G-COMPANY'],
        False)

  def test_Person_setReference(self):
    person = self.portal.person_module.newContent(portal_type='Person')
    self.assertSecurityGroup(person, [self.user_id, 'G-COMPANY'], False)

    person.edit(reference='TESTPER-%s' % self.generateNewId())
    transaction.commit()

    self.assertSecurityGroup(person, [self.user_id, 'G-COMPANY',
        person.getReference(), 'SHADOW-%s' % person.getReference()], False)

  def test_SoftwareInstallation_setAggregate(self):
    installation = self.portal.software_installation_module.newContent(
        portal_type='Software Installation')
    self.assertSecurityGroup(installation, [self.user_id, 'G-COMPANY'], False)

    computer = self.portal.computer_module.newContent(portal_type='Computer',
        reference='TESTC-%s' % self.generateNewId())

    installation.edit(aggregate=computer.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(installation, [self.user_id, 'G-COMPANY',
        computer.getReference()], False)


  def test_SoftwareInstallation_setDestinationSection(self):
    installation = self.portal.software_installation_module.newContent(
        portal_type='Software Installation')
    self.assertSecurityGroup(installation, [self.user_id, 'G-COMPANY'], False)

    self._makePerson()

    installation.edit(destination_section=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(installation, [self.user_id, 'G-COMPANY',
        self.person_user.getReference()], False)

  def test_SoftwareInstance_setSpecialise(self):
    software_instance = self.portal.software_instance_module.newContent(
        portal_type='Software Instance')
    self.assertSecurityGroup(software_instance, [self.user_id, 'G-COMPANY'],
        False)

    hosting_subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription', reference='TESTHS-%s' %
            self.generateNewId())
    software_instance.edit(specialise=hosting_subscription.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(software_instance, [self.user_id, 'G-COMPANY',
        hosting_subscription.getReference()], False)

  def test_SoftwareInstance_setAggregate(self):
    hosting_subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription', reference='TESTHS-%s' %
            self.generateNewId())
    software_instance = self.portal.software_instance_module.newContent(
        portal_type='Software Instance',
        specialise=hosting_subscription.getRelativeUrl())
    self.assertSecurityGroup(software_instance, [self.user_id, 'G-COMPANY',
        hosting_subscription.getReference()],
        False)

    computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    computer.edit(reference='TESTC-%s' % self.generateNewId())
    partition = computer.newContent(portal_type='Computer Partition')
    self.portal.portal_workflow._jumpToStateFor(partition, 'busy')
    self.assertSecurityGroup(partition, [self.user_id],
        True)
    software_instance.edit(aggregate=partition.getRelativeUrl())
    self.tic()

    self.assertSecurityGroup(software_instance, [self.user_id, 'G-COMPANY',
        computer.getReference(), hosting_subscription.getReference()], False)
    self.assertSecurityGroup(partition, [self.user_id,
        hosting_subscription.getReference()], True)

  def test_SlaveInstance_setSpecialise(self):
    slave_instance = self.portal.software_instance_module.newContent(
        portal_type='Slave Instance')
    self.assertSecurityGroup(slave_instance, [self.user_id, 'G-COMPANY'],
        False)

    hosting_subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription', reference='TESTHS-%s' %
            self.generateNewId())
    slave_instance.edit(specialise=hosting_subscription.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(slave_instance, [self.user_id, 'G-COMPANY',
        hosting_subscription.getReference()], False)

  def test_SlaveInstance_setAggregate(self):
    hosting_subscription = self.portal.hosting_subscription_module.newContent(
        portal_type='Hosting Subscription', reference='TESTHS-%s' %
            self.generateNewId())
    software_instance = self.portal.software_instance_module.newContent(
        portal_type='Software Instance',
        reference='TESTSO-%s' % self.generateNewId(),
        specialise=hosting_subscription.getRelativeUrl())
    software_instance.validate()
    slave_instance = self.portal.software_instance_module.newContent(
        portal_type='Slave Instance',
        specialise=hosting_subscription.getRelativeUrl())
    self.assertSecurityGroup(slave_instance, [self.user_id, 'G-COMPANY',
        hosting_subscription.getReference()],
        False)

    computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    computer.edit(reference='TESTC-%s' % self.generateNewId())
    partition = computer.newContent(portal_type='Computer Partition')
    software_instance.edit(aggregate=partition.getRelativeUrl())
    self.portal.portal_workflow._jumpToStateFor(partition, 'busy')
    self.tic()

    slave_instance.edit(aggregate=partition.getRelativeUrl())

    self.assertSecurityGroup(slave_instance, [self.user_id, 'G-COMPANY',
        software_instance.getReference(), computer.getReference(),
        hosting_subscription.getReference()], False)

  def test_PaymentTransaction_setDestinationSection(self):
    self._makePerson()
    payment_transaction = self.portal.accounting_module.newContent(
        portal_type='Payment Transaction')
    self.assertSecurityGroup(payment_transaction, [self.user_id,
        'G-COMPANY'],
        False)

    payment_transaction.edit(
        destination_section=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(payment_transaction, [self.user_id,
        'G-COMPANY', 'SHADOW-%s' % self.person_user.getReference(),
        self.person_user.getReference()],
        False)

  def test_PayzenEvent_setDestinationSection(self):
    self._makePerson()
    payment_transaction = self.portal.system_event_module.newContent(
        portal_type='Payzen Event')
    self.assertSecurityGroup(payment_transaction, [self.user_id,
        'G-COMPANY'],
        False)

    payment_transaction.edit(
        destination_section=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(payment_transaction, [self.user_id,
        'G-COMPANY', 'SHADOW-%s' % self.person_user.getReference()],
        False)

  def test_IntegrationSite_reindexObject(self):
    integration_site = self.portal.portal_integrations.newContent(
        portal_type="Integration Site")
    self.tic()
    comment = 'recursiveReindexObject triggered on reindexObject'
    def verify_recursiveReindexObject_call(self, *args, **kw):
      if self.getRelativeUrl() == integration_site.getRelativeUrl():
        if integration_site.workflow_history['edit_workflow'][-1]['comment'] != comment:
          integration_site.portal_workflow.doActionFor(integration_site, action='edit_action',
          comment=comment)
      else:
        return self.recursiveReindexObject_call(*args, **kw)

    # Replace recursiveReindexObject by a dummy method
    from Products.ERP5Type.Core.Folder import Folder
    Folder.recursiveReindexObject_call = Folder.recursiveReindexObject
    Folder.recursiveReindexObject = verify_recursiveReindexObject_call
    try:
      integration_site.reindexObject()
      self.tic()
    finally:
      Folder.recursiveReindexObject = Folder.recursiveReindexObject_call
    self.assertEqual(comment,
        integration_site.workflow_history['edit_workflow'][-1]['comment'])

  def test_SaleInvoiceTransaction_setDestinationSection(self):
    self._makePerson()
    sale_invoice_transaction = self.portal.accounting_module.newContent(
        portal_type='Sale Invoice Transaction')
    self.assertSecurityGroup(sale_invoice_transaction, [self.user_id,
        'G-COMPANY'],
        False)

    sale_invoice_transaction.edit(
        destination_section=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(sale_invoice_transaction, [self.user_id,
        'G-COMPANY', self.person_user.getReference()],
        False)

  def test_SupportRequest_setDestinationDecision(self):
    self._makePerson()
    support_request = self.portal.support_request_module.newContent(
        portal_type='Support Request')
    self.assertSecurityGroup(support_request, ['G-COMPANY', self.user_id], False)

    support_request.edit(destination_decision=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(support_request, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_RegularisationRequest_setDestinationDecision(self):
    self._makePerson()
    regularisation_request = self.portal.regularisation_request_module.newContent(
        portal_type='Regularisation Request')
    self.assertSecurityGroup(regularisation_request, ['G-COMPANY', self.user_id], False)

    regularisation_request.edit(destination_decision=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(regularisation_request, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_Acknowledgement_setDestination(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Acknowledgement')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(destination=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_Acknowledgement_setSource(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Acknowledgement')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(source=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_FaxMessage_setDestination(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Fax Message')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(destination=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_FaxMessage_setSource(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Fax Message')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(source=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_Letter_setDestination(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Letter')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(destination=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_Letter_setSource(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Letter')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(source=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_MailMessage_setDestination(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Mail Message')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(destination=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_MailMessage_setSource(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Mail Message')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(source=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_Note_setDestination(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Note')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(destination=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_Note_setSource(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Note')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(source=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_PhoneCall_setDestination(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Phone Call')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(destination=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_PhoneCall_setSource(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Phone Call')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(source=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_ShortMessage_setDestination(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Short Message')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(destination=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_ShortMessage_setSource(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Short Message')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(source=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_SiteMessage_setDestination(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Site Message')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(destination=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_SiteMessage_setSource(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Site Message')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(source=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_Visit_setDestination(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Visit')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(destination=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_Visit_setSource(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Visit')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(source=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_WebMessage_setDestination(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Web Message')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(destination=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_WebMessage_setSource(self):
    self._makePerson()
    event = self.portal.event_module.newContent(
        portal_type='Web Message')
    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id], False)

    event.edit(source=self.person_user.getRelativeUrl())
    transaction.commit()

    self.assertSecurityGroup(event, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_SalePackingList_setSpecialise(self):
    self._makePerson()
    sale_packing_list = self.portal.sale_packing_list_module.newContent(
      destination_decision_value=self.person_user,  
      portal_type='Sale Packing List')
    self.assertSecurityGroup(sale_packing_list, ['G-COMPANY', self.user_id], False)

    sale_packing_list.edit(
      specialise="sale_trade_condition_module/slapos_subscription_trade_condition")
    transaction.commit()

    self.assertSecurityGroup(sale_packing_list, ['G-COMPANY', self.user_id,
        self.person_reference], False)

  def test_SalePackingList_setDestinationDecision(self):
    self._makePerson()
    sale_packing_list = self.portal.sale_packing_list_module.newContent(
      specialise="sale_trade_condition_module/slapos_subscription_trade_condition",
      portal_type='Sale Packing List')
    self.assertSecurityGroup(sale_packing_list, ['G-COMPANY', self.user_id], False)

    sale_packing_list.edit(
      destination_decision_value=self.person_user)
    transaction.commit()

    self.assertSecurityGroup(sale_packing_list, ['G-COMPANY', self.user_id,
        self.person_reference], False)
