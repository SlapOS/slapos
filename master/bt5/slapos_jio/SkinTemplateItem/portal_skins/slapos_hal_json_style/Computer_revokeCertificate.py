import json
try:
  context.revokeCertificate()
  return json.dumps(True)
except ValueError:
  return json.dumps(False)
