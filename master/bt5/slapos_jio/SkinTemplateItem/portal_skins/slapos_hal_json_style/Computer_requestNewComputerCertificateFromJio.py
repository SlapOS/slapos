if REQUEST.other['method'] != "POST":
  response.setStatus(405)
  return ""

import json

computer = context
request = context.REQUEST
response = REQUEST.RESPONSE

context.Base_prepareCorsResponse(RESPONSE=response)

computer.generateCertificate()

return json.dumps({
  'certificate': request.get('computer_certificate'),
  'key': request.get('computer_key')
}, indent=2)
