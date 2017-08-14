from zExceptions import Unauthorized
from AccessControl import getSecurityManager
if REQUEST is None:
  raise Unauthorized

response = REQUEST.RESPONSE
mime_type = 'application/json'

if REQUEST.other['method'] != "POST":
  response.setStatus(405)
  return ""
elif mime_type != context.Base_getRequestHeader('Content-Type'):
  response.setStatus(406)
  return ""
elif context.getPortalType() != "Person":
  response.setStatus(403)
  return ""
else:
  import json
  try:
    data_dict = json.loads(context.Base_getRequestBody())
  except (TypeError, ValueError):
    response.setStatus(400)
    return ""
  else:

    def dictToXml(dict_data):
      assert same_type(dict_data, {})
      result = "<?xml version='1.0' encoding='utf-8'?><instance>\n"
      for key, value in dict_data.items():
        result += """  <parameter id="%s">%s</parameter>\n""" % (key.encode("UTF-8"), value.encode("UTF-8"))
      result += "</instance>"
      return result

    try:
      parameter_kw = {
        'software_release': data_dict['software_release'].encode("UTF-8"),
        'software_title': data_dict['title'].encode("UTF-8"),
        'software_type': data_dict['software_type'].encode("UTF-8"),
        'instance_xml': dictToXml(data_dict['parameter']),
        'sla_xml': dictToXml(data_dict['sla']),
        'shared': data_dict['slave'],
        'state': data_dict['status'].encode("UTF-8"),
      }
    except KeyError:
      response.setStatus(400)
      return ""
    else:

      context.requestSoftwareInstance(**parameter_kw)
      # XXX Return hosting subscription link
      response.setStatus(201)
      return ""
