from zExceptions import Unauthorized
portal = context.getPortalObject()
web_site = context.getWebSiteValue()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()

# XXX Proxy role is Manager so user to open ticket which is closed.
# We check permissions
if not person:
  raise Unauthorized("You need to be logged in before modify this object!")

if context.getDestinationDecision() != person.getRelativeUrl():
  raise Unauthorized

request = context.REQUEST
if 'field_your_description' in request:
  description = request['field_your_description']
else:
  return context.Base_redirect('view', keep_items={'portal_status_message':context.Base_translateString('No changes.')})

web_message_template = portal.restrictedTraverse(
    portal.portal_preferences.getPreferredWebMessageTemplate())
web_message = web_message_template.Base_createCloneDocument(batch_mode=1)
# XXX init script is not called when cloning?
# web_message.Event_init()
# XXX cannot call init script here with proxy role as Manager.
web_message.setContentType(portal.portal_preferences.getPreferredTextFormat())
web_message.Event_generateReference()

web_message.edit(
  title="Re: %s" % context.getTitle(),
  content_type="text/plain",
  text_content=description,
  source_value=person,
  resource=context.getResource(),
  start_date=DateTime(),
  follow_up_value=context,
)

web_message.stop(comment="Submitted from the web site contact form")
if portal.portal_workflow.isTransitionPossible(context, "validate"):
  context.validate(comment="See %s" % web_message.getRelativeUrl())

# Redirect to web site to hide the indexation process
web_site.Base_redirect('view', keep_items={'editable_mode': 0, 'portal_status_message':context.Base_translateString('Ticket updated.')})
