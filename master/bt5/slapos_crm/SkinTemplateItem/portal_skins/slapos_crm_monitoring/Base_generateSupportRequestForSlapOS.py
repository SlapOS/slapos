from DateTime import DateTime

portal = context.getPortalObject()
aggregate_value = portal.restrictedTraverse(source_relative_url)

if aggregate_value.getPortalType() == "Computer":
  destination_decision = aggregate_value.getSourceAdministration()
elif aggregate_value.getPortalType() == "Software Instance":
  destination_decision = aggregate_value.getSpecialiseValue().getDestinationSection()
elif aggregate_value.getPortalType() == "Hosting Subscription":
  destination_decision = aggregate_value.getDestinationSection()
elif aggregate_value.getPortalType() == "Software Installation":
  destination_decision = aggregate_value.getDestinationSection()
else:
  destination_decision = None

if portal.ERP5Site_isSupportRequestCreationClosed(destination_decision):
  # Stop ticket creation
  return

support_request_in_progress = portal.portal_catalog.getResultValue(
  portal_type = 'Support Request',
  title = title,
  simulation_state = ["validated", "submitted", "suspended"],
  default_aggregate_uid = aggregate_value.getUid(),
)

if support_request_in_progress is not None:
  return support_request_in_progress

support_request_in_progress = context.REQUEST.get("support_request_in_progress", None)

if support_request_in_progress is not None:
  support_request = portal.restrictedTraverse(support_request_in_progress, None)
  if support_request and support_request.getTitle() == title and \
        support_request.getAggregatetUid() == aggregate_value.getUid():
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
    aggregate_value = aggregate_value,
    resource=resource
  )
support_request.validate()

context.REQUEST.set("support_request_in_progress", support_request.getRelativeUrl())

return support_request
