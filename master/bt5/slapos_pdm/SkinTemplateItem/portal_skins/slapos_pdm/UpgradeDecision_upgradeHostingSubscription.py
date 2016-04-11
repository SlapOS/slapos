if context.getSimulationState() != 'started':
  # Update Decision is not on started state, Upgrade is not possible!
  return False

hosting_subscription = context.UpgradeDecision_getHostingSubscription()
software_release = context.UpgradeDecision_getSoftwareRelease()

if hosting_subscription is None:
  return False

if software_release is None:
  return False 

software_release_url = software_release.getUrlString()

person = hosting_subscription.getDestinationSectionValue(portal_type="Person")

status = hosting_subscription.getSlapState()

if status == "start_requested":
  state = "started"
elif status == "stop_requested":
  state = "stopped"
elif status == "destroy_requested":
  state = "destroyed"
  
person.requestSoftwareInstance(
  state=state,
  software_release=software_release_url,
  software_title=hosting_subscription.getTitle(),
  software_type=hosting_subscription.getSourceReference(),
  instance_xml=hosting_subscription.getTextContent(),
  sla_xml=hosting_subscription.getSlaXml(),
  shared=hosting_subscription.isRootSlave()
)

context.stop()

return True
