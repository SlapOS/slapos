# Copyright (c) 2013 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from erp5.component.test.SlapOSTestCaseMixin import SlapOSTestCaseMixin
from Products.ERP5Type.tests.utils import createZODBPythonScript

class TestSlapOSRequestValidationPayment(SlapOSTestCaseMixin):

  def _makeSlaveTree(self, requested_template_id='template_slave_instance'):
    SlapOSTestCaseMixin.\
        _makeTree(self, requested_template_id=requested_template_id)

  def _simulateSoftwareInstance_requestValidationPayment(self):
    script_name = 'SoftwareInstance_requestValidationPayment'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by SoftwareInstance_requestValidationPayment') """ )
    transaction.commit()

  def _dropSoftwareInstance_requestValidationPayment(self):
    script_name = 'SoftwareInstance_requestValidationPayment'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def test_alarm_software_instance_unallocated(self):
    self._makeTree()
    preference =  self.portal.portal_preferences.getActiveSystemPreference()
    preference.setPreferredCloudContractEnabled(True)
    self.tic()
    self._simulateSoftwareInstance_requestValidationPayment()
    try:
      self.portal.portal_alarms.slapos_contract_request_validation_payment.activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_requestValidationPayment()
    self.assertEqual(
        'Visited by SoftwareInstance_requestValidationPayment',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_slave_instance_unallocated(self):
    self._makeSlaveTree()
    preference =  self.portal.portal_preferences.getActiveSystemPreference()
    preference.setPreferredCloudContractEnabled(True)
    self.tic()
    self._simulateSoftwareInstance_requestValidationPayment()
    try:
      self.portal.portal_alarms.slapos_contract_request_validation_payment.activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_requestValidationPayment()
    self.assertEqual(
        'Visited by SoftwareInstance_requestValidationPayment',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_software_instance_unallocated_disable_cloud_contract(self):
    self._makeTree()
    preference =  self.portal.portal_preferences.getActiveSystemPreference()
    preference.setPreferredCloudContractEnabled(False)
    self.tic()

    self._simulateSoftwareInstance_requestValidationPayment()
    try:
      self.portal.portal_alarms.slapos_contract_request_validation_payment.activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_requestValidationPayment()
    self.assertEqual(
        'Visited by SoftwareInstance_requestValidationPayment',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_slave_instance_unallocated_disable_cloud_contract(self):
    self._makeSlaveTree()
    preference =  self.portal.portal_preferences.getActiveSystemPreference()
    preference.setPreferredCloudContractEnabled(False)
    self.tic()

    self._simulateSoftwareInstance_requestValidationPayment()
    try:
      self.portal.portal_alarms.slapos_contract_request_validation_payment.activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_requestValidationPayment()
    self.assertNotEqual(
        'Visited by SoftwareInstance_requestValidationPayment',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_software_instance_allocated(self):
    self._makeTree()
    preference =  self.portal.portal_preferences.getActiveSystemPreference()
    preference.setPreferredCloudContractEnabled(True)
    self.tic()
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.tic()
    self._simulateSoftwareInstance_requestValidationPayment()
    try:
      self.portal.portal_alarms.slapos_contract_request_validation_payment.activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_requestValidationPayment()
    self.assertNotEqual(
        'Visited by SoftwareInstance_requestValidationPayment',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])

  def test_alarm_slave_instance_allocated(self):
    self._makeSlaveTree()
    preference =  self.portal.portal_preferences.getActiveSystemPreference()
    preference.setPreferredCloudContractEnabled(True)
    self.tic()
    self._makeComputer()
    self.software_instance.setAggregate(self.partition.getRelativeUrl())
    self.tic()
    self._simulateSoftwareInstance_requestValidationPayment()
    try:
      self.portal.portal_alarms.slapos_contract_request_validation_payment.activeSense()
      self.tic()
    finally:
      self._dropSoftwareInstance_requestValidationPayment()
    self.assertNotEqual(
        'Visited by SoftwareInstance_requestValidationPayment',
        self.software_instance.workflow_history['edit_workflow'][-1]['comment'])
