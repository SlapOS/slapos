if instance_xml is None:
  instance_xml = context.getTextContent()
if state is None:
  state = {'start_requested': 'started', 
           'destroy_requested': 'destroyed', 
           'stop_requested': 'stopped'}[context.getSlapState()]

person = context.getDestinationSectionValue()
person.requestSoftwareInstance(
  state=state,
  software_release=context.getUrlString(),
  software_title=context.getTitle(),
  software_type=context.getSourceReference(),
  instance_xml=instance_xml,
  sla_xml=context.getSlaXml(),
  shared=context.isRootSlave()
)
