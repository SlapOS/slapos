portal = context.getPortalObject()

event = portal.portal_catalog.getResultValue(
             follow_up_uid=context.getUid(), 
             sort_on=[('modification_date', 'DESC')],
)


if event:
  return event.getModificationDate()

return context.getModificationDate()
