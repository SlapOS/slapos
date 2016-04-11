from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

from Products.ERP5Type.DateUtils import addToDate, getClosestDate

hosting_subscription = context
portal = context.getPortalObject()

start_date = context.HostingSubscription_calculateSubscriptionStartDate()

workflow_item_list = portal.portal_workflow.getInfoFor(
  ob=hosting_subscription,
  name='history',
  wf_id='instance_slap_interface_workflow')
result_date = None
for item in workflow_item_list:
  if item.get('slap_state') == 'destroy_requested':
    end_date = item.get('time')
    result_date = getClosestDate(target_date=end_date, precision='day')
    if result_date <= end_date:
      result_date = addToDate(result_date, to_add={'day': 1})
    break

return result_date
