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
elif context.getPortalType() not in ["Software Installation"]:
  response.setStatus(403)
  return ""
else:

  if context.getSlapState() == "stop_requested":
    state = 'stopped'
  elif context.getSlapState() == "start_requested":
    state = 'started'
  else:
    state = 'destroyed'

  import json
  result_dict = {
      'title': context.getTitle(),
      'status': state,
      '_links': {
        "self": { "href": context.Base_getRequestUrl() },
        "index": {
          "href": "urn:jio:get:%s" % context.getRelativeUrl(),
          "title": "Software Installation"
        },
      },
    }
  url_string = context.getUrlString(None)
  if url_string is not None:
    result_dict["_links"]["software_release"] = { "href": url_string }

  response.setHeader('Content-Type', mime_type)
  return json.dumps(result_dict)
