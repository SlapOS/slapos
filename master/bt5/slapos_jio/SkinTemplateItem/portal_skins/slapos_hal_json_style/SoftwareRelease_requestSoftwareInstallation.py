import json
portal = context.getPortalObject()

computer = portal.restrictedTraverse(computer)

computer.requestSoftwareRelease(
  software_release_url=context.getUrlString(),
  state='available')

return json.dumps(context.REQUEST.get('software_installation_url'))
