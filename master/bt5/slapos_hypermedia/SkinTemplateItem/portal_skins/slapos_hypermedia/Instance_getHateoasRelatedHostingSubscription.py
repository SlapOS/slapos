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
elif context.getPortalType() not in ["Software Instance", "Slave Instance"]:
  response.setStatus(403)
  return ""

if context.getSlapState() == "stop_requested":
  state = 'stopped'
elif context.getSlapState() == "start_requested":
  state = 'started'
else:
  state = 'destroyed'

import json
result_dict = {
  '_links': {
    "self": { "href": context.Base_getRequestUrl() },
    "index": {
      "href": "urn:jio:get:%s" % context.getRelativeUrl(),
      "title": "Software Instance",
    },
    'action_object_jump': {
      "href": "%s/ERP5Document_getHateoas" %  context.getSpecialiseValue().getAbsoluteUrl(),
      "title": "Hosting Subscription",
    }
  },
}

response.setHeader('Content-Type', mime_type)
return json.dumps(result_dict, indent=2)
