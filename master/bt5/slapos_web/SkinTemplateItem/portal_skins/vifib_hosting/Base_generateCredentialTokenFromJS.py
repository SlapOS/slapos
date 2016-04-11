import json

portal = context.getPortalObject()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()

# Revoke user certificate
try:
  person.revokeCertificate()
except ValueError:
  pass

web_site = context.getWebSiteValue()
request_method = "POST"
request_url = "%s/%s" % (web_site.absolute_url(), "myspace/my_account/request-a-certificate/WebSection_requestNewCertificate")

access_token = portal.access_token_module.newContent(
  portal_type="One Time Restricted Access Token",
  agent_value=person,
  url_string=request_url,
  url_method="POST",
)
access_token.validate()

request = context.REQUEST
response = request.RESPONSE
response.setHeader('Content-Type', "application/json")
return json.dumps({'access_token': access_token.getId()})
