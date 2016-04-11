from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

from Products.ERP5Type.DateUtils import addToDate, getClosestDate

hosting_subscription = context
portal = context.getPortalObject()

workflow_item_list = portal.portal_workflow.getInfoFor(
  ob=hosting_subscription,
  name='history',
  wf_id='instance_slap_interface_workflow')
start_date = None
for item in workflow_item_list:
  start_date = item.get('time')
  if start_date:
    break

if start_date is None:
  # Compatibility with old Hosting subscription
  start_date = hosting_subscription.getCreationDate()

start_date = getClosestDate(target_date=start_date, precision='day')

return start_date
