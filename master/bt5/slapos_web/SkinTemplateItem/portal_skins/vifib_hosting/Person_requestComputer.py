import json
portal = context.getPortalObject()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()

request = context.REQUEST
response = request.RESPONSE

if person is None:
  response.setStatus(403)
else:
  request_kw = dict(computer_title=title)
  person.requestComputer(**request_kw)
  computer = context.restrictedTraverse(context.REQUEST.get('computer'))
  computer.generateCertificate()

  return json.dumps({
    "certificate" : request.get('computer_certificate'),
    "key" : request.get('computer_key'),
    "reference": computer.getReference(),
    "relative_url": computer.getRelativeUrl()
  })
