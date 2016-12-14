from DateTime import DateTime
portal = context.getPortalObject()

portal.portal_catalog.searchAndActivate(
  portal_type="Trial Request",
  validation_state="draft",
  method_id="TrialRequest_processRequest",
  activity_kw={tag: tag}

)

portal.portal_catalog.searchAndActivate(
  portal_type="Trial Request",
  validation_state="submitted",
  method_id="TrialRequest_processNotify",
  activity_kw={tag: tag}
)

portal.portal_catalog.searchAndActivate(
  portal_type="Trial Request",
  validation_state="validated",
  creation_date="<=%s" % (DateTime()-1).strftime("%Y/%m/%d"),
  method_id="TrialRequest_processDestroy",
  packet_size=1,
  activity_count=1,
  activity_kw={tag: tag}
)
context.activate(after_tag=tag).getId()
