""" This script is required due the ValueError, should be more HTTP friendly.
"""
person = context.ERP5Site_getAuthenticatedMemberPersonValue()
request = context.REQUEST
response = request.RESPONSE
import json


if person is None:
  response.setStatus(403)
else:
  try:
    person.revokeCertificate()
    return json.dumps(True)
  except ValueError:
    return json.dumps(False)
