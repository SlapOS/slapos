# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from Products.ERP5Type.tests.utils import createZODBPythonScript
from Products.ERP5Type.tests.backportUnittest import skip
import json
from DateTime import DateTime

class TestSlapOSPayzenUpdateConfirmedPayment(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def _simulatePaymentTransaction_startPayzenPayment(self):
    script_name = 'PaymentTransaction_startPayzenPayment'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by PaymentTransaction_startPayzenPayment') """ )
    transaction.commit()

  def _dropPaymentTransaction_startPayzenPayment(self):
    script_name = 'PaymentTransaction_startPayzenPayment'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_confirmed_draft_payzen(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'confirmed')
    self.tic()

    self._simulatePaymentTransaction_startPayzenPayment()
    try:
      self.portal.portal_alarms.slapos_payzen_update_confirmed_payment.activeSense()
      self.tic()
    finally:
      self._dropPaymentTransaction_startPayzenPayment()
    self.tic()
    self.assertEqual(
        'Visited by PaymentTransaction_startPayzenPayment',
        transaction.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_confirmed(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      )
    self.tic()

    self._simulatePaymentTransaction_startPayzenPayment()
    try:
      self.portal.portal_alarms.slapos_payzen_update_confirmed_payment.activeSense()
      self.tic()
    finally:
      self._dropPaymentTransaction_startPayzenPayment()
    self.tic()
    self.assertNotEqual(
        'Visited by PaymentTransaction_startPayzenPayment',
        transaction.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_draft(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'confirmed')
    self.portal.portal_workflow._jumpToStateFor(transaction, 'solved')
    self.tic()

    self._simulatePaymentTransaction_startPayzenPayment()
    try:
      self.portal.portal_alarms.slapos_payzen_update_confirmed_payment.activeSense()
      self.tic()
    finally:
      self._dropPaymentTransaction_startPayzenPayment()
    self.tic()
    self.assertNotEqual(
        'Visited by PaymentTransaction_startPayzenPayment',
        transaction.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_payzen(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'confirmed')
    self.tic()

    self._simulatePaymentTransaction_startPayzenPayment()
    try:
      self.portal.portal_alarms.slapos_payzen_update_confirmed_payment.activeSense()
      self.tic()
    finally:
      self._dropPaymentTransaction_startPayzenPayment()
    self.tic()
    self.assertNotEqual(
        'Visited by PaymentTransaction_startPayzenPayment',
        transaction.workflow_history['edit_workflow'][-1]['comment'])

  def _simulatePaymentTransaction_getTotalPayablePrice(self):
    script_name = 'PaymentTransaction_getTotalPayablePrice'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""return 1""")
    transaction.commit()

  def _simulatePaymentTransaction_getZeroTotalPayablePrice(self):
    script_name = 'PaymentTransaction_getTotalPayablePrice'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""return 0""")
    transaction.commit()

  def _dropPaymentTransaction_getTotalPayablePrice(self):
    script_name = 'PaymentTransaction_getTotalPayablePrice'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_not_confirmed_payment(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      )
    simulation_state = transaction.getSimulationState()
    modification_date = transaction.getModificationDate()
    self._simulatePaymentTransaction_getTotalPayablePrice()
    try:
      transaction.PaymentTransaction_startPayzenPayment()
    finally:
      self._dropPaymentTransaction_getTotalPayablePrice()
    self.assertEquals(transaction.getSimulationState(), simulation_state)
    self.assertEquals(transaction.getModificationDate(), modification_date)

  def test_not_payzen_payment(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'confirmed')
    simulation_state = transaction.getSimulationState()
    modification_date = transaction.getModificationDate()
    self._simulatePaymentTransaction_getTotalPayablePrice()
    try:
      transaction.PaymentTransaction_startPayzenPayment()
    finally:
      self._dropPaymentTransaction_getTotalPayablePrice()
    self.assertEquals(transaction.getSimulationState(), simulation_state)
    self.assertEquals(transaction.getModificationDate(), modification_date)

  def test_zero_amount_payment(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'confirmed')
    simulation_state = transaction.getSimulationState()
    modification_date = transaction.getModificationDate()

    self._simulatePaymentTransaction_getZeroTotalPayablePrice()
    try:
      transaction.PaymentTransaction_startPayzenPayment()
    finally:
      self._dropPaymentTransaction_getTotalPayablePrice()
    self.assertEquals(transaction.getSimulationState(), simulation_state)
    self.assertEquals(transaction.getModificationDate(), modification_date)

  def _simulatePaymentTransaction_sendManualPayzenPaymentUrl(self):
    script_name = 'PaymentTransaction_sendManualPayzenPaymentUrl'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by PaymentTransaction_sendManualPayzenPaymentUrl') """ )
    transaction.commit()

  def _dropPaymentTransaction_sendManualPayzenPaymentUrl(self):
    script_name = 'PaymentTransaction_sendManualPayzenPaymentUrl'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_expected_payment(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'confirmed')

    self._simulatePaymentTransaction_sendManualPayzenPaymentUrl()
    self._simulatePaymentTransaction_getTotalPayablePrice()
    try:
      transaction.PaymentTransaction_startPayzenPayment()
    finally:
      self._dropPaymentTransaction_sendManualPayzenPaymentUrl()
      self._dropPaymentTransaction_getTotalPayablePrice()
    self.assertEquals(transaction.getSimulationState(), 'started')
    self.assertEqual(
        'Visited by PaymentTransaction_sendManualPayzenPaymentUrl',
        transaction.workflow_history['edit_workflow'][-1]['comment'])


class TestSlapOSPayzenUpdateStartedPayment(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def test_not_started_payment(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      )
    simulation_state = transaction.getSimulationState()
    modification_date = transaction.getModificationDate()
    transaction.PaymentTransaction_updateStatus()
    self.assertEquals(transaction.getSimulationState(), simulation_state)
    self.assertEquals(transaction.getModificationDate(), modification_date)

  def test_not_payzen_payment(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'started')
    simulation_state = transaction.getSimulationState()
    modification_date = transaction.getModificationDate()
    transaction.PaymentTransaction_updateStatus()
    self.assertEquals(transaction.getSimulationState(), simulation_state)
    self.assertEquals(transaction.getModificationDate(), modification_date)

  def _simulatePaymentTransaction_addPayzenTicket(self):
    script_name = 'PaymentTransaction_addPayzenTicket'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by PaymentTransaction_addPayzenTicket') """ )
    transaction.commit()

  def _dropPaymentTransaction_addPayzenTicket(self):
    script_name = 'PaymentTransaction_addPayzenTicket'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_not_registered_payment(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'started')

    self._simulatePaymentTransaction_addPayzenTicket()
    try:
      transaction.PaymentTransaction_updateStatus()
    finally:
      self._dropPaymentTransaction_addPayzenTicket()
    self.assertEquals(transaction.getSimulationState(), 'started')
    self.assertEqual(
        'Visited by PaymentTransaction_addPayzenTicket',
        transaction.workflow_history['edit_workflow'][-1]['comment'])

  def _simulatePaymentTransaction_createPaidPayzenEvent(self):
    script_name = 'PaymentTransaction_createPayzenEvent'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by PaymentTransaction_createPayzenEvent')

class Foo:
  def updateStatus(self):
    context.stop()
return Foo()
""" )
    transaction.commit()

  def _simulatePaymentTransaction_createNotPaidPayzenEvent(self):
    script_name = 'PaymentTransaction_createPayzenEvent'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by PaymentTransaction_createPayzenEvent')

class Foo:
  def updateStatus(self):
    pass
return Foo()
""" )
    transaction.commit()

  def _dropPaymentTransaction_createPayzenEvent(self):
    script_name = 'PaymentTransaction_createPayzenEvent'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_paid_payment(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      start_date=DateTime(),
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'started')

    # Manually generate mapping
    transaction.PaymentTransaction_generatePayzenId()

    self._simulatePaymentTransaction_addPayzenTicket()
    self._simulatePaymentTransaction_createPaidPayzenEvent()
    try:
      transaction.PaymentTransaction_updateStatus()
    finally:
      self._dropPaymentTransaction_addPayzenTicket()
      self._dropPaymentTransaction_createPayzenEvent()
    self.assertEqual(
        'Visited by PaymentTransaction_createPayzenEvent',
        transaction.workflow_history['edit_workflow'][-1]['comment'])
    self.assertEqual(
        None,
        transaction.workflow_history['edit_workflow'][-2]['comment'])
    self.assertEquals(transaction.getSimulationState(), 'stopped')

  def test_not_paid_payment(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      start_date=DateTime(),
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'started')

    # Manually generate mapping
    transaction.PaymentTransaction_generatePayzenId()

    self._simulatePaymentTransaction_addPayzenTicket()
    self._simulatePaymentTransaction_createNotPaidPayzenEvent()
    try:
      transaction.PaymentTransaction_updateStatus()
    finally:
      self._dropPaymentTransaction_addPayzenTicket()
      self._dropPaymentTransaction_createPayzenEvent()
    self.assertEqual(
        'Visited by PaymentTransaction_createPayzenEvent',
        transaction.workflow_history['edit_workflow'][-2]['comment'])
    self.assertEqual(
        'Visited by PaymentTransaction_addPayzenTicket',
        transaction.workflow_history['edit_workflow'][-1]['comment'])
    self.assertEquals(transaction.getSimulationState(), 'started')

  def _simulatePaymentTransaction_updateStatus(self):
    script_name = 'PaymentTransaction_updateStatus'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by PaymentTransaction_updateStatus') """ )
    transaction.commit()

  def _dropPaymentTransaction_updateStatus(self):
    script_name = 'PaymentTransaction_updateStatus'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_started_draft_payzen(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'started')
    self.tic()

    self._simulatePaymentTransaction_updateStatus()
    try:
      self.portal.portal_alarms.slapos_payzen_update_started_payment.activeSense()
      self.tic()
    finally:
      self._dropPaymentTransaction_updateStatus()
    self.tic()
    self.assertEqual(
        'Visited by PaymentTransaction_updateStatus',
        transaction.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_started(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      )
    self.tic()

    self._simulatePaymentTransaction_updateStatus()
    try:
      self.portal.portal_alarms.slapos_payzen_update_started_payment.activeSense()
      self.tic()
    finally:
      self._dropPaymentTransaction_updateStatus()
    self.tic()
    self.assertNotEqual(
        'Visited by PaymentTransaction_updateStatus',
        transaction.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_draft(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      payment_mode="payzen",
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'started')
    self.portal.portal_workflow._jumpToStateFor(transaction, 'solved')
    self.tic()

    self._simulatePaymentTransaction_updateStatus()
    try:
      self.portal.portal_alarms.slapos_payzen_update_started_payment.activeSense()
      self.tic()
    finally:
      self._dropPaymentTransaction_updateStatus()
    self.tic()
    self.assertNotEqual(
        'Visited by PaymentTransaction_updateStatus',
        transaction.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_payzen(self):
    new_id = self.generateNewId()
    transaction = self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      )
    self.portal.portal_workflow._jumpToStateFor(transaction, 'started')
    self.tic()

    self._simulatePaymentTransaction_updateStatus()
    try:
      self.portal.portal_alarms.slapos_payzen_update_started_payment.activeSense()
      self.tic()
    finally:
      self._dropPaymentTransaction_updateStatus()
    self.tic()
    self.assertNotEqual(
        'Visited by PaymentTransaction_updateStatus',
        transaction.workflow_history['edit_workflow'][-1]['comment'])
