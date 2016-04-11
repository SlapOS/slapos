portal = context.getPortalObject()

portal.portal_catalog.searchAndActivate(
  portal_type="Computer Consumption TioXML File",
  validation_state="submitted",
  method_id='ComputerConsumptionTioXMLFile_solveInvoicingGeneration',
  activity_count=1,
  packet_size=1,
  activate_kw={'tag': tag, 'priority': 5}
)

context.activate(after_tag=tag).getId()
