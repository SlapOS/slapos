from DateTime import DateTime

computer = context
portal = context.getPortalObject()
allocation_scope = computer.getAllocationScope()
computer_reference = computer.getReference()

if allocation_scope not in ['open/public', 'open/friend', 'open/personal']:
  return

if allocation_scope == target_allocation_scope:
  # already changed
  return

person = computer.getSourceAdministrationValue(portal_type="Person")
if not person:
  return

if not person.Person_isServiceProvider():
  edit_kw = {
    'allocation_scope': target_allocation_scope,
  }

  # Create a ticket (or re-open it) for this issue!
  request_title = 'We have changed allocation scope for %s' % computer_reference
  request_description = 'Allocation scope has been changed to ' \
                       '%s for %s' % (target_allocation_scope, computer_reference)
            
  support_request = context.Base_generateSupportRequestForSlapOS(
                 request_title,
                 request_description,
                 computer.getRelativeUrl()
               )

  if support_request.getSimulationState() != "validated":
    support_request.validate()
  
  # Send notification message
  message = request_description
  notification_message = portal.portal_notifications.getDocumentValue(
                 reference=notification_message_reference)

  if notification_message is not None:
    mapping_dict = {'computer_title':computer.getTitle(),
                    'computer_id':computer_reference,
                    'allocation_scope':allocation_scope}

    message = notification_message.asText(
              substitution_method_parameter_dict={'mapping_dict': mapping_dict})

  event = support_request.SupportRequest_trySendNotificationMessage(
           request_title, message, person.getRelativeUrl())

  if event is not None:
    computer.edit(**edit_kw)

  return support_request
