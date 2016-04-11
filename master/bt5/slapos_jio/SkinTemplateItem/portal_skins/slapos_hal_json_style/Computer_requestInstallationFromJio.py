if REQUEST.other['method'] != "POST":
  response.setStatus(405)
  return ""

computer = context
computer.requestSoftwareRelease(software_release_url=software_release, state='available')

return context.REQUEST.get('software_installation_url').Base_redirect()
