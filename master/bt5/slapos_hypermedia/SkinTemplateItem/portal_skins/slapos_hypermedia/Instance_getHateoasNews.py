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

import json

memcached_dict = context.getPortalObject().portal_memcached.getMemcachedDict(
  key_prefix='slap_tool',
  plugin_path='portal_memcached/default_memcached_plugin')
try:
  d = memcached_dict[context.getReference()]
except KeyError:
  d = {
    "user": "SlapOS Master",
    "text": "#error no data found for %s" % context.getReference()
  }
else:
  d = json.loads(d)

result_dict = {
  'news': [d],
  '_links': {
    "self": { "href": context.Base_getRequestUrl() },
    # XXX current type
    "index": {
      "href": "urn:jio:get:%s" % context.getRelativeUrl(),
      "title": "Software Instance"
    },
  },
}

response.setHeader('Content-Type', mime_type)
return json.dumps(result_dict, indent=2)
