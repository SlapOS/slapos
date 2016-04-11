request = context.REQUEST
if 'field_your_instance_xml' in request:
  if context.getTextContent() != request['field_your_instance_xml']:
    context.HostingSubscription_requestPerson(instance_xml=request['field_your_instance_xml'])
    return context.Base_redirect('view', keep_items={'portal_status_message':context.Base_translateString('Data updated.')})
return context.Base_redirect('view', keep_items={'portal_status_message':context.Base_translateString('No changes.')})
