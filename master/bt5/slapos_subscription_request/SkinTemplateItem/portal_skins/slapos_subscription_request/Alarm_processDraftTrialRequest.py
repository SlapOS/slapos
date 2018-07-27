from DateTime import DateTime
portal = context.getPortalObject()

portal.portal_catalog.searchAndActivate(
  portal_type="Trial Request",
  validation_state="draft",
  method_id="TrialRequest_processRequest",
  activity_kw={tag: tag}

)

context.activate(after_tag=tag).getId()
