from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

portal = context.getPortalObject()

kw.update({
  'portal_type': 'Payzen Event',
  'source': portal.Base_getPayzenServiceRelativeUrl(),
  'destination_value': context,
})

return portal.system_event_module.newContent(**kw)
