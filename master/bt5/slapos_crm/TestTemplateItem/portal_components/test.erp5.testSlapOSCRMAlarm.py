# Copyright (c) 2013 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from DateTime import DateTime
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

class TestSlapOSCrmDeleteHostingSubscription(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      )

  def _simulateRegularisationRequest_deleteHostingSubscriptionList(self):
    script_name = 'RegularisationRequest_deleteHostingSubscriptionList'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by RegularisationRequest_deleteHostingSubscriptionList') """ )
    transaction.commit()

  def _dropRegularisationRequest_deleteHostingSubscriptionList(self):
    script_name = 'RegularisationRequest_deleteHostingSubscriptionList'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_matching_regularisation_request(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_delete_acknowledgement')
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_deleteHostingSubscriptionList()
    try:
      self.portal.portal_alarms.\
          slapos_crm_delete_hosting_subscription.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_deleteHostingSubscriptionList()
    self.assertEqual(
        'Visited by RegularisationRequest_deleteHostingSubscriptionList',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_suspended(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_delete_acknowledgement')
    ticket.validate()

    self.tic()
    self._simulateRegularisationRequest_deleteHostingSubscriptionList()
    try:
      self.portal.portal_alarms.\
          slapos_crm_delete_hosting_subscription.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_deleteHostingSubscriptionList()
    self.assertNotEqual(
        'Visited by RegularisationRequest_deleteHostingSubscriptionList',
        ticket.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_other_resource(self):
    ticket = self.createRegularisationRequest()
    ticket.edit(resource='service_module/slapos_crm_delete_reminder')
    ticket.validate()
    ticket.suspend()

    self.tic()
    self._simulateRegularisationRequest_deleteHostingSubscriptionList()
    try:
      self.portal.portal_alarms.\
          slapos_crm_delete_hosting_subscription.activeSense()
      self.tic()
    finally:
      self._dropRegularisationRequest_deleteHostingSubscriptionList()
    self.assertNotEqual(
        'Visited by RegularisationRequest_deleteHostingSubscriptionList',
        ticket.workflow_history['edit_workflow'][-1]['comment'])
        

class TestSlapOSCrmMonitoringCheckComputerState(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def _simulateComputer_checkState(self):
    script_name = 'Computer_checkState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Computer_checkState') """ )
    transaction.commit()

  def _dropComputer_checkState(self):
    script_name = 'Computer_checkState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_check_public_computer_state(self):
    self._makeComputer()
    self.computer.edit(allocation_scope='open/public')
    
    self._simulateComputer_checkState()

    try:
      self.portal.portal_alarms.slapos_crm_check_computer_state.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkState()

    self.assertEqual('Visited by Computer_checkState',
      self.computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_check_friend_computer_state(self):
    self._makeComputer()
    self.computer.edit(allocation_scope='open/friend')
    
    self._simulateComputer_checkState()

    try:
      self.portal.portal_alarms.slapos_crm_check_computer_state.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkState()

    self.assertEqual('Visited by Computer_checkState',
      self.computer.workflow_history['edit_workflow'][-1]['comment'])


  def _test_alarm_check_computer_state_not_selected(self, allocation_scope):
    self._makeComputer()
    self.computer.edit(allocation_scope=allocation_scope)
    
    self._simulateComputer_checkState()

    try:
      self.portal.portal_alarms.slapos_crm_check_computer_state.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkState()

    self.assertNotEqual('Visited by Computer_checkState',
      self.computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_check_computer_state_no_public_computer(self):
    self._test_alarm_check_computer_state_not_selected(
      allocation_scope='open/personal')
      
  def test_alarm_check_computer_state_closed_forever_computer(self):
    self._test_alarm_check_computer_state_not_selected(
      allocation_scope='closed/forever')
      
  def test_alarm_check_computer_state_closed_mantainence_computer(self):
    self._test_alarm_check_computer_state_not_selected(
      allocation_scope='closed/maintenance')
      
  def test_alarm_check_computer_state_closed_termination_computer(self):
    self._test_alarm_check_computer_state_not_selected(
      allocation_scope='closed/termination')


class TestSlapOSCrmMonitoringCheckComputerAllocationScope(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def _makeSoftwareInstallation(self):
    software_installation = self.portal\
       .software_installation_module.template_software_installation\
       .Base_createCloneDocument(batch_mode=1)
    software_installation.edit(
       url_string=self.generateNewSoftwareReleaseUrl(),
       aggregate=self.computer.getRelativeUrl(),
       reference='TESTSOFTINSTS-%s' % self.generateNewId(),
       title='Start requested for %s' % self.computer.getUid()
     )
    software_installation.validate()
    software_installation.requestStart()

    return software_installation

  def _simulateComputer_checkAndUpdateAllocationScope(self):
    script_name = 'Computer_checkAndUpdateAllocationScope'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Computer_checkAndUpdateAllocationScope') """ )
    transaction.commit()
    
  def _dropComputer_checkAndUpdateAllocationScope(self):
    script_name = 'Computer_checkAndUpdateAllocationScope'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()
  
  def test_alarm_not_allowed_allocation_scope_OpenPublic(self):
    self._makeComputer()
    self.computer.edit(allocation_scope = 'open/public')
    
    self._simulateComputer_checkAndUpdateAllocationScope()

    try:
      self.portal.portal_alarms.slapos_crm_check_update_allocation_scope.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkAndUpdateAllocationScope()

    self.assertEqual('Visited by Computer_checkAndUpdateAllocationScope',
      self.computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_allowed_allocation_scope_OpenFriend(self):
    self._makeComputer()
    self.computer.edit(allocation_scope = 'open/friend')
    
    self._simulateComputer_checkAndUpdateAllocationScope()

    try:
      self.portal.portal_alarms.slapos_crm_check_update_allocation_scope.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkAndUpdateAllocationScope()

    self.assertEqual('Visited by Computer_checkAndUpdateAllocationScope',
      self.computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_not_allowed_allocationScope_open_personal(self):
    self._makeComputer()
    self.computer.edit(allocation_scope = 'open/personal')
    
    self._simulateComputer_checkAndUpdateAllocationScope()

    try:
      self.portal.portal_alarms.slapos_crm_check_update_allocation_scope.activeSense()
      self.tic()
    finally:
      self._dropComputer_checkAndUpdateAllocationScope()

    self.assertNotEqual('Visited by Computer_checkAndUpdateAllocationScope',
      self.computer.workflow_history['edit_workflow'][-1]['comment'])


class TestSlapOSCrmMonitoringCheckComputerPersonalAllocationScope(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def _makeSoftwareInstallation(self):
    software_installation = self.portal\
       .software_installation_module.template_software_installation\
       .Base_createCloneDocument(batch_mode=1)
    software_installation.edit(
       url_string=self.generateNewSoftwareReleaseUrl(),
       aggregate=self.computer.getRelativeUrl(),
       reference='TESTSOFTINSTS-%s' % self.generateNewId(),
       title='Start requested for %s' % self.computer.getUid()
     )
    software_installation.validate()
    software_installation.requestStart()

    return software_installation

  def _simulateComputer_checkAndUpdatePersonalAllocationScope(self):
    script_name = 'Computer_checkAndUpdatePersonalAllocationScope'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Computer_checkAndUpdatePersonalAllocationScope') """ )
    transaction.commit()
    
  def _dropComputer_checkAndUpdatePersonalAllocationScope(self):
    script_name = 'Computer_checkAndUpdatePersonalAllocationScope'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_allowed_allocation_scope_OpenPersonal_old_computer(self):
    self._makeComputer()
    self.computer.edit(allocation_scope = 'open/personal')
    def getModificationDate(self):
      return DateTime() - 50
    
    from Products.ERP5Type.Base import Base
    
    self._simulateComputer_checkAndUpdatePersonalAllocationScope()
    original_get_modification = Base.getModificationDate
    Base.getModificationDate = getModificationDate

    try:
      self.portal.portal_alarms.slapos_crm_check_update_personal_allocation_scope.activeSense()
      self.tic()
    finally:
      Base.getModificationDate = original_get_modification
      self._dropComputer_checkAndUpdatePersonalAllocationScope()

    self.assertEqual('Visited by Computer_checkAndUpdatePersonalAllocationScope',
      self.computer.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_allowed_allocation_scope_OpenPersonalWithSoftwareInstallation(self):
    self._makeComputer()
    self.computer.edit(allocation_scope = 'open/personal')
    self._makeSoftwareInstallation()
    def getModificationDate(self):
      return DateTime() - 50
    
    from Products.ERP5Type.Base import Base
    
    self._simulateComputer_checkAndUpdatePersonalAllocationScope()
    original_get_modification = Base.getModificationDate
    Base.getModificationDate = getModificationDate

    try:
      self.portal.portal_alarms.slapos_crm_check_update_personal_allocation_scope.activeSense()
      self.tic()
    finally:
      Base.getModificationDate = original_get_modification
      self._dropComputer_checkAndUpdatePersonalAllocationScope()

    self.assertNotEqual('Visited by Computer_checkAndUpdatePersonalAllocationScope',
      self.computer.workflow_history['edit_workflow'][-1]['comment'])

class TestSlapOSCrmMonitoringCheckInstanceInError(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()
  
  def _makeHostingSubscription(self):
    person = self.portal.person_module.template_member\
         .Base_createCloneDocument(batch_mode=1)
    hosting_subscription = self.portal\
      .hosting_subscription_module.template_hosting_subscription\
      .Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    new_id = self.generateNewId()
    hosting_subscription.edit(
        title= "Test hosting sub ticket %s" % new_id,
        reference="TESTHST-%s" % new_id,
        destination_section_value=person
    )

    return hosting_subscription
    
  def _makeSoftwareInstance(self, hosting_subscription):

    kw = dict(
      software_release=hosting_subscription.getUrlString(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='started'
    )
    hosting_subscription.requestStart(**kw)
    hosting_subscription.requestInstance(**kw)

  def _simulateHostingSubscription_checkSofwareInstanceState(self):
    script_name = 'HostingSubscription_checkSofwareInstanceState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
      script_name,
      '*args, **kw',
      '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by HostingSubscription_checkSofwareInstanceState') """ )
    transaction.commit()
  
  def _dropHostingSubscription_checkSofwareInstanceState(self):
    script_name = 'HostingSubscription_checkSofwareInstanceState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()
  
  def test_alarm_check_instance_in_error_validated_hosting_subscription(self):
    host_sub = self._makeHostingSubscription()

    self._simulateHostingSubscription_checkSofwareInstanceState()

    try:
      self.portal.portal_alarms.slapos_crm_check_instance_in_error.activeSense()
      self.tic()
    finally:
      self._dropHostingSubscription_checkSofwareInstanceState()

    self.assertEqual('Visited by HostingSubscription_checkSofwareInstanceState',
      host_sub.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_check_instance_in_error_archived_hosting_subscription(self):
    host_sub = self._makeHostingSubscription()
    host_sub.archive()
    
    self._simulateHostingSubscription_checkSofwareInstanceState()

    try:
      self.portal.portal_alarms.slapos_crm_check_instance_in_error.activeSense()
      self.tic()
    finally:
      self._dropHostingSubscription_checkSofwareInstanceState()

    self.assertNotEqual('Visited by HostingSubscription_checkSofwareInstanceState',
      host_sub.workflow_history['edit_workflow'][-1]['comment'])
      
      
