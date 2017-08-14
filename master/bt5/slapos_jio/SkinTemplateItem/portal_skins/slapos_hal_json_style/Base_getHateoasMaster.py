from zExceptions import Unauthorized
from AccessControl import getSecurityManager

if REQUEST is None:
  raise Unauthorized

response = REQUEST.RESPONSE
mime_type = 'application/hal+json'

if REQUEST.other['method'] != "GET":
  response.setStatus(405)
  return ""
elif mime_type != context.Base_handleAcceptHeader([mime_type]):
  response.setStatus(406)
  return ""

import json
result_dict = json.loads(context.ERP5Document_getHateoas(REQUEST))

portal = context.getPortalObject()

person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
if person is not None:
  result_dict['_links']['me'] = {
    "href": "urn:jio:get:%s" % person.getRelativeUrl(),
  }

else:
  user = str(portal.portal_membership.getAuthenticatedMember())
  if user != "Anonymous User":
    user_document = context.ERP5Site_getUserDocument(user)
    result_dict['_links']['me'] = {
      'href': 'urn:jio:get:%s' % user_document.getRelativeUrl(),
    }

response.setHeader('Content-Type', mime_type)
return json.dumps(result_dict, indent=2)
