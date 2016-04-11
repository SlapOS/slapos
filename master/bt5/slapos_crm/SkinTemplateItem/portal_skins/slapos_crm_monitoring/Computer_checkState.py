from DateTime import DateTime
import json

portal = context.getPortalObject()

if portal.ERP5Site_isSupportRequestCreationClosed():
  # Stop ticket creation
  return

reference = context.getReference()
computer_title = context.getTitle()
ticket_title = "[MONITORING] Lost contact with computer %s" % reference
description = ""
should_notify = True
last_contact = "No Contact Information"

memcached_dict = context.getPortalObject().portal_memcached.getMemcachedDict(
  key_prefix='slap_tool',
  plugin_path='portal_memcached/default_memcached_plugin')

try:
  d = memcached_dict[reference]
  d = json.loads(d)
  last_contact = DateTime(d.get('created_at'))
  if (DateTime() - last_contact) > 0.01:
    description = "The Computer %s (%s) has not contacted the server for more than 30 minutes" \
    "(last contact date: %s)" % (computer_title, reference, last_contact)
  else:
    should_notify = False
except KeyError:
  ticket_title = "[MONITORING] No information about %s" % reference
  description = "The Computer %s (%s)  has not contacted the server (No Contact Information)" % (
                  computer_title, reference)

if should_notify:
  support_request = context.Base_generateSupportRequestForSlapOS(
    ticket_title,
    description,
    context.getRelativeUrl()
  )

  person = context.getSourceAdministrationValue(portal_type="Person")
  if not person:
    return support_request

  # Send Notification message
  notification_reference = 'slapos-crm-computer_check_state.notification'
  notification_message = portal.portal_notifications.getDocumentValue(
                 reference=notification_reference)

  if notification_message is None:
    message = """%s""" % description
  else:
    mapping_dict = {'computer_title':context.getTitle(),
                    'computer_id':reference,
                    'last_contact':last_contact}
    message = notification_message.asText(
              substitution_method_parameter_dict={'mapping_dict':mapping_dict})

  support_request.SupportRequest_trySendNotificationMessage(
              ticket_title,
              message, person.getRelativeUrl())
              
  return support_request
