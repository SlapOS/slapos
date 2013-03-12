# Copyright (c) 2013 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from Products.ERP5Type.tests.utils import createZODBPythonScript

class TestSlapOSCRMCreateRegularisationRequest(testSlapOSMixin):

  def _simulatePerson_checkToCreateRegularisationRequest(self):
    script_name = 'Person_checkToCreateRegularisationRequest'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Person_checkToCreateRegularisationRequest') """ )
    transaction.commit()

  def _dropPerson_checkToCreateRegularisationRequest(self):
    script_name = 'Person_checkToCreateRegularisationRequest'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_expected_person(self):
    new_id = self.generateNewId()
    person = self.portal.person_module.newContent(
      portal_type='Person',
      title="Test person %s" % new_id,
      reference="TESTPERS_%s" % new_id,
      default_email_text="%s@example.org" % new_id,
      )
    person.validate()

    self.tic()
    self._simulatePerson_checkToCreateRegularisationRequest()
    try:
      self.portal.portal_alarms.\
          slapos_crm_create_regularisation_request.activeSense()
      self.tic()
    finally:
      self._dropPerson_checkToCreateRegularisationRequest()
    self.assertEqual(
        'Visited by Person_checkToCreateRegularisationRequest',
        person.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_no_email(self):
    new_id = self.generateNewId()
    person = self.portal.person_module.newContent(
      portal_type='Person',
      title="Test person %s" % new_id,
      reference="TESTPERS_%s" % new_id,
      )
    person.validate()

    self.tic()
    self._simulatePerson_checkToCreateRegularisationRequest()
    try:
      self.portal.portal_alarms.\
          slapos_crm_create_regularisation_request.activeSense()
      self.tic()
    finally:
      self._dropPerson_checkToCreateRegularisationRequest()
    self.assertNotEqual(
        'Visited by Person_checkToCreateRegularisationRequest',
        person.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_no_reference(self):
    new_id = self.generateNewId()
    person = self.portal.person_module.newContent(
      portal_type='Person',
      title="Test person %s" % new_id,
      default_email_text="%s@example.org" % new_id,
      )
    person.validate()

    self.tic()
    self._simulatePerson_checkToCreateRegularisationRequest()
    try:
      self.portal.portal_alarms.\
          slapos_crm_create_regularisation_request.activeSense()
      self.tic()
    finally:
      self._dropPerson_checkToCreateRegularisationRequest()
    self.assertNotEqual(
        'Visited by Person_checkToCreateRegularisationRequest',
        person.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_validated(self):
    new_id = self.generateNewId()
    person = self.portal.person_module.newContent(
      portal_type='Person',
      title="Test person %s" % new_id,
      reference="TESTPERS_%s" % new_id,
      default_email_text="%s@example.org" % new_id,
      )
    person.validate()
    person.invalidate()

    self.tic()
    self._simulatePerson_checkToCreateRegularisationRequest()
    try:
      self.portal.portal_alarms.\
          slapos_crm_create_regularisation_request.activeSense()
      self.tic()
    finally:
      self._dropPerson_checkToCreateRegularisationRequest()
    self.assertNotEqual(
        'Visited by Person_checkToCreateRegularisationRequest',
        person.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSCrmInvalidateSuspendedRegularisationRequest(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      )

  def _simulateRegularisationRequest_invalidateIfPersonBalanceIsOk(self):
    script_name = 'RegularisationRequest_invalidateIfPersonBalanceIsOk'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by RegularisationRequest_invalidateIfPersonBalanceIsOk') """ )
    transaction.commit()

  def _dropRegularisationRequest_invalidateIfPersonBalanceIsOk(self):
    script_name = 'RegularisationRequest_invalidateIfPersonBalanceIsOk'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_not_suspended_regularisation_request(self):
    ticket = self.createRegularisationRequest()
    ticket.validate()

    self.tic()
    self._simulateRegularisationRequest_invalidateIfPersonBalanceIsOk()
    try:
      self.portal.portal_alarms.\
          slapos_crm_invalidate_suspended_regularisation_request.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_invalidateIfPersonBalanceIsOk()
    self.assertNotEqual(
        'Visited by RegularisationRequest_invalidateIfPersonBalanceIsOk',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_suspended_regularisation_request(self):
    ticket = self.createRegularisationRequest()
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_invalidateIfPersonBalanceIsOk()
    try:
      self.portal.portal_alarms.\
          slapos_crm_invalidate_suspended_regularisation_request.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_invalidateIfPersonBalanceIsOk()
    self.assertEqual(
        'Visited by RegularisationRequest_invalidateIfPersonBalanceIsOk',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSCrmCancelInvoiceRelatedToSuspendedRegularisationRequest(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      )

  def _simulateRegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty(self):
    script_name = 'RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty') """ )
    transaction.commit()

  def _dropRegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty(self):
    script_name = 'RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_not_suspended_regularisation_request(self):
    ticket = self.createRegularisationRequest()
    ticket.validate()

    self.tic()
    self._simulateRegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty()
    try:
      self.portal.portal_alarms.\
          slapos_crm_cancel_invoice.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty()
    self.assertNotEqual(
        'Visited by RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_suspended_regularisation_request(self):
    ticket = self.createRegularisationRequest()
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty()
    try:
      self.portal.portal_alarms.\
          slapos_crm_cancel_invoice.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty()
    self.assertEqual(
        'Visited by RegularisationRequest_cancelInvoiceIfPersonOpenOrderIsEmpty',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSCrmTriggerEscalationOnAcknowledgmentRegularisationRequest(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      )

  def _simulateRegularisationRequest_triggerAcknowledgmentEscalation(self):
    script_name = 'RegularisationRequest_triggerAcknowledgmentEscalation'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by RegularisationRequest_triggerAcknowledgmentEscalation') """ )
    transaction.commit()

  def _dropRegularisationRequest_triggerAcknowledgmentEscalation(self):
    script_name = 'RegularisationRequest_triggerAcknowledgmentEscalation'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_matching_regularisation_request(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_acknowledgement')
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_triggerAcknowledgmentEscalation()
    try:
      self.portal.portal_alarms.\
          slapos_crm_trigger_acknowledgment_escalation.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_triggerAcknowledgmentEscalation()
    self.assertEqual(
        'Visited by RegularisationRequest_triggerAcknowledgmentEscalation',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_suspended(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_acknowledgement')
    ticket.validate()

    self.tic()
    self._simulateRegularisationRequest_triggerAcknowledgmentEscalation()
    try:
      self.portal.portal_alarms.\
          slapos_crm_trigger_acknowledgment_escalation.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_triggerAcknowledgmentEscalation()
    self.assertNotEqual(
        'Visited by RegularisationRequest_triggerAcknowledgmentEscalation',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_expected_resource(self):
    ticket = self.createRegularisationRequest()
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_triggerAcknowledgmentEscalation()
    try:
      self.portal.portal_alarms.\
          slapos_crm_trigger_acknowledgment_escalation.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_triggerAcknowledgmentEscalation()
    self.assertNotEqual(
        'Visited by RegularisationRequest_triggerAcknowledgmentEscalation',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSCrmTriggerEscalationOnStopReminderRegularisationRequest(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      )

  def _simulateRegularisationRequest_triggerStopReminderEscalation(self):
    script_name = 'RegularisationRequest_triggerStopReminderEscalation'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by RegularisationRequest_triggerStopReminderEscalation') """ )
    transaction.commit()

  def _dropRegularisationRequest_triggerStopReminderEscalation(self):
    script_name = 'RegularisationRequest_triggerStopReminderEscalation'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_matching_regularisation_request(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_stop_reminder')
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_triggerStopReminderEscalation()
    try:
      self.portal.portal_alarms.\
          slapos_crm_trigger_stop_reminder_escalation.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_triggerStopReminderEscalation()
    self.assertEqual(
        'Visited by RegularisationRequest_triggerStopReminderEscalation',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_suspended(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_stop_reminder')
    ticket.validate()

    self.tic()
    self._simulateRegularisationRequest_triggerStopReminderEscalation()
    try:
      self.portal.portal_alarms.\
          slapos_crm_trigger_stop_reminder_escalation.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_triggerStopReminderEscalation()
    self.assertNotEqual(
        'Visited by RegularisationRequest_triggerStopReminderEscalation',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_expected_resource(self):
    ticket = self.createRegularisationRequest()
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_triggerStopReminderEscalation()
    try:
      self.portal.portal_alarms.\
          slapos_crm_trigger_stop_reminder_escalation.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_triggerStopReminderEscalation()
    self.assertNotEqual(
        'Visited by RegularisationRequest_triggerStopReminderEscalation',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSCrmTriggerEscalationOnStopAcknowledgmentRegularisationRequest(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      )

  def _simulateRegularisationRequest_triggerStopAcknowledgmentEscalation(self):
    script_name = 'RegularisationRequest_triggerStopAcknowledgmentEscalation'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by RegularisationRequest_triggerStopAcknowledgmentEscalation') """ )
    transaction.commit()

  def _dropRegularisationRequest_triggerStopAcknowledgmentEscalation(self):
    script_name = 'RegularisationRequest_triggerStopAcknowledgmentEscalation'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_matching_regularisation_request(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_stop_acknowledgement')
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_triggerStopAcknowledgmentEscalation()
    try:
      self.portal.portal_alarms.\
          slapos_crm_trigger_stop_acknowledgment_escalation.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_triggerStopAcknowledgmentEscalation()
    self.assertEqual(
        'Visited by RegularisationRequest_triggerStopAcknowledgmentEscalation',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_suspended(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_stop_acknowledgement')
    ticket.validate()

    self.tic()
    self._simulateRegularisationRequest_triggerStopAcknowledgmentEscalation()
    try:
      self.portal.portal_alarms.\
          slapos_crm_trigger_stop_acknowledgment_escalation.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_triggerStopAcknowledgmentEscalation()
    self.assertNotEqual(
        'Visited by RegularisationRequest_triggerStopAcknowledgmentEscalation',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_expected_resource(self):
    ticket = self.createRegularisationRequest()
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_triggerStopAcknowledgmentEscalation()
    try:
      self.portal.portal_alarms.\
          slapos_crm_trigger_stop_acknowledgment_escalation.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_triggerStopAcknowledgmentEscalation()
    self.assertNotEqual(
        'Visited by RegularisationRequest_triggerStopAcknowledgmentEscalation',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSCrmTriggerEscalationOnDeleteReminderRegularisationRequest(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      )

  def _simulateRegularisationRequest_triggerDeleteReminderEscalation(self):
    script_name = 'RegularisationRequest_triggerDeleteReminderEscalation'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by RegularisationRequest_triggerDeleteReminderEscalation') """ )
    transaction.commit()

  def _dropRegularisationRequest_triggerDeleteReminderEscalation(self):
    script_name = 'RegularisationRequest_triggerDeleteReminderEscalation'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_matching_regularisation_request(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_delete_reminder')
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_triggerDeleteReminderEscalation()
    try:
      self.portal.portal_alarms.\
          slapos_crm_trigger_delete_reminder_escalation.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_triggerDeleteReminderEscalation()
    self.assertEqual(
        'Visited by RegularisationRequest_triggerDeleteReminderEscalation',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_suspended(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_delete_reminder')
    ticket.validate()

    self.tic()
    self._simulateRegularisationRequest_triggerDeleteReminderEscalation()
    try:
      self.portal.portal_alarms.\
          slapos_crm_trigger_delete_reminder_escalation.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_triggerDeleteReminderEscalation()
    self.assertNotEqual(
        'Visited by RegularisationRequest_triggerDeleteReminderEscalation',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_expected_resource(self):
    ticket = self.createRegularisationRequest()
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_triggerDeleteReminderEscalation()
    try:
      self.portal.portal_alarms.\
          slapos_crm_trigger_delete_reminder_escalation.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_triggerDeleteReminderEscalation()
    self.assertNotEqual(
        'Visited by RegularisationRequest_triggerDeleteReminderEscalation',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSCrmStopHostingSubscription(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      )

  def _simulateRegularisationRequest_stopHostingSubscriptionList(self):
    script_name = 'RegularisationRequest_stopHostingSubscriptionList'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by RegularisationRequest_stopHostingSubscriptionList') """ )
    transaction.commit()

  def _dropRegularisationRequest_stopHostingSubscriptionList(self):
    script_name = 'RegularisationRequest_stopHostingSubscriptionList'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_matching_regularisation_request(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_delete_reminder')
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_stopHostingSubscriptionList()
    try:
      self.portal.portal_alarms.\
          slapos_crm_stop_hosting_subscription.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_stopHostingSubscriptionList()
    self.assertEqual(
        'Visited by RegularisationRequest_stopHostingSubscriptionList',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_matching_regularisation_request_2(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_stop_acknowledgement')
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_stopHostingSubscriptionList()
    try:
      self.portal.portal_alarms.\
          slapos_crm_stop_hosting_subscription.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_stopHostingSubscriptionList()
    self.assertEqual(
        'Visited by RegularisationRequest_stopHostingSubscriptionList',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_suspended(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_stop_acknowledgement')
    ticket.validate()

    self.tic()
    self._simulateRegularisationRequest_stopHostingSubscriptionList()
    try:
      self.portal.portal_alarms.\
          slapos_crm_stop_hosting_subscription.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_stopHostingSubscriptionList()
    self.assertNotEqual(
        'Visited by RegularisationRequest_stopHostingSubscriptionList',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_other_resource(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_acknowledgement')
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_stopHostingSubscriptionList()
    try:
      self.portal.portal_alarms.\
          slapos_crm_stop_hosting_subscription.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_stopHostingSubscriptionList()
    self.assertNotEqual(
        'Visited by RegularisationRequest_stopHostingSubscriptionList',
        ticket.workflow_history['edit_workflow'][-1]['comment'])
