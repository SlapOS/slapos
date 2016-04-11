support_request = context
portal = context.getPortalObject()

resource = portal.service_module.slapos_crm_information.getRelativeUrl()
# create Web message if needed for this ticket
last_event = context.portal_catalog.getResultValue(
             title=message_title,
             follow_up_uid=support_request.getUid(), 
             sort_on=[('delivery.start_date', 'DESC')],
)
if last_event:
  # User has already been notified for this problem.
  return last_event

event = portal.event_module.slapos_crm_web_message_template.\
  Base_createCloneDocument(batch_mode=1)

event.edit(
  title=message_title,
  text_content=message,
  start_date = DateTime(),
  resource = resource,
  source=source_relative_url,
  follow_up=support_request.getRelativeUrl(),
)
event.stop()
event.deliver()

event.immediateReindexObject()

return event
