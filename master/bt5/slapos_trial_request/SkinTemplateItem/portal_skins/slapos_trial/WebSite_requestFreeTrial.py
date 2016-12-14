from zExceptions import Unauthorized
from AccessControl import getSecurityManager
if REQUEST is None:
  raise Unauthorized

request = context.REQUEST
response = REQUEST.RESPONSE
portal = context.getPortalObject()

if REQUEST.other['method'] != "GET":
  raise ValueError("Method is not GET")

else:
  if default_email_text is None:
    return context.Base_redirect("WebSite_viewFreeTrialForm", keep_items={"portal_status_message", "Please Provide some email!"})

  return context.WebSite_requestFreeTrialProxy(software_release, default_email_text, batch_mode=0)
