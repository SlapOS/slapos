request = context.REQUEST

def isSoftwareTypeChanged(software_type):
  base_type = ['RootSoftwareInstance', 'default']
  current_software_type = context.getSourceReference()
  if software_type in base_type and current_software_type in base_type:
    return False
  else:
    return current_software_type != software_type

if 'software_type' in request and isSoftwareTypeChanged(request['software_type']):
  message = "Sorry, you cannot change 'Software Type' value."
  return context.Base_redirect('view', keep_items={'portal_status_message':context.Base_translateString(message)})
if 'field_your_instance_xml' in request:
  if context.getTextContent() != request['field_your_instance_xml']:
    context.HostingSubscription_requestPerson(instance_xml=request['field_your_instance_xml'])
    return context.Base_redirect('view', keep_items={'portal_status_message':context.Base_translateString('Data updated.')})
return context.Base_redirect('view', keep_items={'portal_status_message':context.Base_translateString('No changes.')})
