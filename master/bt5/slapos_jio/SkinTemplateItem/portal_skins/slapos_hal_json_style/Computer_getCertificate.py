import json
request = context.REQUEST
try:
  context.generateCertificate()
  return json.dumps({
    "certificate" : request.get('computer_certificate'),
    "key" : request.get('computer_key')
  })
except ValueError:
  return json.dumps(False)
