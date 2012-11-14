# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from DateTime import DateTime
from Products.ERP5Type.DateUtils import addToDate

class TestHostingSubscriptionSimulation(testSlapOSMixin):
  def _prepare(self):
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    self.subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    self.initial_date = DateTime('2011/02/16')
    stop_date = DateTime('2011/04/16')
    self.subscription.edit(
      periodicity_hour=0,
      periodicity_minute=0,
      periodicity_month_day=self.initial_date.day(),
      destination_section=person.getRelativeUrl()
    )
    self.portal.portal_workflow._jumpToStateFor(self.subscription, 'validated')

    open_sale_order_template = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredOpenSaleOrderTemplate())
    open_sale_order_line_template = self.portal.restrictedTraverse(
        self.portal.portal_preferences.getPreferredOpenSaleOrderLineTemplate())
    open_order = open_sale_order_template.Base_createCloneDocument(
        batch_mode=1)
    open_order.edit(
        destination_decision=person.getRelativeUrl(),
        destination_section=person.getRelativeUrl(),
        destination=person.getRelativeUrl(),
        effective_date=self.initial_date,
        expiration_date=self.initial_date + 1,
    )
    self.portal.portal_workflow._jumpToStateFor(open_order, 'validated')

    self.open_order_line = open_sale_order_line_template.Base_createCloneDocument(
        batch_mode=1, destination=open_order)
    self.open_order_line.edit(
        aggregate=self.subscription.getRelativeUrl(),
        start_date=self.initial_date,
        stop_date=stop_date
    )
    self.tic()

    applied_rule_list = self.portal.portal_catalog(portal_type='Applied Rule',
        causality_uid=self.subscription.getUid())
    self.assertEqual(0, len(applied_rule_list))

    self.subscription.updateSimulation(expand_root=1)
    self.tic()

  def test_simulation(self):
    self._prepare()
    applied_rule_list = self.portal.portal_catalog(portal_type='Applied Rule',
        causality_uid=self.subscription.getUid())
    self.assertEqual(1, len(applied_rule_list))

    applied_rule = applied_rule_list[0].getObject()
    rule = applied_rule.getSpecialiseValue()

    self.assertEqual('Subscription Item Root Simulation Rule',
        rule.getPortalType())
    self.assertEqual('default_subscription_item_rule', rule.getReference())

    simulation_movement_list = self.portal.portal_catalog(
        portal_type='Simulation Movement',
        parent_uid=applied_rule.getUid(),
        sort_on=(('movement.start_date', 'ASC'),)
    )

    # There are 2 movements, for February and March
    self.assertEqual(2, len(simulation_movement_list))

    # Check the list of expected simulation
    idx = 0
    for simulation_movement in simulation_movement_list:
      simulation_movement = simulation_movement.getObject()
      movement_start_date = addToDate(self.initial_date, to_add=dict(month=idx))
      movement_stop_date = addToDate(self.initial_date, to_add=dict(month=idx+1))
      # Check simulation movement property
      self.assertEqual(movement_start_date, simulation_movement.getStartDate())
      self.assertEqual(movement_stop_date, simulation_movement.getStopDate())
      self.assertEquals(self.open_order_line.getQuantity(),
        simulation_movement.getQuantity())
      self.assertEquals(self.open_order_line.getQuantityUnit(),
        simulation_movement.getQuantityUnit())
      self.assertEquals(self.open_order_line.getPrice(),
        simulation_movement.getPrice())
      self.assertEquals(self.open_order_line.getPriceCurrency(),
        simulation_movement.getPriceCurrency())
      self.assertEquals(self.open_order_line.getSource(),
        simulation_movement.getSource())
      self.assertEquals(self.open_order_line.getSourceSection(),
        simulation_movement.getSourceSection())
      self.assertEquals(self.open_order_line.getDestination(),
        simulation_movement.getDestination())
      self.assertEquals(self.open_order_line.getDestinationSection(),
        simulation_movement.getDestinationSection())
      self.assertEquals(self.open_order_line.getSpecialise(),
        simulation_movement.getSpecialise())
      self.assertEquals(self.open_order_line.getResource(),
        simulation_movement.getResource())
      self.assertEquals(applied_rule.getSpecialiseValue().getTradePhaseList(),
        simulation_movement.getTradePhaseList())
      self.assertSameSet(self.open_order_line.getAggregateList(),
        simulation_movement.getAggregateList())
      self.assertEqual('planned', simulation_movement.getSimulationState())
      self.assertEqual(None, simulation_movement.getDelivery())

      applied_rule_list_level_2 = simulation_movement.contentValues(
          portal_type='Applied Rule')
      self.assertEqual(0, len(applied_rule_list_level_2))
      # check next simulation movement
      idx += 1

  def test_increaseOpenOrderCoverage(self):
    self._prepare()
    applied_rule_list = self.portal.portal_catalog(portal_type='Applied Rule',
        causality_uid=self.subscription.getUid())
    self.assertEqual(1, len(applied_rule_list))

    applied_rule = applied_rule_list[0].getObject()
    rule = applied_rule.getSpecialiseValue()

    self.assertEqual('Subscription Item Root Simulation Rule',
        rule.getPortalType())
    self.assertEqual('default_subscription_item_rule', rule.getReference())

    simulation_movement_list = self.portal.portal_catalog(
        portal_type='Simulation Movement',
        parent_uid=applied_rule.getUid(),
        sort_on=(('movement.start_date', 'ASC'),)
    )

    # There are 2 movements, for February and March
    self.assertEqual(2, len(simulation_movement_list))

    self.open_order_line.edit(stop_date=DateTime('2011/05/16'))
    self.tic()

    self.subscription.updateSimulation(expand_root=1)
    self.tic()

    simulation_movement_list = self.portal.portal_catalog(
        portal_type='Simulation Movement',
        parent_uid=applied_rule.getUid(),
        sort_on=(('movement.start_date', 'ASC'),)
    )

    # There are 3 movements, for February, March and April
    self.assertEqual(3, len(simulation_movement_list))


