from DateTime import DateTime
import json

from Products.ERP5Type.DateUtils import addToDate

portal = context.getPortalObject()
document = context.getSourceProjectValue()

if document is None:
  return

has_error = False

# Check if at least one software Instance is Allocated
for instance in document.getSpecialiseRelatedValueList(
                 portal_type=["Software Instance", "Slave Instance"]):
  if instance.getSlapState() not in ["start_requested", "stop_requested"]:
    continue

  if instance.getAggregateValue() is not None:
    if instance.getPortalType() == "Software Instance" and \
        instance.SoftwareInstance_hasReportedError():
      has_error = True
      break
  else:
    has_error = True
    break
    
if not has_error:
  person = context.getDestinationDecision(portal_type="Person")
  if not person:
    return 

  if context.getSimulationState() == "validated":
    context.suspend()
  else:
    return 

  # Send Notification message
  message = """ Suspending this ticket as the problem is not present anymore. 
  """

  notification_reference = "slapos-crm-support-request-suspend-hs-notification"
  notification_message = portal.portal_notifications.getDocumentValue(
                 reference=notification_reference)

  if notification_message is not None:
    mapping_dict = {'hosting_subscription_title':document.getTitle()}

    message = notification_message.asText(
              substitution_method_parameter_dict={'mapping_dict':mapping_dict})
  
  return context.SupportRequest_trySendNotificationMessage(
              "Suspending this ticket as the problem is not present anymore", message, person)
