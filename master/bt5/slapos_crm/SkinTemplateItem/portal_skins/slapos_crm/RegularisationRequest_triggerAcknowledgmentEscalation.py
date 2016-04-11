from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

notification_message = context.getPortalObject().portal_notifications.getDocumentValue(reference="slapos-crm.acknowledgment.escalation")
if notification_message is None:
  subject = 'Reminder: invoice payment requested'
  body = """Dear user,

We would like to remind you the unpaid invoice you have on %s.
If no payment is done during the coming days, we will stop all your current instances to free some hardware resources.

Do not hesitate to visit the web forum (http://community.slapos.org/forum) in case of question.

Regards,
The slapos team
""" % context.getPortalObject().portal_preferences.getPreferredSlaposWebSiteUrl()

else:
  subject = notification_message.getTitle()
  body = notification_message.convert(format='text')[1]

return context.RegularisationRequest_checkToTriggerNextEscalationStep(
  38,
  'service_module/slapos_crm_acknowledgement',
  'service_module/slapos_crm_stop_reminder',
  subject,
  body,
  'Stopping reminder.',
)
