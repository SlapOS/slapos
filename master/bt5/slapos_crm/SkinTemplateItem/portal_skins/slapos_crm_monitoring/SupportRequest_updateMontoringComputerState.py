from DateTime import DateTime
import json

from Products.ERP5Type.DateUtils import addToDate

portal = context.getPortalObject()

if context.getSimulationState() == "invalidated":
  return

document = context.getSourceProjectValue()

if document is not None and document.getPortalType() == "Computer":
  memcached_dict = context.getPortalObject().portal_memcached.getMemcachedDict(
    key_prefix='slap_tool',
    plugin_path='portal_memcached/default_memcached_plugin')

  try:
    d = json.loads(memcached_dict[computer.getReference()])
    last_contact = DateTime(d.get('created_at'))
    if not ((DateTime() - last_contact) < 0.01):
      return 
  except KeyError:
    return
  
  person = context.getDestinationDecision(portal_type="Person")
  if not person:
    return 

  if context.getSimulationState() != "suspended":
    context.suspend()

  # Send Notification message
  message = """ Suspending this ticket as the computer contacted is contactin again. 
  """

  notification_reference = "slapos-crm-support-request-suspend-computer-back-notification"
  notification_message = portal.portal_notifications.getDocumentValue(
                 reference=notification_reference)

  if notification_message is not None:
    mapping_dict = {'hosting_subscription_title':document.getTitle(), 
                    'last_contact' : last_contact }

    message = notification_message.asText(
              substitution_method_parameter_dict={'mapping_dict':mapping_dict})
  
  return context.SupportRequest_trySendNotificationMessage(
              "Hosting Subscription was destroyed was destroyed by the user", message, person)
