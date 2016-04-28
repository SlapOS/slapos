import json
import base64

request = context.REQUEST

option_dict = {
  'parameter' : {
    'json_url': "%s.json" % context.getUrlString(),
    'parameter_hash': base64.b64encode('<?xml version="1.0" encoding="utf-8" ?><instance></instance>'),
    'restricted_softwaretype': False
    },
  }

if request.get("software_type", None) is not None:
  option_dict['parameter']['softwaretype'] = request.get("software_type", None)
  
if request.get("parameter_hash", None) is not None:
  option_dict['parameter']['parameter_hash'] = request.get("parameter_hash", None)

if context.getPortalType() == "Hosting Subscription":
  option_dict['parameter']['softwaretype'] = context.getSourceReference()
  if context.getTextContent() is not None:
    option_dict['parameter']['parameter_hash'] = base64.b64encode(context.getTextContent())
  option_dict['parameter']['restricted_softwaretype'] = True

return json.dumps(option_dict)
