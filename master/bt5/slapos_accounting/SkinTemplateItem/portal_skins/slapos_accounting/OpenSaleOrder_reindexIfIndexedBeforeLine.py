from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

order = context
portal = context.getPortalObject()
indexation_timestamp = portal.portal_catalog(
  uid=order.getUid(),
  select_dict={'indexation_timestamp': None})[0].indexation_timestamp

line_list = portal.portal_catalog(
  portal_type="Open Sale Order Line", 
  parent_uid=order.getUid(),
  indexation_timestamp={'query': indexation_timestamp, 'range': 'nlt'},
  limit=1)

if len(line_list):
  order.activate().immediateReindexObject()
