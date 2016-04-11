if REQUEST.other['method'] != "POST":
  response.setStatus(405)
  return ""

context.getAggregateValue(portal_type='Computer').requestSoftwareRelease(software_release_url=context.getUrlString(), state='destroyed')

return ""
