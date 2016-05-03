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

if request.get("shared", None) is not None:
  if str(request.get("shared", "")).lower() in ['0', 'false']:
    option_dict['parameter']['shared'] = False
  if str(request.get("shared", "")).lower() in ['1', 'true']:
    option_dict['parameter']['shared'] = True
  

if request.get("restricted_softwaretype", None) is not None:
  
  if str(request.get("restricted_softwaretype", "")).lower() in ['0', 'false']:
    option_dict['parameter']['restricted_softwaretype'] = False
  if str(request.get("restricted_softwaretype", "")).lower() in ['1', 'true']:
    option_dict['parameter']['restricted_softwaretype'] = True
    

if request.get("parameter_hash", None) is not None:
  option_dict['parameter']['parameter_hash'] = request.get("parameter_hash", None)

if context.getPortalType() == "Hosting Subscription":
  option_dict['parameter']['softwaretype'] = context.getSourceReference()
  if context.getTextContent() is not None:
    option_dict['parameter']['parameter_hash'] = base64.b64encode(context.getTextContent())
  option_dict['parameter']['restricted_softwaretype'] = True
  option_dict['parameter']['shared'] = False
  predecessor = context.getPredecessorValue(portal_type=["Software Instance", "Slave Instance"])
  if predecessor is not None and predecessor.getPortalType() == "Slave Instance":
    option_dict['parameter']['shared'] = True

return json.dumps(option_dict)
