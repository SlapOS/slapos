portal = context.getPortalObject()

return portal.portal_catalog.getResultValue(
  follow_up_uid=context.getUid(),
  portal_type=portal.getPortalEventTypeList(),
  simulation_state=["confirmed", "started", "stopped", "delivered"],
  sort_on=(("modification_date", 'DESC'),))
