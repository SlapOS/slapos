if REQUEST.other['method'] != "POST":
  response.setStatus(405)
  return ""

if action not in ("started", "stopped", "destroyed"):
  raise NotImplementedError, "Unknown action %s" % action

person = context.getDestinationSectionValue()
person.requestSoftwareInstance(
  state=action,
  software_release=context.getUrlString(),
  software_title=context.getTitle(),
  software_type=context.getSourceReference(),
  instance_xml=context.getTextContent(),
  sla_xml=context.getSlaXml(),
  shared=context.isRootSlave()
)

context.Base_redirect()
