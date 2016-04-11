from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

hosting_subscription = context
assert hosting_subscription.getDefaultDestinationSection() == person_relative_url
person = hosting_subscription.getDefaultDestinationSectionValue()

slap_state = hosting_subscription.getSlapState()
if (slap_state in ['start_requested', 'stop_requested']):
  person.requestSoftwareInstance(
    state='destroyed',
    software_release=hosting_subscription.getUrlString(),
    software_title=hosting_subscription.getTitle(),
    software_type=hosting_subscription.getSourceReference(),
    instance_xml=hosting_subscription.getTextContent(),
    sla_xml=hosting_subscription.getSlaXml(),
    shared=hosting_subscription.isRootSlave()
  )
  return True
return False
