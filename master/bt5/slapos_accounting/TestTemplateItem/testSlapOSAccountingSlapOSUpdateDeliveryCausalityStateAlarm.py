# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

import transaction
import functools
import os
import tempfile
from Products.ERP5Type.tests.utils import createZODBPythonScript
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin

def withAbort(func):
  @functools.wraps(func)
  def wrapped(self, *args, **kwargs):
    try:
      func(self, *args, **kwargs)
    finally:
      transaction.abort()
  return wrapped

class Simulator:
  def __init__(self, outfile, method, to_return=None):
    self.outfile = outfile
    open(self.outfile, 'w').write(repr([]))
    self.method = method
    self.to_return = to_return

  def __call__(self, *args, **kwargs):
    """Simulation Method"""
    old = open(self.outfile, 'r').read()
    if old:
      l = eval(old)
    else:
      l = []
    l.append({'recmethod': self.method,
      'recargs': args,
      'reckwargs': kwargs})
    open(self.outfile, 'w').write(repr(l))
    return self.to_return

def simulateDelivery_updateCausalityState(func):
  @functools.wraps(func)
  def wrapped(self, *args, **kwargs):
    script_name = 'Delivery_updateCausalityState'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
if context.getTitle() == 'Not visited by Delivery_updateCausalityState':
  context.setTitle('Visited by Delivery_updateCausalityState')
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
  @simulateDelivery_updateCausalityState
  def _test(self, state, message):
    delivery = self.portal.sale_packing_list_module.newContent(
        title='Not visited by Delivery_updateCausalityState',
        portal_type='Sale Packing List')
    self.portal.portal_workflow._jumpToStateFor(delivery, state)
    self.tic()

    self.portal.portal_alarms.slapos_update_delivery_causality_state\
        .activeSense()
    self.tic()

    self.assertEqual(message, delivery.getTitle())

  def test_building(self):
    self._test('building', 'Visited by Delivery_updateCausalityState')

  def test_calculating(self):
    self._test('calculating', 'Visited by Delivery_updateCausalityState')

  def test_diverged(self):
    self._test('diverged', 'Not visited by Delivery_updateCausalityState')

  def test_solved(self):
    self._test('solved', 'Not visited by Delivery_updateCausalityState')

  @withAbort
  def _test_Delivery_updateCausalityState(self, state, empty=False):
    delivery = self.portal.sale_packing_list_module.newContent(
        title='Not visited by Delivery_updateCausalityState',
        portal_type='Sale Packing List')
    self.portal.portal_workflow._jumpToStateFor(delivery, state)

    updateCausalityState_simulator = tempfile.mkstemp()[1]
    try:
      from Products.ERP5.Document.Delivery import Delivery
      Delivery.original_updateCausalityState = Delivery\
          .updateCausalityState
      Delivery.updateCausalityState = Simulator(
          updateCausalityState_simulator, 'updateCausalityState')

      delivery.Delivery_updateCausalityState()

      value = eval(open(updateCausalityState_simulator).read())

      if empty:
        self.assertEqual([], value)
      else:
        self.assertEqual([{
          'recmethod': 'updateCausalityState',
          'recargs': (),
          'reckwargs': {'solve_automatically': False}}],
          value
        )
    finally:
      Delivery.updateCausalityState = Delivery.original_updateCausalityState
      delattr(Delivery, 'original_updateCausalityState')
      if os.path.exists(updateCausalityState_simulator):
        os.unlink(updateCausalityState_simulator)

  def test_Delivery_updateCausalityState_calculating(self):
    self._test_Delivery_updateCausalityState('calculating')

  def test_Delivery_updateCausalityState_building(self):
    self._test_Delivery_updateCausalityState('building')

  def test_Delivery_updateCausalityState_solved(self):
    self._test_Delivery_updateCausalityState('solved', True)

  def test_Delivery_updateCausalityState_diverged(self):
    self._test_Delivery_updateCausalityState('diverged', True)
