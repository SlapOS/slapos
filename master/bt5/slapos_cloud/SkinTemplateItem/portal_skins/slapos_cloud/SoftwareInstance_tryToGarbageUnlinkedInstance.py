from zExceptions import Unauthorized
from DateTime import DateTime
from Products.ERP5Type.DateUtils import addToDate
if REQUEST is not None:
  raise Unauthorized

instance = context

if instance.getSlapState() == "destroy_requested":
  return

hosting_subscription = instance.getSpecialiseValue()
if hosting_subscription is None or \
    hosting_subscription.getSlapState() == "destroy_requested":
  return

# If instance modificationDate is too recent, skip
# Delay destroy of unlinked instances
if not delay_time:
  delay_time = 50
if instance.getModificationDate() - addToDate(DateTime(), {'minute': -1*delay_time}) > 0:
  return

if hosting_subscription.getTitle() == instance.getTitle():
  # Refuse to destroy root instance
  return

if instance.getPredecessorRelatedValue() is None:
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
