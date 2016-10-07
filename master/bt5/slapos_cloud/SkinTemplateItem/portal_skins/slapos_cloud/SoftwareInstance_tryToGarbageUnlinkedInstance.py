from zExceptions import Unauthorized
from DateTime import DateTime
from Products.ERP5Type.DateUtils import addToDate
if REQUEST is not None:
  raise Unauthorized

instance = context

def checkInstanceTree(instance_list):
  """
  Check if predecessor link is really removed to this instance
  """
  sub_instance_list = []
  if instance_list == []:
    return
  for item in instance_list:
    if item.getUid() == instance.getUid():
      return item
    sub_instance_list.extend(item.getPredecessorValueList())

  return checkInstanceTree(sub_instance_list)

if instance.getSlapState() == "destroy_requested":
  return

hosting_subscription = instance.getSpecialiseValue()
if hosting_subscription is None or \
    hosting_subscription.getSlapState() == "destroy_requested":
  return

root_instance = hosting_subscription.getPredecessorValue()
if root_instance is None:
  # Refuse to destroy root instance
  raise ValueError("Hosting Subscription %s has no root instance, this should "\
                   "not happen!!" % hosting_subscription.getRelativeUrl())

# If instance modificationDate is too recent, skip
# Delay destroy of unlinked instances
if instance.getModificationDate() - addToDate(DateTime(), {'minute': -1*delay_time}) > 0:
  return

if checkInstanceTree([root_instance]) is None:
  # This unlinked instance to parent should be removed
  is_slave = False
  if instance.getPortalType() == 'Slave Instance':
    is_slave = True
  promise_kw = {
    'instance_xml': instance.getTextContent(),
    'software_type': instance.getSourceReference(),
    'sla_xml': instance.getSlaXml(),
    'software_release': instance.getUrlString(),
    'shared': is_slave,
  }
  instance.requestDestroy(**promise_kw)
  # Unlink all children of this instance
  instance.edit(predecessor="", comment="Destroyed garbage collector!")

return instance.getRelativeUrl()
