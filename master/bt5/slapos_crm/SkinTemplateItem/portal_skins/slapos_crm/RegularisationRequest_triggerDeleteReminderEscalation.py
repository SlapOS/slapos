from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

notification_message = context.getPortalObject().portal_notifications.getDocumentValue(reference="slapos-crm.delete.reminder.escalation")
if notification_message is None:
  subject = 'Acknowledgment: instances deleted'
  body = """Dear user,

Despite our last reminder, you still have an unpaid invoice on %s.
We will now delete all your instances.

Do not hesitate to visit the web forum (http://community.slapos.org/forum) in case of question.

Regards,
The slapos team
""" % context.getPortalObject().portal_preferences.getPreferredSlaposWebSiteUrl()
else:
  subject = notification_message.getTitle()
  body = notification_message.convert(format='text')[1]

return context.RegularisationRequest_checkToTriggerNextEscalationStep(
  2,
  'service_module/slapos_crm_delete_reminder',
  'service_module/slapos_crm_delete_acknowledgement',
  subject,
  body,
  'Deleting acknowledgment.',
)
