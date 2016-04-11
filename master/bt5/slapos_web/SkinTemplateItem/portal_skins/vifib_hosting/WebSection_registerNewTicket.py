portal = context.getPortalObject()
web_site = context.getWebSiteValue()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
context.REQUEST.set('new_support_request', None)

support_request_template = portal.restrictedTraverse(
  portal.portal_preferences.getPreferredSupportRequestTemplate())
support_request = support_request_template.Base_createCloneDocument(batch_mode=1)

kw = {}
if context.getPortalType() in ["Hosting Subscription", "Computer"]:
  kw['source_project'] = context.getRelativeUrl()

support_request.edit(
  title=title,
  destination_decision_value=person,
  resource=resource,
  start_date=DateTime(),
  **kw
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

keep_item_dict = {'editable_mode': 0, 
  'new_support_request': support_request.getRelativeUrl(), 
  'portal_status_message':context.Base_translateString('Ticket created.')}


if context.getPortalType() in ["Hosting Subscription", "Computer"]:
  return context.Base_redirect('', keep_items=keep_item_dict)
else:
  web_site.myspace.Base_redirect('', keep_items=keep_item_dict)
