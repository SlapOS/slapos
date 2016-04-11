portal = context.getPortalObject()

portal.portal_catalog.searchAndActivate(
  portal_type=["Slave Instance", "Software Instance"],
  validation_state="validated",
  specialise_validation_state="validated",
  method_id='Instance_tryToStopCollect',
  activate_kw={'tag': tag}
)

context.activate(after_tag=tag).getId()
