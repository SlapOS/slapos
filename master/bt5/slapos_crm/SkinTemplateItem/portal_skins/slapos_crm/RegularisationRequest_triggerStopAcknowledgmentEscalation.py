from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

notification_message = context.getPortalObject().portal_notifications.getDocumentValue(reference="slapos-crm.stop.acknowledgment.escalation")
if notification_message is None:
  subject = 'Last reminder: invoice payment requested'
  body = """Dear user,

We would like to remind you the unpaid invoice you have on %s.
If no payment is done during the coming days, we will delete all your instances.

Do not hesitate to visit the web forum (http://community.slapos.org/forum) in case of question.

Regards,
The slapos team
""" % context.getPortalObject().portal_preferences.getPreferredSlaposWebSiteUrl()
else:
  subject = notification_message.getTitle()
  body = notification_message.convert(format='text')[1]

return context.RegularisationRequest_checkToTriggerNextEscalationStep(
  13,
  'service_module/slapos_crm_stop_acknowledgement',
  'service_module/slapos_crm_delete_reminder',
  subject,
  body,
  'Deleting reminder.',
)
