from DateTime import DateTime
from Products.ERP5Type.DateUtils import addToDate
portal = context.getPortalObject()

person = portal.portal_catalog.getResultValue(
  portal_type="Person", 
  reference="free_trial_user")

if person is None:
  return "Free Trial Person not Found"

connection_key_list = context.getSubjectList()

instance = context.getAggregateValue()

email = context.getDefaultEmailText()

connection_dict = instance.getConnectionXmlAsDict()
state = instance.getSlapState()

if context.getValidationState() in ["validated", "invalidated"]:
  return "Already Valid Skip"

if state != "destroy_requested":
  if connection_dict:

    if len([ x for x, y in connection_dict.items() if x in connection_key_list]) != len(connection_key_list):
      return "Not ready %s != %s" % ([ x for x, y in connection_dict.items() if x in connection_key_list], connection_key_list)
 
    for x, y in connection_dict.items():
      if x in connection_key_list and y in ['None', None, 'http://', '']:
        return "key %s has invalid value %s" % (x, y)

    connection_string = '\n'.join(['%s: %s' % (x,y) for x,y in connection_dict.items() if x in connection_key_list])

    notification_message_reference = 'slapos-free.trial.token'

    notification_message = portal.portal_notifications.getDocumentValue(
                     reference=notification_message_reference)

    subject = notification_message.getTitle()

    mapping_dict = {"token": connection_string }

    message = message = notification_message.asText(
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
       source=person.getRelativeUrl(),
       title=subject,
       resource="service_module/slapos_crm_information",
       text_content=message,
    )


    portal.portal_workflow.doActionFor(event, 'start_action', send_mail=True)
    event.stop()
    event.deliver()
    event.reindexObject()

    context.validate()
