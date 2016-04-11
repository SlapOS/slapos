portal = context.getPortalObject()

portal.portal_catalog.searchAndActivate(
  portal_type=["Slave Instance", "Software Instance"],
  causality_state="diverged",
  method_id='Instance_solveInvoicingGeneration',
  activate_kw={'tag': tag},
  packet_size=1, # Separate calls to many transactions (calculation can take time)
  activity_count=1,
)

context.activate(after_tag=tag).getId()
