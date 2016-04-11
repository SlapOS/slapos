from DateTime import DateTime
portal = context.getPortalObject()
hosting_subscription = context

now = DateTime()

if hosting_subscription.getDestinationSectionValue().getReference() == 'seleniumtester' and \
  hosting_subscription.getModificationDate() < (now - 1):

  person = hosting_subscription.getDestinationSectionValue(portal_type="Person")
  person.requestSoftwareInstance(
    software_release=hosting_subscription.getUrlString(),
    instance_xml=hosting_subscription.getTextContent(),
    software_type=hosting_subscription.getSourceReference(),
    sla_xml=hosting_subscription.getSlaXml(),
    shared=hosting_subscription.getRootSlave(),
    state="destroyed",
    software_title=hosting_subscription.getTitle(),
    comment='Requested by clenaup alarm', 
    activate_kw={'tag': tag}
  )
