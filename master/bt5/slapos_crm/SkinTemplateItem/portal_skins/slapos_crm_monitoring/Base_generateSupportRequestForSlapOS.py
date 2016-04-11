from DateTime import DateTime

portal = context.getPortalObject()
source_project_value = portal.restrictedTraverse(source_relative_url)

if source_project_value.getPortalType() == "Computer":
  destination_decision = source_project_value.getSourceAdministration()
elif source_project_value.getPortalType() == "Software Instance":
  destination_decision = source_project_value.getSpecialiseValue().getDestinationSection()
elif source_project_value.getPortalType() == "Hosting Subscription":
  destination_decision = source_project_value.getDestinationSection()
elif source_project_value.getPortalType() == "Software Installation":
  destination_decision = source_project_value.getDestinationSection()
else:
  destination_decision = None

if portal.ERP5Site_isSupportRequestCreationClosed(destination_decision):
  # Stop ticket creation
  return

support_request_in_progress = portal.portal_catalog.getResultValue(
  portal_type = 'Support Request',
  title = title,
  simulation_state = ["validated", "submitted", "suspended"],
  source_project_uid = source_project_value.getUid(),
)

if support_request_in_progress is not None:
  return support_request_in_progress

support_request_in_progress = context.REQUEST.get("support_request_in_progress", None)

if support_request_in_progress is not None:
  return portal.restrictedTraverse(support_request_in_progress)

resource = portal.service_module.\
                  slapos_crm_monitoring.getRelativeUrl()

support_request = portal.\
    support_request_module.\
    slapos_crm_support_request_template_for_monitoring.\
    Base_createCloneDocument(batch_mode=1)
support_request.edit(
    title = title,
    description = description,
    start_date = DateTime(),
    destination_decision=destination_decision,
    source_project_value = source_project_value,
    resource=resource
  )
support_request.validate()

context.REQUEST.set("support_request_in_progress", support_request.getRelativeUrl())

return support_request
