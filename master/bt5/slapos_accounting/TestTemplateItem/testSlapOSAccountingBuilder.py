# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from DateTime import DateTime

def convertCategoryList(base, l):
  return ['%s/%s' % (base, q) for q in l]

class TestSlapOSSalePackingListBuilder(testSlapOSMixin):
  def test(self):
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    applied_rule = self.portal.portal_simulation.newContent(
      portal_type='Applied Rule',
      causality=hosting_subscription.getRelativeUrl(),
      specialise='portal_rules/slapos_subscription_item_rule'
    )
    person = self.portal.person_module.template_member\
        .Base_createCloneDocument(batch_mode=1)
    simulation_movement_kw = dict(
        portal_type='Simulation Movement',
        aggregate=hosting_subscription.getRelativeUrl(),
        base_contribution=['base_amount/invoicing/discounted',
            'base_amount/invoicing/taxable'],
        causality=['business_process_module/slapos_sale_business_process'
            '/deliver', 'business_process_module/slapos_sale_business_pr'
            'ocess/delivery_path'],
        destination=person.getRelativeUrl(),
        destination_decision=person.getRelativeUrl(),
        destination_section=person.getRelativeUrl(),
        price_currency='currency_module/EUR',
        quantity_unit='unit/piece',
        resource='service_module/slapos_instance_subscription',
        source='organisation_module/slapos',
        source_section='organisation_module/slapos',
        specialise='sale_trade_condition_module/slapos_trade_condition',
        trade_phase='slapos/delivery',
        use='trade/sale',
    )
    simulation_movement_1 = applied_rule.newContent(
        quantity=1.2,
        price=3.4,
        start_date=DateTime('2012/01/01'),
        stop_date=DateTime('2012/02/01'),
        **simulation_movement_kw
    )
    simulation_movement_2 = applied_rule.newContent(
        quantity=5.6,
        price=7.8,
        start_date=DateTime('2012/03/01'),
        stop_date=DateTime('2012/04/01'),
        **simulation_movement_kw
    )

    self.tic()

    self.portal.portal_deliveries.slapos_sale_packing_list_builder.build(
        path='%s/%%' % applied_rule.getPath())
    self.tic()

    def checkSimulationMovement(simulation_movement):
      self.assertEqual(1.0, simulation_movement.getDeliveryRatio())
      self.assertEqual(0.0, simulation_movement.getDeliveryError())
      self.assertNotEqual(None, simulation_movement.getDeliveryValue())

    checkSimulationMovement(simulation_movement_1)
    checkSimulationMovement(simulation_movement_2)

    delivery_line_1 = simulation_movement_1.getDeliveryValue()
    delivery_line_2 = simulation_movement_2.getDeliveryValue()
    self.assertNotEqual(delivery_line_1.getRelativeUrl(),
        delivery_line_2.getRelativeUrl())

    def checkDeliveryLine(simulation_movement, delivery_line):
      self.assertEqual('Sale Packing List Line', delivery_line.getPortalType())
      self.assertSameSet([
          'resource/service_module/slapos_instance_subscription',
          'use/trade/sale',
          'quantity_unit/unit/piece',
          'base_contribution/base_amount/invoicing/discounted',
          'base_contribution/base_amount/invoicing/taxable'] \
            + convertCategoryList('aggregate',
              simulation_movement.getAggregateList()),
        delivery_line.getCategoryList()
      )
      self.assertEqual(simulation_movement.getQuantity(),
          delivery_line.getQuantity())
      self.assertEqual(simulation_movement.getPrice(),
          delivery_line.getPrice())
      self.assertFalse(delivery_line.hasStartDate())
      self.assertFalse(delivery_line.hasStopDate())

    checkDeliveryLine(simulation_movement_1, delivery_line_1)
    checkDeliveryLine(simulation_movement_2, delivery_line_2)

    delivery_1 = delivery_line_1.getParentValue()
    delivery_2 = delivery_line_2.getParentValue()

    def checkDelivery(simulation_movement, delivery):
      self.assertEqual('Sale Packing List', delivery.getPortalType())
      self.assertEqual('delivered', delivery.getSimulationState())
      self.assertEqual('building', delivery.getCausalityState())
      self.assertEqual(simulation_movement.getStartDate(),
        delivery.getStartDate())
      self.assertEqual(simulation_movement.getStopDate(),
        delivery.getStopDate())
      self.assertSameSet([
            'source/organisation_module/slapos',
            'source_section/organisation_module/slapos',
            'price_currency/currency_module/EUR',
            'specialise/sale_trade_condition_module/slapos_trade_condition'] \
              + convertCategoryList('destination',
                  simulation_movement.getDestinationList()) \
              + convertCategoryList('destination_section',
                  simulation_movement.getDestinationSectionList()) \
              + convertCategoryList('destination_decision',
                  simulation_movement.getDestinationDecisionList()) \
              + convertCategoryList('causality',
                  simulation_movement.getParentValue().getCausalityList()),
        delivery.getCategoryList())

    checkDelivery(simulation_movement_1, delivery_1)
    checkDelivery(simulation_movement_2, delivery_2)
