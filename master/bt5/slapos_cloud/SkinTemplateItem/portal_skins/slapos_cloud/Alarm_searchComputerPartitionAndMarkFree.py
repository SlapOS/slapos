portal = context.getPortalObject()

portal.portal_catalog.searchAndActivate(
  portal_type=["Software Instance", "Slave Instance"],
  default_aggregate_relative_url="computer_module/%/%",
  validation_state="invalidated",
  method_id='Instance_tryToUnallocatePartition',
  activate_kw={'tag': tag}
)

context.activate(after_tag=tag).getId()
