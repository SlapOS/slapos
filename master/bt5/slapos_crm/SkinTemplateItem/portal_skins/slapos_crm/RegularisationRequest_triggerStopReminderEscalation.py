from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

notification_message = context.getPortalObject().portal_notifications.getDocumentValue(reference="slapos-crm.stop.reminder.escalation")
if notification_message is None:
  subject = 'Acknowledgment: instances stopped'
  body = """Dear user,

Despite our last reminder, you still have an unpaid invoice on %s.
We will now stop all your current instances to free some hardware resources.

Do not hesitate to visit the web forum (http://community.slapos.org/forum) in case of question.

Regards,
The slapos team
""" % context.getPortalObject().portal_preferences.getPreferredSlaposWebSiteUrl()
else:
  subject = notification_message.getTitle()
  body = notification_message.convert(format='text')[1]

return context.RegularisationRequest_checkToTriggerNextEscalationStep(
  7,
  'service_module/slapos_crm_stop_reminder',
  'service_module/slapos_crm_stop_acknowledgement',
  subject,
  body,
  'Stopping acknowledgment.',
)
