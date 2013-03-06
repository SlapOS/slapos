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

