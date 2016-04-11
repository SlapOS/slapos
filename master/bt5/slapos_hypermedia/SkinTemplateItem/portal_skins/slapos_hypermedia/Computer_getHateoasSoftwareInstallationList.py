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
elif context.getPortalType() != "Computer":
  response.setStatus(403)
  return ""

import json
result_dict = {
  '_links': {
    "self": { "href": context.Base_getRequestUrl() },
    "index": {
      "href": "urn:jio:get:%s" % context.getRelativeUrl(),
      "title": "Computer"
    },
    "content": [],
  },
}

for sql_obj in context.getPortalObject().portal_catalog(
                                               portal_type='Software Installation',
                                               default_aggregate_uid=context.getUid(),
                                               validation_state='validated',
                                               ):
  obj = sql_obj.getObject()
  result_dict['_links']['content'].append({
    'href': '%s/ERP5Document_getHateoas' % obj.absolute_url(),
    'title': obj.getUrlString()
  })

response.setHeader('Content-Type', mime_type)
return json.dumps(result_dict, indent=2)
