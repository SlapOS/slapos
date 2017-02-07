#
# XXX This ticket contains dupplicated coded found arround SlapOS
#     It is required to rewrite this in a generic way. 
#     See also: HostingSubscription_checkSoftwareInstanceState
#     See also: Computer_checkState
#

from DateTime import DateTime
import json

from Products.ERP5Type.DateUtils import addToDate

if context.getSimulationState() == "invalidated":
  return "Closed Ticket"


portal = context.getPortalObject()

document = context.getAggregateValue()

if document is None:
  return True

aggregate_portal_type = document.getPortalType()

memcached_dict = context.getPortalObject().portal_memcached.getMemcachedDict(
  key_prefix='slap_tool',
  plugin_path='portal_memcached/default_memcached_plugin')

if aggregate_portal_type == "Computer":
  try:
    d = memcached_dict[document.getReference()]
    d = json.loads(d)
    last_contact = DateTime(d.get('created_at'))
    if (DateTime() - last_contact) < 0.01:
      return "All OK, latest contact: %s " % last_contact
    else:
      return "Problem, latest contact: %s" % last_contact
  except KeyError:
    return "No Contact Information"

if aggregate_portal_type == "Hosting Subscription":
  message_list = []
  hosting_subscription = document

  software_instance_list = hosting_subscription.getSpecialiseRelatedValueList(
                 portal_type=["Software Instance", "Slave Instance"])

  has_newest_allocated_instance = False
  has_unallocated_instance = False
  failing_instance = None

  # Check if at least one software Instance is Allocated
  for instance in software_instance_list:
    if instance.getSlapState() not in ["start_requested", "stop_requested"]:
      continue

    if instance.getAggregateValue() is not None:
      has_newest_allocated_instance = True
      computer = instance.getAggregateValue().getParentValue()
      if instance.getPortalType() == "Software Instance" and \
          computer.getAllocationScope() in ["open/public", "open/friend"] and \
          instance.SoftwareInstance_hasReportedError():
        message_list.append("%s has error (%s, %s at %s scope %s)" % (instance.getReference(), instance.getTitle(), 
                                                                      instance.getUrlString(), computer.getReference(),
                                                                      computer.getAllocationScope()))
      if instance.getPortalType() == "Software Instance" and \
          instance.getAggregateValue().getParentValue().getAllocationScope() in ["closed/outdated", "open/personal"]: 
        message_list.append("%s on a %s computer" % (instance, computer.getAllocationScope()) )
    else:
      message_list.append("%s is not allocated" % instance)
  return ",".join(message_list)

return None
