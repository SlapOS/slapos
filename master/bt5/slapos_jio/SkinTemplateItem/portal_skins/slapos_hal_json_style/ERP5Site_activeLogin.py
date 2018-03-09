from Products.ERP5Type.Message import translateString
from ZTUtils import make_query

portal = context.getPortalObject()

assert key
mail_message = portal.ERP5Site_unrestrictedSearchMessage(key=key)

came_from = portal.absolute_url() + "/#!login?p.page=slapos{&n.me}"
credential_request = mail_message.getFollowUpValue()
if credential_request.getValidationState() in ('submitted', 'accepted'):
  message = translateString("Your account is already active.")
else:
  credential_request.submit(comment=translateString('Created by subscription form'))
  mail_message.deliver()
  message = translateString("Your account is being activated. You will receive an e-mail when activation is complete.")

url = "%s/login_form?portal_status_message=%s&%s" % (
  context.getWebSectionValue().absolute_url(),
  message,
  make_query({"came_from": came_from})
)

context.REQUEST.RESPONSE.setHeader('Location', url)
context.REQUEST.RESPONSE.setStatus(303)
