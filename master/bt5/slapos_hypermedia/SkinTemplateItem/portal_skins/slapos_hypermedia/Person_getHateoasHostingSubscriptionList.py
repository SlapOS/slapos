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
elif context.getPortalType() != "Person":
  response.setStatus(403)
  return ""

import json
result_dict = {
  '_links': {
    "self": { "href": context.Base_getRequestUrl() },
    # XXX current type
    "index": {
      "href": "urn:jio:get:%s" % context.getRelativeUrl(),
      "title": "Person"
    },
    "content": [],
  },
}

for sql_obj in context.getPortalObject().portal_catalog(
                                               portal_type="Hosting Subscription",
                                               default_destination_section_uid=context.getUid(),
                                               validation_state="validated"
                                               ):
  obj = sql_obj.getObject()
  result_dict['_links']['content'].append({
    'href': '%s/ERP5Document_getHateoas' % obj.absolute_url(),
    'title': obj.getTitle()
  })

response.setHeader('Content-Type', mime_type)
return json.dumps(result_dict, indent=2)
