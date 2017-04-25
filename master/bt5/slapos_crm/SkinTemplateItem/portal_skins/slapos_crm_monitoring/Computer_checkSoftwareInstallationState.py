from DateTime import DateTime
import json

portal = context.getPortalObject()

if portal.ERP5Site_isSupportRequestCreationClosed():
  # Stop ticket creation
  return

software_installation_list = portal.portal_catalog(
      portal_type='Software Installation',
      default_aggregate_uid=context.getUid(),
      validation_state='validated',
      sort_on=(('creation_date', 'DESC'),)
    )

support_request_list = []
computer_reference = context.getReference()
computer_title = context.getTitle()
should_notify = True

memcached_dict = context.getPortalObject().portal_memcached.getMemcachedDict(
  key_prefix='slap_tool',
  plugin_path='portal_memcached/default_memcached_plugin')

tolerance = DateTime()-0.5
for software_installation in software_installation_list:
  should_notify = False
  if software_installation.getCreationDate() > tolerance:
    # Give it 12 hours to deploy.
    continue

  reference = software_installation.getReference()
  try:
    d = memcached_dict[reference]
    d = json.loads(d)
    last_contact = DateTime(d.get('created_at'))
    if d.get("text").startswith("building"):
      should_notify = True
      ticket_title = "[MONITORING] %s is building for too long on %s" % (reference, computer_reference)
      description = "The software release %s is building for mode them 12 hours on %s, started on %s" % \
              (software_installation.getUrlString(), computer_title, software_installation.getCreationDate())
    elif d.get("text").startswith("#access"):
      # Nothing to do.
      pass
    elif d.get("text").startswith("#error"):
      should_notify = True
      ticket_title = "[MONITORING] %s is failing to build on %s" % (reference, computer_reference)
      description = "The software release %s is failing to build for too long on %s, started on %s" % \
        (software_installation.getUrlString(), computer_title, software_installation.getCreationDate())

  except KeyError:
    ticket_title = "[MONITORING] No information for %s on %s" % (reference, computer_reference)
    description = "The software release %s did not started to build on %s since %s" % \
        (software_installation.getUrlString(), computer_title, software_installation.getCreationDate())

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
    notification_reference = 'slapos-crm-computer_software_installation_state.notification'
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

    support_request_list.append(support_request)

return support_request_list
