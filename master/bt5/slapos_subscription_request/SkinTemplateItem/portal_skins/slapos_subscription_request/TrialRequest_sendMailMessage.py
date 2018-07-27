portal = context.getPortalObject()

notification_message = portal.portal_notifications.getDocumentValue(
                     reference=notification_message_reference)

subject = notification_message.getTitle()

message = notification_message.asText(
  substitution_method_parameter_dict={'mapping_dict': mapping_dict})


person_title = "%s FREE TRIAL" % email

free_trial_destination = portal.portal_catalog.getResultValue(
  portal_type="Person",
  title=person_title,
  reference=None)

    
if free_trial_destination is None:
  free_trial_destination = portal.person_module.newContent(
    portal_type="Person",
    title=person_title)

  free_trial_destination.setDefaultEmailText(email)

event = portal.event_module.newContent(
       portal_type="Mail Message",
       start_date=DateTime(),
       destination=free_trial_destination.getRelativeUrl(),
       follow_up=context.getRelativeUrl(),
       source=sender.getRelativeUrl(),
       title=subject,
       resource="service_module/slapos_crm_information",
       text_content=message,
    )


portal.portal_workflow.doActionFor(event, 'start_action', send_mail=True)
event.stop()
event.deliver()
event.reindexObject()

return event
