if REQUEST.other['method'] != "POST":
  response.setStatus(405)
  return ""

computer = context
response = REQUEST.RESPONSE
context.Base_prepareCorsResponse(RESPONSE=response)

computer.revokeCertificate()

return ""
