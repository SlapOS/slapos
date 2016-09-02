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

if check_service_provider and person.Person_isServiceProvider():
  return

edit_kw = {
  'allocation_scope': target_allocation_scope,
}

# Create a ticket (or re-open it) for this issue!
request_title = 'Allocation scope of %s changed to %s' % (computer_reference,
                                               target_allocation_scope)
request_description = 'Allocation scope has been changed to ' \
                     '%s for %s' % (target_allocation_scope, computer_reference)

support_request = context.Base_generateSupportRequestForSlapOS(
               request_title,
               request_description,
               computer.getRelativeUrl()
             )

if support_request is not None:
  if support_request.getSimulationState() != "validated":
    support_request.validate()

  # Send notification message
  message = request_description
  notification_message = portal.portal_notifications.getDocumentValue(
                 reference=notification_message_reference)

  if notification_message is not None:
    mapping_dict = {'computer_title':computer.getTitle(),
                    'computer_id':computer_reference,
                    'computer_url':computer.getRelativeUrl(),
                    'allocation_scope':allocation_scope}
  
    message = notification_message.asText(
              substitution_method_parameter_dict={'mapping_dict': mapping_dict})

  event = support_request.SupportRequest_trySendNotificationMessage(
           request_title, message, person.getRelativeUrl())

  if event is not None:
    # event added, suspend ticket
    if portal.portal_workflow.isTransitionPossible(support_request, 'suspend'):
      support_request.suspend()
  elif not force:
    return support_request

  computer.edit(**edit_kw)
  return support_request

elif force:
  # Update computer event if ticket is not created
  computer.edit(**edit_kw)
