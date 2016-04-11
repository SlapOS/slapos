computer = context
portal = context.getPortalObject()

software_installation_list = portal.portal_catalog(
      portal_type='Software Installation',
      default_aggregate_uid=context.getUid(),
      validation_state='validated',
      limit=1,
      url_string={'query': portal.portal_catalog.getResultValue(uid=software_release_uid).getUrlString(), 'key': 'ExactMatch'},
      sort_on=(('creation_date', 'DESC'),)
    )

if len(software_installation_list) == 0:
  return 'Destroyed'  

software_installation = software_installation_list[0].getObject()

s = software_installation.getSlapState()
if s == 'start_requested':
  return 'Installation requested'
else:
  return 'Destruction requested'
