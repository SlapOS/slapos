if REQUEST.other['method'] != "POST":
  response.setStatus(405)
  return ""

portal = context.getPortalObject()
computer = context
response = REQUEST.RESPONSE

context.Base_prepareCorsResponse(RESPONSE=response)

if allocation_scope == 'open/public':
  # Public computer capacity is handle by an alarm
  capacity_scope = 'close'
elif allocation_scope.startswith('open'):
  # Capacity is not handled for 'private' computers
  capacity_scope = 'open'
else:
  capacity_scope = 'close'

edit_kw = {
  'allocation_scope': allocation_scope,
  'capacity_scope': capacity_scope,
}

self_person = computer.getSourceAdministrationValue(portal_type="Person")
self_email = self_person.getDefaultEmailCoordinateText()
if allocation_scope == 'open/public':
  # reset friends and update in place
  edit_kw['subject_list'] = ['']
  edit_kw['destination_section'] = None
elif allocation_scope == 'open/personal':
  # reset friends to self and update in place
  edit_kw['subject_list'] = [self_email]
  edit_kw['destination_section_value'] = self_person
else:
  if self_email not in subject_list:
    # add self as friend
    subject_list.append(self_email)
  edit_kw['subject_list'] = subject_list

computer.edit(**edit_kw)

return ""
