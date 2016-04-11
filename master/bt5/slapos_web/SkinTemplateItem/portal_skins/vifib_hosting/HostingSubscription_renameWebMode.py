request = context.REQUEST

if not context.getPortalType() == "Hosting Subscription":
  return context.Base_redirect('view', keep_items={'portal_status_message':context.Base_translateString('Hosting subscription is needed!')})
if 'field_your_new_title' in request:
  context.edit(short_title=request['field_your_new_title'], description=request.get('field_your_description', ''))
  return context.Base_redirect('view', keep_items={'portal_status_message':context.Base_translateString('Hosting subscription edited.')})

return context.Base_redirect('HostingSubscription_viewUpdateInformationAsWeb', keep_items={})
