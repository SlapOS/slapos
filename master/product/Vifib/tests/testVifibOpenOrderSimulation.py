import unittest
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.DateUtils import getClosestDate, addToDate
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

from DateTime.DateTime import DateTime

class TestVifibOpenOrderSimulation(TestVifibSlapWebServiceMixin):

  def stepCheckSimulationMovement(self, sequence, **kw):
    # find related documents: open order, open order line,
    # subscription item, etc.
    person = self.portal.person_module['test_vifib_customer']
    open_order = self.portal.portal_catalog.getResultValue(
      default_destination_decision_uid=person.getUid(),
      validation_state='validated',
      portal_type="Open Sale Order")
    open_order_line_list = \
      open_order.contentValues(portal_type="Open Sale Order Line")
    self.assertEquals(1, len(open_order_line_list))
    open_order_line = open_order_line_list[0]
    hosting_subscription = \
      open_order_line.getAggregateValue(portal_type="Hosting Subscription")
    applied_rule = \
      hosting_subscription.getCausalityRelatedValue(portal_type="Applied Rule")
    self.assertEquals(
      "portal_rules/vifib_subscription_item_rule",
      applied_rule.getSpecialise())

    # check start date and stop date of the subscription item,
    # currently there is 1 month
    instance_setup_delivery = self.portal.portal_catalog.getResultValue(
      portal_type='Sale Packing List Line',
      default_aggregate_uid=sequence['software_instance_uid'],
      resource=self.portal.portal_preferences\
        .getPreferredInstanceSetupResource()).getParentValue()

    self.assertEqual('delivered', instance_setup_delivery.getSimulationState())
    start_date = None
    for item in self.portal.portal_workflow.getInfoFor(
      ob=instance_setup_delivery, name='history', wf_id='packing_list_workflow'):
      if item.get('simulation_state') == 'delivered':
        start_date = item.get('time')
        break

    start_date = getClosestDate(target_date=start_date, precision='day')
    while start_date.day() >= 29:
      start_date = addToDate(start_date, to_add={'day': -1})
    stop_date = addToDate(start_date, to_add={'month': 1})
    # check periodicity, should be first day of each month
    self.assertEquals(
      None, hosting_subscription.getPeriodicityMinuteFrequency())
    self.assertEquals(
      [0], hosting_subscription.getPeriodicityMinuteList())
    self.assertEquals(
      None, hosting_subscription.getPeriodicityHourFrequency())
    self.assertEquals(
      [0], hosting_subscription.getPeriodicityHourList())
    self.assertEquals(
      None, hosting_subscription.getPeriodicityDayFrequency())
    self.assertEquals(
      None, hosting_subscription.getPeriodicityMonthFrequency())
    self.assertEquals(
      [start_date.day()], hosting_subscription.getPeriodicityMonthDayList())
    self.assertEquals(
      None, hosting_subscription.getPeriodicityWeekFrequency())

    self.assertEqual(start_date, open_order_line.getStartDate())
    self.assertEqual(stop_date, open_order_line.getStopDate())

    simulation_movement_list = self.portal.portal_catalog(
      portal_type='Simulation Movement',
      parent_uid=applied_rule.getUid(),
      sort_on=(('movement.start_date', 'desc'),)
    )
    # Check that simulation is created by the periodicity for one month
    self.assertEquals(1,
                      len(simulation_movement_list))

    # Check the list of expected simulation
    idx = 0
    for simulation_movement in simulation_movement_list:
      # Check simulation movement property
      self.assertEquals(1.0,
        simulation_movement.getQuantity())
      self.assertEquals("unit/piece",
        simulation_movement.getQuantityUnit())
      self.assertEquals(0.83612040133800003,
        simulation_movement.getPrice())
      self.assertEquals("currency_module/EUR",
        simulation_movement.getPriceCurrency())
      # XXX supplier
      self.assertEquals("organisation_module/vifib_internet",
        simulation_movement.getSource())
      self.assertEquals("organisation_module/vifib_internet",
        simulation_movement.getSourceSection())
      # XXX customer
      self.assertEquals("person_module/test_vifib_customer",
        simulation_movement.getDestination())
      self.assertEquals("person_module/test_vifib_customer",
        simulation_movement.getDestinationSection())
      self.assertEquals(open_order_line.getSpecialise(),
        simulation_movement.getSpecialise())
      self.assertEquals("service_module/vifib_instance_subscription",
        simulation_movement.getResource())
      self.assertEquals("vifib/delivery",
        simulation_movement.getTradePhase())
      self.assertEquals(None,
                           simulation_movement.getAggregate(
                             portal_type="Computer Partition"))
      self.assertEquals(None,
                           simulation_movement.getAggregate(
                             portal_type="Software Instance"))
      self.assertEquals(hosting_subscription.getRelativeUrl(),
                           simulation_movement.getAggregate(
                             portal_type="Hosting Subscription"))
      self.assertEquals(None,
                           simulation_movement.getAggregate(
                             portal_type="Software Release"))
      self.assertEqual(start_date, simulation_movement.getStartDate())
      self.assertEqual(stop_date, simulation_movement.getStopDate())

      # delivered already...
      self.assertNotEqual(None, simulation_movement.getDelivery())
      self.assertEqual('Sale Packing List Line',
        simulation_movement.getDeliveryValue().getPortalType())
      # ...so no buildable
      self.assertFalse(simulation_movement.isBuildable())

      # delivered...
      self.assertEqual('delivered', simulation_movement.getSimulationState())
      # ...so invoice rule applied
      self.assertEqual(1,
        len(simulation_movement.contentValues(portal_type="Applied Rule")))
      # ...with one simulation movement
      invoice_applied_rule = simulation_movement.contentValues(
        portal_type="Applied Rule")[0]
      self.assertEqual(1, len(invoice_applied_rule.contentValues()))

      # check next simulation movement
      idx += 1

  def stepIncreaseOpenOrderCoverage(self, sequence, **kw):
    self.portal.portal_alarms.vifib_person_update_open_order.\
      Alarm_updatePersonOpenOrder(
      tag='test_tag', fixit=False,
      params={'stop_date': addToDate(getClosestDate(target_date=DateTime(),
        precision='month', before=1), month=3)})

  def stepCheckThreeTopLevelSimulationMovement(self, sequence, **kw):
    hosting_subscription = self.portal.portal_catalog.getResultValue(
      uid=sequence['hosting_subscription_uid'])
    # 2 open order lines:
    #  * one with start date and stop date
    #  * one with stop date extended by test
    self.assertEqual(2, self.portal.portal_catalog.countResults(
      default_aggregate_uid=sequence['hosting_subscription_uid'],
      portal_type='Open Sale Order Line')[0][0]
    )
    applied_rule = \
      hosting_subscription.getCausalityRelatedValue(portal_type="Applied Rule")
    self.assertEquals(
      "portal_rules/vifib_subscription_item_rule",
      applied_rule.getSpecialise())
    simulation_movement_list = self.portal.portal_catalog(
      portal_type='Simulation Movement',
      parent_uid=applied_rule.getUid(),
      sort_on=(('movement.start_date', 'desc'),)
    )
    # Check that simulation is created by the periodicity for two months
    self.assertEquals(3,
                      len(simulation_movement_list))

  def test_OpenOrder_request_changeSoftwareType(self):
    """
    Check that requesting the same instance with a different software type
    does not create a new instance
    """
    self.computer_partition_amount = 1
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_installed_computer_partition_sequence_string + """
      LoginERP5TypeTestCase

      CallVifibTriggerBuildAlarm
      CleanTic
      CallVifibUpdateDeliveryCausalityStateAlarm
      CleanTic
      CallDeliverSubscriptionSalePackingListAlarm
      CleanTic
      CallVifibExpandDeliveryLineAlarm
      CleanTic
      CallDeliverSubscriptionSalePackingListAlarm
      CleanTic

      CheckSimulationMovement
      SlapLogout

      LoginERP5TypeTestCase
      IncreaseOpenOrderCoverage
      Tic
      CheckThreeTopLevelSimulationMovement
      Logout

      LoginTestVifibCustomer
      SetSequenceSoftwareInstanceStateDestroyed
      PersonRequestSoftwareInstance
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListConfirmed
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceDestroyed
      Tic
      Tic # in order to update Open Order
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceCleanupSalePackingListDelivered
      CheckComputerPartitionIsFree
      CheckOpenOrderLineRemoved
      Logout

      LoginERP5TypeTestCase
      Tic # in order to call update simulation alarm of open order
      Tic
      CheckThreeTopLevelSimulationMovement
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibOpenOrderSimulation))
  return suite
