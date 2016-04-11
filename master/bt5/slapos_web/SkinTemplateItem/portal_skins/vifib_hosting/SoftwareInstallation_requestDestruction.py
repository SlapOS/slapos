context.getAggregateValue(portal_type='Computer').requestSoftwareRelease(software_release_url=context.getUrlString(), state='destroyed')
context.Base_redirect('view', keep_items={'portal_status_message': 'Requested Destruction'})
