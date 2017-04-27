portal = context.getPortalObject()

# TODO: We should filter for the specialise related
# (Hosting Subscription) which are on stop_requested
# state too.

portal.portal_catalog.searchAndActivate(
  portal_type=["Slave Instance", "Software Instance"],
  validation_state="validated",
  specialise_validation_state="validated",
  method_id='Instance_tryToStopCollect',
  activate_kw={'tag': tag},
  **{"slapos_item.slap_state": "start_requested"}
)

context.activate(after_tag=tag).getId()
