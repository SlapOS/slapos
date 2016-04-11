from Products.ERP5Type.DateUtils import addToDate, getClosestDate
from DateTime import DateTime

portal = context.getPortalObject()
now = DateTime()
person = context
tag = '%s_%s' % (person.getUid(), script.id)
activate_kw = {'tag': tag}
if portal.portal_activities.countMessageWithTag(tag) > 0:
  # nothing to do
  return

def newOpenOrder(open_sale_order):
  open_order_edit_kw = {
    'effective_date': DateTime(),
    'activate_kw': activate_kw,
  }
  if open_sale_order is None:
    open_sale_order_template = portal.restrictedTraverse(
        portal.portal_preferences.getPreferredOpenSaleOrderTemplate())
    new_open_sale_order = open_sale_order_template.Base_createCloneDocument(batch_mode=1)
    open_order_edit_kw.update({
      'destination': person.getRelativeUrl(),
      'destination_decision': person.getRelativeUrl(),
      'title': "%s SlapOS Subscription" % person.getTitle(),
    })
  else:
    new_open_sale_order = open_sale_order.Base_createCloneDocument(batch_mode=1)
    open_sale_order.setExpirationDate(now, activate_kw=activate_kw)
  new_open_sale_order.edit(**open_order_edit_kw)
  new_open_sale_order.order(activate_kw=activate_kw)
  new_open_sale_order.validate(activate_kw=activate_kw)
  return new_open_sale_order

def storeWorkflowComment(document, comment):
  portal.portal_workflow.doActionFor(document, 'edit_action', comment=comment)

def calculateOpenOrderLineStopDate(open_order_line, hosting_subscription):
  end_date = hosting_subscription.HostingSubscription_calculateSubscriptionStopDate()
  if end_date is None: 
    # Be sure that start date is different from stop date
    next_stop_date = hosting_subscription.getNextPeriodicalDate(hosting_subscription.HostingSubscription_calculateSubscriptionStartDate())
    current_stop_date = next_stop_date
    while next_stop_date < now:
      # Return result should be < now, it order to provide stability in simulation (destruction if it happen should be >= now)
      current_stop_date = next_stop_date
      next_stop_date = \
         hosting_subscription.getNextPeriodicalDate(current_stop_date)
    return addToDate(current_stop_date, to_add={'second': -1})
  else:
    stop_date = end_date
  return stop_date

# Prevent concurrent transaction to update the open order
context.serialize()

# First, check the existing open order. Does some lines need to be removed, updated?
open_sale_order_list = portal.portal_catalog(
  default_destination_uid=person.getUid(),
  portal_type="Open Sale Order",
  validation_state="validated",
  limit=2,
)
open_sale_order_count = len(open_sale_order_list)
if open_sale_order_count == 0:
  open_sale_order = None
elif open_sale_order_count == 1:
  open_sale_order = open_sale_order_list[0].getObject()
else:
  raise ValueError, "Too many open order '%s' found: %s" % (person.getRelativeUrl(), [x.path for x in open_sale_order_list])

delete_line_list = []
add_line_list = []

updated_hosting_subscription_dict = {}
deleted_hosting_subscription_dict = {}

if open_sale_order is not None:
  for open_order_line in open_sale_order.contentValues(
                           portal_type='Open Sale Order Line'):
    current_start_date = open_order_line.getStartDate()
    current_stop_date = open_order_line.getStopDate()

    # Prevent mistakes
    assert current_start_date is not None
    assert current_stop_date is not None
    assert current_start_date < current_stop_date

    hosting_subscription = open_order_line.getAggregateValue(portal_type='Hosting Subscription')
    assert current_start_date == hosting_subscription.HostingSubscription_calculateSubscriptionStartDate()

    # First check if the hosting subscription has been correctly simulated (this script may run only once per year...)
    stop_date = calculateOpenOrderLineStopDate(open_order_line, hosting_subscription)
    if current_stop_date != stop_date:
      # Bingo, new subscription to generate
      open_order_line.edit(
        stop_date=stop_date,
        activate_kw=activate_kw)
      storeWorkflowComment(open_order_line,
                           'Stop date updated to %s' % stop_date)

    if hosting_subscription.getSlapState() == 'destroy_requested':
      # Line should be deleted
      assert hosting_subscription.getCausalityState() == 'diverged'
      delete_line_list.append(open_order_line.getId())
      hosting_subscription.converge(comment="Last open order: %s" % open_order_line.getRelativeUrl())
      deleted_hosting_subscription_dict[hosting_subscription.getRelativeUrl()] = None
      updated_hosting_subscription_dict[hosting_subscription.getRelativeUrl()] = None

    elif (hosting_subscription.getCausalityState() == 'diverged'):
      hosting_subscription.converge(comment="Nothing to do on open order.")
      updated_hosting_subscription_dict[hosting_subscription.getRelativeUrl()] = None

# Time to check the open order line to add (remaining diverged Hosting
# Subscription normally)
for hosting_subscription in portal.portal_catalog(
    portal_type='Hosting Subscription',
    default_destination_section_uid=context.getUid(),
    causality_state="diverged"):
  hosting_subscription = hosting_subscription.getObject()
  if hosting_subscription.getCausalityState() == 'diverged':
    # Simply check that it has never been simulated
    assert len(portal.portal_catalog(
      portal_type='Open Sale Order Line',
      default_aggregate_uid=hosting_subscription.getUid(),
      limit=1)) == 0

    # Let's add
    add_line_list.append(hosting_subscription)
  else:
    # Should be in the list of lines to remove
    assert (hosting_subscription.getRelativeUrl() in deleted_hosting_subscription_dict) or \
      (hosting_subscription.getRelativeUrl() in updated_hosting_subscription_dict)

manual_archive = False
if (add_line_list):
  # No need to create a new open order to add lines
  if open_sale_order is None:
    open_sale_order = newOpenOrder(None)
    manual_archive = True

  open_order_explanation = ""
  # Add lines
  added_line_list = []
  open_sale_order_line_template = portal.restrictedTraverse(
      portal.portal_preferences.getPreferredOpenSaleOrderLineTemplate())
  for hosting_subscription in add_line_list:
    open_sale_order_line = open_sale_order_line_template.Base_createCloneDocument(batch_mode=1,
        destination=open_sale_order)
    start_date = hosting_subscription.HostingSubscription_calculateSubscriptionStartDate()
    open_sale_order_line.edit(
      activate_kw=activate_kw,
      title=hosting_subscription.getTitle(),
      start_date=start_date,
      stop_date=calculateOpenOrderLineStopDate(open_sale_order_line, hosting_subscription),
      aggregate_value=hosting_subscription,
      )
    storeWorkflowComment(open_sale_order_line, "Created for %s" % hosting_subscription.getRelativeUrl())
    if (hosting_subscription.getSlapState() == 'destroy_requested'):
      # Added line to delete immediately
      delete_line_list.append(open_sale_order_line.getId())
      hosting_subscription.converge(comment="Last open order: %s" % open_sale_order_line.getRelativeUrl())
    else:
      hosting_subscription.converge(comment="First open order: %s" % open_sale_order_line.getRelativeUrl())
    added_line_list.append(open_sale_order_line.getId())
  open_order_explanation += "Added %s." % str(added_line_list)

new_open_sale_order = None
if (delete_line_list):
  # All Verifications done. Time to clone/create open order
  new_open_sale_order = newOpenOrder(open_sale_order)
  if manual_archive == True:
    open_sale_order.archive()

  open_order_explanation = ""
  # Remove lines
  new_open_sale_order.deleteContent(delete_line_list)
  open_order_explanation += "Removed %s." % str(delete_line_list)

  storeWorkflowComment(new_open_sale_order, open_order_explanation)
