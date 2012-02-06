from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from Products.DCWorkflow.DCWorkflow import ValidationFailed
from random import random
from slapos import slap
from zExceptions import Unauthorized
from DateTime import DateTime
from Products.ERP5Type.tests.backportUnittest import skip

class TestVifibSlapComputerPartitionLock(TestVifibSlapWebServiceMixin):

  def stepCheckPersonPaymentState(self, sequence, **kw):
    """
    Check that person payment state is the same than slap state
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    self.assertEquals('open_order_created', person.getSlapState())
    self.assertEquals(person.getSlapState(), person.getPaymentState())

  @skip('Dropped implementation')
  def test_person_payment_state(self):
    """Person payment state value is the same than slap state
    """
    sequence_list = SequenceList()
    sequence_string = '\
      LoginDefaultUser \
      CheckPersonPaymentState \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckPersonLockedState(self, sequence, **kw):
    """
    Check that person slap state is locked
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    self.assertEquals('locked', person.getSlapState())

  def stepCheckPersonUnlockedState(self, sequence, **kw):
    """
    Check that person slap state is unlocked
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    self.assertEquals('unlocked', person.getSlapState())

  def stepCheckPersonUnlimitedState(self, sequence, **kw):
    """
    Check that person slap state is unlimited
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    self.assertEquals('unlimited', person.getSlapState())

  register_new_user_sequence_string = '\
      Logout \
      RequestCredentialFromWebSite \
      Tic \
      LoginDefaultUser \
      SubmitCredentialRequest \
      Tic \
      AcceptSubmittedCredentialsActiveSense \
      Tic \
      Logout \
      '

  create_new_user_instance_sequence_string = '\
      LoginWebUser \
      PersonRequestSoftwareInstance \
      Tic \
      Logout \
      \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      SetSelectedComputerPartition \
      SelectCurrentlyUsedSalePackingListUid \
      Logout \
      '

  create_new_user_slave_instance_sequence_string = '\
      LoginWebUser \
      PersonRequestSlaveInstance \
      Tic \
      Logout \
      \
      LoginDefaultUser \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      SetSelectedComputerPartition \
      SelectCurrentlyUsedSalePackingListUid \
      Logout \
      '

  @skip('Dropped implementation')
  def test_person_locked_by_default(self):
    """Newly registered customer are locked by default
    """
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      LoginWebUser \
      CheckPersonLockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepPersonRequestIsForbidden(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    software_release = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_release_uid'])
    software_title = sequence.get('software_title',
      self.id() + str(random()))

    self.assertRaises(Unauthorized, person.requestSoftwareInstance,
      software_release=software_release.getUrlString(),
      software_title=software_title,
      instance_xml=self.minimal_correct_xml,
      sla_xml=sequence.get('sla_xml'),
      **kw)

  def stepSoftwareInstanceSaleOrderConfirmRaisesUnauthorized(self, sequence,
    **kw):
    """Checks that current software instance is realted only with sale order
    
    and that this sale order cannot be confirmed because of Unauthorized
    
    It means that user has bad balance."""
    software_instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])

    aggregate_value_list = software_instance.getAggregateRelatedValueList(
        portal_type=[self.sale_packing_list_line_portal_type,
        self.sale_order_line_portal_type])

    self.assertEqual(1, len(aggregate_value_list))
    self.assertTrue(self.sale_order_line_portal_type in [q.getPortalType() for\
        q in aggregate_value_list])
    sale_order_line = aggregate_value_list[0]
    sale_order = sale_order_line.getParentValue()

    self.assertRaises(Unauthorized, sale_order.confirm)

  def stepAssertNoComputerPartition(self, sequence, **kw):
    """Sets in sequence computer partition parameters related to current
    software instance"""
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    delivery_line_list = [q for q in software_instance
        .getAggregateRelatedValueList(
          portal_type=self.sale_packing_list_line_portal_type)]
    self.assertEqual(0, len(delivery_line_list))

  def test_negative_person_balance_request(self):
    """Locked person can not request
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_installed_software_release_sequence_string + \
      self.register_new_user_sequence_string \
      + self.lock_user_string() + '\
      LoginWebUser \
      PersonRequestSoftwareInstance \
      Tic \
      Logout \
      \
      LoginDefaultUser \
      SoftwareInstanceSaleOrderConfirmRaisesUnauthorized \
      ConfirmOrderedSaleOrderActiveSense \
      Tic \
      AssertNoComputerPartition \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepTriggerUnlockPersonAlarm(self, sequence, **kw):
    """
    Trigger global person unlocking
    """
    self.portal.portal_alarms.vifib_unlock_person.activeSense()

  def stepTriggerLockPersonAlarm(self, sequence, **kw):
    """
    Trigger global person locking
    """
    self.portal.portal_alarms.vifib_lock_person.activeSense()

  def stepUnlimitPerson(self, sequence, **kw):
    """
    Unlimit user access
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    person.unlimit()

  @skip('Dropped implementation')
  def test_automated_person_without_payment_unlocking(self):
    """Test that a person is automatically unlocked by an alarm if no payment
    """
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonUnlockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_automated_person_without_payment_not_locking(self):
    """Test that a person is not automatically locked by an alarm if no payment
    """
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonUnlockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      TriggerLockPersonAlarm \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonUnlockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCreateSmallInvoiceWebUser(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    invoice = self.portal.accounting_module.newContent(
      portal_type='Sale Invoice Transaction',
      start_date=DateTime(),
      resource='currency_module/EUR',
      source_section='organisation_module/vifib_internet',
      source='organisation_module/vifib_internet',
      destination_section=person.getRelativeUrl(),
      destination=person.getRelativeUrl(),
      specialise='sale_trade_condition_module/vifib_trade_condition'
    )
    invoice.newContent(
      portal_type='Invoice Line',
      resource=self.portal.portal_preferences.getPreferredRegistrationResource(),
      quantity=1,
      price=1
    )
    sequence['invoice'] = invoice

  def stepPlanInvoice(self, sequence, **kw):
    sequence['invoice'].plan()

  def stepConfirmInvoice(self, sequence, **kw):
    sequence['invoice'].confirm()

  def stepStartInvoice(self, sequence, **kw):
    sequence['invoice'].start()

  def stepCheckWebUserBalanceHighAmount(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    self.assertEqual(-10000.0,
      self.portal.portal_simulation.getInventoryAssetPrice(
      node_category='account_type/asset/receivable',
      simulation_state=['started', 'stopped', 'delivered'],
      section_uid=self.portal.restrictedTraverse(
        'organisation_module/vifib_internet').getUid(),
      mirror_section_uid=person.getUid())
    )

  def stepCheckWebUserBalanceSmallAmount(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    self.assertEqual(-1.0,
      self.portal.portal_simulation.getInventoryAssetPrice(
      node_category='account_type/asset/receivable',
      simulation_state=['started', 'stopped', 'delivered'],
      section_uid=self.portal.restrictedTraverse(
        'organisation_module/vifib_internet').getUid(),
      mirror_section_uid=person.getUid())
    )

  create_small_registration_fee_invoice = """
    LoginERP5TypeTestCase
    CreateSmallInvoiceWebUser
    Tic
    PlanInvoice
    Tic
    ConfirmInvoice
    StartInvoice
    Tic
    CheckWebUserBalanceSmallAmount
    Logout
  """

  @skip('Dropped implementation')
  def test_automated_person_small_not_paid_not_locking(self):
    """Test that a person is not automatically locked by an alarm if
    recent small payment is not paid yet
    """
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonUnlockedState \
      Tic \
      Logout \
      ' + self.create_small_registration_fee_invoice + '\
      TriggerLockPersonAlarm \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonUnlockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCreatePastSmallPayment(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    payment_transaction = self.portal.accounting_module.newContent(
        destination_section='organisation_module/vifib_internet',
        source_section=person.getRelativeUrl(),
        resource='currency_module/EUR',
        portal_type="Payment Transaction",
        start_date=DateTime()-90,
        )
    payment_transaction.newContent(
        portal_type="Accounting Transaction Line",
        quantity=1,
        destination='account_module/receivable',
        )
    payment_transaction.newContent(
        portal_type="Accounting Transaction Line",
        quantity=-1,
        destination='account_module/sales',
        )
    payment_transaction.confirm()
    payment_transaction.checkConsistency()

    sequence['payment_transaction'] = payment_transaction

  def stepCancelPayment(self, sequence, **kw):
    sequence['payment_transaction'].cancel()

  def stepStartPayment(self, sequence, **kw):
    sequence['payment_transaction'].start()

  def stepStopPayment(self, sequence, **kw):
    sequence['payment_transaction'].stop()

  def stepDeliverPayment(self, sequence, **kw):
    sequence['payment_transaction'].deliver()

  @skip('Dropped implementation')
  def test_automated_person_past_not_paid_locking(self):
    """Test that a person is automatically locked by an alarm if payment has
    not been done for a long time.
    """
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonUnlockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CreatePastSmallPayment \
      Tic \
      Logout \
      \
      TriggerLockPersonAlarm \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonLockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_automated_unlimited_person_past_not_paid_locking(self):
    """Test that an unlimited person is automatically locked by 
    an alarm if payment has not been done for a long time.
    """
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      UnlimitPerson \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonUnlimitedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CreatePastSmallPayment \
      Tic \
      Logout \
      \
      TriggerLockPersonAlarm \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonLockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCreateHighBalanceInvoiceWebUser(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    invoice = self.portal.accounting_module.newContent(
      portal_type='Sale Invoice Transaction',
      start_date=DateTime(),
      resource='currency_module/EUR',
      source_section='organisation_module/vifib_internet',
      source='organisation_module/vifib_internet',
      destination_section=person.getRelativeUrl(),
      destination=person.getRelativeUrl(),
      specialise='sale_trade_condition_module/vifib_trade_condition'
    )
    invoice.newContent(
      portal_type='Invoice Line',
      resource=self.portal.portal_preferences.getPreferredRegistrationResource(),
      quantity=1,
      price=10000
    )
    sequence['invoice'] = invoice

  @skip('Dropped implementation')
  def test_automated_person_high_not_paid_locking(self):
    """Test that a person is automatically locked by an alarm if payment has
    an high quantity
    """
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonUnlockedState \
      Tic \
      Logout \
      ' + self.lock_user_string() + '\
      LoginWebUser \
      CheckPersonLockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_automated_unlimited_person_high_not_paid_locking(self):
    """Test that an unlimited person is automatically locked by 
    an alarm if payment has an high quantity
    """
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      UnlimitPerson \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonUnlimitedState \
      Tic \
      Logout \
      ' + self.lock_user_string() + '\
      LoginWebUser \
      CheckPersonLockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_automated_person_with_ongoing_payment_unlocking(self):
    """Test that a person is can not be unlocked if there is an ongoing
    payment.
    Unlocking alarm doesn't have to know why user is locked.
    """
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      \
      LoginERP5TypeTestCase \
      CreatePastSmallPayment \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonLockedState \
      Logout \
      \
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonLockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_automated_person_with_delivered_payment_unlocking(self):
    """Test that a person is can be unlocked if payment are delivered
    """
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      \
      LoginERP5TypeTestCase \
      CreatePastSmallPayment \
      Tic \
      StartPayment \
      StopPayment \
      DeliverPayment \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonLockedState \
      Logout \
      \
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonUnlockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_automated_person_with_cancelled_payment_unlocking(self):
    """Test that a person is can be unlocked if payment are cancelled
    """
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      \
      LoginERP5TypeTestCase \
      CreatePastSmallPayment \
      Tic \
      CancelPayment \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonLockedState \
      Logout \
      \
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      \
      LoginWebUser \
      CheckPersonUnlockedState \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckInstanceLocked(self, sequence, **kw):
    instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])
    self.assertEqual('locked', instance.getSlapState())

  def stepCheckInstanceNotLocked(self, sequence, **kw):
    instance = self.portal.portal_catalog.getResultValue(
      uid=sequence['software_instance_uid'])
    self.assertNotEqual('locked', instance.getSlapState())

  @skip('Dropped implementation')
  def test_automated_software_instance_unlock(self):
    """Locked person's instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_installed_software_release_sequence_string + \
      self.register_new_user_sequence_string + '\
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      ' + \
      self.create_new_user_instance_sequence_string + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      \
      DeliverPayment \
      Tic \
      CheckInstanceUnlocked \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepInstanceRequestIsForbidden(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])
    kw = dict(software_release=sequence['software_release_uri'],
      software_type=sequence.get('requested_software_type',
                                 'requested_software_type'),
      partition_reference=sequence.get('requested_reference',
        'requested_reference'),
      partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
      filter_kw=sequence.get('requested_filter_dict', {}),
      state=sequence.get('instance_state'))

    self.assertRaises(slap.Unauthorized, slap_computer_partition.request, **kw)

  def new_software_instance_string(self):
    return \
      self.prepare_installed_software_release_sequence_string + \
      self.register_new_user_sequence_string + '\
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      ' + \
      self.create_new_user_instance_sequence_string

  def new_slave_instance_string(self):
    return \
      self.prepare_installed_computer_partition_sequence_string + \
      self.register_new_user_sequence_string + '\
      LoginERP5TypeTestCase \
      TriggerUnlockPersonAlarm \
      Tic \
      Logout \
      ' + \
      self.create_new_user_slave_instance_sequence_string

  def lock_user_string(self):
    return '\
      LoginERP5TypeTestCase \
      CreateHighBalanceInvoiceWebUser \
      Tic \
      PlanInvoice \
      Tic \
      ConfirmInvoice \
      StartInvoice \
      Tic \
      CheckWebUserBalanceHighAmount \
      TriggerLockPersonAlarm \
      Tic \
      Logout \
        '

  @skip('Dropped implementation')
  def test_locked_instance_request(self):
    """Locked person's instance can not request
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_software_instance_string() + \
      self.lock_user_string() + '\
      \
      SlapLoginCurrentSoftwareInstance \
      InstanceRequestIsForbidden \
      SlapLogout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_software_instance_requested(self):
    """Locked person's requested instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_software_instance_string() + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_software_instance_building(self):
    """Locked person's building instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_software_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SlapLogout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_software_instance_installed(self):
    """Locked person's installed instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_software_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SoftwareInstanceAvailable \
      Tic \
      SlapLogout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_software_instance_starting(self):
    """Locked person's starting instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_software_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SoftwareInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSoftwareInstanceStart \
      Tic \
      Logout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_software_instance_started(self):
    """Locked person's started instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_software_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SoftwareInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSoftwareInstanceStart \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_software_instance_stopping(self):
    """Locked person's stopping instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_software_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SoftwareInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSoftwareInstanceStart \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSoftwareInstanceStop \
      Tic \
      Logout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_software_instance_stopped(self):
    """Locked person's stopped instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_software_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SoftwareInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSoftwareInstanceStart \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSoftwareInstanceStop \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStopped \
      Tic \
      SlapLogout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_software_instance_update(self):
    """Locked person's updated instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_software_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SoftwareInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSoftwareInstanceStart \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSoftwareInstanceUpdate \
      Tic \
      Logout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_software_instance_destroying(self):
    """Locked person's destroying instance are not automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_software_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SoftwareInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSoftwareInstanceStart \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSoftwareInstanceDestroy \
      Tic \
      Logout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceNotLocked \
      CheckDestroyedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_software_instance_destroyed(self):
    """Locked person's destroyed instance are not automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_software_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceBuilding \
      Tic \
      SoftwareInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSoftwareInstanceStart \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSoftwareInstanceDestroy \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceDestroyed \
      Tic \
      SlapLogout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceNotLocked \
      CheckDestroyedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_software_instance_can_be_destroyed(self):
    """Locked person's instance can be destroyed
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_software_instance_string() + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginWebUser \
      RequestSoftwareInstanceDestroy \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckInstanceNotLocked \
      CheckDestroyedComputerPartitionGetStateCall \
      Logout \
      \
      SlapLoginCurrentComputer \
      SoftwareInstanceDestroyed \
      Tic \
      SlapLogout \
      \
      LoginERP5TypeTestCase \
      CheckInstanceNotLocked \
      CheckDestroyedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_slave_instance_requested(self):
    """Locked person's requested instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_slave_instance_string() + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_slave_instance_building(self):
    """Locked person's building instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_slave_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SlaveInstanceBuilding \
      Tic \
      SlapLogout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_slave_instance_installed(self):
    """Locked person's installed instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_slave_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SlaveInstanceBuilding \
      Tic \
      SlaveInstanceAvailable \
      Tic \
      SlapLogout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_slave_instance_starting(self):
    """Locked person's starting instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_slave_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SlaveInstanceBuilding \
      Tic \
      SlaveInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSlaveInstanceStart \
      Tic \
      Logout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_slave_instance_started(self):
    """Locked person's started instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_slave_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SlaveInstanceBuilding \
      Tic \
      SlaveInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSlaveInstanceStart \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SlaveInstanceStarted \
      Tic \
      SlapLogout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_slave_instance_stopping(self):
    """Locked person's stopping instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_slave_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SlaveInstanceBuilding \
      Tic \
      SlaveInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSlaveInstanceStart \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SlaveInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSlaveInstanceStop \
      Tic \
      Logout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_slave_instance_stopped(self):
    """Locked person's stopped instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_slave_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SlaveInstanceBuilding \
      Tic \
      SlaveInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSlaveInstanceStart \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SlaveInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSlaveInstanceStop \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SlaveInstanceStopped \
      Tic \
      SlapLogout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_slave_instance_update(self):
    """Locked person's updated instance are automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_slave_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SlaveInstanceBuilding \
      Tic \
      SlaveInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSlaveInstanceStart \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SlaveInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSlaveInstanceUpdate \
      Tic \
      Logout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_slave_instance_destroying(self):
    """Locked person's destroying instance are not automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_slave_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SlaveInstanceBuilding \
      Tic \
      SlaveInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSlaveInstanceStart \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SlaveInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSlaveInstanceDestroy \
      Tic \
      Logout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceNotLocked \
      CheckDestroyedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_slave_instance_destroyed(self):
    """Locked person's destroyed instance are not automatically locked
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_slave_instance_string() + '\
      \
      SlapLoginCurrentComputer \
      SlaveInstanceBuilding \
      Tic \
      SlaveInstanceAvailable \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSlaveInstanceStart \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SlaveInstanceStarted \
      Tic \
      SlapLogout \
      \
      LoginWebUser \
      RequestSlaveInstanceDestroy \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      SlaveInstanceDestroyed \
      Tic \
      SlapLogout \
      ' + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceNotLocked \
      CheckDestroyedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Dropped implementation')
  def test_lock_slave_instance_can_be_destroyed(self):
    """Locked person's instance can be destroyed
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.new_slave_instance_string() + \
      self.lock_user_string() + '\
      LoginERP5TypeTestCase \
      CheckInstanceLocked \
      CheckStoppedComputerPartitionGetStateCall \
      Logout \
      \
      LoginWebUser \
      RequestSlaveInstanceDestroy \
      Tic \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckInstanceNotLocked \
      CheckDestroyedComputerPartitionGetStateCall \
      Logout \
      \
      SlapLoginCurrentComputer \
      SlaveInstanceDestroyed \
      Tic \
      SlapLogout \
      \
      LoginERP5TypeTestCase \
      CheckInstanceNotLocked \
      CheckDestroyedComputerPartitionGetStateCall \
      Logout \
      \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionLock))
  return suite
