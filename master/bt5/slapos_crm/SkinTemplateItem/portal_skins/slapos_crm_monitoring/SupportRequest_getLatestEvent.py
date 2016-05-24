portal = context.getPortalObject()


return portal.portal_catalog.getResultValue(
  follow_up_uid=context.getUid(),
  portal_type=portal.getPortalEventTypeList(),
  validation_state=["started", "stopped", "deliveried"],
  sort_on=(("modification_date", 'DESC'),))
