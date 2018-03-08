import json
kw = {"node_uid": context.getUid(),
      "at_date": DateTime(),
      "limit": 1}

return json.dumps(len(context.portal_simulation.getCurrentTrackingList(**kw)))
