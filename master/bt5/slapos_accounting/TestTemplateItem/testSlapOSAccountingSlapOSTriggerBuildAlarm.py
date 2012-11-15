# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

import transaction
import functools
from Products.ERP5Type.tests.utils import createZODBPythonScript
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin

def simulateSimulationMovement_buildSlapOS(func):
  @functools.wraps(func)
  def wrapped(self, *args, **kwargs):
    script_name = 'SimulationMovement_buildSlapOS'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
if context.getTitle() == 'Not visited by SimulationMovement_buildSlapOS':
  context.setTitle('Visited by SimulationMovement_buildSlapOS')
""" )
    transaction.commit()
    try:
      func(self, *args, **kwargs)
    finally:
      if script_name in self.portal.portal_skins.custom.objectIds():
        self.portal.portal_skins.custom.manage_delObjects(script_name)
      transaction.commit()
  return wrapped

class TestAlarm(testSlapOSMixin):
  @simulateSimulationMovement_buildSlapOS
  def test_SimulationMovement_withoutDelivery(self):
    applied_rule = self.portal.portal_simulation.newContent(
        portal_type='Applied Rule')
    simulation_movement = applied_rule.newContent(
        portal_type='Simulation Movement',
        title='Not visited by SimulationMovement_buildSlapOS')
    self.tic()

    self.portal.portal_alarms.slapos_trigger_build.activeSense()
    self.tic()

    self.assertEqual(
        'Visited by SimulationMovement_buildSlapOS',
        simulation_movement.getTitle())

  @simulateSimulationMovement_buildSlapOS
  def test_SimulationMovement_withDelivery(self):
    delivery = self.portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List')
    delivery_line = delivery.newContent(portal_type='Sale Packing List Line')
    applied_rule = self.portal.portal_simulation.newContent(
        portal_type='Applied Rule')
    simulation_movement = applied_rule.newContent(
        portal_type='Simulation Movement',
        delivery=delivery_line.getRelativeUrl(),
        title='Shall be visited by SimulationMovement_buildSlapOS')
    self.tic()

    self.portal.portal_alarms.slapos_trigger_build.activeSense()
    self.tic()

    self.assertNotEqual(
        'Not visited by SimulationMovement_buildSlapOS',
        simulation_movement.getTitle())
