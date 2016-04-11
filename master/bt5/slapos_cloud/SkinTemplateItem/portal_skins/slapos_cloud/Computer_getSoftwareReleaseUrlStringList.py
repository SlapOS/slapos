url_string_list = []
for software_installation in context.getPortalObject().portal_catalog(
  portal_type='Software Installation',
  validation_state='validated',
  default_aggregate_uid=context.getUid()
):
  if software_installation.getSlapState() == 'start_requested':
    url_string = software_installation.getUrlString()
    if url_string:
      url_string_list.append(url_string)
return url_string_list
