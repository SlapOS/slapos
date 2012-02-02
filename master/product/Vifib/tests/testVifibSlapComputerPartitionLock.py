from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from Products.DCWorkflow.DCWorkflow import ValidationFailed
from random import random
from slapos import slap
from AccessControl import Unauthorized
from DateTime import DateTime

class TestVifibSlapComputerPartitionLock(TestVifibSlapWebServiceMixin):

  def stepCheckPersonPaymentState(self, sequence, **kw):
    """
    Check that person payment state is the same than slap state
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    self.assertEquals('open_order_created', person.getSlapState())
    self.assertEquals(person.getSlapState(), person.getPaymentState())

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
    Check that person payment state is the same than slap state
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    self.assertEquals('locked', person.getSlapState())

  def stepCheckPersonUnlockedState(self, sequence, **kw):
    """
    Check that person payment state is the same than slap state
    """
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    self.assertEquals('unlocked', person.getSlapState())

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

  def test_locked_person_request(self):
    """Locked person can not request
    """
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_installed_software_release_sequence_string + \
      self.register_new_user_sequence_string + '\
      LoginWebUser \
      CheckPersonLockedState \
      PersonRequestIsForbidden \
      Tic \
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

  def stepCreateSmallPayment(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    payment_transaction = self.portal.accounting_module.newContent(
        source_section='organisation_module/vifib_internet',
        destination_section=person.getRelativeUrl(),
        resource='currency_module/EUR',
        portal_type="Payment Transaction",
        start_date=DateTime(),
        # XXX More info needed
        )
    payment_transaction.newContent(
        portal_type="Accounting Transaction Line",
        quantity=1,
        source='account_module/receivable',
        )
    payment_transaction.newContent(
        portal_type="Accounting Transaction Line",
        quantity=-1,
        source='account_module/sales',
        )
    payment_transaction.confirm()
    # XXX More info needed
    payment_transaction.checkConsistency()

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
        source_section='organisation_module/vifib_internet',
        destination_section=person.getRelativeUrl(),
        resource='currency_module/EUR',
        portal_type="Payment Transaction",
        start_date=DateTime()-90,
        # XXX More info needed
        )
    payment_transaction.newContent(
        portal_type="Accounting Transaction Line",
        quantity=1,
        source='account_module/receivable',
        )
    payment_transaction.newContent(
        portal_type="Accounting Transaction Line",
        quantity=-1,
        source='account_module/sales',
        )
    payment_transaction.confirm()
    # XXX More info needed
    payment_transaction.checkConsistency()

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
      CreatePastNotPaidPayment \
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

  def stepCreateHighBalanceNotPaidPayment(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(sequence[
      'web_user'])
    payment_transaction = self.portal.accounting_module.newContent(
        source_section='organisation_module/vifib_internet',
        destination_section=person.getRelativeUrl(),
        resource='currency_module/EUR',
        portal_type="Payment Transaction",
        start_date=DateTime(),
        # XXX More info needed
        )
    payment_transaction.newContent(
        portal_type="Accounting Transaction Line",
        quantity=10000,
        source='account_module/receivable',
        )
    payment_transaction.newContent(
        portal_type="Accounting Transaction Line",
        quantity=-10000,
        source='account_module/sales',
        )
    payment_transaction.confirm()
    # XXX More info needed
    payment_transaction.checkConsistency()

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
      \
      LoginERP5TypeTestCase \
      CreateHighBalanceNotPaidPayment \
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

  def test_automated_person_with_delivered_payment_unlocking(self):
    """Test that a person is can be unlocked if payment are delivered
    """
    sequence_list = SequenceList()
    sequence_string = self.register_new_user_sequence_string + '\
      \
      LoginERP5TypeTestCase \
      CreatePastSmallPayment \
      Tic \
      DeliverPayment \
      Tic \
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
      self.create_new_user_instance_sequence_string + '\
      LoginERP5TypeTestCase \
      CreateHighBalanceNotPaidPayment \
      Tic \
      \
      TriggerLockPersonAlarm \
      Tic \
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
      CreateHighBalanceNotPaidPayment \
      Tic \
      \
      TriggerLockPersonAlarm \
      Tic \
      Logout \
        '

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
