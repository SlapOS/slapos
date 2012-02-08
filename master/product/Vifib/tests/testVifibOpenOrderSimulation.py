import unittest
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.DateUtils import getClosestDate, addToDate
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

from DateTime.DateTime import DateTime

def generateTimeFrameList(start_date):
  expected_time_frame_list = [start_date]
  current = \
    getClosestDate(target_date=start_date, precision='month', before=0)
  for m in range(0, 12):
    expected_time_frame_list.append(addToDate(current, month=m))
  return expected_time_frame_list

class TestVifibOpenOrderSimulation(TestVifibSlapWebServiceMixin):

  def stepCheckSimulationMovement(self, sequence, **kw):
    # find related documents: open order, open order line,
    # subscription item, etc.
    person = self.portal.person_module['test_vifib_customer']
    open_order = \
      person.getDestinationDecisionRelatedValue(portal_type="Open Sale Order")
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
      [1], hosting_subscription.getPeriodicityMonthDayList())
    self.assertEquals(
      None, hosting_subscription.getPeriodicityWeekFrequency())

    # check start date and stop date of the subscription item,
    # currently there are 2 months
    now = DateTime()
    start_date = \
      getClosestDate(target_date=now, precision='day', before=1)
    self.assertEquals(
      start_date.year(), open_order_line.getStartDate().year())
    self.assertEquals(
      start_date.month(), open_order_line.getStartDate().month())
    self.assertEquals(
      start_date.day(), open_order_line.getStartDate().day())
    self.assertEquals(
      0, open_order_line.getStartDate().hour())
    self.assertEquals(
      0, open_order_line.getStartDate().minute())
    self.assertEquals(
      0.0, open_order_line.getStartDate().second())
    stop_date = addToDate(
      getClosestDate(target_date=now, precision='month', before=1), month=2)
    self.assertEquals(
      stop_date.year(), open_order_line.getStopDate().year())
    self.assertEquals(
      stop_date.month(), open_order_line.getStopDate().month())
    self.assertEquals(
      stop_date.day(), open_order_line.getStopDate().day())
    self.assertEquals(
      0, open_order_line.getStopDate().hour())
    self.assertEquals(
      0, open_order_line.getStopDate().minute())
    self.assertEquals(
      0.0, open_order_line.getStopDate().second())

    # Calculate the list of time frames
    expected_time_frame_list = generateTimeFrameList(start_date)

    # test the test: have we generated 12th next months coverage?
    self.assertEqual(13, len(expected_time_frame_list))

    simulation_movement_list = self.portal.portal_catalog(
      portal_type='Simulation Movement',
      parent_uid=applied_rule.getUid(),
      sort_on=(('movement.start_date', 'desc'),)
    )
    # Check that simulation is created by the periodicity for two months
    self.assertEquals(2,
                      len(simulation_movement_list))

    # Check the list of expected simulation
    idx = 0
    for simulation_movement in simulation_movement_list:
      expected_start_date = expected_time_frame_list[idx]
      expected_stop_date = expected_time_frame_list[idx+1]
      # Check simulation movement property
      self.assertEquals(1.0,
        simulation_movement.getQuantity())
      self.assertEquals("unit/piece",
        simulation_movement.getQuantityUnit())
      self.assertEquals(1.0,
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
      self.assertEqual(expected_start_date, simulation_movement.getStartDate())
      self.assertEqual(expected_stop_date, simulation_movement.getStopDate())

      # delivered already
      self.assertNotEqual(None, simulation_movement.getDelivery())
      self.assertEqual('Sale Packing List Line',
        simulation_movement.getDeliveryValue().getPortalType())
      # packing list shall be buildable
      self.assertFalse(simulation_movement.isBuildable())

      # no invoice movements on this level
      applied_rule_invoice_list = \
        simulation_movement.contentValues(portal_type="Applied Rule")
      # check next simulation movement
      idx += 1

  def stepIncreaseOpenOrderCoverage(self, sequence, **kw):
    person = self.portal.person_module['test_vifib_customer']
    open_order = \
      person.getDestinationDecisionRelatedValue(portal_type="Open Sale Order")
    open_order_line_list = \
      open_order.contentValues(portal_type="Open Sale Order Line")
    self.assertEquals(1, len(open_order_line_list))
    open_order_line = open_order_line_list[0]
    self.portal.portal_alarms.vifib_update_open_sale_order_line.activeSense(
      params={'stop_date': addToDate(getClosestDate(target_date=DateTime(),
        precision='month', before=1), month=3)})


  def stepCheckThreeTopLevelSimulationMovement(self, sequence, **kw):
    person = self.portal.person_module['test_vifib_customer']
    open_order = \
      person.getDestinationDecisionRelatedValue(portal_type="Open Sale Order")
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
      CheckSimulationMovement
      Tic
      SlapLogout

      LoginERP5TypeTestCase
      IncreaseOpenOrderCoverage
      Tic
      CheckThreeTopLevelSimulationMovement
      Logout

      LoginTestVifibCustomer
      RequestSoftwareInstanceStart
      Tic
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout
      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibOpenOrderSimulation))
  return suite
