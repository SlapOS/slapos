if REQUEST.other['method'] != "POST":
  response.setStatus(405)
  return ""

person = context
person.requestSoftwareInstance(
  state=state,
  software_release=software_release,
  software_title=software_title,
  software_type=software_type,
  instance_xml=instance_xml,
  sla_xml=sla_xml,
  shared=int(shared)
)

return context.REQUEST.get('request_hosting_subscription').Base_redirect()
