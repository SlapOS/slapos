from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

portal = context.getPortalObject()
ticket = context
current_service = portal.restrictedTraverse(current_service_relative_url)
assert current_service.getPortalType() == "Service"

event_portal_type = "Mail Message"

event = portal.portal_catalog.getResultValue(
  portal_type=event_portal_type,
  default_resource_uid=current_service.getUid(),
  default_follow_up_uid=ticket.getUid(),
  simulation_state="delivered",
)

if (ticket.getSimulationState() == 'suspended') and (event is not None) and (ticket.getResource() == current_service_relative_url):
  if (DateTime() - event.getStartDate()) > delay_period_in_days:
    ticket.RegularisationRequest_checkToSendUniqEvent(next_service_relative_url, title, text_content, comment)
    return event.getRelativeUrl()

return None
