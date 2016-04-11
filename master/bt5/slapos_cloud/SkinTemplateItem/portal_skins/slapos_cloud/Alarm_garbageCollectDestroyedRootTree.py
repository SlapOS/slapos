portal = context.getPortalObject()

portal.portal_catalog.searchAndActivate(
  portal_type=["Slave Instance", "Software Instance"],
  validation_state="validated",
  specialise_validation_state="archived",
  method_id='Instance_tryToGarbageCollect',
  activate_kw={'tag': tag}
)

context.activate(after_tag=tag).getId()
