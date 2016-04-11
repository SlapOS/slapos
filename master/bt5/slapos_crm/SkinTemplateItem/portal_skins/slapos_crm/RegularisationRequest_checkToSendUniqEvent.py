from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

portal = context.getPortalObject()
ticket = context
service = portal.restrictedTraverse(service_relative_url)
assert service.getPortalType() == "Service"
event_portal_type = "Mail Message"

# XXX TODO
# # Prevent to create 2 tickets during the same transaction
# transactional_variable = getTransactionalVariable()
# if tag in transactional_variable:
#   raise RuntimeError, 'ticket %s already exist' % tag
# else:
#   transactional_variable[tag] = None

event = portal.portal_catalog.getResultValue(
  portal_type=event_portal_type,
  default_resource_uid=service.getUid(),
  default_follow_up_uid=ticket.getUid(),
)

if (event is None) and (ticket.getSimulationState() == 'suspended'):
  tag = "%s_addUniqEvent_%s" % (ticket.getUid(), service.getUid())
  if (portal.portal_activities.countMessageWithTag(tag) > 0):
    # The event is already under creation but can not be fetched from catalog
    return None

  # Prevent concurrent transaction to create 2 events for the same ticket
  ticket.edit(resource=service_relative_url)

  event = portal.event_module.newContent(
    portal_type=event_portal_type,
    start_date=DateTime(),
    destination=ticket.getDestination(),
    follow_up=ticket.getRelativeUrl(),
    source=context.getSource(),
    title=title,
    resource=service_relative_url,
    text_content=text_content,
  )

  portal.portal_workflow.doActionFor(event, 'start_action', send_mail=True, comment=comment)
  event.stop(comment=comment)
  event.deliver(comment=comment)
  event.reindexObject(activate_kw={'tag': tag})

return event
