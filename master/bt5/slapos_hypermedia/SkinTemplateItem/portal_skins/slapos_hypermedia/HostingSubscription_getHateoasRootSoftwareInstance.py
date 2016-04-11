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
elif context.getPortalType() != "Hosting Subscription":
  response.setStatus(403)
  return ""

instance_list = context.getPredecessorValueList()
for instance in instance_list:
  if instance.getTitle() == context.getTitle():
    root_instance = instance
    break
else:
  raise Exception('Root instance not found.')

import json
result_dict = {
  '_links': {
    "self": { "href": context.Base_getRequestUrl() },
    "content": [
       {'href': '%s/ERP5Document_getHateoas' % root_instance.getAbsoluteUrl()},
     ],
    "index": {
      "href": "urn:jio:get:%s" % context.getRelativeUrl(),
      "title": "Hosting Subscription"
    },
  },
}

response.setHeader('Content-Type', mime_type)
return json.dumps(result_dict, indent=2)
