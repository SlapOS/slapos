import json

portal = context.getPortalObject()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()

if person is None:
  raise ValueError("User Not Found")

document_path = ""

if context.getPortalType() in ["Hosting Subscription", "Computer"]:
  document_path = "/%s" % context.getRelativeUrl()

web_site = context.getWebSiteValue()
request_url = "%s/feed%s" % (web_site.absolute_url(), document_path)

# XXX - Cannot search in catalog with parameter url_string
access_token = None
for token_item in portal.portal_catalog(
  portal_type="Restricted Access Token",
  default_agent_uid=person.getUid(),
  validation_state='validated'
  ):
  if token_item.getUrlString() == request_url:
    access_token = token_item
    reference = access_token.getReference()
    break

if access_token is None:
  access_token = portal.access_token_module.newContent(
    portal_type="Restricted Access Token",
    url_string=request_url,
    url_method="GET",
  )
  access_token.setAgentValue(person)
  reference = access_token.getReference()  
  access_token.validate()

url = "%s/feed%s?portal_skin=RSS&access_token=%s&access_token_secret=%s" % (
        web_site.absolute_url(),
        document_path,
        access_token.getId(),
        reference)

request = context.REQUEST
response = request.RESPONSE
response.setHeader('Content-Type', "application/json")
return json.dumps({'restricted_access_url': url})
