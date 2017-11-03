person = context.ERP5Site_getAuthenticatedMemberPersonValue()
request = context.REQUEST
response = request.RESPONSE

import json

if person is None:
  response.setStatus(403)
  return {}

try:
  return json.dumps(person.getCertificate())
  # Certificate is Created
except ValueError:
  # Certificate was already requested, please revoke existing one.
  return json.dumps(False)
