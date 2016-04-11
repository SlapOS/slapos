from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

instance = context
portal = context.getPortalObject()

if instance.getValidationState() != 'validated' \
  or instance.getSlapState() not in ('start_requested', 'stop_requested') \
  or instance.getAggregateValue(portal_type='Computer Partition') is not None:
  return

latest_comment = portal.portal_workflow.getInfoFor(instance, 'comment', wf_id='edit_workflow')
if latest_comment != 'Allocation failed: no free Computer Partition':
  # No nothing if allocation alarm didn't run on it
  return

latest_edit_time = portal.portal_workflow.getInfoFor(instance, 'time', wf_id='edit_workflow')
if (int(DateTime()) - int(latest_edit_time)) < 259200:
  # Allow 3 days gap betweeb latest allocation try and deletion
  return

# Only destroy if the instance is the only one in the tree
hosting_subscription = instance.getSpecialiseValue("Hosting Subscription")
if (hosting_subscription.getPredecessor() != instance.getRelativeUrl()):
  return
if (len(hosting_subscription.getPredecessorList()) != 1):
  return
instance_list = portal.portal_catalog(
  portal_type=["Software Instance", "Slave Instance"],
  default_specialise_uid=hosting_subscription.getUid(),
  limit=2)
if len(instance_list) != 1:
  return

# OK, destroy hosting subscription
hosting_subscription.requestDestroy(
  software_release=hosting_subscription.getUrlString(),
  software_title=hosting_subscription.getTitle(),
  software_type=hosting_subscription.getSourceReference(),
  instance_xml=hosting_subscription.getTextContent(),
  sla_xml=hosting_subscription.getSlaXml(),
  shared=hosting_subscription.isRootSlave(),
  state='destroyed',
  comment="Garbage collect %s not allocated for more than 3 days" % instance.getRelativeUrl(),
)
hosting_subscription.archive()
