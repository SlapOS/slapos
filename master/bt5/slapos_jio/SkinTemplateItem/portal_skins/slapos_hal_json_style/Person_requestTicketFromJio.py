if REQUEST.other['method'] != "POST":
  response.setStatus(405)
  return ""

person = context
portal = person.getPortalObject()

support_request_template = portal.restrictedTraverse(
  portal.portal_preferences.getPreferredSupportRequestTemplate())
support_request = support_request_template.Base_createCloneDocument(batch_mode=1)

support_request.edit(
  title=title,
  destination_decision_value=person,
  resource=resource,
  start_date=DateTime(),
)
support_request.validate(comment="Submitted from the web site contact form")

web_message_template = portal.restrictedTraverse(
  portal.portal_preferences.getPreferredWebMessageTemplate())
web_message = web_message_template.Base_createCloneDocument(batch_mode=1)
# XXX init script is not called when cloning?
web_message.Event_init()
web_message.edit(
  title=title,
  content_type="text/plain",
  text_content=description,
  source_value=person,
  resource=resource,
  start_date=DateTime(),
  follow_up_value=support_request,
)
web_message.stop(comment="Submitted from the web site contact form")

return support_request.Base_redirect()
