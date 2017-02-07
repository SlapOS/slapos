from DateTime import DateTime
from Products.ERP5Type.DateUtils import addToDate

hosting_subscription = context
portal = context.getPortalObject()

if portal.ERP5Site_isSupportRequestCreationClosed():
  # Stop ticket creation
  return

date_check_limit = addToDate(DateTime(), to_add={'hour': -1})

if (date_check_limit - hosting_subscription.getCreationDate()) < 0:
  # Too early to check
  return

#if not source_instance:
#  return

software_instance_list = hosting_subscription.getSpecialiseRelatedValueList(
                 portal_type=["Software Instance", "Slave Instance"])

has_newest_allocated_instance = False
has_unallocated_instance = False
failing_instance = None

# Check if at least one software Instance is Allocated
for instance in software_instance_list:
  if instance.getSlapState() not in ["start_requested", "stop_requested"]:
    continue

  if (date_check_limit - instance.getCreationDate()) < 0:
    continue

  computer_partition = instance.getAggregateValue()
  if computer_partition is not None:
    has_newest_allocated_instance = True
    if instance.getPortalType() == "Software Instance" and \
        computer_partition.getParentValue().getAllocationScope() in ["open/friend", "open/public"] and \
        instance.SoftwareInstance_hasReportedError():
      return context.HostingSubscription_createSupportRequestEvent(
        instance, 'slapos-crm-hosting-subscription-instance-state.notification')
  else:
    has_unallocated_instance = True
    failing_instance = instance

  if has_unallocated_instance and has_newest_allocated_instance:
    return context.HostingSubscription_createSupportRequestEvent(
      failing_instance, 'slapos-crm-hosting-subscription-instance-allocation.notification')

return
