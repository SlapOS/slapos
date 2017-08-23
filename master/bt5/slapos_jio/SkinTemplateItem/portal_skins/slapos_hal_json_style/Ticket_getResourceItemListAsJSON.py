"""
  This script is a workarround as the responde for Ticket_getResourceItemList
  under a jio_getAttachement is not JSON friendly for parsing in Javascript.
  it returns [("", "")] instead of [["", ""]]

  Please remove this script as soon it is possible.
"""
import json
return json.dumps(context.Ticket_getResourceItemList(portal_type="Support Request", include_context=False))
