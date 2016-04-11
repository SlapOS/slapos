portal = context.getPortalObject()

ticket_title = "Hosting Subscription %s is failing." % context.getTitle()

description = "%s contains software instances which are unallocated or reporting errors." % (
        context.getTitle())
       
support_request = context.Base_generateSupportRequestForSlapOS(
  ticket_title,
  description,
  context.getRelativeUrl())

if support_request is None:
  return
  
person = context.getDestinationSectionValue(portal_type="Person")
if not person:
  return
  
if support_request.getSimulationState() != "validated":
  support_request.validate()

# Send Notification message
message = description

notification_reference = notification_message_reference
notification_message = portal.portal_notifications.getDocumentValue(
                 reference=notification_reference)
if notification_message is not None:
  mapping_dict = {'hosting_subscription_title':context.getTitle(),
                  'instance': instance.getTitle()}

  message = notification_message.asText(
              substitution_method_parameter_dict={'mapping_dict':mapping_dict})
  
return support_request.SupportRequest_trySendNotificationMessage(
              ticket_title, message, person.getRelativeUrl())
