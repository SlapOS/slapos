if context.getPortalType() != 'Hosting Subscription' \
  or context.getValidationState() != 'validated' \
  or context.getSlapState() not in ['start_requested', 'stop_requested'] \
  or context.getTitle() in context.getPredecessorTitleList():
  # nothing to do
  return

context.requestInstance(
  software_release=context.getUrlString(),
  software_title=context.getTitle(),
  software_type=context.getSourceReference(),
  instance_xml=context.getTextContent(),
  sla_xml=context.getSlaXml(),
  shared=context.isRootSlave(),
  state={'start_requested': 'started', 'stop_requested': 'stopped'}[context.getSlapState()],
)
