if REQUEST.other['method'] != "POST":
  response.setStatus(405)
  return ""

ticket = context
portal = ticket.getPortalObject()
person = ticket.getDestinationDecisionValue()

web_message_template = portal.restrictedTraverse(
  portal.portal_preferences.getPreferredWebMessageTemplate())
web_message = web_message_template.Base_createCloneDocument(batch_mode=1)
# XXX init script is not called when cloning?
web_message.Event_init()
web_message.edit(
  title="Re: %s" % context.getTitle(),
  content_type="text/plain",
  text_content=description,
  source_value=person,
  resource=ticket.getResource(),
  start_date=DateTime(),
  follow_up_value=ticket,
)
web_message.stop(comment="Submitted from the web site contact form")
if portal.portal_workflow.isTransitionPossible(context, "validate"):
  context.validate(comment="See %s" % web_message.getRelativeUrl())

return ""
