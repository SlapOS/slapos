# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from Products.ERP5Type.tests.utils import createZODBPythonScript
from Products.ERP5Type.tests.backportUnittest import skip
import json
from DateTime import DateTime
from zExceptions import Unauthorized

class TestSlapOSERP5CleanupActiveProcess(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def _simulateActiveProcess_deleteSelf(self):
    script_name = 'ActiveProcess_deleteSelf'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""description = '%s\\nVisited by ActiveProcess_deleteSelf' % context.getDescription()
context.edit(description=description)""")
    transaction.commit()

  def _dropActiveProcess_deleteSelf(self):
    script_name = 'ActiveProcess_deleteSelf'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def check_cleanup_active_process_alarm(self, date, assert_method):
    def verify_getCreationDate_call(*args, **kwargs):
      return date
    ActiveProcessClass = self.portal.portal_types.getPortalTypeClass(
        'Active Process')
    ActiveProcessClass.getCreationDate_call = ActiveProcessClass.\
        getCreationDate
    ActiveProcessClass.getCreationDate = verify_getCreationDate_call

    new_id = self.generateNewId()
    active_process = self.portal.portal_activities.newContent(
      portal_type='Active Process',
      title="Active Process %s" % new_id,
      reference="ACTPROC-%s" % new_id,
      description="Active Process %s" % new_id,
      )
    self.assertEquals(active_process.getCreationDate(), date)

    self._simulateActiveProcess_deleteSelf()
    try:
      self.portal.portal_alarms.slapos_erp5_cleanup_active_process.activeSense()
      self.tic()
    finally:
      self._dropActiveProcess_deleteSelf()
      self.portal.portal_types.resetDynamicDocumentsOnceAtTransactionBoundary()
      transaction.commit()

    assert_method(active_process.getDescription('').\
        endswith("Visited by ActiveProcess_deleteSelf"),
        active_process.getDescription(''))

  def test_alarm_old_active_process(self):
    self.check_cleanup_active_process_alarm(DateTime() - 22, self.assertTrue)

  def test_alarm_new_active_process(self):
    self.check_cleanup_active_process_alarm(DateTime() - 20, self.assertFalse)


class TestSlapOSERP5ActiveProcess_deleteSelf(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createActiveProcess(self):
    new_id = self.generateNewId()
    return self.portal.portal_activities.newContent(
      portal_type='Active Process',
      title="Active Process %s" % new_id,
      reference="ACTPROC-%s" % new_id,
      description="Active Process %s" % new_id,
      )

  def test_disallowedPortalType(self):
    document = self.portal.person_module.newContent()
    self.assertRaises(
      TypeError,
      document.ActiveProcess_deleteSelf,
      )

  def test_REQUEST_disallowed(self):
    active_process = self.createActiveProcess()
    self.assertRaises(
      Unauthorized,
      active_process.ActiveProcess_deleteSelf,
      REQUEST={})

  def test_default_use_case(self):
    active_process = self.createActiveProcess()
    module = active_process.getParentValue()
    id = active_process.getId()
    active_process.ActiveProcess_deleteSelf()
    self.assertRaises(
      KeyError,
      module._getOb,
      id)
